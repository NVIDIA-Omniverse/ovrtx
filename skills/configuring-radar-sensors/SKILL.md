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
name: configuring-radar-sensors
description: >
  Authoring and configuring OmniRadar sensor prims and radar PointCloud render outputs.
  Use when user asks to create a radar scene, configure an OmniRadar prim, choose radar
  output frame/coordinate behavior, configure radar scan outputs, or request radar
  PointCloud channels.
license: LicenseRef-NvidiaProprietary
version: "0.3.0"
author: NVIDIA ovrtx
tags:
  - ovrtx
  - sensors
  - radar
tools:
  - Read
  - Grep
---

# Configuring Radar Sensors

## When to Use

Use this skill when the user asks to create a radar scene, configure an OmniRadar prim, choose radar output frame/coordinate behavior, configure radar scan outputs, or request radar PointCloud channels.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, USD, or a combination.
- Radar sensor prim path, pose, frame rate, scan configuration, and output format attributes.
- RenderProduct path, PointCloud RenderVar path, requested output channels, coordinate representation, and output frame.
- Whether the user needs USD authoring only or an end-to-end example that steps and reads the configured output.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Use `reading-sensor-pointclouds` for map/read code after the configured scene renders.
- Use `interpreting-radar-pointclouds` for channel units, signed radial velocity, validity, and visualization semantics.

## Instructions

1. Identify the radar prim, RenderProduct, PointCloud RenderVar, requested channels, scan behavior, coordinate behavior, and output frame.
2. Read the matching USD, Python, or C/C++ source snippet before writing API usage.
3. Author the `OmniRadar` prim and `PointCloud` RenderVar channel set explicitly; do not imply channels are available unless requested or auto-enabled.
4. Combine configuration, reading, and interpretation skills only when the user asks for an end-to-end radar workflow.
5. When changing code, run the narrow docs test or example that owns the snippet whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

An ovrtx radar setup has two parts:

- An `OmniRadar` prim with `OmniSensorGenericRadarWpmDmatAPI` that defines the sensor model, pose, frame rate, and output format.
- A `RenderProduct` pointing at that radar plus a `PointCloud` `RenderVar` that selects the radar output channels to expose.

The same USDA scene pattern is used from Python and C; the language-specific code only loads the scene, steps the render product, and maps the output.

## Minimal Radar Prim

### Python example scene

> **Source:** `examples/python/radar/radar_example.usda` snippet `configure-radar-sensor`

### C example scene

> **Source:** `examples/c/radar/radar_example.usda` snippet `configure-radar-sensor`

Use `OmniSensorGenericRadarWpmDmatAPI` for the generic WPM DMAT radar model. The schema automatically includes scan configuration `s001`; apply `OmniSensorGenericRadarWpmDmatScanCfgAPI:s002`, `s003`, and so on only when authoring additional scan patterns.

In Z-up scenes, keep the physical scene Z-up and rotate the radar prim so sensor `+X` points along the intended forward direction. Prefer authoring that transform in USD instead of relying on renderer settings that change the coordinate frame globally.

## Output Attributes

These output-defining attributes, among others, live on the radar prim with the `omni:sensor:WpmDmat:` prefix.

| Attribute | Values / Shape | Use |
|---|---|---|
| `auxOutputType` | `NONE`, `BASIC`, `EXTRA`, `FULL` | Controls auxiliary data in `GenericModelOutput`. It does not add `PointCloud` channels. |
| `elementsCoordsType` | `CARTESIAN`, `SPHERICAL` | Coordinate representation for detection coordinates. |
| `outputFrameOfReference` | `SENSOR`, `WORLD`, `CUSTOM` | Frame of reference for outputs. Prefer `SENSOR` when downstream consumers expect sensor-frame detections. |
| `customFrameOfReferenceTrafo` | `[x, y, z, roll, pitch, yaw]` | Custom transform used only with `outputFrameOfReference = CUSTOM`. |

OmniRadar prims expose many additional WPM DMAT sensor and scan attributes for wavelength, ray depth, CFAR behavior, range/velocity/angular bins, noise, RCS tuning, and antenna/aperture configuration. Preserve existing attributes when editing a tuned sensor, and author model-specific values from the schema.

For the full schema-derived attribute list, read `schemas/omni_sensors/schema.usda`.

## Scan Configuration

The default scan is `s001`, and scan attributes use the `omni:sensor:WpmDmat:scan:<scanName>:` prefix. Use scan attributes such as max range, angular limits, resolution, bin counts, CFAR settings, noise settings, and RCS tuning to match the target radar model.

For concise examples, keep one scan unless the behavior being demonstrated requires near/far or otherwise distinct scan patterns.

## PointCloud Render Output

### Python example scene

> **Source:** `examples/python/radar/radar_example.usda` snippet `configure-radar-pointcloud-output`

### C example scene

> **Source:** `examples/c/radar/radar_example.usda` snippet `configure-radar-pointcloud-output`

For public ovrtx examples, prefer `sourceName = "PointCloud"` when the application only needs selected detection channels. Request only the channels needed by the consumer to keep memory use down.

Common radar channels:

| Channel | Meaning |
|---|---|
| `Coordinates` | 3D detection coordinates in the configured coordinate representation and output frame. |
| `RCS` | Radar cross section in dBsm. |
| `RadialVelocityMs` | Doppler radial velocity in meters per second. Approaching objects can have negative velocity, so use magnitude when checking only for motion. |
| `TimeOffsetNs` | Per-detection time offset in nanoseconds relative to scan start. |
| `Flags` | Model-delivered per-detection status flags. The model auto-enables this channel even when it is not requested explicitly. |
| `Counts` | Model-delivered valid detection count used before reading per-point tensors. The model auto-enables this channel even when it is not requested explicitly. |

Use `GenericModelOutput` only when a consumer specifically needs the traditional packed radar output. For composite tensor workflows, `PointCloud` is the clearer default.

## Troubleshooting

- Output-defining attributes are not intended for runtime mutation; author them in USD before loading the scene.
- `Counts` defines the valid range in per-point tensors. Do not iterate over the full tensor allocation.
- `PointCloud` only needs requested payload channels; the model auto-enables `Counts` and `Flags` and delivers them like ordinary channel tensors.
- `auxOutputType` affects `GenericModelOutput`, not `PointCloud`.
- Radar output frame and visualizer frame are separate concerns. If output is in `SENSOR` frame, configure the visualizer to interpret that frame instead of changing the sensor to `WORLD` unless world-frame output is actually desired.

## Related Skills

- `reading-render-output` for mapping render variables and composite tensors.
- `reading-sensor-pointclouds` for point-cloud tensor access patterns.
- `interpreting-radar-pointclouds` for radar channel units and visualization.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
