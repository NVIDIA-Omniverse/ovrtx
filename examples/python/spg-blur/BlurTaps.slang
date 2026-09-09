// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// [snippet:blur-module]
// The tap loop both blur passes run, kept in its own module so neither entry
// point restates it. This file declares no entry point and is not a node: it is
// reached only through `import BlurTaps;` in BlurKernel.slang, which resolves to
// this file because it sits beside it.
//
// `public` is what makes a symbol visible to an importing module.
public float3 blurTap(Texture2D<float4> image,
                      StructuredBuffer<float> weights,
                      int radius,
                      int width,
                      int height,
                      int2 pixel,
                      int2 direction)
{
    float3 sum = float3(0.0, 0.0, 0.0);
    for (int t = -radius; t <= radius; ++t)
    {
        int2 at = clamp(pixel + t * direction, int2(0, 0), int2(width - 1, height - 1));
        sum += weights[t + radius] * image.Load(int3(at, 0)).rgb;
    }
    return sum;
}
// [/snippet:blur-module]
