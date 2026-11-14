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
#include <cstdint>

// Handle for referencing shaders
struct ShaderHandle {
    uint64_t id = 0;
    bool operator==(ShaderHandle const& other) const { return id == other.id; }
    bool operator!=(ShaderHandle const& other) const { return id != other.id; }
};

// Shader object resource
struct Shader {
    VkShaderEXT shader = VK_NULL_HANDLE;
    VkShaderStageFlagBits stage;
};
