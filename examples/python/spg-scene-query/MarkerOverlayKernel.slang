// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Marker overlay in Slang: the same projection as MarkerOverlayKernel.cu.
//
// Scalars arrive in the parameter block, in the order the launch script lists them. The camera
// transform and the marker positions arrive as read-only buffers of floats, bound after the
// block in the order of the bind list.

// [snippet:marker-overlay-slang-kernel]
struct Params
{
    int width;
    int height;
    float focalLength;
    float horizontalAperture;
    float verticalAperture;
    int markerCount;
    float crosshairSize;
};

[[vk::binding(0, 1)]] ParameterBlock<Params>   g_Params;
[[vk::binding(1, 1)]] StructuredBuffer<float>  g_CameraWorld;      // 16 values, row-major
[[vk::binding(2, 1)]] StructuredBuffer<float>  g_MarkerPositions;  // 3 values per marker
[[vk::binding(3, 1)]] Texture2D<float4>        g_Image;
[[vk::binding(4, 1)]] RWTexture2D<float4>      g_Overlay;

[shader("compute")]
[numthreads(16, 16, 1)]
void markerOverlay(uint3 tid : SV_DispatchThreadID)
{
    if (tid.x >= (uint)g_Params.width || tid.y >= (uint)g_Params.height)
        return;

    float4 pixel = g_Image.Load(int3(tid.xy, 0));

    const float px = tid.x + 0.5;
    const float py = tid.y + 0.5;
    const float scaleX = 2.0 * g_Params.focalLength / g_Params.horizontalAperture;
    const float scaleY = 2.0 * g_Params.focalLength / g_Params.verticalAperture;

    for (int i = 0; i < g_Params.markerCount; ++i)
    {
        const float dx = g_MarkerPositions[3 * i + 0] - g_CameraWorld[12];
        const float dy = g_MarkerPositions[3 * i + 1] - g_CameraWorld[13];
        const float dz = g_MarkerPositions[3 * i + 2] - g_CameraWorld[14];
        const float cx = dx * g_CameraWorld[0] + dy * g_CameraWorld[1] + dz * g_CameraWorld[2];
        const float cy = dx * g_CameraWorld[4] + dy * g_CameraWorld[5] + dz * g_CameraWorld[6];
        const float cz = dx * g_CameraWorld[8] + dy * g_CameraWorld[9] + dz * g_CameraWorld[10];
        if (cz >= 0.0)
            continue; // behind the camera

        const float ndcX = cx / -cz * scaleX;
        const float ndcY = cy / -cz * scaleY;
        const float sx = (ndcX * 0.5 + 0.5) * g_Params.width;
        const float sy = (0.5 - ndcY * 0.5) * g_Params.height;

        const float ax = abs(px - sx);
        const float ay = abs(py - sy);
        const bool onArm = (ax <= g_Params.crosshairSize && ay <= 0.5) || (ay <= g_Params.crosshairSize && ax <= 0.5);
        if (!onArm)
            continue;

        pixel = float4(1.0, 1.0, 1.0, 1.0);
    }

    g_Overlay[tid.xy] = pixel;
}
// [/snippet:marker-overlay-slang-kernel]
