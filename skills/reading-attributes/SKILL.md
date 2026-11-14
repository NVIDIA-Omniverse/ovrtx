---
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
name: reading-attributes
description: >
  Reading scalar or array attributes from prims into CPU or GPU tensors. Use when user
  asks to read an attribute value, fetch mesh data (points, faceVertexCounts, etc.),
  inspect a render setting, or sample transforms.
license: CC-BY-4.0 AND Apache-2.0
author: NVIDIA ovrtx
tags:
  - ovrtx
  - attributes
  - reading
tools:
  - Read
  - Grep
---

# Reading Attributes

## When to Use

Use this skill when the user asks to read an attribute value, fetch mesh data (points, faceVertexCounts, etc.), inspect a render setting, or sample transforms.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, or both.
- Reusable ovstage query, interned attribute token, expected USD value type, and scalar versus array read mode.
- Target consumer: CPU NumPy, C DLTensor, GPU-aware DLPack consumer, or metadata/schema inspection.
- Whether the caller needs raw storage, shape/dtype discovery, or values copied out for later use.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Use `stage-queries` first if the user needs to discover prims or attribute schemas before reading values.

## Instructions

1. Identify the target language, prim paths or prim-list handle, attribute name, scalar/array mode, memory target, and sync/async requirement.
2. Read the matching source snippet and copy its lifecycle pattern rather than inventing equivalent calls.
3. Validate dtype, shape, semantic, and ownership rules before proposing or editing code.
4. Release each fetched ovstage group and read/query handle according to the referenced examples; preserve C compatibility lifetimes when maintaining C code.
5. When changing code, run the narrow docs test or example that owns the snippet whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- Deprecated ovrtx compatibility reads retain their documented unsupported-type limits for string arrays, asset arrays, and timecode attributes.
- Deprecated ovrtx compatibility reads reject write-only conversion semantics; a stored matrix role can still be returned as `OVRTX_SEMANTIC_MATRIX`.
- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

`stage.read_attributes` reads one or more requested attributes through an ovstage query. Each fetched read group owns a shared logical prim-row layout and one or more attribute columns. Consume each column's DLPack tensors, then release the group and read handle.

Use `ovstage.OrdinalRange.latest(ordinal)` to read a snapshot at a sealed ordinal. It returns `OUT_OF_RANGE` if a queried path of a requested attribute changed after that ordinal; use `ovstage.ORDINAL_MAX` as the ordinal to read current values instead.

For mapping (zero-copy writes into ovstage buffers), see the `mapping-attributes` skill.

## USD Type Lookup

Use this table to answer "how do I read USD type X?" Ovstage uses `stage.read_attributes` for both scalar and array-valued columns; inspect each returned column's `is_array` flag. Deprecated C bindings set `binding.binding_desc.attribute_type.is_array = true` for array reads. Read results in both languages use scalar lanes and trailing component dimensions; C binding types still use `DLDataType::lanes` to describe storage width.

| USD type(s) | Python read result | C binding dtype | Notes |
|---|---|---|---|
| `bool` / `bool[]` | `(N,)` or `(M,)`, `np.bool_` | `{kDLBool, 8, 1}` | |
| `uchar` / `uchar[]` | `np.uint8` | `{kDLUInt, 8, 1}` | |
| `int`, `int2`, `int3`, `int4` and arrays | `np.int32`, trailing shape `()`, `(2,)`, `(3,)`, `(4,)` | `{kDLInt, 32, lanes}` | |
| `uint` / `uint[]` | `np.uint32` | `{kDLUInt, 32, 1}` | |
| `int64` / `int64[]` | `np.int64` | `{kDLInt, 64, 1}` | |
| `uint64` / `uint64[]` | `np.uint64` | `{kDLUInt, 64, 1}` | |
| `half`, `half2`, `half3`, `half4` and arrays | `np.float16`, trailing shape by component count | `{kDLFloat, 16, lanes}` | |
| `float`, `float2`, `float3`, `float4` and arrays | `np.float32`, trailing shape by component count | `{kDLFloat, 32, lanes}` | Authored scalar USD `float3` currently populates as zero; prefer role-bearing `point3f`, `normal3f`, `vector3f`, or `color3f` for values read from USD. |
| `double`, `double2`, `double3`, `double4` and arrays | `np.float64`, trailing shape by component count | `{kDLFloat, 64, lanes}` | |
| `point3*`, `normal3*`, `vector3*`, `color3*`, `color4*`, `texCoord2f` and arrays | numeric dtype by suffix (`h/f/d`), trailing role dimensions | same numeric dtype/lanes as storage | Roles are not surfaced as tensor metadata; they still matter for USD population and schema intent. |
| `quat*` and arrays | numeric dtype by suffix, shape `(N, 4)` or `(M, 4)` | `{kDLFloat, bits, 4}` | Runtime component order is `(i, j, k, real)`, while USDA authoring order is `(real, i, j, k)`. |
| `matrix2d`, `matrix3d`, `matrix4d`, `frame4d` and arrays | `np.float64`, matrix roles use square trailing dimensions; untyped tuples use flat component dimensions | `{kDLFloat, 64, 4/9/16}` | Matrix4d reads as `(N, 4, 4)` when the matrix role is known. |
| `extent`, `_worldExtent` | `np.float64`, shape `(N, 6)` | `{kDLFloat, 64, 6}` | `extent` is local-space; `_worldExtent` is world-space. |
| `string` | `uint8` byte array, decode as UTF-8 | `{kDLUInt, 8, 1}` with `is_array=true` | Scalar USD strings are represented as byte arrays. This is not `string[]`; string arrays are not supported. Use `token[]` for string-like arrays. |
| `token` / `token[]` | raw `uint64` token IDs | `{kDLUInt, 64, 1}` | Wrap each ID in `ovstage.Token(id)` before calling `paths.token_to_string()`. |
| `asset` | `uint64` token id pairs with `AttributeSemantic.ASSET_PATH_ID` | `{kDLUInt, 64, 2}` with `is_array=false` | One `(authored, resolved)` pair per prim. Resolve each ID with `paths.token_to_string(ovstage.Token(id))`. Token id 0 is the empty token, so a resolved id of 0 means the path resolved to nothing. |
| `relationship` | raw `uint64` path IDs | path IDs / path-list semantics | Resolve path IDs with `paths.path_to_string(ovstage.PrimPath(id))`. Use relationship-specific skills for schema-specific behavior. |
| `timecode` / `timecode[]` | unsupported | unsupported | |

## Python

A Python `ReadGroup` exposes the shared prim rows through `prim_count` and
`prim_index(i)`, and its `columns` tuple contains the attributes aligned to
those rows. Each `ReadColumn` exposes its own `attribute`, `is_array`, and
`semantic` metadata plus tensor/data-row access through `tensor()`, `array()`,
`dlpack()`, and `data_row_index()`. Keep the group alive while using any column
or borrowed view.

### Scalar read

For a single-attribute read, select the group's sole `ReadColumn`. Its `dlpack(0)` method returns a `ManagedDLTensor`; convert it with `np.from_dlpack()` for a zero-copy NumPy view. Use `column.data_row_index(i)` when mapping logical group row `i` to the column's physical data row.

> **Source:** `tests/docs/python/test_attribute_read.py` snippet `doc-read-attribute-scalar`

### Deprecated compatibility: scalar read into a destination

Pass `dest=` with a DLPack-compatible tensor (NumPy array, Warp array, etc.). The read writes directly into `dest`; the returned tensor aliases the same memory. The `dest` dtype must match how the runtime stores the attribute.

> **Source:** `tests/docs/python/test_attribute_read.py` snippet `doc-read-attribute-dest-tensor`

### Array read

Fetch the array-valued group, copy or consume its DLPack tensor, and release the group.

> **Source:** `tests/docs/python/test_attribute_read.py` snippet `doc-read-array-attribute`

### Async read

Wait for the ovstage read handle, fetch groups, then release each group and the read handle.

> **Source:** `tests/docs/python/test_attribute_read.py` snippet `doc-read-attribute-async`

### Deprecated compatibility: GPU destination (CUDA)

Allocate the destination on the GPU via any DLPack-compatible allocator (e.g. Warp). Pass the CUDA stream handle so the read is stream-ordered with your GPU work.

> **Source:** `tests/docs/python/test_attribute_read.py` snippet `doc-read-attribute-cuda-dest`

### Authored attribute matrix

Python raw snippets:

| Type/pattern | Snippet |
|---|---|
| `bool` | `doc-read-usd-bool` |
| `int` | `doc-read-usd-int` |
| `float` | `doc-read-usd-float` |
| `point3f` | `doc-read-usd-point3f` |
| `point3f[]` | `doc-read-usd-point3f-array` |
| `normal3f` | `doc-read-usd-normal3f` |
| `vector3f` | `doc-read-usd-vector3f` |
| `color3f` | `doc-read-usd-color3f` |
| `matrix4d` | `doc-read-usd-matrix4d` |
| `quatf` | `doc-read-usd-quatf` |
| `string` | `doc-read-usd-string` |

The snippets listed in this table live in `tests/docs/python/test_all_attributes.py`.

These examples use `ovstage.PathDictionary` to obtain attribute-name tokens,
read through a reusable ovstage query, copy each returned tensor, and release
its result group.

### Local and world-space extents

`extent` is the authored local-space extent. `_worldExtent` is populated as the transformed world-space extent.

> **Source:** `tests/docs/python/test_all_attributes.py` snippet `doc-extent-world-extent`

## C

### Scalar read

> **Source:** `tests/docs/c/test_attribute_read.cpp` snippet `doc-read-attribute-scalar-c`

### Array read

Under ovstage, array-vs-scalar kind is not part of the read call — each returned `ovstage_read_column_t::is_array` reflects that column's declared kind. Under the deprecated `ovrtx_read_attribute` compat shim, set `binding.binding_desc.attribute_type.is_array = true` explicitly (defaulted to `false` by `ovrtx_make_binding_desc`).

> **Source:** `tests/docs/c/test_attribute_read.cpp` snippet `doc-read-array-attribute-c`

### Supported authored attribute read snippets in C

The snippets below are ovstage-native: `ovstage_read_attributes` against a `DocsQueryAndToken` (single-prim query + interned attribute token), one capacity-one `ovstage_fetch_read_next` per matched group, `ovstage_release_groups` per group, then `ovstage_release_read`. Each single-attribute snippet selects the group's sole column and asserts `column.data.tensor_count > 0` before dereferencing `column.data.tensors[0]`.

C raw snippets:

| Type/pattern | Snippet |
|---|---|
| scalar numeric | `doc-read-usd-float-c` |
| lane-3 scalar | `doc-read-usd-point3f-c` |
| lane-3 array | `doc-read-usd-point3f-array-c` |
| lane-16 matrix | `doc-read-usd-matrix4d-c` |
| quaternion | `doc-read-usd-quatf-c` |
| token | `doc-read-usd-token-c` |
| token array | `doc-read-usd-token-array-c` |
| string bytes | `doc-read-usd-string-c` |
| scalar asset id pair | `doc-read-usd-asset-c` |

The snippets listed in this table live in `tests/docs/c/test_all_attributes.cpp`.

C token snippets include path-dictionary resolution because the C API exposes `ovstage_get_path_dictionary()`. As of ovstage 0.2, reading a scalar `asset` returns `ASSET_PATH_ID` token id pairs (`{kDLUInt, 64, 2}`, `is_array=false`, one `(authored, resolved)` pair per prim). Resolve both ids through the path dictionary. A resolved id of 0 is the empty token, which means the path resolved to nothing. On ovstage 0.1.x the same read returned `{kDLUInt, 64, 2}` pairs with semantic `NONE`, and on 0.1.0 single-prim reads failed with END_OF_ITERATION. The `doc-read-usd-asset-c` / `doc-write-usd-asset-c` snippets are runtime-validated by `AllAttributesTest.AssetReadWriteSnippets`.

### Local and world-space extents in C

> **Source:** `tests/docs/c/test_all_attributes.cpp` snippet `doc-extent-world-extent-c`

## Key Types / Functions

| Python (ovstage) | C (ovstage) | C (deprecated ovrtx compat) |
|---|---|---|
| `stage.read_attributes(query, attrs, ordinal_range)` | `ovstage_read_attributes(stage, query, tokens, count, range, &read_handle)` | `ovrtx_read_attribute(renderer, &binding, &read_dest, &read_handle)` + fetch/release |
| `read.fetch_next()` / `stage.release_group(group)` | `ovstage_fetch_read_next(stage, read_handle, timeout, &group, 1, &count)` / `ovstage_release_groups(stage, &group, 1)` | `ovrtx_fetch_read_result(...)` / `ovrtx_release_read_result(...)` |
| `ovstage.OrdinalRange.latest(ordinal)` | `ovstage_ordinal_range_t range{}; range.end_ordinal = ordinal;` | stream-ordered compatibility read |

Ovstage C result layout:
- `ovstage_read_group_t::prims` defines the group's logical prim rows. `.list`, `.count`, `.offset`, and `.index_map` enumerate the matched prims; the prim index map applies gather/reorder semantics.
- `ovstage_read_group_t::columns` / `.column_count` is the ordered array of attributes present for those rows. Logical row `i` names the same prim in every column, but each column resolves its own physical value row through its `data` mapping.
- Each `ovstage_read_column_t` carries `.attribute`, `.is_array`, `.semantic`, `.data`, `.meta`, `.ordinal`, and `.is_delete`. Attribute identity, array-vs-scalar kind, authored semantic, values, and attribute metadata are exposed through the column rather than the group.
- `column.data.tensors` / `column.data.tensor_count` is the column's DLTensor array. `tensor_count==1` under the packed-uniform layout every snippet uses; always assert `tensor_count > 0` before dereferencing `tensors[0]`.
- Each returned read or mapped `DLTensor` has `dtype.lanes=1`, a leading data-row or array-element axis, and trailing component axes: matrix4d uses `[N,4,4]`, point3f uses `[N,3]`. Strides count scalar elements. Binding declarations and canonical write inputs retain the lane-based storage width. For logical group row `i`, test `column.data.mask` when present, then select physical row `column.data.index_map[i]` when present or row `i` otherwise.
- Route multi-attribute reads (for example, `doc-extent-world-extent-c`) by iterating `group.columns` and comparing each `column.attribute` to the interned tokens. One token can yield more than one column across groups: when the queried prims use the name for several column types and no ovstage write has given the name an identity, each prim is served with the type of its own column, so the groups differ in `dtype` and `is_array`. Read the shape from each column rather than from the first one. Such a name cannot be served to a GPU destination, so a device read returns no column for it and serves the rest of the read normally (ovstage >= 0.2).
- An attribute absent from every logical row is omitted. Partial presence is represented by that column's data mapping or by a separate group, so callers must accept valid single-column groups. Different groups have no ordering or partition guarantee.
- The group owns all borrowed prim, column, tensor, mapping, and metadata views. Keep it alive while consuming any column and call `ovstage_release_groups` once those views are no longer used.

Deprecated C compat result layout (`ovrtx_read_output_t`):
- Fixed-size reads: `buffer_count == 1`, single tensor with leading shape `[prim_count]` and type-aware trailing axes.
- Array reads: `buffer_count == prim_count`, one tensor per prim (variable length).
- When a caller-supplied `read_dest` tensor was passed in: `buffer_count == 0` (data landed in your tensor).

## Troubleshooting

- **Matrix shape needs type information.** Typed matrix4d values read as `[N,4,4]`; an untyped 16-component tuple reads as `[N,16]`. Use the authored semantic when interpreting OVStage results. When creating a matrix attribute through OVStage with a shape-based write, set `semantic=AttributeSemantic.MATRIX` in Python or `OVSTAGE_SEMANTIC_MATRIX` in C; shape alone does not assign the matrix semantic.
- **Generic authored USD attributes require opt-in population.** Root-layer `customLayerData.populateAllAuthoredAttributes = true` asks the runtime to populate authored attributes beyond the normal schema set. Use it only when needed: populating everything can dramatically increase memory usage on assets with many unused properties. See `loading-usd` for the layer metadata tradeoff.
- **Schema-owned attributes fix the element type.** `omni:rtx:rtpt:maxBounces` is stored as `uint32` even if you wrote it as `int32`. When allocating a `dest` tensor, match the runtime's dtype (`np.uint32`) — not what you wrote.
- **Release fetched ovstage groups explicitly.** Call `stage.release_group(group)` after consuming or copying each group, and release manually managed read/query handles.
- **Ovstage reads carry array-vs-scalar kind in each returned column, not the request.** Check `column.is_array` after `ovstage_fetch_read_next` — the read call itself takes no `is_array` parameter. The deprecated `ovrtx_read_attribute` compat shim still requires `binding.binding_desc.attribute_type.is_array = true` on the binding (defaulted to `false` by `ovrtx_make_binding_desc`).
- **Ovstage queries own their prim-list storage; ovrtx compat bindings borrow.** `ovstage_query_from_path_list` retains a reference to the passed `ovx_primpath_list_t` until `ovstage_release_query` fires — the caller then calls `path_dictionary_release_path_list_reference`. The deprecated `ovrtx_make_binding_desc` stores the `ovx_string_t*` prim path array you pass without copying; keep it alive until the read has been enqueued, waited, fetched, and released.
- **Unsupported authored types are tested as absent.** `tests/docs/data/all-attributes.usda` deliberately authors `string[]`, `asset[]`, custom relationships, `timecode`, and `timecode[]`; the all-attributes tests assert they are not populated by the current runtime.

## Deprecated Standalone APIs

The renderer attribute-read APIs in this skill are deprecated in 0.4 and retained
for compatibility. New code should read through an ovstage query, consume fetched
groups, and release each group and read handle according to ovstage ownership rules.

See `docs/core/ovstage_integration.rst`, `skills/update-0_3-0_4-c/SKILL.md` and `skills/update-0_3-0_4-python/SKILL.md`.

## Related skills

- `stage-queries` — discover prims and their attribute schemas before reading.
- `writing-attributes` — write values that can then be read back.
- `mapping-attributes` — zero-copy mapping (no fetch step).
- `async-operations` — polling, timeouts, the two-phase `Operation`/`PendingFetch` lifecycle.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
