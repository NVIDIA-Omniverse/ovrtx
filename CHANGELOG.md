# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-07-17

# ovrtx 0.4.0 Release Notes

## Summary

ovrtx 0.4 introduces integration with the new [ovstage](https://github.com/nvidia-omniverse/ovstage) 0.1 library. Applications can attach an externally owned ovstage instance and render its scene data.

Existing ovrtx APIs for loading USD and reading or writing stage attributes remain available for compatibility but are deprecated and will be removed in a future release.

This release also includes breaking C API changes, improved DLSS Ray Reconstruction quality under motion, and numerous rendering, sensor, and stability fixes.

## Highlights

### ovstage integration

New C APIs support attached-stage workflows:

- `ovrtx_attach_ovstage()` and `ovrtx_detach_ovstage()`
- `ovrtx_step_with_stage()`
- `ovrtx_update_from_stage()`

While attached, ovrtx stage-building, write, and map APIs return `OVRTX_API_ERROR`. Read-only `ovrtx_query_prims()` remains available.

### Motion BVH configuration

`OVRTX_CONFIG_MOTION_BVH` replaces the former Boolean option:

- `Disable` — off and now the default
- `Enable` — enabled when the renderer is created
- `Auto` — enabled when required by sensors or motion-sensitive cameras

Applications that relied on implicit auto-detection must explicitly select `Auto`.

### Schema registration

Automatic registration in `PXR_PLUGINPATH_NAME` is now disabled by default. Register schemas by setting `OVRTX_PXR_SCHEMA_AUTO_REGISTER` or calling `ovrtx_register_schema_paths()` before OpenUSD initializes.

Standalone applications using `ovrtx_initialize()` or `ovrtx_create_renderer()` continue to register paths automatically. `OVRTX_SKIP_SCHEMA_AUTO_REGISTER` has been removed.

### Other additions

- NDC-based picking, pickability controls, and configurable selection outlines
- Geometry streaming configuration
- Rolling-shutter, RenderVar channel, physical-camera responsivity, and light-shaping schemas
- Render Output Compression, LPE labels for AOVs, and multiple dome lights
- Gaussian splats and scene partitioning in RTX Minimal
- SPG output fanout, multiple descriptor sets, structured buffers, and large array inputs
- Updated DLSS Ray Reconstruction with better quality under motion

## Breaking Changes

All C consumers must be recompiled.

- `ovrtx_release_read_result()` now accepts the original `ovrtx_read_handle_t`.
- `ovrtx_read_map_handle_t` and `ovrtx_read_output_t::map_handle` were removed.
- Picking rectangles now use NDC coordinates.
- SPG parameters are now authored as shader inputs.
- `ovx_string_t::str` and `::len` became `::ptr` and `::length`.
- RT1 `DirectLightingSampled` and `DirectLightingLtc` modes were removed.

## Notable Fixes

- Corrected HDR color, illuminance, motion-vector, and dome-light AOV behavior
- Fixed rect, sphere, distant, and dome-light rendering issues
- Fixed OmniSurface volume coefficients
- Fixed lidar direction handling, beams-mode crashes, and mixed sensor tick-rate crashes
- Improved motion transforms, velocity estimation, and semantic-label determinism
- Fixed VRAM accounting and scene-partitioning out-of-memory failures
- Added DLPack v1.2-compliant row-major strides
- Enabled SPG by default

## Known Issues

- Multi-GPU viewport picking is limited to GPU 0; set RenderProduct `deviceIds = [0]`.
- Repeated renderer creation on headless Linux may crash in `libEGL.so`. Use `keep_system_alive = true` with early `ovrtx_initialize()`, or set `VK_LOADER_DISABLE_DYNAMIC_LIBRARY_UNLOADING=1`.
- ovrtx must initialize before ovphysx.
- ovstage 0.1 does not support USD-active reads.
- The material-editor C example has not yet been migrated to ovstage or validated.

## Upgrading from ovrtx 0.3.x

1. Recompile C consumers and update read-result, picking, string, and SPG APIs.
2. Enable schema registration explicitly if your application depends on it.
3. Select Motion BVH `Auto` if you relied on the former implicit behavior.
4. Migrate deprecated scene, attribute, query, and USD population APIs to ovstage.
5. Commit at least one ovstage write before calling `ovrtx_step_with_stage()`.
6. Replace removed RT1 direct-lighting modes.

The repository includes agent-assisted `update-0_3-0_4-c` and `update-0_3-0_4-python` migration skills.


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
- Render-variable outputs are now multi-tensor capable. The C struct `ovrtx_rendered_output_t` is replaced by `ovrtx_render_var_output_t`, exposing named `tensors[]` and `params[]` arrays and a single `cuda_sync` field; the corresponding handle types and `ovrtx_map_rendered_output` / `ovrtx_unmap_rendered_output` are renamed to `ovrtx_render_var_output_*`. C consumers must recompile and migrate field accesses. Python `MappedRenderVar` exposes tensors via dict access (`rv["name"]`) or DLPack on the mapping itself for single-tensor render variables; the legacy `MappedRenderVar.tensor` accessor still works for single-tensor render variables but emits `DeprecationWarning` and will be removed. See the refreshed `docs/sensors/configuration.rst`, the `reading-render-output` skill, and `examples/{c,python}/minimal` for the new usage.
- Image RenderVar tensors now use channel-last shapes such as `[height, width, channels]` with scalar DLPack lanes.
- Python `MappedRenderVar` mappings now have a consumer-owned lifetime: the underlying buffer stays valid as long as any DLPack-derived array, `RenderVarTensor`, or `RenderVarParam` view holds a reference, even after `unmap()` or context-manager exit. `ManagedDLTensor.numpy()` is a zero-copy view; use `.copy()` while the mapping is live when an independent array is needed. See the `MappedRenderVar` docstring and the `reading-render-output` skill for the full contract.
- Python `Renderer.step_async()` now follows the standard two-phase async lifecycle: it returns `Operation[PendingFetch[RenderProductSetOutputs]]`; call `wait()` to wait for rendering and `fetch()` to retrieve outputs. Synchronous `Renderer.step()` still waits and fetches for callers.
- `RendererConfig.keep_system_alive` now defaults to enabled in the native layer, reducing teardown/recreate churn for multi-renderer lifecycles.
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
