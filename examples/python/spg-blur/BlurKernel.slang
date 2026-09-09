// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// The Slang half of the separable blur. Both entry points live here, and the
// tap loop they share lives in BlurTaps.slang beside this file.

import BlurTaps;

struct Params
{
    int width;
    int height;
    int radius;
};

[[vk::binding(0, 1)]] ParameterBlock<Params>      g_Params;
[[vk::binding(1, 1)]] StructuredBuffer<float>     g_Weights;
[[vk::binding(2, 1)]] Texture2D<float4>           g_InImage;
[[vk::binding(3, 1)]] RWTexture2D<float4>         g_OutBlurred;

// One invocation per output pixel: the mapping SPG derives from the output's
// shape and this thread group size, with nothing stated in the launch script.
[shader("compute")]
[numthreads(16, 16, 1)]
void blurHorizontal(uint3 tid : SV_DispatchThreadID)
{
    int2 pixel = int2(tid.xy);
    if (pixel.x >= g_Params.width || pixel.y >= g_Params.height)
        return;

    float3 sum = blurTap(g_InImage, g_Weights, g_Params.radius, g_Params.width, g_Params.height, pixel, int2(1, 0));
    g_OutBlurred[pixel] = float4(sum, g_InImage.Load(int3(pixel, 0)).a);
}

// [snippet:blur-vertical-slang-kernel]
// One invocation per output COLUMN, each walking its column top to bottom. The
// iteration domain is the width alone, so the launch script states the grid.
[shader("compute")]
[numthreads(256, 1, 1)]
void blurVertical(uint3 tid : SV_DispatchThreadID)
{
    int x = int(tid.x);
    if (x >= g_Params.width)
        return;

    for (int y = 0; y < g_Params.height; ++y)
    {
        int2 pixel = int2(x, y);
        float3 sum = blurTap(g_InImage, g_Weights, g_Params.radius, g_Params.width, g_Params.height, pixel, int2(0, 1));
        g_OutBlurred[pixel] = float4(sum, g_InImage.Load(int3(pixel, 0)).a);
    }
}
// [/snippet:blur-vertical-slang-kernel]
