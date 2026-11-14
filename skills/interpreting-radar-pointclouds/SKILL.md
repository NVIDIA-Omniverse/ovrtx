---
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
name: interpreting-radar-pointclouds
description: >
  Interpret already-read radar PointCloud tensors: channel meanings, units, valid
  detection ranges, RCS, signed radial velocity, time offsets, flags, counts,
  scan-metadata params, and visualization values. Use reading-sensor-pointclouds
  when the user needs to map or fetch the tensors first.
license: CC-BY-4.0 AND Apache-2.0
author: NVIDIA ovrtx
tags:
  - ovrtx
  - radar
  - pointclouds
tools:
  - Read
  - Grep
---

# Interpreting Radar PointClouds

## When to Use

Use this skill when the user asks what already-read radar Coordinates, RCS, RadialVelocityMs, TimeOffsetNs, Flags, or Counts tensors mean, or what the scan-metadata params delivered beside them report. Use `reading-sensor-pointclouds` instead when the user needs map/read code to obtain the tensors.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Radar channel names and tensor values or summaries already available to the caller.
- Authored radar settings that affect interpretation, especially coordinate representation, output frame, scan timing, and requested output channels.
- Validity context: `Counts`, `Flags`, desired `RCS` or `RadialVelocityMs` filtering, and visualization needs.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Start from tensors the caller has already read, or a conceptual question about channel meaning. Use `reading-sensor-pointclouds` if the user needs code to access the tensors.
- Use `configuring-radar-sensors` when the requested channel is missing because it was not authored in the radar `PointCloud` RenderVar.

## Instructions

1. Identify the radar channels being interpreted and the settings that define their coordinate frame, scan timing, and validity behavior.
2. Read the matching interpretation source snippet before explaining channel behavior or visualization choices.
3. Use `Counts[0]` for tensor bounds and `Flags` bit tests for per-detection validity before summarizing `RCS`, `RadialVelocityMs`, or timing channels. A scan with no detections has `Counts[0] == 0`; skip per-detection reads while retaining its scan metadata (see Validity). `RCS` arrives only when requested, so use `configuring-radar-sensors` to add it when the consumer needs detection strength.
4. Treat `RadialVelocityMs` as signed Doppler velocity and explain sign conventions explicitly.
5. Explain channel meaning without adding mapping boilerplate unless the user also asks how to read the tensors.
6. When changing code, run the narrow docs test or example that owns the snippet whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

Radar `PointCloud` output is a composite render var with one tensor per detection channel. Use `Counts[0]` to bound the delivered entries before interpreting `Coordinates`, `RCS`, `RadialVelocityMs`, `TimeOffsetNs`, or `Flags`, and use the `Flags` `VALID` bit for per-detection validity.

> **Source:** `examples/python/radar/main.py` snippet `read-radar-pointcloud`
> **Source:** `examples/c/radar/main.cpp` snippet `read-radar-pointcloud`

The radar examples demonstrate the usual interpretation path: slice to the delivered detection range, filter that range with `Flags`, summarize channel values, and treat radial velocity sign deliberately. The two example scenes differ only in whether they request `RCS`: the C scene does, the Python scene does not.

## Channels

These are the available radar `PointCloud` channels of the Radar generic wpmDmat model. `Nmax` is the per-frame allocation bound.

| Channel | Type / Shape | Unit | Meaning |
|---|---|---|---|
| `Counts` | `int32 [1]` | detections | Model-delivered entry count: the number of entries delivered this frame, which is `0` for a scan that detected nothing (see Validity); use it to bound every per-detection tensor. |
| `Coordinates` | `float32 [3, Nmax]` | m, or deg / deg / m | Detection coordinates, component-first: one row per component, each `Nmax` long, so the stride between components is the allocation bound and not `Counts[0]`. Cartesian rows are x/y/z in meters. Spherical rows are azimuth/elevation in degrees followed by range in meters. Representation is controlled by `omni:sensor:WpmDmat:elementsCoordsType`, defaulting to `SPHERICAL`. The output frame, controlled by `omni:sensor:WpmDmat:outputFrameOfReference` and defaulting to `SENSOR`, applies to either representation. |
| `RCS` | `float32 [Nmax]` | dBsm | Radar cross section, a logarithmic measure of radar detectability; the value range depends on sensor and scene attributes. |
| `TimeOffsetNs` | `int32 [Nmax]` | ns | Time offset of the detection within the scan. It is `0` for every detection by design, because the model simulates each scan at one instant, so a radar frame carries no per-detection timing. |
| `RadialVelocityMs` | `float32 [Nmax]` | m/s | Signed Doppler radial velocity. Approaching detections can be negative; use absolute value when checking only for motion. |
| `Flags` | `uint8 [Nmax]` | unitless | Model-delivered detection status bit field. `VALID` (`1 << 6`, `0x40`) marks a valid detection, and this model sets no other bit; see Validity. |

The model auto-enables `Counts` and `Flags`, and they are delivered as ordinary `PointCloud` channel tensors. `Coordinates`, `RCS`, `RadialVelocityMs`, and `TimeOffsetNs` are present only when requested.

## Validity

Within the first `Counts[0]` entries, a detection is valid when `(Flags[i] & VALID) != 0`. A detection is invalid when that bit is clear. Use a bit test instead of `Flags[i] == VALID` so future modality-specific flag bits do not break the filter.

Use `Counts` for tensor bounds and `Flags` for per-detection validity. Status-aware consumers should ignore invalid detections before summarizing `RCS`, `RadialVelocityMs`, or timing channels.

A scan that detects nothing is published with `Counts[0] == 0` and its scan metadata. The per-detection tensors retain their allocated capacity, but contain no delivered entries to read. `Counts` alone identifies an empty scan; `RCS` need only be requested when the consumer uses detection strength. See [empty scans](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/outputs.html#sensors-nonvisual-radar-outputs-empty-scan).

A step without a radar acquisition publishes no radar PointCloud frame. A published scan's `timestampNs` may be zero because a scan can fire at time zero.

## Interpretation Notes

- `Coordinates` can be Cartesian or spherical. Read the delivered `coordsType` param (`0` Cartesian, `1` spherical) before treating components as XYZ: it reports what the model used, from the next frame after an edit of `omni:sensor:WpmDmat:elementsCoordsType`.
- `RCS` is in dBsm. Min/max summaries are often more useful than printing a single value because detections can span materials, geometry, and noise.
- `RadialVelocityMs` is signed Doppler velocity. In the public radar example, the cube moving toward the sensor produces negative values.
- `TimeOffsetNs` reads zero for every detection by design: the model simulates each scan at one instant. A frame carries no per-detection timing; the frame's own timing is in its params — `timestampNs` is the scan's acquisition instant, its scan time plus the scan's `timeOffsetUsec`, and `frameStartTimeStampNs` and `frameEndTimeStampNs` bound the frame's time window, inside which that instant falls. Radar measures the offset within the scan while the Lidar generic core model measures it from the frame's `timestampNs`, so do not read one with a routine written for the other.
- The allocation bound is a fixed per-scan cap of 2500 detections, not a function of what was authored, and it is also the `maxPoints` param. Detections beyond it are dropped with nothing in the output saying the scan saturated, so a `Counts[0]` pinned at 2500 is the tell.
- The params delivered beside the channels describe the scan as well as the frame: `scanIdx` is the index of the scan configuration that produced the frame, and `maxRangeM` (m), `minVelMps` and `maxVelMps` (m/s), and `minAzRad`, `maxAzRad`, `minElRad` and `maxElRad` (rad) are that scan's limits. The angle limits are radians while spherical `Coordinates` are degrees, so convert one side before checking a detection against them, and check only when `frameOfReference` is `0` (sensor): the limits are angles about the sensor, while world or custom output measures a detection's angles in that frame.
- `Flags` should be used when an application needs status-aware filtering. `Counts` still defines the delivered tensor range.

## Visualization

> **Source:** `examples/python/radar/main.py` snippet `radial-velocity-colors`
> **Source:** `examples/python/radar/main.py` snippet `log-radar-points`

Coloring by signed `RadialVelocityMs` is a useful default: one color for approaching detections, another for receding detections, and a neutral color near zero. Color by `RCS` when the goal is material or detectability inspection.

## Related Skills

- `reading-sensor-pointclouds` for mapping and slicing composite PointCloud tensors.
- `configuring-radar-sensors` for authoring radar output channels.
- `nonvisual-materials` for material labels that influence radar return behavior.

## Troubleshooting

- If source snippets do not cover the requested variant, add or update a focused docs test or example before documenting the new pattern.
- If behavior differs between Python and C/C++, prefer the language-specific snippet and call out the difference explicitly.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.

Product documentation owns the detail this skill only summarizes:

- [Radar Outputs](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/outputs.html) -- every radar channel with element type, shape, unit and meaning, empty-scan output, the radial-velocity sign, the time offset, the detection cap and the scan params, stated once.
- [Radar generic wpmDmat model](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/index.html) -- why a detection is not a surface sample, multipath and ghost targets, aliasing, and what a radar reads from a material label.
- [Sensor Outputs](https://nvidia-omniverse.github.io/ovrtx/sensors/common/sensor_outputs.html) -- the output container, capacity versus count, the `VALID` bit, and the params the lidar and radar point clouds share.
- [Troubleshooting](https://nvidia-omniverse.github.io/ovrtx/sensors/troubleshooting/symptoms.html) -- indexed by what you observed.
