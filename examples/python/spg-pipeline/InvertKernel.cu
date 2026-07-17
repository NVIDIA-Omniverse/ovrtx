// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Second pass of the pipeline: invert an image. The input is whatever upstream
// shader is connected to inputs:Image — here, the grayscale output.
extern "C" __global__ void invert(
    int width,
    int height,
    float strength,
    cudaTextureObject_t inputImage,
    cudaSurfaceObject_t outputInverted)
{
    int x = blockIdx.x * blockDim.x + threadIdx.x;
    int y = blockIdx.y * blockDim.y + threadIdx.y;

    if (x < width && y < height)
    {
        uchar4 pixel = tex2D<uchar4>(inputImage, x, y);

        // lerp(original, 255 - original, strength) per RGB channel.
        unsigned char r = (unsigned char)(pixel.x + strength * (255 - 2 * pixel.x));
        unsigned char g = (unsigned char)(pixel.y + strength * (255 - 2 * pixel.y));
        unsigned char b = (unsigned char)(pixel.z + strength * (255 - 2 * pixel.z));

        uchar4 out = { r, g, b, pixel.w };
        surf2Dwrite<uchar4>(out, outputInverted, x * sizeof(uchar4), y);
    }
}
