// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// A separable Gaussian blur, in two passes that share this file. Both entry
// points are extern "C" so NVRTC resolves them by the subIdentifier authored in
// USD; two Shader prims point at this one source and name a different one.
//
// The tap weights are not computed here. They depend only on the radius, so the
// launch script builds them once and hands them over as a device buffer.

// [snippet:blur-tap]
// One row of taps, walked in the direction (dx, dy). Coordinates are clamped to
// the image, so an edge pixel repeats rather than sampling nothing.
__device__ inline float4 blurTap(cudaTextureObject_t image,
                                 const float* weights,
                                 int radius,
                                 int width,
                                 int height,
                                 int x,
                                 int y,
                                 int dx,
                                 int dy)
{
    float4 sum = make_float4(0.0f, 0.0f, 0.0f, 0.0f);
    for (int t = -radius; t <= radius; ++t)
    {
        int sx = min(max(x + t * dx, 0), width - 1);
        int sy = min(max(y + t * dy, 0), height - 1);
        uchar4 texel = tex2D<uchar4>(image, sx, sy);
        float w = weights[t + radius];
        sum.x += w * texel.x;
        sum.y += w * texel.y;
        sum.z += w * texel.z;
    }
    return sum;
}
// [/snippet:blur-tap]

__device__ inline uchar4 toPixel(float4 sum, unsigned char alpha)
{
    return make_uchar4((unsigned char)min(255.0f, sum.x + 0.5f), (unsigned char)min(255.0f, sum.y + 0.5f),
                       (unsigned char)min(255.0f, sum.z + 0.5f), alpha);
}

// [snippet:blur-horizontal-kernel]
// One thread per output pixel. This is the mapping SPG derives when the launch
// script states no block and no grid.
extern "C" __global__ void blurHorizontal(int width,
                                          int height,
                                          int radius,
                                          const float* weights,
                                          cudaTextureObject_t image,
                                          cudaSurfaceObject_t blurred)
{
    int x = blockIdx.x * blockDim.x + threadIdx.x;
    int y = blockIdx.y * blockDim.y + threadIdx.y;
    if (x >= width || y >= height)
        return;

    float4 sum = blurTap(image, weights, radius, width, height, x, y, 1, 0);
    uchar4 centre = tex2D<uchar4>(image, x, y);
    surf2Dwrite<uchar4>(toPixel(sum, centre.w), blurred, x * sizeof(uchar4), y);
}
// [/snippet:blur-horizontal-kernel]

// [snippet:blur-vertical-kernel]
// One thread per output COLUMN, each walking its column top to bottom. The
// iteration domain is the width alone, so the launch script has to say so.
extern "C" __global__ void blurVertical(int width,
                                        int height,
                                        int radius,
                                        const float* weights,
                                        cudaTextureObject_t image,
                                        cudaSurfaceObject_t blurred)
{
    int x = blockIdx.x * blockDim.x + threadIdx.x;
    if (x >= width)
        return;

    for (int y = 0; y < height; ++y)
    {
        float4 sum = blurTap(image, weights, radius, width, height, x, y, 0, 1);
        uchar4 centre = tex2D<uchar4>(image, x, y);
        surf2Dwrite<uchar4>(toPixel(sum, centre.w), blurred, x * sizeof(uchar4), y);
    }
}
// [/snippet:blur-vertical-kernel]
