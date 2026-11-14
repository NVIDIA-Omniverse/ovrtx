# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - 2026-11-12

### Added

- [DLSS-NR](https://nvidia-omniverse.github.io/ovrtx/0.7.0/sensors/cameras/render_modes/dlss_nr.html) is now available on Linux.
- The new [Generic WPM sensors](https://nvidia-omniverse.github.io/ovrtx/0.7.0/sensors/nonvisual/generic_wpm/index.html) allow low-level access to the WPM model,
  supporting custom transmitter, receiver, and ray-bundle patterns and returning raw `Contributions` outputs.
- Experimental WPM lidar rendering of NuRec-trained Gaussian splats with `lidarExtraSignals`; ordinary
  RGB splats do not provide a lidar response.
- [`ParticleField` Gaussian splats can be relit](https://nvidia-omniverse.github.io/ovrtx/0.7.0/geometry/gaussian_splats.html#diffuse-relighting)
  using the included `ParticleFieldSHDiffuse.mdl`.
- [Runtime textures](https://nvidia-omniverse.github.io/ovrtx/0.7.0/materials/runtime_textures.html)
  allow writing texture data directly to ovstage and using it in the renderer, enabling dynamic and procedurally generated texturing. [A new example](https://nvidia-omniverse.github.io/ovrtx/0.7.0/examples/python_runtime_textures.html) demonstrates mapping a rendered output onto a primitive.
- The [`SelectionState`](https://nvidia-omniverse.github.io/ovrtx/0.7.0/scene/picking.html#selectionstate-aov)
  output allows you to draw selection outlines and fills yourself using the same data that ovrtx uses internally, making it possible to style the selection highlighting however you want. [A new example](https://nvidia-omniverse.github.io/ovrtx/0.7.0/examples/c_selection_spg.html) shows how to do this using SPG.
- C and Python
  [profiling APIs](https://nvidia-omniverse.github.io/ovrtx/0.7.0/core/profiling.html) support CPU/GPU
  timing, memory metrics, live reads, and file capture. Independent readers retain their own position,
  and samples identify their parent scope and execution context.
- [C and Python data-provider APIs](https://nvidia-omniverse.github.io/ovrtx/0.7.0/c_api/index.html#data-providers)
  let ovrtx load assets from your application's own storage or memory. Use them to connect your asset
  system or supply generated data without first saving it to files. Supported assets include textures,
  MDL resources, NuRec/IndeX volumes, and SPG assets.
- Mesh lights can now use IES profiles to reproduce the measured directional light distribution of real fixtures.
- [MDL material displacement](https://nvidia-omniverse.github.io/ovrtx/0.7.0/core/renderer_configuration.html)
  now works with geometry streaming, including static, animated, and skinned meshes.
- RTX Minimal can display a dome light's environment map as the background behind scene geometry.
- Tiled rendering can use camera transforms directly from GPU memory, reducing CPU overhead for large
  camera arrays. This also supports rendering across multiple GPUs.
- [`ovrtx_clear_history()`](https://nvidia-omniverse.github.io/ovrtx/0.7.0/c_api/index.html#c.ovrtx_clear_history)
  and Python
  [`Renderer.clear_history()`](https://nvidia-omniverse.github.io/ovrtx/0.7.0/python_api/index.html#ovrtx.Renderer.clear_history)
  /
  [`clear_history_async()`](https://nvidia-omniverse.github.io/ovrtx/0.7.0/python_api/index.html#ovrtx.Renderer.clear_history_async)
  reset temporal and lidar/radar model history without resetting simulation time or sensor schedules.
  Optional tile selection and first-frame quality control support selective resets.
- Experimental rendering of retained ovstage history with
  [`enable_history_presentation`](https://nvidia-omniverse.github.io/ovrtx/0.7.0/python_api/index.html#ovrtx.RendererConfig.enable_history_presentation)
  and a `history_selective` stage in borrow mode. Selected numeric attributes can render at an earlier
  committed ordinal; nonnumeric attributes retain their latest values.
- Experimental [`MappedRenderVar.producer_stream`](https://nvidia-omniverse.github.io/ovrtx/0.7.0/python_api/index.html#ovrtx.MappedRenderVar.producer_stream)
  / `cuda_sync.stream` handoff lets CUDA consumers enqueue reads on the output's producer stream. The
  stream is borrowed and enqueue-only; consumers using `wait_event` should ignore it.
- Compressed RenderVars can be mapped directly to CPU memory with
  [`OVRTX_MAP_DEVICE_TYPE_CPU`](https://nvidia-omniverse.github.io/ovrtx/0.7.0/c_api/index.html#c.OVRTX_MAP_DEVICE_TYPE_CPU),
  without application-side CUDA code. The map waits for encoding and returns the `NV_ENC_ENCODE_OUT_PARAMS` header
  followed by only the valid bitstream bytes.
- Compressed outputs expose CPU-resident metadata on both CPU and GPU mappings: `compression:type`
  identifies the codec (1 = H.264, 2 = HEVC, 3 = AV1); `compression:shape` gives the pre-encoding image's
  height, width, and channels; `compression:dtype` gives its DLPack code, bits, and lanes.
  `compression:headerBytes` gives the size of the `NV_ENC_ENCODE_OUT_PARAMS` header before the bitstream,
  and `compression:headerVersion` identifies its NVENC structure version. The bitstream contains RGB only.
- AV1 RenderVar compression on GPUs with an NVENC AV1 encoder. Author `ovrtx:compression:type = "av1"`
  on the RenderVar. AV1 accepts `iFrameQp`, `pFrameQp`, and `bFrameQp` values of 0–255 and `targetQuality`
  values of 0–63; H.264 and HEVC retain 0–51. These parameters use the `ovrtx:compression:` namespace.
- SPG nodes can retain private buffers and images across frames through
  [`self.memory`](https://nvidia-omniverse.github.io/ovrtx/0.7.0/spg/do/state.html).
- [SPG shader prims inherit ports, value inputs, and defaults](https://nvidia-omniverse.github.io/ovrtx/0.7.0/spg/ref/usd.html#spg-schema-inputs)
  from their applied USD API schemas.
- [Python RenderVar outputs](https://nvidia-omniverse.github.io/ovrtx/0.7.0/sensors/common/sensor_outputs.html)
  can be looked up by a unique prim name as well as their full path. Ambiguous names still require a full
  path.
- [Graphics API validation](https://nvidia-omniverse.github.io/ovrtx/0.7.0/core/renderer_configuration.html#graphics-api-debug-validation)
  can be requested through `RendererConfig.enable_debug_validation` /
  `OVRTX_CONFIG_ENABLE_DEBUG_VALIDATION` at renderer creation.
- A platform-independent
  [`ovrtx-schemas@<version>.zip`](https://nvidia-omniverse.github.io/ovrtx/0.7.0/core/usd_plugin_paths.html#use-the-schemas-without-installing-ovrtx)
  release asset allows USD schema authoring without installing the ovrtx runtime.
- Anonymous library-startup telemetry is enabled by default, sending at most one ovrtx report per
  process. Opt out before initialization with `ovrtx_library_telemetry_opt_out()` /
  `ovrtx.library_telemetry_opt_out()`, or set `NVIDIA_OMNIVERSE_PRODUCT_TELEMETRY_DISABLED=1` before
  process startup. See [TELEMETRY.md](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/TELEMETRY.md) for the data sent and transport details.
- The scene-wide `omni:rtx:rendering:perViewTlasMinSeparation` setting controls when separated cameras
  use per-view acceleration structures. Author it on RenderSettings; RenderProduct values are ignored.
- Distributed shader caches accept query-style `grpc://` URLs with TLS and DNS-discovery options, or an
  explicit endpoint list.
- The [Vulkan interop sample](https://nvidia-omniverse.github.io/ovrtx/0.7.0/examples/c_vulkan_interop.html)
  adds support for DLSS Frame Generation, with paced presentation of real and interpolated frames.
- Adaptive sampling in Real-Time Path Tracing uses the previous DLSS-denoised frame to concentrate
  samples where they are needed. It is disabled for rolling-shutter cameras.

### Changed

- **Breaking (C/C++ and Python):** Resource handles, operation IDs, tokens, prim paths, and path
  lists are distinct types. Replace implicit integers with the matching handle type and use `.raw_id` at
  numeric boundaries. Public C layouts remain compatible on supported 64-bit platforms; rebuild C++ interfaces
  and update Python consumers together.
- **Breaking:** Rename `ovx_string_or_token_t` to `ovx_token_or_string_t`; field order and binary layout are
  unchanged.
- **Breaking:** `OVX_INVALID_TOKEN` is now `UINT64_MAX`; token `0` represents the empty string. A non-null
  string pointer takes precedence over the token, including for an empty string. Empty prim paths remain
  invalid.
- **Breaking (ABI):** Step results include a status and error message for each requested RenderVar, including
  failed outputs; DLSS-G interpolated frames carry only color outputs. Other RenderVars continue rendering.
  Python exposes `RenderVarOutput.status` and `error_message`; rebuild native consumers for the larger result
  structure.
- **Breaking:** Non-image SDG outputs, including bounding boxes, ID maps, and `CameraParams`, expose named
  tensors and CPU parameters instead of packed byte buffers. Decode by field name and DLPack strides, and
  respect `valid_count`; scalar parameters have shape `(1,)`. Empty semantic bounding-box outputs can be
  mapped to CPU memory. See [SDG output
  decoding](https://nvidia-omniverse.github.io/ovrtx/0.7.0/sensors/cameras/decoding_outputs.html).
- **Breaking (C/C++ build):** ovrtx no longer bundles ovstage headers. Supply the matching ovstage package
  through `CMAKE_PREFIX_PATH` or beside ovrtx; manual include-path setups must add ovstage's headers
  explicitly.
- **Breaking:** Author depth sensors on the `Camera` using `OmniSensorGenericDepthSensorSingleViewAPI` and
  `omni:sensor:depthSensor:*`, replacing the RenderProduct API and `omni:rtx:post:depthSensor:*` parameters.
  Camera-core and depth sensors now select schema/model versions; existing depth content must be re-authored.
- **Breaking:** Compression settings are read only from RenderVars listed in `orderedVars`. Author
  `ovrtx:compression:*` on those RenderVars; fallback locations based on `sourceName` are no longer consulted.
  RenderVars that relied on fallback settings now return uncompressed output.
- **Breaking (SPG):** Pass Slang arrays with `slang.array(...)`, and provide `{ offset, strides }` layouts for
  arrays and matrices in precompiled shaders. Previous-frame reads more than eight frames back now fail
  explicitly.
- **Breaking (SPG):** CUDA/Slang argument wrappers and launch configurations are now userdata. Use field
  access, `pairs`, and `#`; replace table-type checks, `next()`, and table-library operations on these objects.
- **Breaking:** RenderProducts sharing a camera, resolution, and authored `viewportHandle` now fail instead
  of potentially dropping output. Remove `viewportHandle` or give each product a distinct value.
- `omni:sensor:frameLimit` is now an `int`: `-1` means unlimited and `0` pauses production. Raising the limit
  resumes on the current scheduled frame number. Clear history before resuming if scene objects moved during
  the pause. Legacy `uint` values retain their old meaning with a deprecation warning. A sensor that starts
  paused receives first-frame streaming and quality treatment when it begins producing frames.
- Each RenderProduct honors its own streaming-wait and accumulation settings. Only products participating in
  the wait render during it, and completed products no longer accumulate unnecessary frames.
- Compressed-output buffers are sized to the actual image resolution, substantially reducing GPU memory use:
  at 1280×720, about 42 MiB instead of 3 GiB per compressed RenderVar with the default buffer count.
  GPU mappings still advertise capacity; read the header for the valid encoded length.
- Headless, Minimal-only renderers use less GPU memory during material loading by avoiding intermediate
  ray-tracing pipelines.
- SPG graph execution has lower CPU overhead, particularly for graphs containing many small CUDA or Slang
  nodes.
- Texture streaming uses stable per-view demand and hysteresis to reduce mip oscillation and unnecessary
  uploads, with less render-thread contention during background feedback processing.
- Texture streaming uses a 90-second progress timeout with bounded retries for stalled loads.
- Material loading reuses cached MDL materials and shared shader translations more effectively; equivalent
  MaterialX graphs retain stable cache identities.
- Reduced CPU work for static/tiled cameras and motion-history processing.
- WPM lidar reuses configuration-dependent calculations and output layouts instead of repeating them every
  frame.
- Sensor memory pools grow with workload demand instead of stopping at a fixed pool limit.
- Synthetic-data bounding-box generation reuses CUDA scratch buffers, reducing allocation overhead.
- Repeated image readbacks reuse host buffers, and segmentation-output transfers are batched before frame
  completion.
- Memory profiling distinguishes sensor types and SPG graphs, nodes, and retained output history.
- Film-grain noise uses an integer hash for more consistent results across GPU backends and drivers.
- Multi-GPU rendering works when either real-time or path-tracing multi-GPU mode is enabled. Automatic
  RenderProduct placement uses all active GPUs while preserving explicit device assignments.
- Motion BVH configuration is independent per renderer; creating one renderer no longer changes another
  renderer's motion policy.
- Shader execution reordering is disabled for renderers that can activate Motion BVH, working around GPU
  stalls in multi-rate rendering.
- Editing constant primvars on non-streamed static meshes avoids rebuilding the geometry as an animated mesh.
- CUDA-shared textures and buffers remain available for pool reuse longer, reducing allocation churn during
  repeated rendering.
- GPU transform updates batch contiguous copies and avoid a CPU readback, reducing update overhead in large
  cloned scenes.
- Spectral rendering precomputes constant-color conversions and avoids an unnecessary color-conversion round
  trip in fog.
- Render-mode schema tokens now match `RealTimePathTracing`, `PathTracing`, and `MinimalRendering`. Historical
  spellings remain accepted.
- Nonvisual sensors report CUDA and cuFFT failures through renderer logging, with repeated errors
  rate-limited.
- Improved ray-origin offsets reduce self-intersection artifacts.

### Deprecated

- The `omni:rtx:viewTile:renderHistoryReset:*` attributes are deprecated; use `ovrtx_clear_history()` with a
  tile list.
- SPG `slang.dispatch()` and `{ offset, order, stride }` matrix layouts are deprecated; use `slang.compute()`
  and `{ offset, strides }`.

### Fixed

- Large buffer uploads, including per-tile parameters for RenderProducts with many view tiles, use pooled GPU
  memory instead of allocating and freeing dedicated memory every frame. (NVBug 7056209)
- In multi-tick mode, motion vectors are marked invalid when a low-rate camera's previous frame is older than
  the retained transform history, instead of incorrectly reporting near-zero motion. (NVBug 7053867)
- On Windows, processes running under a network logon, such as a service, no longer hang during shutdown.
  (NVBug 6856431)
- File logging honors the renderer's configured severity level. (NVBug 7005387)
- Log callbacks preserve channel names, filenames, and other string metadata when messages are queued
  concurrently. (NVBug 7032664)
- An unwritable log destination disables file logging with a warning instead of buffering messages
  indefinitely; sensor configuration no longer emits an INFO message every step. (NVBug 7057945)
- Renderer-creation errors retain the underlying initialization failure and available dependency-version
  details in C/Python errors and logs. (NVBug 6937410)
- Releasing render results frees their per-product metadata, preventing host-memory growth during repeated
  rendering. (NVBug 7051463)
- Selecting only GPU 0 no longer initializes and allocates memory on an unused second GPU. (NVBug 7042020)
- Concurrent render-result release and RenderVar mapping no longer crash; existing mappings remain valid until
  unmapped. (NVBug 5953350)
- Reset and detach synchronize with attached-stage updates; attach/detach reject pending renderer operations
  without modifying state. Detaching preserves caller-owned USD payloads.
- Python `fetch()` no longer consumes a result when `timeout_ns` has an invalid type, allowing a corrected
  retry. (NVBug 6931476)
- Python prim-path decoding handles paths deeper than 64 components. (NVBug 6853427)
- Creating ovstage before ovrtx no longer leaves incompatible Hydra scene-index emulation enabled. (NVBug
  6881657)
- Process exit no longer attempts GPU teardown through exit hooks, avoiding crashes after renderer destruction
  without `ovrtx_shutdown()`. Late Python finalizers no longer call into a shut-down runtime. (NVBug 6904601)
- The configured first-frame quality frame count is honored.
- Lidar scan history and accumulated tick metadata survive render-quality retries without missing scheduled
  captures.
- Invalid initial Core lidar configurations report an error and produce no output until corrected. (NVBug
  6978799)
- Gaussian-beam lidar measurements no longer have a range bias at grazing angles. (NVBug 6897288)
- Radar validates configuration before applying complete runtime updates, rejects invalid scan/waveform
  settings, suppresses zero-gain detections, and marks empty-scan placeholders invalid. Antenna and
  hit-geometry defaults are corrected. (NVBug 6876483, 6876521, 6876604, 6876629)
- Acoustic sensors with interference enabled honor the authored sample duration and readout stride, correcting
  echo-distance measurements. (NVBug 6876541)
- Nonvisual sensor motion is updated only for valid time steps, preventing incorrect motion during repeated
  quality renders. (NVBug 5967822)
- Live mesh primvar edits render in the same step as GPU position updates, including displaced meshes. (NVBug
  6289420)
- CUDA-deformed meshes attached through ovstage produce `TargetMotionSD` on their first deforming frame.
  (NVBug 6970978)
- PointInstancer instances continue moving when GPU transform updates are enabled. (NVBug 6974092)
- GPU transform propagation supports more than 2^20 prims sharing an attribute layout; failures report an
  error and fall back to CPU propagation instead of leaving CUDA error 700.
- Transforms update correctly when simulation time is paused.
- Unchanged transform updates no longer keep retired motion history dirty and cause repeated per-frame
  processing. (NVBug 6942528)
- Scene-partition geometry remains visible after renderer reset. (NVBug 6932534)
- Lights no longer leak into unrelated scene partitions when the partition limit is exceeded. (NVBug 6594502)
- Meshes removed and re-added while geometry is streaming reload correctly instead of remaining invisible.
  (NVBug 6441596)
- Selection outlines assigned before the first render appear on that first frame. (NVBug 6925441)
- Inclusive area picking handles selection-rectangle offsets and fully enclosed gizmos correctly. (NVBug
  6312141)
- 3D bounding boxes update from deformed/skinned geometry instead of retaining undeformed bounds. (NVBug
  5839835)
- Empty bounding-box outputs report zero valid records. (NVBug 6704813)
- Gaussian segmentation in Minimal SDG modes 0–2 matches rendered geometry and bounding boxes. (NVBug 6943411)
- Gaussian `cameraDistance` sorting uses distance from the camera rather than projection onto the ray. (NVBug
  6895968)
- Invalid Gaussian positions are prevented from propagating NaN/Inf values into acceleration-structure
  updates. (NVBug 6681242)
- OpenCV fisheye cameras compute the correct automatic field of view for circular lenses instead of rendering
  a tiny disc or no image. (NVBug 6925711)
- RenderProduct-authored `omni:rtx:dlssnr:*` settings take effect. (NVBug 6963166)
- RTX Minimal reads the connected metallic and roughness texture channels in `UsdPreviewSurface`, fixing black
  surfaces with packed ORM textures. (NVBug 6938664)
- RTX Minimal's fallback camera light no longer lets geometry behind the camera cast unwanted shadows onto
  visible objects. (NVBug 6943722)
- Luminance calculations use the correct BT.709 weights for linear RGB, correcting brightness-dependent
  rendering and filtering.
- Path Tracing continues accumulating for static orthographic cameras and when other sensors skip scene
  updates in multi-tick mode.
- The Path Tracing volume AOV is denoised when AOV denoising is enabled. (NVBug 6901590)
- Oversized path-tracing buffers fail with a clear error instead of silently producing black camera views.
  (NVBug 6925535)
- Retiring or resizing a render view releases its OptiX denoiser buffers, reducing retained GPU memory. (NVBug
  6944828)
- OptiX denoiser initialization completes before use, and DLSS reconstruction retains the
  subsurface-scattering albedo guide.
- Assigning a new material while editing the previous material no longer prevents the new material from
  appearing. (NVBug 6561483)
- Cached remote MDL materials resolve relative textures against the current asset rather than reusing another
  asset's location. (NVBug 6834966)
- Different textures inside the same USDZ package no longer collide in the texture cache.
- Asynchronous material/texture completion and rapid material reloads retain their owners safely, preventing
  teardown and reload crashes.
- Cancelled material loads clear their loading state instead of leaving rendering waiting indefinitely. (NVBug
  6982223)
- Displacement-enabled materials no longer reuse shader-cache results generated with displacement disabled.
- Linux packaged video textures load the correct GLib libraries; HTTPS snapshot videos resolve correctly, and
  decoder shutdown retains in-flight tasks safely.
- HTTP(S) OCIO configurations and their LUTs load through the asset client.
- Texture transitions and background streaming uploads remain correctly ordered across render operations and
  viewport lifetimes, preventing GPU synchronization failures. (NVBug 6440987, 6640350)
- GPU resource retirement and shader-cache shutdown wait for outstanding work, preventing premature resource
  destruction.
- Streaming and shader-loading waits avoid worker starvation, false cold-start timeouts, and repeated geometry
  load/drop cycles.
- Large instanced scenes no longer hang while recording instances concurrently.
- Failed NVENC initialization no longer double-destroys the encoder session and crashes during teardown.
- Fractional `targetQuality` values are honored in `TargetQuality` rate-control mode for H.264 and HEVC.
- H.264, HEVC, and AV1 streams carry color-description metadata, correcting shifted colors in video players
  that previously guessed the color conversion. Encoded image samples are unchanged. (NVBug 6898797)
- Compressed streams restart with an independently decodable frame after reset, detach, borrow-mode
  attachment, or a step that omits the compressed output. (NVBug 6901683)
- Compression honors the requested one-pass or two-pass mode set by `ovrtx:compression:multiPassMode`.
  (NVBug 6898796)
- RenderVar mapping errors identify the render product and RenderVar once the output handle has been resolved.
  (NVBug 6898795)
- SPG state is isolated per renderer, preventing cross-renderer interference and empty outputs from additional
  renderer instances.
- SPG correctly passes 64-bit integers, small numeric types, vectors, arrays, and matrices to CUDA/Slang.
  Invalid or unsupported arguments fail explicitly instead of silently shifting or corrupting kernel
  arguments.
- SPG previous-frame reads return the correct frame, including across GPUs. Empty arrays no longer stop
  graphs, and oversized node outputs no longer write beyond their AOV's memory.
- SPG responds to live input, connection, RenderVar source, and output-binding edits, and runs bound outputs
  only for their intended RenderProduct.
- SPG reports invalid/conflicting port bindings, preserves errors from `cuda.static` / `slang.static`, and
  retries sandbox-limited nodes when their value inputs change.
- SPG `cuda.static` and `slang.static` functions defined in launch scripts no longer consume more Lua memory
  every frame. SPG also releases cached-script and asset resources, preserves log history, and refreshes
  Fabric attribute handles after framework restart.
- SPG CUDA defaults omitted block dimensions to one; Slang reserves explicit resource slots before assigning
  implicit bindings.
- Downsampled dome maps average all covered texels, avoiding missed bright details in approximate image-based
  lighting.
- Multi-tick rendering preserves absolute simulation time for effects such as Flow. (NVBug 6225263)
- Eco mode continues rendering when GPU-authored transforms change. (NVBug 6887809)
- Stages containing instanceable Materials no longer abort on the first frame when populated with a selector
  description; unsupported Material instances are ignored. (NVBug 7033822)
- Point particles with matching velocities move correctly between time samples instead of stopping or
  collapsing when point counts or ordering change, correcting sub-frame motion blur. (NVBug 7009351)
- Fabric-backed meshes recover texture-coordinate roles from matching USD declarations, preventing the wrong
  UV set from being used. (NVBug 6893785)
- Runtime/video-texture scenes and scenes without texture streaming bind valid texture metadata, preventing
  GPU faults during normal-map sampling.
- Stochastic cutout and volume sampling use screen-pixel seeds so changing the GPU count does not change a
  pixel's random sampling pattern.
- A step whose renderer produces no results reports failure instead of silently succeeding, including
  oversized tiled-rendering buffers.
- Ray tracing renders the correct surviving instances when element-array acceleration-structure inputs are
  compacted after culling.
- Linux OpenGL interop preserves vendor-neutral dispatch when probing GLX vendors, preventing headless EGL
  rendering from resolving the wrong driver's GL functions.
- Remote driver shader caching works independently of UJITSO cache selection, avoiding unexpected local-cache
  fallback and slow startup.
- Changing a persistent RenderProduct's resolution, camera, or viewport identity releases the old view's GPU
  resources. (NVBug 6818689)
- Resuming color rendering after Minimal mode 0 or explicit color disable resets incomplete temporal history,
  preventing GPU stalls.
- Attached-stage rendering uses completed scene writes and current instance mappings. Procedural geometry
  retains previous positions, and finite lights remain visible across Motion BVH transitions.
- GPU-skinned bounding boxes remain complete during initialization and after mesh visibility changes.
- Requesting individual first-bounce normal or diffuse Path Tracing outputs no longer writes to unallocated
  guide buffers.
- Alpha-mask composition binds safe defaults for omitted matte, translucency, and background inputs,
  preventing GPU page faults.
- Shader recompilation releases reflection and compiler-session resources correctly, reducing leaks during
  repeated compilation. (NVBug 6852487)
- SPG graphs remain discoverable when ovstage population selectors are used, preventing empty outputs.
- Geometry CUDA-buffer lookup checks subsequent GPUs correctly instead of hanging when the first device has no
  CUDA pointer.
- Coarse mesh levels of detail generated on Linux ARM64 match the intended decimation results.
- Approximate image-based lighting avoids reading an absent ambient-occlusion buffer, preventing device loss
  when GPU systems are reused.
- Existing RenderProduct and RenderVar prims authored outside `/Render` are no longer automatically hidden by
  the renderer. (NVBug 6449704)

### Security

- Updated the bundled stb image decoder to address crashes caused by malicious image files. (NVBug 6926678)
- Updated bundled asset/networking, volume, and video dependencies with security fixes. (NVBug 6907330,
  6959770)

### Known Issues

- Enabling `omni:rtx:scenePartitioning:showAllPartitionsByDefault` can expose geometry from other
  environments to cameras assigned to a scene partition, even when the environments do not overlap.
  Leave it disabled when partition isolation is required. Neural-reconstruction volumes are not
  isolated by partition assignments with either value.
  See [Scene Partitions](https://nvidia-omniverse.github.io/ovrtx/0.7.0/sensors/cameras/scene_partitions.html#viewing-all-partitions).
- On Linux, a process that exits (returns from `main` or calls `exit()`) while a step or other operation is
  still running, without destroying its renderers or calling `ovrtx_shutdown()`, can crash or corrupt its heap
  during exit. Destroy every renderer and call `ovrtx_shutdown()` before exiting, as described in
  [Process Exit](https://nvidia-omniverse.github.io/ovrtx/0.7.0/core/application_flow.html#process-exit); in
  Python, call `Renderer.destroy()`. If that is not possible, wait for outstanding operations to complete
  before exiting. (NVBug 7057906)

## [0.6.0] - 2026-10-13

### Added

- Added experimental support for [DLSS 5 Neural Rendering](https://nvidia-omniverse.github.io/ovrtx/sensors/cameras/render_modes/dlss_nr.html) on Windows only. Note that DLSS 5 requires unsupported driver
  615.64+
- The location where ovrtx writes its runtime caches now defaults to `$XDG_CACHE_HOME` or `$HOME/.cache` on Linux, and
  `%LOCALAPPDATA%` on Windows. This location can also be configured. See [Cache
  Locations](https://nvidia-omniverse.github.io/ovrtx/core/renderer_configuration.html#cache-locations).
- Path Tracing mode now supports [spectral rendering](https://nvidia-omniverse.github.io/ovrtx/sensors/cameras/render_modes/spectral_rendering.html). Spectral path tracing startup configuration through Python
  [`RendererConfig.enable_spectral_rendering`](https://nvidia-omniverse.github.io/ovrtx/python_api/index.html#ovrtx.RendererConfig.enable_spectral_rendering) and C [`OVRTX_CONFIG_ENABLE_SPECTRAL_RENDERING`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#c.ovrtx_config_bool_t.OVRTX_CONFIG_ENABLE_SPECTRAL_RENDERING).
- Path Tracing mode now supports [Light Path Expressions (LPEs)](https://nvidia-omniverse.github.io/ovrtx/sensors/cameras/light_path_expressions.html). LPEs enable creating custom outputs that select specific
  paths from the light transport integral, for debugging and compositing applications.
- Setting `omni:rtx:scene:useSimulationTime` on a render product makes its temporal
  effects, such as auto exposure, follow that sensor's own render time, based on the [`delta_time`](https://nvidia-omniverse.github.io/ovrtx/python_api/index.html#ovrtx.Renderer.step) passed to the step.
  Off by default.
- Add Python [`RendererConfig.enable_crash_reporter`](https://nvidia-omniverse.github.io/ovrtx/python_api/index.html#ovrtx.RendererConfig.enable_crash_reporter) and C [`OVRTX_CONFIG_ENABLE_CRASH_REPORTER`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#c.ovrtx_config_bool_t.OVRTX_CONFIG_ENABLE_CRASH_REPORTER) /
  [`ovrtx_config_entry_enable_crash_reporter()`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#c.ovrtx_config_entry_enable_crash_reporter). A host application that owns crash handling sets it to false
  on the first renderer so ovrtx installs no crash handlers and uploads no dumps. Enabled when omitted.
- [`OVRTX_SEMANTIC_MATRIX`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#c.ovrtx_attribute_semantic_t.OVRTX_SEMANTIC_MATRIX) / Python [`Semantic.MATRIX`](https://nvidia-omniverse.github.io/ovrtx/python_api/index.html#ovrtx.Semantic.MATRIX) represents generic 2x2, 3x3, or 4x4 double matrices
  independently of transform semantics.
- Add [C](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#c.ovrtx_config_entry_enable_mdl_displacement) and [Python](https://nvidia-omniverse.github.io/ovrtx/python_api/index.html#ovrtx.RendererConfig.enable_mdl_displacement) renderer configuration for MDL material displacement. Displacement is disabled when the
  option is omitted.
- Add public [`RendererConfig.enable_minimal`](https://nvidia-omniverse.github.io/ovrtx/python_api/index.html#ovrtx.RendererConfig.enable_minimal), [`enable_realtimepathtracing`](https://nvidia-omniverse.github.io/ovrtx/python_api/index.html#ovrtx.RendererConfig.enable_realtimepathtracing), and [`enable_pathtracing`](https://nvidia-omniverse.github.io/ovrtx/python_api/index.html#ovrtx.RendererConfig.enable_pathtracing) options
  with corresponding C keys and helpers to choose the available modes when the first ovrtx renderer instance is created,
  reducing GPU memory use and startup work.
- Add [C](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#c.ovrtx_get_config) and [Python readback](https://nvidia-omniverse.github.io/ovrtx/python_api/index.html#ovrtx.Renderer.config) for the explicit configuration used to create a renderer.
- Complete build identity is now embedded in ovrtx binaries and packages, logged at renderer startup, and
  attached to crash reports. Native callers can query it with [`ovrtx_get_build_info()`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#c.ovrtx_get_build_info); after renderer
  initialization, Python callers can use [`ovrtx.get_build_info()`](https://nvidia-omniverse.github.io/ovrtx/python_api/index.html#ovrtx.get_build_info) or [`Renderer.build_info`](https://nvidia-omniverse.github.io/ovrtx/python_api/index.html#ovrtx.Renderer.build_info).
- Radar [`PointCloud`](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/outputs.html) outputs now expose the CPU-resident scan metadata params [`sensorID`](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/outputs.html#sensors-nonvisual-radar-outputs-scan-params), [`scanIdx`](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/outputs.html#sensors-nonvisual-radar-outputs-scan-params),
  [`cycleCnt`](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/outputs.html#sensors-nonvisual-radar-outputs-scan-params), [`maxRangeM`](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/outputs.html#sensors-nonvisual-radar-outputs-scan-params), [`minVelMps`](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/outputs.html#sensors-nonvisual-radar-outputs-scan-params), [`maxVelMps`](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/outputs.html#sensors-nonvisual-radar-outputs-scan-params), [`minAzRad`](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/outputs.html#sensors-nonvisual-radar-outputs-scan-params), [`maxAzRad`](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/outputs.html#sensors-nonvisual-radar-outputs-scan-params), [`minElRad`](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/outputs.html#sensors-nonvisual-radar-outputs-scan-params), and [`maxElRad`](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/radar_wpm_dmat/outputs.html#sensors-nonvisual-radar-outputs-scan-params).
- Each render product's outputs now signal readiness as soon as that render product finishes, instead of
  waiting for the whole step. Render products with the same start time keep the order in which the caller
  added them.
- A render product can now hold several sensor render variables with the same source name and different
  channel lists.
- SPG Lua launch scripts can read current-frame prim attributes and transforms through read-only tables for
  render products, cameras, render variables, or arbitrary paths.
- SPG accepts USD `uchar[]` value inputs.
- New documentation and tested examples: Gaussian splats; USD plugin paths and schema registration; spectral
  rendering; cameras (lens calibration, rolling shutter, scene partitions, and USD camera attributes); light
  path expressions; light controls; pick query flags; multi-rate sensors and observer cameras; acoustic
  sensors; hardware and driver requirements; RTX Minimal anti-aliasing and DLSS; decals; G-buffer debug views;
  reading simulation timestamps from step results; and C API handle lifetime, invalid-handle behavior, and
  log-callback context lifetime. SPG diagrams in the published documentation now display as images.
- Expanded camera sensor SPG processing with photon estimation, HDR noise, YCbCr/MJPEG encoding, CFA-to-MIPI
  conversion, and embedded-line generation and splicing.

### Changed

- **Breaking (C and Python):** compatibility attribute reads now return scalar-lane tensors with explicit
  component dimensions, such as `[N,3]` for vectors and `[N,4,4]` for 4x4 matrices, instead of `[N]` with 3 or
  16 lanes. This also applies to array value tensors. Update raw tensor shape, stride, and byte-count handling
  to include every dimension. Generic 16-component tuples remain `[N,16]`; MATRIX semantics identify square
  matrices. Returned attribute maps use the same scalar-lane component axes: scalars `[N]`, tuples `[N,C]`,
  and square MATRIX values `[N,S,S]` for S=2,3,4. Update raw dtype, rank, and row-stride checks as well.
  Binding creation dtypes and canonical write inputs retain their multi-lane layout; unmap ownership and
  synchronization are unchanged. Rendered output tensors keep their existing layout.
- **Breaking:** Animation time is now permanently the accumulated simulation clock built from [`ovrtx_step`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#c.ovrtx_step) /
  [`ovrtx_step_with_stage`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#c.ovrtx_step_with_stage) deltas, for every stage. Anything driven by animation time (MDL
  `state::animation_time()`, video texture frame selection, animated NuRec volumes and Gaussian splats)
  advances with the step delta.
- **Breaking:** lidar point-cloud [`ChannelId`](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/lidar_core/outputs.html#sensors-nonvisual-lidar-core-outputs-identity) now reports the channel IDs authored in the sensor profile.
  Default profiles report 1 to N instead of 0 to N-1, and sparse channel numbering is supported.
- **Breaking:** acoustic sensors now publish one composite [`SignalWays`](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/acoustic_wpm/outputs.html#sensors-nonvisual-acoustic-outputs-requesting) output, matching lidar and radar point
  clouds. Previously each channel was a separate untyped output.
- **Breaking:** the camera sensor attribute `omni:sensor:core:colorFilterArrayMaximalValue` is now `float`
  instead of `int`. Re-author assets that set it as `int`.
- **Breaking (C):** logging APIs now live in [`<ovrtx/ovrtx_logging.h>`](https://nvidia-omniverse.github.io/ovrtx/c_api/practical_patterns.html#logging-callback) and use [`ovx_log_severity_t`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#logging-types) /
  [`OVX_LOG_*`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#logging-types) and [`ovx_log_callback_t`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#logging-types). Callbacks receive an [`ovx_log_message_t`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#logging-types) containing message text,
  nanosecond timestamps, channel, and source metadata instead of separate severity, timestamp, and text
  arguments. Update callback signatures and recompile.
- Auto exposure, temporal anti-aliasing, and DLSS now advance by the simulation step time instead of
  wall-clock time, so brightness adaptation is repeatable across runs and machines.
- The Gaussian splat skip-tonemapping option now works in path tracing and RTX Minimal as well as real-time
  path tracing, using `omni:rtx:gaussian:skipTonemapping:enabled`.
- Default physical illuminant resampling to the existing 1 nm mode instead of 5 nm, preserving finer spectral
  features without changing interpolation or buffer layout.
- ovrtx 0.6 attached mode requires ovstage 0.3.x. [`ovrtx_attach_ovstage()`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#c.ovrtx_attach_ovstage) now rejects incompatible ovstage
  versions before attaching. OVStage 0.3 defaults to `NONDECREASING` ordinal admission: mutations older than
  retained changes can be rejected even if they clear write floors; equal ordinals remain allowed. See
  [OVStage integration](https://nvidia-omniverse.github.io/ovrtx/core/ovstage_integration.html#ovstage-ordinal-admission)
  for migration guidance.
- Installed wheels now report their complete distribution version, including the build number, through
  [`ovrtx.__version__`](https://nvidia-omniverse.github.io/ovrtx/python_api/index.html#ovrtx.__version__); source checkouts continue to report the semantic version, and the native
  [`ovrtx_get_version()`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#c.ovrtx_get_version) / [`Renderer.version`](https://nvidia-omniverse.github.io/ovrtx/python_api/index.html#ovrtx.Renderer.version) compatibility contract is unchanged.
- On Windows, the loader opens the ovrtx runtime library with a restricted DLL search (the library's own
  directory, the package dependency directories, and System32) instead of the inherited `PATH`, so an
  unrelated DLL on the host's `PATH` can no longer replace a packaged dependency.
- The Linux ARM64 package is smaller: debug symbols are stripped from bundled third-party libraries.
- Sensor model revisions now count from `0` within each schema version. Use a supported integer revision,
  including `"0"`, or `"latest"` in `omni:sensor:modelVersion`; malformed, unsupported, and runtime-changing
  requests remain rejected.
- Section planes no longer remove lights. New `omni:rtx:scene:sectionPlane:preserveSectionedLighting`
  preserves shadows, bounce light, and reflections from clipped geometry when enabled; it defaults to false.
- Identical streamed texture mip data now shares GPU allocations, reducing memory use and duplicate uploads
  even when textures use different file paths.
- Reduced RTX Minimal GPU memory use by reusing eligible color-output buffers and avoiding redundant full-size
  intermediate images.
- The supported number of lights is raised from 8,192 to more than 16 million.

### Deprecated

- The `uniform` anti-aliasing sample pattern is deprecated and now renders as `box`.
- The old Gaussian splat skip-tonemapping attribute is deprecated. Use
  `omni:rtx:gaussian:skipTonemapping:enabled`; the previous name remains supported.
- The section-plane `sectionLight` option is deprecated and ignored. Use
  `omni:rtx:scene:sectionPlane:preserveSectionedLighting` to preserve lighting from clipped geometry.

### Fixed

- Renderer initialization failures (GPU Foundation, CUDA runtime, UJITSO, Hydra engine, static plugin
  registration) now fail [`ovrtx_create_renderer()`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#c.ovrtx_create_renderer) / [`Renderer()`](https://nvidia-omniverse.github.io/ovrtx/python_api/index.html#ovrtx.Renderer) with an error instead of terminating the
  host process.
- Python [`Semantic.MATRIX`](https://nvidia-omniverse.github.io/ovrtx/python_api/index.html#ovrtx.Semantic.MATRIX) writes accept NumPy 2x2, 3x3, and 4x4 double matrices. Persistent bindings accept
  matching scalar-lane NumPy input and preserve an explicit float64 dtype with 4, 9, or 16 components; their
  mapped Python views expose the corresponding square shape. A binding without an explicit component count
  defaults to 4x4, and transform semantics remain 4x4. Mismatched matrix sizes and scalar types are rejected.
- [`Depth`](https://nvidia-omniverse.github.io/ovrtx/sensors/cameras/outputs.html) D32 outputs support direct CUDA array mapping on Vulkan and DX12 without intermediate textures or
  pixel copies. Linear CUDA-buffer mappings use the existing device-to-device copy path. Device-depth values
  and explicit CPU mappings are preserved.
- Prevent the startup GPU diagnostic subprocess from opening a console window in Windows GUI applications.
- ovrtx now links a private, hidden-visibility copy of ImGui into the runtime library instead of depending on
  a shared `libimgui.so` / `imgui.dll`, and the package no longer ships
  `bin/plugins/renderer.imgui/libimgui.so` / `imgui.dll`. A host process that loads its own ImGui under the
  same name no longer shares one copy with ovrtx: previously, whichever loaded first was used by both, so the
  host could fail with undefined ImGui symbols or ovrtx could run against an ImGui with a different ABI.
- Failed internal assertions inside the ovrtx shared library no longer open a modal dialog on Windows. A
  failed check in a headless process (CI, embedded hosts) previously blocked on the dialog until the process
  was killed. An attached debugger still breaks on the assertion.
- [`step()`](https://nvidia-omniverse.github.io/ovrtx/python_api/index.html#ovrtx.Renderer.step) no longer hangs when progressive geometry loading reaches its memory or instance budget.
- Fixed hangs when two or more renderers run in the same process, on the first step with an attached stage and
  while waiting on geometry streaming status.
- An idle renderer no longer exhausts rendering resources shared with other renderers in the same process.
- Multiple renderers in the same process using camera or depth-sensor processing no longer interfere with each
  other.
- Fixed GPU memory growth when render products without a viewport share a camera and resolution.
- Fixed GPU memory growth when render products using DLSS are repeatedly created and destroyed.
- [`ovrtx_attach_ovstage()`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#c.ovrtx_attach_ovstage) now retains its own stage handle, so destroying the caller's handle while the
  renderer remains attached is safe. The documentation now states that [`ovrtx_attach_ovstage()`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#c.ovrtx_attach_ovstage) and
  [`ovrtx_detach_ovstage()`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#c.ovrtx_detach_ovstage) rebuild renderer state on the calling thread, so previously enqueued operations
  must be waited for with [`ovrtx_wait_op()`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#c.ovrtx_wait_op) first. An [`ovrtx_wait_op()`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#c.ovrtx_wait_op) timeout does not cancel an operation,
  so a timed-out wait is not sufficient. After a detach failure, do not use the renderer except to destroy it.
- [`ovrtx_reset()`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#c.ovrtx_reset) now discards all accumulated rendering history, as documented. Previously the path tracer's
  radiance cache, the Flow simulation and the frame number that sampling sequences depend on survived it, so a
  renderer rendered differently after a reset than a newly created one.
- On multi-GPU systems, a render product added after [`ovrtx_reset()`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#c.ovrtx_reset) now renders on the GPU a new renderer
  would choose, instead of the next GPU in the automatic assignment.
- A REPLICATE-attached renderer now drops a prim's type, applied-schema and ancestor-type tags when the stage
  deletes `usd-prim-type`, `usd-schemas` or `usd-ancestor-types`, as a BORROW-attached renderer does.
  Previously a prim that a live USD edit left typeless kept its old type and ancestor types under REPLICATE
  only.
- `path_dictionary_create_paths_from_tokens()` now constructs absolute paths, matching ovstage and returning
  the same handle as the equivalent absolute string path within the same dictionary. Zero-component paths now
  resolve to `/`. Previously, component paths omitted the leading `/` and could identify a different prim.
- The deprecated [`ovrtx_clone_usd`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#c.ovrtx_clone_usd) / [`Renderer.clone_usd`](https://nvidia-omniverse.github.io/ovrtx/python_api/index.html#ovrtx.Renderer.clone_usd) now reject a missing source and any already-existing
  target path before mutating the stage, and the per-operation error names the offending path(s), e.g.
  `ovrtx_clone_usd: target prim already exists at '/Tile3'`. Previously the operation reported success while
  cloning over the existing prim, or created empty prims when the source did not exist.
- An attached renderer no longer returns frames for render products that have been removed from the stage.
- CUDA-backed `UsdGeomPoints` buffers now resize correctly after an ovstage stage is attached.
- Cloned geometry is shared during initial streaming, so scenes with many cloned environments no longer use
  excess GPU memory.
- Fixed intermittent heap corruption and crashes in the shader cache.
- The package now includes all required USD schema plugins.
- [`OVRTX_PICK_FLAG_INCLUDE_TRACKED_INFO`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#c.OVRTX_PICK_FLAG_INCLUDE_TRACKED_INFO) now returns tracked metadata in pick results.
- Python: a rejected [`step()`](https://nvidia-omniverse.github.io/ovrtx/python_api/index.html#ovrtx.Renderer.step), for example one with an invalid render product path, no longer re-raises its
  error on the next valid step or reset, and no longer reports leaked step outputs.
- Python: renderer teardown at interpreter exit no longer prints a false cleanup warning.
- Lidar: scan start time and pose are kept across simulation steps.
- Lidar: solid-state beams with Gaussian or uniform ray types return points.
- Lidar: rotary scans are no longer empty at certain frame rates.
- Lidar: hit normals are transformed into the output frame.
- Lidar: motion-compensated points from moving sensors line up with the scene geometry.
- Lidar: completed scans report scan-level pose and timestamps.
- Lidar: point-cloud outputs report the correct scan timestamp and compaction type.
- Changing parameters on a running sensor no longer resets its scan or frame counter, and reconfiguring or
  removing sensors while frames are in flight no longer crashes.
- Fixed a heap overflow when RTX sensor materials use paint variants.
- [`DistanceToCamera`](https://nvidia-omniverse.github.io/ovrtx/sensors/cameras/outputs.html) is now correct for lat-long, fisheye and other non-pinhole cameras.
- Instanced meshes no longer disappear in multi-rate rendering with motion BVH enabled.
- Gaussian splats now render in RTX Minimal on GPUs without inline ray tracing.
- Fixed Gaussian splat white-strip artifacts with tiled cameras, depth-of-field artifacts when tone mapping is
  skipped, and incorrect rendering of particle fields with array attributes, spherical-harmonic data or empty
  positions.
- Reduced shadow flicker on Gaussian splats lit by several lights.
- Cylinder lights with IES profiles now reach their target photometric power.
- Fixed artifacts on the back faces of area lights in RTX Minimal.
- Path tracing handles transmissive objects consistently when a path reaches its bounce limit.
- Corrected fast-refraction shadow brightness with spectral rendering.
- Path tracing [`PtPreDenoisedResult`](https://nvidia-omniverse.github.io/ovrtx/sensors/cameras/outputs.html) output is no longer denoised, and Multi-Matte outputs now produce correct
  geometry and material masks.
- Stable-ID outputs now include all IDs, including geometry that loads after the first frames.
- Curves whose widths start empty and are filled in later now render at the correct width.
- Fixed decal shadows crashing the shader compiler on some drivers.
- Fixed possible heap corruption in the material system on Linux ARM64.
- Cloning a subtree that contains scene-graph instances whose prototype has an intermediate prim between the
  instance root and its geometry (for example a link-level `instanceable` group above the meshes) now keeps
  the cloned instance proxies attached to their rebased hierarchy parent. They were attached to their literal
  path parent, which is not a prim in that layout, so they kept the source's world transform and every clone
  rendered on top of the source ([`ovrtx_clone_usd`](https://nvidia-omniverse.github.io/ovrtx/c_api/index.html#c.ovrtx_clone_usd) / [`Renderer.clone_usd`](https://nvidia-omniverse.github.io/ovrtx/python_api/index.html#ovrtx.Renderer.clone_usd), and `ovstage_clone` with an
  attached stage). A clone whose destination parent is not a prim now hangs under the nearest existing
  ancestor, as population does for an instance proxy whose intermediate ancestors are not populated, instead
  of being left unparented.
- Matrix-array writes preserve outer slices, including byte strides that are not a whole matrix size, and
  reject noncompact component axes explicitly.
- A renderer created without an explicit [`motion_bvh`](https://nvidia-omniverse.github.io/ovrtx/python_api/index.html#ovrtx.RendererConfig.motion_bvh) option now restores the process defaults instead of
  inheriting a previous renderer's Motion BVH override.
- Linux ovrtx runtime and rendering plugins now hide internal symbols, reducing symbol collisions with
  libraries loaded by the host application.
- Linux OpenGL interop now falls back safely to device EGL when GLX is unavailable or fails, including
  headless systems, and preserves shared EGL displays while other contexts still use them.
- Rotary lidar partial captures retain their requested interval when crossing a scan boundary.
- Instant solid-state lidar samples the requested endpoint time and pose instead of treating the flash as a
  swept interval.
- Idealized lidar multi-return outputs now report each return's [`EchoId`](https://nvidia-omniverse.github.io/ovrtx/sensors/nonvisual/lidar_core/outputs.html#sensors-nonvisual-lidar-core-outputs-identity) instead of zero for every return.
- Fixed invalid factor-8 tiled subsampling schedules in WPM lidar.
- Lidar atmospheric and solar settings apply consistently across frames, and live sun-direction or irradiance
  changes take effect without changing the aerosol model.
- Invalid lidar and radar sensor parameters now produce error diagnostics.
- Fixed OpenPBR material loading at startup when shader inputs have both a connection and an authored fallback
  value.
- Fixed shadow-terminator artifacts on hard surfaces in RTX Minimal.
- Corrected spectral texture sampling for cameras with custom spectral responsivity, and improved spectral
  subsurface-scattering compatibility with RGB rendering.
- Fixed random-sampling seed collisions and repeated material sampling dimensions that could introduce
  correlations in path-traced and subsurface-scattering images.
- Animated Gaussian splat bounds now update on the GPU so moving splats remain correctly bounded.
- A syntax error in an SPG Lua script now fails only its node instead of terminating the process.

### Security

- **Breaking:** SPG Lua scripts now run under enforced limits: 1 million instructions per load or launch, 64
  KB of log output per call, and 10 MB of memory. `pcall`, `xpcall` and the string pattern functions are no
  longer available. A node whose script exceeds a limit stops until its SPG setup changes.
- Package contents are scanned for embedded credentials before the archive and the wheel are assembled, and
  the finished archive and wheel are scanned again before they are uploaded. On Linux, ELF `.comment` entries
  that embed a URL, a build path or a source-control reference (toolchain-identification strings inherited
  from prebuilt third-party components) are blanked before packaging.

## [0.5.1] - 2026-10-05

### Changed

- Increased the tiled-rendering limit to 32,768 view tiles, with memory allocated on demand.
- Added structured-radiance support for DLSS Ray Reconstruction Preset F.

### Fixed

- Fixed scene-loading hangs involving cached assets and streaming.
- Fixed motion vectors during multi-tick rendering and cutout opacity in RTX Minimal.
- Fixed missing simultaneous solid-state lidar emissions and Gaussian-splat fallback rendering.
- Fixed cloned-instance transforms, partial attribute writes, and GPU transform initialization in ovstage integration.
- Fixed MaterialX DLL conflicts on Windows.
- Updated bundled dependencies to address security vulnerabilities.

## [0.5.0] - 2026-09-03

### Highlights

- Sensor Processing Graphs (SPG) now have [much improved documentation and examples](https://nvidia-omniverse.github.io/ovrtx/spg/overview.html). SPG also adds  ["stateful nodes"](https://nvidia-omniverse.github.io/ovrtx/spg/do/state.html) - the ability to keep data across frames so that graphs can refer to previous frames' data, and  [raygen shaders](https://nvidia-omniverse.github.io/ovrtx/spg/do/raygen.html), allowing graphs to trace rays against the scene.
- [UV Projectors](https://nvidia-omniverse.github.io/ovrtx/materials/projectors.html) allow defining procedural UV texture coordinates on geometry with multiple projection modes including planar, cylindrical, spherical, and triplanar. This allows textured materials to work on assets without texture coordinate primvars. Projectors can be especially helpful for CAD data with no authored texture coordinates, and for very large scenes where texture coordinate primvars can consume a significant amount of memory.
- [Decals](https://nvidia-omniverse.github.io/ovrtx/materials/decals.html) project materials onto geometry with a projection and a bounding region. Decals can be used to add multiple layers of labels, stickers, dirt, or wear on top of existing materials without adjusting the base material or its textures.

### Added

- Python `RenderProductSetOutputs.simulation_start_time` / `simulation_end_time` expose the step simulation window from the C API. After `Renderer.reset(time=T)`, the next step reports `simulation_start_time == T`. These values are distinct from per-frame `FrameOutput.start_time` (sensor capture inside `[T, T + delta_time]`).
- RTX acoustic, radar, lidar, and IDS sensors now resolve a `{schema, model}` version at creation. The schema version comes from the applied `OmniSensorGeneric*` API (`_N` suffix, or `1` when unsuffixed), while `omni:sensor:modelVersion` accepts a supported positive integer string scoped to that schema or `"latest"`. Malformed, unsupported, and runtime-changing requests are rejected with diagnostics.
- Added `OVRTX_CONFIG_SENSORS_ALLOWED_DEPRECATION_BASE`, `ovrtx_config_entry_sensors_allowed_deprecation_base()`, and Python `RendererConfig.sensors_allowed_deprecation_base`. Soft-deprecated sensor versions remain rejected by default and are accepted only when this plain `<major>.<minor>.<patch>` value exactly matches the running OVRTX version; the opt-in must be revisited after every OVRTX upgrade.
- [SPG](https://nvidia-omniverse.github.io/ovrtx/spg/overview.html) [Slang shaders](https://nvidia-omniverse.github.io/ovrtx/spg/ref/lua_slang.html) now work on Windows (Vulkan) as well as Linux.
- [SPG](https://nvidia-omniverse.github.io/ovrtx/spg/overview.html) [Slang nodes](https://nvidia-omniverse.github.io/ovrtx/spg/ref/lua_slang.html) now have feature parity with CUDA.
- MDL can now be packaged in USDZ, including UDIM support.
- Improved multi-rate sensor rendering so moving instances, materials, and attached lights are evaluated consistently at each sensor’s capture time.
- Added missing `bool omni:rtx:post:bloom:apertureShapeCircular` to `OmniRtxPostBloomPhysicalAPI_1` to allow selecting a circular aperture for the post bloom effect.
- Added `ovrtx_get_usd_plugin_paths()`/`ovrtx.usd_plugin_paths()` to query the locations of the ovrtx schema plugins so that they can be added to an external OpenUSD.
- Added per-process control over ovrtx’s integrated Nsight Aftermath GPU-crash diagnostics, allowing applications to enable, disable, or automatically configure crash-dump generation with `ovrtx_config_entry_aftermath_mode(OVRTX_AFTERMATH_{ENABLE,DISABLE,AUTO})`/`ovrtx.RendererConfig(aftermath_mode=ovrtx.AftermathMode.{ENABLE,DISABLE,AUTO})`
- Applications can now use the settings `int omni:rtx:lights:dome:baking:resolution = 4096`, `int omni:rtx:domeLight:baking:spp = 4`, and `bool omni:rtx:lights:dome:baking:denoising:enabled = false` to control resolution, sample rate, and denoising of materials that are assigned to a dome light when they are baked to the dome light map. Note that although the settings are scoped to a `RenderProduct`, they are shared per stage. If there are multiple `RenderProducts`, they will all share the settings of the first one encountered.

### Changed

- **Breaking:** `MappedRenderVar`, `RenderVarTensor`, `RenderVarParam`, and
  `AttributeMapping` now consistently expose `shape`, `dtype`, `ndim`, `data`,
  and `device`. `device` now returns `DLDevice`. Properties on released
  mappings are unavailable after unmap.
- **Breaking:** Deprecated attribute-read APIs with a caller-provided
  destination now return that destination directly.
- **Breaking:** Renderer tensor inputs now require the standard `__dlpack__`
  protocol; raw `DLTensor` structures are no longer accepted.
- **Breaking:** Public OVRTX packages now use Vulkan exclusively on Windows. The
  Python `RendererConfig.use_vulkan` field and the C
  `OVRTX_CONFIG_USE_VULKAN` / `ovrtx_config_entry_use_vulkan()` API have
  been removed. Recompile C applications against the 0.5 headers and remove
  backend selection; pre-0.5 binaries that pass the retired key receive a clear
  `OVRTX_API_ERROR`.
- **Breaking:** `omni:sensor:modelVersion` now inherits `"latest"` from `OmniSensorAPI`. Legacy dotted values such as `"0.0.0"` are invalid; migrate authored assets to `"latest"` or a supported positive integer revision such as `"1"`.
- **Breaking:** Python `ManagedDLTensor` can no longer be constructed directly.
- **Breaking:** Previously, ovrtx identified `RenderVar`s by their `sourceName`. `RenderVar`s are now identified by their full path. For example, `frame.render_vars["/Render/Product/LdrColor"]`.
- **Breaking:** The absolute specular and transmission bounce limits have been replaced by attributes that specify additional bounces beyond `maxBounces`:
  - RTPT: `omni:rtx:rtpt:maxSpecularAndTransmissionBounces` was replaced by `omni:rtx:rtpt:extraSpecularAndTransmissiveBounces`. Legacy authored data is converted using `extraSpecularAndTransmissiveBounces = max(maxSpecularAndTransmissionBounces - maxBounces, 0)`.
  - PathTracing: `omni:rtx:pt:limits:maxGlossyBounces` was replaced by `omni:rtx:pt:limits:extraSpecularAndTransmissiveBounces`. Legacy authored data is converted using `extraSpecularAndTransmissiveBounces = max(maxGlossyBounces - maxBounces, 0)`.
- CMake model #2 now pairs `ovrtx::ovrtx` with the new ovstage shared loader
  behind `ovstage::ovstage`, so both runtimes remain deferred until API
  initialization. The C minimal example builds and checks both loader models.
- `ovrtx_set_reset_xform_stack()` now declares its payload as `{kDLBool, 8, 1}` instead of `{kDLUInt, 8, 1}`, matching the documented USD `bool` mapping. The bytes on the wire are unchanged (one byte per prim) and the helper still writes only to prims that already carry the attribute.
- Python `ManagedDLTensor.numpy()` now raises `RuntimeError` for non-CPU tensors to guard against trying to use a GPU pointer on the CPU.
- `ovrtx_register_schema_paths()` now registers ovrtx's schema families with ovstage, so an attached ovstage resolves them when it populates. Call it before ovstage's first populate.
- MDL SDK updated to 2026.0.1. This also fixes a crash observed when cold-loading some materials on ARM.
- The `DepthSD` AOV is deprecated. Use `DistanceToImagePlaneSD` or `DistanceToCameraSD` instead.
- `ovrtx` and `ovstage` now automatically apply relevant RTX schemata to `Camera` and `RenderProduct` prims, meaning applications do not need to apply these manually in order to set render settings.
- Updated the `UsdPreviewSurface` implementation to match the [OpenUSD 25.11 specification](https://openusd.org/25.11/spec_usdpreviewsurface.html#preview-surface). In particular, this adds the `opacityMode` attribute.
- Enabled native selection outlines by default. Applications can assign and style selection groups at runtime or disable the global outline pass when creating the renderer.
- Enabled multiple dome lights by default and bounded path-tracing cost by sampling at most eight dome lights per sample when scenes contain larger dome-light sets.

### Removed

- **Breaking:** Removed the renderer-wide DomeLight MDL baking resolution
  control: `OVRTX_CONFIG_DOME_BAKING_RESOLUTION`,
  `ovrtx_config_entry_dome_baking_resolution()`, and Python
  `RendererConfig.dome_baking_resolution`. Baking is now configured per
  RenderProduct, by authoring `omni:rtx:lights:dome:baking:resolution` on a
  product carrying `OmniRtxSettingsCommonAdvancedAPI_1`. Note a baked dome light
  is a scene-level resource: RTX resolves the attribute from the scene's
  reference view, so products sharing a scene must author the same value rather
  than baking that dome light differently. Recompile C applications against the
  0.5 headers; pre-0.5 binaries that pass the retired key receive a clear
  `OVRTX_API_ERROR` naming the replacement attribute.
- **Breaking:** Removed Python `ManagedDLTensor` and the deprecated
  `MappedRenderVar.tensor` property. Pass mappings and tensor views directly to
  `np.from_dlpack()` or another DLPack consumer. Use their common tensor
  properties for metadata and the consuming library for copying or
  serialization.
- **Breaking:** Removed support for the `GenericModelOutput` render var. A
  render product that requests `sourceName = "GenericModelOutput"` is skipped
  with a diagnostic. Author the composite `PointCloud` render var instead and
  read its named tensors (`Coordinates`, `Intensity`, `Counts`,
  `TimeOffsetNs`, `Flags`, `RCS`, `RadialVelocityMs`, ...). This breaks
  authored USD only; no header, symbol, or struct changed, so C applications
  need no recompile or relink.
- **Breaking:** The package no longer ships `bin/libs/sensors-gmo`, which
  contained the `GenericModelOutput` runtime, its Python extension, and HDF5.
  Consumers that still need the `GenericModelOutput` decoder should take the
  standalone `generic-model-output` package or wheel.

### Fixed

- Corrected the `Minimal` render-mode token to `MinimalRendering` in public docs and skills.
- Fixed a significant performance regression introduced between ovrtx 0.3 and 0.4 when an application mapped and processed an output on an application-owned CUDA stream.
- Significantly improved performance with `read_gpu_transforms=true` and multi-tick rendering.
- Reduced CPU overhead for tiled multi-camera rendering by caching unchanged camera transforms and skipping redundant view-tile calculations and GPU buffer uploads.
- `Renderer.step()` and `Renderer.reset()` now reject non-finite, negative, and unsupported simulation times before they reach native sensor scheduling.
- Deprecated attribute reads now reject DLPack destinations with non-zero byte offsets or non-C-contiguous layouts.
- Python DLPack exports now reliably release consumed and unconsumed versioned and unversioned tensors during normal and exceptional cleanup without replacing the active exception. Repeated `__dlpack__()` calls create independently owned exports. Foreign DLPack inputs retain producer resources until the consuming operation finishes.
- Python `DLDataType.from_str()` now validates the `lanes` override: values outside `[1, 65535]` raise `ValueError` and non-integer values raise `TypeError`, instead of silently wrapping through the underlying uint16 struct field (for example `lanes=-1` previously produced a corrupt dtype with `lanes == 65535`). DLPack export likewise rejects dtypes with `lanes == 0`.
- Fixed an issue where SPG would ignore the user-provided launch configuration.
- Reduced IndeX package size by 70 MB, reducing ovrtx package footprint and startup time.
- Fixed an unstable module identity in MaterialX UJITSO material caches, stopping redundant recompilations of the same material and reducing scene load times.
- Suppressed the C183 unused-parameter warning when compiling MaterialX materials with MDL, reducing log spam.
- Fixed an issue where ovrtx would generate malformed texture URIs for some MDL materials.
- Fixed an issue where curves would sometimes ignore primvars.
- Fixed an issue where thin-walled MaterialX materials would refract as if they were solid.
- Gaussian splats now render on A100 and H100 GPUs.
- Fixed a crash when adding the SPG camera-core AOV OmniCameraSensorPreIsp to a RenderProduct in a scene with MotionBVH enabled.
- `ManagedDLTensor` now propagates non-contiguous strides correctly.
- `ManagedDLTensor` now correctly raises `TypeError` and `BufferError` for malformed `dl_device` values and cross-device requests, respectively.
- Fixed the C API docs to correctly state that `keep_system_alive` is enabled by default.
- Fixed the Python API `Renderer` docs for `step()`, `step_async()`, `reset()` and `reset_async()` to clarify the expected value of simulation time.
- Attempts to attach more than one renderer to an `ovstage` with `ovrtx_attach_ovstage()` now correctly return an error.
- Removed unused GStreamer plugins, reducing package size.
- Fixed a crash with `BoundBox3DSD` AOV when changing the number of objects visible in the scene.
- Fixed a race condition when writing to the runtime stage from multiple threads concurrently.
- `ovrtx_step()` and `ovrtx_step_with_stage()` no longer crash when passed a `NULL` RenderProduct path. `OVRTX_API_ERROR` is returned instead.
- Fixed a rare crash with textured mesh lights in PathTracing mode.
- ovrtx headers now compile as C.
- Fixed a crash when exceeding the scene partition limit of 15625.
- Fixed an issue where `TargetMotionSD` producing zero motion vectors on the first frame.
- Fixed an issue where malformed `RendererConfig` entries could silently be coerced into incorrect accepted values.
- Fixed a rare crash when RTX generated smooth normals while processing multiple meshes in parallel.
- Fixed an issue with deformation timing in motion BVH refits for deforming geometry, correcting animated-mesh intersections for rolling-shutter and swept-sensor rendering.
- Fixed an issue where toggling visibility on instances sharing a prototype could make child instance transforms become incorrect.
- Resetting DLSS history with the `float[] omni:rtx:viewTile:renderHistoryReset:tileIndices` and `int omni:rtx:viewTile:renderHistoryReset:requestId` attributes now reliably clears temporal history, removing lingering ghosts.

## [0.4.1] - 2026-08-04

### Summary

- ovrtx 0.4.1 adds rendering configuration controls and includes rendering,
  sensor, GPU interoperability, and stability improvements.

### Highlights

- Added `OVRTX_CONFIG_TEXTURE_STREAMING_MODE` and corresponding C and Python
  APIs to select disabled, synchronous, or asynchronous texture streaming.
- `OVRTX_CONFIG_DOME_BAKING_RESOLUTION` renderer configuration control for the DomeLight MDL baking resolution (texels), with the C helper `ovrtx_config_entry_dome_baking_resolution()` and the Python `RendererConfig.dome_baking_resolution` field. Applies renderer-wide to all dome lights; valid range `1..8192` (out-of-range values are clamped). When omitted, ovrtx does not write the setting (`4096` for the first renderer in a fresh process; a value set by a prior in-process renderer or dev settings is left in place). Init-time only.
- Added `OVRTX_CONFIG_DATASTORE_CACHE` and corresponding C and Python APIs for
  local and gRPC UJITSO caches.
- Added `OVRTX_CONFIG_SUPPRESS_DEPRECATION_WARNINGS` and corresponding C and
  Python APIs to silence runtime deprecation warnings during phased migrations.
- Added per-tile render-history reset controls to reduce ghosting after camera
  changes.
- Added opt-in spectator rendering for cameras without an assigned scene
  partition.

### Notable Fixes

- Improved RTX Minimal motion output for static scenes, deforming meshes, and
  animated Points.
- Improved StableIdMap correctness and stability, restoring semantic mappings
  and preventing an `instance_segmentation_fast` crash.
- Fixed missing or incorrect transforms when GPU transform reads are enabled.
- Fixed camera targets on tiled RenderProducts cloned through ovstage.
- Improved transform updates for scene-partitioned content.
- Improved texture readiness and rendering stability by correcting texture-mip
  selection and residency handling.
- Improved rendering determinism by resetting temporal state consistently and waiting for required texture mips to finish loading.
- Fixed RTX Minimal procedural geometry.
- Improved foreground TLAS determinism for scene-partitioned content.
- Fixed GPU asynchronous writes for Points and BasisCurves.
- Fixed empty SPG AOVs in ovstage-attached workflows.
- Fixed Python CUDA interop in packaged installations.
- Prevented renderer teardown from hanging indefinitely on stalled operations.

## [0.4.0] - 2026-07-17

### Summary

- ovrtx 0.4 introduces integration with the new [ovstage](https://github.com/nvidia-omniverse/ovstage) 0.1 library. Applications can attach an externally owned ovstage instance and render its scene data.

- Existing ovrtx APIs for loading USD and reading or writing stage attributes remain available for compatibility but are deprecated and will be removed in a future release.

- This release also includes breaking C API changes, improved DLSS Ray Reconstruction quality under motion, and numerous rendering, sensor, and stability fixes.

### Highlights

- **ovstage integration**

- New C APIs support attached-stage workflows:

  - `ovrtx_attach_ovstage()` and `ovrtx_detach_ovstage()`
  - `ovrtx_step_with_stage()`
  - `ovrtx_update_from_stage()`

- While attached, ovrtx stage-building, write, and map APIs return `OVRTX_API_ERROR`. Read-only `ovrtx_query_prims()` remains available.

- **Motion BVH configuration**

- `OVRTX_CONFIG_MOTION_BVH` replaces the former Boolean option:

  - `Disable` — off and now the default
  - `Enable` — enabled when the renderer is created
  - `Auto` — enabled when required by sensors or motion-sensitive cameras

- Applications that relied on implicit auto-detection must explicitly select `Auto`.

- **Schema registration**

- Automatic registration in `PXR_PLUGINPATH_NAME` is now disabled by default. Register schemas by setting `OVRTX_PXR_SCHEMA_AUTO_REGISTER` or calling `ovrtx_register_schema_paths()` before OpenUSD initializes.

- Standalone applications using `ovrtx_initialize()` or `ovrtx_create_renderer()` continue to register paths automatically. `OVRTX_SKIP_SCHEMA_AUTO_REGISTER` has been removed.

- `ovrtx_get_usd_plugin_path_count()` and `ovrtx_get_usd_plugin_paths()` enumerate ovrtx's USD schema/plugin directories without mutating any environment variable (the Python `ovrtx.usd_plugin_paths()` forwards an explicit root via the config struct rather than the env). Enumeration and registration share one first-call-wins effective-root pin: whichever runs first pins the root, and the other warns and acts on the pinned root on mismatch, in either order.

- **Other additions**

  - NDC-based picking, pickability controls, and configurable selection outlines
  - Geometry streaming configuration
  - Rolling-shutter, RenderVar channel, physical-camera responsivity, and light-shaping schemas
  - Render Output Compression, LPE labels for AOVs, and multiple dome lights
  - Gaussian splats and scene partitioning in RTX Minimal
  - SPG output fanout, multiple descriptor sets, structured buffers, and large array inputs
  - Updated DLSS Ray Reconstruction with better quality under motion

### Breaking Changes

- All C consumers must be recompiled.

- `ovrtx_release_read_result()` now accepts the original `ovrtx_read_handle_t`.
- `ovrtx_read_map_handle_t` and `ovrtx_read_output_t::map_handle` were removed.
- Picking rectangles now use NDC coordinates.
- SPG parameters are now authored as shader inputs.
- `ovx_string_t::str` and `::len` became `::ptr` and `::length`.
- RT1 `DirectLightingSampled` and `DirectLightingLtc` modes were removed.

### Notable Fixes

- Corrected HDR color, illuminance, motion-vector, and dome-light AOV behavior
- Fixed rect, sphere, distant, and dome-light rendering issues
- Fixed OmniSurface volume coefficients
- Fixed lidar direction handling, beams-mode crashes, and mixed sensor tick-rate crashes
- Improved motion transforms, velocity estimation, and semantic-label determinism
- Fixed VRAM accounting and scene-partitioning out-of-memory failures
- Added DLPack v1.2-compliant row-major strides
- Enabled SPG by default

### Known Issues

- Known driver scheduling interaction on Linux: CUDA stream synchronization concurrent with the renderer's Vulkan work reduces throughput. Set `CUDA_DEVICE_MAX_CONNECTIONS=1` before the first CUDA context is created. Windows is unaffected. Refer to the "CUDA and Vulkan Scheduling on Linux" documentation page.
- Multi-GPU viewport picking is limited to GPU 0; set RenderProduct `deviceIds = [0]`.
- Repeated renderer creation on headless Linux may crash in `libEGL.so`. Use `keep_system_alive = true` with early `ovrtx_initialize()`, or set `VK_LOADER_DISABLE_DYNAMIC_LIBRARY_UNLOADING=1`.
- ovrtx must initialize before ovphysx.
- ovstage 0.1 does not support USD-active reads.
- The material-editor C example has not yet been migrated to ovstage or validated.

### Upgrading

- From ovrtx 0.3.x:
  1. Recompile C consumers and update read-result, picking, string, and SPG APIs.
  2. Enable schema registration explicitly if your application depends on it.
  3. Select Motion BVH `Auto` if you relied on the former implicit behavior.
  4. Migrate deprecated scene, attribute, query, and USD population APIs to ovstage.
  5. Commit at least one ovstage write before calling `ovrtx_step_with_stage()`.
  6. Replace removed RT1 direct-lighting modes.

- The repository includes agent-assisted `update-0_3-0_4-c` and `update-0_3-0_4-python` migration skills.


## [0.3.0] - 2026-05-15

### Added

- Upgrade skill to migrate an existing codebase from 0.2.0 to 0.3.0. Ask your agent to "upgrade from 0.2 to 0.3".
- New root-stage loading API. In C, `ovrtx_open_usd_from_file()` and `ovrtx_open_usd_from_string()` replace the active root layer, while `ovrtx_add_usd_reference_from_file()` and `ovrtx_add_usd_reference_from_string()` add removable referenced content below a caller-provided prefix path so multiple layers can be composed under separate prims. Exposed in Python as `Renderer.open_usd()` / `open_usd_from_string()` / `add_usd_reference()` / `add_usd_reference_from_string()` and their `_async` variants.
- `ovrtx_register_schema_paths()` for publishing ovrtx USD schema/plugin paths before any shared OpenUSD runtime is initialized. Python exposes `register_schema_paths()` and auto-registers on `import ovrtx` unless `OVRTX_SKIP_SCHEMA_AUTO_REGISTER=1` is set.
- Stage query API for discovering prims and their attribute schemas. In C, `ovrtx_query_prims()` / `ovrtx_fetch_query_results()` / `ovrtx_release_query_results()` return prims grouped by shared attribute schema, with AND/OR/NOT filters on prim type and attribute presence. The returned `prim_list_handle` plugs directly into subsequent read/write bindings. Exposed in Python as `Renderer.query_prims()` / `query_prims_async()`.
- Stage attribute read API. In C, `ovrtx_read_attribute()` / `ovrtx_fetch_read_result()` / `ovrtx_release_read_result()` enqueue stream-ordered reads of scalar or array attributes and optionally write into a caller-provided `ovrtx_read_dest_t` tensor (including GPU/CUDA destinations). Exposed in Python as `Renderer.read_attribute()` / `read_array_attribute()` and their `_async` variants.
- Expanded attribute write and mapping APIs. Python writes now accept CPU or GPU DLPack-compatible tensors directly, support synchronous or asynchronous data access with CUDA stream/event synchronization, and can use persistent `AttributeBinding` handles or direct `Renderer.map_attribute()` / `AttributeMapping.unmap_async()` workflows for repeated updates and caller-managed lifetimes.
- `ovrtx_get_path_dictionary()` to obtain the renderer's path dictionary for converting between tokens/path handles and strings, and for pre-resolving filter names for repeated queries.
- Lidar and radar sensor support, including composite `PointCloud` render variables with named tensors for channels such as coordinates, intensity, velocity, radar cross section, flags, and counts; see the new C/Python lidar and radar sensor examples.
- Viewport picking and selection outline support. Applications can enqueue RenderProduct-space pick rectangles with `ovrtx_enqueue_pick_query()` / `Renderer.enqueue_pick_query_async()`, read the synthetic pick-hit render var, resolve picked prim paths through the path dictionary, and draw selection outlines with `ovrtx_set_selection_outline_group()` / `Renderer.set_selection_outline_group()`. The C API also adds `ovrtx_set_selection_group_styles()` and `ovrtx_set_pickable()`; Python adds `SelectionGroupStyle`, `SelectionFillMode`, `Renderer.set_selection_group_styles()`, and `Renderer.set_pickable()`. The Vulkan interop example now demonstrates click picking, marquee selection with a Vulkan overlay rectangle, selected-prim path printing, and styled ovrtx selection outlines with translucent fill.
- New renderer configuration controls: `OVRTX_CONFIG_SELECTION_OUTLINE_ENABLED`, `OVRTX_CONFIG_SELECTION_OUTLINE_WIDTH`, `OVRTX_CONFIG_SELECTION_FILL_MODE`, `OVRTX_CONFIG_ENABLE_GEOMETRY_STREAMING`, `OVRTX_CONFIG_ENABLE_GEOMETRY_STREAMING_LOD`, and experimental `OVRTX_CONFIG_ENABLE_SPG`, plus matching C helper functions and `RendererConfig` fields. `ovrtx_config.h` also includes typed config-entry constructors such as `ovrtx_config_entry_bool()`, `ovrtx_config_entry_string()`, `ovrtx_config_entry_int()`, and `ovrtx_config_entry_binary_package_root_path()`.
- Windows ovrtx binaries are now Authenticode-signed so Windows deployments can verify the publisher and avoid unsigned-binary trust warnings.
- ovrtx packages can connect to DDCS servers through the renderer-plugin version of GRPCDataStore, enabling DDCS-backed workflows such as IsaacLab and Windows deployments.
- New attribute semantics for query results: `OVRTX_SEMANTIC_TOKEN_ID`, `OVRTX_SEMANTIC_PATH_ID`, and `OVRTX_SEMANTIC_TAG` (name-only tag attributes with no data).
- Python: `Renderer.update_from_usd_time_async()` to schedule a stage-time update asynchronously, `Operation.query_status()` for polling operation progress, and `AttributeMapping.unmap_async()` for asynchronous attribute-map commits.
- Python public surface expanded in `ovrtx.__init__`: `AttributeFilterMode`, `FilterKind`, `BindingFlag`, `EventStatus`, `SelectionFillMode`, `SelectionGroupStyle`, `AttributeInfo`, `AttributeBinding`, `AttributeMapping`, `FrameOutput`, `ProductOutput`, `RenderProductSetOutputs`, `RenderVarOutput`, `RenderVarParam`, `RenderVarTensor`, `Operation`, `OperationCounter`, `OperationStatus`, `PendingFetch`, `MappedRenderVar`, and `ManagedDLTensor`.
- New examples: C Material Editor, C/Python status queries, Python tiled rendering, Python semantic segmentation, and C/Python lidar and radar sensor examples.
- Expanded documentation and skills for camera RenderVars, render modes, render settings, sensor configuration, render output interpretation, lidar/radar point clouds, semantic labels, material binding, viewport picking/selection, stage queries, attribute reads, and status queries.


### Changed

- Root-stage composition is now explicit: `open_usd*` owns the single active root layer and replaces any previous root, while `add_usd_reference*` is only for additive, removable references under an already-open root stage.
- `ovrtx_wait_op()` now returns only the op ids that produced errors plus the lowest still-pending op id, instead of an inline list of error strings and all active op ids. Error strings are retrieved per-id via `ovrtx_get_last_op_error()` and are transient thread-local data invalidated by the next `ovrtx_wait_op()` on the same thread. The separate `ovrtx_release_errors` cleanup step is no longer needed.
- Logging callbacks are now process-global instead of renderer-scoped. `ovrtx_set_log_callback()` no longer takes a renderer, `ovrtx_log_callback_t` no longer receives an op id, timestamps are wall-clock seconds, severity values now mirror carb log levels (`INFO=-1`, `WARNING=0`, `ERROR=1`, `FATAL=2`), and `ovrtx_flush_op_log()` is replaced by `ovrtx_flush_log()`. The `channel_filter` string now accepts comma-separated `<channel_prefix>=<level>` rules with longest-prefix matching and RUST_LOG-style level names.
- `ovrtx_query_extension()` is documented as internal-only and unsupported for public API compatibility guarantees.
- Documentation clarified: `ovx_string_t` consumers should prefer the explicit `length` field over relying on the null terminator, and strings returned from `ovrtx_get_last_error()` should be copied or consumed before the next API call on the same thread.
- Render-variable outputs are now multi-tensor capable. The C struct `ovrtx_rendered_output_t` is replaced by `ovrtx_render_var_output_t`, exposing named `tensors[]` and `params[]` arrays and a single `cuda_sync` field; the corresponding handle types and `ovrtx_map_rendered_output` / `ovrtx_unmap_rendered_output` are renamed to `ovrtx_render_var_output_*`. C consumers must recompile and migrate field accesses. Python `MappedRenderVar` exposes tensors via dict access (`rv["name"]`) or DLPack on the mapping itself for single-tensor render variables; the legacy `MappedRenderVar.tensor` accessor still works for single-tensor render variables but emits `DeprecationWarning` and will be removed. See the refreshed `docs/sensors/common/sensor_outputs.rst`, the `reading-render-output` skill, and `examples/{c,python}/minimal` for the new usage.
- Image RenderVar tensors now use channel-last shapes such as `[height, width, channels]` with scalar DLPack lanes.
- Python `MappedRenderVar` mappings now have a consumer-owned lifetime: the underlying buffer stays valid as long as any DLPack-derived array, `RenderVarTensor`, or `RenderVarParam` view holds a reference, even after `unmap()` or context-manager exit. `ManagedDLTensor.numpy()` is a zero-copy view; use `.copy()` while the mapping is live when an independent array is needed. See the `MappedRenderVar` docstring and the `reading-render-output` skill for the full contract.
- Python `Renderer.step_async()` now follows the standard two-phase async lifecycle: it returns `Operation[PendingFetch[RenderProductSetOutputs]]`; call `wait()` to wait for rendering and `fetch()` to retrieve outputs. Synchronous `Renderer.step()` still waits and fetches for callers.
- `RendererConfig.keep_system_alive` now defaults to enabled in the native layer, reducing teardown/recreate churn for multi-renderer lifecycles.
- Selection outlines are now enabled by default. Pass `selection_outline_enabled=False` in Python or `ovrtx_config_entry_selection_outline_enabled(false)` in C to disable them.
- Multi-GPU RenderProducts without authored `deviceIds` are now auto-assigned to GPU devices at RenderProduct creation time when multiple devices are active.
- Tiled rendering workloads with many RenderProducts or cameras now spend less CPU time updating per-view tile parameters.
- GPU transform mode now supports per-tick TLAS updates during multi-tick steps, improving dynamic-scene behavior when GPU transform propagation is enabled.
- License text was updated to the current NVIDIA Software License Agreement and Product Specific Terms for NVIDIA AI Products.

### Fixed

- Fixed Python DLPack/render-var/attribute mapping lifetime issues, including `AttributeBinding.write()` after `unbind()`, empty `prim_paths=[]` writes, leaked or locked attribute mappings outside a context manager, abandoned async step handles, double-unmap on exceptions, failed DLTensor construction after a successful C map, and renderer teardown with active mappings or bindings.
- Fixed Python import/library discovery failures caused by inaccessible Windows `PATH` entries such as `WindowsApps`.
- Fixed ovrtx schema/plugin discovery when running from non-Kit executables, from Python, or in processes that also load another USD-based subsystem, including the missing `OmniPlaybackAPI` schema warning when loading materials.
- ovrtx now vendors OpenUSD libraries that are namespaced to avoid symbol collisions. OpenUSD and usd-core can now be used in the same process as ovrtx without issue.
- Fixed logging callback flush/lost-wakeup races and applied init-time log file/log level settings when the first renderer is created.
- Fixed multi-GPU picking readback device mismatches and related selection-outline ordering issues.
- Fixed CUDA interop failures including BAR1/NVML permission handling and Vulkan sparse-buffer corruption cases.
- Fixed a Windows rendering issue where every other frame could be black during repeated transform-update rendering.
- Fixed `dataWindowNDC` on `RenderProduct` prims so mapped output tensors reflect the cropped output size instead of always returning the full authored resolution.
- Fixed texture-processing failures for invalid texture inputs that could emit `TextureProcessor : Failed to process texture ...` errors.
- Fixed crashes or incorrect updates around time-sampled visibility, GPU point updates, and stage loading regressions.
- Fixed package/deploy issues including missing shader cache content, missing CMake config files, and recursive dependency updates for nested Python examples.

### Removed

- `OVRTX_CONFIG_OUTPUT_PARTIAL_FRAMES` and the corresponding `ovrtx_config_entry_output_partial_frames()` helper. Partial-frame output is now controlled per render product via the USD attribute `bool omni:sensor:Core:accumulateOutputs` on the camera prim (defaults to `false`, i.e. partial frames are emitted every step — the same as the old default). Setting it to `true` suppresses partial frames for that sensor and only emits a frame once the exposure has been fully accumulated.
- `ovrtx_add_usd()` and `ovrtx_usd_input_t`. Use `ovrtx_open_usd_from_file()` / `ovrtx_open_usd_from_string()` for root-stage loading and `ovrtx_add_usd_reference_from_file()` / `ovrtx_add_usd_reference_from_string()` for additive references.
- Python: `Renderer.add_usd()`, `Renderer.add_usd_layer()`, and their async variants. Use `open_usd*` for root-stage loading and `add_usd_reference*` for additive references.
- Python: the `RendererResult` export. `Renderer.step_async()` returns `Operation[PendingFetch[RenderProductSetOutputs]]`.

### Security

- Updated OpenSSL to 3.5.6 for use-after-free and heap-buffer-overflow fixes, updated PerfSDK to remove bundled Python 3.10.5 CVE exposure, and refreshed USD, GLib/GStreamer, and Python dependency pins for security fixes.

### Limitations

- Viewport picking currently only works for RenderProducts running on CUDA-visible GPU 0. On multi-GPU systems, author `uint[] deviceIds = [0]` on RenderProducts that are used for picking. `deviceIds` is an allow-list of indices into `CUDA_VISIBLE_DEVICES`; ovrtx may choose any CUDA-visible GPU from the list.
- On Linux systems with no display, repeatedly creating and destroying renderers may result in a crash with the stack trace pointing into `libEGL.so` when shared graphics resources are torn down between renderers. This can happen if `keep_system_alive` is configured to `false`, or if `ovrtx_initialize()` is not called before the multi-renderer lifecycle. In the implicit-initialization pattern (when `ovrtx_initialize()` is not called), the `keep_system_alive` config setting is effectively ignored. Avoid this by both configuring `keep_system_alive` to `true` (`RendererConfig(keep_system_alive=True)` in Python, `ovrtx_config_entry_keep_system_alive(true)` in C) and calling `ovrtx_initialize()` before creating renderers. If this is not possible, or the crash persists, a further workaround is to set the environment variable `VK_LOADER_DISABLE_DYNAMIC_LIBRARY_UNLOADING=1`.
- When ovrtx is used together with ovPhysX in the same process, ovrtx must be initialized first. In Python, this means `import ovrtx` must come before `import ovphysx`. In C/C++, call `ovrtx_initialize()` before initializing ovPhysX.

## [0.2.0] - 2026-03-06

### Added

- Support for Gaussian Splats and other particle field primitive types using the [`UsdVol.ParticleField`](https://openusd.org/dev/user_guides/schemas/usdVol/ParticleField.html) schema.
- Operation status query API and logging callback for monitoring renderer operations.
- Dedicated functions for creating supported config values.
- GPU selection by CUDA device index at renderer creation using `ovrtx_config_entry_active_cuda_gpus()` and per render product using `uint[] deviceIds`.
- `ovrtx_get_version()` Python binding with version compatibility check between the Python package and native library.
- Python bindings for `enable_profiling`, `read_gpu_transforms` config entries.
- Async data access in Python bindings (`write_attribute`, `write_array_attribute`) matching the C API.

### Changed

- Upgraded DLPack from 0.8 to 1.3 in both C and Python APIs, allowing creating boolean tensors.
- Python attribute writes now accept NumPy-style tensors as input. This means that an N-element, 4x4 matrix can be
  written from Python as shape=[N, 4, 4], making NumPy interop simpler. The C attribute read/write API remains
  lane-based: the same matrix attribute is shape=[N] with 16 lanes, and point3f[] data is shape=[point_count] with
  3 lanes. Rendered output/AOV tensors remain channel-last with scalar lanes.
- C API headers are now pure C compatible (removed C++ constructs from `ovrtx_attributes.h` and `pathdictionary_helper.h`)
- Transform attributes now use the `omni:xform` alias; direct writing of `localMatrix`/`worldMatrix` is no longer
  supported and transforms must be written to `omni:xform` instead. If those transforms are in world space as opposed to
  local space then `bool resetXformStack=true` must also be set on the same prim.

### Fixed

- Removed spurious `IRenderSettings::getRenderSettings failed` warning when no global RenderSettings prim is present in the USD stage.
- Removed nvidia-smi printout on startup.
- Fixed material-related memory leaks.
- Fixed a visual glitch when calling `ovrtx_reset_stage()`.

### Security

- Updated OpenSSL to address CVE-2025-15467

## [0.1.0] - 2026-02-13

### Added

- Initial release of ovrtx: NVIDIA Omniverse RTX Rendering library
- C library
- Python bindings
- Example source code
- Documentation

### Limitations

- ovrtx cannot be used in a process that also links OpenUSD that is not v25.11, non-monolithic and Python-enabled, linked against oneTBB. In particular, this means ovrtx cannot be used together with `usd-core` in the same process. This limitation will be lifted in a future version.
- ovrtx currently supports camera sensors only. Other types of sensors will be supported in the next minor release.

[0.7.0]: https://github.com/NVIDIA-Omniverse/ovrtx/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/NVIDIA-Omniverse/ovrtx/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/NVIDIA-Omniverse/ovrtx/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/NVIDIA-Omniverse/ovrtx/compare/v0.4.1...v0.5.0
[0.4.1]: https://github.com/NVIDIA-Omniverse/ovrtx/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/NVIDIA-Omniverse/ovrtx/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/NVIDIA-Omniverse/ovrtx/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/NVIDIA-Omniverse/ovrtx/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/NVIDIA-Omniverse/ovrtx/releases/tag/v0.1.0
