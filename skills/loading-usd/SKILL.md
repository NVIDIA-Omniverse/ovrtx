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
name: loading-usd
description: >
  Loading USD scenes into ovstage for rendering from files, URLs, or inline USDA strings. Use
  when user asks to load a USD scene, compose USD content, add cameras or
  RenderProducts to an existing USD layer, add referenced content, or create runtime
  geometry.
license: LicenseRef-NvidiaProprietary
version: "0.3.0"
author: NVIDIA ovrtx
tags:
  - ovrtx
  - usd
  - loading
tools:
  - Read
  - Grep
---

# Loading USD

## When to Use

Use this skill when the user asks to load a USD scene, compose USD content, add cameras or RenderProducts to an existing USD layer, add referenced content, or create runtime geometry.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, or both.
- Application lifecycle stage: renderer creation, scene loading, stepping, warmup, output readback, or cleanup.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- For code changes, preserve renderer lifecycle ordering and cleanup semantics for the selected language.

## Instructions

1. Identify the requested language and lifecycle stage before choosing an example.
2. Read the referenced snippet that matches the requested stage and language.
3. For Python, create an ovstage, attach it to the renderer, populate it at an ordinal, advance the write floor, and step at that ordinal. Preserve the standalone C lifecycle when maintaining C code.
4. Apply the async, status-query, error-handling, and warmup skills when the workflow crosses those concerns.
5. When changing code, run the narrow example or docs test that owns the snippet whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

Before rendering, load USD content into an application-owned ovstage. Python supports three input modes through `ovstage.population`:

1. **File path or URL** -- open an existing `.usd`/`.usda`/`.usdc` file as the root layer.
2. **Inline USDA string** -- open runtime-generated USD content as the root layer. The inline root layer may use USD `subLayers` to compose a base scene and additional authored prims.
3. **USD references** -- compose additional file or string content under a specific path prefix.

There are two common composition patterns:

- **Inline root with `subLayers`** -- build one inline root USDA layer that sublayers the original scene and authors the extra prims, then load it with `ovstage.population.open_usd_from_string()` in Python.
- **Additive references** -- use `ovstage.population.add_usd_reference*()`, apply the USD changes at an ordinal, and advance the write floor.

## Python

### Open from file or URL

> **Source:** `examples/python/minimal/main.py` snippet `add-usd`

### Open from inline USDA string

Useful for creating RenderProducts, cameras, or runtime geometry without editing the original scene:

> **Source:** `tests/docs/python/test_sensor_configuration.py` snippet `doc-add-render-config-layer`

### Compose a base scene plus extra prims

When a USD layer has the scene content but lacks render configuration or sensors, compose a new inline root layer: add `subLayers = [@existing_scene.usda@]`, author the missing Camera / RenderProduct / RenderVar prims in that same inline layer, and populate it with `ovstage.population.open_usd_from_string()`.

> **USDA source:** `tests/docs/usd/data/inline_sublayers_camera_renderproduct.usda` snippet `doc-usda-inline-sublayers-camera-renderproduct`
>
> **Source:** `tests/docs/python/test_sensor_configuration.py` snippet `doc-add-render-config-layer`
>
> **Query check:** `tests/docs/python/test_stage_query.py` snippet `doc-query-inline-sublayer-composition`

### Add a USD reference with a path prefix

Use `ovstage.population.add_usd_reference()` or `add_usd_reference_from_string()` after a root stage is open. Call `apply_usd_changes()` at the next ordinal, then advance the write floor.

### Compose multiple inputs

Use inline `subLayers` for one composed root stage, or ovstage reference APIs for incremental additions.

### Remove USD

Use `ovstage.population.remove_usd(stage, handle)`, then apply the change at a new ordinal and advance the write floor.

## C

### Open from file or URL

> **Source:** `examples/c/minimal/main.cpp` snippet `load-usd-and-wait`

### Poll for completion

Loading is asynchronous in C. Poll until done:

> **Source:** `examples/c/minimal/main.cpp` snippet `load-usd-and-wait`

Or block indefinitely:

> **Source:** `examples/c/minimal/main.cpp` snippet `step-renderer`
>
> The step snippet demonstrates blocking with `ovrtx_timeout_infinite`.

### Add a USD reference with a path prefix

> Use `ovrtx_add_usd_reference_from_file` or `ovrtx_add_usd_reference_from_string` with a path prefix.

### Open from inline USDA content

> **Source:** `tests/docs/c/test_sensor_configuration.cpp` snippet `doc-add-render-config-layer-c`
>
> Use `ovrtx_open_usd_from_file` for files/URLs and `ovrtx_open_usd_from_string` for inline root USDA, including inline roots with `subLayers`.

### Compose a base scene plus extra prims

When a USD layer has the scene content but lacks render configuration or sensors, pass one inline root USDA string to `ovrtx_open_usd_from_string()`. That inline root can sublayer the existing scene and author missing Camera / RenderProduct / RenderVar prims.

> **USDA source:** `tests/docs/usd/data/inline_sublayers_camera_renderproduct.usda` snippet `doc-usda-inline-sublayers-camera-renderproduct`
>
> **Source:** `tests/docs/c/test_sensor_configuration.cpp` snippet `doc-add-render-config-layer-c`

### Remove USD

> C: `ovrtx_enqueue_result_t result = ovrtx_remove_usd(renderer, usd_handle);`

### Update time-sampled attributes

For animated USD scenes, re-evaluate time-sampled attributes with `ovstage.population.update_from_usd_time()` (Python) or `ovstage_population_apply_usd_time()` (attached-mode C), apply the changes at a new ordinal, and advance the write floor.

**Timecodes vs. seconds — the common confusion.** USD authors time samples in **timecodes** (frame-like units), but every ovrtx time API takes **seconds**. Convert with the stage's `timeCodesPerSecond` metadata:

- `seconds = timecode / timeCodesPerSecond`
- `timecode = seconds * timeCodesPerSecond`

Example: with `timeCodesPerSecond = 24`, a sample authored at timecode `48` is at **2.0 seconds** — call `update_from_usd_time(2.0)`, not `update_from_usd_time(48)`.

> ⚠️ The parameter is named `usd_time`, but it is in **seconds**, not timecodes — the runtime converts to timecodes internally via `timeCodesPerSecond`.

This is a **different clock** from the *simulation time* advanced by `step(delta_time)` (see the `stepping-and-rendering` skill): `update_from_usd_time` moves USD animation; `step` advances the simulation/sensor clock. The two are independent — advancing one does not advance the other.

> **Source:** `tests/docs/python/test_base.py` snippet `doc-update-from-usd-time-async`
>
> **Source:** `tests/docs/c/test_base.cpp` snippet `doc-update-from-usd-time-async-c`

### Reset stage to empty

Clear all USD content from the runtime stage:

> Python: `renderer.reset_stage()` / `renderer.reset_stage_async()`
>
> C: `ovrtx_reset_stage(renderer)`

## Key Types / Functions

| Python | C |
|--------|---|
| `ovstage.population.open_usd(stage, path, ordinal=...)` | `ovrtx_open_usd_from_file(renderer, file)` |
| `ovstage.population.open_usd_from_string(stage, usda, ordinal=...)` | `ovrtx_open_usd_from_string(renderer, content)` |
| `ovstage.population.add_usd_reference(stage, path, prefix)` | `ovrtx_add_usd_reference_from_file(renderer, file, prefix, &handle)` |
| `ovstage.population.add_usd_reference_from_string(stage, usda, prefix)` | `ovrtx_add_usd_reference_from_string(renderer, content, prefix, &handle)` |
| `ovstage.population.remove_usd(stage, handle)` | `ovrtx_remove_usd(renderer, handle)` |
| `ovstage.population.update_from_usd_time(stage, usd_time)` | `ovstage_population_apply_usd_time(stage, ordinal, usd_time)` (attached mode; deprecated standalone: `ovrtx_update_stage_from_usd_time`) |

## Troubleshooting

- **Only one root layer is allowed.** Calling an ovstage root population function replaces the root layer. To combine a scene file with extra prims such as Cameras and RenderProducts, use one inline root layer with `subLayers`:

  > **Source:** `tests/docs/python/test_sensor_configuration.py` snippet `doc-add-render-config-layer`

- **Reference additions are a separate pattern.** Use `add_usd_reference*` when a root stage is already open and you want to place additional referenced content at a new absolute path. The `prefix_path` must not collide with existing prim paths, and inline reference layers must set `defaultPrim`.
- **Remote USD/S3 asset failures are environment blockers first.** If an example fails while opening a remote USD or S3 asset, verify internet access, proxy/firewall settings, and direct access to the asset URL. Treat the failure as a network or asset-access blocker unless the same URL is reachable outside ovrtx.
- Authored attributes that are not part of the normal population schema are ignored unless the root layer sets `customLayerData.populateAllAuthoredAttributes = true`. Use this only for workflows that need generic authored attributes, because populating every authored attribute can dramatically increase memory usage when assets contain many properties the runtime will never read or write.
- In C, `ovrtx_open_usd_from_file()` is always asynchronous -- you must poll or wait.
- Load errors (e.g., file not found) are reported through `ovrtx_op_wait_result_t::error_op_ids`, not the immediate return value.

## Deprecated Standalone APIs

The renderer population APIs in this skill are deprecated in 0.4 and retained for
standalone compatibility. New code should use `ovstage.population`, publish mutations
by advancing the ovstage write floor, and render the attached stage with an ordinal.

See `docs/core/ovstage_integration.rst`, `skills/update-0_3-0_4-c/SKILL.md` and `skills/update-0_3-0_4-python/SKILL.md`.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
