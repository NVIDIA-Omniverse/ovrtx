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

std::pair<ShaderHandle, ShaderHandle> VulkanContext::create_linked_vertex_and_fragment_shaders(
    std::vector<uint32_t> const& vert_spirv,
    std::vector<uint32_t> const& frag_spirv) {

    // Push constants are shared by the fullscreen pass (texture index) and the
    // marquee overlay pass (rectangle + viewport size).
    VkPushConstantRange push_constant_range = {};
    push_constant_range.stageFlags =
        VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT;
    push_constant_range.offset = 0;
    push_constant_range.size = sizeof(float) * 8;

    VkShaderCreateInfoEXT shader_infos[2] = {};

    shader_infos[0].sType = VK_STRUCTURE_TYPE_SHADER_CREATE_INFO_EXT;
    shader_infos[0].flags = VK_SHADER_CREATE_LINK_STAGE_BIT_EXT;
    shader_infos[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
    shader_infos[0].nextStage = VK_SHADER_STAGE_FRAGMENT_BIT;
    shader_infos[0].codeType = VK_SHADER_CODE_TYPE_SPIRV_EXT;
    shader_infos[0].codeSize = vert_spirv.size() * sizeof(uint32_t);
    shader_infos[0].pCode = vert_spirv.data();
    shader_infos[0].pName = "main";
    shader_infos[0].setLayoutCount = 1;
    shader_infos[0].pSetLayouts = &_descriptor_set_layout;
    shader_infos[0].pushConstantRangeCount = 1;
    shader_infos[0].pPushConstantRanges = &push_constant_range;

    shader_infos[1].sType = VK_STRUCTURE_TYPE_SHADER_CREATE_INFO_EXT;
    shader_infos[1].flags = VK_SHADER_CREATE_LINK_STAGE_BIT_EXT;
    shader_infos[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
    shader_infos[1].nextStage = 0;
    shader_infos[1].codeType = VK_SHADER_CODE_TYPE_SPIRV_EXT;
    shader_infos[1].codeSize = frag_spirv.size() * sizeof(uint32_t);
    shader_infos[1].pCode = frag_spirv.data();
    shader_infos[1].pName = "main";
    shader_infos[1].setLayoutCount = 1;
    shader_infos[1].pSetLayouts = &_descriptor_set_layout;
    shader_infos[1].pushConstantRangeCount = 1;
    shader_infos[1].pPushConstantRanges = &push_constant_range;

    VkShaderEXT shaders[2];
    VK_CHECK(vkCreateShadersEXT(_device, 2, shader_infos, nullptr, shaders));

    // Insert into map
    ShaderHandle vert_handle{_next_shader_id++};
    ShaderHandle frag_handle{_next_shader_id++};

    _shaders[vert_handle.id] = Shader{shaders[0], VK_SHADER_STAGE_VERTEX_BIT};
    _shaders[frag_handle.id] = Shader{shaders[1], VK_SHADER_STAGE_FRAGMENT_BIT};

    return {vert_handle, frag_handle};
}

Shader const& VulkanContext::shader(ShaderHandle handle) const {
    auto it = _shaders.find(handle.id);
    if (it == _shaders.end()) {
        throw std::runtime_error("Invalid shader handle");
    }
    return it->second;
}

void VulkanContext::destroy_shader(ShaderHandle handle) {
    auto it = _shaders.find(handle.id);
    if (it == _shaders.end()) {
        throw std::runtime_error("Invalid shader handle");
    }
    vkDestroyShaderEXT(_device, it->second.shader, nullptr);
    _shaders.erase(it);
}

void VulkanContext::bind_shaders(
    std::optional<ShaderHandle> vertex,
    std::optional<ShaderHandle> fragment,
    std::optional<ShaderHandle> tessellation_control,
    std::optional<ShaderHandle> tessellation_evaluation,
    std::optional<ShaderHandle> geometry) {

    // Build arrays for all 5 possible stages
    VkShaderStageFlagBits stages[5] = {
        VK_SHADER_STAGE_VERTEX_BIT,
        VK_SHADER_STAGE_TESSELLATION_CONTROL_BIT,
        VK_SHADER_STAGE_TESSELLATION_EVALUATION_BIT,
        VK_SHADER_STAGE_GEOMETRY_BIT,
        VK_SHADER_STAGE_FRAGMENT_BIT
    };

    VkShaderEXT shader_handles[5] = {
        vertex.has_value() ? shader(*vertex).shader : VK_NULL_HANDLE,
        tessellation_control.has_value() ? shader(*tessellation_control).shader : VK_NULL_HANDLE,
        tessellation_evaluation.has_value() ? shader(*tessellation_evaluation).shader : VK_NULL_HANDLE,
        geometry.has_value() ? shader(*geometry).shader : VK_NULL_HANDLE,
        fragment.has_value() ? shader(*fragment).shader : VK_NULL_HANDLE
    };

    vkCmdBindShadersEXT(_vk_command_buffer, 5, stages, shader_handles);
}
