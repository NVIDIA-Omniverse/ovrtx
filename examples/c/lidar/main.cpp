// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#endif

#include <ovrtx/ovrtx.h>
#include <ovrtx/ovrtx_config.h>
#include <ovrtx/ovrtx_types.h>
#include <ovstage/ovstage.h>
#include <ovstage/ovstage_config.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <iostream>
#include <string>
#include <string_view>
#include <system_error>

#ifdef _WIN32
#include <windows.h>
#endif

namespace {

constexpr char kRenderProductPath[] = "/World/Render/Products/LidarProduct";
constexpr char kDefaultSceneFileName[] = "lidar_example.usda";
constexpr int kWarmupStepCount = 3;
constexpr double kStepDeltaTimeSeconds = 0.1;

// [snippet:ovx-string-view-helper]
ovx_string_t to_ovx_string(std::string_view value)
{
    return { value.data(), value.size() };
}
// [/snippet:ovx-string-view-helper]

// [snippet:resolve-executable-dir]
// Locate files copied next to the executable, regardless of the launch cwd.
std::filesystem::path getExecutableDir(char const* argv0)
{
#ifdef _WIN32
    wchar_t buffer[MAX_PATH];
    DWORD length = GetModuleFileNameW(nullptr, buffer, MAX_PATH);
    if (length > 0 && length < MAX_PATH) {
        return std::filesystem::path(buffer).parent_path();
    }
#endif

#ifdef __linux__
    std::error_code error;
    std::filesystem::path executable =
        std::filesystem::canonical("/proc/self/exe", error);
    if (!error) {
        return executable.parent_path();
    }
#endif

    return std::filesystem::absolute(argv0).parent_path();
}
// [/snippet:resolve-executable-dir]

// [snippet:string-helper]
// ovrtx strings carry pointer + length, so compare without requiring a
// null-terminated value from the API.
bool string_equals(ovx_string_t value, char const* expected)
{
    const size_t expected_length = std::strlen(expected);
    return value.ptr && value.length == expected_length &&
           std::strncmp(value.ptr, expected, expected_length) == 0;
}
// [/snippet:string-helper]

// [snippet:check-error-helper]
// Print the last ovrtx error for any API call that does not report success.
template <typename ResultT>
bool check_api_result(ResultT const& result, std::string_view operation)
{
    if (result.status == OVRTX_API_SUCCESS) {
        return true;
    }

    if (result.status == OVRTX_API_TIMEOUT) {
        std::cerr << "ovrtx " << operation << " timed out\n";
        return false;
    }

    ovx_string_t error = ovrtx_get_last_error();
    if (error.ptr && error.length > 0) {
        std::cerr << "ovrtx " << operation << " failed: "
                  << std::string_view(error.ptr, error.length) << "\n";
    } else {
        std::cerr << "ovrtx " << operation << " failed\n";
    }
    return false;
}
// [/snippet:check-error-helper]

// [snippet:wait-op-helper]
// ovrtx work is asynchronous. Wait for the enqueued operation and print any
// per-operation errors reported by the renderer.
bool wait_for_success(ovrtx_renderer_t* renderer,
                      ovrtx_op_id_t op_id,
                      std::string_view operation)
{
    ovrtx_op_wait_result_t wait_result = {};

    // Wait for the enqueue operation itself to complete.
    ovrtx_result_t result =
        ovrtx_wait_op(renderer, op_id, ovrtx_timeout_infinite, &wait_result);
    if (!check_api_result(result, operation)) {
        return false;
    }

    if (wait_result.num_error_ops == 0) {
        return true;
    }

    // A completed wait can still report failed child operations. Print their
    // messages so the sample is useful when a USD load or render step fails.
    for (size_t i = 0; i < wait_result.num_error_ops; ++i) {
        ovx_string_t msg = ovrtx_get_last_op_error(wait_result.error_op_ids[i]);
        if (msg.ptr && msg.length > 0) {
            std::cerr << operation << ": op " << wait_result.error_op_ids[i]
                      << " failed: " << std::string_view(msg.ptr, msg.length)
                      << "\n";
        } else {
            std::cerr << operation << ": op " << wait_result.error_op_ids[i]
                      << " failed\n";
        }
    }
    return false;
}
// [/snippet:wait-op-helper]

// [snippet:find-render-var-output-helper]
// Step results are organized by render product, frame, and render variable.
// This example has one render product and one PointCloud render variable.
ovrtx_render_var_output_handle_t find_render_var_output(
    ovrtx_render_product_set_outputs_t const& outputs,
    char const* render_var_name)
{
    for (size_t p = 0; p < outputs.output_count; ++p) {
        ovrtx_render_product_output_t const& product = outputs.outputs[p];

        // A render product can produce multiple frames; each frame owns the
        // render variable outputs produced for that frame.
        for (size_t f = 0; f < product.output_frame_count; ++f) {
            ovrtx_render_product_frame_output_t const& frame =
                product.output_frames[f];
            for (size_t v = 0; v < frame.render_var_count; ++v) {
                ovrtx_render_product_render_var_output_t const& var =
                    frame.output_render_vars[v];
                if (string_equals(var.render_var_name, render_var_name)) {
                    return var.output_handle;
                }
            }
        }
    }
    return OVRTX_INVALID_HANDLE;
}
// [/snippet:find-render-var-output-helper]

// [snippet:find-tensor-helper]
// A composite render variable exposes named tensors. Find the channel tensor
// requested in lidar_example.usda.
ovrtx_render_var_tensor_t const* find_tensor(ovrtx_render_var_output_t const& output,
                                             char const* name)
{
    // Tensor names are ovrtx strings, so compare by length and content.
    for (size_t i = 0; i < output.num_tensors; ++i) {
        ovrtx_render_var_tensor_t const& tensor = output.tensors[i];
        if (tensor.name && string_equals(*tensor.name, name)) {
            return &tensor;
        }
    }
    return nullptr;
}
// [/snippet:find-tensor-helper]

// [snippet:cpu-tensor-helper]
// Return host-readable data for a named channel in the CPU-mapped composite
// output. The template type matches the DLTensor dtype requested by the USD.
template <typename T>
T const* cpu_tensor_data(ovrtx_render_var_output_t const& output,
                         char const* name)
{
    ovrtx_render_var_tensor_t const* tensor = find_tensor(output, name);

    // After CPU mapping, each requested channel should expose a CPU DLTensor.
    if (!tensor || !tensor->dl || tensor->dl->device.device_type != kDLCPU ||
        !tensor->dl->data) {
        std::cerr << "Lidar PointCloud tensor '" << name
                  << "' is not available on CPU\n";
        return nullptr;
    }
    return static_cast<T const*>(tensor->dl->data);
}
// [/snippet:cpu-tensor-helper]

// [snippet:read-lidar-pointcloud]
// Read one mapped lidar PointCloud. Counts is the valid point count; Intensity
// and TimeOffsetNs are per-point channels over that valid range.
bool print_pointcloud_summary(ovrtx_render_var_output_t const& output)
{
    // The USD also requests Coordinates; this example only needs scalar and
    // time channels for the printed statistics.
    int32_t const* counts_data = cpu_tensor_data<int32_t>(output, "Counts");
    float const* intensity_data = cpu_tensor_data<float>(output, "Intensity");
    int32_t const* time_offset_data =
        cpu_tensor_data<int32_t>(output, "TimeOffsetNs");

    if (!counts_data || !intensity_data || !time_offset_data) {
        return false;
    }

    // Counts is a scalar tensor containing the number of valid point entries.
    int32_t const valid_point_count = counts_data[0];
    if (valid_point_count <= 0) {
        std::cerr << "Expected at least one valid lidar point, got "
                  << valid_point_count << "\n";
        return false;
    }

    double intensity_sum = 0.0;
    int32_t max_time_offset_ns = time_offset_data[0];

    // Only the first Counts entries are valid in each per-point channel.
    for (int32_t i = 0; i < valid_point_count; ++i) {
        const float intensity = intensity_data[i];
        if (!std::isfinite(intensity)) {
            std::cerr << "Intensity tensor contained a non-finite value\n";
            return false;
        }
        intensity_sum += intensity;
        max_time_offset_ns = std::max(max_time_offset_ns, time_offset_data[i]);
    }

    const double mean_intensity =
        intensity_sum / static_cast<double>(valid_point_count);
    std::cout << "valid points=" << valid_point_count
              << ", mean intensity=" << mean_intensity
              << ", max point time offset to point cloud frame start=" << max_time_offset_ns << " ns\n";
    return true;
}
// [/snippet:read-lidar-pointcloud]

// [snippet:destroy-results-helper]
// Result handles own step output memory and must be destroyed after use.
bool destroy_step_results(ovrtx_renderer_t* renderer,
                          ovrtx_step_result_handle_t* step_handle)
{
    if (*step_handle == OVRTX_INVALID_HANDLE) {
        return true;
    }

    ovrtx_result_t result = ovrtx_destroy_results(renderer, *step_handle);

    // Clear the handle so repeated cleanup attempts are harmless.
    *step_handle = OVRTX_INVALID_HANDLE;
    return check_api_result(result, "destroy_results");
}
// [/snippet:destroy-results-helper]

// ovstage owns scene ingest in attach mode. These helpers mirror the minimal /
// status-queries examples: surface ovstage errors and block on ovstage's own
// async ops (population + write-floor commit) the same way wait_for_success
// blocks on ovrtx render ops above.
bool print_ovstage_error(ovstage_instance_t* stage,
                         ovstage_api_status_t status,
                         std::string_view operation)
{
    ovx_string_t error = ovstage_population_get_last_error();
    if ((!error.ptr || error.length == 0) && stage) {
        error = ovstage_get_last_error();
    }

    std::cerr << "ovstage " << operation << " failed (" << static_cast<int>(status) << ")";
    if (error.ptr && error.length > 0) {
        std::cerr << ": " << std::string_view(error.ptr, error.length);
    }
    std::cerr << "\n";
    return false;
}

// Wait for an ovstage population op (e.g. open_usd_from_file). Returns true on
// failure so callers can early-out, matching the enqueue/wait pattern above.
bool wait_population_op(ovstage_instance_t* stage,
                        ovstage_population_enqueue_result_t const& enqueue,
                        std::string_view operation)
{
    if (enqueue.status != OVSTAGE_OK) {
        print_ovstage_error(stage, enqueue.status, operation);
        return true;
    }

    ovstage_population_op_wait_result_t wait_result {};
    ovstage_api_status_t status = ovstage_population_wait_op(
        stage, enqueue.op_index, OVSTAGE_TIMEOUT_INFINITE, &wait_result);
    if (status != OVSTAGE_OK) {
        print_ovstage_error(stage, status, operation);
        return true;
    }
    for (size_t i = 0; i < wait_result.error_op_id_count; ++i) {
        ovstage_population_op_id_t op_id = wait_result.error_op_ids[i];
        ovx_string_t error = ovstage_population_get_last_op_error(op_id);
        std::cerr << "ovstage " << operation << ": op " << op_id << " failed";
        if (error.ptr && error.length > 0) {
            std::cerr << ": " << std::string_view(error.ptr, error.length);
        }
        std::cerr << "\n";
    }
    return wait_result.error_op_id_count != 0;
}

// Wait for an ovstage instance op (e.g. advance_write_floor).
bool wait_ovstage_op(ovstage_instance_t* stage,
                     ovstage_enqueue_result_t const& enqueue,
                     std::string_view operation)
{
    if (enqueue.status != OVSTAGE_OK) {
        print_ovstage_error(stage, enqueue.status, operation);
        return true;
    }

    ovstage_op_wait_result_t wait_result {};
    ovstage_api_status_t status =
        ovstage_wait_op(stage, enqueue.op_index, OVSTAGE_TIMEOUT_INFINITE, &wait_result);
    if (status != OVSTAGE_OK) {
        print_ovstage_error(stage, status, operation);
        return true;
    }
    for (size_t i = 0; i < wait_result.error_op_id_count; ++i) {
        ovstage_op_id_t op_id = wait_result.error_op_ids[i];
        ovx_string_t error = ovstage_get_last_op_error(stage, op_id);
        std::cerr << "ovstage " << operation << ": op " << op_id << " failed";
        if (error.ptr && error.length > 0) {
            std::cerr << ": " << std::string_view(error.ptr, error.length);
        }
        std::cerr << "\n";
    }
    return wait_result.error_op_id_count != 0;
}

// Commit an ordinal's writes so the attached renderer can see them. ovstage
// gates renderable state behind the write floor; ovrtx_step_with_stage renders
// the committed ordinal.
bool commit_ovstage_ordinal(ovstage_instance_t* stage, ovstage_ordinal_t ordinal)
{
    ovstage_write_floor_desc_t write_floor {};
    write_floor.ordinal = ordinal;
    write_floor.scope = OVSTAGE_SCOPE_ALL;
    return wait_ovstage_op(stage, ovstage_advance_write_floor(stage, &write_floor),
                           "advance_write_floor");
}

} // namespace

int main(int argc, char* argv[])
{
    ovrtx_renderer_t* renderer = nullptr;
    ovstage_instance_t* stage = nullptr;
    bool stage_attached = false;
    // ovstage gates renderable state behind an ordinal-keyed write floor. One
    // ordinal is enough for this static scene: populate at it, commit it, render
    // it.
    ovstage_ordinal_t stage_ordinal = 1;
    ovrtx_enqueue_result_t enqueue_result = {};
    ovrtx_result_t result = {};
    ovx_string_t render_product_path = {};
    ovrtx_render_product_set_t render_products = {};

    // Load the scene copied next to the executable by CMake. argv[1] lets copied
    // builds run the same binary against another USDA file.
    // [snippet:resolve-default-scene-path]
    std::string defaultSceneFilePath =
        (getExecutableDir(argv[0]) / kDefaultSceneFileName).string();
    char const* sceneFilePath =
        (argc > 1) ? argv[1] : defaultSceneFilePath.c_str();
    // [/snippet:resolve-default-scene-path]

    // [snippet:create-renderer]
    // The STATIC ovrtx loader resolves the ${executable_dir} token to the running
    // executable's directory; ovrtx_setup_runtime() links the package bin beside
    // the exe as "ovrtx/", which we hand the loader as the binary package root.
    ovx_string_t ovrtx_package_root = {
        OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx",
        sizeof(OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx") - 1};
    // Enable motion BVH: required by the lidar sensor pipeline. Sensor output
    // fetch/map is a renderer-side concern and stays on the ovrtx APIs; ovstage
    // only takes over scene ingest and drives stepping via ovrtx_step_with_stage.
    ovrtx_config_entry_t config_entries[] = {
        ovrtx_config_entry_binary_package_root_path(ovrtx_package_root),
        ovrtx_config_entry_motion_bvh(OVRTX_MOTION_BVH_ENABLE),
    };
    ovrtx_config_t config = { config_entries, 2 };

    // Create the renderer before attaching a stage or populating the scene.
    result = ovrtx_create_renderer(&config, &renderer);
    if (!check_api_result(result, "create_renderer")) {
        return 1;
    }
    // [/snippet:create-renderer]

    // Tear down in reverse order on every exit path: detach the stage from the
    // renderer, destroy the ovstage instance, destroy the renderer, then release
    // the ovstage loader. Safe to call at any stage of setup.
    auto cleanup = [&](int exit_code) {
        int result_code = exit_code;
        if (stage_attached) {
            if (!check_api_result(ovrtx_detach_ovstage(renderer), "detach_ovstage")) {
                result_code = 1;
            }
        }
        if (stage) {
            ovstage_api_status_t stage_status = ovstage_destroy_instance(stage);
            if (stage_status != OVSTAGE_OK) {
                print_ovstage_error(stage, stage_status, "destroy_instance");
                result_code = 1;
            }
        }
        if (renderer) {
            if (!check_api_result(ovrtx_destroy_renderer(renderer), "destroy_renderer")) {
                result_code = 1;
            }
        }
        // Release the ovstage static loader (unloads ovstage.dll). Safe even if
        // ovstage_initialize failed or was never reached.
        ovstage_shutdown();
        return result_code;
    };

    // [snippet:load-lidar-scene]
    // Initialize the STATIC ovstage loader with its package root, mirroring the
    // ovrtx setup above. ovstage_setup_runtime() links the package bin beside the
    // exe as "ovstage/" (next to "ovrtx/"). ovrtx_create_renderer() already loaded
    // the shared usd_ms runtime; ovstage.dll loads lazily on the first ovstage
    // call and reuses it.
    ovx_string_t ovstage_package_root = {
        OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovstage",
        sizeof(OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovstage") - 1};
    ovstage_config_entry_t stage_config_entries[] = {
        ovstage_config_entry_binary_package_root_path(ovstage_package_root),
    };
    ovstage_config_t stage_config {};
    stage_config.entries = stage_config_entries;
    stage_config.entry_count =
        sizeof(stage_config_entries) / sizeof(stage_config_entries[0]);
    ovstage_api_status_t stage_init_status = ovstage_initialize(&stage_config);
    if (stage_init_status != OVSTAGE_OK) {
        print_ovstage_error(nullptr, stage_init_status, "initialize");
        return cleanup(1);
    }

    // Create the ovstage instance and attach it to the renderer (BORROW mode).
    ovstage_instance_desc_t stage_desc {};
    stage_desc.name = "lidar";
    ovstage_api_status_t stage_result = ovstage_create_instance(&stage_desc, &stage);
    if (stage_result != OVSTAGE_OK) {
        print_ovstage_error(stage, stage_result, "create_instance");
        return cleanup(1);
    }

    result = ovrtx_attach_ovstage(renderer, stage);
    if (!check_api_result(result, "attach_ovstage")) {
        return cleanup(1);
    }
    stage_attached = true;

    // Populate the stage from the local USD file at our ordinal, then commit the
    // write floor so the attached renderer can see it.
    std::cout << "Loading lidar scene from " << sceneFilePath << "...\n";
    ovstage_population_enqueue_result_t populate_result =
        ovstage_population_open_usd_from_file(stage,
                                              to_ovx_string(sceneFilePath),
                                              stage_ordinal,
                                              /* time = */ 0.0,
                                              OVSTAGE_POPULATION_DOMAIN_RENDERING);
    if (wait_population_op(stage, populate_result, "population_open_usd_from_file") ||
        commit_ovstage_ordinal(stage, stage_ordinal)) {
        return cleanup(1);
    }
    // [/snippet:load-lidar-scene]

    // [snippet:configure-render-product]
    render_product_path = { kRenderProductPath, std::strlen(kRenderProductPath) };
    render_products.render_products = &render_product_path;
    render_products.num_render_products = 1;
    // [/snippet:configure-render-product]

    // [snippet:warm-up-lidar]
    // Render a few warmup frames without reading outputs. In attach mode we drive
    // the renderer with ovrtx_step_with_stage(), rendering the ordinal we
    // committed above.
    for (int i = 0; i < kWarmupStepCount; ++i) {
        ovrtx_step_result_handle_t warmup_handle = OVRTX_INVALID_HANDLE;

        enqueue_result =
            ovrtx_step_with_stage(renderer,
                                  render_products,
                                  kStepDeltaTimeSeconds,
                                  stage_ordinal,
                                  &warmup_handle);
        if (!check_api_result(enqueue_result, "step") ||
            !wait_for_success(renderer, enqueue_result.op_index, "step")) {
            destroy_step_results(renderer, &warmup_handle);
            return cleanup(1);
        }
        if (!destroy_step_results(renderer, &warmup_handle)) {
            return cleanup(1);
        }
    }
    // [/snippet:warm-up-lidar]

    // [snippet:step-lidar-pointcloud]
    ovrtx_step_result_handle_t step_handle = OVRTX_INVALID_HANDLE;

    // Render one lidar frame from the committed ordinal and keep the result
    // handle for fetching.
    enqueue_result =
        ovrtx_step_with_stage(renderer,
                              render_products,
                              kStepDeltaTimeSeconds,
                              stage_ordinal,
                              &step_handle);
    if (!check_api_result(enqueue_result, "step") ||
        !wait_for_success(renderer, enqueue_result.op_index, "step")) {
        destroy_step_results(renderer, &step_handle);
        return cleanup(1);
    }

    // Fetch the completed step and locate the PointCloud render variable.
    ovrtx_render_product_set_outputs_t outputs = {};
    result = ovrtx_fetch_results(
        renderer, step_handle, ovrtx_timeout_infinite, &outputs);
    if (!check_api_result(result, "fetch_results")) {
        destroy_step_results(renderer, &step_handle);
        return cleanup(1);
    }

    ovrtx_render_var_output_handle_t pointcloud_handle =
        find_render_var_output(outputs, "PointCloud");
    if (pointcloud_handle == OVRTX_INVALID_HANDLE) {
        std::cerr << "PointCloud render var output not found\n";
        destroy_step_results(renderer, &step_handle);
        return cleanup(1);
    }

    // Map the composite PointCloud render variable to CPU. The mapped output
    // exposes one DLTensor per channel requested in the USD.
    ovrtx_map_output_description_t map_desc = {};
    map_desc.device_type = OVRTX_MAP_DEVICE_TYPE_CPU;
    ovrtx_render_var_output_t pointcloud_output = {};
    result = ovrtx_map_render_var_output(renderer,
                                         pointcloud_handle,
                                         &map_desc,
                                         ovrtx_timeout_infinite,
                                         &pointcloud_output);
    if (!check_api_result(result, "map_render_var_output")) {
        destroy_step_results(renderer, &step_handle);
        return cleanup(1);
    }

    const bool printed_summary = print_pointcloud_summary(pointcloud_output);

    // Always unmap after reading the CPU DLTensor views.
    ovrtx_cuda_sync_t no_sync = {};
    result = ovrtx_unmap_render_var_output(
        renderer, pointcloud_output.map_handle, no_sync);
    if (!check_api_result(result, "unmap_render_var_output") ||
        !printed_summary) {
        destroy_step_results(renderer, &step_handle);
        return cleanup(1);
    }

    if (!destroy_step_results(renderer, &step_handle)) {
        return cleanup(1);
    }
    // [/snippet:step-lidar-pointcloud]

    return cleanup(0);
}
