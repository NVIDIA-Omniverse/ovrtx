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
name: update-0_3-0_4-c
description: >
  Upgrade skill: migrate user C/C++ application code from ovrtx 0.3.x standalone
  stage APIs to ovrtx 0.4.x attached to ovstage 0.1.x. Use when the user asks to
  "upgrade from 0.3 to 0.4 with ovstage", "ovrtx 0.4 ovstage 0.1 migration",
  "migrate my ovrtx app", or "port my application to ovstage". Reference
  implementations: `examples/c/minimal` and `examples/c/status-queries` (Recipe A).
license: LicenseRef-NvidiaProprietary
version: "0.4.0"
author: NVIDIA ovrtx
tags:
  - ovrtx
  - upgrade
  - "0.4"
  - ovstage
  - c/c++

tools:
  - Read
  - Grep
  - Edit
---

# Update 0.3 to 0.4 + ovstage 0.1 (C API)

Standalone ovrtx 0.3.x stage APIs -> ovrtx 0.4.x + ovstage 0.1.x attached mode, for **user application code**.

## Version Scope

| | Version | What changes |
|---|---|---|
| Source | ovrtx 0.3.x | Standalone stage ownership: `ovrtx_open_usd_*`, `ovrtx_write_attribute`, `ovrtx_query_prims`, `ovrtx_step` with the renderer's own Fabric |
| Target ovrtx | ovrtx 0.4.x | Attach APIs (`ovrtx_attach_ovstage`, `ovrtx_update_from_stage`, `ovrtx_step_with_stage`); `OVRTX_DEPRECATED` markers on stage-building/query/write/read entry points in [`../../include/ovrtx/ovrtx.h`](../../include/ovrtx/ovrtx.h) |
| New dependency | ovstage 0.1.x | Scene data plane (`<ovstage/ovstage.h>`), population bridge (`<ovstage/ovstage_population.h>`), ordinal-keyed writes |


## When to Use

Use this skill when the user asks to upgrade an existing C/C++ ovrtx **application** from 0.3.x to 0.4.x, where the same code must now feed the renderer through an attached ovstage instance. Typical prompts: *"upgrade from 0.3 to 0.4 with ovstage"*, *"ovrtx 0.4 ovstage 0.1 migration"*, *"migrate my ovrtx app"*, *"port my application to ovstage"*.

Do **not** use this skill for:

- 0.2 -> 0.3 (see [`update-0_2-0_3`](../../skills/update-0_2-0_3/SKILL.md)).
- Python migration — only the C API is covered here.

**In scope for example work:** porting or validating the public C examples `minimal` and `status-queries` (Recipe A — one-shot load + render). These are the canonical reference implementations for this skill.

**Out of scope for example work:** `material-editor`, `vulkan-interop`, `lidar`, `radar`, and Python examples — blocked on ovstage API gaps or sensor output (see Example Port Status below).

## Inputs

Resolve inputs in this order:

- Target language: C or C++ (skill covers only the C API surface).
- Dependency manager and package pin (the app's `CMakeLists.txt` / `ovrtx.cmake` or equivalent must be able to add `ovstage::ovstage_static`).
- Which deprecated ovrtx entry points the app currently calls (see the mapping table below).
- Whether the app does **one-shot** scene loading (open a USD file once, then step) or **incremental** scene edits (references, resets, attribute writes, time samples).
- Whether the app uses picking, selection outlines, or the renderer's path dictionary — these stay on ovrtx and change independently.

## Prerequisites

- Read [`../update-0_3-0_4-common/Reference.md`](../update-0_3-0_4-common/Reference.md) for language-agnostic ownership, ordering, path-dictionary, transform, exposure, and async-boundary guidance.
- Read the `CHANGELOG.md` `[0.4.0]` section in [`../../CHANGELOG.md`](../../CHANGELOG.md) for release-level context, but if any bullet contradicts this skill or the current doxygen in `ovrtx.h`, trust the header and this skill. The definitive statements for the attach-mode update contract live at the top of the `[0.4.0]` `### Changed` block.
- The app must be able to pull `ovstage` 0.1.x (a new dependency in 0.4). Confirm the CMake / package fetch step provides both `ovrtx::ovrtx_static` and `ovstage::ovstage_static`.
- Preserve user code structure. This is an API migration, not a refactor.


## C API Notes After Reading The Common Reference

The common reference covers language-agnostic migration gotchas. This section only adds C API specifics for those topics.

### Renderer-side APIs that stay on ovrtx

Keep renderer-side selection and picking calls on ovrtx:

- `ovrtx_enqueue_pick_query` and the `OVRTX_RENDER_VAR_PICK_HIT` render variable in [`ovrtx.h`](../../include/ovrtx/ovrtx.h).
- `ovrtx_set_selection_group_styles` in [`ovrtx.h`](../../include/ovrtx/ovrtx.h).
- `ovrtx_set_selection_outline_group` and `ovrtx_set_pickable` in [`ovrtx_attributes.h`](../../include/ovrtx/ovrtx_attributes.h).

The [`picking-selection`](../../skills/picking-selection/SKILL.md) topic skill stays authoritative for the API shape; only the scene-ingest and step calls around it change.

### Path dictionaries

- For ovstage queries and writes, use `ovstage_get_path_dictionary(stage)`.
- For ovrtx outputs and functions that expose or consume ovrtx path IDs, use `ovrtx_get_path_dictionary(renderer)`.

### Transform and attribute helpers

The ovstage public include tree does not provide an equivalent `ovstage_attributes.h`. Convenience helpers in [`ovrtx_attributes.h`](../../include/ovrtx/ovrtx_attributes.h) - transform writers, `ovrtx_set_path_attributes`, `ovrtx_set_token_attributes`, `ovrtx_set_selection_outline_group`, and `ovrtx_set_pickable` - do not have drop-in ovstage counterparts. For ovstage writes, user code must:

1. Build a path list or query with `ovstage_query` / `ovstage_query_from_path_list`.
2. Intern any tokens with `ovstage_get_path_dictionary`.
3. Fill `ovstage_write_data_t` explicitly and call `ovstage_write_attribute`.

Ovstage transform writes use canonical `omni:xform` as a **2-D 4x4 `double` matrix** with `OVSTAGE_SEMANTIC_MATRIX` (row-vector convention, translation in the last row; `ndim=2`, `shape=[4,4]`, `dtype={kDLFloat,64,1}`, `is_array=false`). See the transform recipe in [`ovstage examples/c/runtime-loop/main.cpp`](https://github.com/NVIDIA-Omniverse/ovstage/blob/main/examples/c/runtime-loop/main.cpp). If the 0.3 app used `ovrtx_set_reset_xform_stack`, author `omni:resetXformStack = true` on the affected prims so the ovstage-side transforms are still interpreted as world-space.

### Async wait APIs

Ovstage exposes **two independent async models**. Using the wrong waiter is a common porting bug.

| Work kind | Enqueue returns | Wait with | Per-op error detail |
|---|---|---|---|
| USD population (`ovstage_population_open_usd_*`, `add_usd_reference_*`, `apply_usd_changes`, `apply_usd_time`, `reset_usd`) | `ovstage_population_enqueue_result_t` | `ovstage_population_wait_op(stage, op_index, ...)` | `ovstage_population_get_last_op_error(op_id)` or `ovstage_population_get_last_error()` |
| Data-plane writes / write floor (`ovstage_advance_write_floor`, `ovstage_write_attribute`, reads, queries) | `ovstage_enqueue_result_t` | `ovstage_wait_op(stage, op_index, ...)` | `ovstage_get_last_op_error(stage, op_id)` or `ovstage_get_last_error()` |

Notes:

- `ovstage_get_last_error()` and `ovstage_population_get_last_error()` take **no instance argument** (parameterless). Do not pass `stage` — older drafts did and will not compile against current headers.
- `ovrtx_query_op_status` / `ovrtx_wait_op` apply only to **ovrtx** ops (e.g. `ovrtx_step_with_stage`). They do **not** report progress for ovstage population loads. The ported `status-queries` example polls status while waiting on render steps; USD open uses `wait_population_op` (blocking wait, no `query_op_status`).

## What 0.4 Adds

From `CHANGELOG.md` `[0.4.0]`:

- **Attach APIs.** `ovrtx_attach_ovstage`, `ovrtx_detach_ovstage`, and `ovrtx_step_with_stage(renderer, render_products, delta_time, ordinal, ...)` in [`ovrtx.h`](../../include/ovrtx/ovrtx.h). While attached, stage-building / write / map entry points return `OVRTX_API_ERROR`; read-only queries and rendering flow through the attached stage.
- **State refresh.** `ovrtx_update_from_stage(renderer, ordinal)` — required after incremental population / attribute changes (see Recipe B). It performs a Hydra rebuild after a wholesale `ovstage_population_open_usd_*`, but that rebuild also happens implicitly on the first `ovrtx_step_with_stage`, so it can be skipped for one-shot loads. Time-only updates (`ovstage_population_apply_usd_time`) are documented no-ops.
- **Write-floor gates.** `ovrtx_step_with_stage` and `ovrtx_update_from_stage` reject calls until `ovstage_advance_write_floor` has run at least once (write floor must be > 0), pointing users at `ovstage_population_open_usd_*` / `ovstage_write_* + ovstage_advance_write_floor`.
- **Picking NDC.** `ovrtx_pick_query_desc_t` now uses `left_ndc` / `top_ndc` / `right_ndc` / `bottom_ndc` instead of pixel fields.
- **Read handle release.** `ovrtx_release_read_result(renderer, read_handle, cuda_sync)` now takes the `ovrtx_read_handle_t` directly; the `ovrtx_read_map_handle_t` typedef and `ovrtx_read_output_t::map_handle` are removed.

The 0.3 deprecated entry points still compile in 0.4 — the compiler emits `OVRTX_DEPRECATED` warnings for each — but they should be replaced with the ovstage-based equivalents below.

For a phased migration,
`ovrtx_config_entry_suppress_deprecation_warnings(true)` temporarily suppresses
native runtime warnings. It does not suppress `OVRTX_DEPRECATED` compiler
diagnostics, change deprecated behavior, or extend the API removal schedule.


## Architecture

```
                    ┌────────────────────────────────────────┐
User app code       │  ovstage_instance_t  (owns scene data) │
────────────────────┤  ovstage_population_open_usd_*         │
                    │  ovstage_write_attribute               │
                    │  ovstage_advance_write_floor(ordinal)  │
                    └──────────────┬─────────────────────────┘
                                   │ ovrtx_attach_ovstage
                                   ▼
                    ┌────────────────────────────────────────┐
                    │  ovrtx_renderer_t  (owns rendering)    │
                    │  ovrtx_update_from_stage(ordinal)      │
                    │  ovrtx_step_with_stage(..., ordinal)   │
                    │  picking / selection / render outputs  │
                    └────────────────────────────────────────┘
```

## Headers, CMake, and Runtime Setup

### Headers

- Include both headers in user code: `#include <ovrtx/ovrtx.h>` and `#include <ovstage/ovstage.h>`. They coexist in the same translation unit via the shared `OVX_SHARED_STRING_TYPES_DEFINED` sentinel guard (see `CHANGELOG.md` `[0.4.0]`).
- `<ovrtx/ovrtx.h>` already pulls in `<ovstage/ovstage_api/ovstage_api_types.h>` internally for the attach types. Do **not** add a second explicit include of `<ovstage/ovstage_api/ovstage_api_types.h>` alongside `<ovrtx/ovrtx.h>` — the direct-include path redefines `ovstage_instance_t` incompatibly.
- `<ovstage/ovstage.h>` transitively includes `<ovstage/ovstage_population.h>` — no separate population include is required for `ovstage_population_open_usd_from_file`.

### CMake and linking

Each library is an **independent package** with its own FetchContent / `find_package` target:

```cmake
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../cmake")
include(ovrtx)
include(ovstage)
ovrtx_fetch()
ovstage_fetch()

target_link_libraries(myapp PRIVATE ovrtx::ovrtx_static ovstage::ovstage_static)
ovrtx_setup_runtime(myapp)
ovstage_setup_runtime(myapp)
```

> **Source:** [`examples/c/minimal/CMakeLists.txt`](../../examples/c/minimal/CMakeLists.txt), [`examples/c/cmake/ovrtx.cmake`](../../examples/c/cmake/ovrtx.cmake), [`examples/c/cmake/ovstage.cmake`](../../examples/c/cmake/ovstage.cmake).

Copy `ovstage.cmake` from the examples tree — do not reduce it to "copy `ovstage.dll` next to the exe." The runtime setup is load-order sensitive.

### Windows: `ovstage.dll` must not load at process init

Attach mode needs **one** shared `omni.fabric` / USD runtime in-process. On Windows, `ovstage.dll` statically imports `ov_25.11usd_ms.dll` and `tbb12.dll`. If the OS loads `ovstage.dll` at process init (before `ovrtx_create_renderer` has loaded the single `plugins/ov_25.11usd_ms.dll` from ovrtx's package), you get a second USD module instance → split `PlugRegistry` / `TfType` state → crashes or subtle corruption.

Linking `ovstage::ovstage_static` avoids this by construction: nothing imports `ovstage.dll`, so the OS cannot load it at init. The static loader calls `LoadLibrary` on the first `ovstage_*` call, which in attach mode is always **after** `ovrtx_create_renderer`. `ovstage_setup_runtime()` in [`ovstage.cmake`](../../examples/c/cmake/ovstage.cmake) only junctions the package `bin/` beside the exe as `ovstage/`, which the app passes to `ovstage_initialize()`; there is no DLL copy and no link-option surgery.

If you link the dynamic `ovstage::ovstage` instead, the import is real and must be deferred, so `ovstage_setup_runtime()` applies **`/DELAYLOAD:ovstage.dll`** (+ `delayimp`) on MSVC and copies only **`ovstage.dll`** and **`ovstage_usd_schemas/`** (data-only schema bundle) into the exe directory — **not** ovstage's flat dependency DLLs, since ovrtx's junctioned `plugins/` tree already provides the single USD closure. Non-MSVC Windows toolchains need an equivalent lazy-load strategy; see the warning in `ovstage_setup_runtime`.

### Linux runtime

`ovstage_setup_runtime` appends `OVSTAGE_BINARY_DIR` to the target rpath. Ovrtx and ovstage must be the **same release train** (matched `usd_ms` ABI). Confirm on hardware that only one `usd_ms` / `omni.fabric` is loaded when both packages are present.



## Deprecated C API Mapping

Every `OVRTX_DEPRECATED` entry point in [`ovrtx.h`](../../include/ovrtx/ovrtx.h) has an ovstage 0.1 replacement. The deprecation message on each declaration is the primary source of truth; the table below groups them by workflow.

| 0.3 ovrtx (deprecated in 0.4) | 0.4 + ovstage 0.1 replacement |
|---|---|
| `ovrtx_open_usd_from_file` | `ovstage_population_open_usd_from_file`; then attach and `ovrtx_step_with_stage`. |
| `ovrtx_open_usd_from_string` | `ovstage_population_open_usd_from_string`; then attach and `ovrtx_step_with_stage`. |
| `ovrtx_add_usd_reference_from_file` | `ovstage_population_add_usd_reference_from_file` + `ovstage_population_apply_usd_changes`. |
| `ovrtx_add_usd_reference_from_string` | `ovstage_population_add_usd_reference_from_string` + `ovstage_population_apply_usd_changes`. |
| `ovrtx_remove_usd` | `ovstage_population_remove_usd_reference` + `ovstage_population_apply_usd_changes`. |
| `ovrtx_reset_stage` | `ovstage_population_reset_usd` + `ovstage_population_apply_usd_changes`. |
| `ovrtx_update_stage_from_usd_time` | `ovstage_population_apply_usd_time`. |
| `ovrtx_clone_usd` | `ovstage_clone` (ordinal-keyed write; pair with `ovstage_advance_write_floor` -> `ovrtx_update_from_stage` -> `ovrtx_step_with_stage`, Recipe B). Target paths must not already exist. |
| `ovrtx_write_attribute` | `ovstage_query` / `ovstage_query_from_path_list` -> `ovstage_write_attribute`. |
| `ovrtx_map_attribute` / `ovrtx_unmap_attribute` | `ovstage_map_attribute` + `ovstage_fetch_map_next`; commit with `ovstage_unmap_attribute` / `ovstage_unmap_group`. |
| `ovrtx_read_attribute` / `ovrtx_fetch_read_result` / `ovrtx_release_read_result` | `ovstage_read_attributes` + `ovstage_fetch_read_next` + `ovstage_release_read` (also `ovstage_release_group` for fetched groups). |
| `ovrtx_query_prims` / `ovrtx_fetch_query_results` / `ovrtx_release_query_results` | `ovstage_query` + `ovstage_fetch_query_result` + `ovstage_release_query_result` + `ovstage_release_query`. |
| `ovrtx_create_attribute_binding` / `ovrtx_destroy_attribute_binding` | No persistent-binding equivalent; reuse an `ovstage_query` handle across writes, release with `ovstage_release_query`. |

`ovrtx_step` is **not** deprecated — it remains the standalone-mode step function. While a stage is attached it returns `OVRTX_API_ERROR`; use `ovrtx_step_with_stage(renderer, render_products, delta_time, ordinal, ...)` there instead. The deprecated `ovrtx_query_prims` / read APIs also still function against the borrowed Fabric while attached in the default mode, but new query call sites should be authored against `ovstage_query`.

Non-deprecated ovrtx entry points — `ovrtx_get_path_dictionary`, `ovrtx_enqueue_pick_query`, `ovrtx_set_selection_group_styles`, `ovrtx_map_render_var_output` / `ovrtx_unmap_render_var_output`, `ovrtx_query_op_status` / `ovrtx_release_op_status`, `ovrtx_wait_op`, `ovrtx_set_log_callback`, and so on — remain on the renderer and do not migrate.

## Consumer Lifecycle Recipes

Before either ovrtx or ovstage initializes a shared OpenUSD runtime, call
`ovrtx_register_schema_paths(config)` with the same ovrtx config that will be
passed to `ovrtx_create_renderer`. USD's process-wide schema registry discovers
plugins only once, so this explicit registration is required when ovstage or
another USD subsystem may initialize or open a stage first. Otherwise
`omni.rtx` can report missing `OmniRtx*` API prim definitions and fall back to
schema defaults. The renderer-first ordering in Recipe A registers the paths
implicitly, but ports should not rely on that side effect when initialization
order can vary.

### Recipe A — Initial load (one-shot)

Use this when the app opens one USD scene at startup and does not mutate the stage between frames.

```
ovrtx_create_renderer(config, &renderer)
ovstage_create_instance(&stage_desc, &stage)
ovrtx_attach_ovstage(renderer, stage)
ovstage_population_open_usd_from_file(stage, file, ordinal, time, OVSTAGE_POPULATION_DOMAIN_RENDERING)
    -> ovstage_population_wait_op(stage, ..., INFINITE)
ovstage_advance_write_floor(stage, {ordinal, OVSTAGE_SCOPE_ALL})
    -> ovstage_wait_op(stage, ..., INFINITE)
ovrtx_step_with_stage(renderer, render_products, delta_time, ordinal, &step_result)
    -> ovrtx_wait_op(renderer, ..., INFINITE)
ovrtx_fetch_results / ovrtx_map_render_var_output / ovrtx_unmap_render_var_output
ovrtx_destroy_results(renderer, step_result)
ovrtx_detach_ovstage(renderer)
ovstage_destroy_instance(stage)
ovrtx_destroy_renderer(renderer)
```

`ovrtx_update_from_stage` is optional in this recipe: the write floor moves once, and the first `ovrtx_step_with_stage` acts as a safety net that binds Hydra to the shared Fabric (`CHANGELOG.md` `[0.4.0]` Changed on attach-time Hydra binding). Calling it explicitly is still safe and triggers a Hydra rebuild against the wholesale population op — it is not a no-op after wholesale open — but for one-shot loads that go straight to a step it can be omitted.

> **Source:** [`examples/c/minimal/main.cpp`](../../examples/c/minimal/main.cpp) snippets `create-renderer`, `load-usd-and-wait`, `step-renderer`, `fetch-results`, `map-rendered-output-cpu`, `unmap-and-cleanup`.

### Recipe B — Incremental scene edits (delta on Recipe A)

For apps that mutate the stage after the first frame — add / remove USD references, reset the stage, write attributes, or advance USD time — insert `ovrtx_update_from_stage(renderer, ordinal)` between `ovstage_advance_write_floor` and `ovrtx_step_with_stage`, following the `CHANGELOG.md` `[0.4.0]` pairing contract: `ovstage_population_*` (or `ovstage_write_*`) -> `ovstage_advance_write_floor` -> `ovrtx_update_from_stage` -> `ovrtx_step_with_stage`.

For time-only updates (`ovstage_population_apply_usd_time`), the `ovrtx_update_from_stage` call is a documented no-op — FSD change-tracking picks up time-sampled deltas at the next step — but calling it is still fine, and it keeps mode-agnostic client code simple.

## Shared Helper Patterns

The ported examples factor small helpers into each `main.cpp` (not a shared library). Copy them into the migrating app or extract a local `ovstage_helpers.h` — they are not part of the public API.

| Helper | Waits via | Used for |
|---|---|---|
| `print_ovstage_error` | — | Logs `ovstage_population_get_last_error()` then `ovstage_get_last_error()` (both parameterless) |
| `wait_population_op` | `ovstage_population_wait_op` | USD open / reference / apply / reset population enqueues |
| `wait_ovstage_op` | `ovstage_wait_op` + `ovstage_release_op` | `ovstage_advance_write_floor` and other data-plane enqueues — `ovstage_release_op` must always be called after `ovstage_wait_op` for every successfully enqueued op |
| `commit_ovstage_ordinal` | `wait_ovstage_op` + `ovstage_advance_write_floor` | Seal an ordinal before `ovrtx_step_with_stage` |
| `cleanup` lambda | detach → destroy stage → destroy renderer | Teardown ordering; detach before destroying the stage |

> **Source:** [`examples/c/minimal/main.cpp`](../../examples/c/minimal/main.cpp) — all helpers above.
> **Source:** [`examples/c/status-queries/main.cpp`](../../examples/c/status-queries/main.cpp) — same ovstage helpers plus `wait_with_status` / `print_operation_status` for **ovrtx** render ops only.

When porting `status-queries`, do not add `ovrtx_query_op_status` polling around population load — population progress is not exposed through ovrtx status APIs. Poll status only on `ovrtx_step_with_stage` (shader-cache warmup step and final render step in the ported example).

## Instructions

1. Find version pins first. Update the app's ovrtx package pin to 0.4.x and confirm `ovstage` 0.1.x is available. Add [`ovstage.cmake`](../../examples/c/cmake/ovstage.cmake) alongside [`ovrtx.cmake`](../../examples/c/cmake/ovrtx.cmake); link `ovstage::ovstage_static` and call `ovstage_setup_runtime` (do not hand-roll the Windows runtime layout).
2. Scan the app for the `OVRTX_DEPRECATED` entry points listed above. Every hit is a migration site.
3. Introduce an `ovstage_instance_t` per renderer, create it with `ovstage_create_instance`, attach with `ovrtx_attach_ovstage` before the first step, and detach in the teardown path.
4. Rewrite scene ingest per intent (see the mapping table): root layer replacement -> `ovstage_population_open_usd_from_*`; additive references -> `ovstage_population_add_usd_reference_from_*` + `ovstage_population_apply_usd_changes`; reset -> `ovstage_population_reset_usd` + `ovstage_population_apply_usd_changes`; time-only -> `ovstage_population_apply_usd_time`.
5. Rewrite attribute writes/reads/queries to the ovstage equivalents. Build a query handle once with `ovstage_query` / `ovstage_query_from_path_list` and reuse it across writes; there is no persistent-binding replacement.
6. In the attached frame loop, replace `ovrtx_step` with `ovrtx_step_with_stage(renderer, render_products, delta_time, ordinal, ...)`. Track the current ovstage ordinal in the app; keep it monotonically increasing across frames that commit new state. Apps that detach and go back to standalone mode still use `ovrtx_step` there — it is not deprecated.
7. Insert `ovstage_advance_write_floor` after every population/write batch, before the next `ovrtx_update_from_stage` or `ovrtx_step_with_stage` at that ordinal. Waiting on the advance op is required — the 0.4 write-floor gates reject step/update calls before the floor moves.
8. Add `ovrtx_update_from_stage(renderer, ordinal)` after incremental edits (Recipe B). Skip it for the one-shot open-USD-and-render path (Recipe A) — it is optional there and safe to omit.
9. Leave picking, selection-outline, render-var output, `ovrtx_query_op_status`, `ovrtx_wait_op`, and logging call sites unchanged. Only route path IDs coming out of ovrtx APIs through `ovrtx_get_path_dictionary()`, and path IDs coming out of ovstage APIs through `ovstage_get_path_dictionary()`.
10. Adjust picking sites: `ovrtx_pick_query_desc_t` now takes `left_ndc` / `top_ndc` / `right_ndc` / `bottom_ndc` (0..1) instead of pixel rectangles.
11. If the app called `ovrtx_release_read_result(renderer, read_handle, map_handle, cuda_sync)`, drop the `map_handle` argument — the field is gone from `ovrtx_read_output_t` and the signature is now `ovrtx_release_read_result(renderer, read_handle, cuda_sync)` (source and binary breaking).
12. If the app depended on implicit RTX exposure defaults, apply `OmniRtxCameraExposureAPI_1` on the relevant camera prims and author the `exposure:*` attributes explicitly.
13. Rebuild. `OVRTX_DEPRECATED` warnings mark every remaining migration site; treat any deprecated call remaining after this pass as intentional and document why.

## Output Format

- Start with the concrete files changed and the 0.3 symbols removed.
- Call out behaviors that could not be migrated mechanically — especially transform-semantic rewrites, camera-exposure defaults, and any incremental-edit paths that now need `ovrtx_update_from_stage`.
- Note any places where the app still calls `OVRTX_DEPRECATED` entry points and why.

## Scripts

This skill has no scripts. Use repository search and targeted edits directly.

## Limitations

- Only covers the C API. Python migration is out of scope.

## Troubleshooting

- `ovrtx_step_with_stage` or `ovrtx_update_from_stage` returns `OVRTX_API_ERROR` immediately with a "no committed writes" message — run `ovstage_advance_write_floor` for the target ordinal (and wait on it via `ovstage_wait_op`) before the call.
- Compile error redefining `ovstage_instance_t`: the app added an explicit `<ovstage/ovstage_api/ovstage_api_types.h>` include next to `<ovrtx/ovrtx.h>`. Include only `<ovstage/ovstage.h>` alongside `<ovrtx/ovrtx.h>`.
- Compile error on `ovx_string_t::str` / `ovx_string_t::len`: ovstage now uses the shared `ptr` / `length` spellings. Rename field accesses.
- Compile error passing `stage` to `ovstage_get_last_error(stage)` or `ovstage_population_get_last_error(stage)`: both are **parameterless** in current 0.1.x headers.
- Windows crash at startup or `PlugFindPluginResource` / duplicate `TfType` registration: two USD runtimes loaded — verify the target links `ovstage::ovstage_static` (or, on the dynamic path, that `/DELAYLOAD:ovstage.dll` is set), that `ovstage_setup_runtime` was called, and that no second `ov_25.11usd_ms.dll` was copied into the exe root from the ovstage package.
- Visual tearing, corruption, or undefined-behavior symptoms on the second frame onward: the app queued the next ordinal's writes and `ovstage_advance_write_floor` without first waiting on the previous `ovrtx_step_with_stage` op id. Add `ovrtx_wait_op` on the returned step op before advancing ordinals.
- Prim paths from pick-hit tensors or ovstage queries decode as garbage strings: an ovrtx-produced ID was passed through `ovstage_get_path_dictionary(stage)` (or vice versa). Route IDs through the dictionary of the API that produced them — `ovrtx_get_path_dictionary(renderer)` for pick-hit / other ovrtx-owned IDs, `ovstage_get_path_dictionary(stage)` for ovstage query / write IDs.
- Silent visual regressions after migration typically map to the shared migration behavior reference — check transform tensor layout, unauthored `exposure:*` attributes, or a picking/selection write routed through `ovstage_write_attribute` instead of the ovrtx helpers.
- Hung or silently failing population load: the app called `ovstage_wait_op` on a population `op_index` (or the reverse). Match the waiter to the enqueue API (see Async wait APIs).

## References

- Shared migration behavior: [`../update-0_3-0_4-common/Reference.md`](../update-0_3-0_4-common/Reference.md).
- Ported reference examples: [`examples/c/minimal/main.cpp`](../../examples/c/minimal/main.cpp), [`examples/c/status-queries/main.cpp`](../../examples/c/status-queries/main.cpp).
- [`../../CHANGELOG.md`](../../CHANGELOG.md) `[0.4.0]` sections.
- [`../../docs/core/ovstage_integration.rst`](../../docs/core/ovstage_integration.rst) for ordinals, and the shared-Fabric update loop.
- [`update-0_2-0_3`](../../skills/update-0_2-0_3/SKILL.md) — predecessor migration skill for user apps.
- [`runtime-loop`](https://github.com/NVIDIA-Omniverse/ovstage/blob/main/skills/runtime-loop/SKILL.md) — headless ovstage populate/read/update loop patterns reused by attached-mode apps.
- [`picking-selection`](../../skills/picking-selection/SKILL.md) — renderer-side picking and selection-outline APIs that stay on ovrtx.
- [`writing-attributes`](../../skills/writing-attributes/SKILL.md) — 0.3 ovrtx attribute-write context; migrated code moves the scene-data pieces to ovstage while keeping selection-outline / pickable writes on ovrtx.
- [`project-setup-c`](https://github.com/NVIDIA-Omniverse/ovstage/blob/main/skills/project-setup-c/SKILL.md) — CMake and include layout for adding ovstage 0.1.x to a C consumer.
- [`update-0_3-0_4-python`](../update-0_3-0_4-python/SKILL.md) for Python application migrations.
