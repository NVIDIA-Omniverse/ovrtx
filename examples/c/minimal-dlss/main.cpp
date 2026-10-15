// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include <ovrtx/ovrtx.h>
#include <ovrtx/ovrtx_config.h>
#include <ovrtx/ovrtx_types.h>
#include <ovstage/ovstage.h>

#include <cstring>
#include <filesystem>
#include <iostream>
#include <string>
#include <string_view>

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "../minimal/stb_image_write.h"

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

// Find the handle of the given output in the given set of outputs
static ovrtx_render_var_output_handle_t
find_output(ovrtx_render_product_set_outputs_t const& outputs,
            char const* output_to_find);

static bool print_ovstage_error(ovstage_instance_t* stage,
                                ovstage_api_status_t status,
                                std::string_view operation) {
    ovx_string_t error = ovstage_population_get_last_error();
    if ((!error.ptr || error.length == 0) && stage) {
        error = ovstage_get_last_error();
    }

    std::cerr << "ovstage " << operation << " failed ("
              << static_cast<int>(status) << ")";
    if (error.ptr && error.length > 0) {
        std::cerr << ": " << std::string_view(error.ptr, error.length);
    }
    std::cerr << std::endl;
    return true;
}

static bool
wait_population_op(ovstage_instance_t* stage,
                   ovstage_population_enqueue_result_t const& enqueue,
                   std::string_view operation) {
    if (enqueue.status != OVSTAGE_OK) {
        return print_ovstage_error(stage, enqueue.status, operation);
    }

    ovstage_population_op_wait_result_t wait_result{};
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

    ovstage_op_wait_result_t wait_result{};
    ovstage_api_status_t status = ovstage_wait_op(
        stage, enqueue.op_index, OVSTAGE_TIMEOUT_INFINITE, &wait_result);
    ovstage_release_op(stage, enqueue.op_index);
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

static bool commit_ovstage_ordinal(ovstage_instance_t* stage,
                                   ovstage_ordinal_t ordinal) {
    ovstage_write_floor_desc_t write_floor{};
    write_floor.ordinal = ordinal;
    write_floor.scope = OVSTAGE_SCOPE_ALL;
    return wait_ovstage_op(stage,
                           ovstage_advance_write_floor(stage, &write_floor),
                           "advance_write_floor");
}

int main(int argc, char** argv) {
    if (argc < 2 || argc > 3) {
        std::cerr << "Usage: minimal-dlss <scene.usda> [output.png]\n";
        return 2;
    }
    const std::string scene_path =
        std::filesystem::absolute(argv[1]).generic_string();
    const char* output_path = argc == 3 ? argv[2] : "minimal-dlss.png";
    ovrtx_renderer_t* renderer = nullptr;
    ovstage_instance_t* stage = nullptr;
    bool stage_attached = false;
    ovstage_ordinal_t stage_ordinal = 1;
    ovrtx_result_t result;

    // Create the renderer, providing configuration settings.
    //
    ovrtx_config_t config{};

    // Publish ovrtx's schema paths before either runtime can initialize
    // OpenUSD.
    result = ovrtx_register_schema_paths(&config);
    if (check_and_print_error(result, "register_schema_paths")) {
        return 1;
    }

    std::cerr << "Creating renderer. The first run of the application will "
                 "take some time as shaders are compiled and cached..."
              << std::endl;
    result = ovrtx_create_renderer(&config, &renderer);
    if (check_and_print_error(result, "create_renderer")) {
        return 1;
    }
    std::cerr << "Renderer created." << std::endl;

    auto cleanup = [&](int exit_code) {
        int result_code = exit_code;
        if (stage_attached) {
            result = ovrtx_detach_ovstage(renderer);
            if (check_and_print_error(result, "detach_ovstage")) {
                result_code = 1;
            }
        }
        // Renderer before stage: a failed detach leaves the renderer attached.
        if (renderer) {
            result = ovrtx_destroy_renderer(renderer);
            if (check_and_print_error(result, "destroy_renderer")) {
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
        // Release ovstage process state. Safe even if initialization failed.
        ovstage_shutdown();
        return result_code;
    };

    // Populate an ovstage instance from USD, then attach it to the renderer.
    //
    // As well as just passing a URI to an existing layer, we could pass a USDA
    // string in order to compose a Stage at runtime. This can be very useful
    // for dynamically creating the RenderProducts etc. that define the render
    // output rather than editing the original layer to add them.
    //
    // A real application might want to load the USD layer and traverse it to
    // find either existing RenderProducts, and/or Cameras and allow the user to
    // select which one to render, and which RenderVars to output.
    const char* usd_url = scene_path.c_str();

    ovstage_config_t stage_config{};
    ovstage_api_status_t stage_init_status = ovstage_initialize(&stage_config);
    if (stage_init_status != OVSTAGE_OK) {
        print_ovstage_error(nullptr, stage_init_status, "initialize");
        return cleanup(1);
    }

    ovstage_instance_desc_t stage_desc{};
    stage_desc.name = "minimal-dlss";
    ovstage_api_status_t stage_result =
        ovstage_create_instance(&stage_desc, &stage);
    if (stage_result != OVSTAGE_OK) {
        print_ovstage_error(stage, stage_result, "create_instance");
        return cleanup(1);
    }

    result = ovrtx_attach_ovstage(renderer, stage);
    if (check_and_print_error(result, "attach_ovstage")) {
        return cleanup(1);
    }
    stage_attached = true;

    std::cerr << "Adding " << usd_url << " at root..." << std::endl;
    // [snippet:doc-minimal-dlss-c-populate]
    // The USD layer authors the Minimal DLSS controls on /Render/Camera.
    ovstage_population_enqueue_result_t populate_result =
        ovstage_population_open_usd_from_file(
            stage,
            {usd_url, strlen(usd_url)},
            stage_ordinal,
            OVSTAGE_POPULATION_DEFAULT_TIME,
            OVSTAGE_POPULATION_DOMAIN_RENDERING);
    if (wait_population_op(
            stage, populate_result, "population_open_usd_from_file") ||
        commit_ovstage_ordinal(stage, stage_ordinal)) {
        return cleanup(1);
    }
    // [/snippet:doc-minimal-dlss-c-populate]
    std::cerr << "USD loaded." << std::endl;

    constexpr int frame_count = 32;
    bool image_saved = false;
    for (int frame_index = 0; frame_index < frame_count; ++frame_index) {
        // [snippet:doc-minimal-dlss-c-step-renderer]
        // We render a frame by stepping the renderer.
        //
        // Any sensors whose exposures end during this step will generate a
        // frame that will be available in the step result. Since the camera in
        // the loaded USD layer is instantaneous (does not specify motion blur
        // or rolling shutter), it will generate a frame every time the render
        // is stepped.
        //
        // To step the renderer we need to tell ovrtx which RenderProducts we're
        // interested in, which in this case is the RenderProduct we defined in
        // the loading layer.
        ovrtx_render_product_set_t render_products = {};
        ovx_string_t render_product_str = {"/Render/Camera",
                                           strlen("/Render/Camera")};
        render_products.render_products = &render_product_str;
        render_products.num_render_products = 1;

        // Keep temporal history between steps; save the final frame after
        // warmup.
        ovrtx_step_result_handle_t step_result_handle = 0;
        ovrtx_enqueue_result_t enqueue_result =
            ovrtx_step_with_stage(renderer,
                                  render_products,
                                  1.0 / 60.0,
                                  stage_ordinal,
                                  &step_result_handle);
        if (check_and_print_error(enqueue_result, "step")) {
            return cleanup(1);
        }

        // Wait for the render to complete. Here we'll just block until it's
        // done.
        ovrtx_op_wait_result_t wait_result{};
        result = ovrtx_wait_op(renderer,
                               enqueue_result.op_index,
                               ovrtx_timeout_infinite,
                               &wait_result);
        if (check_and_print_error(result, "wait_op")) {
            ovrtx_destroy_results(renderer, step_result_handle);
            return cleanup(1);
        }
        if (wait_result.num_error_ops != 0) {
            std::cerr << "Rendering reported " << wait_result.num_error_ops
                      << " failed operations." << std::endl;
            ovrtx_destroy_results(renderer, step_result_handle);
            return cleanup(1);
        }
        // [/snippet:doc-minimal-dlss-c-step-renderer]

        ovrtx_render_product_set_outputs_t outputs = {};
        result = ovrtx_fetch_results(
            renderer, step_result_handle, ovrtx_timeout_infinite, &outputs);
        if (check_and_print_error(result, "fetch_results")) {
            ovrtx_destroy_results(renderer, step_result_handle);
            return cleanup(1);
        }

        // Find LdrColor by its authored RenderVar prim path.
        ovrtx_render_var_output_handle_t ldrcolor_output_handle =
            find_output(outputs, "/Render/Camera/LdrColor");
        if (ldrcolor_output_handle == OVRTX_INVALID_HANDLE) {
            std::cerr << "LdrColor output not found" << std::endl;
            ovrtx_destroy_results(renderer, step_result_handle);
            return cleanup(1);
        }

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
            std::cerr << "Unexpected LdrColor render variable: expected 1 "
                         "tensor, got "
                      << rendered_output.num_tensors << "." << std::endl;
            ovrtx_cuda_sync_t no_sync = {};
            ovrtx_unmap_render_var_output(
                renderer, rendered_output.map_handle, no_sync);
            ovrtx_destroy_results(renderer, step_result_handle);
            return cleanup(1);
        }
        DLTensor const& tensor = *rendered_output.tensors[0].dl;
        if (tensor.ndim != 3 || !tensor.shape || tensor.shape[2] != 4 ||
            tensor.dtype.lanes != 1 || tensor.dtype.code != kDLUInt ||
            tensor.dtype.bits != 8) {
            std::cerr << "Unexpected LdrColor tensor layout. Expected [H, W, "
                         "4] and dtype.lanes == 1."
                      << std::endl;
            ovrtx_cuda_sync_t no_sync = {};
            ovrtx_unmap_render_var_output(
                renderer, rendered_output.map_handle, no_sync);
            ovrtx_destroy_results(renderer, step_result_handle);
            return cleanup(1);
        }
        int width = static_cast<int>(tensor.shape[1]);
        int height = static_cast<int>(tensor.shape[0]);
        if (frame_index == frame_count - 1) {
            image_saved =
                stbi_write_png(output_path,
                               width,
                               height,
                               /* components = */ 4,
                               static_cast<const unsigned char*>(tensor.data) +
                                   tensor.byte_offset,
                               /* row stride in bytes = */ tensor.strides
                                   ? static_cast<int>(tensor.strides[0])
                                   : 4 * width) != 0;
        }

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
    }

    if (!image_saved) {
        std::cerr << "Failed to write " << output_path << std::endl;
        return cleanup(1);
    }
    return cleanup(0);
}

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
                if (var.render_var_path.ptr &&
                    std::string_view(var.render_var_path.ptr,
                                     var.render_var_path.length) ==
                        std::string_view(output_to_find)) {
                    return var.output_handle;
                }
            }
        }
    }
    return OVRTX_INVALID_HANDLE;
}
