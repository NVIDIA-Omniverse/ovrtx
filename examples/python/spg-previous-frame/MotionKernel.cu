// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// [snippet:motion-kernel]
// The difference between this frame and the last one. The node holds no state of
// its own: both images are handed to it, one bound to the live AOV and one to
// the same AOV a frame back.
extern "C" __global__ void motion(int width,
                                  int height,
                                  float gain,
                                  cudaTextureObject_t current,
                                  cudaTextureObject_t previous,
                                  cudaSurfaceObject_t difference)
{
    int x = blockIdx.x * blockDim.x + threadIdx.x;
    int y = blockIdx.y * blockDim.y + threadIdx.y;
    if (x >= width || y >= height)
        return;

    uchar4 now = tex2D<uchar4>(current, x, y);
    uchar4 then = tex2D<uchar4>(previous, x, y);

    float changed = (abs((int)now.x - (int)then.x) + abs((int)now.y - (int)then.y) +
                     abs((int)now.z - (int)then.z)) /
                    3.0f;
    unsigned char m = (unsigned char)min(255.0f, changed * gain);

    surf2Dwrite<uchar4>(make_uchar4(m, m, m, 255), difference, x * sizeof(uchar4), y);
}
// [/snippet:motion-kernel]
