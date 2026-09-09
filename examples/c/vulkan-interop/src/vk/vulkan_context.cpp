// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "vulkan_context.hpp"

#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <stdexcept>

// Define volk implementation in this translation unit
#define VOLK_IMPLEMENTATION
#include <volk.h>

#define VK_CHECK(call)                                                           \
    do {                                                                         \
        VkResult result = call;                                                  \
        if (result != VK_SUCCESS) {                                              \
            fprintf(stderr, "Vulkan error at %s:%d: %d\n", __FILE__, __LINE__,   \
                    result);                                                     \
            throw std::runtime_error("Vulkan error");                            \
        }                                                                        \
    } while (0)

static auto uuid_matches(const uint8_t* uuid1, const uint8_t* uuid2) -> bool {
    return memcmp(uuid1, uuid2, VK_UUID_SIZE) == 0;
}

// Forward declaration for debug messenger callback
static VKAPI_ATTR VkBool32 VKAPI_CALL debug_messenger_callback(
    VkDebugUtilsMessageSeverityFlagBitsEXT message_severity,
    VkDebugUtilsMessageTypeFlagsEXT message_type,
    VkDebugUtilsMessengerCallbackDataEXT const* callback_data,
    void* user_data);

VulkanContext::VulkanContext(VulkanContextConfig const& config, CUuuid const& cuda_uuid) {
    _window = config.window;
    _headless = (_window == nullptr);
    _initial_sampled_image_capacity = config.initial_sampled_image_capacity;
    _debug_callback = config.debug_callback;
    
    // Initialize volk (loads global Vulkan functions)
    if (volkInitialize() != VK_SUCCESS) {
        throw std::runtime_error("Failed to initialize volk");
    }
    
    // Initialize Vulkan
    _create_instance();
    
    // Load instance-level functions
    volkLoadInstance(_instance);
    
    // Create debug messenger if validation is enabled (now that instance functions are loaded)
    if (_validation_enabled) {
        VkDebugUtilsMessengerCreateInfoEXT messenger_info = {};
        messenger_info.sType = VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT;
        messenger_info.messageSeverity = VK_DEBUG_UTILS_MESSAGE_SEVERITY_VERBOSE_BIT_EXT |
                                          VK_DEBUG_UTILS_MESSAGE_SEVERITY_INFO_BIT_EXT |
                                          VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT |
                                          VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT;
        messenger_info.messageType = VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT |
                                      VK_DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT |
                                      VK_DEBUG_UTILS_MESSAGE_TYPE_PERFORMANCE_BIT_EXT;
        messenger_info.pfnUserCallback = debug_messenger_callback;
        messenger_info.pUserData = &_debug_callback;
        
        VK_CHECK(vkCreateDebugUtilsMessengerEXT(_instance, &messenger_info, nullptr, &_debug_messenger));
    }
    
    if (!_headless) {
        VK_CHECK(glfwCreateWindowSurface(_instance, _window, nullptr, &_surface));
    }
    
    _select_physical_device(cuda_uuid, config.initial_sampled_image_capacity);
    _find_queue_family();
    _create_device();
    
    // Load device-level functions
    volkLoadDevice(_device);
    
    if (!_headless) {
        // Get window dimensions from GLFW
        int width, height;
        glfwGetFramebufferSize(_window, &width, &height);
        _create_swapchain(width, height);
    }
    
    _create_timeline_semaphore();
    _create_descriptor_set_layout();
    _create_command_pool();
    _create_descriptor_pool_and_set();
    _create_sync_objects();
    _create_timestamp_query_pool();
}

VulkanContext::~VulkanContext() {
    vkDeviceWaitIdle(_device);
    
    // Destroy all sampled images
    for (auto& [id, img] : _sampled_images) {
        vkDestroySampler(_device, img.sampler, nullptr);
        vkDestroyImageView(_device, img.view, nullptr);
        vkDestroyImage(_device, img.image, nullptr);
        vkFreeMemory(_device, img.memory, nullptr);
    }
    _sampled_images.clear();
    
    vkDestroyQueryPool(_device, _timestamp_query_pool, nullptr);
    vkDestroyFence(_device, _in_flight_fence, nullptr);
    if (!_headless) {
        for (VkSemaphore sem : _render_finished_semaphores) {
            vkDestroySemaphore(_device, sem, nullptr);
        }
        vkDestroySemaphore(_device, _image_available_semaphore, nullptr);
    }
    vkDestroySemaphore(_device, _cuda_timeline_semaphore, nullptr);
    
    vkDestroyDescriptorPool(_device, _descriptor_pool, nullptr);
    vkDestroyDescriptorSetLayout(_device, _descriptor_set_layout, nullptr);
    
    // Destroy all shaders
    for (auto& [id, shdr] : _shaders) {
        vkDestroyShaderEXT(_device, shdr.shader, nullptr);
    }
    _shaders.clear();
    vkDestroyPipelineLayout(_device, _pipeline_layout, nullptr);
    
    vkDestroyCommandPool(_device, _command_pool, nullptr);
    
    // Note: shared image is now part of _sampled_images and cleaned up above
    
    if (!_headless) {
        for (auto view : _swapchain_image_views) {
            vkDestroyImageView(_device, view, nullptr);
        }
        
        vkDestroySwapchainKHR(_device, _swapchain, nullptr);
    }
    
    vkDestroyDevice(_device, nullptr);
    
    if (!_headless) {
        vkDestroySurfaceKHR(_instance, _surface, nullptr);
    }
    
    if (_debug_messenger != VK_NULL_HANDLE) {
        vkDestroyDebugUtilsMessengerEXT(_instance, _debug_messenger, nullptr);
    }
    
    vkDestroyInstance(_instance, nullptr);
}

auto VulkanContext::should_close() const -> bool {
    if (_headless) {
        return false;
    }
    return glfwWindowShouldClose(_window);
}

auto VulkanContext::poll_events() -> void {
    if (_headless) {
        return;
    }
    glfwPollEvents();
}

auto VulkanContext::wait_for_fence() -> void {
    vkWaitForFences(_device, 1, &_in_flight_fence, VK_TRUE, UINT64_MAX);
}

auto VulkanContext::reset_fence() -> void {
    vkResetFences(_device, 1, &_in_flight_fence);
}

auto VulkanContext::reset_fence_to_signaled() -> void {
    // Wait for any pending GPU work to complete before manipulating the fence
    vkDeviceWaitIdle(_device);
    
    // Destroy and recreate fence in signaled state
    // This is needed when we reset the fence but then don't submit work
    vkDestroyFence(_device, _in_flight_fence, nullptr);
    
    VkFenceCreateInfo fence_info = {};
    fence_info.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
    fence_info.flags = VK_FENCE_CREATE_SIGNALED_BIT;
    VK_CHECK(vkCreateFence(_device, &fence_info, nullptr, &_in_flight_fence));
}

auto VulkanContext::acquire_next_image(uint32_t& image_index) -> AcquireResult {
    if (_headless) {
        throw std::runtime_error("acquire_next_image not available in headless mode");
    }
    
    // Check for minimized window (0x0 framebuffer)
    auto size = framebuffer_size();
    if (size.x == 0 || size.y == 0) {
        return AcquireResult::Minimized;
    }
    
    VkResult acquire_result = vkAcquireNextImageKHR(_device, _swapchain, UINT64_MAX,
                          _image_available_semaphore, VK_NULL_HANDLE, &image_index);
    _current_image_index = image_index;
    
    // Out of date: image was NOT acquired, semaphore was NOT signaled.
    // Caller must recreate the swapchain before the next acquire.
    if (acquire_result == VK_ERROR_OUT_OF_DATE_KHR) {
        return AcquireResult::OutOfDate;
    }
    // Suboptimal: image WAS acquired and semaphore WAS signaled.
    // Caller should still render this frame and defer swapchain recreation.
    if (acquire_result == VK_SUBOPTIMAL_KHR) {
        return AcquireResult::Suboptimal;
    }
    if (acquire_result != VK_SUCCESS) {
        fprintf(stderr, "Vulkan error at %s:%d: %d\n", __FILE__, __LINE__, acquire_result);
        throw std::runtime_error("Vulkan error");
    }
    return AcquireResult::Success;
}

auto VulkanContext::framebuffer_size() const -> glm::ivec2 {
    if (_headless) {
        return glm::ivec2(0, 0);
    }
    int width, height;
    glfwGetFramebufferSize(_window, &width, &height);
    return glm::ivec2(width, height);
}

auto VulkanContext::recreate_swapchain() -> void {
    if (_headless) {
        throw std::runtime_error("recreate_swapchain not available in headless mode");
    }
    
    // Wait for device to be idle
    vkDeviceWaitIdle(_device);
    
    // Get new dimensions
    auto size = framebuffer_size();
    if (size.x == 0 || size.y == 0) {
        // Window is minimized, can't create swapchain
        return;
    }
    
    // Destroy old swapchain image views
    for (auto view : _swapchain_image_views) {
        vkDestroyImageView(_device, view, nullptr);
    }
    _swapchain_image_views.clear();
    _swapchain_images.clear();
    
    // Store old swapchain for efficient recreation
    VkSwapchainKHR old_swapchain = _swapchain;
    
    // Query surface capabilities
    VkSurfaceCapabilitiesKHR capabilities;
    vkGetPhysicalDeviceSurfaceCapabilitiesKHR(_physical_device, _surface, &capabilities);
    
    // Determine new extent
    if (capabilities.currentExtent.width != UINT32_MAX) {
        _swapchain_extent = capabilities.currentExtent;
    } else {
        _swapchain_extent = {static_cast<uint32_t>(size.x), static_cast<uint32_t>(size.y)};
    }
    
    uint32_t image_count = capabilities.minImageCount + 1;
    if (capabilities.maxImageCount > 0 && image_count > capabilities.maxImageCount) {
        image_count = capabilities.maxImageCount;
    }
    
    // Create new swapchain
    VkSwapchainCreateInfoKHR create_info = {};
    create_info.sType = VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR;
    create_info.surface = _surface;
    create_info.minImageCount = image_count;
    create_info.imageFormat = _swapchain_format;
    create_info.imageColorSpace = VK_COLOR_SPACE_SRGB_NONLINEAR_KHR;
    create_info.imageExtent = _swapchain_extent;
    create_info.imageArrayLayers = 1;
    create_info.imageUsage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT;
    create_info.imageSharingMode = VK_SHARING_MODE_EXCLUSIVE;
    create_info.preTransform = capabilities.currentTransform;
    create_info.compositeAlpha = VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR;
    create_info.presentMode = VK_PRESENT_MODE_FIFO_KHR;
    create_info.clipped = VK_TRUE;
    create_info.oldSwapchain = old_swapchain;
    
    VK_CHECK(vkCreateSwapchainKHR(_device, &create_info, nullptr, &_swapchain));
    
    // Destroy old swapchain
    vkDestroySwapchainKHR(_device, old_swapchain, nullptr);
    
    // Get new swapchain images
    vkGetSwapchainImagesKHR(_device, _swapchain, &image_count, nullptr);
    _swapchain_images.resize(image_count);
    vkGetSwapchainImagesKHR(_device, _swapchain, &image_count, _swapchain_images.data());
    
    // Create new image views
    _swapchain_image_views.resize(image_count);
    for (size_t i = 0; i < image_count; i++) {
        VkImageViewCreateInfo view_info = {};
        view_info.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
        view_info.image = _swapchain_images[i];
        view_info.viewType = VK_IMAGE_VIEW_TYPE_2D;
        view_info.format = _swapchain_format;
        view_info.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        view_info.subresourceRange.baseMipLevel = 0;
        view_info.subresourceRange.levelCount = 1;
        view_info.subresourceRange.baseArrayLayer = 0;
        view_info.subresourceRange.layerCount = 1;
        
        VK_CHECK(vkCreateImageView(_device, &view_info, nullptr, &_swapchain_image_views[i]));
    }
    
    // Resize per-image semaphores if image count changed
    if (image_count != _render_finished_semaphores.size()) {
        // Destroy old semaphores
        for (VkSemaphore sem : _render_finished_semaphores) {
            vkDestroySemaphore(_device, sem, nullptr);
        }
        
        // Create new semaphores
        VkSemaphoreCreateInfo semaphore_info = {};
        semaphore_info.sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO;
        
        _render_finished_semaphores.resize(image_count);
        for (uint32_t i = 0; i < image_count; ++i) {
            VK_CHECK(vkCreateSemaphore(_device, &semaphore_info, nullptr, &_render_finished_semaphores[i]));
        }
    }
    
    printf("Swapchain recreated: %ux%u\n", _swapchain_extent.width, _swapchain_extent.height);
}

auto VulkanContext::record_frame_begin(uint32_t image_index) -> void {
    if (_headless) {
        throw std::runtime_error("record_frame_begin not available in headless mode");
    }
    
    CommandBuffer cmd(_vk_command_buffer);
    
    // Transition swapchain image from UNDEFINED to COLOR_ATTACHMENT_OPTIMAL
    // Use COLOR_ATTACHMENT_OUTPUT as source stage to synchronize with the acquire semaphore wait
    cmd.image_memory_barrier(_swapchain_images[image_index], VK_IMAGE_ASPECT_COLOR_BIT,
                             VK_IMAGE_LAYOUT_UNDEFINED, VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_NONE,
                             VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT);
    
    // Begin dynamic rendering
    VkRenderingAttachmentInfo color_attachment = {};
    color_attachment.sType = VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO;
    color_attachment.imageView = _swapchain_image_views[image_index];
    color_attachment.imageLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    color_attachment.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
    color_attachment.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
    color_attachment.clearValue.color = {{0.0f, 0.0f, 0.0f, 1.0f}};
    
    VkRenderingInfo rendering_info = {};
    rendering_info.sType = VK_STRUCTURE_TYPE_RENDERING_INFO;
    rendering_info.renderArea.offset = {0, 0};
    rendering_info.renderArea.extent = _swapchain_extent;
    rendering_info.layerCount = 1;
    rendering_info.colorAttachmentCount = 1;
    rendering_info.pColorAttachments = &color_attachment;
    
    vkCmdBeginRendering(_vk_command_buffer, &rendering_info);
}

auto VulkanContext::record_frame_end(uint32_t image_index) -> void {
    if (_headless) {
        throw std::runtime_error("record_frame_end not available in headless mode");
    }
    
    vkCmdEndRendering(_vk_command_buffer);
    
    CommandBuffer cmd(_vk_command_buffer);
    
    // Transition swapchain image from COLOR_ATTACHMENT_OPTIMAL to PRESENT_SRC
    cmd.image_memory_barrier(
        _swapchain_images[image_index],
        VK_IMAGE_ASPECT_COLOR_BIT,
        VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
        VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
        VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
        VK_IMAGE_LAYOUT_PRESENT_SRC_KHR,
        VK_PIPELINE_STAGE_2_BOTTOM_OF_PIPE_BIT,
        VK_ACCESS_2_NONE);
}

auto VulkanContext::immediate_submit(std::function<void(CommandBuffer)> const& work) -> void {
    vkResetCommandBuffer(_immediate_command_buffer, 0);
    
    VkCommandBufferBeginInfo begin_info = {};
    begin_info.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
    begin_info.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    
    VK_CHECK(vkBeginCommandBuffer(_immediate_command_buffer, &begin_info));
    
    work(CommandBuffer(_immediate_command_buffer));
    
    VK_CHECK(vkEndCommandBuffer(_immediate_command_buffer));
    
    VkCommandBufferSubmitInfo cmd_submit_info = {};
    cmd_submit_info.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_SUBMIT_INFO;
    cmd_submit_info.commandBuffer = _immediate_command_buffer;
    
    VkSubmitInfo2 submit_info = {};
    submit_info.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO_2;
    submit_info.commandBufferInfoCount = 1;
    submit_info.pCommandBufferInfos = &cmd_submit_info;
    
    VK_CHECK(vkQueueSubmit2(_graphics_queue, 1, &submit_info, VK_NULL_HANDLE));
    VK_CHECK(vkQueueWaitIdle(_graphics_queue));
}

auto VulkanContext::submit_and_present(uint32_t image_index, uint64_t cuda_timeline_wait_value) -> PresentResult {
    if (_headless) {
        throw std::runtime_error("submit_and_present not available in headless mode");
    }
    
    // Use per-image render_finished semaphore indexed by the acquired image
    VkSemaphore render_finished_sem = _render_finished_semaphores[_current_image_index];
    
    // Wait on both the swapchain acquire semaphore (binary) and the CUDA
    // timeline semaphore so Vulkan cannot sample stale/in-progress interop data.
    // Binary acquire handles swapchain readiness; timeline value gates CUDA
    // producer completion for the shared image.
    VkSemaphore wait_semaphores[] = {_image_available_semaphore, _cuda_timeline_semaphore};
    VkPipelineStageFlags wait_stages[] = {
        VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,  // swapchain acquire
        VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT           // CUDA shared image read
    };
    
    // Timeline submit payload binds this submit to an exact CUDA frame value.
    // Binary semaphores still participate in this submit with ignored value 0.
    uint64_t wait_values[] = {0, cuda_timeline_wait_value};
    uint64_t signal_values[] = {0};  // render_finished_sem is binary
    
    VkTimelineSemaphoreSubmitInfo timeline_info = {};
    timeline_info.sType = VK_STRUCTURE_TYPE_TIMELINE_SEMAPHORE_SUBMIT_INFO;
    timeline_info.waitSemaphoreValueCount = 2;
    timeline_info.pWaitSemaphoreValues = wait_values;
    timeline_info.signalSemaphoreValueCount = 1;
    timeline_info.pSignalSemaphoreValues = signal_values;
    
    VkSubmitInfo submit_info = {};
    submit_info.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
    submit_info.pNext = &timeline_info;
    submit_info.waitSemaphoreCount = 2;
    submit_info.pWaitSemaphores = wait_semaphores;
    submit_info.pWaitDstStageMask = wait_stages;
    submit_info.commandBufferCount = 1;
    submit_info.pCommandBuffers = &_vk_command_buffer;
    submit_info.signalSemaphoreCount = 1;
    submit_info.pSignalSemaphores = &render_finished_sem;
    
    VK_CHECK(vkQueueSubmit(_graphics_queue, 1, &submit_info, _in_flight_fence));
    
    VkPresentInfoKHR present_info = {};
    present_info.sType = VK_STRUCTURE_TYPE_PRESENT_INFO_KHR;
    present_info.waitSemaphoreCount = 1;
    present_info.pWaitSemaphores = &render_finished_sem;
    present_info.swapchainCount = 1;
    present_info.pSwapchains = &_swapchain;
    present_info.pImageIndices = &image_index;
    
    VkResult present_result = vkQueuePresentKHR(_graphics_queue, &present_info);
    if (present_result == VK_ERROR_OUT_OF_DATE_KHR) {
        return PresentResult::OutOfDate;
    }
    if (present_result == VK_SUBOPTIMAL_KHR) {
        return PresentResult::Suboptimal;
    }
    if (present_result != VK_SUCCESS) {
        fprintf(stderr, "Vulkan error at %s:%d: %d\n", __FILE__, __LINE__, present_result);
        throw std::runtime_error("Vulkan present error");
    }
    return PresentResult::Success;
}

#ifdef _WIN32
auto VulkanContext::export_memory_handle(SampledImageHandle handle) -> void* {
    SampledImage const& img = sampled_image(handle);
    
    VkMemoryGetWin32HandleInfoKHR handle_info = {};
    handle_info.sType = VK_STRUCTURE_TYPE_MEMORY_GET_WIN32_HANDLE_INFO_KHR;
    handle_info.memory = img.memory;
    handle_info.handleType = VK_EXTERNAL_MEMORY_HANDLE_TYPE_OPAQUE_WIN32_BIT;
    
    HANDLE win_handle;
    VK_CHECK(vkGetMemoryWin32HandleKHR(_device, &handle_info, &win_handle));
    return win_handle;
}

auto VulkanContext::export_timeline_semaphore_handle() -> void* {
    VkSemaphoreGetWin32HandleInfoKHR sem_handle_info = {};
    sem_handle_info.sType = VK_STRUCTURE_TYPE_SEMAPHORE_GET_WIN32_HANDLE_INFO_KHR;
    sem_handle_info.semaphore = _cuda_timeline_semaphore;
    sem_handle_info.handleType = VK_EXTERNAL_SEMAPHORE_HANDLE_TYPE_OPAQUE_WIN32_BIT;
    
    HANDLE win_handle;
    VK_CHECK(vkGetSemaphoreWin32HandleKHR(_device, &sem_handle_info, &win_handle));
    return win_handle;
}
#else
auto VulkanContext::export_memory_handle(SampledImageHandle handle) -> int {
    SampledImage const& img = sampled_image(handle);
    
    VkMemoryGetFdInfoKHR fd_info = {};
    fd_info.sType = VK_STRUCTURE_TYPE_MEMORY_GET_FD_INFO_KHR;
    fd_info.memory = img.memory;
    fd_info.handleType = VK_EXTERNAL_MEMORY_HANDLE_TYPE_OPAQUE_FD_BIT;
    
    int fd;
    VK_CHECK(vkGetMemoryFdKHR(_device, &fd_info, &fd));
    return fd;
}

auto VulkanContext::export_timeline_semaphore_handle() -> int {
    VkSemaphoreGetFdInfoKHR fd_info = {};
    fd_info.sType = VK_STRUCTURE_TYPE_SEMAPHORE_GET_FD_INFO_KHR;
    fd_info.semaphore = _cuda_timeline_semaphore;
    fd_info.handleType = VK_EXTERNAL_SEMAPHORE_HANDLE_TYPE_OPAQUE_FD_BIT;
    
    int fd;
    VK_CHECK(vkGetSemaphoreFdKHR(_device, &fd_info, &fd));
    return fd;
}
#endif

auto VulkanContext::vulkan_elapsed_ms() -> double {
    uint64_t timestamps[2];
    // Don't use VK_QUERY_RESULT_WAIT_BIT - if results aren't ready, just return 0
    // This prevents hangs when swapchain is recreated and queries weren't completed
    VkResult result = vkGetQueryPoolResults(
        _device, _timestamp_query_pool,
        0, 2, sizeof(timestamps), timestamps, sizeof(uint64_t),
        VK_QUERY_RESULT_64_BIT);
    
    if (result == VK_SUCCESS) {
        double vulkan_time_ns = static_cast<double>(timestamps[1] - timestamps[0]) * _timestamp_period;
        return vulkan_time_ns / 1000000.0;
    }
    // VK_NOT_READY means queries aren't complete yet - just return 0
    return 0.0;
}

// Private initialization methods

// Debug messenger callback - static so it can be used as a C callback
static VKAPI_ATTR VkBool32 VKAPI_CALL debug_messenger_callback(
    VkDebugUtilsMessageSeverityFlagBitsEXT message_severity,
    VkDebugUtilsMessageTypeFlagsEXT message_type,
    VkDebugUtilsMessengerCallbackDataEXT const* callback_data,
    void* user_data) {
    
    DebugCallback* callback = static_cast<DebugCallback*>(user_data);
    if (callback && *callback) {
        DebugSeverity severity;
        if (message_severity & VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT) {
            severity = DebugSeverity::Error;
        } else if (message_severity & VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT) {
            severity = DebugSeverity::Warning;
        } else if (message_severity & VK_DEBUG_UTILS_MESSAGE_SEVERITY_INFO_BIT_EXT) {
            severity = DebugSeverity::Info;
        } else {
            severity = DebugSeverity::Verbose;
        }
        (*callback)(severity, callback_data->pMessage);
    }
    return VK_FALSE;
}

static auto is_layer_available(char const* layer_name) -> bool {
    uint32_t layer_count = 0;
    vkEnumerateInstanceLayerProperties(&layer_count, nullptr);
    
    std::vector<VkLayerProperties> available_layers(layer_count);
    vkEnumerateInstanceLayerProperties(&layer_count, available_layers.data());
    
    for (VkLayerProperties const& layer : available_layers) {
        if (strcmp(layer.layerName, layer_name) == 0) {
            return true;
        }
    }
    return false;
}

auto VulkanContext::_create_instance() -> void {
    VkApplicationInfo app_info = {};
    app_info.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app_info.pApplicationName = "CUDA-Vulkan Interop";
    app_info.applicationVersion = VK_MAKE_VERSION(1, 0, 0);
    app_info.pEngineName = "No Engine";
    app_info.engineVersion = VK_MAKE_VERSION(1, 0, 0);
    app_info.apiVersion = VK_API_VERSION_1_3;
    
    std::vector<const char*> extensions;
    
    if (!_headless) {
        uint32_t glfw_extension_count = 0;
        const char** glfw_extensions = glfwGetRequiredInstanceExtensions(&glfw_extension_count);
        extensions.assign(glfw_extensions, glfw_extensions + glfw_extension_count);
    }
    
    // Required to query/enable CUDA interop support on candidate devices.
    extensions.push_back(VK_KHR_EXTERNAL_MEMORY_CAPABILITIES_EXTENSION_NAME);
    extensions.push_back(VK_KHR_EXTERNAL_SEMAPHORE_CAPABILITIES_EXTENSION_NAME);
    extensions.push_back(VK_KHR_GET_PHYSICAL_DEVICE_PROPERTIES_2_EXTENSION_NAME);
    
    // Check if validation layer is available
    bool validation_layer_available = is_layer_available("VK_LAYER_KHRONOS_validation");
    bool enable_validation = _debug_callback && validation_layer_available;
    
    if (_debug_callback && !validation_layer_available) {
        fprintf(stderr, "Warning: VK_LAYER_KHRONOS_validation not available, validation disabled\n");
    }
    
    // Add debug extension if validation is enabled
    if (enable_validation) {
        extensions.push_back(VK_EXT_DEBUG_UTILS_EXTENSION_NAME);
    }
    
    // Enable validation layer if available
    std::vector<char const*> layers;
    if (enable_validation) {
        layers.push_back("VK_LAYER_KHRONOS_validation");
    }
    
    // Enable synchronization validation feature
    VkValidationFeatureEnableEXT enabled_features[] = {
        VK_VALIDATION_FEATURE_ENABLE_SYNCHRONIZATION_VALIDATION_EXT
    };
    VkValidationFeaturesEXT validation_features = {};
    validation_features.sType = VK_STRUCTURE_TYPE_VALIDATION_FEATURES_EXT;
    validation_features.enabledValidationFeatureCount = enable_validation ? 1 : 0;
    validation_features.pEnabledValidationFeatures = enabled_features;
    
    VkInstanceCreateInfo create_info = {};
    create_info.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    create_info.pNext = enable_validation ? &validation_features : nullptr;
    create_info.pApplicationInfo = &app_info;
    create_info.enabledExtensionCount = static_cast<uint32_t>(extensions.size());
    create_info.ppEnabledExtensionNames = extensions.data();
    create_info.enabledLayerCount = static_cast<uint32_t>(layers.size());
    create_info.ppEnabledLayerNames = layers.data();
    
    VK_CHECK(vkCreateInstance(&create_info, nullptr, &_instance));
    
    // Store whether validation is actually enabled (for debug messenger creation)
    _validation_enabled = enable_validation;
}

// [snippet:select-vulkan-device-by-cuda-uuid]
auto VulkanContext::_select_physical_device(const CUuuid& cuda_uuid, uint32_t requested_sampler_capacity) -> void {
    uint32_t device_count = 0;
    vkEnumeratePhysicalDevices(_instance, &device_count, nullptr);
    
    if (device_count == 0) {
        throw std::runtime_error("No Vulkan devices found");
    }
    
    std::vector<VkPhysicalDevice> devices(device_count);
    vkEnumeratePhysicalDevices(_instance, &device_count, devices.data());
    
    for (const auto& device : devices) {
        VkPhysicalDeviceIDProperties id_props = {};
        id_props.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_ID_PROPERTIES;
        
        VkPhysicalDeviceProperties2 props2 = {};
        props2.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2;
        props2.pNext = &id_props;
        
        vkGetPhysicalDeviceProperties2KHR(device, &props2);
        
        printf("Vulkan device: %s\n", props2.properties.deviceName);
        
        if (uuid_matches(id_props.deviceUUID, reinterpret_cast<const uint8_t*>(cuda_uuid.bytes))) {
            printf("  -> Matches CUDA device UUID!\n");
            _physical_device = device;
            _timestamp_period = props2.properties.limits.timestampPeriod;
            
            // Query descriptor indexing limits
            const auto& limits = props2.properties.limits;
            uint32_t max_per_stage = limits.maxPerStageDescriptorSampledImages;
            uint32_t max_set_samplers = limits.maxDescriptorSetSamplers;
            uint32_t max_set_sampled_images = limits.maxDescriptorSetSampledImages;
            
            // Take minimum of requested capacity and all hardware limits
            _max_sampled_image_limit = std::min({max_per_stage, max_set_samplers, max_set_sampled_images});
            _max_sampled_image_descriptors = std::min(requested_sampler_capacity, _max_sampled_image_limit);
            
            printf("  Sampled image descriptor capacity: %u (limit: %u)\n", 
                   _max_sampled_image_descriptors, _max_sampled_image_limit);
            return;
        }
    }
    
    throw std::runtime_error("No Vulkan device matches CUDA device UUID");
}
// [/snippet:select-vulkan-device-by-cuda-uuid]

auto VulkanContext::_find_queue_family() -> void {
    uint32_t queue_family_count = 0;
    vkGetPhysicalDeviceQueueFamilyProperties(_physical_device, &queue_family_count, nullptr);
    
    std::vector<VkQueueFamilyProperties> queue_families(queue_family_count);
    vkGetPhysicalDeviceQueueFamilyProperties(_physical_device, &queue_family_count, queue_families.data());
    
    for (uint32_t i = 0; i < queue_family_count; i++) {
        if (queue_families[i].queueFlags & VK_QUEUE_GRAPHICS_BIT) {
            // In headless mode, we don't need present support
            if (_headless) {
                _graphics_queue_family = i;
                return;
            }
            
            // In windowed mode, check for present support
            VkBool32 present_support = false;
            vkGetPhysicalDeviceSurfaceSupportKHR(_physical_device, i, _surface, &present_support);
            
            if (present_support) {
                _graphics_queue_family = i;
                return;
            }
        }
    }
    
    throw std::runtime_error("No suitable queue family found");
}

auto VulkanContext::_create_device() -> void {
    float queue_priority = 1.0f;
    VkDeviceQueueCreateInfo queue_create_info = {};
    queue_create_info.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
    queue_create_info.queueFamilyIndex = _graphics_queue_family;
    queue_create_info.queueCount = 1;
    queue_create_info.pQueuePriorities = &queue_priority;
    
    // External memory + semaphore extensions are the core Vulkan<->CUDA bridge.
    std::vector<const char*> extensions = {
        VK_KHR_EXTERNAL_MEMORY_EXTENSION_NAME,
#ifdef _WIN32
        VK_KHR_EXTERNAL_MEMORY_WIN32_EXTENSION_NAME,
#else
        VK_KHR_EXTERNAL_MEMORY_FD_EXTENSION_NAME,
#endif
        VK_KHR_EXTERNAL_SEMAPHORE_EXTENSION_NAME,
#ifdef _WIN32
        VK_KHR_EXTERNAL_SEMAPHORE_WIN32_EXTENSION_NAME,
#else
        VK_KHR_EXTERNAL_SEMAPHORE_FD_EXTENSION_NAME,
#endif
        VK_EXT_SHADER_OBJECT_EXTENSION_NAME,
        VK_EXT_DESCRIPTOR_INDEXING_EXTENSION_NAME,
    };
    
    if (!_headless) {
        extensions.push_back(VK_KHR_SWAPCHAIN_EXTENSION_NAME);
    }
    
    // Enable descriptor indexing features
    VkPhysicalDeviceDescriptorIndexingFeatures descriptor_indexing_features = {};
    descriptor_indexing_features.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DESCRIPTOR_INDEXING_FEATURES;
    descriptor_indexing_features.descriptorBindingPartiallyBound = VK_TRUE;
    descriptor_indexing_features.descriptorBindingSampledImageUpdateAfterBind = VK_TRUE;
    descriptor_indexing_features.descriptorBindingVariableDescriptorCount = VK_TRUE;
    descriptor_indexing_features.runtimeDescriptorArray = VK_TRUE;
    descriptor_indexing_features.shaderSampledImageArrayNonUniformIndexing = VK_TRUE;
    
    VkPhysicalDeviceShaderObjectFeaturesEXT shader_object_features = {};
    shader_object_features.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_SHADER_OBJECT_FEATURES_EXT;
    shader_object_features.pNext = &descriptor_indexing_features;
    shader_object_features.shaderObject = VK_TRUE;
    
    VkPhysicalDeviceDynamicRenderingFeatures dynamic_rendering_features = {};
    dynamic_rendering_features.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DYNAMIC_RENDERING_FEATURES;
    dynamic_rendering_features.pNext = &shader_object_features;
    dynamic_rendering_features.dynamicRendering = VK_TRUE;
    
    // synchronization2 is used for explicit image ownership/layout transitions
    // between graphics and external (CUDA) queue families.
    VkPhysicalDeviceSynchronization2Features sync2_features = {};
    sync2_features.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_SYNCHRONIZATION_2_FEATURES;
    sync2_features.pNext = &dynamic_rendering_features;
    sync2_features.synchronization2 = VK_TRUE;
    
    // Enable timeline semaphores for CUDA-Vulkan async sync
    VkPhysicalDeviceTimelineSemaphoreFeatures timeline_features = {};
    timeline_features.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_TIMELINE_SEMAPHORE_FEATURES;
    timeline_features.pNext = &sync2_features;
    timeline_features.timelineSemaphore = VK_TRUE;
    
    // Enable shaderDrawParameters for SV_VertexID in shaders
    VkPhysicalDeviceVulkan11Features vulkan11_features = {};
    vulkan11_features.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_1_FEATURES;
    vulkan11_features.pNext = &timeline_features;
    vulkan11_features.shaderDrawParameters = VK_TRUE;
    
    VkPhysicalDeviceFeatures2 features2 = {};
    features2.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2;
    features2.pNext = &vulkan11_features;
    
    VkDeviceCreateInfo create_info = {};
    create_info.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
    create_info.pNext = &features2;
    create_info.queueCreateInfoCount = 1;
    create_info.pQueueCreateInfos = &queue_create_info;
    create_info.enabledExtensionCount = static_cast<uint32_t>(extensions.size());
    create_info.ppEnabledExtensionNames = extensions.data();
    
    VK_CHECK(vkCreateDevice(_physical_device, &create_info, nullptr, &_device));
    
    vkGetDeviceQueue(_device, _graphics_queue_family, 0, &_graphics_queue);
}

auto VulkanContext::_create_swapchain(int width, int height) -> void {
    VkSurfaceCapabilitiesKHR capabilities;
    vkGetPhysicalDeviceSurfaceCapabilitiesKHR(_physical_device, _surface, &capabilities);
    
    uint32_t format_count;
    vkGetPhysicalDeviceSurfaceFormatsKHR(_physical_device, _surface, &format_count, nullptr);
    std::vector<VkSurfaceFormatKHR> formats(format_count);
    vkGetPhysicalDeviceSurfaceFormatsKHR(_physical_device, _surface, &format_count, formats.data());
    
    VkSurfaceFormatKHR surface_format = formats[0];
    for (const auto& format : formats) {
        if (format.format == VK_FORMAT_B8G8R8A8_SRGB && format.colorSpace == VK_COLOR_SPACE_SRGB_NONLINEAR_KHR) {
            surface_format = format;
            break;
        }
    }
    _swapchain_format = surface_format.format;
    
    if (capabilities.currentExtent.width != UINT32_MAX) {
        _swapchain_extent = capabilities.currentExtent;
    } else {
        _swapchain_extent = {static_cast<uint32_t>(width), static_cast<uint32_t>(height)};
    }
    
    uint32_t image_count = capabilities.minImageCount + 1;
    if (capabilities.maxImageCount > 0 && image_count > capabilities.maxImageCount) {
        image_count = capabilities.maxImageCount;
    }
    
    VkSwapchainCreateInfoKHR create_info = {};
    create_info.sType = VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR;
    create_info.surface = _surface;
    create_info.minImageCount = image_count;
    create_info.imageFormat = surface_format.format;
    create_info.imageColorSpace = surface_format.colorSpace;
    create_info.imageExtent = _swapchain_extent;
    create_info.imageArrayLayers = 1;
    create_info.imageUsage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT;
    create_info.imageSharingMode = VK_SHARING_MODE_EXCLUSIVE;
    create_info.preTransform = capabilities.currentTransform;
    create_info.compositeAlpha = VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR;
    create_info.presentMode = VK_PRESENT_MODE_FIFO_KHR;
    create_info.clipped = VK_TRUE;
    
    VK_CHECK(vkCreateSwapchainKHR(_device, &create_info, nullptr, &_swapchain));
    
    vkGetSwapchainImagesKHR(_device, _swapchain, &image_count, nullptr);
    _swapchain_images.resize(image_count);
    vkGetSwapchainImagesKHR(_device, _swapchain, &image_count, _swapchain_images.data());
    
    _swapchain_image_views.resize(image_count);
    for (size_t i = 0; i < image_count; i++) {
        VkImageViewCreateInfo view_info = {};
        view_info.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
        view_info.image = _swapchain_images[i];
        view_info.viewType = VK_IMAGE_VIEW_TYPE_2D;
        view_info.format = _swapchain_format;
        view_info.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        view_info.subresourceRange.baseMipLevel = 0;
        view_info.subresourceRange.levelCount = 1;
        view_info.subresourceRange.baseArrayLayer = 0;
        view_info.subresourceRange.layerCount = 1;
        
        VK_CHECK(vkCreateImageView(_device, &view_info, nullptr, &_swapchain_image_views[i]));
    }
}

auto VulkanContext::_create_timeline_semaphore() -> void {
    // Create timeline semaphore type info
    VkSemaphoreTypeCreateInfo timeline_info = {};
    timeline_info.sType = VK_STRUCTURE_TYPE_SEMAPHORE_TYPE_CREATE_INFO;
    timeline_info.semaphoreType = VK_SEMAPHORE_TYPE_TIMELINE;
    timeline_info.initialValue = 0;
    
    // Export info for CUDA interop. A timeline semaphore lets CUDA signal N and
    // Vulkan wait for N per frame without binary semaphore churn.
    // Windows: Opaque Win32 handle for timeline semaphore interop with CUDA
    // Linux: Opaque FD works for timeline semaphores
    VkExportSemaphoreCreateInfo export_info = {};
    export_info.sType = VK_STRUCTURE_TYPE_EXPORT_SEMAPHORE_CREATE_INFO;
    export_info.pNext = &timeline_info;
#ifdef _WIN32
    export_info.handleTypes = VK_EXTERNAL_SEMAPHORE_HANDLE_TYPE_OPAQUE_WIN32_BIT;
#else
    export_info.handleTypes = VK_EXTERNAL_SEMAPHORE_HANDLE_TYPE_OPAQUE_FD_BIT;
#endif
    
    VkSemaphoreCreateInfo semaphore_info = {};
    semaphore_info.sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO;
    semaphore_info.pNext = &export_info;
    
    VK_CHECK(vkCreateSemaphore(_device, &semaphore_info, nullptr, &_cuda_timeline_semaphore));
}

auto VulkanContext::_create_descriptor_set_layout() -> void {
    // Binding for texture array with descriptor indexing
    VkDescriptorSetLayoutBinding sampler_binding = {};
    sampler_binding.binding = 0;
    sampler_binding.descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
    sampler_binding.descriptorCount = _max_sampled_image_descriptors;
    sampler_binding.stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT;
    
    // Enable descriptor indexing flags for this binding
    VkDescriptorBindingFlags binding_flags = 
        VK_DESCRIPTOR_BINDING_PARTIALLY_BOUND_BIT |
        VK_DESCRIPTOR_BINDING_UPDATE_AFTER_BIND_BIT |
        VK_DESCRIPTOR_BINDING_VARIABLE_DESCRIPTOR_COUNT_BIT;
    
    VkDescriptorSetLayoutBindingFlagsCreateInfo binding_flags_info = {};
    binding_flags_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_BINDING_FLAGS_CREATE_INFO;
    binding_flags_info.bindingCount = 1;
    binding_flags_info.pBindingFlags = &binding_flags;
    
    VkDescriptorSetLayoutCreateInfo layout_info = {};
    layout_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
    layout_info.pNext = &binding_flags_info;
    layout_info.flags = VK_DESCRIPTOR_SET_LAYOUT_CREATE_UPDATE_AFTER_BIND_POOL_BIT;
    layout_info.bindingCount = 1;
    layout_info.pBindings = &sampler_binding;
    
    VK_CHECK(vkCreateDescriptorSetLayout(_device, &layout_info, nullptr, &_descriptor_set_layout));
    
    // Push constants are shared by the fullscreen pass (texture index) and the
    // marquee overlay pass (rectangle + viewport size).
    VkPushConstantRange push_constant_range = {};
    push_constant_range.stageFlags =
        VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT;
    push_constant_range.offset = 0;
    push_constant_range.size = sizeof(float) * 8;
    
    // Create pipeline layout with push constants
    VkPipelineLayoutCreateInfo pipeline_layout_info = {};
    pipeline_layout_info.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
    pipeline_layout_info.setLayoutCount = 1;
    pipeline_layout_info.pSetLayouts = &_descriptor_set_layout;
    pipeline_layout_info.pushConstantRangeCount = 1;
    pipeline_layout_info.pPushConstantRanges = &push_constant_range;
    
    VK_CHECK(vkCreatePipelineLayout(_device, &pipeline_layout_info, nullptr, &_pipeline_layout));
}

auto VulkanContext::_create_command_pool() -> void {
    VkCommandPoolCreateInfo pool_info = {};
    pool_info.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
    pool_info.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
    pool_info.queueFamilyIndex = _graphics_queue_family;
    
    VK_CHECK(vkCreateCommandPool(_device, &pool_info, nullptr, &_command_pool));
    
    // Allocate main command buffer
    VkCommandBufferAllocateInfo alloc_info = {};
    alloc_info.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
    alloc_info.commandPool = _command_pool;
    alloc_info.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    alloc_info.commandBufferCount = 1;
    
    VK_CHECK(vkAllocateCommandBuffers(_device, &alloc_info, &_vk_command_buffer));
    
    // Allocate immediate command buffer
    VK_CHECK(vkAllocateCommandBuffers(_device, &alloc_info, &_immediate_command_buffer));
}

auto VulkanContext::_create_descriptor_pool_and_set() -> void {
    VkDescriptorPoolSize pool_size = {};
    pool_size.type = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
    pool_size.descriptorCount = _max_sampled_image_descriptors;
    
    VkDescriptorPoolCreateInfo pool_info = {};
    pool_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;
    pool_info.flags = VK_DESCRIPTOR_POOL_CREATE_UPDATE_AFTER_BIND_BIT;
    pool_info.poolSizeCount = 1;
    pool_info.pPoolSizes = &pool_size;
    pool_info.maxSets = 1;
    
    VK_CHECK(vkCreateDescriptorPool(_device, &pool_info, nullptr, &_descriptor_pool));
    
    // Allocate with variable descriptor count
    uint32_t variable_count = _max_sampled_image_descriptors;
    VkDescriptorSetVariableDescriptorCountAllocateInfo variable_info = {};
    variable_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_VARIABLE_DESCRIPTOR_COUNT_ALLOCATE_INFO;
    variable_info.descriptorSetCount = 1;
    variable_info.pDescriptorCounts = &variable_count;
    
    VkDescriptorSetAllocateInfo alloc_info = {};
    alloc_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
    alloc_info.pNext = &variable_info;
    alloc_info.descriptorPool = _descriptor_pool;
    alloc_info.descriptorSetCount = 1;
    alloc_info.pSetLayouts = &_descriptor_set_layout;
    
    VK_CHECK(vkAllocateDescriptorSets(_device, &alloc_info, &_descriptor_set));
    
    // Note: descriptors are written by create_sampled_image when images are created
}

auto VulkanContext::_create_sync_objects() -> void {
    VkSemaphoreCreateInfo semaphore_info = {};
    semaphore_info.sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO;
    
    VkFenceCreateInfo fence_info = {};
    fence_info.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
    fence_info.flags = VK_FENCE_CREATE_SIGNALED_BIT;
    
    // Swapchain semaphores only needed in windowed mode
    if (!_headless) {
        VK_CHECK(vkCreateSemaphore(_device, &semaphore_info, nullptr, &_image_available_semaphore));
        
        // Create per-image render_finished semaphores
        _render_finished_semaphores.resize(_swapchain_images.size());
        for (size_t i = 0; i < _swapchain_images.size(); ++i) {
            VK_CHECK(vkCreateSemaphore(_device, &semaphore_info, nullptr, &_render_finished_semaphores[i]));
        }
    }
    
    VK_CHECK(vkCreateFence(_device, &fence_info, nullptr, &_in_flight_fence));
}

auto VulkanContext::_create_timestamp_query_pool() -> void {
    VkQueryPoolCreateInfo query_pool_info = {};
    query_pool_info.sType = VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO;
    query_pool_info.queryType = VK_QUERY_TYPE_TIMESTAMP;
    query_pool_info.queryCount = 2;
    
    VK_CHECK(vkCreateQueryPool(_device, &query_pool_info, nullptr, &_timestamp_query_pool));
}

auto VulkanContext::reset() -> void {
    vkDeviceWaitIdle(_device);
    
    // Destroy all sampled images (including shared image)
    for (auto& [id, img] : _sampled_images) {
        vkDestroySampler(_device, img.sampler, nullptr);
        vkDestroyImageView(_device, img.view, nullptr);
        vkDestroyImage(_device, img.image, nullptr);
        vkFreeMemory(_device, img.memory, nullptr);
    }
    _sampled_images.clear();
    _next_sampled_image_id = 1;
    _next_descriptor_index = 0;
    _free_descriptor_indices.clear();
    
    // Destroy all user-created shaders
    for (auto& [id, shdr] : _shaders) {
        vkDestroyShaderEXT(_device, shdr.shader, nullptr);
    }
    _shaders.clear();
    _next_shader_id = 1;
    
    // Reset descriptor pool capacity to initial value
    _max_sampled_image_descriptors = std::min(_initial_sampled_image_capacity, _max_sampled_image_limit);
    
    // Destroy and recreate descriptor pool
    vkDestroyDescriptorPool(_device, _descriptor_pool, nullptr);
    
    VkDescriptorPoolSize pool_size = {};
    pool_size.type = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
    pool_size.descriptorCount = _max_sampled_image_descriptors;
    
    VkDescriptorPoolCreateInfo pool_info = {};
    pool_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;
    pool_info.flags = VK_DESCRIPTOR_POOL_CREATE_UPDATE_AFTER_BIND_BIT;
    pool_info.poolSizeCount = 1;
    pool_info.pPoolSizes = &pool_size;
    pool_info.maxSets = 1;
    
    VK_CHECK(vkCreateDescriptorPool(_device, &pool_info, nullptr, &_descriptor_pool));
    
    // Reallocate descriptor set
    uint32_t variable_count = _max_sampled_image_descriptors;
    VkDescriptorSetVariableDescriptorCountAllocateInfo variable_info = {};
    variable_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_VARIABLE_DESCRIPTOR_COUNT_ALLOCATE_INFO;
    variable_info.descriptorSetCount = 1;
    variable_info.pDescriptorCounts = &variable_count;
    
    VkDescriptorSetAllocateInfo alloc_info = {};
    alloc_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
    alloc_info.pNext = &variable_info;
    alloc_info.descriptorPool = _descriptor_pool;
    alloc_info.descriptorSetCount = 1;
    alloc_info.pSetLayouts = &_descriptor_set_layout;
    
    VK_CHECK(vkAllocateDescriptorSets(_device, &alloc_info, &_descriptor_set));
    
    // Reset fence to signaled state
    VkFenceCreateInfo fence_info = {};
    fence_info.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
    fence_info.flags = VK_FENCE_CREATE_SIGNALED_BIT;
    // Can't reset a fence to signaled, so destroy and recreate
    vkDestroyFence(_device, _in_flight_fence, nullptr);
    VK_CHECK(vkCreateFence(_device, &fence_info, nullptr, &_in_flight_fence));
}

auto VulkanContext::swapchain_image_view(uint32_t index) const -> VkImageView {
    if (_headless) {
        throw std::runtime_error("swapchain_image_view() not available in headless mode");
    }
    if (index >= _swapchain_image_views.size()) {
        throw std::runtime_error("Swapchain image view index out of range");
    }
    return _swapchain_image_views[index];
}

auto VulkanContext::swapchain_image(uint32_t index) const -> VkImage {
    if (_headless) {
        throw std::runtime_error("swapchain_image() not available in headless mode");
    }
    if (index >= _swapchain_images.size()) {
        throw std::runtime_error("Swapchain image index out of range");
    }
    return _swapchain_images[index];
}
