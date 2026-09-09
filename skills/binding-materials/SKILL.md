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
name: binding-materials
description: >
  Binding materials to prims at runtime. Use when user asks to assign a material,
  change a material, set material binding, or swap materials on a prim.
license: LicenseRef-NvidiaProprietary
author: NVIDIA ovrtx
tags:
  - ovrtx
  - materials
  - bindings
tools:
  - Read
  - Grep
---

# Binding Materials

## When to Use

Use this skill when the user asks to assign a material, change a material, set material binding, or swap materials on a prim.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, USD, or a combination.
- Geometry prim path or paths that should receive the material binding.
- Existing material prim path, relationship write timing, and whether the workflow is static USD or runtime API code.
- Whether the material is visual-only, sensor-facing nonvisual metadata, or both.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Confirm that the target material prim already exists in the stage or loaded USD content.
- Use `nonvisual-materials` for authoring sensor-facing base material/coating labels; this skill only covers binding a material prim to geometry.

## Instructions

1. Identify the geometry prims, target material prim, target language, and whether the bind happens in USD or through runtime APIs.
2. Read the matching Python or C/C++ source snippet before writing API usage.
3. Write the standard USD `material:binding` relationship on the geometry prim, using path-array helpers where required.
4. Keep material binding separate from sensor label authoring; combine with `nonvisual-materials` only when the request includes sensor material semantics.
5. When changing code, run the narrow docs test or example that owns the snippet whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

To change which material is applied to a prim at runtime, write the `material:binding` attribute as a path string pointing to the target material prim. In USD, `material:binding` is a relationship (array of paths), so use `write_array_attribute()` in Python or `ovrtx_set_path_attributes()` in C.

The material prim must already exist in the stage (e.g., loaded from USD). You write the absolute prim path of the material to the geometry prim that should receive it.

## Python

### Bind a material to a prim

> **Source:** `tests/docs/python/test_base.py` snippet `doc-bind-material`

## C

### Bind a material to a prim

> **Source:** `tests/docs/c/test_base.cpp` snippet `doc-bind-material-c`

## Key Types / Functions

| Python | C |
|--------|---|
| `renderer.write_array_attribute(prim_paths, "material:binding", [["/path/to/material"]])` | `ovrtx_set_path_attributes(renderer, &prim_path, 1, "material:binding", &material_path)` |

## Troubleshooting

- The attribute name is `material:binding` (with a colon), matching the standard USD relationship name.
- In Python, pass a `list[list[str]]` for the `tensors` parameter -- one list of path strings per prim. The string list format is auto-detected as path/relationship data.
- The path must be an absolute prim path to a material that exists in the stage (e.g., `"/World/Looks/MyMaterial"`).
- Write the binding to the geometry prim (the mesh or Xform), not to the material prim.
- In C, use the `ovrtx_set_path_attributes()` convenience helper from `<ovrtx/ovrtx_attributes.h>` -- it handles wrapping the path into the required single-element relationship array.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
