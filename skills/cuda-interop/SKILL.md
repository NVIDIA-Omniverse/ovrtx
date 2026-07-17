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
name: cuda-interop
description: >
  GPU interop patterns for CUDA arrays, timeline semaphores, and Vulkan shared memory.
  Use when user asks about CUDA interop, GPU rendering pipelines, Vulkan interop,
  shared memory, or timeline semaphores.
license: LicenseRef-NvidiaProprietary
version: "0.3.0"
author: NVIDIA ovrtx
tags:
  - ovrtx
  - cuda
  - interop
tools:
  - Read
  - Grep
---

# CUDA Interop

## When to Use

Use this skill when the user asks about CUDA interop, GPU rendering pipelines, Vulkan interop, shared memory, or timeline semaphores.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Target API surface: Python, C/C++, USD, or a combination.
- Interop path: render output to linear CUDA memory, render output to CUDA array, attribute mapping to CUDA, or Vulkan external memory.
- RenderProduct/RenderVar or attribute target, CUDA device expectations, stream/event handles, and ownership boundaries.
- Tensor/image shape, dtype, synchronization points, and whether the consumer expects linear memory or array/image memory.
- Repository source snippets referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Read the relevant `> **Source:**` snippet before writing or explaining API usage.
- Confirm whether the requested path needs `Device.CUDA`, `OVRTX_MAP_DEVICE_TYPE_CUDA`, `OVRTX_MAP_DEVICE_TYPE_CUDA_ARRAY`, or Vulkan shared memory.
- Use `reading-render-output` for CPU readback or non-interop render output mapping.

## Instructions

1. Identify whether the workflow maps render output to CUDA memory, maps output to a CUDA array, writes attributes from CUDA memory, or coordinates CUDA with Vulkan.
2. Read the source snippet for the exact map/unmap path before choosing `OVRTX_MAP_DEVICE_TYPE_CUDA`, `OVRTX_MAP_DEVICE_TYPE_CUDA_ARRAY`, or Python `Device.CUDA`.
3. Preserve the synchronization contract: wait on ovrtx-provided CUDA events before reading, record CUDA work completion events before unmapping, and use `sync_stream` only for the auto-sync path.
4. For Vulkan interop, keep external-memory ownership, timeline semaphore ordering, and double-buffer lifetimes aligned with the full `vulkan-interop` example.
5. When changing code, run the CUDA render-output or Vulkan interop example/test that owns the snippet whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

ovrtx renders on the GPU and can provide output as CUDA device memory, and in C it can also provide CUDA arrays (zero-copy). For advanced pipelines (e.g., Vulkan display, custom CUDA post-processing), you need to handle CUDA synchronization correctly to avoid race conditions between ovrtx's internal GPU work and your own.

## Python

### Map render output to CUDA

> **Source:** `tests/docs/python/test_camera_sensors.py` snippet `doc-map-render-output-cuda`

### Map attribute to CUDA for Warp kernel writes

> **Source:** `tests/docs/python/test_attribute_bindings.py` snippet `doc-map-attribute-cuda`

## C

`OVRTX_MAP_DEVICE_TYPE_CUDA_ARRAY` is available through the C API (`ovrtx_map_render_var_output`). Python render-var mapping uses `device=Device.CPU` / `device=Device.CUDA` and does not expose a CUDA-array selector.

### Map render output to linear CUDA memory

Use `OVRTX_MAP_DEVICE_TYPE_CUDA` when your CUDA consumer expects a linear device pointer. Image outputs may require an internal copy into linear memory.

> **Source:** `tests/docs/c/test_camera_sensors.cpp` snippet `doc-map-render-output-cuda-c`

### Map render output as CUDA array (zero-copy)

Use `OVRTX_MAP_DEVICE_TYPE_CUDA_ARRAY` when your CUDA consumer can read a `CUarray` through texture/surface APIs and you want the zero-copy image path.

> **Source:** `tests/docs/c/test_camera_sensors.cpp` snippet `doc-map-render-output-cuda-array-c`

### Wait for render completion before accessing

The output may not be fully written when `map` returns. Check the wait event:

> **Source:** `examples/c/vulkan-interop/src/main.cpp` snippet `map-rendered-output-cuda-array`
>
> Check `rendered_output.cuda_sync.wait_event` and call `cuStreamWaitEvent` before accessing.

### Signal when CUDA work is done, then unmap

> **Source:** `examples/c/vulkan-interop/src/main.cpp` snippet `write-camera-transform`
>
> Record a CUDA event after your kernel, then pass it via `ovrtx_cuda_sync_t.wait_event` on unmap.

### Double-buffered async pattern (from vulkan-interop example)

For maximum throughput, use two shared images and ping-pong between them.
CUDA writes to one while a consumer (e.g., Vulkan) reads the other.

See `examples/c/vulkan-interop/src/main.cpp` for the full double-buffered async
rendering pattern with timeline semaphores and CUDA-Vulkan shared images.

### Map with sync_stream (auto-sync)

If you provide `sync_stream` on the map call, ovrtx inserts the wait automatically:

> **Source:** `examples/c/vulkan-interop/src/main.cpp` snippet `map-rendered-output-cuda-array`
>
> Set `map_desc.sync_stream = (uintptr_t)cuda_stream` for automatic synchronization.

## Key Types / Functions

| Concept | Python | C |
|---------|--------|---|
| Map to CUDA | `render_var.map(device=Device.CUDA)` | `OVRTX_MAP_DEVICE_TYPE_CUDA` |
| Map to CUDA array | N/A (Python uses CUDA) | `OVRTX_MAP_DEVICE_TYPE_CUDA_ARRAY` |
| Wait for render | `sync_stream=` on `map()` | `cuStreamWaitEvent(stream, wait_event, 0)` |
| Signal done | `var.unmap(stream=...)` | `cuda_sync.wait_event = (uintptr_t)event` |
| Stream sync on map | `sync_stream` parameter | `map_desc.sync_stream` |

C CUDA synchronization uses `ovrtx_cuda_sync_t` with `stream` and `wait_event`
fields. A `stream` value of `0` means no stream, `1` means the default stream,
and values greater than `1` identify a specific CUDA stream. A `wait_event`
value of `0` means no event wait.

## Troubleshooting

- **Consumer owns lifetime (Python).** The C render resource stays alive as long as any DLPack consumer (Warp, PyTorch, CuPy, etc.) holds a reference to the tensor. Drop the views when you're done to release the resource. If you need data to outlive the mapping, take a `.copy()`.
- Always wait on `rendered_output.cuda_sync.wait_event` before accessing CUDA array data.
- Always signal completion (via event or stream) when unmapping after CUDA work, or ovrtx may reclaim the buffer while your kernel is still running.
- In C, `OVRTX_MAP_DEVICE_TYPE_CUDA_ARRAY` returns a `CUarray` (opaque pointer in `dl.data`), not linear memory. Use `surf2Dwrite`/`tex2D` to access it.
- In C, `OVRTX_MAP_DEVICE_TYPE_CUDA` returns linear device memory (may incur a copy for image outputs).
- In Python, `event` and `stream` on `unmap()` are mutually exclusive — pass one or the other.
- `write_attribute()`, `write_array_attribute()`, and `binding.write()` also accept `cuda_stream=` and `cuda_event=` for GPU-synchronised writes. When you pass a CUDA Warp/PyTorch/etc. tensor together with `cuda_stream=`, ovrtx forwards the stream to the producer's DLPack sync — the producer bridges its internal stream automatically, so no manual `wp.synchronize_stream` is needed before the call.

## In Attached Mode (ovrtx 0.4+)

Rendered-output mapping (this skill) is unchanged by attached mode — ovrtx still
owns render products and their DLPack surfaces. What changes is the
**attribute-side** tensor exchange: when reading or writing ovstage-managed
attribute data (transforms, materials, cloned columns), the DLTensor path and
CUDA sync are owned by ovstage. See ovstage
``skills/dlpack-tensor-exchange/SKILL.md`` for the copy-in / copy-out / zero-copy
map/unmap model, CPU vs CUDA residency, and ``cuda_sync`` semantics for
attribute data.

See `docs/core/ovstage_integration.rst`, `skills/update-0_3-0_4-c/SKILL.md` and `skills/update-0_3-0_4-python/SKILL.md`.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
