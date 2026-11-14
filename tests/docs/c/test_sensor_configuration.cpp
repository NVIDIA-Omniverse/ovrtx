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
#include <map>
#include <memory>
#include <string>
#include <vector>

class SensorConfigurationTest : public DocsOvstageTestBase {
protected:
    DOCS_OVSTAGE_TEST_SUITE(SensorConfigurationTest)
};

class MultiRateSensorConfigurationTest : public DocsOvstageTestBase {
protected:
    inline static ovrtx_renderer_t* suite_renderer_ = nullptr;
    static void SetUpTestSuite() {
        TestConfig test_config("MultiRateSensorConfigurationTest");
        ovrtx_config_entry_t entries[] = {
            test_config.entries[0], ovrtx_config_entry_motion_bvh(OVRTX_MOTION_BVH_ENABLE),
        };
        ovrtx_config_t config{entries, 2};
        ASSERT_API_SUCCESS(ovrtx_create_renderer(&config, &suite_renderer_).status);
    }
    static void TearDownTestSuite() { docs_destroy_suite_renderer(&suite_renderer_); }
    void SetUp() override { docs_attach_stage(suite_renderer_); }
    void TearDown() override { docs_detach_stage(); }
};

TEST_F(MultiRateSensorConfigurationTest, MultiRateSensorsKeepEveryProductActive) {
    const std::string scene_path = get_docs_test_data_dir() +
        "/../../../examples/python/multi-rate-sensors/multi_rate.usda";
    docs_open_usd_file(scene_path.c_str());
    if (HasFatalFailure()) return;

    ovstage_ordinal_t ordinal = 1;
    // No Camera schema declares this attribute. Set it through ovstage before
    // the first step, then publish the write ordinal.
    // [snippet:doc-multi-rate-partial-outputs-c]
    ++ordinal;
    auto* dictionary = ovstage_get_path_dictionary(stage_);
    const ovx_string_t sensor_paths[] = {
        ovx_str("/World/Lidar40"), ovx_str("/World/Lidar20"),
        ovx_str("/World/Camera10"), ovx_str("/World/Camera20"),
    };
    ovx_primpath_list_t path_list = OVX_INVALID_PRIMPATH_LIST;
    const auto path_result = path_dictionary_create_path_list_from_strings(
        dictionary, sensor_paths, 4, &path_list);
    ASSERT_EQ(path_result.status, OVX_API_SUCCESS);
    ovstage_query_handle_t query = OVSTAGE_INVALID_QUERY_HANDLE;
    ASSERT_EQ(ovstage_query_from_path_list(stage_, path_list, &query), OVSTAGE_OK);

    // Deliver only completed captures here. Use true to also deliver partial outputs.
    bool partial_outputs[] = {false, false, false, false};
    int64_t shape[] = {4};
    DLTensor tensor{};
    tensor.data = partial_outputs;
    tensor.device = {kDLCPU, 0};
    tensor.ndim = 1;
    tensor.dtype = {kDLBool, 8, 1};
    tensor.shape = shape;
    ovstage_write_data_t data{};
    data.tensors = &tensor;
    data.tensor_count = 1;
    data.is_array = false;
    const ovx_token_or_string_t attribute{
        0, ovx_str("omni:sensor:Core:partialOutputs")
    };
    const auto write = ovstage_write_attribute(
        stage_, query, attribute, ordinal, data, OVSTAGE_PRIM_MODE_UPSERT);
    ASSERT_EQ(write.status, OVSTAGE_OK);
    docs_wait_ovstage_no_errors(stage_, write.op_index);
    const auto release = ovstage_release_query(stage_, query);
    ASSERT_EQ(release.status, OVSTAGE_OK);
    docs_wait_ovstage_no_errors(stage_, release.op_index);
    path_dictionary_release_path_list_reference(dictionary, path_list);
    docs_ovstage_advance_write_floor(stage_, ordinal);
    // [/snippet:doc-multi-rate-partial-outputs-c]

    std::map<std::string, std::vector<double>> camera_capture_times;
    std::map<std::string, size_t> lidar_scan_counts;
    constexpr int step_count = 8;
    for (int step_index = 0; step_index < step_count; ++step_index) {
        // [snippet:doc-multi-rate-step-c]
        // Publish animated scene state before advancing the sensor clock.
        ++ordinal;
        const double simulation_time = (step_index + 1) / 40.0;
        const auto population = ovstage_population_apply_usd_time(stage_, ordinal, simulation_time);
        ASSERT_EQ(population.status, OVSTAGE_OK);
        docs_wait_ovstage_population_no_errors(stage_, population.op_index);
        docs_ovstage_advance_write_floor(stage_, ordinal);

        // Keep slow sensors selected even on steps with no completed output.
        ovx_string_t paths[] = {
            ovx_str("/Render/Lidar40"), ovx_str("/Render/Lidar20"),
            ovx_str("/Render/Camera10"), ovx_str("/Render/Camera20"),
        };
        ovrtx_render_product_set_t products{};
        products.render_products = paths;
        products.num_render_products = 4;
        ovrtx_step_result_handle_t step_handle{};
        const auto operation = ovrtx_step_with_stage(
            renderer_, products, 1.0 / 40.0, ordinal, &step_handle);
        ASSERT_API_SUCCESS(operation.status);
        // [/snippet:doc-multi-rate-step-c]

        // Release the result even if a later assertion returns from the test.
        const auto release_result = [this](ovrtx_step_result_handle_t* handle) {
            ovrtx_destroy_results(renderer_, *handle);
        };
        const std::unique_ptr<ovrtx_step_result_handle_t, decltype(release_result)> result_guard(
            &step_handle, release_result);
        docs_wait_no_errors(renderer_, operation.op_index);
        if (HasFatalFailure()) return;
        ovrtx_render_product_set_outputs_t outputs{};
        ASSERT_API_SUCCESS(ovrtx_fetch_results(renderer_, step_handle, ovrtx_timeout_infinite, &outputs).status);
        EXPECT_NEAR(outputs.simulation_end_time, simulation_time, 1e-9);

        // Iterate every available frame; do not assume every product has one.
        for (size_t product_index = 0; product_index < outputs.output_count; ++product_index) {
            const auto& product = outputs.outputs[product_index];
            const std::string path(product.render_product_path.ptr, product.render_product_path.length);
            for (size_t frame_index = 0; frame_index < product.output_frame_count; ++frame_index) {
                const auto& frame = product.output_frames[frame_index];
                if (path == "/Render/Camera10" || path == "/Render/Camera20") {
                    camera_capture_times[path].push_back(frame.frame_start_time);
                    continue;
                }
                ASSERT_EQ(frame.render_var_count, 1u);
                ovrtx_map_output_description_t description{};
                description.device_type = OVRTX_MAP_DEVICE_TYPE_CPU;
                ovrtx_render_var_output_t cloud{};
                ASSERT_API_SUCCESS(ovrtx_map_render_var_output(renderer_, frame.output_render_vars[0].output_handle,
                                                              &description, ovrtx_timeout_infinite, &cloud).status);
                for (size_t tensor_index = 0; tensor_index < cloud.num_tensors; ++tensor_index) {
                    const auto& tensor = cloud.tensors[tensor_index];
                    if (tensor.name && tensor.name->length == 6 &&
                        std::strncmp(tensor.name->ptr, "Counts", 6) == 0) {
                        const auto* bytes = static_cast<const uint8_t*>(tensor.dl->data) + tensor.dl->byte_offset;
                        if (*reinterpret_cast<const int32_t*>(bytes) > 0) ++lidar_scan_counts[path];
                    }
                }
                ASSERT_API_SUCCESS(ovrtx_unmap_render_var_output(renderer_, cloud.map_handle, {}).status);
            }
        }
    }

    for (const auto& entry : std::map<std::string, int>{{"/Render/Camera10", 10}, {"/Render/Camera20", 20}}) {
        const auto& times = camera_capture_times[entry.first];
        ASSERT_EQ(times.size(), static_cast<size_t>(step_count * entry.second / 40));
        EXPECT_NEAR(times.front(), entry.first == "/Render/Camera10" ? 0.1 : 0.0, 1e-6);
        for (size_t index = 1; index < times.size(); ++index) {
            EXPECT_NEAR(times[index] - times[index - 1], 1.0 / entry.second, 1e-6);
        }
    }
    EXPECT_EQ(lidar_scan_counts["/Render/Lidar40"], 8u);
    EXPECT_EQ(lidar_scan_counts["/Render/Lidar20"], 4u);
}

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

    ovrtx_step_result_handle_t step_handle{};
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
            find_product_output(outputs.outputs[i], "/Render/Vars/LdrColor");
        if (ldr_handle != OVRTX_INVALID_RENDER_VAR_OUTPUT_HANDLE) {
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

    ovrtx_step_result_handle_t step_handle{};
    ovrtx_enqueue_result_t enqueue_result = ovrtx_step_with_stage(
        renderer_, render_products, 1.0 / 60.0, /*ordinal=*/1, &step_handle);
    ASSERT_API_SUCCESS(enqueue_result.status);
    docs_wait_no_errors(renderer_, enqueue_result.op_index);

    ovrtx_render_product_set_outputs_t outputs{};
    ovrtx_result_t result =
        ovrtx_fetch_results(renderer_, step_handle, ovrtx_timeout_infinite, &outputs);
    ASSERT_API_SUCCESS(result.status);
    EXPECT_GE(outputs.output_count, 1u);

    ovrtx_render_var_output_handle_t ldr_handle = find_output(outputs, "/Render/Camera/LdrColor");
    if (ldr_handle != OVRTX_INVALID_RENDER_VAR_OUTPUT_HANDLE) {
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
