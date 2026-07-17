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
name: stepping-and-rendering
description: >
  Running a simulation step to produce rendered frames. Use when user asks to render a
  frame, step the renderer, simulate a sensor, or get an image from ovrtx.
license: LicenseRef-NvidiaProprietary
version: "0.3.0"
author: NVIDIA ovrtx
tags:
  - ovrtx
  - rendering
  - stepping
tools:
  - Read
  - Grep
---

# Stepping and Rendering

## When to Use

Use this skill when the user asks to render a frame, step the renderer, simulate a sensor, or get an image from ovrtx.

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
3. Preserve the normal ovrtx order: create or initialize the renderer, load or compose USD, step or wait for work, read outputs when needed, then release C resources explicitly.
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

After loading USD content, you render frames by calling `step()`. Each step advances the simulation by `delta_time` and produces output for the specified render products (cameras/sensors). The result contains a hierarchy of products, frames, and render variables that can be mapped to access pixel data.

## Simulation time vs. USD time

ovrtx tracks **two independent clocks** — a frequent point of confusion:

| Clock | Unit | Advanced by | Drives |
|-------|------|-------------|--------|
| **Simulation time** | seconds | `step(products, delta_time)` (accumulates); `reset(time)` | sensor timing — motion blur, lidar/radar scan, `TimeOffsetNs` |
| **USD time** | **timecodes** (converted from seconds via `timeCodesPerSecond`) | `update_from_usd_time(seconds)` (see `loading-usd`) | time-sampled attributes — animated transforms, visibility, ... |

`step()` does **not** advance USD animation, and `update_from_usd_time()` does **not** advance the simulation/sensor clock. To render an animated frame at time *t*: call `update_from_usd_time(t)` first, then `step(...)`. `reset(time)` resets simulation time only (not USD time, and distinct from `reset_stage()`). Remember `update_from_usd_time` takes **seconds**, not timecodes — see `loading-usd` for the `timeCodesPerSecond` conversion.

## Python

### Single frame

> **Source:** `examples/python/minimal/main.py` snippet `step`

### Iterate over results

> **Source:** `examples/python/minimal/main.py` snippet `read-render-output`

### Render loop

> **Source:** `tests/docs/python/test_camera_sensors.py` snippet `doc-step-and-map-camera-outputs`

### Reset simulation time

> **Source:** `tests/docs/python/test_support_api.py` snippet `doc-reset-async`
>
> `renderer.reset(time=0.0)` resets accumulated simulation time (distinct from `reset_stage()`).

## C

### Step, wait, fetch

> **Source:** `examples/c/minimal/main.cpp` snippet `step-renderer`
>
> Followed by: `examples/c/minimal/main.cpp` snippet `fetch-results`

### Iterate over C results

> **Source:** `examples/c/minimal/main.cpp` snippet `find-output-helper`

## Key Types / Functions

| Python | C |
|--------|---|
| `renderer.step(products, dt)` | `ovrtx_step()` + `ovrtx_wait_op()` + `ovrtx_fetch_results()` |
| `renderer.step_async(products, dt)` | `ovrtx_step()` (always async) |
| `renderer.reset(time)` | `ovrtx_reset(renderer, time)` |
| `RenderProductSetOutputs` | `ovrtx_render_product_set_outputs_t` |
| `ProductOutput` | `ovrtx_render_product_output_t` |
| `FrameOutput` | `ovrtx_render_product_frame_output_t` |
| `RenderVarOutput` | `ovrtx_render_product_render_var_output_t` |

Result hierarchy:
```
RenderProductSetOutputs
  -> ProductOutput (one per render product path)
    -> FrameOutput (one per frame produced during the step)
      -> RenderVarOutput (one per output variable: LdrColor, HdrColor, depth, etc.)
```

## Troubleshooting

- The first step from a newly built application will block for 1-2 minutes while shaders are compiled and cached. Wait at least 5 minutes before treating this as a failure; later runs should be faster once the shader cache is populated.
- In C, you must call `ovrtx_destroy_results()` after processing to free resources. ovrtx will warn if results are leaked.
- `delta_time` controls sensor simulation timing. A camera without motion blur produces one frame per step regardless of delta.
- The render product paths must match actual RenderProduct prims in the USD stage.
- In Python, `RenderProductSetOutputs` auto-destroys on garbage collection. Step result metadata is released when `products` falls out of scope; live render-var mappings and their DLPack views are unaffected (they have their own independent lifetime).

## In Attached Mode (ovrtx 0.4+)

When ovrtx is attached to ovstage, step through
``ovrtx_step_with_stage(renderer, products, delta_time, ordinal, ...)``
(Python: ``renderer.step(products, dt, ordinal=n)``). The ``ordinal`` is a
committed-publication gate — the renderer observes ovstage state at or above
that ordinal. Call ``ovrtx_update_from_stage(ordinal)`` first to pull committed
prim/attribute state into ovrtx's Fabric, then step. See
``docs/core/ovstage_integration.rst`` "Ordinals and Write-Floor Gates" for the
ordinal model.

See `docs/core/ovstage_integration.rst`, `skills/update-0_3-0_4-c/SKILL.md` and `skills/update-0_3-0_4-python/SKILL.md`.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
