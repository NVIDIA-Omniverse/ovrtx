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
name: dlss-frame-generation
description: >
  Enable DLSS Frame Generation (DLSS-G) on an ovrtx RenderProduct, consume its
  interpolated frames, pace presentation, and diagnose missing frames. Use when
  a user asks about frame generation or a step returns multiple color frames.
license: LicenseRef-NvidiaProprietary
author: NVIDIA ovrtx
tags:
  - ovrtx
  - rendering
  - dlss
tools:
  - Read
  - Grep
---

# DLSS Frame Generation

DLSS Frame Generation inserts frames between consecutively simulated Real-Time Path Tracing frames. It is configured per RenderProduct.

## When to Use

Use this skill when enabling DLSS Frame Generation, consuming a step that may return multiple color frames, pacing those frames for presentation, or diagnosing why interpolation did not engage.

## Inputs

- Target API surface: Python, C/C++, USDA, or a combination.
- RenderProduct path, requested interpolated-frame count, render mode, outputs, resolution, and GPU/display configuration.
- Whether the application consumes frames offline or presents them interactively.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout containing the referenced examples and documentation tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Use the count-based detection and classification snippets only when exactly one camera capture completes per RenderProduct per step and all returned frames belong to that capture. The examples use unscheduled cameras; several scheduled captures in one step invalidate these recipes.
- Require an Ada-or-newer GPU with an active display only for runtime validation; documentation and static checks do not prove interpolation works. The headless C example omits window and swapchain presentation, but its GPU still needs an active display for frame generation.

## Output Contract

Each completed camera capture contributes its interpolated frames, if any, followed by its simulated frame. When exactly one capture completes per RenderProduct per step, the result contains `N + 1` frames: `N` interpolated frames in presentation order, then the simulated frame. Every frame exposes the same color RenderVar path, so select a frame before looking up its RenderVar.

A scheduled camera can complete several captures in one step. For example, a 120 Hz camera stepped at 60 Hz can return two simulated frames without DLSS-G. Total frame count cannot detect interpolation in that case, and `frames[:-1]` or `output_frame_count - 1` would misclassify earlier simulated captures. Do not use these count-based recipes for multi-capture steps.

Read the returned frame count on every step. The renderer can reduce the requested count to the hardware maximum or return only the simulated frame without failing the step.

Interpolated frames are inferred from neighboring simulated frames. They are not additional camera simulations and may be less accurate than simulated frames. Let the downstream application's requirements determine whether to use them.

## Instructions

1. Read the relevant source snippets below before writing API code.
2. Configure `omni:rtx:dlss:frameGeneration` and `omni:rtx:dlss:frameGenerationInterpolatedFrameCount` on the RenderProduct. Write both attributes when the application must override opinions already present in the scene.
3. Check the known compatibility requirements and blockers below.
4. Confirm that exactly one camera capture completes per RenderProduct per step before using count-based detection or classification. Rely on the renderer’s automatic warm-up; do not add an application convergence loop or discard initial steps.
5. Under that single-capture precondition, derive the interpolated count from the returned frame count and select the simulated frame from the last position.
6. If subsequent single-capture steps contain one frame, treat that as a successful step without interpolation and follow the troubleshooting guidance.
7. If presenting frames, select the frame due at the current time, drop expired interpolated frames, and replace superseded batches as described below.

## Source Snippets

### Configure with USDA

> **Source:** `tests/docs/usd/data/frame_generation_render_product.usda` snippet `doc-frame-generation-render-product`

### Configure with the USD Python API

> **Source:** `tests/docs/usd/test_usd_python_examples.py` snippet `doc-frame-generation-render-product-python`

### Detect frame generation in Python

> **Source:** `tests/docs/python/test_frame_generation.py` snippet `doc-frame-generation-detect`

### Separate interpolated and simulated frames in Python

> **Source:** `tests/docs/python/test_frame_generation.py` snippet `doc-frame-generation-read-frames`

### Configure at runtime in C++

> **Source:** `examples/c/frame-generation/main.cpp` snippet `enable-frame-generation`

### Find a RenderProduct result in C++

> **Source:** `examples/c/frame-generation/main.cpp` snippet `find-render-product-output`

### Separate interpolated and simulated frames in C++

> **Source:** `examples/c/frame-generation/main.cpp` snippet `classify-output-frames`

### Step, warm up, and inspect the count in C++

> **Source:** `examples/c/frame-generation/main.cpp` snippet `step-and-inspect-frames`

### Pace frame presentation in C++

> **Source:** `examples/c/vulkan-interop/src/main.cpp` snippet `doc-frame-pacing-promote`

## Settings

| Setting | Type | Default | Meaning |
|---------|------|---------|---------|
| `omni:rtx:dlss:frameGeneration` | `bool` | `false` | Enables frame generation |
| `omni:rtx:dlss:frameGenerationInterpolatedFrameCount` | `int` | `0` | Requests interpolated frames per simulated frame; `0` requests one interpolated frame; use an explicit larger count to request more |

The requested count is limited by hardware: one interpolated frame on Ada and up to three on Blackwell. There is no public capability query, so inspect the returned count.

## Compatibility Requirements

The known public requirements and common renderer blockers are listed below. Meeting them does not guarantee that the installed driver and operating system support frame generation. Always inspect the returned frame count; an unavailable feature normally leaves the step successful with only its simulated frame.

| Requirement | Result when not met |
|-------------|---------------------|
| The RenderProduct uses an Ada (RTX 40-series) or newer GPU | Only the simulated frame; no warning |
| The RenderProduct uses a GPU with an active display attached | Only the simulated frame; no warning |
| The driver and operating system support DLSS Frame Generation | Only the simulated frame; startup logs may report the requirement |
| Render mode is `RealTimePathTracing` | Only the simulated frame |
| The only requested RenderVar is `LdrColor` or `HdrColor` | Frame generation is disabled for the whole RenderProduct; all requested simulated outputs are still returned |
| The color output does not contain alpha | Only the simulated frame; log reports `output contains alpha` |
| Both resolution dimensions are at least 126 pixels | Only the simulated frame; log reports `unsupported viewport resolution` |
| OmniGraph postprocessing is not active on the RenderProduct | Only the simulated frame; log reports `OmniGraph postprocessing being active` |
| No renderer debug view is active | Only the simulated frame; log reports `not supported with debug views` |
| SDG disable-color rendering is not active | Only the simulated frame; log reports `not supported with SDG disable color render mode` |

SPG outputs are additional RenderVars, so a RenderProduct that requests them does not meet the color-only requirement.

For incompatible outputs, alpha, resolution, or OmniGraph postprocessing, the renderer logs `Disabling DLSS Frame Generation for at least one view due to ...` once for each distinct combination of causes. Debug views and SDG disable-color mode use `Disabling DLSS Frame Generation for ... because it is ...`. Inspect the log from the start of the run. Unsupported and display-less GPUs do not produce these blocker warnings.

## Frame Pacing

For paced presentation, select frames by their presentation times instead of displaying every generated frame:

1. Publish the newest complete step once all of its frames are ready, preserving their returned order. Discard any unshown frames from the previous batch.
2. Estimate the presentation interval from recent completed steps and the current batch's frame count. The Vulkan example averages the last ten publish intervals, divides by the frame count, and shortens the result by one sixth to reach the simulated frame earlier.
3. At each presentation, select the frame due using elapsed time since the batch became ready. Never move backward within the batch. Drop interpolated frames whose presentation times have passed instead of showing them late.
4. Re-present the current image when no newer frame is due.
5. Continue rendering and copying the next step independently of presentation. Use independently synchronized buffers so holding a displayed frame does not block the next copy. The Vulkan example uses ten slots for the published batch, the next batch being copied, and spare slots.

Track render steps, frames made visible, present calls, dropped frames, and visible-frame gaps separately. The `examples/c/vulkan-interop` example implements this policy when pacing is enabled. With `--no-pace`, it advances one frame per present within the batch; a newer complete step still replaces the previous batch.

## Troubleshooting

- **A single-capture step contains one frame.** Consume the simulated frame normally. Do not assume the first step must have this shape: automatic warm-up can allow interpolation on the first returned step.
- **Several frames appear with DLSS-G disabled.** A scheduled camera can complete several simulated captures per step. Total frame count cannot detect interpolation or classify frames in that case.
- **Every single-capture step contains one frame.** Check the known compatibility requirements and blockers, then inspect the log from startup. Remember that unsupported and display-less GPUs log no blocker.
- **Requested three frames but received one interpolated frame.** The request was reduced to Ada's hardware maximum.
- **The wrong image is consumed.** Look for code that scans frames and returns the first matching RenderVar. Select the RenderProduct, then select the intended frame, then look up the RenderVar.
- **The frame rate rises but motion still judders.** Select frames by presentation time and skip expired interpolation slots instead of presenting all frames from a step immediately.
- **Enabling or disabling has no effect.** Inspect the RenderProduct's authored opinions. Write both settings when the application must override the loaded scene.

## Validation

Runtime validation requires an Ada-or-newer GPU with an active display attached, a supported driver, and unsandboxed execution. Do not claim runtime validation from documentation or parse-only checks.

Run the headless frame-generation example against a local ovrtx and ovstage build, then build the documentation and validate inline skill snippets. Use the repository's documented development commands rather than changing package pins to match an in-progress source tree.


The executable relies on the renderer's automatic warm-up and saves every requested step. It defaults to two steps so users can inspect startup and the next capture. A zero exit code validates basic rendering, output mapping, and PNG writing. Frame generation itself is validated only when a single-capture step reports more than one output frame. PNG files are written to the process's current working directory.

## Output Format

- For explanations, state the returned-frame ordering, compatibility requirements, and any presentation-pacing implications.
- For code changes, summarize the source snippets, documentation, and skill references changed, plus validation performed.

## Scripts

This skill has no scripts.

## Limitations

- There is no public capability query for the supported interpolated-frame count; inspect each step's returned frame count.
- Unsupported and display-less GPUs can decline frame generation without logging a blocker.
- Runtime validation requires suitable hardware, driver, display, and an unsandboxed execution environment.

## References

- `docs/sensors/cameras/render_modes/real_time_path_tracing/frame_generation.rst`
- `examples/c/frame-generation/README.md`
- `examples/c/vulkan-interop`
- `skills/render-settings/SKILL.md`
- `skills/reading-render-output/SKILL.md`
- `skills/cuda-interop/SKILL.md`
- `skills/render-product-device-pinning/SKILL.md`
- `skills/warmup/SKILL.md`
