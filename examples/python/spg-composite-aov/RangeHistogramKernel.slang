// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// [snippet:histogram-slang-kernel]
// Slang counterpart of RangeHistogramKernel.cu: count a lidar sweep's returns by
// distance and draw the result as a bar chart.
//
// The composite's channels arrive as StructuredBuffer rather than as raw
// pointers, which is how a Slang node reads any buffer-shaped input. Coordinates
// is laid out [3, Nmax], all x then all y then all z, so the stride between the
// three runs is Nmax, the allocated capacity, not the number of valid points.
// Counts holds one number for the whole sweep and bounds the loop below.
//
// One thread per output column, which is why the launch script states a grid
// and grid explicitly rather than letting SPG derive them from the output shape.
// Each thread owns its column exclusively, so the node needs no atomics, does
// not depend on the output arriving cleared, and produces the same result
// whatever order the threads run in.
struct Params
{
    int maxPoints;     // Nmax: the stride between the x, y and z runs
    int numBins;       // distance bins across the full width
    float maxRange;    // distance at the right edge of the chart
    float maxCount;    // bin population at full bar height
};

[[vk::binding(0, 1)]] ParameterBlock<Params> g_Params;
[[vk::binding(1, 1)]] StructuredBuffer<float> g_Coordinates;
[[vk::binding(2, 1)]] StructuredBuffer<int> g_Counts;
[[vk::binding(3, 1)]] RWTexture2D<float4> g_Histogram;

[shader("compute")]
[numthreads(256, 1, 1)]
void rangeHistogram(uint3 tid : SV_DispatchThreadID)
{
    uint uw = 0, uh = 0;
    g_Histogram.GetDimensions(uw, uh);

    int width = int(uw);
    int height = int(uh);
    int col = int(tid.x);
    if (col >= width)
        return;

    int columnsPerBin = width / g_Params.numBins;
    int bin = col / columnsPerBin;
    float binLo = float(bin) * g_Params.maxRange / float(g_Params.numBins);
    float binHi = float(bin + 1) * g_Params.maxRange / float(g_Params.numBins);

    // Only the first Counts[0] entries hold a return. Running to maxPoints
    // instead would count entries the sweep never wrote.
    int valid = min(g_Counts[0], g_Params.maxPoints);

    int tally = 0;
    for (int i = 0; i < valid; ++i)
    {
        float px = g_Coordinates[i];
        float py = g_Coordinates[i + g_Params.maxPoints];
        float pz = g_Coordinates[i + 2 * g_Params.maxPoints];
        float range = sqrt(px * px + py * py + pz * pz);
        if (range >= binLo && range < binHi)
            ++tally;
    }

    float fraction = min(1.0, float(tally) / max(1.0, g_Params.maxCount));
    int barTop = height - int(fraction * float(height) + 0.5);

    // A blank column at the right of each bin, so neighbouring bars stay apart.
    bool gap = (col % columnsPerBin) == columnsPerBin - 1;

    float4 barColour = float4(90.0 / 255.0, 170.0 / 255.0, 1.0, 1.0);
    float4 background = float4(18.0 / 255.0, 18.0 / 255.0, 22.0 / 255.0, 1.0);

    for (int row = 0; row < height; ++row)
        g_Histogram[uint2(col, row)] = (!gap && row >= barTop) ? barColour : background;
}
// [/snippet:histogram-slang-kernel]
