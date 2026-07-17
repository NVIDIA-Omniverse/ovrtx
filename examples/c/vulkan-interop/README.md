# vulkan-interop

Demonstrates how to integrate ovrtx with ovstage and Vulkan by sharing renders on the GPU.

The USD scene is populated through ovstage and rendered with an attached ovrtx renderer. ovrtx outputs are mapped to CUDA arrays every frame, which are then copied to CUDA-exported VkImage memory. The resulting textures are then sampled on a fullscreen quad to display the render in real time in a GLFW window. Memory access between CUDA and Vulkan is synchronized using timeline semaphores.

The sample also demonstrates ovrtx viewport picking and selection: left-click picks the prim under the cursor, left-drag performs marquee selection with a Vulkan overlay rectangle, picked prim paths are printed to stderr, and selected prims are highlighted with styled ovrtx selection outlines and translucent fill. Camera attribute updates are authored back to ovstage, then rendered through `ovrtx_step_with_stage()`.

Any scene used with picking must restrict the picked RenderProduct to CUDA-visible GPU 0 with `uint[] deviceIds = [0]`.

> _“Create a C++ interactive viewer that renders ovrtx camera output directly into a Vulkan presentation path through CUDA interop, with GPU selection, GPU image mapping, exported-image copies, explicit synchronization, double buffering, orbit camera controls, finite-frame capture, and click or marquee picking with selection outlines.”_

![example-vulkan-interop](../../../img/example-vulkan-interop.gif)

## Linux

### Prerequisites

- `sudo apt install build-essential cmake`
- [Vulkan SDK 1.3.250+](https://vulkan.lunarg.com/sdk/home)
- [CUDA Toolkit 12.0+](https://developer.nvidia.com/cuda-downloads)
- NVIDIA RTX-capable GPU
- Supported NVIDIA driver
- Internet access to download the default remote S3 scene asset
- Unsandboxed runtime execution

`ovstage` must be installed and available via `CMAKE_PREFIX_PATH`. If ovrtx or glfw3 are already installed and available via `CMAKE_PREFIX_PATH`, the local installations are used. Otherwise they are downloaded automatically at configure time. Other dependencies (GLM, volk, unordered_dense) are always downloaded via FetchContent.


### Building

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

### Running

```bash
./build/ovrtx-interop
```

## Windows

### Prerequisites

- [Visual Studio 2017+](https://visualstudio.microsoft.com/downloads/)
- [Vulkan SDK 1.3.250+](https://vulkan.lunarg.com/sdk/home)
- [CUDA Toolkit 12.0+](https://developer.nvidia.com/cuda-downloads)
- NVIDIA RTX-capable GPU
- Supported NVIDIA driver
- Internet access to download the default remote S3 scene asset
- Unsandboxed runtime execution

`ovstage` must be installed and available via `CMAKE_PREFIX_PATH`. If ovrtx or glfw3 are already installed and available via `CMAKE_PREFIX_PATH`, the local installations are used. Otherwise they are downloaded automatically at configure time. Other dependencies (GLM, volk, unordered_dense) are always downloaded via FetchContent.

### Building

```pwsh
cmake -B build
cmake --build build --config Release
```

### Running

```pwsh
.\build\Release\ovrtx-interop.exe
```

The example is configured to load the robot scene from Omniverse. Running the default configuration requires internet access to download this remote S3 scene asset:

| Setting | Value |
|---------|-------|
| USD Scene | `https://omniverse-content-production.s3.us-west-2.amazonaws.com/Samples/Robot-OVRTX/robot-ovrtx.usda` |
| Render Product | `/Render/Camera` |
| Up Axis | Z |
| Units | Meters |

### Controls

- **Right-click and drag** — Rotate camera around the target point
- **Left-click** — Pick the prim under the cursor and print its path
- **Left-click and drag** — Marquee-select prims and print their paths
- **Mouse wheel** — Dolly camera in/out

# Licensing

This example contains stb_image_write.h, © Sean Barrett, released under Public Domain.
