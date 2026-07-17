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
name: writing-attributes
description: >
  Writing scalar and array attribute data to prims. Use when user asks to write an
  attribute, set a property, change a material, set a color, or modify mesh data.
license: LicenseRef-NvidiaProprietary
version: "0.3.0"
author: NVIDIA ovrtx
tags:
  - ovrtx
  - attributes
  - writing
tools:
  - Read
  - Grep
---

# Writing Attributes

## When to Use

Use this skill when the user asks to write an attribute, set a property, change a material, set a color, or modify mesh data.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, or both.
- Prim paths, attribute name, USD value type, scalar versus array shape, and desired values.
- Data source location, dtype, semantic conversion, ordinal, and write-floor publication.
- Whether the write is one-shot, repeated with a stable target, or needs direct mapped-buffer access.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Use `attribute-bindings` for repeated writes to the same prims/attribute, and `mapping-attributes` for zero-copy direct writes.
- Use `binding-materials` when the request is specifically to set `material:binding`.

## Instructions

1. Identify the target language, prim paths, attribute name, value kind, data shape, memory target, and sync/async requirement.
2. Read the matching source snippet and copy its lifecycle pattern rather than inventing equivalent calls.
3. Validate dtype, shape, semantic, and ownership rules before proposing or editing code.
4. Wait for the ovstage write, then advance the write floor before rendering its ordinal; preserve C compatibility lifetimes when maintaining C code.
5. When changing code, run the narrow docs test or example that owns the snippet whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- Deprecated ovrtx compatibility writes retain their documented unsupported-type limits for string arrays, asset arrays, and timecode attributes.
- For ovstage token and path values, intern IDs through `ovstage.PathDictionary` and use the matching `AttributeSemantic`.
- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

Beyond transforms, ovstage can write arbitrary attributes to prims: colors, visibility, mesh geometry, string tokens, and more. The DLTensor dtype must exactly match the USD attribute schema.

There are two categories:
- **Scalar attributes** -- one value per prim (e.g., a color, a transform)
- **Array attributes** -- variable-length per prim (e.g., mesh points, face vertex counts)

## Tensor layout

Ovstage Python and the C compatibility API use lane-based DLTensor attribute layouts.

### Python ovstage — lane-based attributes

Scalar values can use NumPy arrays directly. For vectors and matrices, wrap NumPy storage with `ovstage.make_dltensor`, set the logical element count in `shape`, and set the component count in `dtype.lanes`:

| USD type | NumPy storage | ovstage DLTensor |
|---|---|---|
| `int` / `float` scalar for N prims | `(N,)` | `shape=[N]`, lanes 1 |
| `float3` / `point3f` scalar for N prims | `(N, 3)` | `shape=[N]`, lanes 3 |
| `float4` / `color4f` scalar for N prims | `(N, 4)` | `shape=[N]`, lanes 4 |
| 4x4 matrix for N prims | `(N, 4, 4)` | `shape=[N]`, lanes 16 |
| `int[]` array with M elements on one prim | `(M,)` | `shape=[M]`, lanes 1 |
| `float3[]` / `point3f[]` with M elements on one prim | `(M, 3)` | `shape=[M]`, lanes 3 |

> **Source:** `tests/docs/python/test_attribute_shapes.py` snippets `doc-shape-scalar-int32`, `doc-shape-float3-array`, `doc-shape-mat4-array`.

### C — lane-based attributes

The C API uses `DLDataType::lanes` for multi-component attribute reads and writes. The shape counts logical attribute elements; the lane count holds the vector or matrix component count:

| USD type | C DLTensor shape | C `DLDataType` |
|---|---|---|
| `int` / `float` scalar for N prims | `[N]` | `{kDLInt/kDLFloat, bits, 1}` |
| `float3` / `point3f` scalar for N prims | `[N]` | `{kDLFloat, 32, 3}` |
| 4x4 double matrix for N prims | `[N]` | `{kDLFloat, 64, 16}` |
| `int[]` array with M elements on one prim | `[M]` | `{kDLInt, 32, 1}` |
| `float3[]` / `point3f[]` with M elements on one prim | `[M]` | `{kDLFloat, 32, 3}` |

> **Source:** `tests/docs/c/test_attribute_shapes.cpp` snippets `doc-shape-scalar-int32-c`, `doc-shape-float3-array-c`, `doc-shape-mat4-array-c`.

For a C `point3f[]` attribute with 10 points, write or read one tensor with `shape=[10]` and `dtype={kDLFloat, 32, 3}`. Rendered output/AOV tensors are not attribute tensors; in C they use channel-last shapes such as `[height, width, channels]` with `dtype.lanes=1`.

## USD Type Lookup

Use this table to answer "how do I write USD type X?" For ovstage, pass `is_array=True` for array-valued attributes. The C compatibility API sets `binding.binding_desc.attribute_type.is_array = true`.

| USD type(s) | Python value to write | C tensor dtype | Notes |
|---|---|---|---|
| `bool` / `bool[]` | `np.bool_`, shape `(N,)` or per-prim `(M,)` | `{kDLBool, 8, 1}` | |
| `uchar` / `uchar[]` | `np.uint8` | `{kDLUInt, 8, 1}` | |
| `int`, `int2`, `int3`, `int4` and arrays | `np.int32`, trailing shape `()`, `(2,)`, `(3,)`, `(4,)` | `{kDLInt, 32, lanes}` | |
| `uint` / `uint[]` | `np.uint32` | `{kDLUInt, 32, 1}` | |
| `int64` / `int64[]` | `np.int64` | `{kDLInt, 64, 1}` | |
| `uint64` / `uint64[]` | `np.uint64` | `{kDLUInt, 64, 1}` | |
| `half`, `half2`, `half3`, `half4` and arrays | `np.float16`, trailing shape by component count | `{kDLFloat, 16, lanes}` | |
| `float`, `float2`, `float3`, `float4` and arrays | `np.float32`, trailing shape by component count | `{kDLFloat, 32, lanes}` | Direct runtime writes to scalar `float3` work, but authored scalar USD `float3` population is bugged in the current runtime. Prefer role-bearing `point3f`, `normal3f`, `vector3f`, or `color3f` for USD-authored data. |
| `double`, `double2`, `double3`, `double4` and arrays | `np.float64`, trailing shape by component count | `{kDLFloat, 64, lanes}` | |
| `point3*`, `normal3*`, `vector3*`, `color3*`, `color4*`, `texCoord2f` and arrays | numeric dtype by suffix (`h/f/d`), trailing role dimensions | same numeric dtype/lanes as storage | Roles are schema intent; tensor storage is numeric. |
| `quat*` and arrays | numeric dtype by suffix, shape `(N, 4)` or `(M, 4)` | `{kDLFloat, bits, 4}` | Write runtime order `(i, j, k, real)`, not USDA order `(real, i, j, k)`. |
| `matrix2d`, `matrix3d`, `matrix4d`, `frame4d` and arrays | `np.float64`, flattened trailing shape `(4,)`, `(9,)`, `(16,)`, `(16,)` | `{kDLFloat, 64, 4/9/16}` | Generic authored matrix attrs are flattened. Transform semantic writes may use `(N, 4, 4)` Python arrays or `{kDLFloat,64,16}` C tensors. |
| `extent`, `_worldExtent` | `np.float64`, shape `(N, 6)` | `{kDLFloat, 64, 6}` | Usually read-only from population; `extent` is local-space, `_worldExtent` is world-space. |
| `string` | UTF-8 `np.uint8` byte rows with `is_array=True` and `AttributeSemantic.STRING` | `{kDLUInt, 8, 1}` with `is_array=true` | One byte row represents one USD string value. |
| `token` / `token[]` | `np.uint64` IDs from `PathDictionary.intern_token()` with `AttributeSemantic.TOKEN_ID` | `{kDLUInt, 64, 1}` raw IDs with `OVRTX_SEMANTIC_TOKEN_ID`, or compatibility string helpers | Set `is_array` to match the USD attribute kind. |
| `asset` | UTF-8 `np.uint8` byte rows with `AttributeSemantic.ASSET_STRING` | `{kDLUInt, 64, 2}` | Deprecated C compatibility writes represent scalar assets as token pairs. |
| `relationship` | `np.uint64` IDs from `PathDictionary.intern_path()` with `is_array=True` and `AttributeSemantic.RELATIONSHIP_PATH_ID` | path string/path ID semantics | Use relationship-specific skills for schema-specific behavior. |
| `timecode` / `timecode[]` | unsupported | unsupported | |

## Python

### Array attribute write (mesh points)

> **Source:** `tests/docs/python/test_attribute_shapes.py` snippet `doc-shape-float3-array`

### Array attribute write (same pattern for other array schemas)

> **Source:** `tests/docs/python/test_attribute_shapes.py` snippet `doc-shape-float3-array`

### Prim modes

> **Source:** `tests/docs/python/test_attribute_bindings.py` snippet `doc-bind-attribute-write`

### Token array attribute

> **Source:** `tests/docs/python/test_attribute_bindings.py` snippet `doc-write-token-array`

### Path/relationship array attribute

> **Source:** `tests/docs/python/test_base.py` snippet `doc-bind-material`

### Deprecated compatibility: authored attribute matrix

Python raw snippets:

| Type/pattern | Snippet |
|---|---|
| `bool` | `doc-write-usd-bool` |
| `int` | `doc-write-usd-int` |
| `float` | `doc-write-usd-float` |
| `point3f` | `doc-write-usd-point3f` |
| `point3f[]` | `doc-write-usd-point3f-array` |
| `normal3f` | `doc-write-usd-normal3f` |
| `vector3f` | `doc-write-usd-vector3f` |
| `color3f` | `doc-write-usd-color3f` |
| `matrix4d` | `doc-write-usd-matrix4d` |
| `quatf` | `doc-write-usd-quatf` |
| `string` | `doc-write-usd-string` |
| `token` | `doc-write-usd-token` |
| `token[]` | `doc-write-usd-token-array` |

The snippets listed in this table live in `tests/docs/python/test_all_attributes.py`.

Use `ovstage.PathDictionary` to intern token and relationship strings, then write
the resulting IDs with `AttributeSemantic.TOKEN_ID` or
`AttributeSemantic.RELATIONSHIP_PATH_ID`. String and asset payloads use byte rows
with `AttributeSemantic.STRING` or `AttributeSemantic.ASSET_STRING`.

## C

### Generic scalar write in C

> **Source:** `tests/docs/c/test_attribute_bindings.cpp` snippet `doc-write-bound-attribute-c`

### Supported authored attribute write snippets in C

The snippets below are ovstage-native: they issue `ovstage_write_attribute` against a `DocsQueryAndToken` (single-prim query handle + interned attribute token) with an `ovstage_write_data_t` describing the DLTensor payload, `is_array`, and `OVSTAGE_SEMANTIC_*`. Each block advances the write floor and bumps the caller's tracked ordinal so a follow-up `latest(ordinal)` read observes the write. The ovrtx `ovrtx_write_attribute` + `ovrtx_binding_desc_or_handle_t` compatibility shim is still present for standalone-renderer callers but is not used by these snippets — the recommended path is attached ovstage.

C raw snippets:

| Type/pattern | Snippet |
|---|---|
| scalar numeric | `doc-write-usd-float-c` |
| lane-3 scalar | `doc-write-usd-point3f-c` |
| lane-3 array | `doc-write-usd-point3f-array-c` |
| lane-16 matrix | `doc-write-usd-matrix4d-c` |
| quaternion | `doc-write-usd-quatf-c` |
| token | `doc-write-usd-token-c` |
| token array | `doc-write-usd-token-array-c` |
| string bytes | `doc-write-usd-string-c` |
| scalar asset byte row (test SKIPPED — known ovstage gap) | `doc-write-usd-asset-c` |

The snippets listed in this table live in `tests/docs/c/test_all_attributes.cpp`. **The scalar-asset write snippet is currently under `GTEST_SKIP` alongside its read counterpart (`AllAttributesTest.AssetReadWriteSnippets`); this is a known issue tracked internally. Treat both `doc-read-usd-asset-c` and `doc-write-usd-asset-c` as *provisional / not runtime-validated* until it is resolved.**

## Key Types / Functions

| Python (ovstage) | C (ovstage) | C (deprecated ovrtx compat) |
|---|---|---|
| `stage.write_attribute(query, attr, ordinal=..., tensors=..., is_array=...)` | `ovstage_write_attribute(stage, query_handle, attr_ref, ordinal, write_data, prim_mode)` | `ovrtx_write_attribute(renderer, &binding, &buffer, access)` |
| `stage.advance_write_floor(ordinal, ovstage.Scope.ALL)` | `ovstage_advance_write_floor(stage, &desc)` with `desc.ordinal=N, desc.scope=OVSTAGE_SCOPE_ALL` | (renderer implicitly seals per step) |

Ovstage C write payload (`ovstage_write_data_t`):
- `.tensors` / `.tensor_count` — DLTensor array. `tensor_count==1` for the packed-uniform layout used by every snippet.
- `.is_array` — sole authority for fixed (`false`) vs. array (`true`) storage. Does NOT auto-derive from the DLTensor's shape.
- `.semantic` — `ovstage_attribute_semantic_t`, tag the write with the same geometric role the column was created under, or `OVSTAGE_SEMANTIC_NONE` to preserve an existing column's authored role.

Semantics (Python: `ovstage.AttributeSemantic`; C ovstage: `ovstage_attribute_semantic_t`; C ovrtx compat: `ovrtx_attribute_semantic_t`):
- `AttributeSemantic.NONE` / `OVSTAGE_SEMANTIC_NONE` / `OVRTX_SEMANTIC_NONE` -- generic data.
- `AttributeSemantic.MATRIX` / `OVSTAGE_SEMANTIC_MATRIX` / `OVRTX_SEMANTIC_XFORM_MAT4x4` -- matrix data.
- `OVRTX_SEMANTIC_XFORM_POS3d_ROT4f_SCALE3f` -- decomposed transform (C ovrtx compat only).
- `OVRTX_SEMANTIC_XFORM_POS3d_ROT3x3f` -- decomposed transform (C ovrtx compat only).
- `AttributeSemantic.RELATIONSHIP_PATH_ID` / `OVSTAGE_SEMANTIC_RELATIONSHIP_PATH_ID` -- interned relationship path IDs (write `is_array=true`).
- `AttributeSemantic.TOKEN_ID` / `OVSTAGE_SEMANTIC_TOKEN_ID` / `OVRTX_SEMANTIC_TOKEN_ID` -- interned token IDs.
- `AttributeSemantic.STRING` / `OVSTAGE_SEMANTIC_STRING` -- UTF-8 USD string bytes (write `is_array=true`, dtype `{kDLUInt, 8, 1}`).
- `AttributeSemantic.ASSET_STRING` / `OVSTAGE_SEMANTIC_ASSET_STRING` -- UTF-8 asset bytes (same shape as STRING).

In C, `ovstage_write_attribute` returns `ovstage_enqueue_result_t` which contains both `.status` (check for `OVSTAGE_OK`) and `.op_index` (for async tracking via `ovstage_wait_op`). Every doc-test snippet uses the shared `docs_wait_ovstage_no_errors(stage, op_index)` helper from `tests/docs/c/helpers.h` to wait + assert on op errors.

The deprecated `ovrtx_write_attribute` still returns `ovrtx_enqueue_result_t` and tracks via `ovrtx_wait_op` for standalone-mode callers.

Deprecated renderer data access modes (Python: `from ovrtx import DataAccess`):
- `DataAccess.SYNC` -- copies data during the call, safe to free after return
- `DataAccess.ASYNC` -- data accessed later during stream execution, must keep alive; pass `cuda_stream=` or `cuda_event=` for GPU synchronization. Not allowed with string data.

## Troubleshooting

- Array attribute dtype must exactly match the USD schema. Using numpy's default `float64` for a `float3[]` attribute (which expects `float32`) will cause errors.
- In the current runtime, authored scalar USD `float3` values may be created but populated as zero by `populateAllAuthoredAttributes`. If a value needs to come from USD, author it as a role-bearing type such as `vector3f`, `point3f`, `normal3f`, or `color3f`. Direct runtime writes to scalar `float3` still work.
- Quaternion tensors use ovrtx/Fabric lane order `(i, j, k, real)`. USDA `quat*` values are authored as `(real, i, j, k)`, so reading `quatd`, `quatf`, or `quath` attributes reorders the components into `(i, j, k, real)`, and writes should use that runtime tensor order.
- Deprecated renderer string writes using `Semantic.PATH_STRING` or `Semantic.TOKEN_STRING` require `DataAccess.SYNC`.
- Deprecated renderer compatibility writes do not support string arrays, asset arrays, or timecode attributes.
- Custom relationships are not populated by the generic authored-attribute path. Specific relationships used by supported schemas, such as `material:binding` and shader connections, are handled by their schema/population code paths; arbitrary custom relationships are ignored today.
- Unsupported authored types are covered by negative tests in `tests/docs/python/test_all_attributes.py` and `tests/docs/c/test_all_attributes.cpp`; if one starts populating, keep this documentation and those tests in sync.
- For array attributes in Python, pass a list of tensors (one per prim), not a single tensor. NumPy arrays, Warp arrays, and any `__dlpack__`-compatible objects are accepted directly.
- `PrimMode.UPSERT` creates absent prims and updates existing prims. `PrimMode.INSERT` is create-only. When a write creates a column whose authored interpretation is not generic, pass the matching `AttributeSemantic`.
- For ovstage token and relationship writes, intern strings with `PathDictionary` and write the resulting IDs with `TOKEN_ID` or `RELATIONSHIP_PATH_ID` semantics.
- The ovstage-native "binding" is the pair (`ovstage_query_handle_t`, `ovx_token_t attr_token`) reserved with `ovstage_query_from_path_list` + `path_dictionary_create_tokens_from_strings`. Both are stable across writes/reads until released via `ovstage_release_query` and `path_dictionary_release_path_list_reference`. `tests/docs/c/helpers.h` factors the setup into `DocsQueryAndToken` + `docs_make_query_and_token` / `docs_release_query_and_token` — every C attribute doc-test uses those helpers to keep the boilerplate out of `[snippet:]` blocks. The deprecated `ovrtx_make_binding_desc` still exists for standalone-mode callers and borrows its input `ovx_string_t` prim path array; keep it alive until the write completes.
- `dirty_bits` is a bitvector with 1 bit per prim -- the byte array size must be `(prim_count + 7) / 8`.
- In C, `dirty_bits` support three combination modes via `ovrtx_write_bits_t` in the `ovrtx_input_buffer_t.dirty_bits_mode` field: `OVRTX_DIRTY_MASK_REPLACE` (default -- replace existing mask), `OVRTX_DIRTY_MASK_OR` (merge with existing), `OVRTX_DIRTY_MASK_AND` (intersect with existing).

C convenience helpers for string attributes (`#include <ovrtx/ovrtx_attributes.h>`):
- `ovrtx_set_path_attributes(renderer, paths, count, attr_name, path_values)` -- write path/relationship attributes. Each prim gets a single-element array (relationships are always arrays in USD).
- `ovrtx_set_token_attributes(renderer, paths, count, attr_name, token_values)` -- write token string attributes (one per prim).

> **Source:** `tests/docs/c/test_attribute_helpers.cpp` snippet `doc-set-token-attributes-c`

## Deprecated Standalone APIs

The renderer attribute-write APIs in this skill are deprecated in 0.4 and retained
for compatibility. New code should write through ovstage with an application-owned
ordinal, wait for completion, and advance the write floor before rendering.

See `docs/core/ovstage_integration.rst`, `skills/update-0_3-0_4-c/SKILL.md` and `skills/update-0_3-0_4-python/SKILL.md`.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
