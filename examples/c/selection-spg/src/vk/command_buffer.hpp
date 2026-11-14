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

#include <volk.h>

// Wrapper around VkCommandBuffer providing command recording methods
class CommandBuffer {
public:
    explicit CommandBuffer(VkCommandBuffer cmd) : _cmd(cmd) {}

    // Get the underlying Vulkan handle
    VkCommandBuffer handle() const { return _cmd; }

    // Reset the command buffer for reuse
    void reset();

    // Begin recording commands
    void begin();

    // End recording commands
    void end();

    // Dynamic rendering
    void begin_rendering(VkRenderingInfo const& rendering_info);
    void end_rendering();

    // Query pool operations
    void reset_query_pool(VkQueryPool query_pool, uint32_t first_query, uint32_t query_count);
    void write_timestamp(VkPipelineStageFlagBits stage, VkQueryPool query_pool, uint32_t query);

    // Synchronization (Vulkan 1.3)
    void image_memory_barrier(VkImage image, VkImageAspectFlags aspect_mask,
                              VkImageLayout old_layout, VkPipelineStageFlags2 src_stage, VkAccessFlags2 src_access,
                              VkImageLayout new_layout, VkPipelineStageFlags2 dst_stage, VkAccessFlags2 dst_access,
                              uint32_t src_queue_family = VK_QUEUE_FAMILY_IGNORED,
                              uint32_t dst_queue_family = VK_QUEUE_FAMILY_IGNORED);

    // Dynamic state - viewport/scissor
    void set_viewport(float x, float y, float width, float height, float min_depth = 0.0f, float max_depth = 1.0f);
    void set_scissor(int32_t x, int32_t y, uint32_t width, uint32_t height);

    // Dynamic state - rasterization
    void set_rasterizer_discard_enable(bool enable);
    void set_polygon_mode(VkPolygonMode polygon_mode);
    void set_cull_mode(VkCullModeFlags cull_mode);
    void set_front_face(VkFrontFace front_face);
    void set_depth_bias_enable(bool enable);

    // Dynamic state - primitive topology
    void set_primitive_topology(VkPrimitiveTopology topology);
    void set_primitive_restart_enable(bool enable);

    // Dynamic state - depth/stencil
    void set_depth_test_enable(bool enable);
    void set_depth_write_enable(bool enable);
    void set_depth_bounds_test_enable(bool enable);
    void set_stencil_test_enable(bool enable);

    // Dynamic state - multisample
    void set_rasterization_samples(VkSampleCountFlagBits samples);
    void set_sample_mask(VkSampleCountFlagBits samples, uint32_t mask);
    void set_alpha_to_coverage_enable(bool enable);

    // Dynamic state - color blend
    void set_color_blend_enable(uint32_t attachment, bool enable);
    void set_color_write_mask(uint32_t attachment, VkColorComponentFlags mask);

    // Dynamic state - vertex input
    void set_vertex_input_empty();

    // Descriptor sets
    void bind_descriptor_sets(VkPipelineBindPoint bind_point, VkPipelineLayout layout,
                              uint32_t first_set, uint32_t set_count, VkDescriptorSet const* sets);

    // Push constants
    void push_constants(VkPipelineLayout layout, VkShaderStageFlags stage_flags,
                        uint32_t offset, uint32_t size, void const* data);

    // Draw commands
    void draw(uint32_t vertex_count, uint32_t instance_count = 1,
              uint32_t first_vertex = 0, uint32_t first_instance = 0);

private:
    VkCommandBuffer _cmd;
};
