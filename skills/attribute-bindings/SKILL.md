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
name: attribute-bindings
description: >
  Replacing persistent ovrtx attribute bindings with reusable ovstage queries for
  repeated writes or maps. Use when user asks about persistent bindings, repeated
  writes, efficient animation loops, bind_attribute, or updating transforms every
  frame with caller-owned tensors.
license: LicenseRef-NvidiaProprietary
version: "0.3.0"
author: NVIDIA ovrtx
tags:
  - ovrtx
  - attributes
  - bindings
tools:
  - Read
  - Grep
---

# Attribute Bindings

## When to Use

Use this skill when the user asks about persistent bindings, repeated writes, efficient animation loops, `bind_attribute`, or updating transforms every frame with caller-owned data. In new Python code, replace the binding with a reusable ovstage query. Use `mapping-attributes` when the user specifically needs zero-copy direct access or map/unmap lifetimes.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, or both.
- Prim paths, attribute name, element type, semantic conversion, and whether the attribute is scalar or array-valued.
- Repeated-write cadence, sync/async behavior, caller-owned data location, and whether CUDA stream/event synchronization is needed.
- Whether the user needs reusable query writes, query maps, or one-shot writes.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Use `writing-attributes` for one-shot or infrequent writes where descriptor creation cost does not matter.
- Use `mapping-attributes` for zero-copy direct buffer access; this skill can still apply when creating a persistent binding first and then mapping through it repeatedly.

## Instructions

1. Identify whether the user needs repeated ovstage writes or maps through a stable query.
2. Read the matching source snippet and copy its create/use/destroy lifecycle rather than inventing equivalent calls.
3. Validate prim list, attribute name, dtype, shape, semantic, and array/scalar rules before proposing or editing code.
4. Keep the ovstage query alive across repeated updates and release it when the hot path ends.
5. Choose `mapping-attributes` when avoiding the data copy matters more than avoiding descriptor recreation.
6. When changing code, run the narrow docs test or example that owns the snippet whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

When writing the same attribute to the same set of prims every frame, create one ovstage query and reuse it for `stage.write_attribute()` or `stage.map_attribute()`. Advance the write floor after each ordinal that must become visible to rendering.

## Python

### Deprecated renderer API: CUDA async write

The following snippet documents CUDA async writes through the deprecated renderer wrapper, including caller-provided stream synchronization:

> **Source:** `tests/docs/python/test_attribute_bindings.py` snippet `doc-write-attribute-async-data-access`

### Create a reusable query and write

For repeated writes to the same attribute and prims, create a query once:

> **Source:** `tests/docs/python/test_attribute_bindings.py` snippet `doc-bind-attribute-write`

### Reuse the query for repeated writes

> **Source:** `tests/docs/python/test_attribute_bindings.py` snippet `doc-binding-write-async`

### Array attribute write through a query

> **Source:** `tests/docs/python/test_attribute_bindings.py` snippet `doc-bind-array-attribute`

### Write with an explicit semantic

> **Source:** `tests/docs/python/test_attribute_bindings.py` snippet `doc-bind-attribute-write`

### Use the query for mapping (zero-copy)

> **Source:** `tests/docs/python/test_attribute_bindings.py` snippet `doc-map-bound-attribute`

## C

### Create and use a persistent binding

> **Source:** `tests/docs/c/test_attribute_bindings.cpp` snippets `doc-create-attribute-binding-c`, `doc-write-bound-attribute-c`, `doc-destroy-attribute-binding-c`

## Key Types / Functions

| Python | C |
|--------|---|
| `stage.query(...)` / `stage.query_from_path_list(...)` | `ovrtx_create_attribute_binding(renderer, &desc, &handle)` |
| `stage.write_attribute(query, attr, ordinal=..., ...)` | `ovrtx_write_attribute(renderer, &binding_ref, &buffer, access)` |
| `stage.map_attribute(query, attr, ordinal=...)` | `ovrtx_map_attribute(renderer, &binding_ref, mapping_desc, &out)` |
| `query.release()` | `ovrtx_destroy_attribute_binding(renderer, handle)` |

Binding flags (C only, set via `desc.flags`):
- `OVRTX_BINDING_FLAG_NONE` -- default
- `OVRTX_BINDING_FLAG_OPTIMIZE` -- optimize internal structures for frequent high-volume writes

## Troubleshooting

- **Tensor lifetime:** Fetched mapping groups are valid only while the ovstage mapping is active. Copy anything that must outlive unmap.
- The canonical transform attribute name is `"omni:xform"`. The legacy name `"omni:fabric:localMatrix"` (used in examples above) is also accepted. New code should prefer `"omni:xform"`.
- Release reusable ovstage queries explicitly when the hot path is done.
- In C, `OVRTX_BINDING_FLAG_OPTIMIZE` should be used for the primary hot-path binding. The last binding created with this flag takes priority.

## Deprecated Standalone APIs

Persistent ovrtx attribute bindings are deprecated in 0.4 and retained for
compatibility. They have no direct ovstage equivalent; reuse an ovstage query handle
for repeated read, write, or map operations and release the query when finished.

See `docs/core/ovstage_integration.rst`, `skills/update-0_3-0_4-c/SKILL.md` and `skills/update-0_3-0_4-python/SKILL.md`.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
