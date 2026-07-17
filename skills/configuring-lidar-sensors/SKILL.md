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
name: configuring-lidar-sensors
description: >
  Authoring and configuring OmniLidar sensor prims and lidar PointCloud render outputs.
  Use when user asks to create a lidar scene, configure an OmniLidar prim, choose lidar
  output frame/coordinate behavior, or request lidar PointCloud channels.
license: LicenseRef-NvidiaProprietary
version: "0.3.0"
author: NVIDIA ovrtx
tags:
  - ovrtx
  - sensors
  - lidar
tools:
  - Read
  - Grep
---

# Configuring Lidar Sensors

## When to Use

Use this skill when the user asks to create a lidar scene, configure an OmniLidar prim, choose lidar output frame/coordinate behavior, or request lidar PointCloud channels.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, USD, or a combination.
- Lidar sensor prim path, pose, frame rate, sensor model attributes, and optional emitter-state requirements.
- RenderProduct path, PointCloud RenderVar path, requested output channels, coordinate representation, and output frame.
- Whether the user needs USD authoring only or an end-to-end example that steps and reads the configured output.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Use `reading-sensor-pointclouds` for map/read code after the configured scene renders.
- Use `interpreting-lidar-pointclouds` for channel units, validity, and visualization semantics.

## Instructions

1. Identify the lidar prim, RenderProduct, PointCloud RenderVar, requested channels, coordinate behavior, and output frame.
2. Read the matching USD, Python, or C/C++ source snippet before writing API usage.
3. Author the `OmniLidar` prim and `PointCloud` RenderVar channel set explicitly; do not imply channels are available unless requested or auto-enabled.
4. Combine configuration, reading, and interpretation skills only when the user asks for an end-to-end lidar workflow.
5. When changing code, run the narrow docs test or example that owns the snippet whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

An ovrtx lidar setup has two parts:

- An `OmniLidar` prim with `OmniSensorGenericLidarCoreAPI` that defines the sensor model, pose, frame rate, and output behavior.
- A `RenderProduct` pointing at that lidar plus a `PointCloud` `RenderVar` that selects the lidar output channels to expose.

The same USDA scene pattern is used from Python and C; the language-specific code only loads the scene, steps the render product, and maps the output.

## Minimal Lidar Prim

### Python example scene

> **Source:** `examples/python/lidar/lidar_example.usda` snippet `configure-lidar-sensor`

### C example scene

> **Source:** `examples/c/lidar/lidar_example.usda` snippet `configure-lidar-sensor`

Use `OmniSensorGenericLidarCoreAPI` for the generic lidar model. Add emitter-state API schemas only when authoring custom firing patterns with explicit emitter state arrays.

In Z-up scenes, keep the physical scene Z-up and rotate the lidar prim so sensor `+X` points along the intended forward direction. Avoid changing the output frame just to satisfy visualization; choose the frame based on the data contract the application needs.

## Output Attributes

These attributes, among others, live on the lidar prim with the `omni:sensor:Core:` prefix.

| Attribute | Values / Shape | Use |
|---|---|---|
| `elementsCoordsType` | `CARTESIAN`, `SPHERICAL` | Coordinate representation for basic output elements. |
| `outputMotionCompensationState` | `NONCOMPENSATED`, `COMPENSATED` | Motion compensation state for all outputs, including auxiliary data. |
| `outputFrameOfReference` | `SENSOR`, `WORLD`, `CUSTOM` | Frame of reference for all outputs. Prefer `SENSOR` when downstream consumers expect sensor-frame points. |
| `customFrameOfReferenceTrafo` | `[x, y, z, roll, pitch, yaw]` | Custom transform used only with `outputFrameOfReference = CUSTOM`. |
| `includeInvalidPoints` | `true`, `false` | When `false`, the model drops invalid lidar returns before output. When `true`, invalid returns are preserved in the point tensors and consumers must use the `Flags` channel's `VALID` bit to distinguish valid from invalid entries. |

OmniLidar prims expose many additional sensor, scan, and emitter attributes for range, angular coverage, resolution, timing, firing patterns, and model-specific behavior. Preserve existing attributes when editing a tuned sensor, and author model-specific values from the schema when the example defaults are not enough.

For the full schema-derived attribute list, read `schemas/omni_sensors/schema.usda`.

## Output Behavior

| Attribute | Default | Use |
|---|---:|---|
| `partialOutputs` | `true` | Emit the part of the scan covered by the current step. If `false`, output only when the full scan is complete. |
| `instantLidar` | `false` | Emit a full scan every frame. Useful for simple demonstrations, but not representative of a time-resolved scan. |

## PointCloud Render Output

### Python example scene

> **Source:** `examples/python/lidar/lidar_example.usda` snippet `configure-lidar-pointcloud-output`

### C example scene

> **Source:** `examples/c/lidar/lidar_example.usda` snippet `configure-lidar-pointcloud-output`

For public ovrtx examples, prefer `sourceName = "PointCloud"` when the application only needs selected point-cloud channels. Request only the channels needed by the consumer to keep memory use down.

Common lidar channels:

| Channel | Meaning |
|---|---|
| `Coordinates` | 3D point coordinates in the configured coordinate representation and output frame. |
| `Intensity` | Reflection intensity per point. |
| `TimeOffsetNs` | Per-point time offset in nanoseconds. |
| `Flags` | Per-point flags. |
| `EmitterId`, `ChannelId`, `TickId`, `EchoId` | Emitter, detector/channel, scan tick, and return identifiers. |
| `MaterialId`, `ObjectId` | Hit material and object identifiers. |
| `HitNormal`, `Velocity` | Surface normal and velocity at the hit point. |
| `TickState` | State of the scan tick. |
| `Counts` | ovrtx examples use this as the valid point count before reading per-point tensors. |

Use `GenericModelOutput` only when a consumer specifically needs the traditional packed sensor model output. For composite tensor workflows, `PointCloud` is the clearer default.

## Troubleshooting

- Output-defining attributes are not intended for runtime mutation; author them in USD before loading the scene.
- `PointCloud` only contains requested channels. If a downstream reader expects `Intensity` or `TimeOffsetNs`, include those names in `string[] channels`.
- `Counts` defines the valid range in per-point tensors. Do not iterate over the full tensor allocation.
- If `includeInvalidPoints = true`, `Counts` bounds the delivered entries, but entries inside that range can still be invalid; test `Flags[i] & VALID` before consuming point attributes that require a real return.
- MotionBVH is required for correct lidar motion effects. Static scenes may run without it, but moving objects or motion compensation need MBVH enabled through the renderer configuration.
- Lidar output frame and visualizer frame are separate concerns. If output is in `SENSOR` frame, configure the visualizer to interpret that frame instead of changing the sensor to `WORLD` unless world-frame output is actually desired.
- The model auto-enables `Flags` and `Counts` even when not requested, and delivers them like ordinary channel tensors.

## Related Skills

- `reading-render-output` for mapping render variables and composite tensors.
- `reading-sensor-pointclouds` for point-cloud tensor access patterns.
- `interpreting-lidar-pointclouds` for lidar channel units and visualization.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
