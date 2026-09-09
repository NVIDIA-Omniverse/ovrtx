// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// [snippet:invert-slang-kernel]
// Second pass of the pipeline: invert an image. Slang counterpart of
// InvertKernel.cu. The input is whatever upstream shader is connected to
// inputs:Image -- here, the grayscale output.
//
// Value-inputs are not passed as arguments like in CUDA. They are packed into
// a constant buffer described by a struct, which the shader reads through a
// ParameterBlock. The struct field order must match the order the launch
// script lists the values in slang.ParameterBlock(...).
struct Params
{
    float strength;
};

[[vk::binding(0, 1)]] ParameterBlock<Params> g_Params;
[[vk::binding(1, 1)]] Texture2D<float4> g_InImage;
[[vk::binding(2, 1)]] RWTexture2D<float4> g_OutInverted;

[shader("compute")]
[numthreads(32, 32, 1)]
void invert(uint3 tid : SV_DispatchThreadID)
{
    uint width = 0, height = 0;
    g_InImage.GetDimensions(width, height);

    if (tid.x >= width || tid.y >= height)
        return;

    float4 pixel = g_InImage.Load(int3(tid.xy, 0));

    // lerp(original, inverted, strength) per RGB channel. The CUDA kernel does
    // the same blend on 0..255 integers; here the channels are normalized
    // floats, so full inversion is 1.0 - value.
    float3 inverted = lerp(pixel.rgb, 1.0 - pixel.rgb, g_Params.strength);

    g_OutInverted[tid.xy] = float4(inverted, pixel.a);
}
// [/snippet:invert-slang-kernel]
