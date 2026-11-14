// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// [snippet:checker-kernel]
// A node that reads no AOV. Everything it needs arrives as a typed USD
// attribute, and it writes a checkerboard into its own output.
//
// A vector value-input arrives as a pointer to its components, not by value,
// so the two colours are const float*. No system #include: NVRTC has no
// toolkit include path. uchar4 is a CUDA built-in.
extern "C" __global__ void checker(
    int width,
    int height,
    int squareSize,
    const float* colorA,
    const float* colorB,
    cudaSurfaceObject_t output)
{
    const int x = blockIdx.x * blockDim.x + threadIdx.x;
    const int y = blockIdx.y * blockDim.y + threadIdx.y;
    if (x >= width || y >= height)
    {
        return;
    }

    const bool onA = (((x / squareSize) + (y / squareSize)) % 2) == 0;
    const float* c = onA ? colorA : colorB;

    // Round to the nearest 8-bit value rather than truncate.
    uchar4 out;
    out.x = (unsigned char)(c[0] * 255.0f + 0.5f);
    out.y = (unsigned char)(c[1] * 255.0f + 0.5f);
    out.z = (unsigned char)(c[2] * 255.0f + 0.5f);
    out.w = 255;
    surf2Dwrite(out, output, x * (int)sizeof(uchar4), y);
}
// [/snippet:checker-kernel]
