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
  GPU interop patterns for CUDA arrays, timeline semaphores, Vulkan shared memory,
  and MIG-safe CUDA-to-Vulkan device matching.
  Use when user asks about CUDA interop, GPU rendering pipelines, Vulkan interop,
  shared memory, timeline semaphores, MIG, or multi-GPU output routing.
license: LicenseRef-NvidiaProprietary
author: NVIDIA ovrtx
tags:
  - ovrtx
  - cuda
  - interop
  - mig
  - multi-gpu
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
- Confirm whether the requested path needs linear CUDA memory (`Device.CUDA` / `OVRTX_MAP_DEVICE_TYPE_CUDA`), a CUDA array (`Device.CUDA_ARRAY` / `OVRTX_MAP_DEVICE_TYPE_CUDA_ARRAY`), or Vulkan shared memory.
- Use `reading-render-output` for CPU readback or non-interop render output mapping.

## Instructions

1. Identify whether the workflow maps render output to CUDA memory, maps output to a CUDA array, writes attributes from CUDA memory, or coordinates CUDA with Vulkan.
2. Read the source snippet for the exact map/unmap path before choosing between linear CUDA memory and a CUDA array; both selectors exist in C (`OVRTX_MAP_DEVICE_TYPE_CUDA`, `OVRTX_MAP_DEVICE_TYPE_CUDA_ARRAY`) and in Python (`Device.CUDA`, `Device.CUDA_ARRAY`).
3. Preserve the synchronization contract: wait on ovrtx-provided CUDA events before reading, record CUDA work completion events before unmapping, and use `sync_stream` only for the auto-sync path.
4. For Vulkan interop, keep external-memory ownership, timeline semaphore ordering, and double-buffer lifetimes aligned with the full `vulkan-interop` example.
5. When changing code, run the CUDA render-output or Vulkan interop example/test that owns the snippet whenever practical.
6. Select a Vulkan device by comparing `cuDeviceGetUuid_v2()` for the configured or mapped CUDA ordinal with `VkPhysicalDeviceIDProperties::deviceUUID`. Do not use PCI identity, `cudaDeviceProp::uuid`, or legacy `cuDeviceGetUuid()` for MIG selection.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.
- On Linux, the CUDA stream/event synchronization in this skill is subject to a known driver scheduling interaction. Windows is unaffected. Refer to `docs/core/cuda_vulkan_scheduling.rst`.

## Overview

ovrtx renders on the GPU and can provide output as CUDA device memory or as a CUDA array (zero-copy). Both are reachable from C and from Python. For advanced pipelines (e.g., Vulkan display, custom CUDA post-processing), you need to handle CUDA synchronization correctly to avoid race conditions between ovrtx's internal GPU work and your own.

## Python

### Map render output to CUDA

> **Source:** `tests/docs/python/test_camera_sensors.py` snippet `doc-map-render-output-cuda`

### Map attribute to CUDA for Warp kernel writes

> **Source:** `tests/docs/python/test_attribute_bindings.py` snippet `doc-map-attribute-cuda`

### Map render output as CUDA array (zero-copy)

`device=Device.CUDA_ARRAY` takes the same zero-copy image path as the C API: ovrtx hands back the render target's CUDA array instead of copying it into linear memory. The array is an opaque image handle, so the DLTensor reports an opaque-handle dtype and **no DLPack consumer can read it** — `np.from_dlpack(rv)`, `.numpy()`, and Warp DLPack ingest all fail or are meaningless here. Read the handle from `tensor.cuda_array`.

`tensor.cuda_array` raises if the tensor is linear memory rather than an array, which is what distinguishes it from reading the raw `dl.data` field yourself. Use `rv["<tensor_name>"]` when the render variable carries several tensors.

> **Source:** `tests/docs/python/test_camera_sensors.py` snippet `doc-map-render-output-cuda-array`

**Reading the handle is your CUDA work, not ovrtx's.** ovrtx exposes the handle as a plain `int` and intentionally ships no Python-CUDA bridge to dereference it. Pick an existing one:

- **Warp 1.15+** (recommended, and what the ovrtx test suite uses): `wp.Texture2D(cuda_array=tensor.cuda_array)` aliases the array without taking ownership and infers extent/dtype from it, then `texture.copy_to(wp_array_or_numpy)` copies the pixels out, or `wp.texture_sample()` samples it inside a kernel. Warp 1.15 is where external-`cuda_array` interop landed; earlier versions have no texture API at all.
  - **`copy_to` picks its own stream: the texture device's *current* Warp stream.** So `rv.wait_on(stream.cuda_stream)` only orders the copy after the producer while that same stream is still current at `copy_to` time — an intervening `wp.ScopedStream(other)` gates the producer on one stream and enqueues the copy on another, and an event recorded on the first stream then does not cover the copy. Bind `stream = wp.get_stream()` once and use it for both the `wait_on` and the post-copy `record_event()`.
  - Warp's `array.numpy()` reads on the device's null stream, bypassing your barrier — synchronize the copy's event first, then read the copy at rest.
- **CuPy**, via `cupy.cuda.texture.CUDAarray` / `TextureObject`.
- **Your own ctypes/driver wrapper**, calling `cudaMemcpy2DFromArray` / `cuMemcpy2D` or binding a surface directly.

**Caveat — pick the device from the tensor, not the default.** The render product is not guaranteed to be on CUDA device 0; with several devices active, different render products can land on different ones. Always take the device from `tensor.device.device_id` and make it current before issuing the copy (`wp.ScopedDevice(f"cuda:{tensor.device.device_id}")`), otherwise the runtime call is issued against the wrong context. Map-time `sync_stream=` is awkward here for the same reason — the stream must live on the array's device, which you only learn after the mapping exists — so prefer `rv.wait()` or `rv.wait_on(stream)`.

## C

`OVRTX_MAP_DEVICE_TYPE_CUDA_ARRAY` is the C spelling of the same zero-copy path (`ovrtx_map_render_var_output`); the Python equivalent is `device=Device.CUDA_ARRAY`.

### Select the exact Vulkan device, including MIG

CUDA device indices are process-visible ordinals after `CUDA_VISIBLE_DEVICES`
is applied. Use the same ordinal for the OVRTX active-GPU filter,
RenderProduct `deviceIds`, and application-side CUDA initialization.

Resolve that ordinal with the CUDA Driver API and query its MIG-aware identity:

> **Source:** `examples/c/vulkan-interop/src/cuda/cuda_kernel.cpp` snippet `resolve-cuda-device-uuid`

Enumerate Vulkan physical devices and compare those UUID bytes with
`VkPhysicalDeviceIDProperties::deviceUUID`:

> **Source:** `examples/c/vulkan-interop/src/vk/vulkan_context.cpp` snippet `select-vulkan-device-by-cuda-uuid`

For a simple application, validate the first mapped output against the
configured ordinal, then retain the initialization-time mapping:

> **Source:** `examples/c/vulkan-interop/src/main.cpp` snippet `validate-render-output-cuda-device`

For multi-GPU rendering, use each mapped output's `DLTensor.device.device_id`
to select a Vulkan context cached for that CUDA ordinal. Do not use PCI identity,
`cudaDeviceProp::uuid`, legacy `cuDeviceGetUuid()`, Vulkan enumeration order, or
whichever CUDA context happens to be current to distinguish MIG instances.

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
| Map to CUDA array | `render_var.map(device=Device.CUDA_ARRAY)` | `OVRTX_MAP_DEVICE_TYPE_CUDA_ARRAY` |
| Get the CUDA array handle | `tensor.cuda_array` | `(CUarray)dl.data` |
| Read the CUDA array | `wp.Texture2D(cuda_array=...)` (Warp 1.15+), CuPy, or your own wrapper | `surf2Dwrite`/`tex2D`, `cudaMemcpy2DFromArray` |
| Wait for render | `rv.wait()`, `rv.wait_on(stream)`, or `sync_stream=` on `map()` | `cuStreamWaitEvent(stream, wait_event, 0)` |
| Signal done | `var.unmap(event=...)` or `var.unmap(stream=...)` | `cuda_sync.wait_event = (uintptr_t)event` |
| Stream sync on map | `sync_stream` parameter | `map_desc.sync_stream` |

C CUDA synchronization uses `ovrtx_cuda_sync_t` with `stream` and `wait_event`
fields. A `stream` value of `0` means no stream, `1` means the default stream,
and values greater than `1` identify a specific CUDA stream. A `wait_event`
value of `0` means no event wait.

## Troubleshooting

- **Vulkan workload much slower than expected on Linux.** Correct stream-ordered synchronization triggers a known driver scheduling interaction that stalls the renderer's Vulkan work. Windows is unaffected. Refer to `docs/core/cuda_vulkan_scheduling.rst` for the workarounds and their tradeoffs. An application can apply the recommended one in-process, provided it runs before the renderer is created:

  > **Source:** `examples/c/vulkan-interop/src/cuda/cuda_kernel.cpp` snippet `cuda-device-max-connections`

- **Consumer owns lifetime (Python).** The C render resource stays alive as long as any DLPack consumer (Warp, PyTorch, CuPy, etc.) holds a reference to the tensor. Drop the views when you're done to release the resource. If you need data to outlive the mapping, take a `.copy()`.
- Always wait on `rendered_output.cuda_sync.wait_event` before accessing CUDA array data.
- Always signal completion (via event or stream) when unmapping after CUDA work, or ovrtx may reclaim the buffer while your kernel is still running.
- The CUDA-array path returns a `CUarray` (opaque handle in `dl.data`, or `tensor.cuda_array` in Python), not linear memory. In C, use `surf2Dwrite`/`tex2D` or copy out with `cudaMemcpy2DFromArray`; in Python, go through Warp 1.15+, CuPy, or your own wrapper. Dereferencing it as a device pointer is an invalid access, not an error you get told about.
- The CUDA path (`OVRTX_MAP_DEVICE_TYPE_CUDA` / `Device.CUDA`) returns linear device memory (may incur a copy for image outputs).
- CUDA mappings report their process-visible CUDA ordinal in `tensor.device.device_id` (C: `dl.device.device_id`). It is in the same post-`CUDA_VISIBLE_DEVICES` namespace used by ovrtx active-GPU filtering and RenderProduct `deviceIds`; use it to route multi-GPU outputs. A CUDA array is not necessarily on device 0, so make that device current before issuing copies or launching kernels against the handle.
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
- Use `render-product-device-pinning` for the RenderProduct `deviceIds` allow-list and CUDA-visible ordinal semantics that precede Vulkan matching.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
