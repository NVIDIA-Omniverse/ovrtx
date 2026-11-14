---
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
name: configuring-lidar-sensors
description: >
  Authoring and configuring OmniLidar sensor prims and lidar PointCloud render outputs.
  Use when user asks to create a lidar scene, configure an OmniLidar prim, choose lidar
  output frame/coordinate behavior, or request lidar PointCloud channels.
license: CC-BY-4.0 AND Apache-2.0
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

Use `OmniSensorGenericLidarCoreAPI` for the Lidar generic core model. Add emitter-state API schemas only when authoring custom firing patterns with explicit emitter state arrays.

In Z-up scenes, keep the physical scene Z-up and rotate the lidar prim so that its local `-Z`, the prim's forward direction, points along the intended forward direction with `+Y` up; the lidar example authors `xformOp:rotateXYZ = (90, 0, -90)` to look along world `+X`, and the delivered points are expressed in the output's sensor frame, `+X` forward. Avoid changing the output frame just to satisfy visualization; choose the frame based on the data contract the application needs.

## Output Attributes

These attributes, among others, live on the lidar prim with the `omni:sensor:Core:` prefix.

| Attribute | Values / Shape | Use |
|---|---|---|
| `elementsCoordsType` | `CARTESIAN`, `SPHERICAL` | Coordinate representation for basic output elements. |
| `outputMotionCompensationState` | `NONCOMPENSATED`, `COMPENSATED` | Motion compensation state for `Coordinates`, `HitNormal` and `Velocity` (see PointCloud Render Output). |
| `outputFrameOfReference` | `SENSOR`, `WORLD`, `CUSTOM` | Frame of reference for `Coordinates`; `HitNormal` and `Velocity` are rotated into it too (see PointCloud Render Output). Prefer `SENSOR` when downstream consumers expect sensor-frame points. |
| `customFrameOfReferenceTrafo` | `[x, y, z, roll, pitch, yaw]` | Custom transform used only with `outputFrameOfReference = CUSTOM`. |
| `includeInvalidPoints` | `true`, `false` | When `false` (the default), the model drops invalid lidar returns before output. When `true`, invalid returns are preserved in the point tensors and consumers must use the `Flags` channel's `VALID` (`0x40`) bit to distinguish valid from invalid entries. |

OmniLidar prims expose many additional sensor, scan, and emitter attributes for range, angular coverage, resolution, timing, firing patterns, and model-specific behavior. Preserve existing attributes when editing a tuned sensor, and author model-specific values from the schema when the example defaults are not enough.

For what every attribute means, its unit and how it relates to the others, read the product reference:
[USD Attributes](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/lidar_core/attributes.html). The exhaustive tables with each attribute's type, default and tokens are generated into
[Sensor API Schemas](https://nvidia-omniverse.github.io/ovrtx/sensors/reference/schemas.html).

## Output Behavior

| Attribute | Default | Use |
|---|---:|---|
| `partialOutputs` | `false` | Accumulate a scan. Set `true` to emit the part covered by each step. |
| `instantLidar` | `false` | Emit a full scan every frame. Useful for simple demonstrations, but not representative of a time-resolved scan. Firing uses the supplied interval's start time, with zero point time offsets. See [instant lidar](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/lidar_core/howto/output_shaping.html#sensors-lidar-core-instant-lidar) for pose and timing details. |

See [output cadence](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/lidar_core/howto/output_shaping.html#sensors-output-shaping-lidar-timing) for the three cadences and what a mid-scan step delivers.

## PointCloud Render Output

### Python example scene

> **Source:** `examples/python/lidar/lidar_example.usda` snippet `configure-lidar-pointcloud-output`

### C example scene

> **Source:** `examples/c/lidar/lidar_example.usda` snippet `configure-lidar-pointcloud-output`

`sourceName = "PointCloud"` is the lidar sensor render output. Request only the channels needed by the consumer to keep memory use down.

Common lidar channels:

| Channel | Meaning |
|---|---|
| `Coordinates` | 3D point coordinates in the configured coordinate representation and output frame. |
| `Intensity` | Reflection intensity per point. |
| `TimeOffsetNs` | Per-point time offset in nanoseconds. |
| `Flags` | Per-point flags. |
| `EmitterId`, `ChannelId`, `TickId`, `EchoId` | Emitter, detector/channel, scan tick, and return identifiers. |
| `MaterialId`, `ObjectId` | Hit material and object identifiers. |
| `HitNormal`, `Velocity` | Unit surface normal at the hit point, and the hit point's velocity relative to the sensor (the sensor's own motion subtracted). |
| `TickState` | Zero-based index of the emitter state that fired the point; on a solid-state sensor all points of a scan carry the state selected for that scan. |
| `Counts` | Delivered point entry count used to bound every per-point tensor. With default invalid-point dropping, it is also the valid-point count. |

Naming a channel in `token[] channels` is what fills it. The Lidar generic core model writes `EmitterId`, `ChannelId`, `TickId`, `EchoId`, `TickState`, `MaterialId` and `ObjectId` for every valid return whenever the RenderVar names them, and computes `HitNormal` and `Velocity` whenever a `PointCloud` RenderVar requests them; no attribute switches any of them on or off. The model applies `outputFrameOfReference` and `outputMotionCompensationState` to those two along with `Coordinates` in every combination, `CUSTOM` with `NONCOMPENSATED` included.

A `PointCloud` output carries exactly the channels its RenderVar's `channels` list names, plus `Counts` and `Flags`, which the model adds on its own; the [channel table](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/lidar_core/outputs.html#sensors-nonvisual-lidar-core-outputs-channels) on the Outputs page lists every channel with its type, shape and unit.

## Troubleshooting

- Output-defining attributes (`elementsCoordsType`, `outputFrameOfReference`, `customFrameOfReferenceTrafo`, `outputMotionCompensationState`, `includeInvalidPoints`) can be edited on a running sensor and apply from the next frame; the frame in flight keeps the old values. With `partialOutputs = false`, the step that completes a scan converts every point of that scan with its own coordinate representation, frame of reference, custom transform and motion compensation state, so an edit made mid-scan applies to the whole delivered scan, points traced before the edit included. See [Configure Lidar Output](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/lidar_core/howto/output_shaping.html#sensors-output-shaping-runtime-changes).
- `scanType` cannot be changed on a running sensor: an update naming the other scanning principle is rejected whole, so author it in USD before loading the scene and recreate the sensor to change it. `rayType` is read when the model is first set up and cannot move between `IDEALIZED` and a beam ray type on a running sensor, so author `rayType` in USD as well and recreate the sensor to change it.
- If a Lidar generic core model sensor produces no output, check the log for an initial parameter-validation error. Correct the parameters on the existing prim and publish the update to initialize the sensor. Typical causes are an emitter-state array that is neither empty nor `numberOfEmitters` long, fire times that decrease or run past one tick period, more distinct `channelId` values across the emitter states than `numberOfChannels`, and a positive `omni:sensor:frameRate` below 0.466 Hz. See [parameter validation](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/lidar_core/attributes.html#sensors-lidar-core-invalid-parameters).
- `PointCloud` contains requested payload channels plus model-added `Counts` and `Flags`. If a downstream reader expects `Intensity` or `TimeOffsetNs`, include those names in `token[] channels`.
- `Counts` defines the delivered range in per-point tensors. Do not iterate over the full tensor allocation.
- If `includeInvalidPoints = true`, `Counts` bounds the delivered entries, but entries inside that range can still be invalid; test the `VALID` (`0x40`) bit, `Flags[i] & 0x40`, before consuming point attributes that require a real return.
- MotionBVH is required for correct lidar motion effects. Without it the lidar still delivers points, each traced from the sensor's pose at the end of its frame against a scene that does not move, and the model logs a warning once, so a non-zero `Counts[0]` does not show that MBVH is on. Static scenes may run without it, but a moving sensor, moving objects or motion compensation need MBVH enabled through the renderer configuration.
- Lidar output frame and visualizer frame are separate concerns. If output is in `SENSOR` frame, configure the visualizer to interpret that frame instead of changing the sensor to `WORLD` unless world-frame output is actually desired.
- The model auto-enables `Flags` and `Counts` even when not requested, and delivers them like ordinary channel tensors.
- A name in `token[] channels` that the model does not recognize is ignored with a warning, not reported as a failure. The rest of the output is produced as usual, so a consumer indexing the result by that name simply will not find it; check the spelling and case against the Outputs page.

## Related Skills

- `reading-render-output` for mapping render variables and composite tensors.
- `reading-sensor-pointclouds` for point-cloud tensor access patterns.
- `interpreting-lidar-pointclouds` for lidar channel units and visualization.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.

Product documentation owns the detail this skill only summarizes:

- [Lidar generic core model](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/lidar_core/index.html) -- ticks, emitters, channels and returns, scan types, delivery cadence; the attribute, how-to, output and tutorial pages hang under it.
- [USD Attributes](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/lidar_core/attributes.html) -- every `omni:sensor:Core:*` attribute's meaning, unit and relations, group by group; the generated [Sensor API Schemas](https://nvidia-omniverse.github.io/ovrtx/sensors/reference/schemas.html) tables carry each attribute's type, default and tokens.
- [Configure Lidar Output](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/lidar_core/howto/output_shaping.html) -- coordinate type, frame of reference and cadence, and how a runtime edit shows up in the delivered params.
- [Configure a Firing Pattern](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/lidar_core/howto/firing_pattern.html) -- emitter states, tick structure, per-emitter azimuth/elevation/fire-time offsets.
- [Outputs](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/lidar_core/outputs.html) -- element type, shape, unit and validity rules for every lidar channel, the params a frame carries, and how scans, frames and steps relate.
- [Sensor Configuration](https://nvidia-omniverse.github.io/ovrtx/sensors/common/sensor_configuration.html) -- the sensor prim, its applied schema and where overrides are authored.
- [Output Configuration](https://nvidia-omniverse.github.io/ovrtx/sensors/common/output_configuration.html) -- RenderProduct and RenderVar wiring, channel requests, and the renderer options a sensor scene depends on.
- [Motion Artifacts](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/lidar_core/howto/motion_artifacts.html) -- motion BVH and motion compensation, and what breaks when only one is set.
- [Troubleshooting](https://nvidia-omniverse.github.io/ovrtx/sensors/troubleshooting/index.html) -- the symptom index with candidate causes, and the by-design limits of the models.
