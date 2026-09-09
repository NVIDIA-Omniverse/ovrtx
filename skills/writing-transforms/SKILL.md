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
name: writing-transforms
description: >
  Writing 4x4 transform matrices to move, rotate, or scale prims. Use when user asks to
  move an object, set a transform, update position, animate a transform, or set a
  camera transform.
license: LicenseRef-NvidiaProprietary
author: NVIDIA ovrtx
tags:
  - ovrtx
  - transforms
  - attributes
tools:
  - Read
  - Grep
---

# Writing Transforms

## When to Use

Use this skill when the user asks to move an object, set a transform, update position, animate a transform, or set a camera transform.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, or both.
- Prim paths to move, desired translation/rotation/scale or full 4x4 matrices, and whether values are authored per prim.
- Transform storage name, semantic conversion, row-vector matrix convention, and sync/async behavior.
- Update cadence: one-shot movement, per-frame animation, or zero-copy GPU-computed transform updates.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Use `attribute-bindings` for per-frame transform writes to the same prims, and `mapping-attributes` when GPU kernels should write transforms directly into mapped ovrtx buffers.

## Instructions

1. Identify the target language, prim paths, transform representation, matrix convention, memory target, and sync/async requirement.
2. Read the matching source snippet and copy its lifecycle pattern rather than inventing equivalent calls.
3. Validate dtype, shape, semantic, and ownership rules before proposing or editing code.
4. Keep bindings, mapped buffers, operation handles, and C strings alive only for the lifetimes documented by the referenced examples.
5. When changing code, run the narrow docs test or example that owns the snippet whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- Transform semantic conversion is write-side only; read transform attributes with raw storage semantics.
- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

Transforms control the position, rotation, and scale of prims in the scene. ovrtx supports three transform representations. The most common is a 4x4 matrix of doubles using the USD row-vector convention: translation is in the last row (`[3][0..2]`). Use the `"omni:xform"` attribute name, which is also used by the C convenience helpers in `ovrtx_attributes.h`.

## Python

### Write a 4x4 transform (single prim)

> **Source:** `tests/docs/python/test_attribute_shapes.py` snippet `doc-shape-mat4-array`

### Write transforms for multiple prims

> **Source:** `tests/docs/python/test_attribute_bindings.py` snippet `doc-bind-attribute-write`

## C

### Write identity transform on a single prim

> **Source:** `examples/c/vulkan-interop/src/main.cpp` snippet `write-camera-transform`

### Batch write (N prims)

> **Source:** `examples/c/vulkan-interop/src/main.cpp` snippet `write-camera-transform`
>
> For multiple prims, increase `prim_list.num_paths` and provide a contiguous array of transforms.

### C convenience helpers (`ovrtx_attributes.h`)

Instead of building DLTensor and binding descriptors manually, use the convenience helpers that handle the boilerplate:

> **Source:** `tests/docs/c/test_transform_helpers.cpp` snippets `doc-set-xform-mat-c`, `doc-set-xform-pos-rot-scale-c`, `doc-set-xform-pos-rot3x3-c`, `doc-set-reset-xform-stack-c`.

`#include <ovrtx/ovrtx_attributes.h>` provides `ovrtx_set_xform_mat(renderer, paths, count, transforms)`, `ovrtx_set_xform_pos_rot_scale(...)`, `ovrtx_set_xform_pos_rot3x3(...)`, and `ovrtx_set_reset_xform_stack(...)`.

## Tensor layout

Python and C expose different transform tensor layouts:
- Python uses NumPy-style matrices: an N-prim batch has shape `(N, 4, 4)` and `dtype=float64`.
- C uses DLTensor lanes for attributes: an N-prim batch has shape `[N]` and `DLDataType{kDLFloat, 64, 16}`.
- C rendered outputs/AOVs are different from attributes; image tensors use channel-last shapes such as `[height, width, channels]` with `dtype.lanes=1`.

> **Source:** `tests/docs/python/test_attribute_shapes.py` snippet `doc-shape-mat4-array`.
>
> **Source:** `tests/docs/c/test_attribute_shapes.cpp` snippet `doc-shape-mat4-array-c`.

Semantics are a **write-side** conversion hint. `ovrtx_read_attribute` rejects any semantic other than `OVRTX_SEMANTIC_NONE` with "Semantic conversion is not supported for read_attribute". When reading a transform attribute, leave the semantic as `OVRTX_SEMANTIC_NONE` and ask for the raw storage layout.

## Key Types / Functions

| Representation | Python | C | Size per prim |
|----------------|--------|---|---------------|
| 4x4 matrix (doubles) | `Semantic.XFORM_MAT4x4` or `dtype="float64", shape=(4, 4)` | `OVRTX_SEMANTIC_XFORM_MAT4x4` with `ndim=1, shape=[N], dtype={kDLFloat, 64, 16}` | 128 bytes |
| pos3d + rot4f + scale3f | (C only) | `OVRTX_SEMANTIC_XFORM_POS3d_ROT4f_SCALE3f` | 56 bytes |
| pos3d + rot3x3f | (C only) | `OVRTX_SEMANTIC_XFORM_POS3d_ROT3x3f` | 64 bytes |

C convenience helpers (`#include <ovrtx/ovrtx_attributes.h>`):
- `ovrtx_set_xform_mat(renderer, paths, count, transforms)` -- 4x4 matrix
- `ovrtx_set_xform_pos_rot_scale(renderer, paths, count, transforms)` -- pos + quat + scale
- `ovrtx_set_xform_pos_rot3x3(renderer, paths, count, transforms)` -- pos + 3x3 rotation
- `ovrtx_set_reset_xform_stack(renderer, paths, count, values)` -- set `omni:resetXformStack`

Python semantic: `Semantic.XFORM_MAT4x4` (from `from ovrtx import Semantic`). For interop, the preferred approach is `dtype="float64", shape=(4, 4)` on `bind_attribute`/`map_attribute`, or passing an `(N, 4, 4)` float64 array directly to `write_attribute` (type is auto-inferred when the attribute already exists in the stage). The `dtype` parameter accepts string names (`"float64"`), NumPy dtypes (`np.float64`), or Python built-ins (`float`). The `semantic=` parameter is required when creating attributes from scratch via `prim_mode=PrimMode.CREATE_NEW`.

## Troubleshooting

- Matrices use the **USD row-vector convention** (same as `GfMatrix4d`). Translation is in the last row: `v[12]`, `v[13]`, `v[14]` (or `matrix[3][0..2]` in Python/C).
- Use the `"omni:xform"` attribute name to match the C convenience helpers (`ovrtx_set_xform_mat`, etc.).
- Transform dtype is `float64` (doubles), not float32. Using the wrong dtype will cause errors.
- For repeated per-frame transform updates, use attribute bindings or mapping for better performance (see `attribute-bindings` and `mapping-attributes` skills).
- Earlier code may use `ovrtx.math.Matrix4d` for single-prim writes; the `ovrtx.math` module and the `Matrix4d` class have been removed. Pass an `(N, 4, 4)` `float64` array (NumPy, Warp, or any DLPack-compatible tensor) directly to `write_attribute`, or use `dtype="float64", shape=(4, 4)` with `bind_attribute` / `map_attribute`.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
