---
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
name: nonvisual-materials
description: >
  Authoring non-visual material labels for sensor simulation. Use when user asks to
  assign lidar/radar/acoustic material semantics, choose nonvisual base materials,
  coatings, or attributes, debug material IDs, or bind sensor-facing USD materials.
license: CC-BY-4.0 AND Apache-2.0
author: NVIDIA ovrtx
tags:
  - ovrtx
  - materials
  - sensors
tools:
  - Read
  - Grep
---

# Nonvisual Materials

## When to Use

Use this skill when the user asks to assign lidar/radar/acoustic material semantics, choose nonvisual base materials, coatings, or attributes, debug material IDs, or bind sensor-facing USD materials.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, USD, or a combination.
- Sensor modality: lidar, radar, acoustic, or mixed sensor workflow.
- Material prim paths and desired base material, coating, and attributes.
- Geometry binding targets, existing visual materials, and any `MaterialId` debugging or pointcloud attribution needs.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Author nonvisual labels on material prims; use `binding-materials` when the geometry still needs `material:binding`.
- Use sensor configuration skills to request `MaterialId` output channels, and interpreting skills to explain returned material IDs.

## Instructions

1. Identify the sensor modality, material prims, and nonvisual base/coating/attribute labels.
2. Read the matching USD source snippet before writing material metadata.
3. Preserve exact supported base material, coating, and attribute strings.
4. Keep visual material binding, nonvisual label authoring, and PointCloud `MaterialId` reading as separate steps unless the user asks for the full workflow.
5. When changing code, run the narrow docs test or example that owns the snippet whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

Non-visual material labels let lidar, radar, and acoustic sensors map USD materials to sensor-return behavior. The semantics come from custom material attributes that encode a base material, coating, and optional attributes into one 16-bit material ID: base in bits 0-7, coating in bits 8-10, attribute flags in bits 11-15. No surface shader is needed: a bound `Material` carrying at least one of the non-visual attributes resolves on a fresh load with nothing connected to its surface output -- see Troubleshooting.

## USDA Pattern

### Python example scene

> **Source:** `examples/python/radar/radar_example.usda` snippet `configure-nonvisual-materials`

### C example scene

> **Source:** `examples/c/radar/radar_example.usda` snippet `configure-nonvisual-materials`

Author the labels on the `Material` prim that geometry binds with `rel material:binding`. The base material is required. Coating and attributes are optional; use `none` for unlabeled surfaces.

Use the Omniverse SimReady attributes: `omni:simready:nonvisual:base` and `omni:simready:nonvisual:coating` are tokens; `omni:simready:nonvisual:attributes` is a token array.

## Base Materials

Use these exact base material strings.

| Category | Materials |
|---|---|
| Default | `none` (0) |
| Metals | `aluminum` (1), `steel` (2), `oxidized_steel` (3), `iron` (4), `oxidized_iron` (5), `silver` (6), `brass` (7), `bronze` (8), `oxidized_bronze_patina` (9), `tin` (10) |
| Polymers | `plastic` (11), `fiberglass` (12), `carbon_fiber` (13), `vinyl` (14), `plexiglass` (15), `pvc` (16), `nylon` (17), `polyester` (18) |
| Glass | `clear_glass` (19), `frosted_glass` (20), `one_way_mirror` (21), `mirror` (22), `ceramic_glass` (23) |
| Other | `asphalt` (24), `concrete` (25), `leaf_grass` (26), `dead_leaf_grass` (27), `rubber` (28), `wood` (29), `bark` (30), `cardboard` (31), `paper` (32), `fabric` (33), `skin` (34), `fur_hair` (35), `leather` (36), `marble` (37), `brick` (38), `stone` (39), `gravel` (40), `dirt` (41), `mud` (42), `water` (43), `salt_water` (44), `snow` (45), `ice` (46), `calibration_lambertian` (47) |

## Coatings

| Coating | Index | Use |
|---|---:|---|
| `none` | 0 | Default, unlabeled, or unspecified coating. |
| `paint` | 1 | Painted surface. |
| `clearcoat` | 2 | Clear-coated surface. |
| `paint_clearcoat` | 3 | Painted and clear-coated surface. |
| `TBD` | 4-7 | Reserved for future use; do not select for authored content. |

## Attributes

Attributes are encoded as a bit field, so multiple attributes can be combined when the USD representation supports a list.

| Attribute | Index | Use |
|---|---:|---|
| `none` | 0 | Unspecified attribute. |
| `emissive` | 1 | Energy-emitting surface. |
| `retroreflective` | 2 | Retroreflective surface. |
| `single_sided` | 4 | Single-sided surface for non-thin geometry. |
| `visually_transparent` | 8 | Material is visually transparent. |
| `TDB` | 16 | Reserved for future use; do not select for authored content. |

The `Index` column above is the **bit value** that lands in bits 11-15 -- what to compare against after masking. The SimReady table numbers the attributes from 1 instead, and an attribute with SimReady index `n` sets bit `n - 1` of the field; both get called "the index", so SimReady index 3 is `single_sided`, whose bit value is 4. The reserved rows are placeholders: `TBD` and `TDB` are not authorable tokens.

## Troubleshooting

- Non-visual labels belong on the bound `Material`, not directly on the mesh.
- If every object behaves like the same material, check that the bound material authors the `omni:simready:nonvisual` attributes with the expected token and token-array types.
- The Lidar generic core model, the Radar generic wpmDmat model and the Acoustic generic wpm model answer from the labels alone: a texture or a tint on the visual shader changes nothing in their returns. Only the Lidar generic wpm model can consult the visual material as well -- its diffuse reflectance, roughness and shading normal -- and only when the per-sensor `omni:sensor:LidarWpm:useVisualMaterialInputs` is `true` (`false` by default); no other switch selects visual-material use for that model.
- A non-visual material does not need a surface shader. A `Material` that geometry binds and that carries at least one of the three non-visual attributes resolves to its encoded ID with nothing connected to its surface output, on a fresh load as well as in the session that authored it, and adding, changing or removing any of those attributes on a loaded stage takes effect without saving or reopening it. A material that also drives visual rendering still needs its visual shader network for that purpose; if it already has one, leave it alone.
- Base and coating tokens are matched exactly, so a misspelling or a wrong case contributes `0` rather than raising an error.
- Base ID `0` is a real catalog entry, not a diagnostic. An unmatched token, an absent base attribute and a deliberate `none` all produce `0`, and the number will not say which happened.
- Reading the ID back: request `MaterialId` on the lidar `PointCloud` RenderVar; the Lidar generic core model writes it for every valid return whenever the RenderVar names it, and no attribute switches it on or off. The Lidar generic wpm model publishes the same channel with the same encoding. Neither the radar nor the acoustic model publishes a `MaterialId` channel -- radar's `PointCloud` and acoustic's `SignalWays` have none -- so a radar or acoustic output offers no way back to the material ID.

## Related Skills

- `binding-materials` for USD material binding mechanics.
- `configuring-lidar-sensors` and `configuring-radar-sensors` for sensor output configuration.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.

Product documentation owns the detail this skill only summarizes:

- [Non-Visual Sensor Materials](https://nvidia-omniverse.github.io/ovrtx/materials/nonvisual_sensor_materials.html) -- the two material systems, the three `omni:simready:nonvisual` attributes and their authoring rules, where the labels live, what each model reads from them, and diagnosing a label that is not taking effect; the label tables themselves are in the SimReady specification it links.
- [Lidar generic core model outputs](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/lidar_core/outputs.html) -- the `MaterialId` channel, its element type and shape, the bit layout with a worked decode, and which models report a material id.
- [Sensor Outputs](https://nvidia-omniverse.github.io/ovrtx/sensors/common/sensor_outputs.html) -- mapping a `PointCloud` output and reading its tensors and params by name.
- [Troubleshooting](https://nvidia-omniverse.github.io/ovrtx/sensors/troubleshooting/symptoms.html) -- symptoms of a material that is not answering as authored.

The label vocabulary itself is defined by the [SimReady non-visual material specification](https://nvidia.github.io/simready-foundation/latest/capabilities/nonvisual_sensors/nonvisual_materials/capability-nonvisual_materials.html).
