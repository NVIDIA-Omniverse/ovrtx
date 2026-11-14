<!--
SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
-->

# Render outputs and product identity

Use this reference with the [0.6-to-0.7 upgrade skill](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/skills/update-0-6-to-0-7/SKILL.md).

## Per-output status and result layouts

Search step/fetch consumers for assumptions that every returned RenderVar succeeded,
that a failed output disappears, or that every interpolated frame has all outputs.

- Check each output's status before mapping. Failed outputs report an error
  message; other outputs from the same RenderProduct can still succeed.
- Python exposes `RenderVarOutput.status` and `error_message`. C consumers must
  use the target `ovrtx_render_product_render_var_output_t` layout.
- DLSS Frame Generation's interpolated frames contain color outputs only.
  Do not index absent depth or segmentation outputs as if they were simulated frames.
- Handle missing, failed, and successful-but-empty outputs separately.

Read [render-output handling](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/skills/reading-render-output/SKILL.md) and
[frame generation](https://nvidia-omniverse.github.io/ovrtx/0.7.0/sensors/cameras/render_modes/real_time_path_tracing/frame_generation.html).

## Structured non-image SDG outputs

Search custom decoders for packed byte offsets and casts for bounding boxes,
ID maps, semantic records, and `CameraParams`.

- Replace packed-blob assumptions with lookup of named tensors and CPU parameters.
  Inspect each field's declared dtype, shape, strides, and byte offset.
- Do not assume fields are contiguous or stored in independent allocations.
- For outputs exposing `valid_count`, consume only that many records, not the
  allocated capacity. Scalar parameters have shape `(1,)`.
- Keep mappings alive while reading their views, and synchronize GPU access.
  Empty semantic bounding-box outputs can be mapped to CPU memory.
- Update downstream decoders and serialized reference data together; do not
  reinterpret a new structured result using the old binary record layout.

Read [SDG output decoding](https://nvidia-omniverse.github.io/ovrtx/0.7.0/sensors/cameras/decoding_outputs.html).

> **Source (Python):** [Camera output decoders](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/tests/docs/python/test_camera_aovs.py), snippet `doc-sd-boxes-python`.
>
> **Source (C):** [Camera output decoders](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/tests/docs/c/test_camera_aovs.cpp), snippet `doc-sd-boxes-c`.

## Compression authoring and buffer sizes

Search `ovrtx:compression:*`, `orderedVars`, `sourceName`, and compressed-buffer readers.

- Author compression settings on the actual RenderVars listed in `orderedVars`.
  Remove reliance on fallback locations derived from `sourceName`.
- Apply settings independently to distinct RenderVars, including those that
  share a source name. Check output status when a codec/configuration is unsupported.
- GPU mappings describe buffer capacity. Read the encoded header for the valid
  bitstream length instead of treating every allocated byte as encoded data.

Read the target [C API](https://nvidia-omniverse.github.io/ovrtx/0.7.0/c_api/index.html)
and [Python output API](https://nvidia-omniverse.github.io/ovrtx/0.7.0/python_api/index.html#python-api-render-outputs).

## RenderProduct identity

Search multiple-product setup for repeated camera/resolution/`viewportHandle`
combinations.

- RenderProducts with the same camera, resolution, and authored `viewportHandle`
  are rejected. For independent products, remove `viewportHandle` or give each a
  distinct value. Consolidate RenderVars only if one product is intended.
