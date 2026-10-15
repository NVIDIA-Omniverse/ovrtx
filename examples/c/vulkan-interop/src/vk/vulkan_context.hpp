// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

// Platform-specific defines for Vulkan Win32 extensions
#ifdef _WIN32
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#define VK_USE_PLATFORM_WIN32_KHR
#endif

#include <volk.h>

#ifdef _WIN32
#include <vulkan/vulkan_win32.h>
#endif

#define GLFW_INCLUDE_VULKAN
#define GLFW_INCLUDE_NONE
#include <GLFW/glfw3.h>

#include "command_buffer.hpp"
#include "sampled_image.hpp"
#include "shader.hpp"

#include <ankerl/unordered_dense.h>
#include <glm/vec2.hpp>
#include <cuda.h>
#include <vector>
#include <cstdint>
#include <optional>
#include <functional>
#include <string_view>

// Result of acquire_next_image operation
enum class AcquireResult {
    Success,     // Image acquired successfully
    Suboptimal,  // Image acquired, but swapchain should be recreated soon
    OutOfDate,   // Swapchain needs immediate recreation (resize, etc.)
    Minimized    // Window is minimized (0x0 size)
};

// Result of submit_and_present operation
enum class PresentResult {
    Success,
    Suboptimal,
    OutOfDate
};

// Debug message severity levels
enum class DebugSeverity {
    Verbose,
    Info,
    Warning,
    Error
};

// Debug callback function type
using DebugCallback = std::function<void(DebugSeverity severity, std::string_view message)>;

// Requested swapchain presentation behavior. Only Fifo is guaranteed by the
// Vulkan spec; the others are used when the surface reports support and fall
// back to Fifo when it does not.
//
// Fifo blocks the presentation engine to the display refresh, which caps how
// fast frames can be shown. That cap hides throughput work such as DLSS Frame
// Generation, so Mailbox (tear-free, drops stale frames) and Immediate
// (uncapped, may tear) exist to measure and display the real frame rate.
enum class PresentMode {
    Fifo,
    Mailbox,
    Immediate
};

// Configuration for VulkanContext
struct VulkanContextConfig {
    GLFWwindow* window = nullptr;  // nullptr = headless mode
    uint32_t initial_sampled_image_capacity = 1024;
    DebugCallback debug_callback = nullptr;  // nullptr = no debug messenger
    PresentMode present_mode = PresentMode::Fifo;
};

// Human-readable name for a present mode, for logging and CLI parsing.
auto present_mode_name(PresentMode mode) -> std::string_view;

class VulkanContext {
public:
    // Initialize Vulkan with config and CUDA UUID for device matching
    VulkanContext(VulkanContextConfig const& config, CUuuid const& cuda_uuid);
    ~VulkanContext();
    
    // Non-copyable
    VulkanContext(const VulkanContext&) = delete;
    auto operator=(const VulkanContext&) -> VulkanContext& = delete;
    
    // Window/event handling
    auto should_close() const -> bool;
    auto poll_events() -> void;
    
    // Frame synchronization
    auto wait_for_fence() -> void;
    auto reset_fence() -> void;
    auto reset_fence_to_signaled() -> void;
    auto acquire_next_image(uint32_t& image_index) -> AcquireResult;
    
    // Window/swapchain management
    auto framebuffer_size() const -> glm::ivec2;
    auto recreate_swapchain() -> void;
    
    // Command buffer access
    auto command_buffer() -> CommandBuffer { return CommandBuffer(_vk_command_buffer); }
    
    // Render loop helpers
    auto record_frame_begin(uint32_t image_index) -> void;
    auto record_frame_end(uint32_t image_index) -> void;
    // Submit draw work and present while waiting for CUDA producer progress.
    // cuda_timeline_wait_value is the frame value signaled by CUDA after it
    // finished writing the shared image Vulkan will sample this frame.
    auto submit_and_present(uint32_t image_index, uint64_t cuda_timeline_wait_value = 0) -> PresentResult;
    
    // CUDA interop exports. Callers pass these OS handles to CUDA so both APIs
    // reference the same memory/semaphore objects.
#ifdef _WIN32
    auto export_memory_handle(SampledImageHandle handle) -> void*;
    auto export_timeline_semaphore_handle() -> void*;
#else
    auto export_memory_handle(SampledImageHandle handle) -> int;
    auto export_timeline_semaphore_handle() -> int;
#endif
    
    // Timing
    auto timestamp_period() const -> float { return _timestamp_period; }
    auto timestamp_query_pool() const -> VkQueryPool { return _timestamp_query_pool; }
    auto vulkan_elapsed_ms() -> double;
    
    
    // Sampled image management
    auto create_sampled_image(int width, int height, VkFormat format, 
                              VkFilter filter, bool exportable = false) -> SampledImageHandle;
    auto sampled_image(SampledImageHandle handle) const -> SampledImage const&;
    auto destroy_sampled_image(SampledImageHandle handle) -> void;
    auto num_sampled_images() const -> size_t { return _sampled_images.size(); }
    auto sampled_image_limit() const -> uint32_t { return _max_sampled_image_limit; }
    
    // Shader management
    auto create_linked_vertex_and_fragment_shaders(std::vector<uint32_t> const& vert_spirv, 
                                                    std::vector<uint32_t> const& frag_spirv) 
        -> std::pair<ShaderHandle, ShaderHandle>;
    auto shader(ShaderHandle handle) const -> Shader const&;
    auto destroy_shader(ShaderHandle handle) -> void;
    auto bind_shaders(std::optional<ShaderHandle> vertex,
                      std::optional<ShaderHandle> fragment,
                      std::optional<ShaderHandle> tessellation_control = std::nullopt,
                      std::optional<ShaderHandle> tessellation_evaluation = std::nullopt,
                      std::optional<ShaderHandle> geometry = std::nullopt) -> void;
    
    // Reset context to post-construction state (preserves device, clears user resources)
    auto reset() -> void;
    
    // Swapchain accessors (for render graph)
    auto swapchain_image_view(uint32_t index) const -> VkImageView;
    auto swapchain_image(uint32_t index) const -> VkImage;
    auto swapchain_extent() const -> VkExtent2D { return _swapchain_extent; }
    auto swapchain_format() const -> VkFormat { return _swapchain_format; }
    // The mode the surface actually accepted, which may differ from the
    // requested one when the surface does not support it.
    auto present_mode() const -> PresentMode { return _present_mode; }
    auto device() const -> VkDevice { return _device; }
    auto graphics_queue() const -> VkQueue { return _graphics_queue; }
    auto is_headless() const -> bool { return _headless; }
    auto queue_family() const -> uint32_t { return _graphics_queue_family; }
    auto pipeline_layout() const -> VkPipelineLayout { return _pipeline_layout; }
    auto descriptor_set() const -> VkDescriptorSet { return _descriptor_set; }
    
    // Immediate command execution (synchronous, blocks until complete)
    auto immediate_submit(std::function<void(CommandBuffer)> const& work) -> void;

private:
    // Initialization helpers
    auto _create_instance() -> void;
    auto _select_physical_device(const CUuuid& cuda_uuid, uint32_t requested_sampler_capacity) -> void;
    auto _find_queue_family() -> void;
    auto _create_device() -> void;
    auto _create_swapchain(int width, int height) -> void;
    // Resolve the requested present mode against surface support, caching the
    // result in _present_mode. Both swapchain creation paths call this so they
    // cannot disagree.
    auto _select_present_mode() -> VkPresentModeKHR;
    auto _create_timeline_semaphore() -> void;
    auto _create_descriptor_set_layout() -> void;
    auto _create_command_pool() -> void;
    auto _create_descriptor_pool_and_set() -> void;
    auto _create_sync_objects() -> void;
    auto _create_timestamp_query_pool() -> void;
    
    // Mode
    bool _headless = false;
    
    // Debug
    DebugCallback _debug_callback = nullptr;
    bool _validation_enabled = false;  // True only if callback set AND layer available
    VkDebugUtilsMessengerEXT _debug_messenger = VK_NULL_HANDLE;
    
    // Vulkan core objects
    GLFWwindow* _window = nullptr;
    VkInstance _instance = VK_NULL_HANDLE;
    VkPhysicalDevice _physical_device = VK_NULL_HANDLE;
    VkDevice _device = VK_NULL_HANDLE;
    VkQueue _graphics_queue = VK_NULL_HANDLE;
    uint32_t _graphics_queue_family = 0;
    VkSurfaceKHR _surface = VK_NULL_HANDLE;
    
    // Swapchain
    VkSwapchainKHR _swapchain = VK_NULL_HANDLE;
    std::vector<VkImage> _swapchain_images;
    std::vector<VkImageView> _swapchain_image_views;
    VkFormat _swapchain_format = VK_FORMAT_UNDEFINED;
    VkExtent2D _swapchain_extent = {};
    PresentMode _requested_present_mode = PresentMode::Fifo;
    PresentMode _present_mode = PresentMode::Fifo;
    
    // Shader objects
    ankerl::unordered_dense::map<uint64_t, Shader> _shaders;
    uint64_t _next_shader_id = 1;
    VkPipelineLayout _pipeline_layout = VK_NULL_HANDLE;
    VkDescriptorSetLayout _descriptor_set_layout = VK_NULL_HANDLE;
    VkDescriptorPool _descriptor_pool = VK_NULL_HANDLE;
    VkDescriptorSet _descriptor_set = VK_NULL_HANDLE;
    
    // Command buffers
    VkCommandPool _command_pool = VK_NULL_HANDLE;
    VkCommandBuffer _vk_command_buffer = VK_NULL_HANDLE;
    VkCommandBuffer _immediate_command_buffer = VK_NULL_HANDLE;
    
    // Synchronization
    // Single acquire semaphore (signaled by acquire, immediately consumed by submit)
    VkSemaphore _image_available_semaphore = VK_NULL_HANDLE;
    // Per-image render finished semaphores (signaled by submit, waited on by present)
    std::vector<VkSemaphore> _render_finished_semaphores;
    VkFence _in_flight_fence = VK_NULL_HANDLE;
    uint32_t _current_image_index = 0;  // Track last acquired image for submit/present
    // Timeline semaphore for CUDA-Vulkan synchronization
    VkSemaphore _cuda_timeline_semaphore = VK_NULL_HANDLE;
    
    // Timing
    VkQueryPool _timestamp_query_pool = VK_NULL_HANDLE;
    float _timestamp_period = 0.0f;
    
    // Sampled image storage
    ankerl::unordered_dense::map<uint64_t, SampledImage> _sampled_images;
    uint64_t _next_sampled_image_id = 1;
    uint32_t _max_sampled_image_descriptors = 0;  // Current descriptor array capacity
    uint32_t _max_sampled_image_limit = 0;        // Hardware limit
    uint32_t _initial_sampled_image_capacity = 0; // Initial capacity for reset()
    
    // Descriptor index management for bindless texturing
    uint32_t _next_descriptor_index = 0;           // Next index to allocate
    std::vector<uint32_t> _free_descriptor_indices; // Recycled indices from destroyed images
    
    // Helper to grow descriptor pool when needed
    auto _grow_descriptor_pool_if_needed() -> void;
};
