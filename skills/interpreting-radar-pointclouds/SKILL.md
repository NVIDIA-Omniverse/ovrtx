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
name: interpreting-radar-pointclouds
description: >
  Interpreting already-read radar PointCloud tensors: channel meanings, units, valid
  detection ranges, RCS, signed radial velocity, time offsets, flags, counts, and
  visualization values. Use reading-sensor-pointclouds when the user needs to map or
  fetch the tensors first.
license: LicenseRef-NvidiaProprietary
version: "0.3.0"
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

Use this skill when the user asks what already-read radar Coordinates, RCS, RadialVelocityMs, TimeOffsetNs, Flags, or Counts tensors mean. Use `reading-sensor-pointclouds` instead when the user needs map/read code to obtain the tensors.

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
3. Use `Counts[0]` for tensor bounds and `Flags` bit tests for per-detection validity before summarizing `RCS`, `RadialVelocityMs`, or timing channels.
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

Radar `PointCloud` output is a composite render var with one tensor per detection channel. Use `Counts[0]` to bound the delivered detections before interpreting `Coordinates`, `RCS`, `RadialVelocityMs`, `TimeOffsetNs`, or `Flags`, and use the `Flags` `VALID` bit for per-detection validity.

> **Source:** `examples/python/radar/main.py` snippet `read-radar-pointcloud`
> **Source:** `examples/c/radar/main.cpp` snippet `read-radar-pointcloud`

The radar examples demonstrate the usual interpretation path: slice to valid detections, summarize channel values, and treat radial velocity sign deliberately.

## Channels

These are the available radar `PointCloud` channels from `omni.sensors.nv.radar`.

| Channel | Type / Shape | Unit | Meaning |
|---|---|---|---|
| `Counts` | `int32` scalar | detections | Model-delivered detection count; use it to bound every per-detection tensor. |
| `Coordinates` | `float` 2D, `3 x N` | m, rad | Detection coordinates. Representation is controlled by the radar coordinate type: Cartesian positions or spherical range/angle components. Frame is controlled by the configured output frame. |
| `RCS` | `float` 1D, `N` | dBsm | Radar cross section, a logarithmic measure of how detectable the target is to radar. value range depends on attributes |
| `TimeOffsetNs` | `int32` 1D, `N` | ns | Per-detection time offset relative to scan start. |
| `RadialVelocityMs` | `float` 1D, `N` | m/s | Doppler radial velocity. Approaching detections can be negative; use absolute value when checking only for motion. value range depends on attributes |
| `Flags` | `uint8` 1D, `N` | unitless | Model-delivered detection status flag bit field. `VALID` (`1 << 6`, `0x40`) marks a valid detection. |

The model auto-enables `Counts` and `Flags`, and they are delivered as ordinary `PointCloud` channel tensors. `RCS`, `RadialVelocityMs`, and `TimeOffsetNs` are present only when requested.

## Validity

Within the first `Counts[0]` entries, a detection is valid when `(Flags[i] & VALID) != 0`. A detection is invalid when that bit is clear. Use a bit test instead of `Flags[i] == VALID` so future modality-specific flag bits do not break the filter.

Use `Counts` for tensor bounds and `Flags` for per-detection validity. Status-aware consumers should ignore invalid detections before summarizing `RCS`, `RadialVelocityMs`, or timing channels.

## Interpretation Notes

- `Coordinates` can be Cartesian or spherical. Check the authored coordinate type before treating components as XYZ.
- `RCS` is in dBsm. Min/max summaries are often more useful than printing a single value because detections can span materials, geometry, and noise.
- `RadialVelocityMs` is signed Doppler velocity. In the public radar example, the cube moving toward the sensor produces negative values.
- `TimeOffsetNs` lets consumers reason about detection timing within a scan, especially when combining radar output with motion.
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
