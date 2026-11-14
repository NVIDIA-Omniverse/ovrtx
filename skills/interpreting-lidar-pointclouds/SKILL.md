---
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
name: interpreting-lidar-pointclouds
description: >
  Interpreting already-read lidar PointCloud tensors: channel meanings, units, valid
  point ranges, coordinate-frame implications, flags, IDs, normals, velocity, and
  visualization values. Use reading-sensor-pointclouds when the user needs to map or
  fetch the tensors first.
license: CC-BY-4.0 AND Apache-2.0
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

The lidar examples demonstrate a minimal interpretation path: read `Coordinates`, `Counts`, `Intensity`, and `TimeOffsetNs`, slice each per-point tensor to the delivered range, and summarize or visualize the result. Their scenes explicitly set `includeInvalidPoints = false`, so the delivered range is also the valid range.

## Channels

These are the available lidar `PointCloud` channels of the Lidar generic core model, the model `OmniSensorGenericLidarCoreAPI` selects (`omni:sensor:modelName = "LidarCore"`). The Lidar generic wpm model, selected by `OmniSensorGenericLidarWpmAPI` (`"LidarWpm"`), publishes a different channel set; refer to [Lidar generic wpm model](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/lidar_wpm/index.html).

| Channel | Type / Shape | Unit | Meaning |
|---|---|---|---|
| `Counts` | `int32` 1D, `1` | points | Model-delivered point entry count; use it to bound every per-point tensor. With default invalid-point dropping this is the valid point count, but `includeInvalidPoints = true` can preserve invalid entries inside the range. |
| `Coordinates` | `float32` 2D, `3 x N` | m, deg | Point coordinates, component-first: all x, then all y, then all z, so the stride between components is the allocation bound and not `Counts[0]`. Representation is controlled by `elementsCoordsType`: Cartesian positions, or spherical as azimuth (deg), elevation (deg), distance (m). Frame is controlled by `outputFrameOfReference`. |
| `Intensity` | `float32` 1D, `N` | unitless | Processed return strength, normalized by the lidar intensity processing mode. Range depends on scaling and mapping attribute, base is [0,1] |
| `TimeOffsetNs` | `int32` 1D, `N` | ns | Per-point time offset relative to the sensor frame timestamp. Always `0` for [instant lidar](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/lidar_core/howto/output_shaping.html#sensors-lidar-core-instant-lidar). |
| `Flags` | `uint8` 1D, `N` | unitless | Model-delivered point status flags. `VALID` (`1 << 6`, `0x40`) marks a valid point. This model is the only one that also sets the new-scan bit `0x20` (`1 << 5`): it marks a return that belongs to the scan after the one the frame started in. Only a rotary sensor with `partialOutputs = true` delivers such a frame, one whose window crosses a scan boundary; its returns from the end of one scan carry `VALID` alone, and its returns from the start of the next scan carry `VALID` and `0x20`. With `partialOutputs = false` every frame holds one whole scan, and a solid-state sensor's windows never cross a scan boundary, so neither carries the bit. See [the new-scan bit](https://nvidia-omniverse.github.io/ovrtx/sensors/common/sensor_outputs.html#sensors-common-sensor-outputs-new-scan-bit). |
| `EmitterId` | `uint32` 1D, `N` | unitless | Internal emitter or laser index in the emitter state array. |
| `ChannelId` | `uint32` 1D, `N` | unitless | Detector/channel id of the emitter that produced the point, reported exactly as authored in its `channelId` -- a vendor label, not an index, so one-based, zero-based, sparse or large id sets come back unchanged. The schema's default emitter state numbers its channels 1 through `numberOfChannels`, so a profile that keeps that default reports 1 through `numberOfChannels`. It is not the emitter index: a profile that authors emitter *i* as channel `i + 1`, as the schema's default emitter state does, reports every point's `ChannelId` as its `EmitterId` plus one, except on a solid-state sensor thinned by tiled subsampling, whose surviving emitters are renumbered from 0 but keep their authored ids; any other profile relates the two only through its authored `channelId` values, and complex channel configurations can map several emitters to one id. |
| `TickId` | `uint32` 1D, `N` | unitless | Zero-based firing-pattern tick index within the scan; always `0` on a solid-state sensor, which has one tick per scan. |
| `EchoId` | `uint8` 1D, `N` | unitless | Return index within the firing, from `0`; its order depends on `rayType`. With `IDEALIZED` rays it counts surfaces along the ray's path (`0` is the first); with `GAUSSIAN_BEAM` or `UNIFORM_BEAM` it ranks the merged peaks by summed irradiance (`0` is the strongest, not necessarily the nearest). |
| `TickState` | `uint8` 1D, `N` | unitless | Zero-based index of the emitter state that fired the point. On a rotary sensor each tick can carry its own state, so the value can change from tick to tick within one scan; on a solid-state sensor all points of a scan carry the state selected for that scan. |
| `MaterialId` | `uint32` 1D, `N` | unitless | Encoded nonvisual material ID of the hit surface. |
| `ObjectId` | `uint32` 2D, `N x 4` | unitless | 128-bit stable object ID for the hit object, packed as four `uint32` values per point. By default it does not identify the object; see Interpretation Notes. |
| `HitNormal` | `float32` 2D, `N x 3` | unitless | Unit surface normal at the hit point. It follows `outputFrameOfReference` and `outputMotionCompensationState` like `Coordinates`, in every combination of the two: rotated, never translated, and always Cartesian whatever `elementsCoordsType` says. With `SENSOR` and `NONCOMPENSATED` it is delivered as traced, in the sensor's axes at the pose the ray was fired from. |
| `Velocity` | `float32` 2D, `N x 3` | m/s | Velocity of the hit point relative to the sensor: the sensor's own linear velocity, and the velocity its rotation gives the hit point, are subtracted. It is rotated into the output frame and compensation state as `HitNormal` is; the rotation does not add the sensor's motion back, so in `WORLD` it is still relative to the sensor. |

The model auto-enables `Counts` and `Flags`, and they are delivered as ordinary `PointCloud` channel tensors. Every other channel in the table is present only when the `PointCloud` RenderVar requests it, and the request alone fills it.

Packing is a property of the model, not of the channel name. The Lidar generic core model publishes `Coordinates` component-first as above; the Lidar generic wpm model publishes the same channel point-first. Take the layout from the shape and strides the mapped tensor reports, not from the name -- the wrong assumption reads out as something that looks like a point cloud and is not.

## Validity

Within the first `Counts[0]` entries, a point is valid when `(Flags[i] & VALID) != 0`. A point is invalid when that bit is clear. Do not compare `Flags[i] == VALID`, because the model can also set the new-scan bit `0x20` on the same point.

With the default `omni:sensor:Core:includeInvalidPoints = false`, invalid lidar returns are dropped before output, so entries up to `Counts[0]` are expected to be valid. With `includeInvalidPoints = true`, invalid returns are preserved; filter by `Flags` before using channels such as `Coordinates`, `Intensity`, `ChannelId`, `HitNormal`, or `Velocity` as real returns. An entry no emitter wrote carries `ChannelId` `0`, which a zero-based profile also uses for a real detector, so the value alone cannot tell them apart. The delivered `compactionType` param records which applied: `2` means invalid returns were dropped, `1` that they were kept.

## Interpretation Notes

- `Coordinates` may be Cartesian or spherical. Read the delivered `coordsType` param (`0` Cartesian, `1` spherical) before treating components as XYZ: it reports what the model used, which is the authored `elementsCoordsType` as it stood when the frame started; a frame already in flight when you edit the attribute keeps the value it started with (see [Configure Lidar Output](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/lidar_core/howto/output_shaping.html)).
- Lidar sensor-frame output is often easiest for sensor algorithms and visualization in sensor coordinates; world-frame output is useful for scene-level fusion.
- `Intensity` is processing-mode dependent, so compare values only across runs with compatible lidar intensity settings and materials.
- `TimeOffsetNs` matters for scanning sensors because different points in one reported frame can come from different firing times.
- `EmitterId`, `ChannelId`, `TickId`, `EchoId`, and `TickState` are useful for reconstructing scan pattern behavior or filtering by beam/return; on a solid-state sensor `TickId` is always `0` and `TickState` is the same for every point of a scan, so use `EmitterId` there.
- `MaterialId`, `ObjectId`, `HitNormal` and `Velocity` are filled whenever the `PointCloud` RenderVar names them, and nothing else gates them (see their rows above). A surface whose material carries no readable non-visual labels answers as `none` and resolves to `MaterialId` 0, so a uniformly zero `MaterialId` points at the labels (see `nonvisual-materials`). `ObjectId` identifies the hit object only while the renderer's stable IDs are on, and they are off by default; requesting `ObjectId` does not turn them on, so by default its first three values are 0 on every point and the last is only the hit mesh part's number (the primitive's, for procedural geometry), which is 0 for a mesh in one part. Rendering any render product that requests `StableIdMap`, `StableIdMapDeltas`, `StableIdSegmentation`, `StableIdSemanticIdMap` or `SemanticInstanceSegmentation` turns them on for the whole scene.
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

Product documentation owns the detail this skill only summarizes:

- [Sensor Outputs](https://nvidia-omniverse.github.io/ovrtx/sensors/common/sensor_outputs.html) -- mapping an output, capacity versus count, the `Counts` bound and the `VALID` bit, the packing rule, the params delivered beside the channels, and the synchronization and lifetime rules, stated once for every model.
- [Lidar generic core model](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/lidar_core/index.html) -- what a tick, emitter, channel and return are, and why one frame spans several firing times.
- [Lidar generic core model outputs](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/lidar_core/outputs.html) -- every channel with element type, shape, unit and meaning, this model's validity rules and params, and decoding a `MaterialId` into base, coating and attribute fields.
- [Non-Visual Sensor Materials](https://nvidia-omniverse.github.io/ovrtx/materials/nonvisual_sensor_materials.html) -- the non-visual material labels behind `MaterialId`, the SimReady vocabulary they come from, and what to check when every return reads 0.
- [Troubleshooting](https://nvidia-omniverse.github.io/ovrtx/sensors/troubleshooting/symptoms.html) -- indexed by what you observed.
