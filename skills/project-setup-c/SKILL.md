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
name: project-setup-c
description: >
  Setting up a new CMake C/C++ project that uses ovrtx. Use when user asks to create a
  new C project, set up CMake with ovrtx, scaffold a C++ app, or configure build
  dependencies.
license: LicenseRef-NvidiaProprietary
author: NVIDIA ovrtx
tags:
  - ovrtx
  - c
  - setup
tools:
  - Read
  - Grep
  - Shell
  - Write
---

# Project Setup (C)

## When to Use

Use this skill when the user asks to create a new C project, set up CMake with ovrtx, scaffold a C++ app, or configure build dependencies.

## Inputs

Resolve inputs in this order: existing repository files and referenced snippets, explicit user request, then broader agent context.

- Project language, package manager, build system, and target platform from the user request.
- Whether the project should use packaged ovrtx or the local dev-mode build.
- Repository source snippets and example projects referenced below. Treat these snippets as the API source of truth.

## Prerequisites

- Use an ovrtx checkout that contains the referenced examples and docs tests.
- Confirm Python, CMake, compiler, and package-index requirements before giving setup commands.
- Avoid modifying tracked dependency files unless the user explicitly asks for project scaffolding changes.

## Instructions

1. Identify the requested project type, platform, package source, and expected run command.
2. Read the minimal example and setup snippets before writing scaffolding.
3. Use the repository's existing Python or CMake conventions instead of inventing a new layout.
4. Include renderer creation and first-frame validation only after the project dependency setup is complete.
5. When changing code, run the narrow example setup or docs test whenever practical.

## Output Format

- For explanations, cite the relevant API names, source snippets, and caveats.
- For code changes, summarize the files changed, snippets affected, and validation run.

## Scripts

This skill has no scripts.

## Limitations

- The referenced snippets remain the source of truth; update or add tested snippets before documenting new API usage.

## Overview

ovrtx provides a C API with a CMake config for easy integration. The recommended approach uses CMake FetchContent to download the ovrtx binary package from GitHub Releases. A convenience macro in `ovrtx.cmake` handles fetching, finding, and runtime setup.

## Project Structure

```
my-ovrtx-app/
  CMakeLists.txt
  cmake/
    ovrtx.cmake       # Copy from examples/c/cmake/ovrtx.cmake
  main.cpp
```

## CMakeLists.txt

> **Source:** `examples/c/minimal/CMakeLists.txt` snippet `project-setup`
>
> **Source (continued):** `examples/c/minimal/CMakeLists.txt` snippet `linking-models`
>
> The canonical example builds both loader models with ovstage attached. For an
> ovrtx-only application, omit the ovstage fetch, link target, and setup call.

## ovrtx.cmake

Copy `examples/c/cmake/ovrtx.cmake` into your project's `cmake/` directory. The key macro it provides:

- `ovrtx_fetch()` -- downloads the ovrtx package via FetchContent and makes both `ovrtx::ovrtx` (shared loader) and `ovrtx::ovrtx_static` (static loader) available.
- `ovrtx_setup_runtime(TARGET)` -- auto-selects the runtime layout from how the target links ovrtx. For `ovrtx::ovrtx_static` (model #1) it stages a single side-by-side `ovrtx/` link pointing at the package `bin/`. For `ovrtx::ovrtx` (model #2) it configures rpath (Linux) or copies DLLs and creates runtime-directory junctions (Windows).

Update the `FetchContent_Declare` URL inside `ovrtx.cmake` to point to the appropriate GitHub Releases package for your platform.

## Minimal main.cpp

> **Source:** `examples/c/minimal/main.cpp` snippet `check-error-helper`
>
> **Source (continued):** `examples/c/minimal/main.cpp` snippet `create-renderer`
>
> **Source (continued):** `examples/c/minimal/main.cpp` snippet `load-usd-and-wait`
>
> See the full minimal example for the complete flow including step, fetch, map, and cleanup.

## Build and Run

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
./build/my-ovrtx-app
```

## Runtime Packaging

The ovrtx binary distribution includes runtime dependencies under `bin/`:

```
bin/
  libovrtx-dynamic.so / ovrtx-dynamic.dll
  cache/
  library/
  libs/
  mdl/
  plugins/
  rendering-data/
  usd_plugins/
```

**Static loader (model #1).** Link
`ovrtx::ovrtx_static` and pass the package root to `ovrtx_create_renderer()` via
`ovrtx_config_entry_binary_package_root_path()`. Build the path from
`OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx"` so the loader resolves it against the
running executable's directory at runtime. `ovrtx_setup_runtime()` stages the
matching side-by-side `ovrtx/` link pointing at the package `bin/`, keeping the
exe directory self-contained without baking an absolute path into the binary:

> **Source:** `examples/c/minimal/main.cpp` snippet `create-renderer`

**Shared loader (model #2).** Link `ovrtx::ovrtx`; the operating system loads
only the forwarding loader. The loader opens the ovrtx runtime on the first
initialization call. ovrtx expects the `bin/`
runtime directories (`cache/`, `library/`, `libs/`, `mdl/`, `plugins/`,
`rendering-data/`, `usd_plugins/`) next to `ovrtx-dynamic.dll` /
`libovrtx-dynamic.so`, and `ovrtx_setup_runtime()` configures rpath (Linux) or
copies DLLs + creates junctions (Windows). In this mode `binary_package_root_path`
is only needed when your install/deploy layout breaks apart the default `bin/`
structure. The config-entry pattern is identical either way:

> **Source:** `tests/docs/c/test_support_api.cpp` snippet `doc-version-and-config-c`

## Headers

| Header | Purpose |
|--------|---------|
| `<ovrtx/ovrtx.h>` | Main API: create/destroy renderer, add USD, step, fetch results, map output |
| `<ovrtx/ovrtx_types.h>` | All type definitions (handles, structs, enums) |
| `<ovrtx/ovrtx_config.h>` | Config entry builders (`ovrtx_config_entry_*` helpers) |

## Troubleshooting

- ovrtx runtime validation requires an NVIDIA RTX-capable GPU and a supported NVIDIA driver. If no RTX GPU is visible, rerun validation outside the sandbox. If no RTX GPU is still visible, stop runtime validation and tell the user they need an RTX GPU.
- Supported NVIDIA driver versions are listed in `docs/driver_requirements.rst`. Use that page as the ovrtx source of truth for runtime validation. If driver detection fails, the driver is inaccessible, or the detected version is older than the listed baseline for the host OS, GPU generation, and GPU type, rerun validation outside the sandbox. If the driver is still missing or incompatible, stop runtime validation and tell the user they need a supported NVIDIA driver.
- `binary_package_root_path` is only needed for static linking or custom layouts that split the default `bin/` structure.
- `ovrtx_setup_runtime()` must be called for each executable target that uses ovrtx.
- On Linux, the build rpath is set automatically. For installed/packaged binaries, ensure the install rpath points to the ovrtx `bin/` directory.
- The first step from a newly built application will block for 1-2 minutes while shaders are compiled and cached. Wait at least 5 minutes before treating this as a failure.
- CMake >= 3.16 is required: `ovrtxConfig.cmake` calls `cmake_minimum_required(VERSION 3.16)`, so on CMake 3.15 or older `find_package(ovrtx)` fails with "CMake 3.16 or higher is required" from inside `ovrtx_fetch()`. If `cmake` is missing (`cmake: command not found`), is older than 3.16, or configure/build fails because no generator, compiler, or C++ toolchain is available, install the platform toolchain before treating the failure as ovrtx-specific. On Windows, install Visual Studio 2022 17.8 or newer with C++ tools and CMake — ovrtx binaries need the VC runtime 14.38 or newer, which older Visual Studio releases do not ship. On Ubuntu/Linux, install `build-essential cmake`. Ninja is optional; use the default CMake generator unless the project or platform requires another generator.

## In Attached Mode (ovrtx 0.4+)

Attached mode pairs independent ovrtx and ovstage packages. Use the same model
for both unless your deployment has a specific reason to mix them:

- **Model #1 — static loaders.** Link `ovrtx::ovrtx_static` and
  `ovstage::ovstage_static`. Pass each package root in its initialization config.
  Each loader opens its runtime on the first initialization call.
- **Model #2 — shared loaders.** Link `ovrtx::ovrtx` and `ovstage::ovstage`.
  The operating system resolves the two small loader libraries; neither imports
  OpenUSD. Each loader opens its runtime on the first initialization call.

For both models, call `ovrtx_register_schema_paths()` before the first
`ovstage_initialize()` / `ovstage_create_instance()` if ovstage may initialize
first. The call only publishes discovery paths; it does not load the renderer or
OpenUSD. The minimal example demonstrates both link models and this ordering:

ovrtx and ovstage must come from the same release train (matched `usd_ms` ABI);
a single USD runtime in attach mode still needs on-hardware confirmation.

> **Source:** `examples/c/minimal/CMakeLists.txt` snippet `linking-models`
>
> **Source (continued):** `examples/c/minimal/main.cpp` snippet `create-renderer`

See `docs/core/ovstage_integration.rst` for the attached-mode overview and
`examples/c/minimal/` for a complete attach-mode project.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
