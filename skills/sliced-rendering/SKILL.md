---
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
name: sliced-rendering
description: >
  Render one ovrtx RenderProduct as sequential dataWindowNDC crops and stitch
  the mapped tiles into one image. Use for sliced or chunked image rendering, or when the user asks how to render a very large image; do not use for multi-camera tiled RenderProducts.
license: LicenseRef-NvidiaProprietary
author: NVIDIA ovrtx
tags:
  - ovrtx
  - rendering
  - cropping
  - stitching
tools:
  - Read
  - Grep
---

# Sliced Rendering

## When to Use

Use this skill when an application must render one camera image as multiple
``dataWindowNDC`` regions and reassemble the mapped outputs, for example to render an image larger than 8k. Use the tiled
rendering example instead when one RenderProduct combines multiple cameras.

## Inputs

- Full RenderProduct resolution and RenderVar path.
- Crop grid or explicit ``(xmin, ymin, xmax, ymax)`` windows.
- Tile traversal order, warmup count, and output device.
- Destination image layout and whether exact full-frame equivalence is needed.

## Prerequisites

- Read ``writing-attributes`` and ``attribute-bindings`` for repeated OVStage
  writes through one stable RenderProduct query.
- Read ``warmup`` for accumulation and texture-streaming behavior.
- Read ``reading-render-output`` for mapping and ownership.
- Start from the runnable Python source referenced below.

## Instructions

1. Keep the RenderProduct's authored ``resolution`` at the desired full-image
   size. Author or populate ``dataWindowNDC`` as a scalar ``float4`` first.
2. Define non-overlapping, pixel-aligned crop windows. OpenUSD NDC uses
   ``(xmin, ymin, xmax, ymax)`` with a bottom-left origin.
3. Reuse one OVStage query for the RenderProduct. Encode each crop as one
   ``float32`` logical element with four DLPack lanes, not four scalar rows.
4. For every crop, allocate a monotonically increasing ordinal, wait for the
   attribute write, advance the write floor, and render that same ordinal.
5. Warm up after publishing each crop when RTPT image quality matters. Discard
   warmup outputs and capture a separate final step.
6. Map the full RenderVar prim path to CPU, copy the DLPack view before unmap,
   and validate tile shape, dtype, and channel count before stitching.
7. Place tiles using the renderer output's row orientation. The reference
   ``LdrColor`` workflow places the lower NDC half in the lower-index tensor
   rows; do not assume Pillow's top-left display convention matches NDC.
8. Verify every destination pixel is covered exactly once. Visually inspect
   seams and, when equivalence is required, compare with a full-window render.
9. Release the reusable query and path list before detaching and destroying the
   stage and renderer.

## Python

> **Source (tested crop writes and stitching):** `tests/docs/python/test_base.py` snippet `doc-sliced-rendering`
> **Source (complete application setup):** `examples/python/sliced-rendering/main.py` snippet `sliced-rendering-setup`
> **Source (warmup and capture loop):** `examples/python/sliced-rendering/main.py` snippet `sliced-rendering-render-and-stitch`

## Validation

- Run ``tests/docs/python/test_base.py::test_sliced_rendering`` against the
  intended OVRTX and OVStage builds.
- Run ``examples/python/sliced-rendering/main.py --png`` and confirm the output
  is full resolution with correctly oriented, continuous seams.

## Output Format

- State the crop windows, traversal order, full resolution, and tile sizes.
- Identify the application-owned ordinal and warmup count.
- Report the output RenderVar path, dtype, shape, and stitching orientation.
- List the exact validation command and observed output dimensions.

## Scripts

This skill has no scripts. Use the tested snippets and runnable example.

## Limitations

- Successive RTPT crops may not be pixel-identical to a single full-window
  render because temporal accumulation and sampling history differ by crop.
- Non-pixel-aligned NDC boundaries can introduce gaps, overlaps, or rounding
  differences.
- This skill covers CPU stitching. For GPU-resident composition, also use the
  ``cuda-interop`` skill and preserve explicit synchronization.

## Troubleshooting

- If crop dimensions are wrong, verify the NDC boundaries align with pixel
  centers at the authored full resolution.
- If tiles are vertically swapped, check NDC bottom-left orientation against
  the mapped tensor's row order before changing crop traversal.
- If seams differ in brightness or noise, warm up every crop equally and avoid
  advancing unrelated scene state between captures.
- If a crop update is ignored, wait for its write, advance the write floor, and
  render the same ordinal.

## References

- ``examples/python/crop-window`` for one static crop.
- ``examples/python/sliced-rendering`` for four sequential quadrants.
- ``docs/examples/python_sliced_rendering.rst`` for the user-facing workflow.
