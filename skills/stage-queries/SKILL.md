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
name: stage-queries
description: >
  Discovering prims on the runtime stage and inspecting their attribute schemas. Use
  when user asks to find prims by type, filter by attribute, list all prims, or look up
  attribute types before reading or writing them.
license: LicenseRef-NvidiaProprietary
version: "0.3.0"
author: NVIDIA ovrtx
tags:
  - ovrtx
  - usd
  - queries
tools:
  - Read
  - Grep
---

# Stage Queries

## When to Use

Use this skill when the user asks to find prims by type, filter by attribute, list all prims, or look up attribute types before reading or writing them.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, or both.
- Query goal: list all prims, filter by prim type, require/exclude attributes, or inspect attribute schemas before read/write.
- Filter predicates, requested attribute tokens, and whether names must be resolved through a path dictionary.
- Desired execution mode: Python ovstage query or C compatibility query.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Use this before attribute read/write skills when the target prim list or schema is unknown.

## Instructions

1. Identify whether the caller needs all prims, prims by type, prims with required attributes, or a filtered include/exclude query.
2. Read the matching Python or C query snippet before choosing filter fields or result traversal.
3. For async queries, preserve the two-phase wait/fetch lifecycle before reading result dictionaries or C result arrays.
4. In C, resolve path and attribute IDs through the path dictionary before presenting names to users.
5. When changing code, run the stage-query docs test that owns the snippet whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

`stage.query` finds prims on ovstage that match a filter. A query handle can be reused by subsequent ovstage read, write, and map calls, so a typical workflow is:

1. Query to discover prims and/or their attribute schemas.
2. Decide what to read/write based on the result.
3. Reuse the query handle to read or write without re-resolving paths.

Build an `ovstage.Filter` from predicates such as `usd-prim-type` or `usd-path`. Pass interned attribute tokens through `attrs` when the query should report specific columns. The deprecated renderer query remains useful only for compatibility cases that require its OR/NOT filter shape.

## Python

### Discover every prim (no attribute descriptors)

> **Source:** `tests/docs/python/test_stage_query.py` snippet `doc-query-prims-basic`

### Filter by USD prim type

> **Source:** `tests/docs/python/test_stage_query.py` snippet `doc-query-prims-by-type`

### Request specific attribute descriptors

Intern requested names through `ovstage.PathDictionary`, then inspect the attribute token ids reported by the result.

> **Source:** `tests/docs/python/test_stage_query.py` snippet `doc-query-prims-with-attributes`

### Deprecated compatibility: combine OR and NOT filters

> **Source:** `tests/docs/python/test_stage_query.py` snippet `doc-query-require-any-exclude`

### Async query

An ovstage query can be waited explicitly before calling `.result()`. Release manually created queries when they are no longer needed, or use a context manager.

> **Source:** `tests/docs/python/test_stage_query.py` snippet `doc-query-prims-async`

## C

### Basic query

> **Source:** `tests/docs/c/test_stage_query.cpp` snippet `doc-query-prims-basic-c`

### Filter by prim type

> **Source:** `tests/docs/c/test_stage_query.cpp` snippet `doc-query-prims-by-type-c`

### Filter by attribute existence

> **Source:** `tests/docs/c/test_stage_query.cpp` snippet `doc-query-has-attribute-c`

### Combine OR and NOT filters

> **Source:** `tests/docs/c/test_stage_query.cpp` snippet `doc-query-require-any-exclude-c`

### Empty specific-attribute lists

> **Source:** `tests/docs/c/test_stage_query.cpp` snippet `doc-query-specific-empty-attributes-c`

### Path dictionary round-trip

The renderer's path dictionary resolves `ovx_primpath_t` / `ovx_token_t` handles to strings and back. It is valid for the lifetime of the renderer — no release call is required.

> **Source:** `tests/docs/c/test_stage_query.cpp` snippet `doc-path-dictionary-resolve-c`

Python ovstage code should use `ovstage.PathDictionary` to intern attribute tokens and create path lists.

## Key Types / Functions

| Python | C |
|--------|---|
| `stage.query(filter=..., attrs=...)` | `ovrtx_query_prims(renderer, &desc, &query_handle)` + `ovrtx_fetch_query_results(...)` |
| `ovstage.Filter` / `ovstage.Predicate` | `OVRTX_FILTER_*` compatibility filters |
| `ovstage.PathDictionary(stage)` | `ovrtx_get_path_dictionary(renderer, &pd)` |

C result shape:
- `ovrtx_query_result_t.groups` — one `ovrtx_query_prim_group_t` per attribute-schema bucket.
- Each group's `prim_list_handle` is a persistent `ovx_primpath_list_t` that plugs into `ovrtx_binding_desc_t::prims_list_handle`.
- Attribute names are returned as tokens — resolve via the path dictionary's `get_strings_from_tokens`.

## Troubleshooting

- In C, the pointers in `ovrtx_query_result_t` and `ovrtx_query_prim_group_t` become invalid after `ovrtx_release_query_results()`. Copy anything you want to keep.
- Deprecated renderer queries use `AttributeFilterMode`; `SPECIFIC` with an empty `attribute_names` list returns no descriptors, while `ALL` returns every descriptor and `NONE` performs lightweight discovery.
- Deprecated renderer query descriptors report relationship-valued attributes with `Semantic.PATH_ID`, not `PATH_STRING`.
- Ovstage query results return attribute-name token IDs. Resolve them with `ovstage.PathDictionary.token_to_string()`.
- An empty deprecated renderer filter matches every prim; pair it with `AttributeFilterMode.NONE` for the cheapest full-stage walk.

## Deprecated Standalone APIs

`query_prims*` is deprecated in 0.4 and retained for compatibility. New code should
query ovstage directly and use the ovstage-owned path dictionary for path lists and
token identities.

See `docs/core/ovstage_integration.rst`, `skills/update-0_3-0_4-c/SKILL.md` and `skills/update-0_3-0_4-python/SKILL.md`.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
