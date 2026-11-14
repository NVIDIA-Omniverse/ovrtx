// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "command_buffer.hpp"

void CommandBuffer::reset() {
    vkResetCommandBuffer(_cmd, 0);
}

void CommandBuffer::begin() {
    vkResetCommandBuffer(_cmd, 0);

    VkCommandBufferBeginInfo begin_info = {};
    begin_info.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
    vkBeginCommandBuffer(_cmd, &begin_info);
}

void CommandBuffer::end() {
    vkEndCommandBuffer(_cmd);
}

void CommandBuffer::begin_rendering(
    VkRenderingInfo const& rendering_info) {
    vkCmdBeginRendering(_cmd, &rendering_info);
}

void CommandBuffer::end_rendering() {
    vkCmdEndRendering(_cmd);
}

void CommandBuffer::reset_query_pool(VkQueryPool query_pool, uint32_t first_query, uint32_t query_count) {
    vkCmdResetQueryPool(_cmd, query_pool, first_query, query_count);
}

void CommandBuffer::write_timestamp(VkPipelineStageFlagBits stage, VkQueryPool query_pool, uint32_t query) {
    vkCmdWriteTimestamp(_cmd, stage, query_pool, query);
}

void CommandBuffer::image_memory_barrier(VkImage image, VkImageAspectFlags aspect_mask,
                                          VkImageLayout old_layout, VkPipelineStageFlags2 src_stage, VkAccessFlags2 src_access,
                                          VkImageLayout new_layout, VkPipelineStageFlags2 dst_stage, VkAccessFlags2 dst_access,
                                          uint32_t src_queue_family, uint32_t dst_queue_family) {
    VkImageMemoryBarrier2 barrier = {};
    barrier.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER_2;
    barrier.srcStageMask = src_stage;
    barrier.srcAccessMask = src_access;
    barrier.dstStageMask = dst_stage;
    barrier.dstAccessMask = dst_access;
    barrier.oldLayout = old_layout;
    barrier.newLayout = new_layout;
    barrier.srcQueueFamilyIndex = src_queue_family;
    barrier.dstQueueFamilyIndex = dst_queue_family;
    barrier.image = image;
    barrier.subresourceRange.aspectMask = aspect_mask;
    barrier.subresourceRange.baseMipLevel = 0;
    barrier.subresourceRange.levelCount = 1;
    barrier.subresourceRange.baseArrayLayer = 0;
    barrier.subresourceRange.layerCount = 1;

    VkDependencyInfo dependency_info = {};
    dependency_info.sType = VK_STRUCTURE_TYPE_DEPENDENCY_INFO;
    dependency_info.imageMemoryBarrierCount = 1;
    dependency_info.pImageMemoryBarriers = &barrier;

    vkCmdPipelineBarrier2(_cmd, &dependency_info);
}

void CommandBuffer::set_viewport(float x, float y, float width, float height, float min_depth, float max_depth) {
    VkViewport viewport = {};
    viewport.x = x;
    viewport.y = y;
    viewport.width = width;
    viewport.height = height;
    viewport.minDepth = min_depth;
    viewport.maxDepth = max_depth;
    vkCmdSetViewportWithCount(_cmd, 1, &viewport);
}

void CommandBuffer::set_scissor(int32_t x, int32_t y, uint32_t width, uint32_t height) {
    VkRect2D scissor = {};
    scissor.offset = {x, y};
    scissor.extent = {width, height};
    vkCmdSetScissorWithCount(_cmd, 1, &scissor);
}

void CommandBuffer::set_rasterizer_discard_enable(bool enable) {
    vkCmdSetRasterizerDiscardEnable(_cmd, enable ? VK_TRUE : VK_FALSE);
}

void CommandBuffer::set_polygon_mode(VkPolygonMode polygon_mode) {
    vkCmdSetPolygonModeEXT(_cmd, polygon_mode);
}

void CommandBuffer::set_cull_mode(VkCullModeFlags cull_mode) {
    vkCmdSetCullMode(_cmd, cull_mode);
}

void CommandBuffer::set_front_face(VkFrontFace front_face) {
    vkCmdSetFrontFace(_cmd, front_face);
}

void CommandBuffer::set_depth_bias_enable(bool enable) {
    vkCmdSetDepthBiasEnable(_cmd, enable ? VK_TRUE : VK_FALSE);
}

void CommandBuffer::set_primitive_topology(VkPrimitiveTopology topology) {
    vkCmdSetPrimitiveTopology(_cmd, topology);
}

void CommandBuffer::set_primitive_restart_enable(bool enable) {
    vkCmdSetPrimitiveRestartEnable(_cmd, enable ? VK_TRUE : VK_FALSE);
}

void CommandBuffer::set_depth_test_enable(bool enable) {
    vkCmdSetDepthTestEnable(_cmd, enable ? VK_TRUE : VK_FALSE);
}

void CommandBuffer::set_depth_write_enable(bool enable) {
    vkCmdSetDepthWriteEnable(_cmd, enable ? VK_TRUE : VK_FALSE);
}

void CommandBuffer::set_depth_bounds_test_enable(bool enable) {
    vkCmdSetDepthBoundsTestEnable(_cmd, enable ? VK_TRUE : VK_FALSE);
}

void CommandBuffer::set_stencil_test_enable(bool enable) {
    vkCmdSetStencilTestEnable(_cmd, enable ? VK_TRUE : VK_FALSE);
}

void CommandBuffer::set_rasterization_samples(VkSampleCountFlagBits samples) {
    vkCmdSetRasterizationSamplesEXT(_cmd, samples);
}

void CommandBuffer::set_sample_mask(VkSampleCountFlagBits samples, uint32_t mask) {
    VkSampleMask sample_mask = mask;
    vkCmdSetSampleMaskEXT(_cmd, samples, &sample_mask);
}

void CommandBuffer::set_alpha_to_coverage_enable(bool enable) {
    vkCmdSetAlphaToCoverageEnableEXT(_cmd, enable ? VK_TRUE : VK_FALSE);
}

void CommandBuffer::set_color_blend_enable(uint32_t attachment, bool enable) {
    VkBool32 enables[] = {enable ? VK_TRUE : VK_FALSE};
    vkCmdSetColorBlendEnableEXT(_cmd, attachment, 1, enables);
}

void CommandBuffer::set_color_write_mask(uint32_t attachment, VkColorComponentFlags mask) {
    VkColorComponentFlags masks[] = {mask};
    vkCmdSetColorWriteMaskEXT(_cmd, attachment, 1, masks);
}

void CommandBuffer::set_vertex_input_empty() {
    vkCmdSetVertexInputEXT(_cmd, 0, nullptr, 0, nullptr);
}

void CommandBuffer::bind_descriptor_sets(VkPipelineBindPoint bind_point, VkPipelineLayout layout,
                                          uint32_t first_set, uint32_t set_count, VkDescriptorSet const* sets) {
    vkCmdBindDescriptorSets(_cmd, bind_point, layout, first_set, set_count, sets, 0, nullptr);
}

void CommandBuffer::push_constants(VkPipelineLayout layout, VkShaderStageFlags stage_flags,
                                    uint32_t offset, uint32_t size, void const* data) {
    vkCmdPushConstants(_cmd, layout, stage_flags, offset, size, data);
}

void CommandBuffer::draw(uint32_t vertex_count, uint32_t instance_count,
                          uint32_t first_vertex, uint32_t first_instance) {
    vkCmdDraw(_cmd, vertex_count, instance_count, first_vertex, first_instance);
}
