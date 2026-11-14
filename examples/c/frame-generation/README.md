<!--
SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: LicenseRef-NvidiaProprietary

NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
property and proprietary rights in and to this material, related
documentation and any modifications thereto. Any use, reproduction,
disclosure or distribution of this material and related documentation
without an express license agreement from NVIDIA CORPORATION or
its affiliates is strictly prohibited.
-->
# DLSS Frame Generation (headless)

DLSS Frame Generation makes motion smoother in an interactive viewer by adding color frames between simulated camera frames. You can display these extra frames without increasing the camera simulation rate. It works in Real-Time Path Tracing.

This example enables the feature, moves an NVIDIA logo across a grid, and saves each returned frame as a PNG so you can inspect the intermediate positions. For a viewer that displays the frames, see [`../vulkan-interop`](../vulkan-interop), including how to pace presentation and drop interpolated frames that are no longer needed.

The four images below are one Blackwell step in presentation order. The first three are interpolated; the fourth is the simulated frame.

<table>
  <tr>
    <td align="center"><img src="../../../img/example-frame-generation-interp0.avif" alt="First interpolated frame" width="100%"><br><em>Interpolated 0</em></td>
    <td align="center"><img src="../../../img/example-frame-generation-interp1.avif" alt="Second interpolated frame" width="100%"><br><em>Interpolated 1</em></td>
    <td align="center"><img src="../../../img/example-frame-generation-interp2.avif" alt="Third interpolated frame" width="100%"><br><em>Interpolated 2</em></td>
    <td align="center"><img src="../../../img/example-frame-generation-simulated.avif" alt="Simulated frame" width="100%"><br><em>Simulated</em></td>
  </tr>
</table>

The example is headless and does not present the frames. See [`../vulkan-interop`](../vulkan-interop) for swapchain presentation and frame pacing.

## Prerequisites

- CMake 3.16 or newer and a C++17 toolchain. On Windows, use Visual Studio 2022 17.8 or newer with the C++ tools installed. On Ubuntu, install `build-essential` and `cmake`.
- For frame-generation validation, an Ada (RTX 40-series) or newer GPU with an active display, a supported NVIDIA driver and operating system, and unsandboxed execution.
- Network access while configuring the packaged build so CMake can download the pinned ovrtx and ovstage archives. The bundled scene does not require network access at runtime.

Here, *headless* means that the application does not create a window or present to a swapchain. It does not remove the active-display requirement for the GPU running the RenderProduct. The example can still render on an unsupported or display-less GPU, but it returns only the simulated frame.

## Running

### Linux

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
./build/frame-generation --frames 3
```

### Windows

```powershell
cmake -B build
cmake --build build --config Release
.\build\Release\frame-generation.exe --frames 3
```


| Option | Meaning |
|--------|---------|
| `--usd <path>` | USD layer to render (default: bundled `frame-generation.usda`) |
| `--frames <n>` | Non-negative interpolated-frame count to request; `0` requests one interpolated frame; use an explicit larger count to request more |
| `--steps <n>` | Positive number of steps to render and save (default: 2) |
| `--sweep <units>` | Distance the logo moves along X per step (default: 5 world units) |
| `--no-frame-gen` | Disable frame generation for comparison with the same scene |

## Output

The example saves every requested step to the process's current working directory. The default two steps let you inspect startup and the next capture. A startup or reset step may contain only the simulated frame while interpolation history is established.

The printed `output_frame_count` tells you what was returned. For the bundled camera, a count greater than one means frame generation is active. A successful run with one frame per step still rendered and saved the simulated images.

On Blackwell, `--frames 3` can return three interpolated frames followed by the simulated frame:

```text
Step 1: output_frame_count = 4 (3 interpolated + 1 simulated)
  ...
  wrote step1_interp0.png (1280x720)
  wrote step1_interp1.png (1280x720)
  wrote step1_interp2.png (1280x720)
  wrote step1_simulated.png (1280x720)
```

Ada supports one interpolated frame, so the same request can return two frames.

If later steps still contain only one frame, the renderer did not generate interpolated frames. The step itself still succeeds. See the [DLSS Frame Generation documentation](../../../docs/sensors/cameras/render_modes/real_time_path_tracing/frame_generation.rst) for hardware limits, compatibility requirements, and diagnostic guidance.

## Using frame generation in your application

Configure your RenderProduct for Real-Time Path Tracing with one color output, then enable frame generation. This USD example requests three interpolated frames; the camera at `/World/Camera` must already exist:

```usda
#usda 1.0
def Scope "Render" {
    def RenderProduct "Camera" {
        int2 resolution = (640, 480)
        rel camera = </World/Camera>
        rel orderedVars = [<LdrColor>]
        token omni:rtx:rendermode = "RealTimePathTracing"
        bool omni:rtx:dlss:frameGeneration = 1
        int omni:rtx:dlss:frameGenerationInterpolatedFrameCount = 3

        def RenderVar "LdrColor" {
            string sourceName = "LdrColor"
        }
    }
}
```

You can also write these attributes at runtime. This example uses `author_frame_generation()` in `main.cpp` to apply the command-line options through ovstage before stepping.

Step the renderer as usual, then select the RenderProduct from the result. For the unscheduled camera used here, every step completes one capture: its interpolated frames come first and its simulated frame comes last. Derive their indices from the returned count:

```cpp
// All returned frames must belong to one completed capture, as in this example.
// Scheduled cameras can return multiple simulated captures, so their total frame
// count cannot classify interpolation. For one capture, frames [0, N) are
// interpolated in presentation order and the last frame is simulated; N is zero
// when frame generation is off or declined.
//
// Never hardcode N. Derive it from output_frame_count on every step -- the count
// can change at runtime when the renderer starts or stops honouring the request.
/// Frame indices for a result containing exactly one completed camera capture.
struct FrameLayout {
    size_t interpolated_count;  // N
    size_t simulated_frame_index;  // always output_frame_count - 1
    bool frame_generation_active;
};

/// Classify a nonempty, single-capture result; multi-capture steps are unsupported.
FrameLayout classify_output_frames(ovrtx_render_product_output_t const& output) {
    FrameLayout layout{};
    layout.simulated_frame_index = output.output_frame_count - 1;
    layout.interpolated_count = output.output_frame_count - 1;
    layout.frame_generation_active = output.output_frame_count > 1;
    return layout;
}
```

Select a frame before looking up its color RenderVar, then map, consume, and unmap the output. Each frame uses the same RenderVar path. The example saves all frames; a viewer should select the frame due for presentation and drop overdue interpolated frames.

Custom `--usd` scenes must retain the expected `/Render/Camera`, `/Render/LdrColor`, and `/World/Logo` prims and complete exactly one capture per step. A scheduled camera can return several simulated captures in one step, so this example's count-based classification does not apply to that case.

## See also

- [`../vulkan-interop`](../vulkan-interop) — presenting and pacing generated frames
- [`../../../skills/dlss-frame-generation/SKILL.md`](../../../skills/dlss-frame-generation/SKILL.md) — agent-facing guidance
- [`../../../docs/sensors/cameras/render_modes/real_time_path_tracing/frame_generation.rst`](../../../docs/sensors/cameras/render_modes/real_time_path_tracing/frame_generation.rst) — feature requirements and output contract
