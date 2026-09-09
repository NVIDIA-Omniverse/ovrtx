// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// SPG shader: convert the LdrColor AOV to grayscale. Slang counterpart of
// GrayscaleKernel.cu -- same inputs, same output, same result.
//
// The entry point name ("grayscale") must match the subIdentifier authored in
// GrayscaleKernel.slang.usda and the Lua launch function name.
//
// Resources are bound positionally: the Nth resource declared here receives
// the Nth entry of the launch script's bind list. Slot 0 of the binding space
// is reserved for the parameter block, so resources start at slot 1.
[[vk::binding(1, 1)]] Texture2D<float4> g_InLdrColor;
[[vk::binding(2, 1)]] RWTexture2D<float4> g_OutLdrGrayscale;

[shader("compute")]
[numthreads(32, 32, 1)]
void grayscale(uint3 tid : SV_DispatchThreadID)
{
    // The image size comes from the bound texture, so no width/height inputs
    // are needed.
    uint width = 0, height = 0;
    g_InLdrColor.GetDimensions(width, height);

    if (tid.x >= width || tid.y >= height)
        return;

    // An RGBA8 AOV is read as a normalized float4 (each channel 0..1).
    float4 pixel = g_InLdrColor.Load(int3(tid.xy, 0));

    // ITU-R BT.601 luminance weights.
    float luminance = dot(pixel.rgb, float3(0.299, 0.587, 0.114));

    // Writing float4 to an RGBA8 output re-quantizes to 8 bits per channel.
    g_OutLdrGrayscale[tid.xy] = float4(luminance, luminance, luminance, pixel.a);
}
