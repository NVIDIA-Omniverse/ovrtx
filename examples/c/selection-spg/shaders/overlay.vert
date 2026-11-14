// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#version 450

layout(push_constant) uniform PushConstants {
    vec4 rect;          // left, top, right, bottom in framebuffer pixels
    vec2 viewport_size; // width, height in framebuffer pixels
    vec2 pad;
} push;

void main() {
    vec2 corners[5] = vec2[](
        vec2(push.rect.x, push.rect.y),
        vec2(push.rect.z, push.rect.y),
        vec2(push.rect.z, push.rect.w),
        vec2(push.rect.x, push.rect.w),
        vec2(push.rect.x, push.rect.y)
    );

    vec2 pixel = corners[gl_VertexIndex];
    vec2 ndc = vec2(
        (pixel.x / push.viewport_size.x) * 2.0 - 1.0,
        (pixel.y / push.viewport_size.y) * 2.0 - 1.0
    );
    gl_Position = vec4(ndc, 0.0, 1.0);
}
