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
name: mapping-attributes
description: >
  Zero-copy attribute map/unmap for direct memory access to ovstage buffers. Use
  when user asks about zero-copy writes, map attribute, direct memory access, or
  repeated mapped updates. Use attribute-bindings for repeated writes with
  caller-owned tensors when a copy is acceptable.
license: LicenseRef-NvidiaProprietary
version: "0.3.0"
author: NVIDIA ovrtx
tags:
  - ovrtx
  - attributes
  - mapping
tools:
  - Read
  - Grep
---

# Mapping Attributes

## When to Use

Use this skill when the user asks about zero-copy writes, `map_attribute`, direct memory access, or mapped attribute updates. Use `attribute-bindings` for repeated writes through a reusable ovstage query when the caller already owns the data tensor.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, or both.
- Prim paths, attribute name, element type, semantic conversion, and whether the attribute is mappable.
- Mapping API, target device, and required synchronization.
- Synchronization and lifetime requirements: stream/event, map duration, whether data must outlive the mapping, and whether array attributes are involved.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- For ragged array attributes such as `float3[] points`, provide one `element_sizes` entry per queried prim. Omit `element_sizes` for fixed-size attributes.
- Use `attribute-bindings` first when the user wants repeated updates but does not need zero-copy direct buffer access.

## Instructions

1. Identify the concrete map/unmap target, language, prim list, attribute name, memory target, and synchronization requirement.
2. Read the matching source snippet and copy its map/write/unmap lifecycle rather than inventing equivalent calls.
3. Validate dtype, shape, semantic, mappability, and ownership rules before proposing or editing code.
4. Keep mapped tensor views alive only until unmap, and copy anything that must outlive the mapping.
5. For repeated map/unmap cycles, retain and reuse the ovstage query.
6. When changing code, run the narrow docs test or example that owns the snippet whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- Ragged array mappings require `element_sizes`; its length must match the number of prims selected by the query.
- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

Mapping gives you direct access to an ovstage attribute buffer. Instead of copying data in, write through each fetched group, then unmap and advance the write floor.

The pattern is: **map -> write into tensor -> unmap**.

## Python

### CPU mapping with NumPy

> **Source:** `tests/docs/python/test_attribute_bindings.py` snippet `doc-map-attribute-cpu`

### Context manager (recommended)

> **Source:** `tests/docs/python/test_attribute_bindings.py` snippet `doc-map-attribute-cpu`

### Deprecated renderer API: GPU mapping with Warp

From the planet-system example -- map on CUDA, compute with a Warp kernel, unmap with stream sync:

> **Source:** `tests/docs/python/test_attribute_bindings.py` snippet `doc-map-attribute-cuda`

### Reusing a query for mapping

Reuse the query across map/unmap cycles:

> **Source:** `tests/docs/python/test_attribute_bindings.py` snippet `doc-map-bound-attribute`

## C

### Map, write, unmap

> **Source:** `tests/docs/c/test_attribute_bindings.cpp` snippet `doc-map-attribute-cpu-c`

### GPU mapping with CUDA sync

> **Source:** `examples/c/vulkan-interop/src/main.cpp` snippet `map-rendered-output-cuda-array`

## Key Types / Functions

| Python | C |
|--------|---|
| `stage.map_attribute(query, attr, ordinal=..., element_sizes=...)` | `ovrtx_map_attribute(renderer, &binding, desc, &out)` |
| `mapping.fetch_next()` | `out_mapping.dl` (DLTensor) |
| `mapping.unmap()` | `ovrtx_unmap_attribute(renderer, handle, sync)` |

Tensor layout follows the lane-based attribute rules in the `writing-attributes` skill. DLPack consumers expose lane components as trailing dimensions, so a lane-16 matrix group can be reshaped to `(N, 4, 4)`.

> **Source:** `tests/docs/python/test_attribute_shapes.py` snippets `doc-shape-scalar-int32`, `doc-shape-float3-array`, `doc-shape-mat4-array`.

## Troubleshooting

- **Tensor lifetime:** A tensor fetched from an ovstage mapping group is valid only while the mapping is active. Copy data that must outlive unmap.
- The canonical transform attribute name is `"omni:xform"`. The legacy name `"omni:fabric:localMatrix"` (used in examples above) is also accepted. New code should prefer `"omni:xform"`.
- For ragged array mappings, pass the per-prim element counts through `element_sizes`. The number of entries must match the query's prim count; omit it for fixed-size attributes.
- Data must be fully written before calling `unmap()`, and the write floor must advance before rendering that ordinal.
- Deprecated renderer CUDA mappings require stream or event synchronization on unmap.

## Deprecated Standalone APIs

The ovrtx attribute map/unmap APIs are deprecated in 0.4 and retained for
compatibility. New code should map through ovstage, iterate writable groups, unmap
the mapping, and advance the write floor.

See `docs/core/ovstage_integration.rst`, `skills/update-0_3-0_4-c/SKILL.md` and `skills/update-0_3-0_4-python/SKILL.md`.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
