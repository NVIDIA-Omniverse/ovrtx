

# NVIDIA ovrtx

[![Documentation](https://img.shields.io/badge/docs-ovrtx-blue)](https://nvidia-omniverse.github.io/ovrtx)
[![SDK License](https://img.shields.io/badge/SDK%20license-NVIDIA%20Proprietary-red)](LICENSE)
[![Skills License](https://img.shields.io/badge/skills%20license-CC--BY--4.0%20AND%20Apache--2.0-blue)](skills/LICENSE)
[![GitHub last commit](https://img.shields.io/github/last-commit/NVIDIA-Omniverse/ovrtx)](https://github.com/NVIDIA-Omniverse/ovrtx)
[![Docs build](https://github.com/NVIDIA-Omniverse/ovrtx/actions/workflows/docs.yml/badge.svg)](https://github.com/NVIDIA-Omniverse/ovrtx/actions/workflows/docs.yml)

**ovrtx** is a C and Python library for embedding Omniverse RTX sensor simulation and visualization directly into applications. 

**ovrtx** is best suited for developers looking to build applications, tools or workflows that need real-time, physically accurate camera, lidar, radar, and other sensor simulation for [Physical AI](https://www.nvidia.com/en-us/glossary/generative-physical-ai/), targeting robotics learning, synthetic data generation, and industrial and design workflows.

**ovrtx** integrates with the NVIDIA Omniverse [**ovstage**](https://github.com/NVIDIA-Omniverse/ovstage) library. **ovstage** supports loading of USD data to a runtime representation, manages the runtime scene data, ordinal-keyed simulation steps, and change detection. See [Packaging and Dependencies](#packaging-and-dependencies) for how the two libraries relate.

> [!NOTE]
> ovrtx is currently **pre-release** software.

To get started with ovrtx follow the instructions below for the included Python and C/C++ examples.
* [Get started in Python](#getting-started-in-python)
* [Get started in C](#getting-started-in-cc)

Sources live under [`examples/`](examples/) and are the source of truth for the code snippets referenced by the ovrtx skills — see the [examples index](examples/README.md).

![warehouse](img/warehouse.jpg)

## Custom data providers

The [provider helper guide](helpers/ovrtx/providers/README.md) describes optional, header-only C++
utilities for building UDIM manifests and reading stored USDZ package members.
They ship under `helpers/`, separately from the public C interface in `include/`.

## High-level Feature Set

* Physically accurate simulation of cameras, lidar, radar, and other sensors.
* Scalable simulation performance from reinforcement learning in-the-loop with tens of thousands of frames per second, through real-time, photorealistic, interactive viewport and navigation, to offline predictive rendering.
* Support for loading [USD](https://aousd.org/) scene description via [**ovstage**](https://github.com/NVIDIA-Omniverse/ovstage). Compatibility with OpenUSD allows interchange with a vast ecosystem of content creation, CAD and simulation tools.
* Easy integration with Python simulation and AI ecosystem.

## Packaging and Dependencies

ovrtx is distributed as a C package (.zip file) available in the Releases page in this repo, and as Python wheels available via pypi.org.
These packages include a number of pre-packaged dependencies.

The C package contains `ovrtx-build-info.json` at its root, and the wheel contains the same file under its `ovrtx/`
package directory. This schema-versioned file is passive diagnostic metadata for offline inspection: it records the
package build's version, build number, Git branch/hash, and build location. Deployment does not use it as an executable
identity check. `ovrtx_get_build_info()` and, after creating a `Renderer`, `ovrtx.get_build_info()` report the identity
of the OVRTX loader library that exports the API. The C query is safe before `ovrtx_initialize()`; the Python query
intentionally stays inside the `Renderer`-managed native-library lifecycle. Normal packages build the loader and runtime
together. If an application deliberately selects a different runtime with `binary_package_root_path`, runtime startup
logs and crash metadata report that runtime's identity.

In addition to these pre-packaged dependencies, two other dependencies are noted here:
1. ovrtx uses the NVIDIA [ovstage](https://github.com/NVIDIA-Omniverse/ovstage) library, introduced in ovrtx 0.4, to own the runtime scene.
    * ovstage is optional only for standalone compatibility mode. The renderer-owned scene APIs that mode uses have been deprecated since ovrtx 0.4, and scene ownership will transition entirely to ovstage in a future release.
    * To ease the migration to ovstage, you can take advantage of the agent-friendly migration skills for ovrtx 0.3 to 0.4 [for C](skills/update-0_3-0_4-c/SKILL.md) and [for Python](skills/update-0_3-0_4-python/SKILL.md), and for [ovrtx 0.4 to 0.5](skills/update-0-4-to-0-5/SKILL.md).
2. on Windows, ovrtx depends on [Microsoft's VC runtime redistributable libraries](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170), with a minimum version of 14.38 (as included in Visual Studio 2022 17.8). 
    * These libraries can be installed by an end user (using the linked Microsoft resources) or can be included by an application. 
    * The use of this version of the MSVC runtime libraries makes our binaries compatible with the vcruntime140.dll pre-packaged in Python distributions for Windows as old as Python 3.11. Older Python versions include older vcruntime140.dll, and are therefore not guaranteed to work.

## System requirements

- **C/C++**:
    - The ovrtx library has a C11-compatible interface. It can be loaded dynamically or by statically linking to the `ovrtx-static` loader library, which requires linking to the C++ stdlib.
    - The example code requires a C++17 compiler and CMake 3.16+ (`find_package(ovrtx)` fails on older versions); building the whole example set through the top-level `examples/c/CMakeLists.txt` needs 3.18. The examples use cmake to fetch the prebuilt ovrtx and ovstage packages from their GitHub.com release pages.
- **Python**:
    - Python 3.10–3.14 versions are supported. On Windows, use Python 3.11 or newer (see the VC runtime note under [Packaging and Dependencies](#packaging-and-dependencies)).
    - The examples use [uv](https://docs.astral.sh/uv/) to resolve the `ovrtx` wheel.
- CUDA-capable environment for GPU-resident data paths; CPU payload paths are also part of the API surface.
- DLPack-compatible tensor data for CPU/GPU interchange.

## Network hosts

Installing and running the examples reaches the following hosts. If you are
behind a restrictive firewall or proxy, allow outbound HTTPS to all of them:

- `pypi.org` and `files.pythonhosted.org` — the public PyPI index and CDN that
  `uv add ovrtx ovstage` / `pip install ovrtx ovstage` reach to resolve project
  metadata and download the wheels.
- `pypi.nvidia.com` — the `ovrtx` PyPI entry is an sdist stub that fetches the
  platform binary from this host at install time. `ovstage` is fully published to
  PyPI (binary wheels on `files.pythonhosted.org`) and does not reach this host.
- `github.com` and the GitHub release CDN (`objects.githubusercontent.com`) — used
  by `cmake` `FetchContent` in the C examples to download the ovrtx and ovstage
  release archives, and to clone this repository.
- `omniverse-content-production.s3.us-west-2.amazonaws.com` — hosts the sample USD
  scenes loaded at runtime by the Python examples (for example, the robot scene
  used by `examples/python/minimal/main.py`).

The ovrtx library itself also sends one anonymous plain-HTTP report to
`6697362192350625.events.telemetry.data.nvidia.com` per process unless you opt out; see [Data Collection](#data-collection). It does not need to reach that host to work.

## Data Collection

OVRTX collects anonymous initialization data by default to help improve OVRTX. Collection is optional and can be disabled without affecting OVRTX functionality. To opt out, set the environment variable `NVIDIA_OMNIVERSE_PRODUCT_TELEMETRY_DISABLED=1` before launching your application, or call `ovrtx.library_telemetry_opt_out()` (Python) or `ovrtx_library_telemetry_opt_out()` (C) before OVRTX initializes (before `ovrtx_initialize()` or your first renderer is created).

More information is available at [Data Collection & Use](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/TELEMETRY.md).

## Getting Started in Python

[ovrtx](https://pypi.org/project/ovrtx/) and [ovstage](https://pypi.org/project/ovstage/) Python wheels are distributed on [PyPI](https://pypi.org/). We recommend using [uv](https://docs.astral.sh/uv/getting-started/installation/) to install both packages:

```bash
uv add ovrtx ovstage
```

`pip` also works:

```bash
pip install ovrtx ovstage
```

ovstage is optional only when maintaining standalone compatibility code, which uses the deprecated renderer-owned scene APIs. See [Packaging and Dependencies](#packaging-and-dependencies).

The examples in this repository contain pyproject.toml files tested with uv. Python 3.10–3.13 are supported across the examples; projects that allow Python 3.14 declare it in their pyproject.toml.

If installation fails, first verify that your Python version matches the project's pyproject.toml and that your environment can reach PyPI. If you need a specific release artifact, GitHub Releases also contain Python wheels that can be installed explicitly.

To get started with the repository examples, first clone this repository and run the minimal example with uv:

```bash
git clone https://github.com/NVIDIA-Omniverse/ovrtx.git
cd ovrtx/examples/python/minimal
uv run main.py --png
```

See the [Python minimal example documentation](examples/python/minimal/README.md) for more information on environment setup and prerequisites.

The minimal example shows how to create the renderer, load an OpenUSD scene and render a single image, copying the results back to the CPU for display.

![minimal example](img/example-minimal.jpg)


The first step from a newly built application will block for up to 5 minutes while shaders are compiled and cached.

## Getting Started in C/C++

The C/C++ examples require CMake 3.16 or newer and a development environment. On Windows this is provided by [Visual Studio 2022 17.8 or newer](https://visualstudio.microsoft.com/), which is the oldest release shipping the VC runtime 14.38 that ovrtx requires (see the dependency note above).


On Linux (Ubuntu):

```bash
sudo apt-get install build-essential cmake
```

To get started, first clone this repository:

```bash
git clone https://github.com/NVIDIA-Omniverse/ovrtx.git
cd ovrtx/examples/c/minimal
```

Then configure, build, and run the minimal example for your platform.

On Windows:
```
cmake -B build
cmake --build build --config Release
.\build\static\Release\minimal.exe
```

On Linux:
```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
./build/static/minimal
```

See the [C minimal example documentation](examples/c/minimal/README.md) for more information on environment setup and prerequisites.

The minimal example shows how to create the renderer, load an OpenUSD scene and render a single image, copying the results back to the CPU for writing out as a PNG.

![minimal example](img/example-minimal.jpg)

The resulting image will be written to `./out.png` and can be inspected with any image viewer.

The first step from a newly built application will block for up to 5 minutes while shaders are compiled and cached.

## Examples

Further examples using both the C and Python APIs are available in the [examples](examples/README.md) directory. See the individual examples for building and usage instructions.

## Releases

The Releases page of this repository contains binary builds for the official releases of the ovrtx C library and also includes corresponding Python wheels. PyPI is the recommended consumption path for Python users.

These binaries are provided for the supported platforms:
 * Windows x86_64
 * Linux x86_64
 * Linux aarch64

The libraries require a compatible NVIDIA RTX-capable GPU with a compatible NVIDIA driver on the system to be able to initialize correctly.
Supported hardware and driver versions are listed in [Hardware & Driver Requirements](https://nvidia-omniverse.github.io/ovrtx/driver_requirements.html).


## Testing

Tests live under `tests/docs/` in three independent suites: Python, C, and USD validation.

> **Stage ownership in tests:** Stage-owning Python documentation tests request an attached ovstage fixture, with focused compatibility coverage for deprecated renderer wrappers. C documentation tests remain on deprecated standalone renderer stage APIs. USD validation tests do not exercise either stage-ownership model.

> **Windows:** the Python and USD tests read UTF-8 files. Enable Python's UTF-8 mode before running them, for example `$env:PYTHONUTF8 = "1"` in PowerShell.

### Python tests (GPU required)

```bash
cd tests/docs/python

# Run the full suite
uv run pytest -v

# Run a single test
uv run pytest test_base.py::test_base -v
uv run pytest test_base.py::test_bind_material -v
```

### C tests (GPU required)

See the [C documentation test build notes](tests/docs/c/README.md) for the
commands, validation scope, and SDK selection instructions.

```bash
cd tests/docs/c
cmake -B build
cmake --build build --config Release

# Run the full suite
cd build && ctest --output-on-failure

# Run a single test
ctest -R BaseTest.RenderLdrColor --output-on-failure

# Or use the gtest binary directly
./ovrtx_docs_tests --gtest_filter=BaseTest.BindMaterial
```

### USD validation tests (no GPU required)

These tests use the schema descriptors from an extracted OVRTX SDK. Set
`OVRTX_DOCS_USD_PLUGIN_ROOT` to its `bin/usd_plugins` directory before running
pytest; the source checkout does not contain those descriptors.

Linux:

```bash
export OVRTX_DOCS_USD_PLUGIN_ROOT="/absolute/path/to/ovrtx-sdk/bin/usd_plugins"
cd tests/docs/usd
uv run pytest -v
```

Windows (PowerShell):

```powershell
$env:OVRTX_DOCS_USD_PLUGIN_ROOT = "C:\path\to\ovrtx-sdk\bin\usd_plugins"
cd tests/docs/usd
uv run pytest -v
```

Rendered images are written to `_output/` under the respective suite directory.

## Documentation

Documentation is published at https://nvidia-omniverse.github.io/ovrtx

* [Python getting started](https://nvidia-omniverse.github.io/ovrtx/python_api/getting_started.html)
* [C getting started](https://nvidia-omniverse.github.io/ovrtx/c_api/getting_started.html)
* [Examples](examples/README.md)

### Building the Documentation

The documentation build requires [uv](https://docs.astral.sh/uv/) and [Doxygen](https://www.doxygen.nl/). From the `docs` directory, run `make html` on Linux or `make.bat html` on Windows. See [docs/README.md](docs/README.md) for prerequisites, platform-specific notes, and how to preview the output locally.

---

## Contributing

At this time this project is not open to external contributions.

## Authors and acknowledgment

NVIDIA Corporation

## License and security

Except for the skills directory, the software and materials are governed by the [NVIDIA Software License Agreement](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-software-license-agreement/) and the [Product Specific Terms for NVIDIA AI Products](https://www.nvidia.com/en-us/agreements/enterprise-software/product-specific-terms-for-ai-products/).

The [skills directory](skills/) is licensed under CC-BY-4.0 AND Apache-2.0; see [skills/LICENSE](skills/LICENSE) for the full terms.

Third-party material included in this repository, such as the DLPack header and example data, is listed with its license terms in [THIRD-PARTY-NOTICES.txt](THIRD-PARTY-NOTICES.txt).

This project will download and install additional third-party open source software projects. Review the license terms of these open source projects before use.

To report a security issue, see [`SECURITY.md`](SECURITY.md). **Do not report security vulnerabilities through GitHub/GitLab.**

## Support

Report documentation issues, installation problems, and runtime issues through the NVIDIA Omniverse developer forum.
https://forums.developer.nvidia.com/c/omniverse/300

## Roadmap

A public roadmap will be shared as ovrtx approaches general availability.
For recent additions and changes, see the [release notes](https://github.com/NVIDIA-Omniverse/ovrtx/releases).

## AI Coding Agents

The [skills](skills) directory contains a series of Skills to help AI coding agents to understand how to use the API (and they're useful for humans too). Copy this directory to your project and point your agent at it.

Agents should use the [Python minimal example](examples/python/minimal/README.md) as the first runtime validation unless C is specifically requested. Follow that example's README for validation steps, and use [Driver requirements](docs/driver_requirements.rst) to check supported NVIDIA driver versions.

---

*Copyright (c) 2026 NVIDIA Corporation.*
