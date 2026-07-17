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
name: reading-sensor-pointclouds
description: >
  Mapping and reading lidar or radar PointCloud composite render-var tensors. Use
  when user asks how to access PointCloud output data, map Coordinates, Counts,
  Intensity, RCS, RadialVelocityMs, or TimeOffsetNs tensors, slice valid entries, or
  move sensor point clouds through CPU/CUDA memory. For channel meanings and units,
  use the interpreting-lidar-pointclouds or interpreting-radar-pointclouds skills.
license: LicenseRef-NvidiaProprietary
version: "0.3.0"
author: NVIDIA ovrtx
tags:
  - ovrtx
  - sensors
  - pointclouds
tools:
  - Read
  - Grep
---

# Reading Sensor PointClouds

## When to Use

Use this skill when the user asks how to access PointCloud output data, map Coordinates, Counts, Intensity, RCS, RadialVelocityMs, or TimeOffsetNs tensors, slice valid entries, or move sensor point clouds through CPU/CUDA memory. Use an interpreting pointcloud skill instead when the tensors are already available and the question is what their channels mean.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, or both.
- Sensor modality, RenderProduct path, PointCloud RenderVar/output name, and requested tensor channels.
- Mapping target: CPU, linear CUDA memory, or host copy after map.
- Valid-entry handling: `Counts`, `Flags`, desired slice/copy behavior, and whether data must outlive the mapping.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Confirm that the scene already requests a `PointCloud` output; use the lidar or radar configuration skills when the output channel set still needs to be authored.
- Use the modality-specific interpreting skills for channel units, coordinate-frame meaning, validity semantics, or visualization choices.

## Instructions

1. Identify the sensor modality, RenderProduct, PointCloud output, target device, and named tensors to map.
2. Read the matching Python or C/C++ source snippet before writing API usage.
3. Map the composite `PointCloud` output, access tensors by exact channel name, and use `Counts[0]` to bound per-point/per-detection tensors.
4. Handle lifetime by language: in Python the mapping is consumer-owned — a held DLPack consumer view (e.g. a NumPy array) keeps the buffer valid past `unmap`, so lifetime isn't a manual concern; in C, copy data before unmapping if later code needs it. Keep CUDA synchronization aligned with the selected mapping target.
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

Sensor `PointCloud` render vars are composite outputs: mapping one render var exposes one named tensor per channel. `Counts` tensor's content is the number of valid points per tile.

CPU mapping is simplest for examples and printing. GPU mapping is also supported for point-cloud pipelines: Python uses `map(device=ovrtx.Device.CUDA)`, and C uses `OVRTX_MAP_DEVICE_TYPE_CUDA`. GPU-mapped tensors must be consumed as CUDA DLTensors by GPU-aware code, not as host pointers.

## Python

### Lidar PointCloud

> **Source:** `examples/python/lidar/main.py` snippet `read-lidar-pointcloud`

The lidar example maps `PointCloud` to CPU, reads `Coordinates`, `Counts`, `Intensity`, and `TimeOffsetNs`, then copies the valid range out of the mapping for visualization.

### Radar PointCloud

> **Source:** `examples/python/radar/main.py` snippet `read-radar-pointcloud`

The radar example maps `PointCloud` to CPU, reads `Coordinates`, `Counts`, and `RadialVelocityMs`, then slices the valid detections. Approaching radar detections can have negative radial velocity.

## C

### Lidar PointCloud

> **Source:** `examples/c/lidar/main.cpp` snippet `step-lidar-pointcloud`
> **Source:** `examples/c/lidar/main.cpp` snippet `read-lidar-pointcloud`

The lidar C example fetches the stepped render results, finds `PointCloud`, maps it to CPU, reads named tensors, and unmaps after computing summary values.

### Radar PointCloud

> **Source:** `examples/c/radar/main.cpp` snippet `step-radar-pointcloud`
> **Source:** `examples/c/radar/main.cpp` snippet `read-radar-pointcloud`

The radar C example uses the same map/read/unmap flow and additionally reads radar-specific `RCS` and `RadialVelocityMs` channels.

## Common Channel Notes

| Channel | Meaning |
|---|---|
| `Counts` | Scalar valid point count. Always use it to bound per-point channel access. |
| `Coordinates` | Point coordinates, commonly packed as `3 x N`; transpose or index according to the mapped tensor shape. |
| `Flags` | Model-delivered per-point status flags. |
| `TimeOffsetNs` | Per-point time offset in nanoseconds. |

The model auto-enables `Counts` and `Flags`, and they are delivered as ordinary `PointCloud` channel tensors. Other payload channels must be requested by the sensor `PointCloud` `RenderVar`. There are additional modality specific channels, see `configuring-lidar-sensors` and `configuring-radar-sensors`.

## Troubleshooting

- Do not iterate over the full tensor allocation; only the first `Counts[0]` entries are valid.
- **Lifetime.** In Python the mapping is consumer-owned: a held DLPack consumer view (e.g. a NumPy array) keeps the buffer valid even after `unmap`, so lifetime is not a manual concern — copy only if you need data beyond the last view. In C, mapped tensors are valid until `unmap` — copy before unmapping if the data must outlive it.
- CPU examples can use NumPy or raw host pointers. GPU mappings require DLPack-compatible CUDA consumers or custom CUDA code plus correct unmap synchronization.
- For point-cloud tensors in C, use `OVRTX_MAP_DEVICE_TYPE_CUDA` for linear CUDA memory; `OVRTX_MAP_DEVICE_TYPE_CUDA_ARRAY` is intended for image-style outputs.
- Read channel names exactly as authored in the USDA `PointCloud` `RenderVar`.

## Related Skills

- `reading-render-output` for general render-var mapping, lifetime, and sync rules.
- `configuring-lidar-sensors` and `configuring-radar-sensors` for authoring the `PointCloud` channel set.
- `interpreting-lidar-pointclouds` and `interpreting-radar-pointclouds` for channel-specific units and meaning.

## Related Docs

- `docs/sensors/sensor_outputs.rst` -- conceptual reference for the render variable output format, mapping flow, tensor/param layout, and lifetime rules.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
