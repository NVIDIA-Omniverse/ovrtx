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
name: render-settings
description: >
  Writing render settings to control rendering behavior. Use when user asks to change
  render settings, set max bounces, configure path tracing, change render quality, or
  modify RTX settings on a RenderProduct.
license: LicenseRef-NvidiaProprietary
version: "0.3.0"
author: NVIDIA ovrtx
tags:
  - ovrtx
  - rendering
  - settings
tools:
  - Read
  - Grep
---

# Render Settings

## When to Use

Use this skill when the user asks to change render settings, set max bounces, configure path tracing, change render quality, or modify RTX settings on a RenderProduct.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, USD, or a combination.
- RenderProduct prim path and the exact `omni:rtx:*` setting attribute to author or update.
- Desired setting value, USD type, runtime/write timing, and whether reset/warmup behavior matters.
- Existing scene or snippet that already owns related RenderProduct settings.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Confirm the setting belongs on the RenderProduct prim, not on a Camera, RenderVar, or renderer creation option.
- Use `writing-attributes` when the setting is changed through runtime APIs.

## Instructions

1. Identify the RenderProduct path and the exact RTX setting attribute to change.
2. Write settings on the RenderProduct prim, not on the Camera or RenderVar prim.
3. Match the value type to the USD attribute schema and preserve existing authored settings that are unrelated to the request.
4. Apply the writing-attributes skill when setting values through runtime APIs rather than static USD.
5. When changing code, run the render-settings docs test that owns the setting snippet whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

Render settings in ovrtx are written as attributes on the **RenderProduct** prim. To change a setting, use `write_attribute()` in Python or `ovrtx_write_attribute()` in C, targeting the RenderProduct prim path (e.g., `/Render/Camera`) with the setting's attribute name.

Settings use the `omni:rtx:` namespace prefix. For example, to set the maximum number of path tracing bounces, write `omni:rtx:rtpt:maxBounces` as a `uint32` attribute.

After changing a render setting, call `reset()` and run warm-up frames to allow the renderer to converge with the new setting.

## Python

### Set a render setting on a RenderProduct

> **Source:** `tests/docs/python/test_base.py` snippet `doc-set-render-setting`

## C

### Set a render setting on a RenderProduct

> **Source:** `tests/docs/c/test_base.cpp` snippet `doc-set-render-setting-c`

## Key Types / Functions

| Python | C |
|--------|---|
| `renderer.write_attribute(prim_paths=["/Render/Camera"], attribute_name="omni:rtx:rtpt:maxBounces", tensor=np.array([value], dtype=np.uint32))` | `ovrtx_write_attribute(renderer, &binding, &buffer, OVRTX_DATA_ACCESS_SYNC)` with `uint32` DLTensor |

## Render Mode Selection

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `omni:rtx:rendermode` | `token` | `"RealTimePathTracing"` | Render mode: `"RealTimePathTracing"`, `"PathTracing"`, or `"Minimal"` |

## Real-Time Path-Tracing Settings (`rtpt:`)

### Sampling and Caching

| Setting | Type | Default |
|---------|------|---------|
| `omni:rtx:rtpt:cached:enabled` | `bool` | `true` |
| `omni:rtx:rtpt:lightcache:cached:enabled` | `bool` | `true` |
| `omni:rtx:rtpt:ris:meshLights` | `bool` | `false` |

### Ray Bounces and Shading

| Setting | Type | Default |
|---------|------|---------|
| `omni:rtx:rtpt:maxBounces` | `uint` | `3` |
| `omni:rtx:rtpt:maxSpecularAndTransmissionBounces` | `uint` | `3` |
| `omni:rtx:rtpt:maxVolumeBounces` | `uint` | `3` |
| `omni:rtx:pt:fractionalCutoutOpacity` | `bool` | `true` |
| `omni:rtx:rtpt:maxRoughness` | `float` | `0.3` |
| `omni:rtx:rt:reflections:roughnessCacheThreshold` | `float` | `0.3` |
| `omni:rtx:rtpt:translucency:virtualMotion:enabled` | `bool` | `true` |

### Firefly Filter

| Setting | Type | Default |
|---------|------|---------|
| `omni:rtx:rtpt:fireflyFilter:enabled` | `bool` | `true` |
| `omni:rtx:rtpt:fireflyFilter:maxUnexposedIntensityPerSample` | `float` | `3200.0` |
| `omni:rtx:rtpt:fireflyFilter:maxUnexposedIntensityPerSampleDiffuse` | `float` | `3200.0` |
| `omni:rtx:rtpt:fireflyFilter:maxPerEmissiveUnexposedIntensity` | `float` | `3200.0` |

### Gaussian Splatting

| Setting | Type | Default |
|---------|------|---------|
| `omni:rtx:rtpt:gaussian:accumulatedDepth:enabled` | `bool` | `true` |
| `omni:rtx:rtpt:gaussian:accumulatedAlbedo:enabled` | `bool` | `true` |
| `omni:rtx:rtpt:gaussian:maxGaussiansToAccumulate` | `int` | `48` |

## Path Tracing Settings (`pt:`)

### Path Tracing

| Setting | Type | Default |
|---------|------|---------|
| `omni:rtx:pt:samplesPerPixel` | `uint` | `512` |
| `omni:rtx:pt:samplesPerIteration` | `int` | `1` |
| `omni:rtx:pt:adaptiveSampling:enabled` | `bool` | `true` |
| `omni:rtx:pt:limits:maxBounces` | `uint` | `4` |
| `omni:rtx:pt:limits:maxGlossyBounces` | `uint` | `6` |
| `omni:rtx:pt:maxVolumeBounces` | `uint` | `15` |
| `omni:rtx:pt:limits:maxFogBounces` | `uint` | `2` |
| `omni:rtx:pt:fractionalCutoutOpacity` | `bool` | `true` |

### Denoising

| Setting | Type | Default |
|---------|------|---------|
| `omni:rtx:pt:denoising:enabled` | `bool` | `true` |
| `omni:rtx:pt:denoising:optix:temporal` | `bool` | `false` |
| `omni:rtx:pt:denoising:blendFactor` | `float` | `0.0` |
| `omni:rtx:pt:denoising:optix:denoiseAOVs` | `bool` | `true` |

### Sampling and Caching

| Setting | Type | Default |
|---------|------|---------|
| `omni:rtx:pt:radianceCache:enabled` | `bool` | `true` |
| `omni:rtx:pt:lightCache:enabled` | `bool` | `true` |
| `omni:rtx:pt:ris:meshLights` | `bool` | `false` |
| `omni:rtx:pathtracing:rayguide:cached:enabled` | `bool` | `false` |

### Firefly Filter

| Setting | Type | Default |
|---------|------|---------|
| `omni:rtx:pt:fireflyFilter:enabled` | `bool` | `true` |
| `omni:rtx:pt:fireflyFilter:maxUnexposedIntensityPerSample` | `float` | `3200.0` |
| `omni:rtx:pt:fireflyFilter:maxUnexposedIntensityPerSampleDiffuse` | `float` | `3200.0` |
| `omni:rtx:pt:fireflyFilter:maxPerEmissiveUnexposedIntensity` | `float` | `3200.0` |

### Spectral Rendering

| Setting | Type | Default |
|---------|------|---------|
| `omni:rtx:pathtracing:spectral:enabled` | `bool` | `false` |
| `omni:rtx:pathtracing:spectral:wavelengthMin` | `float` | `10.0` |
| `omni:rtx:pathtracing:spectral:wavelengthMax` | `float` | `10000.0` |
| `omni:rtx:renderingColorSpace` | `string` | `"lin_rec709_scene"` |
| `omni:rtx:pathtracing:spectral:responseCurve` | `uint` | `0` |

### Non-Uniform Volumes

| Setting | Type | Default |
|---------|------|---------|
| `omni:rtx:pt:ptvol:enabled` | `bool` | `false` |
| `omni:rtx:pt:volumes:transmittanceMethod` | `token` | `"biasedRayMarching"` |
| `omni:rtx:pt:volumes:tracking:maxScatteringSteps` | `int` | `1024` |
| `omni:rtx:pt:volumes:tracking:maxShadowSteps` | `int` | `32` |
| `omni:rtx:pt:limits:maxVolumeBounces` | `uint` | `2` |

### Multi-GPU

| Setting | Type | Default |
|---------|------|---------|
| `omni:rtx:pt:multigpu:enabled` | `bool` | `true` |
| `omni:rtx:pt:mgpu:autoLoadBalancing:enabled` | `bool` | `true` |
| `omni:rtx:pt:mgpu:compressRadiance` | `bool` | `false` |
| `omni:rtx:pt:mgpu:compressAlbedo` | `bool` | `true` |
| `omni:rtx:pt:mgpu:compressNormals` | `bool` | `true` |
| `omni:rtx:multiThreading:enabled` | `bool` | `true` |

### Global Volumetric Effects

| Setting | Type | Default |
|---------|------|---------|
| `omni:rtx:pt:ptvol:raySky` | `bool` | `false` |
| `omni:rtx:pt:ptvol:raySkyScale` | `float` | `1.0` |
| `omni:rtx:pt:ptvol:raySkyDomelight` | `bool` | `false` |

### Anti-Aliasing

| Setting | Type | Default |
|---------|------|---------|
| `omni:rtx:pt:pixelFilter:filter` | `token` | `"triangle"` |
| `omni:rtx:pt:pixelFilter:radius` | `float` | `1.0` |

## Minimal Settings

Minimal mode is optimized for speed-of-light rendering performance and stability. It only respects the first `DistantLight` found in the scene, and shadows from that light are hard shadows. Other light types, including `DomeLight`, are ignored for Minimal mode lighting; if no `DistantLight` exists, Minimal mode uses a single camera light instead. For improved visibility, use the ambient light attributes documented in `docs/sensors/cameras/render_modes/minimal.rst`, or disable shadows with `omni:rtx:minimal:castShadows`.

| Setting | Type | Description |
|---------|------|-------------|
| `omni:rtx:minimal:mode` | `int` | Minimal render mode variant |
| `omni:rtx:minimal:constantColor` | `color3f` | Constant color output |
| `omni:rtx:minimal:castShadows` | `bool` | Enable hard shadows from the first `DistantLight` |
| `omni:rtx:rt:ambientLight:color` | `color3f` | Ambient light color |
| `omni:rtx:rt:ambientLight:intensity` | `float` | Ambient light intensity |

## Troubleshooting

- Render settings are attributes on the **RenderProduct** prim, not on a separate RenderSettings prim. Write them to the same prim path you pass to `step()` (e.g., `/Render/Camera`).
- The dtype must match the schema type exactly. Most integer settings above are `uint`, so write `np.uint32` -- `omni:rtx:rtpt:maxBounces` is `uint32`, not `int32` or `int64`. Settings typed `token` (such as `omni:rtx:rendermode` and `omni:rtx:pt:pixelFilter:filter`) are written as interned token IDs, not integers; see `writing-attributes` for the full USD-type-to-dtype table.
- After changing a setting, call `reset()` and run warm-up frames before capturing output. The renderer needs time to reconverge.
- Settings use the `omni:rtx:` namespace prefix, with subsystem prefixes like `rtpt:` (real-time path tracing), `post:` (post-processing), etc.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
