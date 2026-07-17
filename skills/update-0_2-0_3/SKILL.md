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
name: update-0_2-0_3
description: >
  Upgrade skill to migrate an existing ovrtx codebase from 0.2.0 to 0.3.0. Use
  when the user asks to "upgrade from 0.2 to 0.3", migrate ovrtx API usage,
  update 0.2 projects to 0.3, or fix code after moving from ovrtx 0.2.x to 0.3.x.
license: LicenseRef-NvidiaProprietary
version: "0.3.0"
author: NVIDIA ovrtx
tags:
  - ovrtx
  - upgrade
  - migration
tools:
  - Read
  - Grep
  - Edit
---

# Update 0.2 to 0.3

## When to Use

Use this skill when the user asks to upgrade an existing ovrtx project from 0.2.0 or 0.2.x to 0.3.0 or 0.3.x, especially with the prompt "upgrade from 0.2 to 0.3".

Do not use this for brand-new examples unless the user explicitly wants migration guidance. For new code, prefer the topic skills that describe current 0.3 usage directly.

## Inputs

Resolve inputs in this order: the user's repository, its dependency files, then source code and docs.

- Target language: Python, C/C++, or both.
- Dependency manager and package pin location.
- Whether USD loading is root-stage loading or additive removable content.
- Whether async render calls, render output mapping, logging callbacks, or partial-frame behavior are present.
- Existing tests/examples the user expects to keep working.

## Prerequisites

- Inspect `CHANGELOG.md` 0.3.0 before editing; it is the release-level source of truth.
- Read current 0.3 snippets before rewriting API usage. Do not infer exact call shapes from memory.
- Preserve user code structure where practical. This is an API migration, not a broad refactor.
- If a project mixes ovrtx with another OpenUSD subsystem, account for schema-path registration before USD initializes.

## Instructions

1. Find version pins first. Search package and lock files for `ovrtx==0.2`, `ovrtx~=0.2`, or equivalent C package references. Update to the user's requested 0.3 build; in this repo's examples the packaged Python pin is `ovrtx==0.3.0`.
2. Scan for 0.2-only Python symbols: `RendererResult`, `add_usd`, `add_usd_layer`, `add_usd_async`, `add_usd_layer_async`, `output_partial_frames`, `step_async`, and `MappedRenderVar.tensor`.
3. Scan for 0.2-only C symbols: `ovrtx_add_usd`, `ovrtx_usd_input_t`, `ovrtx_rendered_output_t`, `ovrtx_map_rendered_output`, `ovrtx_unmap_rendered_output`, `ovrtx_rendered_output_handle_t`, `ovrtx_rendered_output_map_handle_t`, `OVRTX_CONFIG_OUTPUT_PARTIAL_FRAMES`, `ovrtx_release_errors`, `ovrtx_flush_op_log`, and old renderer-scoped `ovrtx_set_log_callback` calls.
4. Rewrite USD loading by intent:
   - Single scene/root layer: use `open_usd*`.
   - Runtime inline root layer, often with `subLayers`: use `open_usd_from_string*`.
   - Additive removable content under a new prim path: use `add_usd_reference*` and keep the returned handle for `remove_usd`.
5. Rewrite Python async rendering. `Renderer.step()` still returns fetched outputs. `Renderer.step_async()` now returns `Operation[PendingFetch[RenderProductSetOutputs]]`; call `wait()` for the pending fetch and then `fetch()` for outputs.
6. Rewrite render output mapping. In Python, use DLPack directly on a single-tensor mapping or named tensor/param access for composite outputs. In C, map to `ovrtx_render_var_output_t`, read `tensors[]` and `params[]`, then unmap with `ovrtx_unmap_render_var_output`.
7. Remove global partial-frame config. If 0.2 code explicitly disabled partial frames, author `bool omni:sensor:Core:accumulateOutputs = true` on the affected camera prim instead. If 0.2 code omitted the setting or used the default partial-frame behavior, remove the config without replacement.
8. Rewrite C wait/error handling. Read `ovrtx_op_wait_result_t.error_op_ids`, fetch strings with `ovrtx_get_last_op_error()`, copy or print them before the next wait on the same thread, and remove `ovrtx_release_errors`.
9. Rewrite C logging. The callback is process-global, no longer receives an op id, uses carb-style severity values, and flushing is `ovrtx_flush_log(timeout)`.
10. Validate with the narrowest runnable project tests or examples. For Python projects, run the user's normal test command or at least import and exercise the migrated code path. For C/C++ projects, rebuild so removed symbols are caught at compile time.

## Output Format

- Start with the concrete files changed and the 0.2 symbols removed.
- Call out any behavior choices that could not be migrated mechanically, especially partial-frame semantics and root-vs-reference USD loading.
- Include the validation commands run and any remaining manual checks.

## Scripts

This skill has no scripts. Use repository search and targeted edits directly.

## Limitations

- This skill covers public API migration from 0.2.0 to 0.3.0. It does not attempt to adopt new optional 0.3 features such as lidar, radar, picking, selection outlines, stage queries, or attribute reads unless the existing code needs them.
- Some USD loading calls require intent. A 0.2 `add_usd(..., path_prefix=None)` usually becomes root-stage `open_usd()`, while prefixed additive content usually becomes `add_usd_reference()`.
- `MappedRenderVar.tensor` still works for single-tensor Python render variables in 0.3 but emits `DeprecationWarning`; migrate it instead of suppressing the warning.
- Partial-frame migration may require editing USD content rather than application config.

## Migration Details

### Python dependency and renderer config

Update the ovrtx dependency pin, remove `RendererResult` imports, and remove `RendererConfig.output_partial_frames`.

> **Source:** `tests/docs/python/test_support_api.py` snippet `doc-renderer-config`

### Python USD loading

Use `open_usd()` for the active root layer and `add_usd_reference*()` for additive removable content.

> **Source:** `examples/python/minimal/main.py` snippet `add-usd`
> **Source:** `tests/docs/python/test_stage_mutation.py` snippet `doc-add-usd-reference-from-string`
> **Source:** `tests/docs/python/test_sensor_configuration.py` snippet `doc-add-render-config-layer`

### Python step and render output readback

Keep synchronous `step()` call sites simple. For async call sites, fetch outputs explicitly after the render operation completes.

> **Source:** `examples/python/minimal/main.py` snippet `step`
> **Source:** `tests/docs/python/test_camera_sensors.py` snippet `doc-step-async`
> **Source:** `examples/python/minimal/main.py` snippet `read-render-output`
> **Source:** `tests/docs/python/test_camera_sensors.py` snippet `doc-step-and-map-camera-outputs`

### C/C++ USD loading

Replace `ovrtx_add_usd()` and `ovrtx_usd_input_t` with root-stage or reference APIs.

> **Source:** `examples/c/minimal/main.cpp` snippet `load-usd-and-wait`
> **Source:** `tests/docs/c/test_stage_mutation.cpp` snippet `doc-add-usd-reference-from-string-c`

### C/C++ render output mapping

Replace rendered-output types and mapping functions with render-var-output names and named tensor access.

> **Source:** `examples/c/minimal/main.cpp` snippet `map-rendered-output-cpu`
> **Source:** `examples/c/minimal/main.cpp` snippet `unmap-and-cleanup`
> **Source:** `tests/docs/c/test_camera_sensors.cpp` snippet `doc-map-render-output-cuda-c`
> **Source:** `tests/docs/c/test_camera_sensors.cpp` snippet `doc-map-render-output-cuda-array-c`

### C/C++ wait errors and logging

Use transient per-thread wait error data and process-global logging callbacks.

> **Source:** `tests/docs/c/test_error_handling.cpp` snippet `doc-wait-op-error-retrieval-c`
> **Source:** `tests/docs/c/test_error_handling.cpp` snippet `doc-wait-op-no-release-errors-c`
> **Source:** `tests/docs/c/test_logging.cpp` snippet `doc-log-callback-prefix-filter-c`

## Troubleshooting

- If a migrated project loads a USD scene and then loses previously loaded content, the rewrite probably used `open_usd*` where the old call was additive. Convert the later load to `add_usd_reference*` and give it a unique absolute prim path.
- If async Python code gets a `PendingFetch` where it expected outputs, add the explicit `.fetch()` step after `op.wait()`.
- If C image code still reads `.buffer.dl`, migrate to `rendered_output.tensors[0].dl` for single-tensor camera outputs and validate shape `[height, width, channels]` with scalar lanes.
- If C error reporting prints empty or invalid strings, consume `ovrtx_get_last_op_error()` results before any later `ovrtx_wait_op()` on the same thread.
- If mixed OpenUSD/ovPhysX applications report missing ovrtx schemas, call `ovrtx_register_schema_paths()` before any subsystem initializes or opens a USD stage.

## References

- `skills/update-0_3-0_4-c/SKILL.md` and `skills/update-0_3-0_4-python/SKILL.md` for the subsequent migration from renderer-owned scene APIs to ovstage.
- `CHANGELOG.md` 0.3.0 `Added`, `Changed`, and `Removed` sections for release-level migration notes.
- `skills/loading-usd/SKILL.md` for current root-stage and reference composition patterns.
- `skills/stepping-and-rendering/SKILL.md` for current step lifecycle.
- `skills/reading-render-output/SKILL.md` for current render-var tensor mapping and lifetime rules.
- `skills/error-handling/SKILL.md` for current C error-reporting patterns.
- `docs/c_api/getting_started.rst` for early `ovrtx_register_schema_paths()` usage in mixed USD processes.
