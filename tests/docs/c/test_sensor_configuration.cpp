// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Tests for C code examples in sensor_configuration.rst. Uses the ovstage
// attach path (matches tests/docs/python/test_sensor_configuration.py).

#include <gtest/gtest.h>
#include "helpers.h"

#include <cmath>
#include <cstring>
#include <string>

class SensorConfigurationTest : public DocsOvstageTestBase {
protected:
    DOCS_OVSTAGE_TEST_SUITE(SensorConfigurationTest)
};

TEST_F(SensorConfigurationTest, StepMultipleRenderProducts) {
    std::string scene_path = get_test_data_dir() + "/simple_camera.usda";
    std::string usda = make_sublayer_usda(scene_path, R"usda(
def "Render" {
    def RenderProduct "FrontCamera" {
        int2 resolution = (640, 480)
        rel camera = </Camera0>
        rel orderedVars = [<../Vars/LdrColor>]
    }

    def RenderProduct "RearCamera" {
        int2 resolution = (640, 480)
        rel camera = </Camera1>
        rel orderedVars = [<../Vars/LdrColor>]
    }

    def "Vars" {
        def RenderVar "LdrColor" {
            string sourceName = "LdrColor"
        }
    }
}
)usda");

    docs_open_usd_string(usda.c_str(), usda.size());
    if (HasFatalFailure()) return;

    ovstage_ordinal_t ordinal = 1;

    // [snippet:doc-step-multiple-render-products-c]
    ovx_string_t rp_paths[] = {
        {"/Render/FrontCamera", strlen("/Render/FrontCamera")},
        {"/Render/RearCamera",  strlen("/Render/RearCamera")},
    };
    ovrtx_render_product_set_t render_products = {};
    render_products.render_products = rp_paths;
    render_products.num_render_products = 2;

    ovrtx_step_result_handle_t step_handle = 0;
    ovrtx_enqueue_result_t enqueue_result = ovrtx_step_with_stage(
        renderer_, render_products, 1.0 / 60.0, ordinal, &step_handle);
    // [/snippet:doc-step-multiple-render-products-c]
    ASSERT_API_SUCCESS(enqueue_result.status);
    docs_wait_no_errors(renderer_, enqueue_result.op_index);
    ovrtx_destroy_results(renderer_, step_handle);

    // Second step for pixel-stability sampling.
    enqueue_result = ovrtx_step_with_stage(
        renderer_, render_products, 1.0 / 60.0, ordinal, &step_handle);
    ASSERT_API_SUCCESS(enqueue_result.status);
    docs_wait_no_errors(renderer_, enqueue_result.op_index);

    ovrtx_render_product_set_outputs_t outputs{};
    ovrtx_result_t result =
        ovrtx_fetch_results(renderer_, step_handle, ovrtx_timeout_infinite, &outputs);
    ASSERT_API_SUCCESS(result.status);
    EXPECT_EQ(outputs.output_count, 2u);

    char const* product_names[] = {"FrontCamera", "RearCamera"};
    ovrtx_map_output_description_t map_desc = {};
    map_desc.device_type = OVRTX_MAP_DEVICE_TYPE_CPU;
    ovrtx_cuda_sync_t no_sync = {};
    for (size_t i = 0; i < outputs.output_count; ++i) {
        ovrtx_render_var_output_handle_t ldr_handle =
            find_product_output(outputs.outputs[i], "LdrColor");
        if (ldr_handle != OVRTX_INVALID_HANDLE) {
            ovrtx_render_var_output_t ldr_output = {};
            ovrtx_result_t map_result = ovrtx_map_render_var_output(
                renderer_, ldr_handle, &map_desc, ovrtx_timeout_infinite, &ldr_output);
            if (map_result.status == OVRTX_API_SUCCESS) {
                DLTensor const& t = *ldr_output.tensors[0].dl;
                std::string name = std::string("SensorConfig.") + product_names[i];
                save_ldr_png(name.c_str(), t.data,
                             static_cast<int>(t.shape[1]),
                             static_cast<int>(t.shape[0]));
                ovrtx_unmap_render_var_output(renderer_, ldr_output.map_handle, no_sync);
            }
        }
    }

    ovrtx_destroy_results(renderer_, step_handle);
}

TEST_F(SensorConfigurationTest, AddRenderConfigLayer) {
    // [snippet:doc-add-render-config-layer-c]
    // Compose a docs-owned render-config layer on top of a scene layer via
    // USD sublayers. The composed root gets populated into the attached
    // ovstage in one call.
    std::string scene_path = get_test_data_dir() + "/simple_camera.usda";
    std::string usda = make_sublayer_usda(scene_path, R"usda(
def "Render" {
    def RenderProduct "Camera" {
        int2 resolution = (640, 480)
        rel camera = </Camera0>
        rel orderedVars = [<LdrColor>, <HdrColor>]

        def RenderVar "LdrColor" {
            string sourceName = "LdrColor"
        }

        def RenderVar "HdrColor" {
            string sourceName = "HdrColor"
        }
    }
}
)usda");
    ovstage_population_enqueue_result_t pr = ovstage_population_open_usd_from_string(
        stage_,
        {usda.c_str(), usda.size()},
        /*ordinal=*/1,
        /*time=*/NAN,
        OVSTAGE_POPULATION_DOMAIN_RENDERING);
    ASSERT_EQ(pr.status, OVSTAGE_OK) << format_ovstage_population_last_error();
    docs_wait_ovstage_population_no_errors(stage_, pr.op_index);
    docs_ovstage_advance_write_floor(stage_, 1);
    // [/snippet:doc-add-render-config-layer-c]

    // Verify the composed layer renders.
    ovx_string_t rp_path = ovx_str("/Render/Camera");
    ovrtx_render_product_set_t render_products{};
    render_products.render_products = &rp_path;
    render_products.num_render_products = 1;

    ovrtx_step_result_handle_t step_handle = 0;
    ovrtx_enqueue_result_t enqueue_result = ovrtx_step_with_stage(
        renderer_, render_products, 1.0 / 60.0, /*ordinal=*/1, &step_handle);
    ASSERT_API_SUCCESS(enqueue_result.status);
    docs_wait_no_errors(renderer_, enqueue_result.op_index);

    ovrtx_render_product_set_outputs_t outputs{};
    ovrtx_result_t result =
        ovrtx_fetch_results(renderer_, step_handle, ovrtx_timeout_infinite, &outputs);
    ASSERT_API_SUCCESS(result.status);
    EXPECT_GE(outputs.output_count, 1u);

    ovrtx_render_var_output_handle_t ldr_handle = find_output(outputs, "LdrColor");
    if (ldr_handle != OVRTX_INVALID_HANDLE) {
        ovrtx_map_output_description_t md = {};
        md.device_type = OVRTX_MAP_DEVICE_TYPE_CPU;
        ovrtx_render_var_output_t ldr_output = {};
        ovrtx_result_t mr = ovrtx_map_render_var_output(
            renderer_, ldr_handle, &md, ovrtx_timeout_infinite, &ldr_output);
        if (mr.status == OVRTX_API_SUCCESS) {
            DLTensor const& t = *ldr_output.tensors[0].dl;
            save_ldr_png("SensorConfig.AddRenderConfigLayer",
                         t.data,
                         static_cast<int>(t.shape[1]),
                         static_cast<int>(t.shape[0]));
            ovrtx_cuda_sync_t no_sync = {};
            ovrtx_unmap_render_var_output(renderer_, ldr_output.map_handle, no_sync);
        }
    }

    ovrtx_destroy_results(renderer_, step_handle);
}
