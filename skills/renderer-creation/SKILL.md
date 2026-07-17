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
name: renderer-creation
description: >
  Creating and configuring an ovrtx renderer instance. Use when user asks to create a
  renderer, initialize ovrtx, configure renderer options, or set up ovrtx.
license: LicenseRef-NvidiaProprietary
version: "0.3.0"
author: NVIDIA ovrtx
tags:
  - ovrtx
  - renderer
  - setup
tools:
  - Read
  - Grep
---

# Renderer Creation

## When to Use

Use this skill when the user asks to create a renderer, initialize ovrtx, configure renderer options, or set up ovrtx.

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

The renderer is the central object in ovrtx. You must create one before loading USD scenes, stepping, or reading output. The renderer manages all GPU resources and the internal rendering pipeline.

## Python

Create a renderer with default settings:

> **Source:** `examples/python/minimal/main.py` snippet `create-renderer`

Or with configuration:

> **Source:** `tests/docs/python/test_support_api.py` snippet `doc-renderer-config`

Cleanup is automatic -- the renderer is destroyed when it goes out of scope.

## C

All public C examples and doc tests link the **static** ovrtx loader
(`ovrtx::ovrtx_static`) and hand `ovrtx_create_renderer()` a
`binary_package_root_path` built from `OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx"`.
`ovrtx_setup_runtime()` stages a side-by-side `ovrtx/` link next to the
executable, and the token resolves to the running executable's directory at
runtime, so the loader finds the package without hard-coding an install path:

> **Source:** `examples/c/minimal/main.cpp` snippet `create-renderer`

### Optional explicit initialize/shutdown

`ovrtx_initialize()` is optional. If you do not call it, `ovrtx_create_renderer()` initializes ovrtx automatically.

Use explicit initialize/shutdown when creating and destroying multiple renderers in a process and you want one-time loader initialization to happen once:

> **Source:** `examples/c/vulkan-interop/src/main.cpp` snippet `initialize-and-create-renderer`

If ovrtx is used together with ovPhysX in the same process, ovrtx must be initialized first. In Python, this means `import ovrtx` must come before `import ovphysx`. In C/C++, call `ovrtx_initialize()` before initializing ovPhysX.

With configuration entries:

> **Source:** `tests/docs/c/test_support_api.cpp` snippet `doc-version-and-config-c`
>
> To add config entries, populate `config.entries` and `config.entry_count` before calling `ovrtx_create_renderer`. See the `ovrtx_config_entry_*` helpers in `ovrtx_config.h`.

Cleanup is manual -- you must call `ovrtx_destroy_renderer()`:

> **Source:** `examples/c/minimal/main.cpp` snippet `unmap-and-cleanup`

## Key Types / Functions

| Python | C |
|--------|---|
| `Renderer(config=None)` | `ovrtx_create_renderer(config, &renderer)` |
| `RendererConfig` | `ovrtx_config_t` + `ovrtx_config_entry_t` |
| automatic `__del__` | `ovrtx_destroy_renderer(renderer)` |
| `renderer.version` → `(major, minor, patch)` | `ovrtx_get_version(&major, &minor, &patch)` (callable before init) |
| `renderer.config` → `RendererConfig` | (no C equivalent -- config was passed at creation) |

Config helpers in C (`ovrtx_config.h`):
- `ovrtx_config_entry_sync_mode(bool)`
- `ovrtx_config_entry_log_file_path(ovx_string_t)`
- `ovrtx_config_entry_log_level(ovx_string_t)`
- `ovrtx_config_entry_binary_package_root_path(ovx_string_t)`
- `ovrtx_config_entry_enable_profiling(bool)`
- `ovrtx_config_entry_read_gpu_transforms(bool)`
- `ovrtx_config_entry_keep_system_alive(bool)` -- keep shared GPU resources alive after the last renderer is destroyed, so a subsequent `ovrtx_create_renderer` reuses them
- `ovrtx_config_entry_active_cuda_gpus(ovx_string_t)` -- comma-separated CUDA-visible device indices (e.g., `"0,1,2"`), after `CUDA_VISIBLE_DEVICES` filtering/remapping, to select which GPUs the renderer may use
- `ovrtx_config_entry_use_vulkan(bool)` -- select Vulkan rendering backend where supported

## Troubleshooting

- **First-run shader compilation:** The first time an ovrtx application runs on a system (or after a driver update), the renderer compiles and caches GPU shaders. This can take several minutes. Subsequent runs reuse the cached shaders and start quickly. If you're running tests or examples for the first time and see a long pause after creating the renderer, this is expected.
- In C, forgetting to call `ovrtx_destroy_renderer()` will leak GPU resources.
- `binary_package_root_path` is only required when static linking ovrtx, or when your install layout breaks apart the ovrtx `bin/` directory.
- With dynamic linking, ovrtx expects runtime directories under `bin/` (`cache/`, `library/`, `libs/`, `mdl/`, `plugins/`, `rendering-data/`, `usd_plugins/`) to be found next to `ovrtx-dynamic.dll` / `libovrtx-dynamic.so`.
- If you call `ovrtx_initialize()` explicitly, pair it with a matching `ovrtx_shutdown()`.
- **Linux headless multi-renderer lifecycle:** On Linux systems with no display, repeatedly creating and destroying renderers may result in a crash with the stack trace pointing into `libEGL.so` when shared graphics resources are torn down between renderers. This can happen if `keep_system_alive` is configured to `false`, or if `ovrtx_initialize()` is not called before the multi-renderer lifecycle. In the implicit-initialization pattern (when `ovrtx_initialize()` is not called), the `keep_system_alive` config setting is effectively ignored. Avoid this by both configuring `keep_system_alive` to `true` (`RendererConfig(keep_system_alive=True)` in Python, `ovrtx_config_entry_keep_system_alive(true)` in C) and calling `ovrtx_initialize()` before creating renderers. If this is not possible, or the crash persists, a further workaround is to set the environment variable `VK_LOADER_DISABLE_DYNAMIC_LIBRARY_UNLOADING=1`.
- Error strings from `ovrtx_get_last_error()` are only valid until the next API call on the same thread.
- Renderer-level `active_cuda_gpus` must be compatible with any per-RenderProduct `deviceIds` allow-list. See `render-product-device-pinning` for the RenderProduct-side USD attribute.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
