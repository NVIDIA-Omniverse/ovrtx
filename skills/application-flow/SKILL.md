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
name: application-flow
description: >
  High-level overview of a typical ovrtx application lifecycle. Use when user asks how
  to structure an ovrtx program, what the main steps are, or how the pieces fit
  together.
license: LicenseRef-NvidiaProprietary
version: "0.3.0"
author: NVIDIA ovrtx
tags:
  - ovrtx
  - workflow
  - lifecycle
tools:
  - Read
  - Grep
---

# Application Flow

## When to Use

Use this skill when the user asks how to structure an ovrtx program, what the main steps are, or how the pieces fit together.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, or both.
- Application lifecycle stage: renderer creation, scene loading, stepping, warmup, output readback, or cleanup.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Validate ovrtx workflows only on a machine with an NVIDIA RTX-capable GPU, a supported NVIDIA driver listed in `docs/driver_requirements.rst`, and unsandboxed runtime execution.
- If NVIDIA driver detection fails, the driver is inaccessible, or the detected version is older than the relevant baseline in `docs/driver_requirements.rst`, rerun validation outside the sandbox. If the driver is still missing or incompatible, stop runtime validation and tell the user they need a supported NVIDIA driver.
- For the repository minimal examples, require internet access because the scene is loaded from S3.
- Python 3.10-3.13 are supported.
- For code changes, preserve renderer lifecycle ordering and cleanup semantics for the selected language.

## Instructions

1. Identify the requested language and lifecycle stage before choosing an example.
2. Read the referenced snippet that matches the requested stage and language.
3. Preserve the normal ovrtx order: create or initialize the renderer, load or compose USD, step or wait for work, read outputs when needed, then release C resources explicitly.
4. Apply the async, status-query, error-handling, and warmup skills when the workflow crosses those concerns.
5. When changing code, run the narrow example or docs test that owns the snippet whenever practical.

## Output Format

- For explanations, return an ordered lifecycle with the relevant follow-on skills.
- For code changes, summarize the lifecycle files touched and validation run.

## Scripts

This skill has no scripts.

## Limitations

- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

Every ovrtx application follows the same core lifecycle, whether in Python or C. This skill gives the high-level sequence and points to the detailed skill for each step.

## Runtime Verification

Run the minimal example first when validating an ovrtx environment:

| Path | Command | Success signal |
|------|---------|----------------|
| Python minimal | `cd examples/python/minimal && uv run main.py --png` | Writes `_output/render.png`; compare it to `img/example-minimal.jpg`. |
| C minimal (Linux) | `cd examples/c/minimal && cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build && ./build/minimal` | Writes `out.png`; compare it to `img/example-minimal.jpg`. |
| C minimal (Windows) | `cd examples/c/minimal && cmake -B build && cmake --build build --config Release && .\build\Release\minimal.exe` | Writes `out.png`; compare it to `img/example-minimal.jpg`. |

Do not claim runtime validation from parse-only checks, docs-only checks, or execution on a host without a supported RTX GPU and driver.

## Key Concepts

The USD stage contains three prim types that work together to produce rendered output:

- **Camera** (or sensor) prim -- defines the sensor itself: position, orientation, lens properties (focal length, aperture), exposure settings. This is a standard `UsdGeomCamera` prim in the scene hierarchy.
- **RenderProduct** prim -- the thing you actually point the renderer at. It ties together a Camera (via `rel camera`), an output resolution (`int2 resolution`), and a list of output variables (via `rel orderedVars`). When you call `step()`, you pass RenderProduct paths, not Camera paths.
- **RenderVar** prim -- declares a single named output (e.g., `LdrColor`, `HdrColor`, `DepthSD`) that the renderer produces for its parent RenderProduct.

```
/World/Camera          ← Camera prim (sensor definition)
/Render/Camera         ← RenderProduct prim (render configuration)
    /Render/Camera/LdrColor  ← RenderVar prim (output variable)
    /Render/Camera/HdrColor  ← RenderVar prim (output variable)
```

Key implications for agents:

- **`step()` takes RenderProduct paths**, not Camera paths. If you pass a Camera path, nothing will render.
- **Render settings** (e.g., `omni:rtx:rtpt:maxBounces`) are written as attributes on the **RenderProduct** prim, not on the Camera prim. See the `render-settings` skill.
- **Scene properties** (position, materials, visibility) are on scene prims under `/World`. **Render configuration** (resolution, outputs, render mode) is on RenderProduct prims, typically under `/Render`.
- A single Camera can be referenced by multiple RenderProducts with different resolutions, outputs, or settings.

## Lifecycle

```
1. Create renderer         → renderer-creation
2. Load USD scene(s)       → loading-usd
3. [Optional] Clone prims  → cloning-prims
4. Render loop:
   a. Write attributes     → writing-transforms, writing-attributes
   b. Step renderer        → stepping-and-rendering
   c. Read output          → reading-render-output
5. Cleanup
```

## Python

> **Source:** `examples/python/minimal/main.py` snippet `create-renderer`
>
> Followed by: `examples/python/minimal/main.py` snippet `add-usd`
>
> Followed by: `examples/python/minimal/main.py` snippet `step`
>
> Followed by: `examples/python/minimal/main.py` snippet `read-render-output`
>
> For the full lifecycle with attribute writes, bindings, and cloning, compose the relevant skill snippets.

## C

> **Source:** `examples/c/minimal/main.cpp` snippet `create-renderer`
>
> Followed by: `examples/c/minimal/main.cpp` snippet `load-usd-and-wait`
>
> Followed by: `examples/c/minimal/main.cpp` snippet `step-renderer`
>
> Followed by: `examples/c/minimal/main.cpp` snippet `fetch-results`
>
> Followed by: `examples/c/minimal/main.cpp` snippet `map-rendered-output-cpu`
>
> Followed by: `examples/c/minimal/main.cpp` snippet `unmap-and-cleanup`

## Key Differences: Python vs C

| Aspect | Python | C |
|--------|--------|---|
| Renderer lifetime | GC or explicit `del` | `ovrtx_destroy_renderer()` |
| USD loading | `open_usd()` blocks | `ovrtx_open_usd_from_file()` is async; must poll/wait |
| Step | `step()` returns outputs directly | `ovrtx_step()` + `ovrtx_wait_op()` + `ovrtx_fetch_results()` |
| Output access | `var = render_vars["..."].map()` | `ovrtx_map_render_var_output()` + `ovrtx_unmap_render_var_output()` |
| Result cleanup | Automatic (GC) | Must call `ovrtx_destroy_results()` |
| Error handling | Python exceptions (`RuntimeError`) | Check `ovrtx_result_t.status` + `ovrtx_get_last_error()` |

## Troubleshooting

- On Linux systems with no display, repeatedly creating and destroying renderers may result in a crash with the stack trace pointing into `libEGL.so` when shared graphics resources are torn down between renderers. This can happen if `keep_system_alive` is configured to `false`, or if `ovrtx_initialize()` is not called before the multi-renderer lifecycle. In the implicit-initialization pattern (when `ovrtx_initialize()` is not called), the `keep_system_alive` config setting is effectively ignored. Avoid this by both configuring `keep_system_alive` to `true` (`RendererConfig(keep_system_alive=True)` in Python, `ovrtx_config_entry_keep_system_alive(true)` in C) and calling `ovrtx_initialize()` before creating renderers. If this is not possible, or the crash persists, a further workaround is to set the environment variable `VK_LOADER_DISABLE_DYNAMIC_LIBRARY_UNLOADING=1`.
- In C, **every async operation** (`ovrtx_open_usd_from_file`, `ovrtx_clone_usd`, `ovrtx_step`) returns an `ovrtx_enqueue_result_t`. You must wait on the `op_index` before using the results.
- In C, **always destroy results** with `ovrtx_destroy_results()` after processing. ovrtx will log warnings if results are leaked.
- In Python, the synchronous API (`open_usd`, `step`, `clone_usd`) handles waiting internally. Use the `_async` variants for explicit control.
- For best performance in animation loops, use **attribute bindings** (see `attribute-bindings` skill) or **mapping** (see `mapping-attributes` skill) instead of per-frame `write_attribute` calls.
- See `error-handling` skill for robust error checking patterns in both languages.

## In Attached Mode (ovrtx 0.4+)

The renderer-owned scene operations described for standalone mode are deprecated in
0.4. For current code, manage scene data with ovstage, advance its write floor, attach
it to ovrtx, and call Python `step(..., ordinal=...)` (or the C attached update/step
pair). Keep the standalone flow only for compatibility work.

See `docs/core/ovstage_integration.rst`, `skills/update-0_3-0_4-c/SKILL.md` and `skills/update-0_3-0_4-python/SKILL.md`.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
