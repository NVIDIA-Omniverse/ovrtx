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
version: "0.3.0"
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

```cmake
cmake_minimum_required(VERSION 3.16)
project(my-ovrtx-app)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Fetch ovrtx library
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/cmake")
include(ovrtx)
ovrtx_fetch()

add_executable(my-ovrtx-app main.cpp)
# Static loader (model #1): all shipped C examples link ovrtx::ovrtx_static and
# pass the package root at renderer creation (see the minimal snippet below).
target_link_libraries(my-ovrtx-app PRIVATE ovrtx::ovrtx_static)

if(MSVC)
    # The package ships a release-only static loader (compiled /MD); force the
    # release CRT so a Debug config links cleanly.
    set_target_properties(my-ovrtx-app PROPERTIES MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")
endif()

# Stage the side-by-side `ovrtx/` link the loader resolves at runtime.
ovrtx_setup_runtime(my-ovrtx-app)
```

## ovrtx.cmake

Copy `examples/c/cmake/ovrtx.cmake` into your project's `cmake/` directory. The key macro it provides:

- `ovrtx_fetch()` -- downloads the ovrtx package via FetchContent and makes both `ovrtx::ovrtx` (dynamic) and `ovrtx::ovrtx_static` (static loader) available.
- `ovrtx_setup_runtime(TARGET)` -- auto-selects the runtime layout from how the target links ovrtx. For `ovrtx::ovrtx_static` (model #1, used by all shipped examples) it stages a single side-by-side `ovrtx/` link (symlink on Linux, junction on Windows) pointing at the package `bin/`. For the dynamic `ovrtx::ovrtx` (model #2) it configures rpath (Linux) or copies DLLs and creates per-runtime-dir junctions (Windows).

Update the `FetchContent_Declare` URL inside `ovrtx.cmake` to point to the appropriate GitHub Releases package for your platform.

## Minimal main.cpp

> **Source:** `examples/c/minimal/main.cpp` snippet `check-error-helper`
>
> Followed by: `examples/c/minimal/main.cpp` snippet `create-renderer`
>
> Followed by: `examples/c/minimal/main.cpp` snippet `load-usd-and-wait`
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

**Static loader (model #1, used by all shipped C examples and doc tests).** Link
`ovrtx::ovrtx_static` and pass the package root to `ovrtx_create_renderer()` via
`ovrtx_config_entry_binary_package_root_path()`. Build the path from
`OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx"` so the loader resolves it against the
running executable's directory at runtime. `ovrtx_setup_runtime()` stages the
matching side-by-side `ovrtx/` link pointing at the package `bin/`, keeping the
exe directory self-contained without baking an absolute path into the binary:

> **Source:** `examples/c/minimal/main.cpp` snippet `create-renderer`

**Dynamic linking (model #2).** Link `ovrtx::ovrtx`; ovrtx then expects the `bin/`
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

The standalone section above already uses the static ovrtx loader (model #1) with
a renderer-owned scene. Attached mode (used by `examples/c/minimal/`) keeps that
same ovrtx loader model but additionally pairs ovrtx with an independent ovstage
package that owns the scene. The two loader concerns are independent: every shipped
example is on model #1; only the ovstage examples add the ovstage runtime below.

- **ovrtx — static loader + binary package root (model #1).** Link
  `ovrtx::ovrtx_static` and pass the package's binary root to `ovrtx_create_renderer`
  via `ovrtx_config_entry_binary_package_root_path()`. The statically linked loader
  then `LoadLibrary`s `ovrtx-dynamic` from the package in place and resolves all of
  ovrtx's runtime resources there. To keep the exe directory self-contained without
  baking an absolute path into the binary, `ovrtx_setup_runtime()` creates a single
  link `ovrtx/` next to the exe (a junction on Windows, a symlink on Linux) pointing at
  the package `bin/`, and the app resolves the root at runtime as
  `<dir of exe>/ovrtx` (see `main.cpp`'s `executable_dir()`).
- **ovstage — static loader + binary package root.** Link `ovstage::ovstage_static` and
  `ovstage_setup_runtime()` exposes the package as a single link `ovstage/` next to the exe
  (a junction on Windows, a symlink on Linux) pointing at the package `bin/`, which the app
  hands to `ovstage_initialize()` as the ovstage binary package root. The static loader
  loads `ovstage.dll` from that link on the first ovstage call and self-locates its own
  `plugins/` and `ovstage_usd_schemas/` beneath it, so there is no DLL copy, no
  `/DELAYLOAD`, and no separate schemas or plugins junction. Every C example here that uses
  ovstage links this static loader.

`ovstage.dll` is loaded lazily on the first `ovstage_*` call, so its static `usd_ms`/`tbb`
imports bind by base name to the single instance ovrtx has already loaded from its package.
ovrtx and ovstage must come from the same release train (matched `usd_ms` ABI); a single
Fabric/USD runtime in attach mode still needs on-hardware confirmation.

The ovstage package also exports a dynamic `ovstage::ovstage` target, and
`ovstage_setup_runtime()` still supports it, but the ovrtx + ovstage setup documented here
uses the static loader.

```cmake
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../cmake")
include(ovrtx)
include(ovstage)
ovrtx_fetch()
ovstage_fetch()

add_executable(my-ovrtx-app main.cpp)
# Static loaders for both packages, as in every ovstage-using C example here.
target_link_libraries(my-ovrtx-app PRIVATE ovrtx::ovrtx_static ovstage::ovstage_static)

ovrtx_setup_runtime(my-ovrtx-app)   # links ovrtx/ beside the exe (main.cpp resolves it)
ovstage_setup_runtime(my-ovrtx-app) # links ovstage/ beside the exe
```

See `docs/core/ovstage_integration.rst` for the attached-mode overview and
`examples/c/minimal/` for a complete attach-mode project.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
