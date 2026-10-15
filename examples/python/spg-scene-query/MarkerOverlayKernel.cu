// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Marker overlay: projects scene prims into the camera image and draws a crosshair on each.
//
// The launch script reads the camera's world transform and lens values and the markers' world
// positions out of the scene and hands them in. This kernel copies the rendered image and, for
// every marker in front of the camera, draws a one-pixel crosshair where the camera model puts it.
//
// The camera transform is the flattened world matrix as USD stores it: row-major, the first
// three rows the camera's axes in world space, the fourth row its position. The camera looks
// down its own -Z axis. No scale is assumed on the camera.

// [snippet:marker-overlay-kernel]
extern "C" __global__ void markerOverlay(
    int width,
    int height,
    const float* cameraWorld,       // 16 values, row-major, translation in the last row
    float focalLength,
    float horizontalAperture,
    float verticalAperture,
    const float* markerPositions,   // 3 values per marker, world space
    int markerCount,
    float crosshairSize,            // half-length of a crosshair arm, in pixels
    cudaTextureObject_t image,
    cudaSurfaceObject_t overlay)
{
    const int x = blockIdx.x * blockDim.x + threadIdx.x;
    const int y = blockIdx.y * blockDim.y + threadIdx.y;
    if (x >= width || y >= height)
        return;

    uchar4 pixel = tex2D<uchar4>(image, x, y);

    const float px = x + 0.5f;
    const float py = y + 0.5f;
    const float scaleX = 2.0f * focalLength / horizontalAperture;
    const float scaleY = 2.0f * focalLength / verticalAperture;

    for (int i = 0; i < markerCount; ++i)
    {
        // World position relative to the camera, then onto the camera's axes.
        const float dx = markerPositions[3 * i + 0] - cameraWorld[12];
        const float dy = markerPositions[3 * i + 1] - cameraWorld[13];
        const float dz = markerPositions[3 * i + 2] - cameraWorld[14];
        const float cx = dx * cameraWorld[0] + dy * cameraWorld[1] + dz * cameraWorld[2];
        const float cy = dx * cameraWorld[4] + dy * cameraWorld[5] + dz * cameraWorld[6];
        const float cz = dx * cameraWorld[8] + dy * cameraWorld[9] + dz * cameraWorld[10];
        if (cz >= 0.0f)
            continue; // behind the camera

        // Perspective projection onto the image, y down.
        const float ndcX = cx / -cz * scaleX;
        const float ndcY = cy / -cz * scaleY;
        const float sx = (ndcX * 0.5f + 0.5f) * width;
        const float sy = (0.5f - ndcY * 0.5f) * height;

        const float ax = fabsf(px - sx);
        const float ay = fabsf(py - sy);
        const bool onArm = (ax <= crosshairSize && ay <= 0.5f) || (ay <= crosshairSize && ax <= 0.5f);
        if (!onArm)
            continue;

        pixel = make_uchar4(255, 255, 255, 255);
    }

    surf2Dwrite<uchar4>(pixel, overlay, x * sizeof(uchar4), y);
}
// [/snippet:marker-overlay-kernel]
