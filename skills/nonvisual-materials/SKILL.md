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
name: nonvisual-materials
description: >
  Authoring non-visual material labels for sensor simulation. Use when user asks to
  assign lidar/radar/acoustic material semantics, choose nonvisual base materials,
  coatings, or attributes, debug material IDs, or bind sensor-facing USD materials.
license: LicenseRef-NvidiaProprietary
version: "0.3.0"
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
- Material prim paths, desired base material, coating, attributes, prefix, and whether both supported prefixes must be authored.
- Geometry binding targets, existing visual materials, and any `MaterialId` debugging or pointcloud attribution needs.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Author nonvisual labels on material prims; use `binding-materials` when the geometry still needs `material:binding`.
- Use sensor configuration skills to request `MaterialId` output channels, and interpreting skills to explain returned material IDs.

## Instructions

1. Identify the sensor modality, material prims, nonvisual base/coating/attribute labels, and prefix requirements.
2. Read the matching USD source snippet before writing material metadata.
3. Preserve exact supported base material, coating, attribute, and prefix strings.
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

Non-visual material labels let lidar, radar, and acoustic sensors map USD materials to sensor-return behavior. A visual shader is optional; the sensor semantics come from custom material attributes that encode a base material, coating, and optional attributes into a material ID.

## USDA Pattern

### Python example scene

> **Source:** `examples/python/radar/radar_example.usda` snippet `configure-nonvisual-materials`

### C example scene

> **Source:** `examples/c/radar/radar_example.usda` snippet `configure-nonvisual-materials`

Author the labels on the `Material` prim that geometry binds with `rel material:binding`. The base material is required. Coating and attributes are optional; use `none` for unlabeled surfaces.

The default runtime prefix is `omni:simready:nonvisual`. The alternate supported prefix is `inputs:nonvisual`, selected by `/rtx/materialDb/nonVisualMaterialSemantics/prefix`. Public examples may write both prefixes so scenes work with either setting.

## Base Materials

Use these exact base material strings.

| Category | Materials |
|---|---|
| Default | `none` (0) |
| Metals | `aluminum` (1), `steel` (2), `oxidized_steel` (3), `iron` (4), `oxidized_iron` (5), `silver` (6), `brass` (7), `bronze` (8), `oxidized_Bronze_Patina` (9), `tin` (10) |
| Polymers | `plastic` (11), `fiberglass` (12), `carbon_fiber` (13), `vinyl` (14), `plexiglass` (15), `pvc` (16), `nylon` (17), `polyester` (18) |
| Glass | `clear_glass` (19), `frosted_glass` (20), `one_way_mirror` (21), `mirror` (22), `ceramic_glass` (23) |
| Other | `asphalt` (24), `concrete` (25), `leaf_grass` (26), `dead_leaf_grass` (27), `rubber` (28), `wood` (29), `bark` (30), `cardboard` (31), `paper` (32), `fabric` (33), `skin` (34), `fur_hair` (35), `leather` (36), `marble` (37), `brick` (38), `stone` (39), `gravel` (40), `dirt` (41), `mud` (42), `water` (43), `salt_water` (44), `snow` (45), `ice` (46), `calibration_lambertian` (47) |

`none` and `calibration_lambertian` map to `DefaultMaterial` behavior. Other base materials default to `CompositeMaterial` behavior.

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

## Behavior Types

The material system can map material IDs to these BSDF behavior types: `Constant`, `DefaultMaterial`, `CoreMaterial`, `AcousticMaterial`, `CompositeMaterial`, `RetroReflectiveMaterial`, and `ValidationMaterial`.

Use behavior remapping settings only when a sensor model needs a non-default BSDF behavior for a material ID.

## Troubleshooting

- Non-visual labels belong on the bound `Material`, not directly on the mesh.
- Keep the runtime prefix and authored prefix aligned. If every object behaves like the same material, check `/rtx/materialDb/nonVisualMaterialSemantics/prefix`.
- Preserve coating and attribute flags unless you intentionally want base-material-only behavior. `/app/sensors/nv/materials/preserveMaterialFlags=0xff` keeps all flags.
- `paint` and `calibration_lambertian` can use visual diffuse color information only when the sensor modality requests reflectance information.
- Material remapping settings are per modality, such as `/app/sensors/nv/lidar/matNameToIdMapOverrides` and `/app/sensors/nv/radar/matBehaviorToIdOverrides`.

## Related Skills

- `binding-materials` for USD material binding mechanics.
- `configuring-lidar-sensors` and `configuring-radar-sensors` for sensor output configuration.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
