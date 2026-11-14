---
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
name: stepping-and-rendering
description: >
  Running a simulation step to produce rendered frames. Use when user asks to render a
  frame, step the renderer, simulate a sensor, or get an image from ovrtx.
license: CC-BY-4.0 AND Apache-2.0
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

`step()` does **not** advance USD animation, and `update_from_usd_time()` does **not** advance the simulation/sensor clock. To render an animated frame at time *t*: call `update_from_usd_time(t)` first, then `step(...)`. `reset(time)` resets the simulation clock, not USD time, and is distinct from `reset_stage()`. It also discards all accumulated rendering history: every render product's, plus the renderer's path-tracer radiance cache, Flow simulation and the frame number its sampling sequences are keyed on, so warm up again before capturing (see `warmup`). Remember `update_from_usd_time` takes **seconds**, not timecodes — see `loading-usd` for the `timeCodesPerSecond` conversion.

### Step window vs. frame capture time

`reset(time=T)` re-bases the clock so the next `step(dt)` simulates `[T, T + dt]`; it does not emit a frame at `T`.

Python exposes both:

| Field | Where | Meaning after `reset(T)` + `step(dt)` |
|-------|-------|----------------------------------------|
| `RenderProductSetOutputs.simulation_start_time` | step result | `T` — the step clock base |
| `RenderProductSetOutputs.simulation_end_time` | step result | `T + dt` |
| `FrameOutput.start_time` / `end_time` | per frame | capture or split interval; an accumulated capture can start before `T` |

A default viewport camera captures instantaneously at the *end* of the step window, so its `FrameOutput.start_time` is `T + dt`, not `T`. That is expected, not a clock bug — assert `products.simulation_start_time` when checking the clock base.

## Python

### Single frame

> **Source:** `examples/python/minimal/main.py` snippet `step`
>
> **Source (local-scene example):** `examples/python/projectors/main.py` snippet `projectors-render`

### Iterate over results

> **Source:** `examples/python/minimal/main.py` snippet `read-render-output`

### Render loop

> **Source:** `tests/docs/python/test_camera_sensors.py` snippet `doc-step-and-map-camera-outputs`

### Sensors with different capture rates

> **Source:** `examples/python/multi-rate-sensors/main.py` snippets `doc-multi-rate-step`, `doc-multi-rate-partial-outputs`, and `doc-multi-rate-read-outputs`
>
> **Source (C):** `tests/docs/c/test_sensor_configuration.cpp` snippets `doc-multi-rate-step-c` and `doc-multi-rate-partial-outputs-c`

Keep all active sensor RenderProducts in every step, including steps with no
completed output. Omitting a product discards its accumulated rendering history.
Apply `OmniSensorAPI` to scheduled cameras and author `omni:sensor:frameRate`
as rational Hz. Set a camera's `omni:sensor:Core:partialOutputs` through ovstage:
no camera USD schema declares this attribute, so an extra USD opinion alone is
not populated.
`LdrColor` has no public completion flag and can repeat the last
completed image during an intermediate rolling-shutter split.

The runnable example and `tests/docs/python/test_multi_rate_sensors.py` validate
40/20 Hz lidars and 10/20 Hz cameras on a 40 Hz simulation clock, both output
policies, and accumulated scan history. The example records from the first step
without warmup. See `docs/sensors/common/multi_rate.rst` for the timing and metadata distinctions.

### Reset simulation time

> **Source:** `tests/docs/python/test_support_api.py` snippet `doc-reset-async`
>
> `renderer.reset(time=0.0)` resets accumulated simulation time (distinct from `reset_stage()`).

> **Source:** `tests/docs/python/test_camera_sensors.py` snippet `doc-reset-simulation-clock`
>
> Assert the clock base via `products.simulation_start_time` after the next step
> (distinct from `FrameOutput.start_time`).

### Clear rendering history

`renderer.clear_history(products)` discards the temporal history of those RenderProducts
(for example after a camera cut) on the next frame each one produces, keeping
the simulation time, the sensor schedule and the other products' history. The
cleared frame renders once, unless it is frame 0 or the first frame of a
product that started paused by `omni:sensor:frameLimit`; pass
`first_frame_quality=True` to apply the product's `omni:rtx:waitForEvents` and
`omni:rtx:quality`, or `quality=RenderQuality(...)` to choose them.
A clear also resets lidar and radar model state. `tiles=[...]` clears
selected tiles of one tiled RenderProduct instead of the deprecated
`omni:rtx:viewTile:renderHistoryReset` attributes.

## C

### Step, wait, fetch

> **Source:** `examples/c/minimal/main.cpp` snippet `step-renderer`
>
> **Source (continued):** `examples/c/minimal/main.cpp` snippet `fetch-results`

### Iterate over C results

> **Source:** `examples/c/minimal/main.cpp` snippet `find-output-helper`

A step returns *zero or more* frames per render product, not always one. A sensor
whose exposures end more than once during the step produces one frame per exposure,
and DLSS Frame Generation produces N interpolated frames followed by the real
rendered frame for each completed camera capture. Total frame count alone cannot
distinguish interpolation from multiple simulated captures in one step. Drive loops from `output_frame_count` and pick the frame you
want deliberately — see `dlss-frame-generation` for the frame-generation contract.

## Key Types / Functions

| Python | C |
|--------|---|
| `renderer.step(products, dt)` | `ovrtx_step()` + `ovrtx_wait_op()` + `ovrtx_fetch_results()` |
| `renderer.step_async(products, dt)` | `ovrtx_step()` (always async) |
| `renderer.reset(time)` | `ovrtx_reset(renderer, time)` |
| `renderer.clear_history(products, ...)` | `ovrtx_clear_history(renderer, products, flags, quality, tiles)` |
| `RenderProductSetOutputs` | `ovrtx_render_product_set_outputs_t` |
| `ProductOutput` | `ovrtx_render_product_output_t` |
| `FrameOutput` | `ovrtx_render_product_frame_output_t` |
| `RenderVarOutput` | `ovrtx_render_product_render_var_output_t` |

Result hierarchy:
```
RenderProductSetOutputs
  .simulation_start_time / .simulation_end_time   # step window [t, t+dt]
  -> ProductOutput (one per render product path)
    -> FrameOutput (one per frame produced during the step)
      .start_time / .end_time                     # capture interval; can start before the step
      -> RenderVarOutput (one per full RenderVar prim path: /Render/Camera/LdrColor, /Render/Camera/HdrColor, etc.)
```

## Troubleshooting

- The first step from a newly built application will block for up to 5 minutes while shaders are compiled and cached. Wait at least 5 minutes before treating this as a failure; later runs should be faster once the shader cache is populated.
- In C, you must call `ovrtx_destroy_results()` after processing to free resources. ovrtx will warn if results are leaked.
- `delta_time` controls sensor simulation timing. A camera without an authored positive sensor frame rate is auto-triggered; a scheduled camera follows its own capture rate.
- The render product paths must match actual RenderProduct prims in the USD stage.
- In Python, `RenderProductSetOutputs` auto-destroys on garbage collection. Step result metadata is released when `products` falls out of scope; live render-var mappings and their DLPack views are unaffected (they have their own independent lifetime).

## In Attached Mode (ovrtx 0.4+)

When ovrtx is attached to ovstage, step through
``ovrtx_step_with_stage(renderer, products, delta_time, ordinal, ...)``
(Python: ``renderer.step(products, dt, ordinal=n)``). The ``ordinal`` is a
committed-publication gate — the renderer observes ovstage state at or above
that ordinal. Call ``ovrtx_update_from_stage(ordinal)`` first to pull committed
prim/attribute state into the renderer, then step. See
``docs/core/ovstage_integration.rst`` "Ordinals and Write-Floor Gates" for the
ordinal model.

See `docs/core/ovstage_integration.rst`, `skills/update-0_3-0_4-c/SKILL.md` and `skills/update-0_3-0_4-python/SKILL.md`.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.

### Simulated camera with an interactive observer

> **Source:** `examples/c/sensor-observer/main.cpp` snippets `doc-observer-output-policy-c`, `doc-observer-step-c`, and `doc-observer-copy-outputs-c`
>
> **Source (Python):** `tests/docs/python/test_sensor_observer.py` snippets `doc-observer-output-policy-python`, `doc-observer-simulation-step-python`, and `doc-observer-view-step-python`

Use an ordinary camera without a scheduled frame rate or long exposure for the
observer. Publish its camera transform at a new ordinal, then step both products
with zero delta time. Update scene motion only on positive simulation steps.
Retain the last completed sensor image between captures; do not remove its
RenderProduct from view-only steps. Start with a positive step, since a zero-time
step exactly at an instantaneous sensor's initial startTime can trigger it.
The C example runs simulation and inspection at 30 Hz and renders the observer
continuously at the rate permitted by display presentation and rendering
performance, including without camera input and while simulation is paused.
It provides an interactive Vulkan window and a headless cadence check.
