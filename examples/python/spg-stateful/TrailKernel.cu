// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// [snippet:trail-kernel]
// Framebuffer feedback: fade what the node published last time, add what it was
// handed this time.
//
//     history[n] = current[n] + decay * history[n-1]
//
// That one line is the whole node. history[n-1] is the previous execution's
// output, and it exists only because the allocation is stateful. Take that away
// and the recursion collapses to history[n] = current[n], which is the frame the
// node was already handed. There is no version of this effect that does not read
// back what it wrote.
//
// The node publishes both images so they can be compared directly. Live is the
// frame as handed in, Trail is the feedback result. They come from the same
// input through the same tone map, so the only difference between them is
// history[n-1].
//
// Feedback amplifies whatever holds still: a pixel showing the same radiance
// every frame settles at current / (1 - decay). Scaling the published image by
// (1 - decay) puts the static scene back at its true brightness, so the backdrop
// reads the same in both images and only what actually moved leaves a tail.

// Reinhard: maps [0, inf) to [0, 1), so the bright ball and the dim backdrop
// share one image without either clipping to a flat block.
__device__ inline float toneMap(float radiance)
{
    return radiance / (1.0f + fmaxf(0.0f, radiance));
}

__device__ inline uchar4 encode(float3 colour)
{
    return make_uchar4(
        (unsigned char)(fminf(1.0f, fmaxf(0.0f, toneMap(colour.x))) * 255.0f + 0.5f),
        (unsigned char)(fminf(1.0f, fmaxf(0.0f, toneMap(colour.y))) * 255.0f + 0.5f),
        (unsigned char)(fminf(1.0f, fmaxf(0.0f, toneMap(colour.z))) * 255.0f + 0.5f),
        255);
}

extern "C" __global__ void trail(
    int width,
    int height,
    float decay,           // fraction of the previous frame kept, 0 to 1
    cudaTextureObject_t inputImage,
    cudaSurfaceObject_t history,
    cudaSurfaceObject_t liveImage,
    cudaSurfaceObject_t trailImage)
{
    int x = blockIdx.x * blockDim.x + threadIdx.x;
    int y = blockIdx.y * blockDim.y + threadIdx.y;

    if (x >= width || y >= height)
        return;

    float4 current = tex2D<float4>(inputImage, x, y);

    // history[n-1], read through an ordinary surface: a stateful output binds
    // like any other. Without the stateful marker this reads back empty every
    // frame, whatever the node wrote below.
    float4 previous;
    surf2Dread<float4>(&previous, history, x * sizeof(float4), y);

    float4 fed;
    fed.x = current.x + decay * previous.x;
    fed.y = current.y + decay * previous.y;
    fed.z = current.z + decay * previous.z;
    fed.w = 1.0f;

    // Carry it to the next execution. This write is the other half of the loop,
    // and it is the only reason the node has anything to fade next frame.
    surf2Dwrite<float4>(fed, history, x * sizeof(float4), y);

    float3 live = make_float3(current.x, current.y, current.z);
    surf2Dwrite<uchar4>(encode(live), liveImage, x * sizeof(uchar4), y);

    float exposure = 1.0f - decay;
    float3 trailed = make_float3(fed.x * exposure, fed.y * exposure, fed.z * exposure);
    surf2Dwrite<uchar4>(encode(trailed), trailImage, x * sizeof(uchar4), y);
}
// [/snippet:trail-kernel]
