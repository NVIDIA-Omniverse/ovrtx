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
name: warmup
description: >
  Warming up the renderer before capturing output. Use when user asks about warmup
  frames, image quality, texture streaming, path tracing convergence, or why renders
  look noisy/incomplete.
license: LicenseRef-NvidiaProprietary
version: "0.3.0"
author: NVIDIA ovrtx
tags:
  - ovrtx
  - rendering
  - quality
tools:
  - Read
  - Grep
---

# Warmup

## When to Use

Use this skill when the user asks about warmup frames, image quality, texture streaming, path tracing convergence, or why renders look noisy/incomplete.

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

After loading a scene or changing render settings in **Real-Time Path-Tracing** (`rtpt`, the default render mode), the first few rendered frames will not be production quality. There are two independent reasons for this:

1. **Texture streaming** -- ovrtx streams textures on demand. The first frames use low-resolution mip levels while higher-resolution data loads in the background. This typically takes 10-30 frames depending on scene complexity.
2. **Path tracing convergence** -- The real-time path tracer accumulates samples over successive frames. Early frames are noisy; quality improves as more samples are gathered.

Texture streaming is asynchronous by default. Applications can select
`TextureStreamingMode.DISABLE`, `SYNCHRONOUS`, or `ASYNCHRONOUS` through
`RendererConfig.texture_streaming_mode` (or the equivalent C config helper).
Synchronous mode controls texture-feedback processing; it does not guarantee
that every texture loading operation completes synchronously.

To get a good quality image in RT2 mode, step the renderer for a number of warmup frames before capturing output. 40 frames is a good default that handles both texture streaming and basic convergence.

### PathTracing (`pt`) mode does not need warmup

When `omni:rtx:rendermode = "PathTracing"` is set on the RenderProduct, the reference path tracer accumulates `omni:rtx:pt:samplesPerPixel` samples within a **single** step and returns a converged frame. You don't need to run warmup frames for PT-mode output — step once (after textures are in place if you need a particular mip level) and read the result. The `test_path_tracing_mode` test demonstrates this.

## When to warm up (RT2 mode)

- After `open_usd()` / `open_usd_from_string()` or `add_usd_reference*()` -- new textures need to stream in.
- After `reset()` -- accumulated path tracing samples are discarded.
- After changing render settings that invalidate the accumulation buffer (e.g., bounce counts).

## Python

> **Source:** `tests/docs/python/test_base.py` snippet `doc-warmup`

## C

> **Source:** `tests/docs/c/test_base.cpp` snippet `doc-warmup-c`

## Troubleshooting

- Warmup frames still produce `RenderProductSetOutputs`. You can safely ignore the results (Python garbage-collects them; in C you must call `ovrtx_destroy_results()` for each step).
- The number of warmup frames needed depends on scene complexity. 40 is a conservative default; simple scenes may converge faster, while scenes with many high-resolution textures or complex lighting may need more.
- After `reset()`, both texture streaming and path tracing restart. After `reset_stage()` + `open_usd()` or `open_usd_from_string()`, the scene is fully reloaded and warmup is essential.
- Applies to RT2 mode only. PathTracing (`pt`) mode converges within a single step; don't warm up for it.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
