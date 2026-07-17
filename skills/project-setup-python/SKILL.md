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
name: project-setup-python
description: >
  Setting up a new Python project that uses ovrtx. Use when user asks to create a new
  Python project, set up ovrtx in Python, create a pyproject.toml, or scaffold a Python
  app.
license: LicenseRef-NvidiaProprietary
version: "0.3.0"
author: NVIDIA ovrtx
tags:
  - ovrtx
  - python
  - setup
tools:
  - Read
  - Grep
  - Shell
  - Write
---

# Project Setup (Python)

## When to Use

Use this skill when the user asks to create a new Python project, set up ovrtx in Python, create a pyproject.toml, or scaffold a Python app.

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

ovrtx and ovstage are distributed as Python packages on PyPI. Use `uv` when you want project and dependency management. This skill scaffolds the current attached-stage workflow with both packages. ovstage remains optional for standalone compatibility code.

## Project Structure

```
my-ovrtx-app/
  pyproject.toml
  main.py
```

## Setup with uv (Recommended)

```bash
mkdir my-ovrtx-app && cd my-ovrtx-app
uv init
uv add ovrtx ovstage
```

This creates a `pyproject.toml` and `uv.lock`. Then add `numpy` (required for array/tensor operations):

```bash
uv add numpy
```

The resulting `pyproject.toml` will look like:

```toml
[project]
name = "my-ovrtx-app"
version = "0.1.0"
requires-python = ">=3.10,<3.14"
dependencies = [
    "ovrtx",
    "ovstage",
    "numpy",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Adding optional dependencies

For image output:

```bash
uv add pillow
```

For GPU compute with Warp:

```bash
uv add warp-lang
```

For visualization with rerun:

```bash
uv add rerun-sdk
```

## Setup with pip

```bash
pip install ovrtx ovstage
```

## Minimal main.py

> **Source:** `examples/python/minimal/main.py` snippet `create-renderer`
>
> Followed by: `examples/python/minimal/main.py` snippet `add-usd`
>
> Followed by: `examples/python/minimal/main.py` snippet `step`
>
> Followed by: `examples/python/minimal/main.py` snippet `read-render-output`

### Run

```bash
uv run main.py --png
# or with pip-installed ovrtx and ovstage:
python main.py --png
```

A successful run writes `_output/render.png`. The output should match the documented minimal reference image.

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `ovrtx` | Core renderer |
| `ovstage` | Runtime scene ownership for attached rendering |
| `pillow` | Image I/O (PNG, JPEG) |
| `numpy` | Array manipulation, DLPack interop |
| `warp-lang` | GPU compute kernels |
| `rerun-sdk` | Real-time visualization |

## Troubleshooting

- If `uv` is missing (`uv: command not found`), install `uv` before using the recommended setup commands, or translate the dependency steps to an equivalent `pip`/virtualenv workflow. PyPI is still the package source.
- ovrtx supports Python 3.10-3.13. If install resolution fails, no matching wheel is found, or imports fail on another Python version, recreate the environment with a supported interpreter (`uv python install 3.13` and `uv python pin 3.13`, or a virtualenv using Python 3.10-3.13). Do not work around unsupported interpreters by editing ovrtx dependency constraints.
- If package installation fails (`uv add ovrtx ovstage` or `pip install ovrtx ovstage` for attached mode), classify the failure before treating it as an ovrtx issue: resolver or `no matching distribution` errors usually indicate an unsupported Python version or platform; connection, TLS, timeout, or index errors usually indicate PyPI/network/proxy access; wheel download or install errors may require checking the target platform tag. PyPI is the recommended package source. GitHub Releases contain Python wheels for explicit release-artifact installs, not normal consumption. Do not edit ovrtx constraints to force unsupported interpreters or platforms. If both PyPI and an explicit release wheel fail, report the exact Python version, OS/architecture, platform tag, command, and full error.
- If `pytest` fails before test assertions because ovrtx cannot load `libovrtx-dynamic.so`, `ovrtx-dynamic.dll`, or required runtime directories, classify it as a package/runtime layout issue rather than a test failure. If pytest reaches runtime validation and fails because the host lacks an RTX GPU, a supported driver, unsandboxed execution, or internet access for remote S3 assets, report the missing prerequisite explicitly. Do not treat import-only, docs-only, or prerequisite-blocked pytest runs as successful runtime validation.
- ovrtx runtime validation requires an NVIDIA RTX-capable GPU and a supported NVIDIA driver. If no RTX GPU is visible, rerun validation outside the sandbox. If no RTX GPU is still visible, stop runtime validation and tell the user they need an RTX GPU.
- Supported NVIDIA driver versions are listed in `docs/driver_requirements.rst`. Use that page as the ovrtx source of truth for runtime validation. If driver detection fails, the driver is inaccessible, or the detected version is older than the listed baseline for the host OS, GPU generation, and GPU type, rerun validation outside the sandbox. If the driver is still missing or incompatible, stop runtime validation and tell the user they need a supported NVIDIA driver.
- Run ovrtx-related runtime code outside sandboxed environments.
- Examples that load remote S3 assets require internet access.
- The first step from a newly built application will block for 1-2 minutes while shaders are compiled and cached. Wait at least 5 minutes before treating this as a failure.
- USD files can be loaded from local paths, `file://` URIs, or `https://` URLs.

## Standalone Compatibility (ovrtx 0.4)

The scaffold above follows the current attached-stage workflow. ovstage can be
omitted when maintaining standalone compatibility code, but the renderer-owned
scene APIs used by that mode are deprecated as scene ownership transitions
entirely to ovstage in a future release:

```toml
dependencies = [
    "ovrtx>=0.4",
    "ovstage>=0.1",
]
```

See `docs/core/ovstage_integration.rst` for the attached-mode overview.

## References

- Use the `> **Source:**` directives in this skill to locate tested snippets before reusing API patterns.
- Keep related skills, docs, and snippets synchronized when changing the workflow.
