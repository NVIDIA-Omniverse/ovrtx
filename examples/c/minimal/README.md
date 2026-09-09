# Minimal Example

This example builds the same renderer flow with both supported link models:
`minimal` uses the static loaders (model #1), while `minimal-dynamic` uses the
shared loaders (model #2). Both render a single RGB frame and write `out.png`.

The example loads a scene from S3 and writes the resulting image to `out.png`. A successful output should match the reference image below.

Runtime validation requires an NVIDIA RTX-capable GPU, a supported NVIDIA driver, internet access to download the remote S3 scene asset, and unsandboxed execution.

The first step from a newly built application will block for 1-2 minutes while shaders are compiled and cached.

> _“Create the smallest useful C/C++ example that initializes ovrtx, loads a USD scene asynchronously, waits for it, renders one camera frame, fetches and CPU-maps the color output, writes it to an image file, and releases all ovrtx resources explicitly.”_

![output](../../../img/example-minimal.jpg)


## Linux

### Prerequisites

- `sudo apt-get install build-essential cmake`
- NVIDIA RTX-capable GPU
- Supported NVIDIA driver
- Internet access to download the remote S3 scene asset
- Unsandboxed runtime execution

The ovrtx and ovstage libraries are downloaded automatically at configure time, each as its own independent package. If either is already installed and available via `CMAKE_PREFIX_PATH`, the local installation is used instead.


### Building

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

### Running

```bash
./build/static/minimal
./build/shared/minimal-dynamic
```

## Windows

### Prerequisites

- [Visual Studio 2017+](https://visualstudio.microsoft.com/downloads/)
- NVIDIA RTX-capable GPU
- Supported NVIDIA driver
- Internet access to download the remote S3 scene asset
- Unsandboxed runtime execution

The ovrtx and ovstage libraries are downloaded automatically at configure time, each as its own independent package. If either is already installed and available via `CMAKE_PREFIX_PATH`, the local installation is used instead.

### Building

```pwsh
cmake -B build
cmake --build build --config Release
```

### Running

```pwsh
.\build\static\Release\minimal.exe
.\build\shared\Release\minimal-dynamic.exe
```

# Licensing

This example contains stb_image_write.h, © Sean Barrett, released under Public Domain.
