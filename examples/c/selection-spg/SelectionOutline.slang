// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.


// [snippet:selection-spg-outline-kernel]
struct Params
{
    int width;
    int shape; // Base shape; groups 2 and 3 rotate to the next shapes (circle, square, diamond).
    float fillAlpha;
    int dashPeriod;
    int hatchSpacing;
    int hatchLineWidth;
    float hiddenFillAlpha;
    int padding;
};
[[vk::binding(0, 1)]] ParameterBlock<Params> g_Params;
[[vk::binding(1, 1)]] Texture2D<float4> g_Color;
[[vk::binding(2, 1)]] Texture2D<uint4> g_SelectionState;
[[vk::binding(3, 1)]] RWTexture2D<float4> g_Result;

// All style choices live here or in the node's USD inputs.
float3 groupColor(uint group)
{
    return group == 3 ? float3(1.0, 0.55, 0.05) :
           group == 2 ? float3(0.85, 0.25, 1.0) : float3(0.0, 0.85, 1.0);
}

// Expand the mask with the requested shape and carry the nearest seed's group and visibility.
// Stable loop order breaks equal-distance ties.
uint4 nearestSelection(int2 pixel, int2 extent, uint4 center)
{
    const int radius = max(0, g_Params.width);
    int4 bestDistance = int4(0x7FFFFFFF);
    uint4 nearest = 0;
    // Interior samples do not need expansion; search only the background channels.
    const bool4 background = (center & 0xFF) == 0;
    for (int y = -radius; y <= radius; ++y)
    {
        for (int x = -radius; x <= radius; ++x)
        {
            const int2 offset = int2(x, y);
            const int2 p = pixel + offset;
            if (any(p < 0) || any(p >= extent))
                continue;
            // Rank eligible seeds in one metric, even when their stroke shapes differ.
            const int distance = x * x + y * y;
            if (!any(background & (distance < bestDistance)))
                continue;
            // One texture read and neighborhood walk serve all four coverage channels.
            const uint4 states = g_SelectionState.Load(int3(p, 0));
            for (uint sample = 0; sample < 4; ++sample)
            {
                const uint group = states[sample] & 0xFF;
                // Test each seed's style before choosing it: a farther, wider stroke can still reach us.
                const int strokeRadius = group == 2 ? max(1, radius / 2) : radius;
                const int shape = (g_Params.shape + (group == 2 ? 1 : group == 3 ? 2 : 0)) % 3;
                const int shapeDistance = shape == 1 ? max(abs(x), abs(y)) :
                                          shape == 2 ? abs(x) + abs(y) : distance;
                const int limit = shape == 0 ? strokeRadius * strokeRadius : strokeRadius;
                if (background[sample] && distance < bestDistance[sample] && group != 0 && shapeDistance <= limit)
                {
                    nearest[sample] = states[sample];
                    bestDistance[sample] = distance;
                }
            }
        }
    }
    return nearest;
}

// Different groups have a white separator; objects in the same group form one mask.
bool4 groupBoundary(int2 pixel, int2 extent, uint4 states)
{
    const uint4 groups = states & 0xFF;
    bool4 boundary = false;
    for (int y = -1; y <= 1; ++y)
    {
        for (int x = -1; x <= 1; ++x)
        {
            const int2 p = pixel + int2(x, y);
            if (any(p < 0) || any(p >= extent))
                continue;
            // All four coverage channels share the same neighborhood texture read.
            const uint4 other = g_SelectionState.Load(int3(p, 0)) & 0xFF;
            for (uint sample = 0; sample < 4; ++sample)
            {
                boundary[sample] = boundary[sample] ||
                    (groups[sample] != 0 && other[sample] != 0 && other[sample] != groups[sample]);
            }
        }
    }
    return boundary;
}

// Share a conservative tile occupancy test so empty image regions skip the expensive neighborhood search.
groupshared uint tileHasSelection;

// Composite each coverage sample independently. Stroke visibility follows its selected seed,
// so an unselected surface underneath an expanded stroke does not reclassify that stroke.
[shader("compute")]
[numthreads(16, 16, 1)]
void selectionOutline(uint3 tid : SV_DispatchThreadID, uint3 groupId : SV_GroupID, uint threadIndex : SV_GroupIndex)
{
    uint width, height;
    g_Color.GetDimensions(width, height);
    // Include the outline halo and the one-pixel separator neighborhood. Every thread participates
    // in both barriers, including threads outside the image in a partial edge workgroup.
    const int radius = max(1, g_Params.width);
    const int tileSize = 16 + 2 * radius;
    const int2 tileOrigin = int2(groupId.xy) * 16 - radius;
    if (threadIndex == 0)
        tileHasSelection = 0;
    GroupMemoryBarrierWithGroupSync();
    bool hasSelection = false;
    for (uint i = threadIndex; i < uint(tileSize * tileSize); i += 256)
    {
        const int2 p = tileOrigin + int2(int(i) % tileSize, int(i) / tileSize);
        if (all(p >= 0) && all(p < int2(width, height)))
            hasSelection = hasSelection || any((g_SelectionState.Load(int3(p, 0)) & 0xFF) != 0);
    }
    if (hasSelection)
        InterlockedOr(tileHasSelection, 1u);
    GroupMemoryBarrierWithGroupSync();
    if (tid.x >= width || tid.y >= height)
        return;
    if (tileHasSelection == 0)
    {
        g_Result[tid.xy] = g_Color.Load(int3(tid.xy, 0));
        return;
    }

    const int2 pixel = int2(tid.xy);
    const int2 extent = int2(width, height);
    const uint4 states = g_SelectionState.Load(int3(pixel, 0));
    uint4 seeds = 0;
    if (g_Params.width > 0 && any((states & 0xFF) == 0))
        seeds = nearestSelection(pixel, extent, states);
    bool4 boundaries = false;
    if (g_Params.width > 0 && any((states & 0xFF) != 0))
        boundaries = groupBoundary(pixel, extent, states);
    const uint period = uint(max(1, g_Params.dashPeriod));
    const bool dash = ((tid.x + tid.y) % period) < ((period + 1) / 2);
    // Cross two screen-space diagonal line families; use bounded residues to avoid unsigned subtraction wrap.
    const uint spacing = uint(clamp(g_Params.hatchSpacing, 1, 4096));
    const uint lineWidth = uint(clamp(g_Params.hatchLineWidth, 0, int(spacing)));
    const uint x = tid.x % spacing;
    const uint y = tid.y % spacing;
    const bool stripe = ((x + y) % spacing) < lineWidth;
    const bool hatch = stripe || ((x + spacing - y) % spacing) < lineWidth;
    // Group 1 uses a regular dot lattice instead of crossed lines in hidden interiors.
    // Reuse hatch spacing/line width as dot spacing/radius; zero width disables both patterns.
    const int2 dotOffset = int2(x, y) - int(spacing / 2);
    const bool stipple = lineWidth > 0 && dotOffset.x * dotOffset.x + dotOffset.y * dotOffset.y <= int(lineWidth * lineWidth);
    float4 overlay = 0; // Premultiplied RGB and alpha, accumulated over coverage samples.

    for (uint sample = 0; sample < 4; ++sample)
    {
        const uint state = states[sample];
        const uint group = state & 0xFF;
        if (group == 0)
        {
            const uint seed = seeds[sample];
            if ((seed & 0xFF) != 0 && ((seed & 0x100) != 0 || dash))
                overlay += float4(groupColor(seed & 0xFF), 1.0);
        }
        else if (boundaries[sample] &&
                 ((state & 0x100) != 0 || dash))
        {
            overlay += float4(1.0);
        }
        else
        {
            // Group 1 has solid fill, group 2 only an outline, and group 3 diagonal stripes.
            // Hidden group 1 uses dots, group 3 single hatching, and the other groups crossed hatching.
            const float visibleAlpha = group == 2 ? 0.0 :
                                       group == 3 ? (stripe ? saturate(g_Params.fillAlpha) : 0.0) :
                                       saturate(g_Params.fillAlpha);
            const bool hiddenPattern = group == 1 ? stipple : group == 3 ? stripe : hatch;
            const float alpha = (state & 0x100) != 0 ? visibleAlpha :
                                hiddenPattern ? saturate(g_Params.hiddenFillAlpha) : 0.0;
            overlay += float4(groupColor(group) * alpha, alpha);
        }
    }

    overlay *= 0.25;
    float4 color = g_Color.Load(int3(pixel, 0));
    color.rgb = color.rgb * (1.0 - overlay.a) + overlay.rgb;
    g_Result[tid.xy] = color;
}
// [/snippet:selection-spg-outline-kernel]
