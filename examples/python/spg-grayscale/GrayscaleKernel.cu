// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// [snippet:grayscale-kernel-template]
// SPG kernel: convert the LdrColor AOV to grayscale.
// The entry point is declared extern "C" so NVRTC can resolve it by the
// subIdentifier name ("grayscale") authored in GrayscaleKernel.usda.
extern "C" __global__ void grayscale(
    int width,
    int height,
    cudaTextureObject_t inputLdrColor,
    cudaSurfaceObject_t outputLdrGrayscale)
{
    int x = blockIdx.x * blockDim.x + threadIdx.x;
    int y = blockIdx.y * blockDim.y + threadIdx.y;

    if (x < width && y < height)
    {
        // Read the input AOV through a read-only, hardware-cached texture.
        uchar4 pixel = tex2D<uchar4>(inputLdrColor, x, y);

        // ITU-R BT.601 luminance weights.
        float luminance = 0.299f * pixel.x + 0.587f * pixel.y + 0.114f * pixel.z;
        unsigned char gray = (unsigned char)min(255.0f, max(0.0f, luminance));

        // Write the output AOV through a read/write surface.
        uchar4 out = { gray, gray, gray, pixel.w };
        surf2Dwrite<uchar4>(out, outputLdrGrayscale, x * sizeof(uchar4), y);
    }
}
// [/snippet:grayscale-kernel-template]
