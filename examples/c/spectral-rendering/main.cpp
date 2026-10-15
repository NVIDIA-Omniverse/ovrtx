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
#include <ovstage/ovstage.h>

#include <cstring>
#include <filesystem>
#include <cmath>
#include <stdexcept>
#include <iostream>
#include <string>
#include <string_view>

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "../minimal/stb_image_write.h"

// Report API errors before dependent operations use invalid results.
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

// Population must finish before sealing the ordinal.
static bool wait_population(ovstage_instance_t* stage,
                            ovstage_population_enqueue_result_t enqueue) {
    if (enqueue.status != OVSTAGE_OK) {
        return true;
    }
    ovstage_population_op_wait_result_t wait_result{};
    return ovstage_population_wait_op(stage,
                                      enqueue.op_index,
                                      OVSTAGE_TIMEOUT_INFINITE,
                                      &wait_result) != OVSTAGE_OK ||
           wait_result.error_op_id_count != 0;
}

// Seal scene writes before the renderer reads this ordinal.
static bool wait_stage(ovstage_instance_t* stage,
                       ovstage_enqueue_result_t enqueue) {
    if (enqueue.status != OVSTAGE_OK) {
        return true;
    }
    ovstage_op_wait_result_t wait_result{};
    ovstage_api_status_t status = ovstage_wait_op(
        stage, enqueue.op_index, OVSTAGE_TIMEOUT_INFINITE, &wait_result);
    ovstage_release_op(stage, enqueue.op_index);
    return status != OVSTAGE_OK || wait_result.error_op_id_count != 0;
}

// A completed wait can still contain failed asynchronous operations.
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

// RenderVars are identified by full prim path in the returned frames.
static ovrtx_render_var_output_handle_t
find_ldr_color(ovrtx_render_product_set_outputs_t const& outputs) {
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

// Select the same USD variants as Python and save a converged PathTracing image.
int main(int argc, char** argv) {
    if (argc < 5 || argc > 7) {
        std::cerr << "Usage: spectral-rendering ILLUMINANT rgb|spectral SPP "
                     "OUTPUT.png [cie1931|canon5d|sony_a7iv [WHITE_POINT_K]]\n";
        return 1;
    }
    std::string illuminant = argv[1];
    std::string transport = argv[2];
    std::string camera = argc >= 6 ? argv[5] : "cie1931";
    if ((illuminant != "white" && illuminant != "blackbody3200" && illuminant != "daylight" && illuminant != "sodium" &&
         illuminant != "mercury") ||
        (transport != "rgb" && transport != "spectral")) {
        std::cerr << "Invalid illuminant or transport.\n";
        return 1;
    }
    if ((camera != "cie1931" && camera != "canon5d" && camera != "sony_a7iv") ||
        (camera != "cie1931" && transport != "spectral")) {
        std::cerr << "Choose cie1931, canon5d, or sony_a7iv; custom responses require spectral transport.\n";
        return 1;
    }
    float white_point = 0.0f;
    if (argc == 7) {
        try {
            size_t consumed = 0;
            white_point = std::stof(argv[6], &consumed);
            if (!std::isfinite(white_point) || white_point <= 0 || consumed != std::strlen(argv[6]) || transport != "spectral")
                throw std::invalid_argument("white point");
        } catch (...) {
            std::cerr << "WHITE_POINT_K must be finite and positive and requires spectral transport.\n";
            return 1;
        }
    }
    int spp = 0;
    try {
        size_t consumed = 0;
        spp = std::stoi(argv[3], &consumed);
        if (spp < 1 || consumed != std::strlen(argv[3])) {
            return 1;
        }
    } catch (...) {
        std::cerr << "SPP must be a positive integer.\n";
        return 1;
    }

    ovrtx_renderer_t* renderer = nullptr;
    ovstage_instance_t* stage = nullptr;
    bool attached = false;

    // [snippet:doc-spectral-config-c]
    // Select the process-wide material backend before creating any renderer.
    ovrtx_config_entry_t entries[] = {
        ovrtx_config_entry_enable_spectral_rendering(transport == "spectral"),
    };
    ovrtx_config_t renderer_config{entries, 1};

    ovrtx_result_t result = ovrtx_register_schema_paths(&renderer_config);
    if (failed(result, "register_schema_paths") ||
        failed(ovrtx_create_renderer(&renderer_config, &renderer),
               "create_renderer")) {
        return 1;
    }
    // [/snippet:doc-spectral-config-c]

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

    ovstage_config_t stage_config{};

    if (ovstage_initialize(&stage_config) != OVSTAGE_OK) {
        return cleanup(1);
    }
    ovstage_instance_desc_t stage_desc{};
    stage_desc.name = "spectral-rendering";
    if (ovstage_create_instance(&stage_desc, &stage) != OVSTAGE_OK ||
        failed(ovrtx_attach_ovstage(renderer, stage), "attach_ovstage")) {
        return cleanup(1);
    }
    attached = true;

    // [snippet:doc-spectral-select-c]
    // Camera prims share geometry/exposure; only their spectral response differs.
    const char* camera_path = camera == "canon5d" ? "/World/Canon5D" :
                              camera == "sony_a7iv" ? "/World/SonyA7IV" : "/World/Camera";
    // Apply the API only when requested; default curves supply CIE 1931 responsivity.
    std::string white_point_layer;
    if (argc == 7) {
        const std::string camera_name = std::string(camera_path).substr(7);
        white_point_layer = "over \"" + camera_name +
            "\" (prepend apiSchemas = [\"PhysicalCameraResponsivityAPI\"]) {\n"
            "float physical:responsivity:colorTemperature = " + std::to_string(white_point) + "\n}\n";
    }
    constexpr ovstage_ordinal_t ordinal = 1;
    std::filesystem::path executable_dir =
        std::filesystem::absolute(argv[0]).parent_path();
    std::string scene_path =
        (executable_dir / "spectral.usda").generic_string();
    std::string layer =
        "#usda 1.0\n(subLayers = [@" + scene_path +
        "@])\n"
        "over \"World\" {\n" + white_point_layer + " over \"RectLight\" (variants = { string illuminant = "
        "\"" +
        illuminant +
        "\" }) {}\n }\n"
        "over \"Render\" {\n over \"Camera\" (variants = { string transport = "
        "\"" +
        transport +
        "\" }) {\n rel camera = <" + camera_path +
        ">\n uint omni:rtx:pt:samplesPerPixel = " + std::to_string(spp) +
        "\n }\n }\n";
    auto populate = ovstage_population_open_usd_from_string(
        stage,
        {layer.c_str(), layer.size()},
        ordinal,
        0.0,
        OVSTAGE_POPULATION_DOMAIN_RENDERING);
    ovstage_write_floor_desc_t floor{ordinal, OVSTAGE_SCOPE_ALL};
    if (wait_population(stage, populate) ||
        wait_stage(stage, ovstage_advance_write_floor(stage, &floor))) {
        std::cerr << "Could not populate the spectral scene." << std::endl;
        return cleanup(1);
    }

    ovx_string_t product_path = {"/Render/Camera", strlen("/Render/Camera")};
    ovrtx_render_product_set_t render_products{&product_path, 1};
    // PathTracing completes its samples within a single step.
    ovrtx_step_result_handle_t final_handle = OVRTX_INVALID_HANDLE;
    auto enqueue = ovrtx_step_with_stage(
        renderer, render_products, 1.0 / 60.0, ordinal, &final_handle);
    ovrtx_op_wait_result_t wait_result{};
    if (failed(enqueue, "step") ||
        failed(ovrtx_wait_op(renderer,
                             enqueue.op_index,
                             ovrtx_timeout_infinite,
                             &wait_result),
               "wait_op") ||
        report_wait_errors(wait_result)) {
        return cleanup(1);
    }
    // [/snippet:doc-spectral-select-c]

    // [snippet:doc-spectral-save-c]
    ovrtx_render_product_set_outputs_t outputs{};
    if (failed(ovrtx_fetch_results(
                   renderer, final_handle, ovrtx_timeout_infinite, &outputs),
               "fetch_results")) {
        return cleanup(1);
    }
    auto output_handle = find_ldr_color(outputs);
    ovrtx_map_output_description_t map_desc{};
    map_desc.device_type = OVRTX_MAP_DEVICE_TYPE_CPU;
    ovrtx_render_var_output_t output{};
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
    std::filesystem::path output_path = std::filesystem::absolute(argv[4]);
    std::filesystem::create_directories(output_path.parent_path());
    bool wrote_output = stbi_write_png(output_path.string().c_str(),
                                       width,
                                       height,
                                       4,
                                       pixels.data,
                                       4 * width) != 0;
    ovrtx_cuda_sync_t no_sync{};
    ovrtx_unmap_render_var_output(renderer, output.map_handle, no_sync);
    ovrtx_destroy_results(renderer, final_handle);
    if (!wrote_output) {
        std::cerr << "Could not write " << output_path << std::endl;
        return cleanup(1);
    }
    std::cout << "Saved " << output_path << std::endl;
    // [/snippet:doc-spectral-save-c]

    return cleanup(0);
}
