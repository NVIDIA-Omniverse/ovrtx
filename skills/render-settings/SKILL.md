---
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
name: render-settings
description: >
  Writing render settings to control rendering behavior. Use when user asks to change
  render settings, set max bounces, configure path tracing, change render quality,
  enable DLSS frame generation, or modify RTX settings on a RenderProduct.
license: CC-BY-4.0 AND Apache-2.0
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

Use this skill when the user asks to change render settings, set max bounces, configure path tracing, change render quality, enable DLSS frame generation, or modify RTX settings on a RenderProduct.

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
| `omni:rtx:rendermode` | `token` | `"RealTimePathTracing"` | Render mode: `"RealTimePathTracing"`, `"PathTracing"`, or `"MinimalRendering"` |

## DLSS Frame Generation (`dlss:`)

DLSS Frame Generation inserts interpolated frames between rendered ones. It is off by default and is enabled per RenderProduct, like any other render setting.

> **Source:** `examples/c/vulkan-interop/src/main.cpp` snippet `enable-dlssg`

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `omni:rtx:dlss:frameGeneration` | `bool` | `false` | Enable frame generation |
| `omni:rtx:dlss:frameGenerationInterpolatedFrameCount` | `int` | `0` | Interpolated frames per rendered frame, clamped to the hardware maximum (1 on Ada, 3 on Blackwell). `0` or unset means 1, so request `3` to get the hardware maximum |

Enabling frame generation changes the shape of the step results: one step returns `output_frame_count == N + 1` output frames instead of 1, ordered with the interpolated frames first and the real rendered frame last. Each frame exposes the same single color render var, and only the last frame carries a meaningful accumulation status. Consumers that assume `output_frames[0]` is the frame to display or inspect need to be updated before turning this on.

The renderer declines frame generation without failing the step, in which case a step keeps returning a single frame. It requires an Ada or newer GPU that drives the display, the `RealTimePathTracing` render mode, `LdrColor` or `HdrColor` as the only render outputs, and a render resolution of at least 126 pixels per side.

## Real-Time Path Tracing Settings (`rtpt:`)

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
| `omni:rtx:rtpt:extraSpecularAndTransmissiveBounces` | `uint` | `0` |
| `omni:rtx:rtpt:maxVolumeBounces` | `uint` | `3` |
| `omni:rtx:pt:fractionalCutoutOpacity` | `bool` | `true` |
| `omni:rtx:rtpt:maxRoughness` | `float` | `0.3` |
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
| `omni:rtx:rtpt:gaussian:nonStochastic:enabled` | `bool` | `false` |

## Path Tracing Settings (`pt:`)

### Path Tracing

| Setting | Type | Default |
|---------|------|---------|
| `omni:rtx:pt:samplesPerPixel` | `uint` | `512` |
| `omni:rtx:pt:samplesPerIteration` | `int` | `1` |
| `omni:rtx:pt:adaptiveSampling:enabled` | `bool` | `true` |
| `omni:rtx:pt:limits:maxBounces` | `uint` | `4` |
| `omni:rtx:pt:limits:extraSpecularAndTransmissiveBounces` | `uint` | `2` |
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

### Firefly Filter

| Setting | Type | Default |
|---------|------|---------|
| `omni:rtx:pt:fireflyFilter:enabled` | `bool` | `true` |
| `omni:rtx:pt:fireflyFilter:maxUnexposedIntensityPerSample` | `float` | `3200.0` |
| `omni:rtx:pt:fireflyFilter:maxUnexposedIntensityPerSampleDiffuse` | `float` | `3200.0` |
| `omni:rtx:pt:fireflyFilter:maxPerEmissiveUnexposedIntensity` | `float` | `3200.0` |

### Spectral Rendering

Enable the process-wide spectral material and light backend before creating the
first renderer, then enable spectral transport on its PT RenderProducts. Run
RGB and spectral comparisons in separate processes; the startup choice cannot
change after initialization, including after destroying all renderer instances.

> **Source (Python startup):** `examples/python/spectral-rendering/main.py` snippet `doc-spectral-config-python`
>
> **Source (C startup):** `examples/c/spectral-rendering/main.cpp` snippet `doc-spectral-config-c`
>
> **Source (USDA):** `tests/docs/usd/data/spectral_rendering.usda` snippet `doc-spectral-authoring`
>
> **Source (USD Python):** `tests/docs/usd/test_spectral_rendering.py` snippet `doc-spectral-authoring-python`

| Setting | Type | Default |
|---------|------|---------|
| `omni:rtx:pathtracing:spectral:enabled` | `bool` | `false` |
| `omni:rtx:pathtracing:spectral:wavelengthMin` | `float` | `10.0` |
| `omni:rtx:pathtracing:spectral:wavelengthMax` | `float` | `10000.0` |
| `renderingColorSpace` | `uniform token` | `"lin_rec709_scene"` |
| `omni:rtx:pathtracing:spectral:responseCurve` | `uint` | `0` |

`renderingColorSpace` is an attribute of the RenderSettings prim, not the RenderProduct, and has no `omni:rtx:` prefix.

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

`omni:rtx:pt:multigpu:enabled` is read from the RenderSettings prim, not the RenderProduct.

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

## View Lighting Mode (Camera Light)

View Lighting Mode replaces all scene lights with a single camera light. By default the camera light is a distant headlight aligned with the view direction; it can be switched to a spot light positioned at the camera. The spot-only settings (radius, cone angle, cone softness) have no effect when the light type is `"distant"`; the angle setting has no effect when the light type is `"spot"`.

> **Source:** `tests/docs/python/test_base.py` snippet `doc-set-view-lighting`

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `omni:rtx:scene:useViewLightingMode` | `bool` | `false` | Enable View Lighting Mode (camera light) |
| `omni:rtx:viewLighting:lightType` | `token` | `"distant"` | Camera light type: `"distant"` or `"spot"` |
| `omni:rtx:viewLighting:color` | `color3f` | `(1, 1, 1)` | Color of the camera light |
| `omni:rtx:viewLighting:intensity` | `float` | `3000.0` | Intensity of the camera light |
| `omni:rtx:viewLighting:normalize` | `bool` | `true` | Removes spot radius-squared brightness gain and normalizes distant angular size. Spot brightness does not attenuate with distance, whether enabled or disabled; radius still affects highlights and grazing illumination |
| `omni:rtx:viewLighting:angle` | `float` | `0.0` | Angular diameter in degrees (distant only) |
| `omni:rtx:viewLighting:radius` | `float` | `0.05` | Sphere radius in world units; larger radii soften specular highlights (spot only) |
| `omni:rtx:viewLighting:coneAngle` | `float` | `90.0` | Degrees from the view direction to the cone edge, UsdLux `shaping:cone:angle` semantics (spot only) |
| `omni:rtx:viewLighting:coneSoftness` | `float` | `0.0` | Softness of the cone falloff, 0 = hard edge (spot only) |

Note: Minimal mode and SDG simple-shading outputs always render the camera light as its distant variant, so the light type and the spot-only settings have no effect there. Both camera-light types are shadowless inspection lights.

## DomeLight MDL Material Baking

When a `DomeLight`'s image source is an MDL material rather than a texture, RTX bakes the material into a lat-long map once and derives importance sampling data from it. These settings control that bake. They are authored per RenderProduct but consumed per scene, as the scoping note below explains.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `omni:rtx:lights:dome:baking:resolution` | `int` | `4096` | Texel width of the baked lat-long map; height is half the width |
| `omni:rtx:domeLight:baking:spp` | `int` | `4` | Samples per texel |
| `omni:rtx:lights:dome:baking:denoising:enabled` | `bool` | `false` | Run the OptiX denoiser over the baked map, so a low `spp` still yields a clean texture |

Both integers are raised to `1` if authored lower, so `0` cannot produce a degenerate bake. Neither has a renderer-side ceiling: the baked texture is capped at 8192 texels *after* `omni:rtx:domeLight:resolutionFactor` is applied, so how large an `omni:rtx:lights:dome:baking:resolution` is usable depends on that factor.

Changing any of the three re-triggers the bake for every affected dome light.

Important: a baked dome light is a **scene-level** resource, not a per-view one. RTX resolves these three settings from the scene's *reference* view (its first view), so when several RenderProducts share a scene only the reference view's opinion is used and the others are silently ignored. Author the same values on every product that shares a dome light. This mirrors how the rest of MDL material baking already behaves.

Denoising trades transient GPU memory for a much lower `spp`. It is worth enabling whenever the MDL material is procedural and noisy; leaving `spp` high instead makes the bake proportionally slower.

Note: `omni:rtx:domeLight:baking:spp` lives on `OmniRtxDebugSettingsAPI_1`, while the other two live on `OmniRtxSettingsCommonAdvancedAPI_1`. A RenderProduct must apply the debug API to author the sample count.

## Minimal Settings

Minimal mode is optimized for speed-of-light rendering performance and stability. It only respects the first `DistantLight` found in the scene, and shadows from that light are hard shadows. Other light types, including `DomeLight`, are ignored for Minimal mode lighting; if no `DistantLight` exists, Minimal mode uses a single camera light instead. For improved visibility, use the ambient light attributes documented in `docs/sensors/cameras/render_modes/minimal.rst`, or disable shadows with `omni:rtx:minimal:castShadows`.

| Setting | Type | Description |
|---------|------|-------------|
| `omni:rtx:minimal:mode` | `int` | Minimal render mode variant |
| `omni:rtx:minimal:constantColor` | `color3f` | Constant color output |
| `omni:rtx:minimal:castShadows` | `bool` | Enable hard shadows from the first `DistantLight` |
| `omni:rtx:sceneDb:ambientLightColor` | `color3f` | Ambient light color |
| `omni:rtx:sceneDb:ambientLightIntensity` | `float` | Ambient light intensity |

### Minimal anti-aliasing and DLSS

Author `int omni:rtx:minimal:dlss:mode` on the RenderProduct: `0` disables DLSS,
`1` enables DLSS-SR, and `2` enables DLSS-RR. Use the token
`omni:rtx:minimal:dlss:execMode` for `auto`, `performance`, `balanced`, `quality`,
or `rtxaa` (native-resolution DLAA). Both attributes belong to
`OmniRtxSettingsMinimalAPI_1`, with defaults of `0` and `auto`, respectively.
These mode-selection controls are separate from the
post-processing DLSS execution mode and the Path Tracing pixel filter.
Gaussian splats additionally require Minimal shading
mode `3` and DLSS-RR for denoising.

The USD authoring snippets use equivalent types, values, and RenderProduct paths:

> **Source (USDA):** `examples/python/minimal-dlss/minimal_dlss.usda` snippet `doc-minimal-dlss-render-product`
>
> **Source (USD Python):** `tests/docs/usd/test_minimal_dlss.py` snippet `doc-minimal-dlss-render-product-python`

The runtime examples load those settings through attached ovstage and preserve
DLSS temporal history across render steps:

> **Source (Python):** `examples/python/minimal-dlss/main.py` snippet `doc-render-minimal-dlss-python`
>
> **Source (C):** `examples/c/minimal-dlss/main.cpp` snippet `doc-minimal-dlss-c-populate`
>
> **Source (C, continued):** `examples/c/minimal-dlss/main.cpp` snippet `doc-minimal-dlss-c-step-renderer`

## Troubleshooting

- Render settings are attributes on the **RenderProduct** prim; write them to the same prim path you pass to `step()` (e.g., `/Render/Camera`). The exceptions in this skill are the global settings `renderingColorSpace` and `omni:rtx:pt:multigpu:enabled`, which are read from the stage's RenderSettings prim (see Spectral Rendering and Multi-GPU).
- The dtype must match the schema type exactly. Most integer settings above are `uint`, so write `np.uint32` -- `omni:rtx:rtpt:maxBounces` is `uint32`, not `int32` or `int64`. Settings typed `token` (such as `omni:rtx:rendermode` and `omni:rtx:pt:pixelFilter:filter`) are written as interned token IDs, not integers; see `writing-attributes` for the full USD-type-to-dtype table.
- After changing a setting, call `reset()` and run warm-up frames before capturing output. The renderer needs time to reconverge.
- Settings use the `omni:rtx:` namespace prefix (`renderingColorSpace`, a UsdRender attribute, has none), with subsystem prefixes like `rtpt:` (real-time path tracing), `post:` (post-processing), etc.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.

## gaussian-splats example

> **Source:** `examples/python/gaussian-splats/main.py` snippet `gaussian-render-python`

## DLSS 5 3D-Guided Neural Rendering

Configure the RenderProduct for `RealTimePathTracing`, request `LdrColor`, and
set `omni:rtx:dlssnr:enabled` to true. `OmniRtxPostDlssNrAPI_1` auto-applies.
The documentation authoring test checks USDA/Python parity without a GPU or
driver; it does not establish runtime behavior or driver support.

> **Source (USDA):** `tests/docs/usd/data/dlss_nr.usda` snippet `doc-dlss-nr-render-product`
>
> **Source (USD Python):** `tests/docs/usd/test_dlss_nr.py` snippet `doc-dlss-nr-render-product-python`

## ParticleField authoring

> **Source:** `tests/docs/usd/test_gaussian_splats_usda.py` snippet `doc-gaussian-non-stochastic-python`

See `docs/geometry/gaussian_splats.rst` for mode restrictions and material behavior.
