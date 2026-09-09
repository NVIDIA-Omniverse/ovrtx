// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// The Slang half of the motion node. Both images arrive as ordinary textures;
// which of them is a past frame is settled in the scene, not here.

struct Params
{
    int width;
    int height;
    float gain;
};

[[vk::binding(0, 1)]] ParameterBlock<Params>  g_Params;
[[vk::binding(1, 1)]] Texture2D<float4>       g_InCurrent;
[[vk::binding(2, 1)]] Texture2D<float4>       g_InPrevious;
[[vk::binding(3, 1)]] RWTexture2D<float4>     g_OutDifference;

[shader("compute")]
[numthreads(16, 16, 1)]
void motion(uint3 tid : SV_DispatchThreadID)
{
    int2 pixel = int2(tid.xy);
    if (pixel.x >= g_Params.width || pixel.y >= g_Params.height)
        return;

    float3 now = g_InCurrent.Load(int3(pixel, 0)).rgb;
    float3 then = g_InPrevious.Load(int3(pixel, 0)).rgb;

    float changed = dot(abs(now - then), float3(1.0, 1.0, 1.0)) / 3.0;
    float m = saturate(changed * g_Params.gain);

    g_OutDifference[pixel] = float4(m, m, m, 1.0);
}
