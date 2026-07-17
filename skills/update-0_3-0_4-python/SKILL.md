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
name: update-0_3-0_4-python
description: >
  Upgrade skill to migrate an existing Python ovrtx codebase from 0.3.x to 0.4.x by
  moving scene population, cloning, queries, attribute reads, writes, mappings,
  and persistent binding workflows to ovstage while keeping rendering in ovrtx.
  Use when the user asks to upgrade from ovrtx 0.3 to 0.4, remove ovrtx 0.4
  deprecation warnings, or adopt ovstage interop in an existing ovrtx project.
license: LicenseRef-NvidiaProprietary
version: "0.4.0"
author: NVIDIA ovrtx
tags:
  - ovrtx
  - upgrade
  - "0.4"
  - ovstage
  - python

tools:
  - Read
  - Grep
  - Edit
---

# Update 0.3 to 0.4 + ovstage 0.1 (Python API)

## Version Scope

| | Version | What changes |
|---|---|---|
| Source | ovrtx 0.3.x | Standalone stage ownership through deprecated `Renderer.open_usd*`, `Renderer.write_attribute*`, `Renderer.query_prims*`, `Renderer.clone_usd*`, `Renderer.bind_attribute*`, and `Renderer.map_attribute` scene APIs, with `Renderer.step()` rendering the renderer-owned stage. |
| Target ovrtx | ovrtx 0.4.x | Attach APIs (`Renderer.attach_ovstage`, `Renderer.detach_ovstage`, `Renderer.update_from_stage`, and `Renderer.step(..., ordinal=...)`); `DeprecationWarning` on renderer-owned scene APIs in [`renderer.py`](../../python/ovrtx/_src/renderer.py). |
| New dependency | ovstage 0.1.x | Scene data plane (`ovstage.Stage`), population bridge (`ovstage.population.open_usd*` and reference/reset/time helpers), ordinal-keyed writes (`Stage.write_attribute`, `Stage.write_attributes`, `Stage.advance_write_floor`). |

## When to Use

Use this skill to migrate an existing ovrtx 0.3.x application to the ovrtx 0.4 scene-ownership model, especially when Python emits `DeprecationWarning` for renderer scene APIs.

For a new application, prefer the current ovstage and ovrtx topic skills directly.

Do **not** use this skill for:

- 0.2 -> 0.3 (see [`update-0_2-0_3`](../../skills/update-0_2-0_3/SKILL.md)).
- C or C++ application ports; switch to `skills/update-0_3-0_4-c/SKILL.md`.

## Inputs

Resolve inputs in this order: the user's Python dependency files, current application code, tests, then the installed ovstage and ovrtx Python packages.

- Current ovrtx and ovstage dependency pins.
- Scene sources: USD file, inline USDA, removable references, or direct data-plane writes.
- Current uses of clone, query, read, write, persistent bindings, and map/unmap.
- Whether the app does **one-shot** scene loading (open a USD file once, then step) or **incremental** scene edits (references, resets, attribute writes, time samples).
- Whether the app uses picking, selection outlines, render-output APIs, or the renderer's path dictionary; these stay on ovrtx and change independently.
- The application's frame ordinal owner and existing simulation/update loop.

## Prerequisites

- Read [`../update-0_3-0_4-common/Reference.md`](../update-0_3-0_4-common/Reference.md) for language-agnostic ownership, ordering, path-dictionary, transform, exposure, and async-boundary guidance.
- Read `CHANGELOG.md` 0.4.0 and `docs/core/ovstage_integration.rst` before editing.
- Consult the public Python documentation shipped with the installed ovstage version for exact API signatures.
- Preserve application structure where practical; this is an ownership/API migration, not a broad refactor.
- Treat the installed Python package signatures as authoritative when documentation differs.

## Architecture

```
User app code       +----------------------------------------+
------------------->|  ovstage.Stage  (owns scene data)     |
                    |  ovstage.population.open_usd*         |
                    |  Stage.write_attribute / clone        |
                    |  Stage.advance_write_floor(ordinal)   |
                    +------------------+---------------------+
                                       | Renderer.attach_ovstage(stage)
                                       v
                    +----------------------------------------+
                    |  ovrtx.Renderer  (owns rendering)     |
                    |  Renderer.step(..., ordinal=ordinal)  |
                    |  picking / selection / render outputs |
                    +----------------------------------------+
```

Python `Renderer.step(..., ordinal=ordinal)` performs the attached-stage update before rendering, so a separate `Renderer.update_from_stage(...)` call is usually unnecessary unless the application explicitly needs to update the renderer before a step.

## Deprecated Python API Mapping

Every `@deprecated(...)` renderer scene method in [`renderer.py`](../../python/ovrtx/_src/renderer.py) should move to ovstage. The deprecation text in the installed Python package is the primary source of truth; this table groups the Python method families by workflow.

| ovrtx 0.3 Python API deprecated in 0.4 | 0.4 + ovstage 0.1 replacement |
|---|---|
| `Renderer.open_usd()` / `open_usd_async()` | `ovstage.population.open_usd(stage, path, ordinal=...)` / `open_usd_async(...)`; then attach and call `Renderer.step(..., ordinal=...)`. |
| `Renderer.open_usd_from_string()` / `open_usd_from_string_async()` | `ovstage.population.open_usd_from_string(stage, usda, ordinal=...)` / `open_usd_from_string_async(...)`; then attach and call `Renderer.step(..., ordinal=...)`. |
| `Renderer.add_usd_reference()` / `add_usd_reference_async()` | `ovstage.population.add_usd_reference(stage, ref_file_path, target_path)` / `add_usd_reference_async(...)`, then `ovstage.population.apply_usd_changes(stage, ordinal=...)`. |
| `Renderer.add_usd_reference_from_string()` / `add_usd_reference_from_string_async()` | `ovstage.population.add_usd_reference_from_string(stage, ref_str, target_path)` / `add_usd_reference_from_string_async(...)`, then `ovstage.population.apply_usd_changes(stage, ordinal=...)`. |
| `Renderer.remove_usd()` / `remove_usd_async()` | `ovstage.population.remove_usd(stage, handle)` / `remove_usd_async(...)`, then `ovstage.population.apply_usd_changes(stage, ordinal=...)`. |
| `Renderer.reset_stage()` / `reset_stage_async()` | `ovstage.population.reset_usd(stage)` / `reset_usd_async(...)`, then `ovstage.population.apply_usd_changes(stage, ordinal=...)`. |
| `Renderer.update_from_usd_time()` / `update_from_usd_time_async()` | `ovstage.population.update_from_usd_time(stage, ordinal, time_code)` / `update_from_usd_time_async(...)`. |
| `Renderer.clone_usd()` / `clone_usd_async()` | `Stage.clone(source_path, target_paths, ordinal)` / `clone_async(...)`; wait for completion, then advance the write floor. |
| `Renderer.query_prims()` / `query_prims_async()` | `Stage.query(...)` or `Stage.query_from_path_list(...)`; fetch and release ovstage query results through the ovstage query handle. |
| `Renderer.read_attribute()` / `read_attribute_async()` | `Stage.read_attributes(query, attrs, ordinal_range)`; fetch read groups from ovstage and release group/read handles. |
| `Renderer.read_array_attribute()` / `read_array_attribute_async()` | `Stage.read_attributes(query, attrs, ordinal_range)`; array/scalar interpretation comes from the fetched ovstage attribute metadata and tensors. |
| `Renderer.write_attribute()` / `write_attribute_async()` | `Stage.write_attribute(query, attribute, ordinal, tensors, is_array=False, ...)`; wait for the op, then advance the write floor. |
| `Renderer.write_array_attribute()` / `write_array_attribute_async()` | `Stage.write_attribute(..., is_array=True, ...)` or `Stage.write_attributes(...)`; wait for the op, then advance the write floor. |
| `Renderer.bind_attribute()` / `bind_attribute_async()` | No persistent-binding object replacement; reuse an ovstage `Query` handle with `Stage.write_attribute`, `Stage.read_attributes`, or `Stage.map_attribute`. |
| `Renderer.bind_array_attribute()` / `bind_array_attribute_async()` | No persistent-binding object replacement; reuse an ovstage `Query` handle and encode array writes through ovstage write/map calls. |
| `Renderer.map_attribute()` | `Stage.map_attribute(query, attribute, ordinal, ...)`; fetch writable map groups, commit groups as needed, then unmap. |
| `Renderer.unmap_attribute()` / `unmap_attribute_async()` | `ovstage.Map.unmap(...)` or `Stage.unmap_attribute(...)`; wait for commit, then advance the write floor. |

`Renderer.step()` and `Renderer.step_async()` are **not** deprecated. In attached mode, pass the committed ovstage ordinal. Picking, selection outlines, render-output mapping, renderer operation status, renderer waits, logging, and renderer-owned path IDs remain on `ovrtx.Renderer`.

## Instructions

1. Update dependencies first. Install the ovstage 0.1 Python wheel alongside ovrtx 0.4.
2. Create one externally owned `ovstage.Stage` for scene data. Keep the instance alive until it has been detached from every renderer.
3. Move USD population from `Renderer.open_usd*` to `ovstage.population.open_usd*`.
4. Move reference add, remove, and reset operations to `ovstage.population`. Follow source edits with `apply_usd_changes` at the application-owned ordinal. Move time-sampled updates to ovstage population's USD-time operation.
5. Publish each completed mutation by advancing the ovstage write floor to the operation's ordinal. Do not render an ordinal above the current write floor.
6. Attach the stage with `Renderer.attach_ovstage`. Render with `Renderer.step(..., ordinal=ordinal)`; it performs the ovrtx stage update automatically.
7. Move cloning from `Renderer.clone_usd*` to `Stage.clone*`, assign an ordinal above the current floor, wait for completion, then advance the floor.
8. Move stage discovery from `Renderer.query_prims*` to ovstage queries. Use the ovstage-owned path dictionary for reusable path lists and token identities.
9. Move attribute reads to `Stage.read_attributes`. Iterate fetched groups, consume or copy borrowed tensor data, release each group, then release the read handle.
10. Move attribute writes to `Stage.write_attribute`. Supply the application ordinal, explicit array/scalar kind, prim mode, semantic, and synchronization required by the current ovstage API.
11. Replace persistent ovrtx attribute bindings with reusable ovstage query handles. Release the query when the repeated read/write/map workflow ends.
12. Move zero-copy mappings to `Stage.map_attribute`. Fetch writable groups, unmap each committed group as required, then unmap the overall map handle. Advance the write floor after the map commit completes.
13. Detach ovstage before destroying either object. Release read groups, reads, maps, queries, and caller-owned path lists according to ovstage ownership rules.
14. Run the narrowest application tests that cover scene population, one mutation, one render step, and teardown. Keep deprecated standalone calls only where compatibility behavior is intentionally being tested.

## Output Format

- Start with the Python dependency files and deprecated renderer scene calls replaced.
- State which component owns the stage, the frame ordinal, and the write-floor advance.
- Call out behaviors that could not be migrated mechanically, especially transform-semantic rewrites, camera-exposure defaults, and incremental-edit paths that now need an explicit renderer update from the attached stage.
- Report validation commands and any remaining intentional deprecated calls.

## Scripts

This skill has no scripts. Use repository search and targeted edits directly.

## Limitations

- This skill covers the ovstage ownership transition and the ovrtx APIs deprecated for that transition. Consult `CHANGELOG.md` for unrelated 0.4 changes.
- ovstage 0.1 retains only the latest committed snapshot. Treat ordinals passed to rendering as committed-publication gates, not requests for retained historical snapshots.
- Persistent ovrtx bindings have no one-to-one ovstage object replacement; reuse a query handle and migrate the surrounding data flow.
- Exact query filters, tensor metadata, and map-group iteration depend on the user's schema and must be derived from current ovstage documentation and code.

## Troubleshooting

- If attached rendering reports that the ordinal is not committed, wait for the ovstage mutation and advance the write floor before stepping.
- If a populated scene does not render, ensure the rendering population domain was requested, the stage was attached, and Python `step` received the committed ordinal.
- If a query, read, or write uses invalid path/token ids, obtain the path dictionary from the ovstage instance rather than the renderer.
- If mapped or read data becomes invalid, check group and handle release order; ovstage result buffers are borrowed unless explicitly copied.
- If writes fail with a write-floor violation, allocate an ordinal above the current floor and advance the floor only after the writes complete.

## References

- Shared migration behavior: [`../update-0_3-0_4-common/Reference.md`](../update-0_3-0_4-common/Reference.md).
- `skills/update-0_3-0_4-c/SKILL.md` for C/C++ application ports, CMake/runtime setup, and C API lifecycle recipes.
- `CHANGELOG.md` 0.4.0 for release-level changes.
- `docs/core/ovstage_integration.rst` for renderer update ordering.
- [`project-setup-python`](../project-setup-python/SKILL.md) for Python environment and package setup.
- `skills/application-flow/SKILL.md` for the ovrtx rendering lifecycle.
- The public documentation shipped with ovstage 0.1 for population, cloning, query, read/write, mapping, and synchronization details.
