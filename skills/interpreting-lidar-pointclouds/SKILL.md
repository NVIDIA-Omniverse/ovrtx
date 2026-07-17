---
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
name: interpreting-lidar-pointclouds
description: >
  Interpreting already-read lidar PointCloud tensors: channel meanings, units, valid
  point ranges, coordinate-frame implications, flags, IDs, normals, velocity, and
  visualization values. Use reading-sensor-pointclouds when the user needs to map or
  fetch the tensors first.
license: LicenseRef-NvidiaProprietary
version: "0.3.0"
author: NVIDIA ovrtx
tags:
  - ovrtx
  - lidar
  - pointclouds
tools:
  - Read
  - Grep
---

# Interpreting Lidar PointClouds

## When to Use

Use this skill when the user asks what already-read lidar Coordinates, Intensity, TimeOffsetNs, Flags, IDs, normals, velocity, or other PointCloud tensors mean. Use `reading-sensor-pointclouds` instead when the user needs map/read code to obtain the tensors.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Lidar channel names and tensor values or summaries already available to the caller.
- Authored lidar settings that affect interpretation, especially `elementsCoordsType`, `outputFrameOfReference`, and `includeInvalidPoints`.
- Validity context: `Counts`, `Flags`, requested visualization, and whether invalid points should be included or filtered.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Start from tensors the caller has already read, or a conceptual question about channel meaning. Use `reading-sensor-pointclouds` if the user needs code to access the tensors.
- Use `configuring-lidar-sensors` when the requested channel is missing because it was not authored in the lidar `PointCloud` RenderVar.

## Instructions

1. Identify the lidar channels being interpreted and the settings that define their coordinate frame, units, and validity behavior.
2. Read the matching interpretation source snippet before explaining channel behavior or visualization choices.
3. Use `Counts[0]` for tensor bounds and `Flags` bit tests for per-point validity when invalid points may be present.
4. Explain channel meaning without adding mapping boilerplate unless the user also asks how to read the tensors.
5. Combine configuration, reading, and interpretation skills only when the user asks for an end-to-end sensor workflow.
6. When changing code, run the narrow docs test or example that owns the snippet whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

Lidar `PointCloud` output is a composite render var with per-point tensors. Use `Counts[0]` to bound the delivered point entries before interpreting any channel, and use the `Flags` `VALID` bit for per-entry validity when invalid points may be present.

> **Source:** `examples/python/lidar/main.py` snippet `read-lidar-pointcloud`
> **Source:** `examples/c/lidar/main.cpp` snippet `read-lidar-pointcloud`

The lidar examples demonstrate a minimal interpretation path: read `Coordinates`, `Counts`, `Intensity`, and `TimeOffsetNs`, slice each per-point tensor to the valid range, and summarize or visualize the result.

## Channels

These are the available lidar `PointCloud` channels from `omni.sensors.nv.lidar`.

| Channel | Type / Shape | Unit | Meaning |
|---|---|---|---|
| `Counts` | `int32` scalar | points | Model-delivered point entry count; use it to bound every per-point tensor. With default invalid-point dropping this is the valid point count, but `includeInvalidPoints = true` can preserve invalid entries inside the range. |
| `Coordinates` | `float` 2D, `3 x N` | m, rad | Point coordinates. Representation is controlled by `elementsCoordsType`: Cartesian positions or spherical components. Frame is controlled by `outputFrameOfReference`. |
| `Intensity` | `float` 1D, `N` | unitless | Processed return strength, normalized by the lidar intensity processing mode. Range depends on scaling and mapping attribute, base is [0,1] |
| `TimeOffsetNs` | `int32` 1D, `N` | ns | Per-point time offset relative to the sensor frame timestamp. |
| `Flags` | `uint8` 1D, `N` | unitless | Model-delivered point status flags. `VALID` (`1 << 6`, `0x40`) marks a valid point. Lidar also uses `FLAG_7` (`1 << 5`, `0x20`) to mark that the point starts a new scan. |
| `EmitterId` | `uint32` 1D, `N` | unitless | Internal emitter or laser index in the emitter state array. |
| `ChannelId` | `uint32` 1D, `N` | unitless | Detector/channel index. This can differ from emitter index for complex channel configurations. |
| `TickId` | `uint32` 1D, `N` | unitless | Tick or scan-step index for the hit. |
| `EchoId` | `uint8` 1D, `N` | unitless | Return index for multi-echo lidar beams. |
| `TickState` | `uint8` 1D, `N` | unitless | Active scan pattern state for the tick that produced the point. |
| `MaterialId` | `uint32` 1D, `N` | unitless | Encoded nonvisual material ID of the hit surface. |
| `ObjectId` | `uint32` 2D, `N x 4` | unitless | 128-bit stable object ID for the hit object, packed as four `uint32` values per point. |
| `HitNormal` | `float` 2D, `N x 3` | unitless | Surface normal at the hit point, in the configured output frame. |
| `Velocity` | `float` 2D, `N x 3` | m/s | Velocity vector at the hit point. |

The model auto-enables `Counts` and `Flags`, and they are delivered as ordinary `PointCloud` channel tensors. Other channels are present only when requested and supported by the sensor configuration.

## Validity

Within the first `Counts[0]` entries, a point is valid when `(Flags[i] & VALID) != 0`. A point is invalid when that bit is clear. Do not compare `Flags[i] == VALID`, because lidar can set additional bits such as `FLAG_7` on the same point.

With the default `omni:sensor:Core:includeInvalidPoints = false`, invalid lidar returns are dropped before output, so entries up to `Counts[0]` are expected to be valid. With `includeInvalidPoints = true`, invalid returns are preserved; filter by `Flags` before using channels such as `Coordinates`, `Intensity`, `HitNormal`, or `Velocity` as real returns.

## Interpretation Notes

- `Coordinates` may be Cartesian or spherical. Check the authored `elementsCoordsType` before treating components as XYZ.
- Lidar sensor-frame output is often easiest for sensor algorithms and visualization in sensor coordinates; world-frame output is useful for scene-level fusion.
- `Intensity` is processing-mode dependent, so compare values only across runs with compatible lidar intensity settings and materials.
- `TimeOffsetNs` matters for scanning sensors because different points in one reported frame can come from different firing times.
- `EmitterId`, `ChannelId`, `TickId`, `EchoId`, and `TickState` are useful for reconstructing scan pattern behavior or filtering by beam/return.
- `MaterialId`, `ObjectId`, `HitNormal`, and `Velocity` are richer attribution channels and may need additional sensor/material settings.
- Use `Counts` for tensor bounds and `Flags` for per-point validity; these are different concepts when invalid points are included.

## Visualization

> **Source:** `examples/python/lidar/main.py` snippet `intensity-colors`
> **Source:** `examples/python/lidar/main.py` snippet `log-lidar-points`

Coloring by `Intensity` is a useful default for public examples. For debugging scan timing, color by `TimeOffsetNs`; for material validation, color or group by `MaterialId`.

## Related Skills

- `reading-sensor-pointclouds` for mapping and slicing composite PointCloud tensors.
- `configuring-lidar-sensors` for authoring lidar output channels.
- `nonvisual-materials` for interpreting `MaterialId` values.

## Troubleshooting

- If source snippets do not cover the requested variant, add or update a focused docs test or example before documenting the new pattern.
- If behavior differs between Python and C/C++, prefer the language-specific snippet and call out the difference explicitly.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
