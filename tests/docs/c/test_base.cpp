// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Tests using ovrtx-test-base.usda, exercised through the ovstage attached
// path. Mirrors tests/docs/python/test_base.py.

#include <gtest/gtest.h>
#include "helpers.h"

#include <cmath>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

namespace {

// Configure /Render/Camera.omni:rtx:rtpt:<setting> = value at `ordinal`.
// Used by the render-setting tests below; kept out of the [snippet:] block
// so the doc quote focuses on the write itself. The rtpt::max* schema
// columns are all uint32.
void write_render_setting_uint32(ovstage_instance_t* stage,
                                  char const* setting_name,
                                  uint32_t value,
                                  ovstage_ordinal_t ordinal) {
    path_dictionary_instance_t* pd = ovstage_get_path_dictionary(stage);
    ovx_string_t prim_path = ovx_str("/Render/Camera");
    ovx_primpath_list_t path_list{};
    ASSERT_EQ(path_dictionary_create_path_list_from_strings(pd, &prim_path, 1, &path_list).status,
              OVX_API_SUCCESS);
    ovstage_query_handle_t query_handle = OVSTAGE_INVALID_QUERY_HANDLE;
    ASSERT_EQ(ovstage_query_from_path_list(stage, path_list, &query_handle), OVSTAGE_OK)
        << format_ovstage_last_error();

    ovx_string_t attr_str = ovx_str(setting_name);
    ovx_token_t attr_token{};
    ASSERT_EQ(path_dictionary_create_tokens_from_strings(pd, &attr_str, 1, &attr_token).status,
              OVX_API_SUCCESS);

    int64_t write_shape[1] = {1};
    DLTensor write_tensor{};
    write_tensor.data = &value;
    write_tensor.device = {kDLCPU, 0};
    write_tensor.ndim = 1;
    write_tensor.dtype = {kDLUInt, 32, 1};
    write_tensor.shape = write_shape;

    ovstage_write_data_t write_data{};
    write_data.tensors = &write_tensor;
    write_data.tensor_count = 1;
    write_data.is_array = false;

    ovx_string_or_token_t attr_ref{};
    attr_ref.token = attr_token;

    ovstage_enqueue_result_t wq = ovstage_write_attribute(
        stage, query_handle, attr_ref, ordinal, write_data, OVSTAGE_PRIM_MODE_UPSERT);
    ASSERT_EQ(wq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage, wq.op_index);

    ovstage_release_query(stage, query_handle);
    path_dictionary_release_path_list_reference(pd, path_list);
}

// Warm up + step once at `ordinal`, then save LdrColor to <name>.
void render_and_save(ovrtx_renderer_t* renderer,
                     ovstage_ordinal_t ordinal,
                     char const* name) {
    ovx_string_t rp_path = ovx_str("/Render/Camera");
    ovrtx_render_product_set_t render_products{};
    render_products.render_products = &rp_path;
    render_products.num_render_products = 1;

    for (int i = 0; i < 40; ++i) {
        ovrtx_step_result_handle_t warmup_handle = 0;
        ovrtx_enqueue_result_t eq = ovrtx_step_with_stage(
            renderer, render_products, 1.0 / 60.0, ordinal, &warmup_handle);
        ASSERT_API_SUCCESS(eq.status);
        docs_wait_no_errors(renderer, eq.op_index);
        ovrtx_destroy_results(renderer, warmup_handle);
    }

    ovrtx_step_result_handle_t step_handle = 0;
    ovrtx_enqueue_result_t eq = ovrtx_step_with_stage(
        renderer, render_products, 1.0 / 60.0, ordinal, &step_handle);
    ASSERT_API_SUCCESS(eq.status);
    docs_wait_no_errors(renderer, eq.op_index);

    ovrtx_render_product_set_outputs_t outputs{};
    ovrtx_result_t result =
        ovrtx_fetch_results(renderer, step_handle, ovrtx_timeout_infinite, &outputs);
    ASSERT_API_SUCCESS(result.status);

    ovrtx_render_var_output_handle_t ldr_handle = find_output(outputs, "LdrColor");
    ASSERT_NE(ldr_handle, OVRTX_INVALID_HANDLE);
    ovrtx_map_output_description_t map_desc = {};
    map_desc.device_type = OVRTX_MAP_DEVICE_TYPE_CPU;
    ovrtx_render_var_output_t ldr_output = {};
    result = ovrtx_map_render_var_output(
        renderer, ldr_handle, &map_desc, ovrtx_timeout_infinite, &ldr_output);
    ASSERT_API_SUCCESS(result.status);

    DLTensor const& tensor = *ldr_output.tensors[0].dl;
    EXPECT_GT(tensor.shape[0], 0);
    EXPECT_GT(tensor.shape[1], 0);
    save_ldr_png(name,
                 tensor.data,
                 static_cast<int>(tensor.shape[1]),
                 static_cast<int>(tensor.shape[0]));

    ovrtx_cuda_sync_t no_sync = {};
    ovrtx_unmap_render_var_output(renderer, ldr_output.map_handle, no_sync);
    ovrtx_destroy_results(renderer, step_handle);
}

} // namespace

class BaseTest : public DocsOvstageTestBase {
protected:
    DOCS_OVSTAGE_TEST_SUITE(BaseTest)
};

TEST_F(BaseTest, RenderLdrColor) {
    docs_load_base();
    if (HasFatalFailure()) return;

    render_and_save(renderer_, /*ordinal=*/1, "base.Camera.LdrColor.0001");
}

TEST_F(BaseTest, BindMaterial) {
    docs_load_base();
    if (HasFatalFailure()) return;

    // [snippet:doc-bind-material-c]
    // Bind /World/Looks/srf_glass as the material for /World/logo/logo/logo.
    // Material bindings are relationships from a geometry prim to a material
    // prim, expressed in ovstage as an array attribute (`material:binding`)
    // whose entries are RELATIONSHIP_PATH_ID rows — one uint64 path handle
    // (ovx_primpath_t) per target material.
    path_dictionary_instance_t* pd = ovstage_get_path_dictionary(stage_);
    ovx_string_t prim_path = ovx_str("/World/logo/logo/logo");
    ovx_primpath_list_t path_list{};
    ASSERT_EQ(path_dictionary_create_path_list_from_strings(pd, &prim_path, 1, &path_list).status,
              OVX_API_SUCCESS);
    ovstage_query_handle_t query_handle = OVSTAGE_INVALID_QUERY_HANDLE;
    ASSERT_EQ(ovstage_query_from_path_list(stage_, path_list, &query_handle), OVSTAGE_OK)
        << format_ovstage_last_error();

    ovx_string_t binding_str = ovx_str("material:binding");
    ovx_token_t binding_token{};
    ASSERT_EQ(path_dictionary_create_tokens_from_strings(pd, &binding_str, 1, &binding_token).status,
              OVX_API_SUCCESS);

    // Intern the target material path so we can write its uint64 handle.
    ovx_string_t material_str = ovx_str("/World/Looks/srf_glass");
    ovx_primpath_t material_path[1] = {};
    ASSERT_EQ(path_dictionary_create_paths_from_strings(pd, &material_str, 1, material_path).status,
              OVX_API_SUCCESS);

    int64_t write_shape[1] = {1};
    DLTensor write_tensor{};
    write_tensor.data = material_path;
    write_tensor.device = {kDLCPU, 0};
    write_tensor.ndim = 1;
    write_tensor.dtype = {kDLUInt, 64, 1};
    write_tensor.shape = write_shape;

    ovstage_write_data_t write_data{};
    write_data.tensors = &write_tensor;
    write_data.tensor_count = 1;
    write_data.is_array = true;
    write_data.semantic = OVSTAGE_SEMANTIC_RELATIONSHIP_PATH_ID;

    ovx_string_or_token_t attr_ref{};
    attr_ref.token = binding_token;

    ovstage_enqueue_result_t wq = ovstage_write_attribute(
        stage_, query_handle, attr_ref, /*ordinal=*/2, write_data, OVSTAGE_PRIM_MODE_UPSERT);
    ASSERT_EQ(wq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, wq.op_index);
    docs_ovstage_advance_write_floor(stage_, 2);

    ovstage_release_query(stage_, query_handle);
    path_dictionary_release_path_list_reference(pd, path_list);
    // [/snippet:doc-bind-material-c]

    // [snippet:doc-warmup-c]
    // Warm up — step enough frames for texture streaming to finish loading
    // high-res mips and for path tracing to converge to a good quality image.
    ovx_string_t rp_path = ovx_str("/Render/Camera");
    ovrtx_render_product_set_t render_products{};
    render_products.render_products = &rp_path;
    render_products.num_render_products = 1;

    ovrtx_step_result_handle_t step_handle = 0;
    int const WARMUP_FRAMES = 40;
    for (int i = 0; i < WARMUP_FRAMES; ++i) {
        ovrtx_enqueue_result_t eq = ovrtx_step_with_stage(
            renderer_, render_products, 1.0 / 60.0, /*ordinal=*/2, &step_handle);
        ASSERT_API_SUCCESS(eq.status);
        docs_wait_no_errors(renderer_, eq.op_index);
        ovrtx_destroy_results(renderer_, step_handle);
    }
    // [/snippet:doc-warmup-c]

    // Render one frame + save.
    ovrtx_enqueue_result_t eq = ovrtx_step_with_stage(
        renderer_, render_products, 1.0 / 60.0, /*ordinal=*/2, &step_handle);
    ASSERT_API_SUCCESS(eq.status);
    docs_wait_no_errors(renderer_, eq.op_index);

    ovrtx_render_product_set_outputs_t outputs{};
    ovrtx_result_t result =
        ovrtx_fetch_results(renderer_, step_handle, ovrtx_timeout_infinite, &outputs);
    ASSERT_API_SUCCESS(result.status);

    ovrtx_render_var_output_handle_t ldr_handle = find_output(outputs, "LdrColor");
    ASSERT_NE(ldr_handle, OVRTX_INVALID_HANDLE);
    ovrtx_map_output_description_t map_desc = {};
    map_desc.device_type = OVRTX_MAP_DEVICE_TYPE_CPU;
    ovrtx_render_var_output_t ldr_output = {};
    result = ovrtx_map_render_var_output(
        renderer_, ldr_handle, &map_desc, ovrtx_timeout_infinite, &ldr_output);
    ASSERT_API_SUCCESS(result.status);

    DLTensor const& tensor = *ldr_output.tensors[0].dl;
    save_ldr_png("bind_material.Camera.LdrColor.0001",
                 tensor.data,
                 static_cast<int>(tensor.shape[1]),
                 static_cast<int>(tensor.shape[0]));

    ovrtx_cuda_sync_t no_sync = {};
    ovrtx_unmap_render_var_output(renderer_, ldr_output.map_handle, no_sync);
    ovrtx_destroy_results(renderer_, step_handle);
}

TEST_F(BaseTest, SettingsRtptMaxBounces) {
    docs_load_base();
    if (HasFatalFailure()) return;

    ovstage_ordinal_t ordinal = 2;
    int bounce_values[] = {2, 3, 23};
    for (int max_bounces : bounce_values) {
        // [snippet:doc-set-render-setting-c]
        // Author a render setting on the RenderProduct prim by writing the
        // attribute through ovstage. omni:rtx:rtpt:maxBounces is a uint32
        // scalar.
        path_dictionary_instance_t* pd = ovstage_get_path_dictionary(stage_);
        ovx_string_t prim_path = ovx_str("/Render/Camera");
        ovx_primpath_list_t path_list{};
        ASSERT_EQ(
            path_dictionary_create_path_list_from_strings(pd, &prim_path, 1, &path_list).status,
            OVX_API_SUCCESS);
        ovstage_query_handle_t query_handle = OVSTAGE_INVALID_QUERY_HANDLE;
        ASSERT_EQ(ovstage_query_from_path_list(stage_, path_list, &query_handle), OVSTAGE_OK);

        ovx_string_t attr_str = ovx_str("omni:rtx:rtpt:maxBounces");
        ovx_token_t attr_token{};
        ASSERT_EQ(path_dictionary_create_tokens_from_strings(pd, &attr_str, 1, &attr_token).status,
                  OVX_API_SUCCESS);

        uint32_t value = static_cast<uint32_t>(max_bounces);
        int64_t write_shape[1] = {1};
        DLTensor write_tensor{};
        write_tensor.data = &value;
        write_tensor.device = {kDLCPU, 0};
        write_tensor.ndim = 1;
        write_tensor.dtype = {kDLUInt, 32, 1};
        write_tensor.shape = write_shape;

        ovstage_write_data_t write_data{};
        write_data.tensors = &write_tensor;
        write_data.tensor_count = 1;
        write_data.is_array = false;

        ovx_string_or_token_t attr_ref{};
        attr_ref.token = attr_token;

        ovstage_enqueue_result_t wq = ovstage_write_attribute(
            stage_, query_handle, attr_ref, ordinal, write_data, OVSTAGE_PRIM_MODE_UPSERT);
        ASSERT_EQ(wq.status, OVSTAGE_OK) << format_ovstage_last_error();
        docs_wait_ovstage_no_errors(stage_, wq.op_index);
        docs_ovstage_advance_write_floor(stage_, ordinal);

        ovstage_release_query(stage_, query_handle);
        path_dictionary_release_path_list_reference(pd, path_list);
        // [/snippet:doc-set-render-setting-c]

        std::string name = "settings_rtpt_maxBounces.Camera.LdrColor.maxBounces-"
                           + std::to_string(max_bounces) + ".0001";
        render_and_save(renderer_, ordinal, name.c_str());
        ordinal++;
    }
}

TEST_F(BaseTest, SettingsRtptMaxSpecularAndTransmissionBounces) {
    docs_load_base();
    if (HasFatalFailure()) return;

    // Bind glass to the logo so specular/transmission bounces are visible.
    // Reuses the same relationship-path-id write as BindMaterial.
    {
        path_dictionary_instance_t* pd = ovstage_get_path_dictionary(stage_);
        ovx_string_t prim_path = ovx_str("/World/logo/logo/logo");
        ovx_primpath_list_t path_list{};
        ASSERT_EQ(
            path_dictionary_create_path_list_from_strings(pd, &prim_path, 1, &path_list).status,
            OVX_API_SUCCESS);
        ovstage_query_handle_t query_handle = OVSTAGE_INVALID_QUERY_HANDLE;
        ASSERT_EQ(ovstage_query_from_path_list(stage_, path_list, &query_handle), OVSTAGE_OK);

        ovx_string_t binding_str = ovx_str("material:binding");
        ovx_token_t binding_token{};
        ASSERT_EQ(path_dictionary_create_tokens_from_strings(pd, &binding_str, 1, &binding_token).status,
                  OVX_API_SUCCESS);
        ovx_string_t material_str = ovx_str("/World/Looks/srf_glass");
        ovx_primpath_t material_path[1] = {};
        ASSERT_EQ(path_dictionary_create_paths_from_strings(pd, &material_str, 1, material_path).status,
                  OVX_API_SUCCESS);

        int64_t write_shape[1] = {1};
        DLTensor write_tensor{};
        write_tensor.data = material_path;
        write_tensor.device = {kDLCPU, 0};
        write_tensor.ndim = 1;
        write_tensor.dtype = {kDLUInt, 64, 1};
        write_tensor.shape = write_shape;
        ovstage_write_data_t write_data{};
        write_data.tensors = &write_tensor;
        write_data.tensor_count = 1;
        write_data.is_array = true;
        write_data.semantic = OVSTAGE_SEMANTIC_RELATIONSHIP_PATH_ID;

        ovx_string_or_token_t attr_ref{};
        attr_ref.token = binding_token;

        ovstage_enqueue_result_t wq = ovstage_write_attribute(
            stage_, query_handle, attr_ref, /*ordinal=*/2, write_data, OVSTAGE_PRIM_MODE_UPSERT);
        ASSERT_EQ(wq.status, OVSTAGE_OK) << format_ovstage_last_error();
        docs_wait_ovstage_no_errors(stage_, wq.op_index);
        docs_ovstage_advance_write_floor(stage_, 2);

        ovstage_release_query(stage_, query_handle);
        path_dictionary_release_path_list_reference(pd, path_list);
    }

    ovstage_ordinal_t ordinal = 3;
    int bounce_values[] = {2, 3, 23};
    for (int bounces : bounce_values) {
        write_render_setting_uint32(stage_,
                                     "omni:rtx:rtpt:maxSpecularAndTransmissionBounces",
                                     static_cast<uint32_t>(bounces),
                                     ordinal);
        ASSERT_NO_FATAL_FAILURE(docs_ovstage_advance_write_floor(stage_, ordinal));

        std::string name =
            "settings_rtpt_maxSpecularAndTransmissionBounces.Camera.LdrColor.maxSpecularAndTransmissionBounces-"
            + std::to_string(bounces) + ".0001";
        render_and_save(renderer_, ordinal, name.c_str());
        ordinal++;
    }
}

TEST_F(BaseTest, UpdateFromUsdTimeAsync) {
    std::string scene_path = get_docs_test_data_dir() + "/ovrtx-test-base-logo-animated.usda";
    docs_open_usd_file(scene_path.c_str());
    if (HasFatalFailure()) return;

    ovx_string_t rp_path = ovx_str("/Render/Camera");
    ovrtx_render_product_set_t render_products{};
    render_products.render_products = &rp_path;
    render_products.num_render_products = 1;

    auto translate_x_at = [&](double t_seconds,
                              ovstage_ordinal_t ordinal,
                              double* out_x) {
        // [snippet:doc-update-from-usd-time-async-c]
        // Time-only update: reevaluate every time-sampled attribute in the
        // scene at t_seconds against the stage's timeCodesPerSecond metadata
        // and publish under `ordinal`. Void-return-op — wait on the op_index
        // then advance the write floor.
        ovstage_population_enqueue_result_t pr =
            ovstage_population_apply_usd_time(stage_, ordinal, t_seconds);
        ASSERT_EQ(pr.status, OVSTAGE_OK) << format_ovstage_population_last_error();
        docs_wait_ovstage_population_no_errors(stage_, pr.op_index);
        docs_ovstage_advance_write_floor(stage_, ordinal);
        // [/snippet:doc-update-from-usd-time-async-c]

        // Drive the render pipeline once so the time-sampled attribute writes
        // are consumed before we read the composed transform back.
        ovrtx_step_result_handle_t step_handle = 0;
        ovrtx_enqueue_result_t eq = ovrtx_step_with_stage(
            renderer_, render_products, 1.0, ordinal, &step_handle);
        ASSERT_API_SUCCESS(eq.status);
        docs_wait_no_errors(renderer_, eq.op_index);
        ovrtx_destroy_results(renderer_, step_handle);

        // Read the composed local matrix back through ovstage. omni:xform is
        // a per-prim 4x4 double matrix; USD row-vector convention places
        // translation in the last row.
        std::vector<uint8_t> bytes;
        docs_read_attribute(stage_, "/World/logo", "omni:xform", ordinal, &bytes);
        ASSERT_GE(bytes.size(), sizeof(double) * 16u);
        double const* matrix = reinterpret_cast<double const*>(bytes.data());
        *out_x = matrix[3 * 4 + 0];
    };

    double x_at_start = 0.0;
    double x_at_end = 0.0;
    translate_x_at(0.0, /*ordinal=*/2, &x_at_start);
    if (HasFatalFailure()) return;
    translate_x_at(1.0, /*ordinal=*/3, &x_at_end);
    if (HasFatalFailure()) return;

    EXPECT_GT(std::fabs(x_at_end - x_at_start), 1.0)
        << "expected time-sampled translate to change across time, "
        << "got x(0s)=" << x_at_start << ", x(1s)=" << x_at_end;
}
