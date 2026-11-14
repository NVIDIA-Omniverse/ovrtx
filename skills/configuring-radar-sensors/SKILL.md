---
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
name: configuring-radar-sensors
description: >
  Authoring and configuring OmniRadar sensor prims and radar PointCloud render outputs.
  Use when user asks to create a radar scene, configure an OmniRadar prim, choose radar
  output frame/coordinate behavior, configure radar scan outputs, or request radar
  PointCloud channels.
license: CC-BY-4.0 AND Apache-2.0
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

Use `OmniSensorGenericRadarWpmDmatAPI` for the Radar generic wpmDmat model. The schema automatically includes scan configuration `s001`; apply `OmniSensorGenericRadarWpmDmatScanCfgAPI:s002`, `s003`, and so on only when authoring additional scan patterns.

In Z-up scenes, keep the stage Z-up and rotate the radar prim so that its local `-Z`, the prim's forward axis, points along the intended forward direction; the examples author `xformOp:rotateXYZ = (90, 0, -90)` to look along world `+X`, and a point straight ahead then comes back on the output's `+X` axis. Author that transform on the prim in USD.

## Output Attributes

These output-defining attributes, among others, live on the radar prim with the `omni:sensor:WpmDmat:` prefix.

| Attribute | Values / Shape | Use |
|---|---|---|
| `elementsCoordsType` | `CARTESIAN`, `SPHERICAL` | Coordinate representation for detection coordinates. |
| `outputFrameOfReference` | `SENSOR`, `WORLD`, `CUSTOM` | Frame of reference for detection coordinates. Doppler remains sensor-relative and scan limits remain sensor-frame. Prefer `SENSOR` when downstream consumers expect sensor-frame detections. |
| `customFrameOfReferenceTrafo` | `[x, y, z, roll, pitch, yaw]` | Custom transform used only with `outputFrameOfReference = CUSTOM`. |

OmniRadar prims expose many additional sensor-level and per-scan attributes for wavelength, ray depth, CFAR behavior, range/velocity/angular bins, noise, RCS tuning, and antenna/aperture configuration. Preserve existing attributes when editing a tuned sensor, and author model-specific values from the schema.

For the full attribute list with types, defaults and tokens, read the product reference:
[Radar Attributes](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/attributes.html).

## Scan Configuration

The default scan is `s001`, and scan attributes use the `omni:sensor:WpmDmat:scan:<scanName>:` prefix. Use scan attributes such as max range, angular limits, resolution, bin counts, CFAR settings, noise settings, and RCS tuning to match the target radar model.

For concise examples, keep one scan unless the behavior being demonstrated requires near/far or otherwise distinct scan patterns.

The model cycles through its scan configurations in lexicographic instance order, one per firing. A step without a radar acquisition leaves the pending scan (the one whose turn is next) and its ambiguity entry unchanged, and publishes no radar PointCloud frame. A frame carries at most one scan, and a step longer than the scan period returns several frames, so inspect every returned frame. A scan's `timeOffsetUsec` delays its acquisition after its scan time, in microseconds, and `timestampNs` reports the delayed time (see [the frame rate](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/attributes.html#sensors-radar-frame-rate)). A published scan with no detections has `Counts[0] == 0` and still carries scan metadata. Read `scanIdx` from every published scan, including empty scans. See [Run More Than One Scan Pattern](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/howto/scan_configurations.html).

## PointCloud Render Output

### Python example scene

> **Source:** `examples/python/radar/radar_example.usda` snippet `configure-radar-pointcloud-output`

### C example scene

> **Source:** `examples/c/radar/radar_example.usda` snippet `configure-radar-pointcloud-output`

`sourceName = "PointCloud"` is the radar sensor render output. Request only the channels needed by the consumer to keep memory use down.

Common radar channels:

| Channel | Meaning |
|---|---|
| `Coordinates` | 3D detection coordinates in the configured coordinate representation and output frame. |
| `RCS` | Radar cross section in dBsm. Request it when the consumer needs to inspect detection strength or material response. |
| `RadialVelocityMs` | Doppler radial velocity in meters per second. Approaching objects can have negative velocity, so use magnitude when checking only for motion. |
| `TimeOffsetNs` | Time offset of the detection within the scan, in nanoseconds. It is `0` for every detection by design, because the model simulates each scan at one instant, so a radar frame carries no per-detection timing. |
| `Flags` | Model-delivered per-detection status flags. The model auto-enables this channel even when it is not requested explicitly. |
| `Counts` | Model-delivered detection entry count used to bound every per-detection tensor; zero for a scan with no detections. The model auto-enables this channel even when it is not requested explicitly. |

## Troubleshooting

- The three output-shaping attributes (`elementsCoordsType`, `outputFrameOfReference`, `customFrameOfReferenceTrafo`) can be changed on a running radar: the model re-reads them with every parameter update and applies them from the next frame, while a frame already in flight keeps the values it started with; [Radar Attributes](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/attributes.html) describes the behavior.
- `Counts` defines the delivered range in per-detection tensors. Do not iterate over the full tensor allocation; use `Flags` for per-detection validity.
- `PointCloud` only needs requested payload channels; the model auto-enables `Counts` and `Flags` and delivers them like ordinary channel tensors.
- Radar output frame and visualizer frame are separate concerns. If output is in `SENSOR` frame, configure the visualizer to interpret that frame instead of changing the sensor to `WORLD` unless world-frame output is actually desired.
- This model needs an active motion BVH for motion effects, with `AUTO` or `ENABLE`: create the renderer with `ENABLE`, as the radar examples do (`ovrtx.MotionBvh.ENABLE` in Python, `OVRTX_MOTION_BVH_ENABLE` in C). Without it the radar runs and raises no error: it traces each scan from the radar's pose at the scan's acquisition time against a scene that does not move, so nothing moves within a frame and an animated target's detections report a radial velocity near zero, though a moving radar still reports radial velocity from its own movement. Nothing in the output reports whether the motion BVH was active; compare a run with it against one without. The Lidar generic core model also keeps running without motion BVH: it delivers its points without motion effects and logs a warning once that says so. Motion BVH is a renderer-level switch chosen when the renderer is created, not an attribute on the prim.
- A scan delivers at most 2500 detections. The cap is fixed in the model, is also the allocation bound published as the `maxPoints` param, and contributions past it are dropped with nothing in the output reporting that the scan saturated.
- The output-shaping attributes are in the radar's own namespace. Authoring `omni:sensor:Core:elementsCoordsType` on a radar prim changes nothing -- that is the Lidar generic core model's namespace. Use `omni:sensor:WpmDmat:`, and note that `elementsCoordsType` defaults to `SPHERICAL` and `outputFrameOfReference` to `SENSOR`.

## Related Skills

- `reading-render-output` for mapping render variables and composite tensors.
- `reading-sensor-pointclouds` for point-cloud tensor access patterns.
- `interpreting-radar-pointclouds` for radar channel units and visualization.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.

Product documentation owns the detail this skill only summarizes:

- [Radar generic wpmDmat model](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/index.html) -- what a detection is, the three attribute namespaces, aliasing, what a radar reads from a material label, the motion BVH requirement.
- [Radar Attributes](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/attributes.html) -- every scan, CFAR, noise, waveform and antenna attribute with its default.
- [Choose Radar Parameter Values](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/howto/choose_parameters.html) and [Validate a Radar Parameterization](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/howto/validate_parameterization.html) -- picking values that hold together, and checking them before trusting output.
- [Run More Than One Scan Pattern](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/howto/scan_configurations.html) -- authoring more than one scan and telling which one produced a frame.
- [Sensor Outputs](https://nvidia-omniverse.github.io/ovrtx/sensors/common/sensor_outputs.html) -- the output container, bounding a read by `Counts`, the `VALID` (`0x40`) bit, packing and the params every point cloud shares.
- [Output Configuration](https://nvidia-omniverse.github.io/ovrtx/sensors/common/output_configuration.html) -- RenderProduct and RenderVar wiring, and the motion BVH renderer option.
- [Troubleshooting](https://nvidia-omniverse.github.io/ovrtx/sensors/troubleshooting/index.html) -- symptoms, their causes, and the by-design limits of the models.
