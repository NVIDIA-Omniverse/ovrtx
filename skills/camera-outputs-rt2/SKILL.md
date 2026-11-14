---
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
name: camera-outputs-rt2
description: >
  Available camera render outputs for Real-Time Path Tracing (RT2) mode. Use when user
  asks what AOVs/render vars are available, what format or dtype an output has, or how
  to read a specific output like depth, normals, albedo, or distance. Also use to
  distinguish RT2 outputs from Path Tracing back-to-beauty compositing passes.
license: CC-BY-4.0 AND Apache-2.0
author: NVIDIA ovrtx
tags:
  - ovrtx
  - rendering
  - camera
tools:
  - Read
  - Grep
---

# Camera Outputs -- Real-Time Path Tracing (RT2)

## When to Use

Use this skill when the user asks what AOVs/render vars are available, what format or dtype an output has, how to read a specific output like depth, normals, albedo, or distance, or whether camera outputs can reconstruct beauty.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, USD, or a combination.
- Requested AOV/sourceName, RenderProduct path, and whether the user needs USD authoring, output selection, or readback guidance.
- Expected dtype, shape, channel count, and any known backend limitations for that output.
- Whether extra outputs are acceptable for memory/performance, or only the requested output should be added.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Use `reading-render-output` for the concrete map/read code once the requested camera output is selected.
- Keep the output catalog scoped to RT2. Use the compositing guidance below to route a back-to-beauty request to the tested Path Tracing workflow. Use sensor skills for lidar/radar PointCloud outputs.

## Instructions

1. Identify the render mode, requested camera output, and whether the caller needs USD authoring, Python readback, or C readback.
2. Start with `LdrColor` unless the request specifically needs HDR, depth, normals, semantic IDs, or another listed AOV.
3. Add only the requested `RenderVar` entries to the RenderProduct `orderedVars`; each extra output has memory cost.
4. Preserve the documented dtype, shape, and channel count when mapping output tensors.
5. When changing code, run the camera AOV smoke test that owns the output table whenever practical.
6. For compositing, follow the exact seven-output Path Tracing recipe below. Do not infer an RT2 reconstruction formula from output names.

## Output Format

- Return the selected `sourceName`, dtype, shape, and readback skill needed for the requested output.
- For code changes, summarize RenderVar/RenderProduct edits and validation run.

## Scripts

This skill has no scripts.

## Limitations

- `DepthSD` is deprecated; use `DistanceToImagePlaneSD` or `DistanceToCameraSD` instead. It also currently returns all zeros through the C API.
- The output table is scoped to Real-Time Path Tracing mode.
- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Default choice

Most applications only need `LdrColor` unless the user specifically requests other outputs (e.g. depth, normals). Do not add extra AOVs by default -- each one has a memory cost.

## Available outputs

The following RenderVar `sourceName` values are available when using Real-Time Path Tracing mode. Set each as the `sourceName` attribute on a `RenderVar` prim under a `RenderProduct`.

| `sourceName` | Format | Type | NumPy dtype | Shape | Description |
|---|---|---|---|---|---|
| `LdrColor` | RGBA | uint8 | `uint8` | `(H, W, 4)` | Tone-mapped sRGB color. Standard display-ready output. |
| `HdrColor` | RGBA | float16 | `float16` | `(H, W, 4)` | Linear-space HDR color. Use for post-processing and compositing. |
| `SelectionState` | Four coverage samples | uint16 | `uint16` | `(H, W, 4)` | Output-resolution selected group (bits 0–7) and visibility (bit 8) per sample; zero group is background. Replaces the native selection overlay. See `examples/c/selection-spg`. Also available in PT. |
| `NormalSD` | XYZA | float32 | `float32` | `(H, W, 4)` | World-space surface normals. |
| `DepthSD` | Z | float32 | `float32` | `(H, W, 1)` | **Deprecated** -- use `DistanceToImagePlaneSD` or `DistanceToCameraSD`. For a perspective camera, unitless raster depth mapped from 1 (near clip) to 0 (far clip), 0 for a miss; orthographic cameras reverse it, and fisheye or other lens projections store the distance from the camera. **Known bug:** returns all zeros via the C API. |
| `DistanceToCameraSD` | Z | float32 | `float32` | `(H, W, 1)` | Euclidean distance from camera origin to surface, in meters. |
| `DistanceToImagePlaneSD` | Z | float32 | `float32` | `(H, W, 1)` | Perpendicular distance from image plane to surface, in meters. |
| `DiffuseAlbedoSD` | RGBA | uint8 | `uint8` | `(H, W, 4)` | Diffuse surface albedo (base color without lighting). |
| `Camera3dPositionSD` | XYZA | float32 | `float32` | `(H, W, 4)` | Camera-space 3D position of each surface point, in scene units. |
| `SemanticSegmentation` | ID | uint32 | `uint32` | `(H, W, 1)` | Per-pixel semantic ID. Decode `SemanticIdMap` to map IDs to semantic label strings. |
| `SemanticIdMap` | IdentifierMap | Named tensors | `uint32`, `uint64`, `uint8` | `id (N,4)`, `label_offsets (N+1,)`, `label_data (B,)` | Semantic IDs and UTF-8 labels. Offsets delimit each row's bytes; preserve sparse rows and all four ID words. |

## Python example

> **Source:** `tests/docs/python/test_camera_aovs.py` snippet `doc-camera-aov-smoke-test`

## C example

In C, image DLTensor outputs use channel-last shape `(H, W, C)` with `dtype.lanes = 1`. The `dtype.code` reflects the format kind directly: `kDLUInt` for `LdrColor` / `DiffuseAlbedoSD` / `SemanticSegmentation`, `kDLFloat` for `HdrColor` / `NormalSD` / `DepthSD` / `DistanceToCameraSD` / `DistanceToImagePlaneSD` / `Camera3dPositionSD`. `SemanticIdMap` exposes three named tensors: `id`, `label_offsets`, and `label_data`. Use the identifier decoder for labels. CPU/default mappings return CPU tensors; CUDA mappings return GPU tensors. CUDA-array mapping is unsupported.

> **Source:** `tests/docs/c/test_camera_aovs.cpp` snippet `doc-camera-aov-smoke-test-c`
> **Source:** `tests/docs/c/test_camera_aovs.cpp` snippet `doc-sd-identifiers-c`
> **Source:** `tests/docs/python/test_camera_aovs.py` snippet `doc-sd-identifiers-python`

## USD setup

Add each output as a `RenderVar` prim under a `RenderProduct`, referencing it
in `orderedVars`:

> **Source:** `tests/docs/python/test_camera_aovs.py` snippet `doc-camera-aov-usda`

Only include the outputs you need -- there is no requirement to request all of them.

## Compositing and back to beauty

The documented seven-pass reconstruction uses ``PathTracing``. RT2 does not
provide a supported general decomposition with the same sum. Its documented
color, geometry, and annotation outputs remain useful for their stated purposes.
Internal lighting or denoiser buffers do not establish a public RT2 compositing
contract.

Read ``docs/sensors/cameras/render_modes/path_tracing.rst``, section
**Compositing and Back to Beauty**, before advising on pass contents, denoising, or another renderer's
compositing workflow. The additive RGB set is exactly:

- ``PtDirectIllumation``: direct diffuse reflection; preserve the renderer spelling.
- ``PtGlobalIllumination``: indirect diffuse reflection.
- ``PtReflections``: direct and indirect glossy/specular reflection, including highlights.
- ``PtRefractions``: direct and indirect glossy/specular transmission.
- ``PtSubsurfaceScattering``: direct and indirect diffuse transmission/subsurface scattering.
- ``PtSelfIllumination``: camera-visible emission, light hits, and environment misses.
- ``PtVolumes``: direct and indirect contributions beginning with volume scattering.

Request the passes on one RenderProduct and capture one completed frame.
Convert the float16 RGB channels to float32, then add the seven arrays.
Ignore alpha for this radiance sum. Never glob ``Pt*.exr``: filters, geometric
outputs, pre-denoised beauty, and background would contaminate it.
``PtBackground`` is not an eighth term; the directly visible background is
already included in ``PtSelfIllumination``.

The lighting passes already contain their material weighting. Do not multiply
them again by ``PtDiffuseFilter``, ``PtReflectionFilter``,
``PtRefractionFilter``, or ``PtSubsurfaceFilter``.
RenderVar ``sourceType = "raw"`` selects a named renderer output. It does not
remove the material filter from a lighting pass.

``PtSubsurfaceFilter`` stores primary-hit subsurface albedo estimated from volume
absorption and scattering coefficients, weighted by diffuse transmission.
``PtSubsurfaceScattering`` also includes diffuse-transmission paths without
volume scattering. It can therefore be nonzero while the filter is zero, for
example for thin-walled materials. Do not infer that a zero filter means the
scattering radiance is zero.

Match the processing stage when choosing a reference. ``PtPreDenoisedResult``
is a pre-denoising reference; ``HdrColor`` is suitable when its processing
matches the passes. For ``LdrColor``, reproduce the capture's exposure,
tone mapping, display transfer, clipping, and quantization after summing.
Do not sum display previews or apply exposure twice.
The supplied PT example's lighting outputs already include camera exposure;
its compositor applies no additional exposure multiplier.

For an undenoised comparison, disable denoising for the beauty and components.
For denoised reconstruction, use
``omni:rtx:pt:denoising:enabled`` and
``omni:rtx:pt:denoising:optix:denoiseAOVs``. A volume scene additionally
requires volume AOV denoising support. Denoising only beauty, or leaving
``PtVolumes`` noisy, does not validate a denoised sum.
Report the actual comparison tolerance; do not promise bit-exact results.

The Python example captures the supplied scene and checks the sum after ACES
Approximation and sRGB conversion. That conversion is specific to its settings.

> **Source:** `examples/python/aov-compositing/render-aovs.py` snippet `doc-aov-compositing-render`
> **Source:** `examples/python/aov-compositing/composite-aovs.py` snippet `doc-aov-compositing-inputs`
> **Source:** `examples/python/aov-compositing/composite-aovs.py` snippet `doc-aov-compositing-sum`
> **Source:** `examples/python/aov-compositing/composite-aovs.py` snippet `doc-aov-compositing-display`
> **Source:** `examples/python/aov-compositing/composite-aovs.py` snippet `doc-aov-compositing-compare`

Use ``docs/sensors/cameras/light_path_expressions.rst`` for custom path
selections and its radiance-cache and nine-output limitations. Arbitrary LPEs
can overlap and must not be assumed additive.

## Discovery versus requested output

Common color and documented SDG outputs are advertised independently of
``/rtx-transient/aov/enableRtxAovs``. This flag defaults to false and adds
extended RTX names to the renderer's available-AOV list. Its authored name is
``omni:rtx:transient:aov:enableRtxAovs``.
Explicit PT RenderVar requests allocate the requested outputs independently
of the discovery flag; do not make enabling it a blanket prerequisite.

A listed or registered name can still identify an internal, conditional, or
mode-specific buffer. Enabling discovery does not produce every buffer, expose
a new RT2 compositing contract, or replace ``orderedVars`` authoring.
Internal denoiser/training composites can use diffuse albedo times diffuse
lighting plus specular albedo times specular lighting plus emission. That
relationship omits operations such as anti-aliasing, fog, and post-processing.
It is not a public RT2 beauty recipe; do not substitute similarly named PT
outputs into it.

## Related skills

- `reading-render-output` -- how to map and access render var pixel data
- `configuring-lidar-sensors` / `configuring-radar-sensors` for non-camera sensors, and [Sensor Configuration](https://nvidia-omniverse.github.io/ovrtx/sensors/common/output_configuration.html) for RenderProduct and RenderVar prim setup
- `stepping-and-rendering` -- stepping the renderer and iterating over results

## Troubleshooting

- If an output is missing from a rendered frame, confirm its `RenderVar` is listed in the parent RenderProduct `orderedVars`.
- If a tensor shape or dtype differs from the table, verify the active render mode and readback path before changing downstream processing.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.

Product documentation owns the detail this skill only summarizes:

- [Camera Outputs](https://nvidia-omniverse.github.io/ovrtx/sensors/cameras/outputs.html) -- the same table per render mode, with example images. Path Tracing currently exposes only `LdrColor` and `HdrColor` as named sources, and also accepts custom outputs written as [Light Path Expressions](https://nvidia-omniverse.github.io/ovrtx/sensors/cameras/light_path_expressions.html). Minimal delivers its shaded image as `LdrColor`, and only when the RenderProduct does not also request `HdrColor`; its `HdrColor` stays black.
- [Render Modes](https://nvidia-omniverse.github.io/ovrtx/sensors/cameras/render_modes.html) -- what each mode is and when to pick it.
- [Cameras](https://nvidia-omniverse.github.io/ovrtx/sensors/cameras.html) and [Sensor Configuration](https://nvidia-omniverse.github.io/ovrtx/sensors/common/output_configuration.html) -- authoring a camera RenderProduct and its RenderVars.
- [Sensor Outputs](https://nvidia-omniverse.github.io/ovrtx/sensors/common/sensor_outputs.html) -- mapping an output and reading the tensor back.
- [Camera generic core model](https://nvidia-omniverse.github.io/ovrtx/sensors/visual/camera_core/index.html) and [Shape an Image Like a Camera Sensor](https://nvidia-omniverse.github.io/ovrtx/sensors/visual/camera_core/howto/image_pipeline.html) -- for a simulated sensor and ISP on top of the rendered image, rather than the raw AOVs above.
