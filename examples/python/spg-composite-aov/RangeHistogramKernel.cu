// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// [snippet:histogram-kernel]
// Counting a lidar sweep's returns by distance, and drawing the result as a bar
// chart.
//
// A composite AOV arrives as several named channels rather than one buffer, and
// each channel reaches the kernel as an ordinary device pointer. Two of them
// matter here:
//
//   Coordinates  [3, Nmax], laid out as all x, then all y, then all z. The
//                stride between the three runs is Nmax, the allocated capacity,
//                not the number of valid points.
//   Counts       one number for the whole sweep: how many entries of
//                Coordinates were filled. Every other entry is untouched, so
//                this is the bound on the loop below and nothing else.
//
// One thread per output column. Each thread owns one column exclusively: it
// counts the returns falling in its own distance bin and then writes its whole
// column, background included. That costs a pass over the points per column,
// where a production histogram would have every point atomically bump a shared
// bin. The trade buys three things worth having in an example: no atomics, no
// dependence on the output arriving cleared, and a result that does not depend
// on the order threads happen to run in.

extern "C" __global__ void rangeHistogram(
    int width,
    int height,
    int maxPoints,     // Nmax: the stride between the x, y and z runs
    int numBins,       // distance bins across the full width
    float maxRange,    // distance at the right edge of the chart
    float maxCount,    // bin population at full bar height
    const float* coordinates,
    const int* counts, // counts[0] = how many points the sweep actually returned
    cudaSurfaceObject_t histogram)
{
    int col = blockIdx.x * blockDim.x + threadIdx.x;
    if (col >= width)
        return;

    int columnsPerBin = width / numBins;
    int bin = col / columnsPerBin;
    float binLo = (float)bin * maxRange / (float)numBins;
    float binHi = (float)(bin + 1) * maxRange / (float)numBins;

    // Only the first counts[0] entries hold a return. Running to maxPoints
    // instead would count entries the sweep never wrote.
    int valid = counts[0];
    if (valid > maxPoints)
        valid = maxPoints;

    int tally = 0;
    for (int i = 0; i < valid; ++i)
    {
        float px = coordinates[i];
        float py = coordinates[i + maxPoints];
        float pz = coordinates[i + 2 * maxPoints];
        float range = sqrtf(px * px + py * py + pz * pz);
        if (range >= binLo && range < binHi)
            ++tally;
    }

    float fraction = (float)tally / fmaxf(1.0f, maxCount);
    if (fraction > 1.0f)
        fraction = 1.0f;
    int barTop = height - (int)(fraction * (float)height + 0.5f);

    // A blank column at the right of each bin, so neighbouring bars stay apart.
    bool gap = (col % columnsPerBin) == columnsPerBin - 1;

    uchar4 barColour = make_uchar4(90, 170, 255, 255);
    uchar4 background = make_uchar4(18, 18, 22, 255);

    for (int row = 0; row < height; ++row)
    {
        uchar4 pixel = (!gap && row >= barTop) ? barColour : background;
        surf2Dwrite<uchar4>(pixel, histogram, col * sizeof(uchar4), row);
    }
}
// [/snippet:histogram-kernel]
