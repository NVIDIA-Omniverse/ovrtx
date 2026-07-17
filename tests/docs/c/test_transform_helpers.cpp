// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Tests for transform convenience helpers in ovrtx_attributes.h.

#include <gtest/gtest.h>
#include "helpers.h"

#include <ovrtx/ovrtx_attributes.h>

#include <cstdint>
#include <cstring>
#include <string>

namespace {

void read_xform_matrix(ovrtx_renderer_t* renderer, char const* prim_path, double out_matrix[16]) {
    ovx_string_t prim = ovx_str(prim_path);
    DLDataType mat_type = {kDLFloat, 64, 16};
    ovrtx_binding_desc_or_handle_t binding =
        ovrtx_make_binding_desc(&prim, 1, ovx_str("omni:xform"), OVRTX_SEMANTIC_NONE, mat_type);

    ovrtx_read_handle_t read_handle = 0;
    ovrtx_enqueue_result_t eq = ovrtx_read_attribute(renderer, &binding, nullptr, &read_handle);
    ASSERT_API_SUCCESS(eq.status);
    docs_wait_no_errors(renderer, eq.op_index);

    ovrtx_read_output_t output{};
    ASSERT_API_SUCCESS(
        ovrtx_fetch_read_result(renderer, read_handle, ovrtx_timeout_infinite, &output).status);
    ASSERT_EQ(output.buffer_count, 1u);

    double const* matrix = static_cast<double const*>(output.buffers[0].dl.data);
    for (int i = 0; i < 16; ++i) {
        out_matrix[i] = matrix[i];
    }

    ovrtx_cuda_sync_t no_sync{};
    ASSERT_API_SUCCESS(ovrtx_release_read_result(renderer, read_handle, no_sync).status);
}

void read_reset_xform_stack(ovrtx_renderer_t* renderer, char const* prim_path, bool* out_value) {
    ovx_string_t prim = ovx_str(prim_path);
    DLDataType bool_type = {kDLUInt, 8, 1};
    ovrtx_binding_desc_or_handle_t binding = ovrtx_make_binding_desc(
        &prim, 1, ovx_str("omni:resetXformStack"), OVRTX_SEMANTIC_NONE, bool_type);

    ovrtx_read_handle_t read_handle = 0;
    ovrtx_enqueue_result_t eq = ovrtx_read_attribute(renderer, &binding, nullptr, &read_handle);
    ASSERT_API_SUCCESS(eq.status);
    docs_wait_no_errors(renderer, eq.op_index);

    ovrtx_read_output_t output{};
    ASSERT_API_SUCCESS(
        ovrtx_fetch_read_result(renderer, read_handle, ovrtx_timeout_infinite, &output).status);
    ASSERT_EQ(output.buffer_count, 1u);

    uint8_t const* values = static_cast<uint8_t const*>(output.buffers[0].dl.data);
    *out_value = values[0] != 0;

    ovrtx_cuda_sync_t no_sync{};
    ASSERT_API_SUCCESS(ovrtx_release_read_result(renderer, read_handle, no_sync).status);
}

} // namespace

class TransformHelpersTest : public ::testing::Test {
protected:
    static void SetUpTestSuite() {
        TestConfig tc("TransformHelpersTest");
        ovrtx_result_t result = ovrtx_create_renderer(&tc.config, &renderer_);
        ASSERT_API_SUCCESS(result.status);
    }

    static void TearDownTestSuite() {
        if (renderer_) {
            ovrtx_destroy_renderer(renderer_);
            renderer_ = nullptr;
        }
    }

    static void load_base() {
        ovrtx_enqueue_result_t eq = ovrtx_reset_stage(renderer_);
        ASSERT_API_SUCCESS(eq.status);
        docs_wait_no_errors(renderer_, eq.op_index);

        std::string scene = get_docs_test_data_dir() + "/ovrtx-test-base.usda";
        eq = ovrtx_open_usd_from_file(renderer_, {scene.c_str(), scene.size()});
        ASSERT_API_SUCCESS(eq.status);
        docs_wait_no_errors(renderer_, eq.op_index);

        eq = ovrtx_reset(renderer_, 0.0);
        ASSERT_API_SUCCESS(eq.status);
        docs_wait_no_errors(renderer_, eq.op_index);
    }

    static ovrtx_renderer_t* renderer_;
};

ovrtx_renderer_t* TransformHelpersTest::renderer_ = nullptr;

TEST_F(TransformHelpersTest, SetXformMat) {
    load_base();

    // [snippet:doc-set-xform-mat-c]
    ovx_string_t prim = ovx_str("/World/Plane");
    ovrtx_xform_matrix44d_t matrix{};
    matrix.v[0] = 1.0;
    matrix.v[5] = 1.0;
    matrix.v[10] = 1.0;
    matrix.v[15] = 1.0;
    matrix.v[12] = 5.0;

    ovrtx_enqueue_result_t eq = ovrtx_set_xform_mat(renderer_, &prim, 1, &matrix);
    ASSERT_API_SUCCESS(eq.status);
    docs_wait_no_errors(renderer_, eq.op_index);
    // [/snippet:doc-set-xform-mat-c]

    double matrix_out[16]{};
    read_xform_matrix(renderer_, "/World/Plane", matrix_out);
    EXPECT_DOUBLE_EQ(matrix_out[12], 5.0);
}

TEST_F(TransformHelpersTest, SetXformPosRotScale) {
    load_base();

    // [snippet:doc-set-xform-pos-rot-scale-c]
    ovx_string_t prim = ovx_str("/World/Plane");
    ovrtx_xform_pos3d_rot4f_scale3f_t transform{};
    transform.position[0] = 6.0;
    transform.rot_quat_xyzw[0] = 1.0f; // 180 degrees around X.
    transform.scale[0] = 2.0f;
    transform.scale[1] = 3.0f;
    transform.scale[2] = 4.0f;

    ovrtx_enqueue_result_t eq = ovrtx_set_xform_pos_rot_scale(renderer_, &prim, 1, &transform);
    ASSERT_API_SUCCESS(eq.status);
    docs_wait_no_errors(renderer_, eq.op_index);
    // [/snippet:doc-set-xform-pos-rot-scale-c]

    double matrix_out[16]{};
    read_xform_matrix(renderer_, "/World/Plane", matrix_out);
    EXPECT_DOUBLE_EQ(matrix_out[12], 6.0);
    EXPECT_NEAR(matrix_out[0], 2.0, 1e-6);
    EXPECT_NEAR(matrix_out[5], -3.0, 1e-6);
    EXPECT_NEAR(matrix_out[10], -4.0, 1e-6);
}

TEST_F(TransformHelpersTest, SetXformPosRot3x3) {
    load_base();

    // [snippet:doc-set-xform-pos-rot3x3-c]
    ovx_string_t prim = ovx_str("/World/Plane");
    ovrtx_xform_pos3d_rot3x3f_t transform{};
    transform.position[0] = 7.0;
    transform.rot_matrix[0] = -1.0f;
    transform.rot_matrix[4] = -1.0f;
    transform.rot_matrix[8] = 1.0f;

    ovrtx_enqueue_result_t eq = ovrtx_set_xform_pos_rot3x3(renderer_, &prim, 1, &transform);
    ASSERT_API_SUCCESS(eq.status);
    docs_wait_no_errors(renderer_, eq.op_index);
    // [/snippet:doc-set-xform-pos-rot3x3-c]

    double matrix_out[16]{};
    read_xform_matrix(renderer_, "/World/Plane", matrix_out);
    EXPECT_DOUBLE_EQ(matrix_out[12], 7.0);
    EXPECT_NEAR(matrix_out[0], -1.0, 1e-6);
    EXPECT_NEAR(matrix_out[5], -1.0, 1e-6);
    EXPECT_NEAR(matrix_out[10], 1.0, 1e-6);
}

TEST_F(TransformHelpersTest, SetResetXformStack) {
    load_base();

    // [snippet:doc-set-reset-xform-stack-c]
    ovx_string_t prim = ovx_str("/World/Plane");
    bool reset_stack = true;
    ovrtx_enqueue_result_t eq = ovrtx_set_reset_xform_stack(renderer_, &prim, 1, &reset_stack);
    ASSERT_API_SUCCESS(eq.status);
    docs_wait_no_errors(renderer_, eq.op_index);
    // [/snippet:doc-set-reset-xform-stack-c]

    bool value = false;
    read_reset_xform_stack(renderer_, "/World/Plane", &value);
    EXPECT_TRUE(value);
}
