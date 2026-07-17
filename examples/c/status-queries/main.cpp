// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include <ovrtx/ovrtx_config.h>
#include <ovrtx/ovrtx_types.h>
#include <ovrtx/ovrtx.h>
#include <ovstage/ovstage.h>
#include <ovstage/ovstage_config.h>

#include <cstring>
#include <filesystem>
#include <iostream>
#include <string>
#include <string_view>

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "../minimal/stb_image_write.h"

// [snippet:check-error-helper]
template <typename ResultT>
static bool check_and_print_error(ResultT const& result,
                                  std::string_view operation) {
    if (result.status == OVRTX_API_ERROR) {
        ovx_string_t error = ovrtx_get_last_error();
        if (error.ptr && error.length > 0) {
            std::cerr << "ovrtx " << operation << " failed: "
                      << std::string_view(error.ptr, error.length) << std::endl;
        } else {
            std::cerr << "ovrtx " << operation << " failed" << std::endl;
        }
        return true;
    }
    return false;
}
// [/snippet:check-error-helper]

// [snippet:format-operation-status-c]
static char const* event_status_name(ovrtx_event_status_t state) {
    switch (state) {
        case OVRTX_EVENT_PENDING:
            return "PENDING";
        case OVRTX_EVENT_COMPLETED:
            return "COMPLETED";
        case OVRTX_EVENT_FAILURE:
            return "FAILURE";
    }
    return "UNKNOWN";
}

static bool print_operation_status(ovrtx_renderer_t* renderer,
                                   ovrtx_op_id_t op_id,
                                   std::string_view label) {
    ovrtx_op_status_t status {};
    ovrtx_result_t result = ovrtx_query_op_status(renderer, op_id, &status);
    if (check_and_print_error(result, "query_op_status")) {
        return true;
    }

    std::cerr << label << ": state=" << event_status_name(status.state);
    if (status.progress < 0.0) {
        std::cerr << " progress=indeterminate";
    } else {
        std::cerr << " progress=" << static_cast<int>(status.progress * 100.0) << "%";
    }

    for (size_t i = 0; i < status.counter_count; ++i) {
        ovrtx_op_counter_t const& counter = status.counters[i];
        std::string_view name(counter.name.ptr ? counter.name.ptr : "",
                              counter.name.ptr ? counter.name.length : 0);
        std::cerr << " " << name << "=" << counter.current << "/";
        if (counter.total == 0) {
            std::cerr << "unknown";
        } else {
            std::cerr << counter.total;
        }
    }
    std::cerr << std::endl;

    result = ovrtx_release_op_status(renderer, &status);
    return check_and_print_error(result, "release_op_status");
}
// [/snippet:format-operation-status-c]

static bool print_wait_errors(ovrtx_op_wait_result_t const& wait_result) {
    if (wait_result.num_error_ops == 0) {
        return false;
    }

    for (size_t i = 0; i < wait_result.num_error_ops; ++i) {
        ovx_string_t error = ovrtx_get_last_op_error(wait_result.error_op_ids[i]);
        std::cerr << "ovrtx operation " << wait_result.error_op_ids[i] << " failed";
        if (error.ptr && error.length > 0) {
            std::cerr << ": " << std::string_view(error.ptr, error.length);
        }
        std::cerr << std::endl;
    }
    return true;
}

// [snippet:wait-operation-with-status-c]
static bool wait_with_status(ovrtx_renderer_t* renderer,
                             ovrtx_op_id_t op_id,
                             std::string_view label) {
    ovrtx_op_wait_result_t wait_result {};
    ovrtx_result_t result =
        ovrtx_wait_op(renderer, op_id, ovrtx_timeout_t {1000000000}, &wait_result);
    while (result.status == OVRTX_API_TIMEOUT) {
        if (print_operation_status(renderer, op_id, label)) {
            return true;
        }
        result = ovrtx_wait_op(renderer, op_id, ovrtx_timeout_t {1000000000}, &wait_result);
    }

    if (check_and_print_error(result, "wait_op")) {
        return true;
    }
    return print_wait_errors(wait_result);
}
// [/snippet:wait-operation-with-status-c]

static bool print_shader_compile_status(ovrtx_renderer_t* renderer,
                                        ovrtx_op_id_t op_id) {
    ovrtx_op_status_t status {};
    ovrtx_result_t result = ovrtx_query_op_status(renderer, op_id, &status);
    if (check_and_print_error(result, "query_op_status")) {
        return true;
    }

    if (status.progress > 0.0) {
        std::cerr << "compiling shaders " << static_cast<int>(status.progress * 100.0)
                  << "%..." << std::endl;
    }

    result = ovrtx_release_op_status(renderer, &status);
    return check_and_print_error(result, "release_op_status");
}

static bool wait_for_shader_cache_step(ovrtx_renderer_t* renderer,
                                       ovrtx_op_id_t op_id) {
    ovrtx_op_wait_result_t wait_result {};
    ovrtx_result_t result =
        ovrtx_wait_op(renderer, op_id, ovrtx_timeout_t {1000000000}, &wait_result);
    while (result.status == OVRTX_API_TIMEOUT) {
        if (print_shader_compile_status(renderer, op_id)) {
            return true;
        }
        result = ovrtx_wait_op(renderer, op_id, ovrtx_timeout_t {1000000000}, &wait_result);
    }

    if (check_and_print_error(result, "wait_op")) {
        return true;
    }
    return print_wait_errors(wait_result);
}

// Find the handle of the given output in the given set of outputs
static ovrtx_render_var_output_handle_t
find_output(ovrtx_render_product_set_outputs_t const& outputs, char const* output_to_find);

static bool print_ovstage_error(ovstage_instance_t* stage,
                                ovstage_api_status_t status,
                                std::string_view operation) {
    ovx_string_t error = ovstage_population_get_last_error();
    if ((!error.ptr || error.length == 0) && stage) {
        error = ovstage_get_last_error();
    }

    std::cerr << "ovstage " << operation << " failed (" << static_cast<int>(status) << ")";
    if (error.ptr && error.length > 0) {
        std::cerr << ": " << std::string_view(error.ptr, error.length);
    }
    std::cerr << std::endl;
    return true;
}

static bool wait_population_op(ovstage_instance_t* stage,
                               ovstage_population_enqueue_result_t const& enqueue,
                               std::string_view operation) {
    if (enqueue.status != OVSTAGE_OK) {
        return print_ovstage_error(stage, enqueue.status, operation);
    }

    ovstage_population_op_wait_result_t wait_result {};
    ovstage_api_status_t status = ovstage_population_wait_op(
        stage, enqueue.op_index, OVSTAGE_TIMEOUT_INFINITE, &wait_result);
    if (status != OVSTAGE_OK) {
        return print_ovstage_error(stage, status, operation);
    }
    for (size_t i = 0; i < wait_result.error_op_id_count; ++i) {
        ovstage_population_op_id_t op_id = wait_result.error_op_ids[i];
        ovx_string_t error = ovstage_population_get_last_op_error(op_id);
        std::cerr << "ovstage " << operation << ": op " << op_id << " failed";
        if (error.ptr && error.length > 0) {
            std::cerr << ": " << std::string_view(error.ptr, error.length);
        }
        std::cerr << std::endl;
    }
    return wait_result.error_op_id_count != 0;
}

static bool wait_ovstage_op(ovstage_instance_t* stage,
                            ovstage_enqueue_result_t const& enqueue,
                            std::string_view operation) {
    if (enqueue.status != OVSTAGE_OK) {
        return print_ovstage_error(stage, enqueue.status, operation);
    }

    ovstage_op_wait_result_t wait_result {};
    ovstage_api_status_t status =
        ovstage_wait_op(stage, enqueue.op_index, OVSTAGE_TIMEOUT_INFINITE, &wait_result);
    if (status != OVSTAGE_OK) {
        return print_ovstage_error(stage, status, operation);
    }
    for (size_t i = 0; i < wait_result.error_op_id_count; ++i) {
        ovstage_op_id_t op_id = wait_result.error_op_ids[i];
        ovx_string_t error = ovstage_get_last_op_error(stage, op_id);
        std::cerr << "ovstage " << operation << ": op " << op_id << " failed";
        if (error.ptr && error.length > 0) {
            std::cerr << ": " << std::string_view(error.ptr, error.length);
        }
        std::cerr << std::endl;
    }
    return wait_result.error_op_id_count != 0;
}

static bool commit_ovstage_ordinal(ovstage_instance_t* stage, ovstage_ordinal_t ordinal) {
    ovstage_write_floor_desc_t write_floor {};
    write_floor.ordinal = ordinal;
    write_floor.scope = OVSTAGE_SCOPE_ALL;
    return wait_ovstage_op(stage, ovstage_advance_write_floor(stage, &write_floor),
                           "advance_write_floor");
}

int main() {
    ovrtx_renderer_t* renderer = nullptr;
    ovstage_instance_t* stage = nullptr;
    bool stage_attached = false;
    ovstage_ordinal_t stage_ordinal = 1;
    ovrtx_result_t result;

    // [snippet:create-renderer]
    // Create the renderer, optionally providing configuration settings.
    //
    // The STATIC ovrtx loader resolves the ${executable_dir} token to the running
    // executable's directory, so we hand it the token instead of computing the path
    // in client code. ovrtx_setup_runtime() links the package bin beside the exe as
    // "ovrtx/".
    ovx_string_t ovrtx_package_root = {
        OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx",
        sizeof(OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx") - 1};
    std::filesystem::path output_dir = "_output";
    std::filesystem::create_directories(output_dir);
    std::string log_path = (output_dir / "status-queries-ovrtx.log").string();
    ovx_string_t log_path_string = {log_path.c_str(), log_path.size()};
    ovrtx_config_entry_t config_entries[] = {
        ovrtx_config_entry_binary_package_root_path(ovrtx_package_root),
        ovrtx_config_entry_log_file_path(log_path_string),
    };
    ovrtx_config_t config {config_entries, 2};
    std::cerr << "Creating renderer..." << std::endl;
    result = ovrtx_create_renderer(&config, &renderer);
    if (check_and_print_error(result, "create_renderer")) {
        return 1;
    }
    std::cerr << "Renderer created." << std::endl;
    // [/snippet:create-renderer]

    auto cleanup = [&](int exit_code) {
        int result_code = exit_code;
        if (stage_attached) {
            result = ovrtx_detach_ovstage(renderer);
            if (check_and_print_error(result, "detach_ovstage")) {
                result_code = 1;
            }
        }
        if (stage) {
            ovstage_api_status_t stage_result = ovstage_destroy_instance(stage);
            if (stage_result != OVSTAGE_OK) {
                print_ovstage_error(stage, stage_result, "destroy_instance");
                result_code = 1;
            }
        }
        if (renderer) {
            result = ovrtx_destroy_renderer(renderer);
            if (check_and_print_error(result, "destroy_renderer")) {
                result_code = 1;
            }
        }
        // Release the ovstage static loader (unloads ovstage.dll). Safe to call
        // even if ovstage_initialize failed or was never reached.
        ovstage_shutdown();
        return result_code;
    };

    // Initialize the STATIC ovstage loader with its package root before any other
    // ovstage_* call, mirroring the ovrtx setup above. ovstage_setup_runtime() links
    // the package bin beside the exe as "ovstage/" (next to "ovrtx/").
    // ovrtx_create_renderer() above already loaded the shared usd_ms runtime;
    // ovstage.dll loads lazily on the first ovstage call and reuses that runtime.
    ovx_string_t ovstage_package_root = {
        OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovstage",
        sizeof(OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovstage") - 1};
    ovstage_config_entry_t stage_config_entries[] = {
        ovstage_config_entry_binary_package_root_path(ovstage_package_root),
    };
    ovstage_config_t stage_config {};
    stage_config.entries = stage_config_entries;
    stage_config.entry_count = sizeof(stage_config_entries) / sizeof(stage_config_entries[0]);
    ovstage_api_status_t stage_init_status = ovstage_initialize(&stage_config);
    if (stage_init_status != OVSTAGE_OK) {
        print_ovstage_error(nullptr, stage_init_status, "initialize");
        return cleanup(1);
    }

    // [snippet:load-usd-with-status-c]
    char const* usd_url = "https://omniverse-content-production.s3.us-west-2.amazonaws.com/Samples/Robot-OVRTX/robot-ovrtx.usda";

    std::cerr << "Opening " << usd_url << "..." << std::endl;
    ovstage_instance_desc_t stage_desc {};
    stage_desc.name = "status-queries";
    ovstage_api_status_t stage_result = ovstage_create_instance(&stage_desc, &stage);
    if (stage_result != OVSTAGE_OK) {
        print_ovstage_error(stage, stage_result, "create_instance");
        return cleanup(1);
    }

    result = ovrtx_attach_ovstage(renderer, stage);
    if (check_and_print_error(result, "attach_ovstage")) {
        return cleanup(1);
    }
    stage_attached = true;

    ovstage_population_enqueue_result_t populate_result =
        ovstage_population_open_usd_from_file(stage,
                                              {usd_url, strlen(usd_url)},
                                              stage_ordinal,
                                              /* time = */ 0.0,
                                              OVSTAGE_POPULATION_DOMAIN_RENDERING);
    if (wait_population_op(stage, populate_result, "population_open_usd_from_file") ||
        commit_ovstage_ordinal(stage, stage_ordinal)) {
        return cleanup(1);
    }
    std::cerr << "USD loaded." << std::endl;
    // [/snippet:load-usd-with-status-c]

    ovrtx_render_product_set_t render_products = {};
    ovx_string_t render_product_str = {"/Render/Camera", strlen("/Render/Camera")};
    render_products.render_products = &render_product_str;
    render_products.num_render_products = 1;

    // [snippet:compile-shader-cache-with-status-c]
    ovrtx_step_result_handle_t shader_cache_step_handle = 0;
    ovrtx_enqueue_result_t enqueue_result =
        ovrtx_step_with_stage(renderer, render_products, 1.0 / 60.0, stage_ordinal, &shader_cache_step_handle);
    if (check_and_print_error(enqueue_result, "step")) {
        return cleanup(1);
    }
    if (wait_for_shader_cache_step(renderer, enqueue_result.op_index)) {
        ovrtx_destroy_results(renderer, shader_cache_step_handle);
        return cleanup(1);
    }
    result = ovrtx_destroy_results(renderer, shader_cache_step_handle);
    if (check_and_print_error(result, "destroy_results")) {
        return cleanup(1);
    }
    // [/snippet:compile-shader-cache-with-status-c]

    // [snippet:step-with-status-c]
    std::cerr << "Stepping renderer..." << std::endl;
    ovrtx_step_result_handle_t step_result_handle = 0;
    enqueue_result =
        ovrtx_step_with_stage(renderer, render_products, 1.0 / 60.0, stage_ordinal, &step_result_handle);
    if (check_and_print_error(enqueue_result, "step")) {
        return cleanup(1);
    }
    if (wait_with_status(renderer, enqueue_result.op_index, "step")) {
        ovrtx_destroy_results(renderer, step_result_handle);
        return cleanup(1);
    }
    std::cerr << "Stepped renderer." << std::endl;
    // [/snippet:step-with-status-c]

    // [snippet:fetch-results]
    std::cerr << "Fetching results..." << std::endl;
    ovrtx_render_product_set_outputs_t outputs = {};
    result = ovrtx_fetch_results(
        renderer, step_result_handle, ovrtx_timeout_infinite, &outputs);
    if (check_and_print_error(result, "fetch_results")) {
        ovrtx_destroy_results(renderer, step_result_handle);
        return cleanup(1);
    }

    // Find LdrColor in outputs
    ovrtx_render_var_output_handle_t ldrcolor_output_handle =
        find_output(outputs, "LdrColor");
    if (ldrcolor_output_handle == OVRTX_INVALID_HANDLE) {
        std::cerr << "LdrColor output not found" << std::endl;
        ovrtx_destroy_results(renderer, step_result_handle);
        return cleanup(1);
    }
    std::cerr << "Fetched results." << std::endl;
    // [/snippet:fetch-results]

    // [snippet:map-rendered-output-cpu]
    // Map rendered output so that it can be accessed on the CPU
    ovrtx_map_output_description_t map_desc = {};
    map_desc.device_type = OVRTX_MAP_DEVICE_TYPE_CPU;
    ovrtx_render_var_output_t rendered_output = {};
    result = ovrtx_map_render_var_output(renderer,
                                       ldrcolor_output_handle,
                                       &map_desc,
                                       ovrtx_timeout_infinite,
                                       &rendered_output);
    if (check_and_print_error(result, "map_render_var_output")) {
        ovrtx_destroy_results(renderer, step_result_handle);
        return cleanup(1);
    }

    // LdrColor is a single-tensor render variable; read tensors[0].
    // Image outputs follow shape [H, W, C] with dtype.lanes == 1.
    if (rendered_output.num_tensors != 1) {
        std::cerr << "Unexpected LdrColor render variable: expected 1 tensor, got " << rendered_output.num_tensors << "." << std::endl;
        ovrtx_cuda_sync_t no_sync = {};
        ovrtx_unmap_render_var_output(renderer, rendered_output.map_handle, no_sync);
        ovrtx_destroy_results(renderer, step_result_handle);
        return cleanup(1);
    }
    DLTensor const& tensor = *rendered_output.tensors[0].dl;
    if (tensor.ndim != 3 || !tensor.shape || tensor.shape[2] != 4 || tensor.dtype.lanes != 1) {
        std::cerr << "Unexpected LdrColor tensor layout. Expected [H, W, 4] and dtype.lanes == 1." << std::endl;
        ovrtx_cuda_sync_t no_sync = {};
        ovrtx_unmap_render_var_output(renderer, rendered_output.map_handle, no_sync);
        ovrtx_destroy_results(renderer, step_result_handle);
        return cleanup(1);
    }
    int width = static_cast<int>(tensor.shape[1]);
    int height = static_cast<int>(tensor.shape[0]);
    stbi_write_png("out.png",
                   width,
                   height,
                   /* components = */ 4,
                   tensor.data,
                   /* row stride in bytes = */ 4 * width);
    // [/snippet:map-rendered-output-cpu]

    // [snippet:unmap-and-cleanup]
    // Unmap output
    ovrtx_cuda_sync_t no_sync = {};
    result = ovrtx_unmap_render_var_output(
        renderer, rendered_output.map_handle, no_sync);
    if (check_and_print_error(result, "unmap_render_var_output")) {
        ovrtx_destroy_results(renderer, step_result_handle);
        return cleanup(1);
    }

    // Clean up resources (ovrtx will warn if results are leaked)
    result = ovrtx_destroy_results(renderer, step_result_handle);
    if (check_and_print_error(result, "destroy_results")) {
        return cleanup(1);
    }
    // [/snippet:unmap-and-cleanup]

    return cleanup(0);
}

// [snippet:find-output-helper]
static ovrtx_render_var_output_handle_t
find_output(ovrtx_render_product_set_outputs_t const& outputs,
            char const* output_to_find) {
    for (size_t i = 0; i < outputs.output_count; ++i) {
        ovrtx_render_product_output_t const& product_output =
            outputs.outputs[i];
        for (size_t f = 0; f < product_output.output_frame_count; ++f) {
            ovrtx_render_product_frame_output_t const& frame =
                product_output.output_frames[f];
            for (size_t v = 0; v < frame.render_var_count; ++v) {
                ovrtx_render_product_render_var_output_t const& var =
                    frame.output_render_vars[v];
                if (var.render_var_name.ptr &&
                    strncmp(var.render_var_name.ptr,
                            output_to_find,
                            var.render_var_name.length) == 0) {
                    return var.output_handle;
                }
            }
        }
    }
    return OVRTX_INVALID_HANDLE;
}
// [/snippet:find-output-helper]
