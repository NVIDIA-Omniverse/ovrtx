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
name: reading-render-output
description: >
  Mapping rendered output to access pixel data on CPU or GPU. Use when user asks to get
  pixels, read an image, save a PNG, display rendered output, or access render var
  data.
license: LicenseRef-NvidiaProprietary
author: NVIDIA ovrtx
tags:
  - ovrtx
  - rendering
  - outputs
tools:
  - Read
  - Grep
---

# Reading Render Output

## When to Use

Use this skill when the user asks to get pixels, read an image, save a PNG, display rendered output, or access render var data.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, USD, or a combination.
- RenderProduct path, full RenderVar prim path or reserved synthetic output name, and whether the output is single-tensor or composite.
- Mapping target: CPU pixels, linear CUDA tensor, or C CUDA array mapping.
- Image/tensor shape, dtype, channel order, synchronization requirements, and whether the data must outlive the mapping.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Confirm the RenderProduct already requests the desired RenderVar; use `camera-outputs-rt2` when the question is which camera output to add.
- Use `reading-sensor-pointclouds` for lidar/radar `PointCloud` composite tensors.

## Instructions

1. Identify the RenderProduct path, full RenderVar prim path, target device, and whether the caller needs CPU pixels, CUDA tensors, or CUDA arrays.
2. Read the matching map/unmap snippet before choosing Python `frame.render_vars[...]` access or C `ovrtx_map_render_var_output()`.
3. Preserve dtype, shape, channel order, and ownership rules for the selected output.
4. Always unmap C outputs, and keep CUDA synchronization aligned with the CUDA interop skill when reading on GPU.
5. When changing code, run the camera sensor or minimal example snippet that owns the readback path whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

This skill is the hands-on counterpart to the conceptual reference at `docs/sensors/sensor_outputs.rst`, which describes what a render variable output is and how its tensors and params are laid out. Use this skill for *how* to map and read one; use the conceptual page when the question is about *what* the structure carries or *why* it is shaped the way it is.

After stepping the renderer and fetching results, each `RenderVarOutput` is identified by its full RenderVar prim path (for example `/Render/Camera/LdrColor`) and must be mapped to access its data. Names such as `LdrColor` or `HdrColor` are RenderVar `source_name` values, not Python `frame.render_vars` keys.

A render variable carries one or more named tensors and zero or more named params. For a single-tensor render variable, consume the mapping directly with DLPack (`np.from_dlpack(rv)`); for a multi-tensor render variable, address tensors by name (`rv["TensorName"]`) and reach params through `rv.params["paramName"]`. Both tensors and params expose the DLPack protocol uniformly, so `np.from_dlpack(rv["TensorName"])` and `np.from_dlpack(rv.params["paramName"])` both yield zero-copy NumPy/Warp/etc. arrays.

- In Python, render-var mapping supports `device=Device.CPU`, `device=Device.CUDA`, and `device=Device.CUDA_ARRAY` (from `from ovrtx import Device`).
- `Device.CUDA_ARRAY` / `OVRTX_MAP_DEVICE_TYPE_CUDA_ARRAY` is the zero-copy image path. It yields an opaque CUDA array handle rather than readable memory, so it is outside the DLPack workflow described here — see the `cuda-interop` skill.

After reading/processing, unmap to release the mapped buffer.

## Python

### Map to CPU and read as NumPy

> **Source:** `examples/python/minimal/main.py` snippet `read-render-output`

### Save as PNG with Pillow

> **Source:** `tests/docs/python/test_camera_sensors.py` snippet `doc-step-and-map-camera-outputs`
>
> **Source (save-to-PNG example):** `examples/python/projectors/main.py` snippet `projectors-save-png`

### Map to CUDA for GPU processing

> **Source:** `tests/docs/python/test_camera_sensors.py` snippet `doc-map-render-output-cuda`

## C

### Map to CPU

> **Source:** `examples/c/minimal/main.cpp` snippet `map-rendered-output-cpu`

### Map to linear CUDA memory

> **Source:** `tests/docs/c/test_camera_sensors.cpp` snippet `doc-map-render-output-cuda-c`

### Map to CUDA array (zero-copy)

> **Source:** `tests/docs/c/test_camera_sensors.cpp` snippet `doc-map-render-output-cuda-array-c`

### Find a specific render var in C

This helper is not part of the ovrtx API; define it in your own code (see `examples/c/minimal/main.cpp`):

> **Source:** `examples/c/minimal/main.cpp` snippet `find-output-helper`

## Key Types / Functions

| Python | C |
|--------|---|
| `rv = render_var.map(device=Device.CPU)` | `ovrtx_map_render_var_output(renderer, handle, &desc, timeout, &output)` |
| `np.from_dlpack(rv)` (single-tensor) | `*rendered_output.tensors[0].dl` (DLTensor) |
| `np.from_dlpack(rv["TensorName"])` (multi-tensor) | iterate `rendered_output.tensors[i]` |
| `np.from_dlpack(rv.params["paramName"])` | iterate `rendered_output.params[i]` |
| last DLPack consumer dropping the tensor | `ovrtx_unmap_render_var_output(renderer, map_handle, sync)` |
| `rv.unmap(stream=...)` | `ovrtx_unmap_render_var_output` with `cuda_sync.stream` / `cuda_sync.wait_event` |

Device types (Python: `from ovrtx import Device`; C: `OVRTX_MAP_DEVICE_TYPE_*`):
- `Device.CPU` -- read back to host memory (sync + copy)
- `Device.CUDA` -- linear CUDA device memory (may copy)
- `Device.CUDA_ARRAY` -- zero-copy for image outputs; an opaque CUDA array handle, not DLPack-readable. Read `tensor.cuda_array` and consume it with Warp 1.15+, CuPy, or your own CUDA wrapper (see `cuda-interop`)
- `Device.DEFAULT` -- auto-selects the most efficient format; returns a CUDA array for image outputs, avoiding an extra copy

Common render variables:
- `LdrColor` -- single-tensor, RGBA uint8, sRGB color space
- `HdrColor` -- single-tensor, RGBA float16, linear color space
- Render variables may also carry multiple tensors plus params (e.g. a point-cloud render variable producing `Coordinates` + `Intensity` tensors alongside `frameId` / `hitCount` params); address those by name.

## Troubleshooting

- **Consumer owns lifetime.** A mapping's C buffer stays alive for exactly as long as DLPack consumers (NumPy, Warp, etc.) reference it via `np.from_dlpack` / `wp.from_dlpack`. Drop those views (via `del`, rebind, or scope exit) to free the resource. If you need data beyond that, take an independent copy: `np.from_dlpack(var).copy()`.
- **Mind Python's deferred reclamation.** A `MappedRenderVar` and any `RenderVarTensor` / `RenderVarParam` / DLPack array minted from it stays alive in its local-variable slot until that name is rebound or the enclosing scope ends. A `with` block releases interest in the mapping (the C unmap fires once the last view is dropped), but the Python names can outlive the `with` — most commonly the loop variable bound inside a `for` loop survives until the next iteration rebinds it, or until the loop exits. When you're done with a mapping but the owning name will outlive that interest, `del` it explicitly so renderer resources are reclaimed promptly instead of waiting on garbage collection.
- Mapping lifetime is independent of the owning `products` object. Dropping `products` (or its C-level `ovrtx_destroy_results`) does not invalidate live mappings — consumer references are what keep their buffers alive.
- For `CUDA_ARRAY` mapping, you must wait for the producer before accessing the data: in C, on `rendered_output.cuda_sync.wait_event`; in Python, via `rv.wait()` or `rv.wait_on(stream)`.
- For explicit CUDA sync in Python, call `var.unmap(stream=...)` or `var.unmap(event=...)` — these record the sync hint used when ovrtx reclaims the buffer.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
