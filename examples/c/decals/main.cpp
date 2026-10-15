// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary

#include <ovrtx/ovrtx_config.h>
#include <ovrtx/ovrtx.h>
#include <ovstage/ovstage.h>

#include <cstring>
#include <filesystem>
#include <iostream>
#include <string>
#include <string_view>

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

template <typename T>
static bool failed(T const& result, std::string_view operation) {
    if (result.status != OVRTX_API_ERROR) {
        return false;
    }
    ovx_string_t error = ovrtx_get_last_error();
    std::cerr << "ovrtx " << operation << " failed";
    if (error.ptr && error.length) {
        std::cerr << ": " << std::string_view(error.ptr, error.length);
    }
    std::cerr << std::endl;
    return true;
}

static bool wait_population(ovstage_instance_t* stage,
                            ovstage_population_enqueue_result_t enqueue) {
    if (enqueue.status != OVSTAGE_OK) {
        return true;
    }
    ovstage_population_op_wait_result_t wait_result {};
    return ovstage_population_wait_op(
               stage, enqueue.op_index, OVSTAGE_TIMEOUT_INFINITE, &wait_result) != OVSTAGE_OK ||
           wait_result.error_op_id_count != 0;
}

static bool wait_stage(ovstage_instance_t* stage, ovstage_enqueue_result_t enqueue) {
    if (enqueue.status != OVSTAGE_OK) {
        return true;
    }
    ovstage_op_wait_result_t wait_result {};
    ovstage_api_status_t status =
        ovstage_wait_op(stage, enqueue.op_index, OVSTAGE_TIMEOUT_INFINITE, &wait_result);
    ovstage_release_op(stage, enqueue.op_index);
    return status != OVSTAGE_OK || wait_result.error_op_id_count != 0;
}

static bool report_wait_errors(ovrtx_op_wait_result_t const& wait_result) {
    if (wait_result.num_error_ops == 0) {
        return false;
    }

    for (size_t i = 0; i < wait_result.num_error_ops; ++i) {
        ovrtx_op_id_t op_id = wait_result.error_op_ids[i];
        ovx_string_t error = ovrtx_get_last_op_error(op_id);
        std::cerr << "ovrtx operation " << op_id << " failed";
        if (error.ptr && error.length) {
            std::cerr << ": " << std::string_view(error.ptr, error.length);
        }
        std::cerr << std::endl;
    }
    return true;
}

static ovrtx_render_var_output_handle_t find_ldr_color(
    ovrtx_render_product_set_outputs_t const& outputs) {
    for (size_t i = 0; i < outputs.output_count; ++i) {
        auto const& product = outputs.outputs[i];
        for (size_t f = 0; f < product.output_frame_count; ++f) {
            auto const& frame = product.output_frames[f];
            for (size_t v = 0; v < frame.render_var_count; ++v) {
                auto const& render_var = frame.output_render_vars[v];
                if (render_var.render_var_path.ptr &&
                    std::string_view(render_var.render_var_path.ptr,
                                     render_var.render_var_path.length) ==
                        "/Render/Camera/LdrColor") {
                    return render_var.output_handle;
                }
            }
        }
    }
    return OVRTX_INVALID_HANDLE;
}

int main(int argc, char** argv) {
    ovrtx_renderer_t* renderer = nullptr;
    ovstage_instance_t* stage = nullptr;
    bool attached = false;

    ovrtx_config_t renderer_config {};
#ifdef OVRTX_EXAMPLE_STATIC_LOADERS
    ovx_string_t ovrtx_root = {
        OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx",
        sizeof(OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx") - 1};
    ovrtx_config_entry_t renderer_entries[] = {
        ovrtx_config_entry_binary_package_root_path(ovrtx_root),
    };
    renderer_config.entries = renderer_entries;
    renderer_config.entry_count = 1;
#endif

    ovrtx_result_t result = ovrtx_register_schema_paths(&renderer_config);
    if (failed(result, "register_schema_paths") ||
        failed(ovrtx_create_renderer(&renderer_config, &renderer), "create_renderer")) {
        return 1;
    }

    auto cleanup = [&](int code) {
        if (attached) {
            failed(ovrtx_detach_ovstage(renderer), "detach_ovstage");
        }
        if (renderer) {
            failed(ovrtx_destroy_renderer(renderer), "destroy_renderer");
        }
        if (stage) {
            ovstage_destroy_instance(stage);
        }
        ovstage_shutdown();
        return code;
    };

    ovstage_config_t stage_config {};
#ifdef OVRTX_EXAMPLE_STATIC_LOADERS
    ovx_string_t ovstage_root = {
        OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovstage",
        sizeof(OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovstage") - 1};
    ovstage_config_entry_t stage_entries[] = {
        ovstage_config_entry_binary_package_root_path(ovstage_root),
    };
    stage_config.entries = stage_entries;
    stage_config.entry_count = 1;
#endif
    if (ovstage_initialize(&stage_config) != OVSTAGE_OK) {
        return cleanup(1);
    }
    ovstage_instance_desc_t stage_desc {};
    stage_desc.name = "decals";
    if (ovstage_create_instance(&stage_desc, &stage) != OVSTAGE_OK ||
        failed(ovrtx_attach_ovstage(renderer, stage), "attach_ovstage")) {
        return cleanup(1);
    }
    attached = true;

    // [snippet:doc-decals-c-render]
    constexpr ovstage_ordinal_t ordinal = 1;
    std::filesystem::path executable_dir =
        std::filesystem::absolute(argc > 0 ? argv[0] : "decals").parent_path();
    std::string scene_path = (executable_dir / "ovrtx-test-decals.usda").string();
    auto populate = ovstage_population_open_usd_from_file(
        stage,
        {scene_path.c_str(), scene_path.size()},
        ordinal,
        0.0,
        OVSTAGE_POPULATION_DOMAIN_RENDERING);
    ovstage_write_floor_desc_t floor {ordinal, OVSTAGE_SCOPE_ALL};
    if (wait_population(stage, populate) ||
        wait_stage(stage, ovstage_advance_write_floor(stage, &floor))) {
        std::cerr << "Could not populate the decal scene." << std::endl;
        return cleanup(1);
    }

    ovx_string_t product_path = {"/Render/Camera", strlen("/Render/Camera")};
    ovrtx_render_product_set_t render_products {&product_path, 1};
    ovrtx_step_result_handle_t final_handle = OVRTX_INVALID_HANDLE;
    for (int frame = 0; frame <= 40; ++frame) {
        ovrtx_step_result_handle_t step_handle = OVRTX_INVALID_HANDLE;
        auto enqueue = ovrtx_step_with_stage(
            renderer, render_products, 1.0 / 60.0, ordinal, &step_handle);
        ovrtx_op_wait_result_t wait_result {};
        if (failed(enqueue, "step") ||
            failed(ovrtx_wait_op(renderer,
                                 enqueue.op_index,
                                 ovrtx_timeout_infinite,
                                 &wait_result),
                   "wait_op") ||
            report_wait_errors(wait_result)) {
            return cleanup(1);
        }
        if (frame < 40) {
            ovrtx_destroy_results(renderer, step_handle);
        } else {
            final_handle = step_handle;
        }
    }
    // [/snippet:doc-decals-c-render]

    // [snippet:doc-decals-c-save]
    ovrtx_render_product_set_outputs_t outputs {};
    if (failed(ovrtx_fetch_results(
                   renderer, final_handle, ovrtx_timeout_infinite, &outputs),
               "fetch_results")) {
        return cleanup(1);
    }
    auto output_handle = find_ldr_color(outputs);
    ovrtx_map_output_description_t map_desc {};
    map_desc.device_type = OVRTX_MAP_DEVICE_TYPE_CPU;
    ovrtx_render_var_output_t output {};
    if (output_handle == OVRTX_INVALID_HANDLE ||
        failed(ovrtx_map_render_var_output(renderer,
                                           output_handle,
                                           &map_desc,
                                           ovrtx_timeout_infinite,
                                           &output),
               "map_render_var_output") ||
        output.num_tensors != 1) {
        return cleanup(1);
    }
    DLTensor const& pixels = *output.tensors[0].dl;
    int width = static_cast<int>(pixels.shape[1]);
    int height = static_cast<int>(pixels.shape[0]);
    std::filesystem::path output_path = executable_dir / "decals.png";
    bool wrote_output =
        stbi_write_png(output_path.string().c_str(), width, height, 4, pixels.data, 4 * width) != 0;
    ovrtx_cuda_sync_t no_sync {};
    ovrtx_unmap_render_var_output(renderer, output.map_handle, no_sync);
    ovrtx_destroy_results(renderer, final_handle);
    if (!wrote_output) {
        std::cerr << "Could not write " << output_path << std::endl;
        return cleanup(1);
    }
    std::cout << "Saved " << output_path << std::endl;
    // [/snippet:doc-decals-c-save]

    return cleanup(0);
}
