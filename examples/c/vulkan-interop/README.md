# vulkan-interop

Demonstrates how to integrate ovrtx with ovstage and Vulkan by sharing renders on the GPU.

The USD scene is populated through ovstage and rendered with an attached ovrtx renderer. ovrtx outputs are mapped to CUDA arrays every frame, which are then copied to CUDA-exported VkImage memory. The resulting textures are then sampled on a fullscreen quad to display the render in real time in a GLFW window. Memory access between CUDA and Vulkan is synchronized using timeline semaphores.

The sample also demonstrates ovrtx viewport picking and selection: left-click picks the prim under the cursor, left-drag performs marquee selection with a Vulkan overlay rectangle, picked prim paths are printed to stderr, and selected prims are highlighted with styled ovrtx selection outlines and translucent fill. Camera attribute updates are authored back to ovstage, then rendered through `ovrtx_step_with_stage()`.

Any scene used with picking must restrict the picked RenderProduct to CUDA-visible GPU 0 with `uint[] deviceIds = [0]`.

> **Known driver scheduling interaction on Linux.** The per-frame CUDA wait this sample performs on the mapped output's `cuda_sync.wait_event` can disturb how the renderer's concurrent Vulkan work is scheduled, which stalls that work and reduces throughput. Windows is unaffected. On Linux the sample applies the recommended workaround itself: the first statement of `main()` sets `CUDA_DEVICE_MAX_CONNECTIONS=1`, which lands before ovrtx creates the first CUDA context. A value already present in the environment is left alone, so `CUDA_DEVICE_MAX_CONNECTIONS=8 ./ovrtx-interop` reproduces the original behavior without a rebuild. Either way the sample prints which path it took. Refer to the "CUDA and Vulkan Scheduling on Linux" page in the ovrtx documentation.
>
> Reproducing the interaction needs the renderer to be submitting Vulkan work *while* a CUDA wait is outstanding.

## Selecting the Vulkan device

CUDA ordinals in this sample are process-visible indices after `CUDA_VISIBLE_DEVICES` is applied. The sample configures ovrtx for CUDA device `0` and requires the RenderProduct to use `uint[] deviceIds = [0]`. It resolves that ordinal once with `cuDeviceGet()` and obtains its exact interop identity with `cuDeviceGetUuid_v2()`. Vulkan selects the `VkPhysicalDevice` whose `VkPhysicalDeviceIDProperties::deviceUUID` contains the same 16 bytes.

Use `cuDeviceGetUuid_v2()` explicitly. On MIG systems, `cudaGetDeviceProperties().uuid` and the legacy `cuDeviceGetUuid()` can return the parent GPU UUID shared by sibling MIG devices. PCI bus identity is also parent-scoped and must not be used to distinguish MIG devices.

Mapped CUDA outputs carry the actual process-visible CUDA ordinal in `DLTensor.device.device_id`. A simple application can validate that value once against its configured device. A multi-GPU application should use it to route each output to the Vulkan context cached for that CUDA ordinal.

> _“Create a C++ interactive viewer that renders ovrtx camera output directly into a Vulkan presentation path through CUDA interop, with GPU selection, GPU image mapping, exported-image copies, explicit synchronization, ring buffering, orbit camera controls, finite-frame capture, and click or marquee picking with selection outlines.”_

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

For non-interactive validation without a GLFW window or Vulkan swapchain:

```bash
./build/ovrtx-interop --headless --num-frames 100
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

For non-interactive validation without a GLFW window or Vulkan swapchain:

```pwsh
.\build\Release\ovrtx-interop.exe --headless --num-frames 100
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

### DLSS Frame Generation

Frame generation is off by default and is enabled with `--dlssg`, which asks for as many interpolated frames per rendered frame as the GPU supports (1 on Ada, 3 on Blackwell). Use `--dlssg-frames <N>` to ask for a specific number instead; it implies `--dlssg`, and the renderer clamps the count to what the GPU supports.

```pwsh
.\build\Release\ovrtx-interop.exe --dlssg-frames 2
```

The sample authors the two DLSS-G render settings on the RenderProduct prim through ovstage at startup, and writes them on every run — including `false` when the flag is absent — so the command line always wins over whatever the scene file authored.

`--dlss-mode {performance,balanced,quality,auto,rtxaa}` sets the DLSS-SR mode on the RenderProduct (`omni:rtx:post:dlss:execMode`), which determines the internal render resolution that DLSS-G interpolates from. `rtxaa` is DLAA. It defaults to `performance`, as in Kit's viewport, and like the DLSS-G settings it is written on every run. Higher-resolution modes such as `quality` show more interpolation artifacts:

```pwsh
.\build\Release\ovrtx-interop.exe --dlssg --dlss-mode quality
```

With frame generation active, one `ovrtx_step_with_stage()` returns several output frames: the interpolated frames first and the real rendered frame last. The sample shows them in that order, and only steps again once the previous step's frames have all been copied out.

The renderer can decline frame generation when it cannot run, in which case a step keeps returning a single frame and the sample prints a warning after warmup. Common requirements and blockers include:

- An Ada or newer GPU that is driving the display
- A supported driver and operating system
- The `RealTimePathTracing` render mode (not `PathTracing`)
- `LdrColor` or `HdrColor` as the only render outputs
- A render resolution of at least 126 pixels per side
- No OmniGraph postprocessing, debug view, or SDG disable-color mode

### Presentation and frame pacing

A step returns its `N + 1` frames together. Current implementations have been observed to make those frames mappable at nearly the same moment, but applications must still poll each map and handle a timeout. Showing a batch as soon as it is ready puts its frames on screen back-to-back and then leaves a gap until the next step lands. The frame counter rises, but the motion reads as judder. Two flags control this:

- `--present-mode {fifo,mailbox,immediate}` selects the swapchain present mode, defaulting to `fifo`. `fifo` waits for vsync, which caps presentation at the display refresh and hides frame-generation throughput; use `immediate` to measure the real rate. Modes the surface does not support fall back to `fifo`, which is the only one Vulkan guarantees.
- `--pace` / `--no-pace` turn on or off timing the frames of a step the way Kit's present thread does, instead of showing them in a burst. Pacing is on by default whenever DLSS-G is enabled, as in Kit; without DLSS-G each step yields one frame and pacing has no effect. On every present it picks frame `elapsed / (mean step interval / frames per step * 5/6)` of the current step, where `elapsed` is the time since that step's frames all became available and the mean covers the last 10 steps. The 5/6 factor makes sure the real frame, which comes last, is reached before the next step arrives. The choice never moves backward, and it works under `fifo` as well as the other modes.

For visual debugging, `--dlssg-force-frame <K>` shows only frame `K` of every step and discards the rest: `0` is the first interpolated frame, and values past the end select the real frame. It implies `--dlssg`, and with `--num-frames` the saved `out.png` is that frame:

```pwsh
.\build\Release\ovrtx-interop.exe --dlssg-force-frame 0
```

`--dlssg-indicator` draws a small square in the top-left corner of the window: green while a real rendered frame is on screen, red while an interpolated one is. It is drawn on the swapchain only, so `out.png` does not contain it.

As in Kit, a step is shown only once all of its frames have arrived, and the newest step always wins: when it arrives, any frames of the previous step that have not been shown yet are discarded rather than queued, so presentation never falls behind the renderer.

The per-second log separates three rates that frame generation makes diverge. `Steps/s` counts renders, `Frames/s` counts frames that became visible, and `Presents/s` counts main-loop iterations — the loop re-presents the current image while the next frame renders, so it is much higher than either. `Frame gap` reports the spread between visible frames, which is what pacing improves, and `dropped` counts frames never shown, either skipped by pacing or superseded by a newer step:

```text
# --dlssg-frames 1, fifo at ~57 Hz, RTX 6000 Ada, default robot scene
Steps/s=11.0  Frames/s=22.0  Presents/s=57
Frame gap (ms): min=13.8   mean=44.8  max=85.7    # --no-pace: frames arrive in pairs
Frame gap (ms): min=21.7   mean=45.6  max=60.8    # paced (default): spread across the step
```

Pacing costs no throughput here — `Steps/s` and `Frames/s` are the same either way, because the ring of 10 shared images lets copies and the next step proceed while the current step's frames wait for their time, and each loop iteration advances the renderer as far as it can rather than one stage at a time. The remaining spread comes from the renderer: steps that take longer or shorter than the recent mean move the real frame's slot, in Kit as well as here. Kit's own DLSS-G comparison caps the render rate for that reason.

Frame generation adds a frame of latency, and this sample has no Reflex to recover it. Pacing can hold a ready frame until its scheduled slot to trade some responsiveness for even spacing. `immediate` avoids the latency of waiting for vsync but may introduce tearing; it is primarily useful here for measuring uncapped throughput.

# Licensing

This example contains stb_image_write.h, © Sean Barrett, released under Public Domain.
