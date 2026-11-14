/* Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
 *
 * NVIDIA CORPORATION and its licensors retain all intellectual property
 * and proprietary rights in and to this software, related documentation
 * and any modifications thereto.  Any use, reproduction, disclosure or
 * distribution of this software and related documentation without an express
 * license agreement from NVIDIA CORPORATION is strictly prohibited.
 */

/** @file ovrtx_config.h */

#ifndef OVRTX_CONFIG_H
#define OVRTX_CONFIG_H

#include "ovrtx_types.h"
#include <ovx/config_tokens.h>

#ifdef __cplusplus
extern "C"
{
#endif

/** @defgroup ovrtx_config_helpers Configuration helper functions
 *  @{
 */

/**
 * Build a config entry for a boolean setting.
 * @param key Config key (e.g. OVRTX_CONFIG_SYNC_MODE). Must be from ovrtx_config_bool_t.
 * @param value Stored by value in the entry.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_bool(ovrtx_config_bool_t key, bool value)
{
    ovrtx_config_entry_t entry;
    entry.key_type = OVRTX_CONFIG_KEY_TYPE_BOOL;
    entry.key.bool_key = key;
    entry.value.bool_value = value;
    return entry;
}

/**
 * Build a config entry for a string setting.
 * @param key Config key (e.g. OVRTX_CONFIG_LOG_FILE_PATH). Must be from ovrtx_config_string_t.
 * @param value String value. value.ptr must remain valid until the API call that consumes the
 *              config returns.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_string(ovrtx_config_string_t key, ovx_string_t value)
{
    ovrtx_config_entry_t entry;
    entry.key_type = OVRTX_CONFIG_KEY_TYPE_STRING;
    entry.key.string_key = key;
    entry.value.string_value = value;
    return entry;
}

/**
 * Build a config entry for an int64 setting.
 * @param key Config key (e.g. OVRTX_CONFIG_SELECTION_OUTLINE_WIDTH). Must be from ovrtx_config_int64_t.
 * @param value Stored by value in the entry.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_int(ovrtx_config_int64_t key, int64_t value)
{
    ovrtx_config_entry_t entry;
    entry.key_type = OVRTX_CONFIG_KEY_TYPE_INT64;
    entry.key.int64_key = key;
    entry.value.int_value = value;
    return entry;
}

/**
 * Configure the OVRTX "binary package root" directory.
 *
 * This is used by the loader to locate the renderer shared library and required runtime resources.
 * If not provided, the loader chooses a default based on the loader's location.
 *
 * @param path The root directory path. path.ptr must remain valid until the API call that consumes the config returns.
 *             The path may contain the @ref OVX_CONFIG_EXECUTABLE_DIR_TOKEN token, which the loader
 *             substitutes with the absolute directory of the running executable
 *             (e.g. OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx/bin").
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_binary_package_root_path(ovx_string_t path)
{
    return ovrtx_config_entry_string(OVRTX_CONFIG_BINARY_PACKAGE_ROOT_PATH, path);
}

/**
 * Enable Spectral PathTracing before creating the first renderer in this process.
 * Also enable spectral rendering on its PathTracing RenderProducts. The choice cannot change
 * during the process lifetime, including after destroying all renderer instances.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_enable_spectral_rendering(bool enabled)
{
    return ovrtx_config_entry_bool(OVRTX_CONFIG_ENABLE_SPECTRAL_RENDERING, enabled);
}

/**
 * Enable or disable the OVRTX crash reporter. Enabled by default.
 *
 * Disable it when the host application owns crash handling: OVRTX then installs no crash
 * handlers and does not upload crash dumps. The first renderer created in this process
 * decides; the choice cannot change during the process lifetime. See OVRTX_CONFIG_ENABLE_CRASH_REPORTER.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_enable_crash_reporter(bool enabled)
{
    return ovrtx_config_entry_bool(OVRTX_CONFIG_ENABLE_CRASH_REPORTER, enabled);
}

/**
 * Enable or disable graphics API debug validation when creating shared graphics devices.
 * Omit this entry to preserve GPU Foundation's default.
 * Additional renderers reuse the existing validation mode; conflicting requests warn and
 * continue with that mode. See @ref OVRTX_CONFIG_ENABLE_DEBUG_VALIDATION for lifetime rules.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_enable_debug_validation(bool enabled)
{
    return ovrtx_config_entry_bool(OVRTX_CONFIG_ENABLE_DEBUG_VALIDATION, enabled);
}

/**
 * Configure synchronous stream execution.
 *
 * When enabled, operations that are normally enqueued for stream-ordered execution will block
 * the calling thread until the operation has completed. Any errors will be returned immediately.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_sync_mode(bool sync_mode)
{
    return ovrtx_config_entry_bool(OVRTX_CONFIG_SYNC_MODE, sync_mode);
}

/**
 * Configure internal profiling.
 *
 * When enabled, the renderer collects additional profiling data. This can add overhead.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_enable_profiling(bool enable_profiling)
{
    return ovrtx_config_entry_bool(OVRTX_CONFIG_ENABLE_PROFILING, enable_profiling);
}

/**
 * Configure transform propagation mode.
 *
 * When enabled, the renderer uses GPU world transform propagation during rendering.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_read_gpu_transforms(bool read_gpu_transforms)
{
    return ovrtx_config_entry_bool(OVRTX_CONFIG_READ_GPU_TRANSFORMS, read_gpu_transforms);
}

/**
 * Enable the history presentation of an attached history-capable ovstage.
 *
 * When enabled, ovrtx_step_with_stage() at an ordinal below the write floor renders the retained
 * values of the renderable history-enabled pairs and restores the live values afterwards. When
 * disabled (the default), the renderer makes no history calls, and such a step fails with a reason
 * that names OVRTX_CONFIG_ENABLE_HISTORY_PRESENTATION. Pass to ovrtx_create_renderer().
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_enable_history_presentation(bool enable_history_presentation)
{
    return ovrtx_config_entry_bool(OVRTX_CONFIG_ENABLE_HISTORY_PRESENTATION, enable_history_presentation);
}

/**
 * Keep the renderer system alive after all instances are destroyed.
 *
 * When enabled (default), the shared RendererWrapperSystem (common GPU resources) is not destroyed
 * when the last renderer instance is destroyed, so a subsequent create_renderer reuses it.
 * When disabled, the system is destroyed when the last renderer instance is destroyed.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_keep_system_alive(bool keep_system_alive)
{
    return ovrtx_config_entry_bool(OVRTX_CONFIG_KEEP_SYSTEM_ALIVE, keep_system_alive);
}

/** Enable or disable Minimal rendering at startup. See OVRTX_CONFIG_ENABLE_MINIMAL. */
static inline ovrtx_config_entry_t ovrtx_config_entry_enable_minimal(bool enable_minimal)
{
    return ovrtx_config_entry_bool(OVRTX_CONFIG_ENABLE_MINIMAL, enable_minimal);
}

/** Enable or disable real-time path tracing at startup. See OVRTX_CONFIG_ENABLE_REALTIMEPATHTRACING. */
static inline ovrtx_config_entry_t ovrtx_config_entry_enable_realtimepathtracing(bool enable_realtimepathtracing)
{
    return ovrtx_config_entry_bool(OVRTX_CONFIG_ENABLE_REALTIMEPATHTRACING, enable_realtimepathtracing);
}

/** Enable or disable path tracing at startup. See OVRTX_CONFIG_ENABLE_PATHTRACING. */
static inline ovrtx_config_entry_t ovrtx_config_entry_enable_pathtracing(bool enable_pathtracing)
{
    return ovrtx_config_entry_bool(OVRTX_CONFIG_ENABLE_PATHTRACING, enable_pathtracing);
}

/** Enable or disable MDL material displacement at renderer creation. */
static inline ovrtx_config_entry_t ovrtx_config_entry_enable_mdl_displacement(bool enable_mdl_displacement)
{
    return ovrtx_config_entry_bool(OVRTX_CONFIG_ENABLE_MDL_DISPLACEMENT, enable_mdl_displacement);
}

/**
 * Build a config entry for the geometry streaming opt-in flag.
 *
 * Geometry streaming is disabled when this entry is not specified.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_enable_geometry_streaming(bool enable_geometry_streaming)
{
    return ovrtx_config_entry_bool(OVRTX_CONFIG_ENABLE_GEOMETRY_STREAMING, enable_geometry_streaming);
}

/**
 * Build a config entry for the geometry streaming LOD opt-in flag.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_enable_geometry_streaming_lod(
    bool enable_geometry_streaming_lod)
{
    return ovrtx_config_entry_bool(OVRTX_CONFIG_ENABLE_GEOMETRY_STREAMING_LOD, enable_geometry_streaming_lod);
}

/**
 * Build a config entry for enabling/disabling RTX Sensor Processing Graphs (enabled by default).
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_enable_spg(bool enable_spg)
{
    return ovrtx_config_entry_bool(OVRTX_CONFIG_ENABLE_SPG, enable_spg);
}

/**
 * Suppress runtime warnings emitted when deprecated OVRTX APIs are called.
 *
 * This does not affect compile-time deprecation diagnostics from OVRTX_DEPRECATED.
 * When omitted, runtime deprecation warnings remain enabled.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_suppress_deprecation_warnings(
    bool suppress_deprecation_warnings)
{
    return ovrtx_config_entry_bool(OVRTX_CONFIG_SUPPRESS_DEPRECATION_WARNINGS, suppress_deprecation_warnings);
}

/**
 * Configure motion BVH (ray-traced motion) behavior for sensor pipelines.
 *
 * @param mode One of @ref ovrtx_motion_bvh_t. Must be set before the first
 *             @ref ovrtx_create_renderer call; changing the value requires recreating
 *             the renderer. When not provided, the renderer uses the process's own motion
 *             BVH settings, which default to @ref OVRTX_MOTION_BVH_DISABLE; it does not
 *             inherit a mode set by an earlier renderer in the process.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_motion_bvh(ovrtx_motion_bvh_t mode)
{
    return ovrtx_config_entry_int(OVRTX_CONFIG_MOTION_BVH, (int64_t)mode);
}

/**
 * Configure texture streaming behavior.
 *
 * @param mode One of @ref ovrtx_texture_streaming_mode_t. When not provided,
 *             texture streaming defaults to @ref OVRTX_TEXTURE_STREAMING_ASYNCHRONOUS.
 *             Synchronous mode processes texture feedback synchronously; it does not
 *             make all texture loading operations synchronous. This setting is
 *             process-global and applies to all active renderer instances.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_texture_streaming_mode(
    ovrtx_texture_streaming_mode_t mode)
{
    return ovrtx_config_entry_int(OVRTX_CONFIG_TEXTURE_STREAMING_MODE, (int64_t)mode);
}

/**
 * Configure NVIDIA Nsight Aftermath diagnostics.
 *
 * @param mode One of @ref ovrtx_aftermath_mode_t. @ref OVRTX_AFTERMATH_DISABLE skips
 *             Aftermath initialization, @ref OVRTX_AFTERMATH_ENABLE selects explicit
 *             diagnostics initialization, and omitted or @ref OVRTX_AFTERMATH_AUTO selects
 *             the initialization mode automatically. This is process-global and must be
 *             selected before the first renderer is created; subsequent renderer
 *             configurations must use the same mode while the renderer system is alive.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_aftermath_mode(ovrtx_aftermath_mode_t mode)
{
    return ovrtx_config_entry_int(OVRTX_CONFIG_AFTERMATH_MODE, (int64_t)mode);
}

/**
 * Configure log file path for carb logging.
 *
 * This setting should be passed to ovrtx_initialize(). The log file is created when the first
 * renderer is created via ovrtx_create_renderer().
 *
 * The path may contain the ${start_timestamp} token which will be replaced with the startup
 * timestamp in YYYYMMDD_HHMMSS format (e.g., "myapp_${start_timestamp}.log").
 *
 * If not specified, defaults to: \<app_directory\>/ovrtx_${start_timestamp}.log
 *
 * @param path Log file path. path.ptr must remain valid until the API call that consumes the config returns.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_log_file_path(ovx_string_t path)
{
    return ovrtx_config_entry_string(OVRTX_CONFIG_LOG_FILE_PATH, path);
}

/**
 * Configure carb logging level (e.g. "verbose", "info", "warn", "error", "fatal").
 *
 * This setting should be passed to ovrtx_initialize(). The log level is applied when the first
 * renderer is created via ovrtx_create_renderer().
 *
 * @param level Log level string.  The memory behind `level.ptr` must remain valid until the
 *              API call that consumes the config returns.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_log_level(ovx_string_t level)
{
    return ovrtx_config_entry_string(OVRTX_CONFIG_LOG_LEVEL, level);
}

/**
 * Configure active CUDA GPUs for rendering.
 *
 * Specifies which GPUs to use for rendering by their CUDA device indices.
 * The indices are translated to Vulkan device indices internally by GPU Foundation.
 * This is useful when CUDA and Vulkan enumerate devices in different orders.
 *
 * @param cuda_gpus Comma-separated list of CUDA device indices (e.g., "0,1,2").
 *                  cuda_gpus.ptr must remain valid until the API call that consumes the config returns.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_active_cuda_gpus(ovx_string_t cuda_gpus)
{
    return ovrtx_config_entry_string(OVRTX_CONFIG_ACTIVE_CUDA_GPUS, cuda_gpus);
}

/**
 * Allow all soft-deprecated sensor versions while pinned to a specific framework release.
 *
 * Soft-deprecated sensor versions are rejected by default. This opt-in allows them only while
 * the value matches the current framework version, so it must be revisited on every framework
 * upgrade (upgrading stops soft-deprecated sensors from loading, forcing migration).
 *
 * @param base "<major>.<minor>.<patch>" (e.g. "0.4.0"). Any non-matching value (or unset) allows none.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_sensors_allowed_deprecation_base(ovx_string_t base)
{
    return ovrtx_config_entry_string(OVRTX_CONFIG_SENSORS_ALLOWED_DEPRECATION_BASE, base);
}

/**
 * Configure the datastore cache used by UJITSO.
 *
 * Supported protocol-prefixed values are:
 * - `grpcdns://host:port` for the Derived Data Cache with TLS
 * - `grpcdns_notls://host:port` for the Derived Data Cache without TLS
 * - `local://path` for a local datastore
 *
 * Omitting this entry preserves the existing cache defaults and environment-variable behavior.
 *
 * @param cache Cache configuration string. cache.ptr must remain valid until the API call that
 *              consumes the config returns.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_datastore_cache(ovx_string_t cache)
{
    return ovrtx_config_entry_string(OVRTX_CONFIG_DATASTORE_CACHE, cache);
}

/**
 * Set the process-wide ${omni_cache} root for OVRTX caches to a nonempty path that resolves to an absolute path.
 * Takes precedence over both the platform default and an ovrtx.portable marker beside the executable or OVRTX binaries.
 * Supply this setting to the first ovrtx_initialize() call or when creating the first renderer in the process
 * with ovrtx_create_renderer(). The chosen root applies to all renderers. If supplied again, use the same path string.
 * Changing the root within the same process is unsupported, even after destroying all renderers and calling
 * ovrtx_shutdown(). Start a new process to use a different root.
 * @param path Nonempty root path. path.ptr must remain valid
 *             until the API call that consumes the config returns.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_cache_root_path(ovx_string_t path)
{
    return ovrtx_config_entry_string(OVRTX_CONFIG_CACHE_ROOT_PATH, path);
}

/**
 * Select the platform's global cache root for ${omni_cache} and OVRTX's writable caches.
 * On Linux, this uses `XDG_CACHE_HOME/ovrtx/<version>` when XDG_CACHE_HOME is absolute,
 * otherwise `HOME/.cache/ovrtx/<version>`.
 * On Windows, this uses the `%LOCALAPPDATA%/ovrtx/<version>`.
 * `<version>` is the compiled OVRTX major.minor.patch version; VERSION.md is not consulted.
 * True is the default when omitted. False in either ovrtx_initialize() or ovrtx_create_renderer() disables the
 * platform root when no true value is supplied in the other call. Without a root request, existing cache-path
 * settings and a nonempty ${omni_cache} token are preserved; an empty token defaults to the application directory.
 * An ovrtx.portable file beside the executable or OVRTX binaries sets ${omni_cache} to the application directory
 * even when this entry is true, while retaining the existing local shader-cache subfolders.
 * A valid path supplied with ovrtx_config_entry_cache_root_path() takes precedence over both.
 * Configure this option in the first ovrtx_initialize() call or when creating the first renderer in the process.
 * Changing the cache root within the same process is unsupported, even after destroying all renderers and
 * calling ovrtx_shutdown(). Start a new process to use a different root.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_enable_global_cache_root(bool enabled)
{
    return ovrtx_config_entry_bool(OVRTX_CONFIG_ENABLE_GLOBAL_CACHE_ROOT, enabled);
}

/**
 * Enable the selection outline postprocessing pass.
 *
 * When enabled, prims marked with a non-zero selection group (via ovrtx_set_selection_outline_group)
 * will have a visible outline drawn in the rendered image.
 * Selection outlines are enabled by default. Pass false to disable them. When disabled, selection 
 * groups are tracked but no outline is rendered.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_selection_outline_enabled(bool enabled)
{
    return ovrtx_config_entry_bool(OVRTX_CONFIG_SELECTION_OUTLINE_ENABLED, enabled);
}

/**
 * Configure the default selection outline width in pixels.
 *
 * Applies to every selection group that has no per-group width of its own.
 *
 * Init-time only; changing this default requires renderer recreation. Valid
 * range is 0..15 (the underlying RTX outline pipeline cap), where 0 draws no
 * outline ring. Out-of-range values are clamped by the renderer. Per-group
 * overrides are applied at runtime via @ref ovrtx_set_selection_group_styles.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_selection_outline_width(int width)
{
    return ovrtx_config_entry_int(OVRTX_CONFIG_SELECTION_OUTLINE_WIDTH, (int64_t)width);
}

/**
 * Configure the selection-outline fill (interior) mode.
 *
 * Init-time only; changing requires renderer recreation.
 * @see ovrtx_selection_fill_mode_t for valid values.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_selection_fill_mode(ovrtx_selection_fill_mode_t mode)
{
    return ovrtx_config_entry_int(OVRTX_CONFIG_SELECTION_FILL_MODE, (int64_t)mode);
}

/** @} */ // end of ovrtx_config_helpers

#ifdef __cplusplus
}
#endif

#endif /* OVRTX_CONFIG_H */
