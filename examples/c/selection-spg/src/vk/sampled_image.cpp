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
#include <stdexcept>

#define VK_CHECK(call)                                                           \
    do {                                                                         \
        VkResult result = call;                                                  \
        if (result != VK_SUCCESS) {                                              \
            fprintf(stderr, "Vulkan error at %s:%d: %d\n", __FILE__, __LINE__,   \
                    result);                                                     \
            throw std::runtime_error("Vulkan error");                            \
        }                                                                        \
    } while (0)

SampledImageHandle VulkanContext::create_sampled_image(int width, int height, VkFormat format,
                                         VkFilter filter, bool exportable) {
    // Check if we need to grow the descriptor pool before adding a new image
    _grow_descriptor_pool_if_needed();

    SampledImage img;
    img.width = width;
    img.height = height;

    // Create image
    VkExternalMemoryImageCreateInfo ext_mem_info = {};
    ext_mem_info.sType = VK_STRUCTURE_TYPE_EXTERNAL_MEMORY_IMAGE_CREATE_INFO;
#ifdef _WIN32
    ext_mem_info.handleTypes = VK_EXTERNAL_MEMORY_HANDLE_TYPE_OPAQUE_WIN32_BIT;
#else
    ext_mem_info.handleTypes = VK_EXTERNAL_MEMORY_HANDLE_TYPE_OPAQUE_FD_BIT;
#endif

    VkImageCreateInfo image_info = {};
    image_info.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
    image_info.pNext = exportable ? &ext_mem_info : nullptr;
    image_info.imageType = VK_IMAGE_TYPE_2D;
    image_info.format = format;
    image_info.extent = {static_cast<uint32_t>(width), static_cast<uint32_t>(height), 1};
    image_info.mipLevels = 1;
    image_info.arrayLayers = 1;
    image_info.samples = VK_SAMPLE_COUNT_1_BIT;
    image_info.tiling = VK_IMAGE_TILING_OPTIMAL;
    image_info.usage = VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_STORAGE_BIT | VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT;
    image_info.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    image_info.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;

    VK_CHECK(vkCreateImage(_device, &image_info, nullptr, &img.image));

    // Get memory requirements
    VkMemoryRequirements mem_requirements;
    vkGetImageMemoryRequirements(_device, img.image, &mem_requirements);

    // Find suitable memory type
    VkPhysicalDeviceMemoryProperties mem_properties;
    vkGetPhysicalDeviceMemoryProperties(_physical_device, &mem_properties);

    uint32_t memory_type_index = UINT32_MAX;
    for (uint32_t i = 0; i < mem_properties.memoryTypeCount; i++) {
        if ((mem_requirements.memoryTypeBits & (1 << i)) &&
            (mem_properties.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT)) {
            memory_type_index = i;
            break;
        }
    }

    if (memory_type_index == UINT32_MAX) {
        vkDestroyImage(_device, img.image, nullptr);
        throw std::runtime_error("Failed to find suitable memory type");
    }

    // Allocate memory
    VkExportMemoryAllocateInfo export_info = {};
    export_info.sType = VK_STRUCTURE_TYPE_EXPORT_MEMORY_ALLOCATE_INFO;
#ifdef _WIN32
    export_info.handleTypes = VK_EXTERNAL_MEMORY_HANDLE_TYPE_OPAQUE_WIN32_BIT;
#else
    export_info.handleTypes = VK_EXTERNAL_MEMORY_HANDLE_TYPE_OPAQUE_FD_BIT;
#endif

    VkMemoryAllocateInfo alloc_info = {};
    alloc_info.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    alloc_info.pNext = exportable ? &export_info : nullptr;
    alloc_info.allocationSize = mem_requirements.size;
    alloc_info.memoryTypeIndex = memory_type_index;

    img.size = mem_requirements.size;

    VK_CHECK(vkAllocateMemory(_device, &alloc_info, nullptr, &img.memory));
    VK_CHECK(vkBindImageMemory(_device, img.image, img.memory, 0));

    // Create image view
    VkImageViewCreateInfo view_info = {};
    view_info.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
    view_info.image = img.image;
    view_info.viewType = VK_IMAGE_VIEW_TYPE_2D;
    view_info.format = format;
    view_info.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    view_info.subresourceRange.baseMipLevel = 0;
    view_info.subresourceRange.levelCount = 1;
    view_info.subresourceRange.baseArrayLayer = 0;
    view_info.subresourceRange.layerCount = 1;

    VK_CHECK(vkCreateImageView(_device, &view_info, nullptr, &img.view));

    // Create sampler
    VkSamplerCreateInfo sampler_info = {};
    sampler_info.sType = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO;
    sampler_info.magFilter = filter;
    sampler_info.minFilter = filter;
    sampler_info.addressModeU = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    sampler_info.addressModeV = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    sampler_info.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    sampler_info.borderColor = VK_BORDER_COLOR_INT_OPAQUE_BLACK;
    sampler_info.unnormalizedCoordinates = VK_FALSE;

    VK_CHECK(vkCreateSampler(_device, &sampler_info, nullptr, &img.sampler));

    // Allocate descriptor index (reuse from free list or allocate new)
    if (!_free_descriptor_indices.empty()) {
        img.descriptor_index = _free_descriptor_indices.back();
        _free_descriptor_indices.pop_back();
    } else {
        img.descriptor_index = _next_descriptor_index++;
    }

    // Write descriptor to the descriptor set
    VkDescriptorImageInfo descriptor_image_info = {};
    descriptor_image_info.imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
    descriptor_image_info.imageView = img.view;
    descriptor_image_info.sampler = img.sampler;

    VkWriteDescriptorSet descriptor_write = {};
    descriptor_write.sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
    descriptor_write.dstSet = _descriptor_set;
    descriptor_write.dstBinding = 0;
    descriptor_write.dstArrayElement = img.descriptor_index;
    descriptor_write.descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
    descriptor_write.descriptorCount = 1;
    descriptor_write.pImageInfo = &descriptor_image_info;

    vkUpdateDescriptorSets(_device, 1, &descriptor_write, 0, nullptr);

    // Store and return handle
    SampledImageHandle handle{_next_sampled_image_id++};
    _sampled_images[handle.id] = img;

    return handle;
}

const SampledImage& VulkanContext::sampled_image(SampledImageHandle handle) const {
    auto it = _sampled_images.find(handle.id);
    if (it == _sampled_images.end()) {
        throw std::runtime_error("Invalid SampledImageHandle");
    }
    return it->second;
}

void VulkanContext::destroy_sampled_image(SampledImageHandle handle) {
    auto it = _sampled_images.find(handle.id);
    if (it == _sampled_images.end()) {
        return;
    }

    SampledImage& img = it->second;

    // Return descriptor index to free list for reuse
    _free_descriptor_indices.push_back(img.descriptor_index);

    vkDestroySampler(_device, img.sampler, nullptr);
    vkDestroyImageView(_device, img.view, nullptr);
    vkDestroyImage(_device, img.image, nullptr);
    vkFreeMemory(_device, img.memory, nullptr);

    _sampled_images.erase(it);
}

void VulkanContext::_grow_descriptor_pool_if_needed() {
    // Check if we need to grow (when map size reaches current capacity)
    if (_sampled_images.size() < _max_sampled_image_descriptors) {
        return;
    }

    // Calculate new capacity (double, or max limit if smaller)
    uint32_t new_capacity = std::min(_max_sampled_image_descriptors * 2, _max_sampled_image_limit);

    // If already at max, we can't grow
    if (new_capacity <= _max_sampled_image_descriptors) {
        throw std::runtime_error("Cannot grow descriptor pool: already at hardware limit");
    }

    printf("Growing descriptor pool: %u -> %u\n", _max_sampled_image_descriptors, new_capacity);

    // Wait for device to be idle before destroying old resources
    vkDeviceWaitIdle(_device);

    // Destroy old descriptor set layout, pool, pipeline layout, and set
    // Note: descriptor set is implicitly freed when pool is destroyed
    vkDestroyDescriptorPool(_device, _descriptor_pool, nullptr);
    vkDestroyDescriptorSetLayout(_device, _descriptor_set_layout, nullptr);
    vkDestroyPipelineLayout(_device, _pipeline_layout, nullptr);
    _pipeline_layout = VK_NULL_HANDLE;

    // Update capacity
    _max_sampled_image_descriptors = new_capacity;

    // Recreate layout and pool with new capacity (also recreates pipeline layout)
    _create_descriptor_set_layout();

    // Recreate pool
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

    // Allocate new descriptor set
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

    // Re-bind all existing sampled images to the new descriptor set using their stored indices
    std::vector<VkDescriptorImageInfo> image_infos;
    std::vector<VkWriteDescriptorSet> writes;

    image_infos.reserve(_sampled_images.size());
    writes.reserve(_sampled_images.size());

    for (std::pair<uint64_t, SampledImage> const& entry : _sampled_images) {
        SampledImage const& img = entry.second;
        VkDescriptorImageInfo info = {};
        info.imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
        info.imageView = img.view;
        info.sampler = img.sampler;
        image_infos.push_back(info);

        VkWriteDescriptorSet write = {};
        write.sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
        write.dstSet = _descriptor_set;
        write.dstBinding = 0;
        write.dstArrayElement = img.descriptor_index;  // Use stored index
        write.descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
        write.descriptorCount = 1;
        write.pImageInfo = &image_infos.back();
        writes.push_back(write);
    }

    if (!writes.empty()) {
        vkUpdateDescriptorSets(_device, static_cast<uint32_t>(writes.size()),
                               writes.data(), 0, nullptr);
    }
}
