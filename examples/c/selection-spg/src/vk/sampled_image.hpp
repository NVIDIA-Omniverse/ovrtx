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

// Handle for referencing sampled images
struct SampledImageHandle {
    uint64_t id = 0;
    bool operator==(SampledImageHandle const& other) const { return id == other.id; }
    bool operator!=(SampledImageHandle const& other) const { return id != other.id; }
};

// Combined image + sampler resource
struct SampledImage {
    VkImage image = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    VkImageView view = VK_NULL_HANDLE;
    VkSampler sampler = VK_NULL_HANDLE;
    VkDeviceSize size = 0;
    int width = 0;
    int height = 0;
    uint32_t descriptor_index = 0;  // Index in descriptor array for bindless access
};
