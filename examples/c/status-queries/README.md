# Status Queries Example

This example is based on the minimal C example and adds operation status
queries for the asynchronous operations in that flow:

1. Create a renderer
2. Load a USD layer from a remote S3 scene URL with `ovstage_population_open_usd_from_file()`
3. Run one shader-cache warm-up step and print shader compilation progress
4. Step the attached renderer with `ovrtx_step_with_stage()` and query status while waiting
5. Map the rendered output and write it to `out.png`

Renderer logs are written to `_output/status-queries-ovrtx.log`.

> _“Create a C/C++ rendering example that demonstrates operation status queries, including logging, asynchronous scene loading, progress and counter polling while waiting, shader warmup feedback, final image output, and both API and asynchronous operation error checks.”_

![output](../../../img/example-minimal.jpg)

## Linux

### Prerequisites

- `sudo apt-get install build-essential cmake`
- NVIDIA RTX-capable GPU
- Supported NVIDIA driver
- Internet access to download the remote S3 scene asset
- Unsandboxed runtime execution

The ovrtx and ovstage libraries are downloaded automatically at configure time,
each as its own independent package. If either is already installed and available
via `CMAKE_PREFIX_PATH`, the local installation is used instead.


### Building

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

### Running

```bash
./build/status-queries
```

## Windows

### Prerequisites

- [Visual Studio 2017+](https://visualstudio.microsoft.com/downloads/)
- NVIDIA RTX-capable GPU
- Supported NVIDIA driver
- Internet access to download the remote S3 scene asset
- Unsandboxed runtime execution

The ovrtx and ovstage libraries are downloaded automatically at configure time,
each as its own independent package. If either is already installed and available
via `CMAKE_PREFIX_PATH`, the local installation is used instead.

### Building

```pwsh
cmake -B build
cmake --build build --config Release
```

### Running

```pwsh
.\build\Release\status-queries.exe
```

# Licensing

This example uses `stb_image_write.h` from the minimal example, (c) Sean Barrett,
released under Public Domain.
