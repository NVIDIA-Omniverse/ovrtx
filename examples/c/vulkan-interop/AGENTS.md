# AGENTS.md - AI Agent Guidelines for ovrtx-interop

> IMPORTANT: Update this file after significant changes to behavior, file layout, or conventions.

## Project Purpose

`vulkan-interop` demonstrates how to display OVRTX-rendered frames from an ovstage-populated scene in Vulkan by:

- Populating a USD scene through ovstage and attaching it to OVRTX
- Mapping OVRTX output as CUDA arrays
- Copying into Vulkan-exported images imported by CUDA
- Synchronizing CUDA and Vulkan with an external timeline semaphore
- Presenting from a ring of shared images, with optional frame pacing

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
./build/ovrtx-interop --headless --num-frames 100
```

Windows:

```pwsh
.\build\Release\ovrtx-interop.exe
.\build\Release\ovrtx-interop.exe --headless --num-frames 100
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
  --headless, --no-window       Run the interop path without GLFW
  --camera, -c <path>           Orbit camera prim (default: /World/Camera)
  --present-mode <mode>         fifo | mailbox | immediate (default: fifo)
  --pace, --no-pace             Time generated frames like Kit's present
                                thread (default: on with DLSS-G, off otherwise)
  --dlssg                       Enable DLSS Frame Generation (default: off)
  --dlssg-frames <N>            Interpolated frames per rendered frame,
                                implies --dlssg (default: GPU maximum)
  --dlssg-force-frame <K>       Show only frame K of each step (0 = first
                                interpolated, clamped to the real frame),
                                implies --dlssg; for visual debugging
  --dlssg-indicator             Draw a corner square: green on real frames,
                                red on interpolated ones
  --dlss-mode <mode>            DLSS-SR mode on the render product:
                                performance | balanced | quality | auto | rtxaa
                                (default: performance, as in Kit's viewport)
  --help, -h                    Show help
```

## Presentation and Frame Pacing

- `--present-mode` selects the swapchain present mode. `fifo` is the default and
  the only mode the Vulkan spec guarantees, so the other two fall back to it when
  `vkGetPhysicalDeviceSurfacePresentModesKHR` does not report them. Both creation
  sites go through `VulkanContext::_select_present_mode()` so they cannot
  disagree, and `VulkanContext::present_mode()` reports what was accepted.
- `fifo` caps presentation at the display refresh, which hides frame-generation
  throughput. `immediate` is the mode to use for benchmarking. On a virtual or
  remote display with no client attached, `fifo` *and* `mailbox` can both pin to
  a very low rate because `vkAcquireNextImageKHR` waits on the display.
- Each present shows one frame of the most recently completed step.
  `SubframeScheduler` implements it:
  - A step is *published* only once all of its frames have landed in the ring,
    so a partially copied sequence is never shown.
  - A newly published step replaces the current one outright. Frames of the old
    step not yet shown are freed unshown, including its real frame; nothing is
    queued behind the newest step.
- Pacing is on by default whenever DLSS-G is enabled; `--no-pace`
  forces it off and `--pace` forces it on. Without DLSS-G a step yields one
  frame, so pacing has no effect.
- Paced, each present picks the frame from time since publish:
  `index = elapsed / (mean_publish_interval / frames_per_step * 5/6)`, clamped to
  the last (real) frame and never moving backward. The mean is over the last 10
  publish intervals, and the 1/6 shortening is an allowance for projection
  error, so the real frame is reached before the next step lands. Frames whose
  time has passed are skipped and counted as dropped. Because the index is
  anchored to the publish time, a late present cannot delay the rest of the step,
  which is why pacing works under `fifo` (vsync) too.
- Before the first publish interval is known, or when a step yields one frame,
  the last frame is shown directly.
- With `--no-pace`, a step's frames are shown one per present, back to back.
- `--dlssg-force-frame K` bypasses `SubframeScheduler::choose` and shows only
  frame `min(K, last)` of each published step, for inspecting interpolated
  frames in isolation. The other frames count as `dropped`, `--num-frames` exits
  and saves `out.png` on the forced frame instead of the real one, and headless
  reads back the forced frame of the final step.
- `--dlssg-indicator` clears a 48 px square at (16, 16) of the swapchain image
  with `vkCmdClearAttachments` after the fullscreen draw: green when
  `read_holds_real_frame`, red otherwise. It needs no pipeline state and never
  touches the shared images, so `out.png` is unaffected.

## Metrics

The per-second line separates measurements that frame generation makes diverge:

- `Steps/s` counts `ovrtx_step_with_stage` calls; `Frames/s` counts frames that
  actually became visible. With DLSS-G it is at most `(N + 1) x Steps/s`;
  frames skipped by pacing or superseded by a newer step count as `dropped`.
- `Presents/s` counts loop iterations. Because the map is polled, the loop
  re-presents the current image while the next frame renders, so this is much
  higher than `Frames/s` and is not a smoothness measure.
- `Step` is enqueue to `ovrtx_fetch_results` success. `MapCopy` is the map plus
  the copy submission, which is cheap now that the unmap is deferred.
- `Frame gap` is the spread between visible frames. Judder shows up here as a
  wide min/max even when the mean looks healthy; pacing is what tightens it.
- `dropped` counts frames never shown: skipped by pacing because their time had
  passed, or freed because a newer step was published first.

## Runtime Flow (Current Implementation)

Initialization:

1. `cuda_apply_scheduling_workaround()` as the first statement of `main()`, before anything can create a CUDA context
2. `ovrtx_initialize` -> `ovrtx_create_renderer`
3. Create an ovstage instance, attach it to OVRTX, populate USD with `ovstage_population_open_usd_from_file`, and advance the write floor
4. Author the DLSS-G settings (`author_dlssg_settings`) and the DLSS-SR mode (`author_dlss_exec_mode`) on the RenderProduct prim, unconditionally, so the CLI overrides the scene's opinion
5. Configure CUDA-visible device 0 in ovrtx, then call `cuda_init(0, &cuda_uuid)` to validate the OVRTX context and obtain its MIG-aware UUID with `cuDeviceGetUuid_v2`
6. Run one `ovrtx_step_with_stage` to detect output type and dimensions
7. Create Vulkan context using CUDA UUID for device matching
8. Create the ring of exportable sampled images (`CUDA_SHARED_IMAGE_COUNT = 10`)
9. Export Vulkan image memory and import into CUDA as surface-backed arrays
10. Export Vulkan timeline semaphore and import into CUDA
11. Prime first frame into buffer 0

Main loop. Nothing in it blocks on the renderer: both ovrtx waits are polled with
a zero timeout, so an iteration that finds nothing ready just re-presents the
current image.

1. Poll window/events and acquire swapchain image
2. Retire ring slots whose copy has landed (`cuEventQuery(slot.copy_done)`):
   release the ovrtx mapping with `release_mapped_output` and move the slot from
   `Writing` to `Ready`
3. Publish the newest step whose `FrameSlot::frames_in_step` frames are all
   `Ready`: free the `Ready` slots of older steps (dropped), order the step's
   slots by `FrameSlot::timeline_value` (copy order), and hand the count to
   `SubframeScheduler::publish` (see `Presentation and Frame Pacing`)
4. Ask `SubframeScheduler::choose` for this present's frame. If it changed, free
   skipped frames and the previously shown slot, adopt the new `read_idx`, and
   take that slot's `timeline_value` and `holds_real_frame`
5. Advance the producer until it stalls: repeat the stages below while any of
   them made progress, so one iteration can copy a step's frames, retire it and
   enqueue the next. Under `fifo` an iteration lasts a whole refresh, and moving
   one stage per iteration used to cap rendering at a fraction of the display rate
   - if no step is in flight, enqueue one (not gated on a free slot; it bumps
     `pending.step`, which each copied slot records in `FrameSlot::step`):
     - if the camera moved, write the transform with `ovstage_write_attribute`
       and advance the write floor. This must happen here, with no step in
       flight: the write blocks until the renderer is done reading the stage, so
       writing while a step renders stalls the loop for the rest of that step.
       Under DLSS-G that left one present per step, always on the interpolated
       frame, because the next step replaced the sequence before the real one
       came up
     - enqueue pending `ovrtx_enqueue_pick_query` before stepping, if the user clicked or dragged in the viewport
     - `ovrtx_step_with_stage`
   - poll `ovrtx_fetch_results` with timeout 0. On success:
     - if a pick query was submitted, resolve and keep the
       `OVRTX_RENDER_VAR_PICK_HIT` handle; the map itself is polled separately
     - `collect_color_outputs` gathers one color handle per output frame, in presentation order
   - if a pick query is still outstanding, poll its CPU map with timeout 0. On
     success, print resolved prim paths and update selection outline groups; on
     `OVRTX_API_TIMEOUT` leave the query pending and retry next iteration
   - if a ring slot is `Free`, poll `copy_output_to_surface` with timeout 0 for
     the next unconsumed frame: map, wait on `cuda_sync.wait_event` (if
     provided), copy OVRTX `CUarray` -> CUDA-imported Vulkan image at the free
     slot. The mapping is **not** released here; it is handed back for step 2
   - signal external timeline semaphore from CUDA and record `slot.copy_done`
   - destroy the step result once every frame it produced has been copied out
     and any pick hit has been read (`PendingFrames::retirable()`)
6. Vulkan draws fullscreen triangle sampling image `read_idx`, plus the marquee overlay line strip while dragging
7. Submit/present with Vulkan waiting on `read_timeline_value`
8. Sleep until the next frame is due, so pacing does not busy-spin on redundant
   presents

## Frame Queue and DLSS Frame Generation

- One `ovrtx_step_with_stage` normally produces one output frame. With DLSS Frame Generation enabled it produces `N + 1`: the interpolated frames first, the real rendered frame last.
- All `N + 1` frames of a step become mappable at essentially the same time, not progressively. Measured on L40 with `N = 1`, `MapCopy by frame-in-step` is ~0.25 ms for both the interpolated and the real frame, and `map polls` stays at 0 — by the time `ovrtx_fetch_results` succeeds, every frame of the step is already mappable. This is why pacing is needed to spread them out, and why the ring has to be able to hold a whole step.
- Consequently the renderer wait lives in the polled `ovrtx_fetch_results`, not in the map. The map poll is kept anyway because it costs nothing and the ordering is a renderer implementation detail, not a documented guarantee.
- `PendingFrames` holds the step result plus one color output handle per frame, and tracks `results_fetched` because a step result is fetched before its frames are mappable. The next step is only enqueued once the queue is drained, and `ovrtx_destroy_results` runs only after the last frame of a step has been copied out.
- Priming uses the last (real) frame of its step, and so does `find_accumulation_status`, since interpolated frames carry no accumulation status.
- `--num-frames` must save a real frame to `out.png`. Each ring slot records `holds_real_frame` (set from `pending.drained()` at copy time), the shown slot's value becomes `read_holds_real_frame`, and the loop exits only once the shown buffer holds a real frame. Once the frame count is reached the present jumps straight to the published step's real frame, because a newer step can otherwise replace the sequence before pacing reaches it. Headless drains all frames of a step in one iteration, so it always exits on a step boundary. Both count frames that became visible, so either can overshoot `--num-frames` by up to `N`.
- The two settings are authored with `ovstage_write_attribute` + `OVSTAGE_PRIM_MODE_UPSERT` on the RenderProduct prim, not through a renderer config entry. No USD API schema needs to be applied first; both the sensor scheduling layer and Hydra read them from the runtime scene by attribute name.
  - `bool omni:rtx:dlss:frameGeneration`
  - `int omni:rtx:dlss:frameGenerationInterpolatedFrameCount`. The renderer clamps it to the GPU maximum and treats 0 or unset as 1, so without `--dlssg-frames` the sample writes `MAX_DLSSG_INTERPOLATED_FRAMES` (3) to get the GPU maximum. The ring (`CUDA_SHARED_IMAGE_COUNT`) is sized for that count, enforced by a `static_assert`.
- `--dlss-mode` authors `token omni:rtx:post:dlss:execMode` the same way (an
  `OVSTAGE_SEMANTIC_TOKEN_ID` write of a token interned through the stage's path
  dictionary). It sets the internal render resolution for DLSS-SR/DLSS-RR, which
  is what DLSS-G interpolates from. Like the DLSS-G settings it is written on
  every run, defaulting to `performance` (`DEFAULT_DLSS_MODE`) to match Kit's
  viewport; `quality` shows noticeably more interpolation artifacts.
- Frame generation is declined silently in several situations, so `report_dlssg_frame_count` warns once if no step produced extra frames within `DLSSG_WARMUP_STEPS`. The warmup exists because DLSS-G interpolates between two rendered frames and legitimately produces a single frame right after a history reset.

## OVRTX Integration Contract

Startup attaches ovstage before enqueueing selection styling because attachment
requires an idle renderer. Styling remains ordered before the first rendered frame.

The core OVRTX frame lifecycle used by this sample:

1. `ovrtx_step_with_stage(...)` enqueues a frame from the current committed ovstage ordinal
2. `ovrtx_fetch_results(...)` returns result metadata. This does **not** mean the
   output frames are ready to map. Timeout 0 makes it a poll returning
   `OVRTX_API_TIMEOUT`
3. `ovrtx_map_render_var_output(...)` maps output as CUDA array (`OVRTX_MAP_DEVICE_TYPE_CUDA_ARRAY`). Timeout 0 makes it a poll
4. Consume `rendered_output.tensors[0].dl->data` as `CUarray`
5. If `rendered_output.cuda_sync.wait_event != 0`, wait on it in CUDA stream
6. After the copy has actually landed, call `ovrtx_unmap_render_var_output(...)`
   and pass the completion event. For a zero-copy CUDA-array mapping this call
   waits for that event on the CPU, so call it only once `cuEventQuery` reports
   the event complete
7. Call `ovrtx_destroy_results(...)`. This is independent of the mappings and may
   run before them

Do not skip unmap/destroy; the sample treats these as required per-frame cleanup.
Deferring the unmap means shutdown has to release any mapping the ring still
holds, which the sample does after `cuStreamSynchronize`.

Check the result of CUDA timeline import, image copy, and timeline signaling.
On failure, drain pending work, release mapped outputs and results, and exit
with a nonzero status before submitting Vulkan work that depends on the failed operation.

CUDA device identity is based on process-visible ordinals after `CUDA_VISIBLE_DEVICES` filtering. The configured ovrtx GPU, RenderProduct `deviceIds`, and mapped DLPack `device_id` use that same ordinal namespace. Vulkan device selection compares `cuDeviceGetUuid_v2` with `VkPhysicalDeviceIDProperties::deviceUUID`; never use PCI identity, `cudaDeviceProp::uuid`, or legacy `cuDeviceGetUuid` to distinguish MIG instances.

## Output Type and Format Mapping

Output detection:

- Search render vars by source name for `HdrColor` first, then `LdrColor`; OVRTX reports regular USD RenderVars by full prim path.
- `HdrColor` is preferred when both exist.

Format mapping used in this sample:

| OVRTX output | Vulkan format | CUDA image format | bytes/pixel |
|---|---|---|---|
| HdrColor | `VK_FORMAT_R16G16B16A16_SFLOAT` | `CudaImageFormat::Half4` | 8 |
| LdrColor | `VK_FORMAT_R8G8B8A8_SRGB` | `CudaImageFormat::UInt8_4` | 4 |

## Synchronization Model

- Startup attaches the stage before enqueueing selection styling; no renderer
  operation is pending at attachment.

- OVRTX -> CUDA: per-frame CUDA wait event from mapped output (`cuda_sync.wait_event`)
- CUDA -> Vulkan: external timeline semaphore; CUDA signals monotonically increasing value
- CPU side: nothing in the windowed loop waits on the renderer.
  `ovrtx_fetch_results` and `ovrtx_map_render_var_output` are polled with
  timeout 0 for the color output *and* for the pick hit, and copy completion is
  polled with `cuEventQuery(slot.copy_done)`. The startup prime and the headless
  loop still use `ovrtx_timeout_infinite`; neither presents interactively
- Ring buffering (`CUDA_SHARED_IMAGE_COUNT` slots, states `Free` / `Writing` /
  `Ready` / `Showing`):
  - CUDA writes into any `Free` slot
  - Vulkan samples the `Showing` slot
  - a slot becomes `Ready` only after its copy event completes, and the slot
    being shown is freed when a newer frame replaces it
  - a `Ready` slot from a superseded step goes straight back to `Free` (dropped)
  - sized `2 * (3 + 1) + 2 = 10`: the published step's frames (one of them
    shown) and the next step's frames being written, for up to 3 interpolated
    frames, plus spare slots so the step after can start copying before the next
    one is published, so the renderer never waits on presentation
- **Each slot owns its own `copy_start` / `copy_done` events.** Several copies are
  in flight at once, so a shared completion event would be unsafe and a shared
  timing pair could not attribute a duration to one frame. The single shared
  `cuda_copy_done_event` remains only for the priming and headless paths, which
  copy one frame at a time and release each mapping before starting the next.
- **The unmap is deferred on purpose.** For a zero-copy CUDA-array mapping,
  `ovrtx_unmap_render_var_output` waits for its fence event on the CPU, and that
  event is stream-ordered behind the renderer's own production. Unmapping right
  after queueing the copy relocates the render wait into the unmap instead of
  removing it, so the mapping is held until `cuEventQuery` reports the copy done.
  Mapping lifetime is independent of `ovrtx_destroy_results()`, which is what
  makes this legal.
- Known driver scheduling interaction on Linux: the OVRTX -> CUDA stream wait above disturbs Vulkan scheduling and stalls the renderer's GPU work. Workaround is `CUDA_DEVICE_MAX_CONNECTIONS=1` in the environment before the first CUDA context is created. `cuda_apply_scheduling_workaround()` (`src/cuda/cuda_kernel.cpp`, snippet `cuda-device-max-connections`) does this from the first statement of `main()`, so the call site must stay first; it defers to a value already in the environment, which is the no-rebuild opt-out. See `docs/core/cuda_vulkan_scheduling.rst`. Windows is unaffected, where the function is a no-op.
- The interaction needs **both** an outstanding stream wait and concurrent renderer Vulkan submission. An outstanding wait alone is not enough: if the loop blocks on the copy before enqueueing more renderer work, the renderer sits idle and nothing is disturbed. The headless loop, which copies one frame at a time, is what reproduces it (`Runtime Flow`). The windowed loop used to be exempt by construction because it gated the next step on the previous copy; now that it polls and keeps a step in flight while copies are still outstanding, it satisfies both conditions too, so the workaround is expected to matter for both loops.

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
- That map is polled with timeout 0 like the color one and returns `PickOutputResult::{Read, NotReady, Failed}`. A CPU map is a readback, so blocking on it would stall presentation for exactly the reason the color path no longer does. `NotReady` leaves `pick_query_submitted` set and the step in flight, so the pick is retried on later iterations instead of being dropped, and `retirable()` holds `ovrtx_destroy_results` back until the pick has been read.
- Picking remains active while attached to ovstage and prints resolved prim paths.
- Selection outlines are enabled at renderer creation with `ovrtx_config_entry_selection_outline_enabled(true)` and `ovrtx_config_entry_selection_fill_mode(OVRTX_SELECTION_FILL_MODE_GROUP_FILL_COLOR)`.
- Group `1` is styled once at startup with `ovrtx_set_selection_group_styles()` (custom outline color plus translucent fill).
- The current selection is drawn by assigning group `1` through `ovrtx_set_selection_outline_group()`; group `0` clears the prior selection. This is renderer-only, stream-ordered state that works while attached without `ovrtx_write_attribute()` or scene attribute writes.

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
