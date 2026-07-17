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
 * Keep the renderer system alive after all instances are destroyed.
 *
 * When enabled, the shared RendererWrapperSystem (common GPU resources) is not destroyed
 * when the last renderer instance is destroyed, so a subsequent create_renderer reuses it.
 * When disabled (default), the system is destroyed when the last renderer instance is destroyed.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_keep_system_alive(bool keep_system_alive)
{
    return ovrtx_config_entry_bool(OVRTX_CONFIG_KEEP_SYSTEM_ALIVE, keep_system_alive);
}

/**
 * Select graphics API.
 *
 * When true, the renderer uses Vulkan. When false, it uses DX12 (Windows only).
 * If this entry is not provided, the platform default is used (DX12 on Windows, Vulkan on Linux).
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_use_vulkan(bool use_vulkan)
{
    return ovrtx_config_entry_bool(OVRTX_CONFIG_USE_VULKAN, use_vulkan);
}

/**
 * Build a config entry for the geometry streaming opt-in flag.
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
 * Configure motion BVH (ray-traced motion) behavior for sensor pipelines.
 *
 * @param mode One of @ref ovrtx_motion_bvh_t. Must be set before the first
 *             @ref ovrtx_create_renderer call; changing the value requires recreating
 *             the renderer. When not provided, defaults to @ref OVRTX_MOTION_BVH_DISABLE.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_motion_bvh(ovrtx_motion_bvh_t mode)
{
    return ovrtx_config_entry_int(OVRTX_CONFIG_MOTION_BVH, (int64_t)mode);
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
 * Configure carb logging level (e.g. "verbose", "info", "warn", "error").
 *
 * This setting should be passed to ovrtx_initialize(). The log level is applied when the first
 * renderer is created via ovrtx_create_renderer().
 *
 * @param level Log level string. level.ptr must remain valid until the API call that consumes the config returns.
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
 * Enable the selection outline postprocessing pass.
 *
 * When enabled, prims marked with a non-zero selection group (via ovrtx_set_selection_outline_group)
 * will have a visible outline drawn in the rendered image.
 * When disabled (default), selection groups are tracked but no outline is rendered.
 */
static inline ovrtx_config_entry_t ovrtx_config_entry_selection_outline_enabled(bool enabled)
{
    return ovrtx_config_entry_bool(OVRTX_CONFIG_SELECTION_OUTLINE_ENABLED, enabled);
}

/**
 * Configure the selection outline width in pixels.
 *
 * Init-time only; changing requires renderer recreation. Valid range is 0..15
 * (the underlying RTX outline pipeline cap). Out-of-range values are clamped
 * by the renderer.
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
