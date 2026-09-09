// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// [snippet:trail-slang-kernel]
// Slang counterpart of TrailKernel.cu: fade what the node published last time,
// add what it was handed this time.
//
//     history[n] = current[n] + decay * history[n-1]
//
// The history is bound as RWTexture2D because the shader reads it as well as
// writes it. Nothing in the shader marks it as state: what makes it survive
// between executions is the launch script allocating it with slang.stateful, so
// the shader treats it exactly like an ordinary output.
//
// The node publishes both images so they can be compared directly. Live is the
// frame as handed in, Trail is the feedback result, and the only difference
// between them is history[n-1].
struct Params
{
    float decay;   // fraction of the previous frame kept, 0 to 1
};

[[vk::binding(0, 1)]] ParameterBlock<Params> g_Params;
[[vk::binding(1, 1)]] Texture2D<float4> g_InImage;
[[vk::binding(2, 1)]] RWTexture2D<float4> g_History;
[[vk::binding(3, 1)]] RWTexture2D<float4> g_OutLive;
[[vk::binding(4, 1)]] RWTexture2D<float4> g_OutTrail;

// Reinhard: maps [0, inf) to [0, 1), so the bright ball and the dim backdrop
// share one image without either clipping to a flat block.
float3 toneMap(float3 radiance)
{
    return radiance / (1.0 + max(float3(0.0), radiance));
}

[shader("compute")]
[numthreads(32, 32, 1)]
void trail(uint3 tid : SV_DispatchThreadID)
{
    uint width = 0, height = 0;
    g_InImage.GetDimensions(width, height);

    if (tid.x >= width || tid.y >= height)
        return;

    float3 current = g_InImage.Load(int3(tid.xy, 0)).rgb;

    // history[n-1], read through an ordinary read/write binding: a stateful
    // output binds like any other. Without the stateful marker this reads back
    // empty every frame, whatever the shader writes below.
    float3 previous = g_History[tid.xy].rgb;

    float3 fed = current + g_Params.decay * previous;

    // Carry it to the next execution. This write is the other half of the loop,
    // and it is the only reason the shader has anything to fade next frame.
    g_History[tid.xy] = float4(fed, 1.0);

    g_OutLive[tid.xy] = float4(toneMap(current), 1.0);

    // Feedback amplifies whatever holds still, settling at 1 / (1 - decay)
    // times the incoming radiance. Scaling by (1 - decay) puts the static scene
    // back where it was, so the backdrop reads the same in both published images
    // and only what actually moved leaves a tail.
    g_OutTrail[tid.xy] = float4(toneMap(fed * (1.0 - g_Params.decay)), 1.0);
}
// [/snippet:trail-slang-kernel]
