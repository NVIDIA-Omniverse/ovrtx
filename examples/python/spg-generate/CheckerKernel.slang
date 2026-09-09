// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// [snippet:checker-slang-kernel]
// Slang counterpart of CheckerKernel.cu. Same node, same attributes, same
// output: a checkerboard built from values alone, with no AOV read.
//
// Values do not arrive individually on Slang. They are packed into one constant
// buffer, and the struct's field order must match the order the launch script
// lists them in slang.ParameterBlock(...).
struct Params
{
    int width;
    int height;
    int squareSize;
    float3 colorA;
    float3 colorB;
};

[[vk::binding(0, 1)]] ParameterBlock<Params> g_Params;
[[vk::binding(1, 1)]] RWTexture2D<float4> g_OutChecker;

[shader("compute")]
[numthreads(16, 16, 1)]
void checker(uint3 tid : SV_DispatchThreadID)
{
    if (tid.x >= (uint)g_Params.width || tid.y >= (uint)g_Params.height)
        return;

    const int cell = int(tid.x) / g_Params.squareSize + int(tid.y) / g_Params.squareSize;
    const float3 c = (cell % 2) == 0 ? g_Params.colorA : g_Params.colorB;

    g_OutChecker[tid.xy] = float4(c, 1.0);
}
// [/snippet:checker-slang-kernel]
