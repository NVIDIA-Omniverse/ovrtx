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
name: camera-outputs-rt2
description: >
  Available camera render outputs for Real-Time Path-Tracing (RT2) mode. Use when user
  asks what AOVs/render vars are available, what format or dtype an output has, or how
  to read a specific output like depth, normals, albedo, or distance.
license: LicenseRef-NvidiaProprietary
author: NVIDIA ovrtx
tags:
  - ovrtx
  - rendering
  - camera
tools:
  - Read
  - Grep
---

# Camera Outputs -- Real-Time Path-Tracing (RT2)

## When to Use

Use this skill when the user asks what AOVs/render vars are available, what format or dtype an output has, or how to read a specific output like depth, normals, albedo, or distance.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, USD, or a combination.
- Requested AOV/sourceName, RenderProduct path, and whether the user needs USD authoring, output selection, or readback guidance.
- Expected dtype, shape, channel count, and any known backend limitations for that output.
- Whether extra outputs are acceptable for memory/performance, or only the requested output should be added.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Use `reading-render-output` for the concrete map/read code once the requested camera output is selected.
- Keep this skill scoped to RT2 camera outputs; use sensor skills for lidar/radar PointCloud outputs.

## Instructions

1. Identify the requested camera output and whether the caller needs USD authoring, Python readback, or C readback.
2. Start with `LdrColor` unless the request specifically needs HDR, depth, normals, semantic IDs, or another listed AOV.
3. Add only the requested `RenderVar` entries to the RenderProduct `orderedVars`; each extra output has memory cost.
4. Preserve the documented dtype, shape, and channel count when mapping output tensors.
5. When changing code, run the camera AOV smoke test that owns the output table whenever practical.

## Output Format

- Return the selected `sourceName`, dtype, shape, and readback skill needed for the requested output.
- For code changes, summarize RenderVar/RenderProduct edits and validation run.

## Scripts

This skill has no scripts.

## Limitations

- `DepthSD` currently returns all zeros through the C API.
- The output table is scoped to Real-Time Path-Tracing mode.
- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Default choice

Most applications only need `LdrColor` unless the user specifically requests other outputs (e.g. depth, normals). Do not add extra AOVs by default -- each one has a memory cost.

## Available outputs

The following RenderVar `sourceName` values are available when using Real-Time Path-Tracing mode. Set each as the `sourceName` attribute on a `RenderVar` prim under a `RenderProduct`.

| `sourceName` | Format | Type | NumPy dtype | Shape | Description |
|---|---|---|---|---|---|
| `LdrColor` | RGBA | uint8 | `uint8` | `(H, W, 4)` | Tone-mapped sRGB color. Standard display-ready output. |
| `HdrColor` | RGBA | float16 | `float16` | `(H, W, 4)` | Linear-space HDR color. Use for post-processing and compositing. |
| `NormalSD` | XYZA | float32 | `float32` | `(H, W, 4)` | World-space surface normals. |
| `DepthSD` | Z | float32 | `float32` | `(H, W, 1)` | Unitless depth, mapped from 1 (near clip) to 0 (far clip). **Known bug:** returns all zeros via the C API. |
| `DistanceToCameraSD` | Z | float32 | `float32` | `(H, W, 1)` | Euclidean distance from camera origin to surface, in meters. |
| `DistanceToImagePlaneSD` | Z | float32 | `float32` | `(H, W, 1)` | Perpendicular distance from image plane to surface, in meters. |
| `DiffuseAlbedoSD` | RGBA | uint8 | `uint8` | `(H, W, 4)` | Diffuse surface albedo (base color without lighting). |
| `Camera3dPositionSD` | XYZA | float32 | `float32` | `(H, W, 4)` | Camera-space 3D position of each surface point, in scene units. |
| `SemanticSegmentation` | ID | uint32 | `uint32` | `(H, W, 1)` | Per-pixel semantic ID. Decode `SemanticIdMap` to map IDs to semantic label strings. |
| `SemanticIdMap` | IdentifierMap | uint8 buffer | `uint8` | buffer | Packed metadata buffer mapping semantic IDs to label strings. |

## Python example

> **Source:** `tests/docs/python/test_camera_aovs.py` snippet `doc-camera-aov-smoke-test`

## C example

In C, image DLTensor outputs use channel-last shape `(H, W, C)` with `dtype.lanes = 1`. The `dtype.code` reflects the format kind directly: `kDLUInt` for `LdrColor` / `DiffuseAlbedoSD` / `SemanticSegmentation`, `kDLFloat` for `HdrColor` / `NormalSD` / `DepthSD` / `DistanceToCameraSD` / `DistanceToImagePlaneSD` / `Camera3dPositionSD`. `SemanticIdMap` is a packed `uint8` metadata buffer, not an image.

> **Source:** `tests/docs/c/test_camera_aovs.cpp` snippet `doc-camera-aov-smoke-test-c`

## USD setup

Add each output as a `RenderVar` prim under a `RenderProduct`, referencing it
in `orderedVars`:

> **Source:** `tests/docs/python/test_camera_aovs.py` snippet `doc-camera-aov-usda`

Only include the outputs you need -- there is no requirement to request all of them.

## Related skills

- `reading-render-output` -- how to map and access render var pixel data
- `configuring-lidar-sensors` / `configuring-radar-sensors` for non-camera sensors, and `docs/sensors/configuration.rst` for RenderProduct and RenderVar prim setup
- `stepping-and-rendering` -- stepping the renderer and iterating over results

## Troubleshooting

- If an output is missing from a rendered frame, confirm its `RenderVar` is listed in the parent RenderProduct `orderedVars`.
- If a tensor shape or dtype differs from the table, verify the active render mode and readback path before changing downstream processing.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
