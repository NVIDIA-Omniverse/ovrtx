# AGENTS.md - AI Agent Guidelines for ovrtx-interop

> IMPORTANT: Update this file after significant changes to behavior, file layout, or conventions.

## Project Purpose

`vulkan-interop` demonstrates how to display OVRTX-rendered frames from an ovstage-populated scene in Vulkan by:

- Populating a USD scene through ovstage and attaching it to OVRTX
- Mapping OVRTX output as CUDA arrays
- Copying into Vulkan-exported images imported by CUDA
- Synchronizing CUDA and Vulkan with an external timeline semaphore
- Presenting with async double-buffering (ping-pong images)

This sample intentionally keeps OVRTX integration in `src/main.cpp` (no wrapper class).

## Current Platform Support

- Linux and Windows are both implemented.
- Platform-specific interop handle types are selected in `src/cuda/cuda_kernel.*` and `src/vk/vulkan_context.*`.

## Source Layout (Current)

```
ovrtx-interop/
├── CMakeLists.txt
├── README.md
├── AGENTS.md
├── shaders/
│   ├── fullscreen.vert
│   ├── fullscreen.frag
│   ├── overlay.vert
│   └── overlay.frag
├── src/
│   ├── main.cpp
│   ├── camera/
│   │   ├── orbit_camera.hpp
│   │   └── orbit_camera.cpp
│   ├── cuda/
│   │   ├── cuda_kernel.hpp
│   │   └── cuda_kernel.cpp
│   ├── glsl/
│   │   └── spirv_loader.hpp
│   └── vk/
│       ├── vulkan_context.hpp
│       ├── vulkan_context.cpp
│       ├── sampled_image.hpp
│       ├── sampled_image.cpp
│       ├── shader.hpp
│       ├── shader.cpp
│       ├── command_buffer.hpp
│       └── command_buffer.cpp
└── tests/ (optional; built only with ENABLE_TESTS=ON)
```

## Build and Run

### Configure + build

Linux:

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

Windows:

```pwsh
cmake -B build
cmake --build build --config Release
```

### Run

Linux:

```bash
./build/ovrtx-interop
```

Windows:

```pwsh
.\build\Release\ovrtx-interop.exe
```

## Command Line Interface (Matches `main.cpp`)

```text
Usage: ovrtx-interop [options]

Options:
  --usd, -u <path>              USD file path or URL
                                default: robot-ovrtx sample URL
  --render-product, -r <path>   Render product prim path
                                default: /Render/Camera
  --up-axis, -a <Y|Z>           Scene up axis (default: Z)
  --units <meters|centimeters>  Scene units (default: meters)
  --num-frames, -n <N>          Render N frames, save out.png, and exit
  --help, -h                    Show help
```

## Runtime Flow (Current Implementation)

Initialization:

1. `ovrtx_initialize` -> `ovrtx_create_renderer`
2. Create an ovstage instance, attach it to OVRTX, populate USD with `ovstage_population_open_usd_from_file`, and advance the write floor
3. Call `cuda_init(&cuda_uuid)` to use the CUDA context/device selected by OVRTX
4. Run one `ovrtx_step_with_stage` to detect output type and dimensions
5. Create Vulkan context using CUDA UUID for device matching
6. Create two exportable sampled images (`SHARED_IMAGE_COUNT = 2`)
7. Export Vulkan image memory and import into CUDA as surface-backed arrays
8. Export Vulkan timeline semaphore and import into CUDA
9. Prime first frame into buffer 0

Main loop:

1. Poll window/events and acquire swapchain image
2. If prior CUDA work is done (`cuEventQuery(cuda_frame_done_event)`):
   - update `read_timeline_value`
   - swap `read_idx` and `write_idx`
3. If camera moved, write transform to ovstage with `ovstage_write_attribute` and advance the write floor
4. If no CUDA work pending:
   - enqueue pending `ovrtx_enqueue_pick_query` before stepping, if the user clicked or dragged in the viewport
   - `ovrtx_step_with_stage` -> `ovrtx_fetch_results` -> `ovrtx_map_render_var_output`
   - if a pick query was submitted, map `OVRTX_RENDER_VAR_PICK_HIT` on CPU, print resolved prim paths, and update selection outline groups
   - wait on `rendered_output.cuda_sync.wait_event` (if provided)
   - copy OVRTX `CUarray` -> CUDA-imported Vulkan image at `write_idx`
   - signal external timeline semaphore from CUDA
   - unmap with `ovrtx_unmap_render_var_output` using `copy_done_event`
   - destroy results via `ovrtx_destroy_results`
5. Vulkan draws fullscreen triangle sampling image `read_idx`, plus the marquee overlay line strip while dragging
6. Submit/present with Vulkan waiting on `read_timeline_value`

## OVRTX Integration Contract

The core OVRTX frame lifecycle used by this sample:

1. `ovrtx_step_with_stage(...)` enqueues a frame from the current committed ovstage ordinal
2. `ovrtx_fetch_results(...)` waits for completion
3. `ovrtx_map_render_var_output(...)` maps output as CUDA array (`OVRTX_MAP_DEVICE_TYPE_CUDA_ARRAY`)
4. Consume `rendered_output.tensors[0].dl->data` as `CUarray`
5. If `rendered_output.cuda_sync.wait_event != 0`, wait on it in CUDA stream
6. After copy/compute, call `ovrtx_unmap_render_var_output(...)` and pass completion event
7. Call `ovrtx_destroy_results(...)`

Do not skip unmap/destroy; the sample treats these as required per-frame cleanup.

## Output Type and Format Mapping

Output detection:

- Search render vars for `HdrColor` first, then `LdrColor`.
- `HdrColor` is preferred when both exist.

Format mapping used in this sample:

| OVRTX output | Vulkan format | CUDA image format | bytes/pixel |
|---|---|---|---|
| HdrColor | `VK_FORMAT_R16G16B16A16_SFLOAT` | `CudaImageFormat::Half4` | 8 |
| LdrColor | `VK_FORMAT_R8G8B8A8_SRGB` | `CudaImageFormat::UInt8_4` | 4 |

## Synchronization Model

- OVRTX -> CUDA: per-frame CUDA wait event from mapped output (`cuda_sync.wait_event`)
- CUDA -> Vulkan: external timeline semaphore; CUDA signals monotonically increasing value
- CPU side: frame completion is polled by `cuEventQuery(cuda_frame_done_event)` to avoid blocking
- Double buffering:
  - CUDA writes `write_idx`
  - Vulkan samples `read_idx`
  - indices swap only after CUDA frame is complete

## Camera and Scene Updates

- Orbit camera input is handled through GLFW callbacks.
- On change, camera transform is written to `/World/Camera` attribute `omni:xform` through `ovstage_write_attribute`.
- `OVSTAGE_SEMANTIC_MATRIX` is used with a 16-lane float64 DLTensor payload.

## Picking and Selection

- Right mouse drag rotates the orbit camera; mouse wheel dollies.
- Left click enqueues a one-pixel-equivalent NDC pick query for the clicked RenderProduct location.
- Left drag enqueues an NDC marquee pick query using the drag rectangle and draws the bounds through `overlay.vert` / `overlay.frag`.
- Any scene used with picking must restrict the picked RenderProduct to CUDA-visible GPU 0 with `uint[] deviceIds = [0]`.
- Pick results are returned as `OVRTX_RENDER_VAR_PICK_HIT`, mapped on CPU, and resolved to string prim paths with `ovrtx_get_path_dictionary` plus `path_dictionary_get_tokens_from_paths`.
- Picking remains active while attached to ovstage and prints resolved prim paths.
- Selection outlines are enabled at renderer creation with `ovrtx_config_entry_selection_outline_enabled(true)` and `ovrtx_config_entry_selection_fill_mode(OVRTX_SELECTION_FILL_MODE_GROUP_FILL_COLOR)`.
- Group `1` is styled once at startup with `ovrtx_set_selection_group_styles()` (custom outline color plus translucent fill).
- The current selection is drawn by assigning group `1` through `ovrtx_set_selection_outline_group()`; group `0` clears the prior selection. This is renderer-only, stream-ordered state that works in BORROW attach mode without `ovrtx_write_attribute()` or Fabric attribute writes.

## Dependencies

System requirements (found via CMake):

- CUDA Toolkit (`find_package(CUDAToolkit REQUIRED)`)
- Vulkan SDK/runtime (`find_package(Vulkan REQUIRED)` + `glslc`)

Fetched automatically by CMake:

- OVRTX via `ovrtx_fetch()`
- GLFW (if not found locally)
- GLM
- volk
- unordered_dense
- GoogleTest (only when `ENABLE_TESTS=ON`)

## Notes for Future Agents

- Prefer keeping OVRTX interop behavior concentrated in `src/main.cpp` unless a refactor is intentional.
- Keep README and this file aligned with actual CLI flags/defaults.
- If you change sync behavior, update both:
  - `OVRTX Integration Contract`
  - `Synchronization Model`
- If you add/remove files or targets, update `Source Layout` and `Build and Run`.
