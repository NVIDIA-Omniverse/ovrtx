// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Round-trip tests for the ovstage C-API DLTensor tensor-layout convention.
// Mirrors tests/docs/python/test_attribute_shapes.py.
//
// The C API uses DLTensor lanes for multi-component attribute data: an
// N-element array of float3 values is shape=[N] with dtype.lanes=3, and an
// N-prim array of 4x4 matrices is shape=[N] with dtype.lanes=16. Rendered
// outputs/AOVs are the exception: image tensors use channel-last shapes such
// as [height, width, channels] with dtype.lanes=1.

#include <gtest/gtest.h>
#include "helpers.h"

#include <cstdint>
#include <cstring>
#include <string>

class AttributeShapesTest : public DocsOvstageTestBase {
protected:
    DOCS_OVSTAGE_TEST_SUITE(AttributeShapesTest)
};

TEST_F(AttributeShapesTest, ScalarInt32) {
    docs_load_base();
    if (HasFatalFailure()) return;

    DocsQueryAndToken q;
    docs_make_query_and_token(stage_, "/Render/Camera", "omni:rtx:rtpt:maxBounces", &q);
    if (HasFatalFailure()) return;
    ovx_string_or_token_t attr_ref{};
    attr_ref.token = q.attr_token;

    // [snippet:doc-shape-scalar-int32-c]
    // Scalar per-prim attribute: shape=[N], dtype.lanes=1. N = 1 here.
    uint32_t write_value = 23;
    int64_t write_shape[1] = {1};
    DLTensor write_tensor{};
    write_tensor.data = &write_value;
    write_tensor.device = {kDLCPU, 0};
    write_tensor.ndim = 1;
    write_tensor.dtype = {kDLUInt, 32, 1};
    write_tensor.shape = write_shape;

    ovstage_write_data_t write_data{};
    write_data.tensors = &write_tensor;
    write_data.tensor_count = 1;
    write_data.is_array = false;

    ovstage_enqueue_result_t wq = ovstage_write_attribute(
        stage_, q.query_handle, attr_ref, /*ordinal=*/2, write_data, OVSTAGE_PRIM_MODE_UPSERT);
    ASSERT_EQ(wq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, wq.op_index);
    docs_ovstage_advance_write_floor(stage_, 2);

    // Read back at latest(2) and confirm the DLTensor shape/lanes round-trip.
    ovstage_ordinal_range_t range{};
    range.end_ordinal = 2;
    ovstage_read_handle_t read_handle = OVSTAGE_INVALID_READ_HANDLE;
    ovstage_enqueue_result_t eq = ovstage_read_attributes(
        stage_, q.query_handle, &q.attr_token, 1, range, &read_handle);
    ASSERT_EQ(eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, eq.op_index);

    ovstage_read_group_t group{};
    ASSERT_EQ(ovstage_fetch_read_next(stage_, read_handle, OVSTAGE_TIMEOUT_INFINITE, &group),
              OVSTAGE_OK);

    DLTensor const& t = group.data.tensors[0];
    EXPECT_EQ(t.ndim, 1);
    EXPECT_EQ(t.shape[0], 1);
    EXPECT_EQ(t.dtype.lanes, 1u);
    EXPECT_EQ(*static_cast<uint32_t const*>(t.data), 23u);

    ovstage_release_group(stage_, &group);
    ovstage_release_read(stage_, read_handle);
    // [/snippet:doc-shape-scalar-int32-c]

    docs_release_query_and_token(stage_, &q);
}

// Single-element variant of the lanes-based float3[] layout. Not a doc
// snippet — kept for coverage of the edge case where the array attribute has
// exactly one element.
TEST_F(AttributeShapesTest, Float3ArraySingleElement) {
    docs_load_base();
    if (HasFatalFailure()) return;

    DocsQueryAndToken q;
    docs_make_query_and_token(stage_, "/World/Plane", "points", &q);
    if (HasFatalFailure()) return;
    ovx_string_or_token_t attr_ref{};
    attr_ref.token = q.attr_token;

    float point_data[1][3] = {{1.0f, 2.0f, 3.0f}};
    int64_t write_shape[1] = {1};
    DLTensor write_tensor{};
    write_tensor.data = point_data;
    write_tensor.device = {kDLCPU, 0};
    write_tensor.ndim = 1;
    write_tensor.dtype = {kDLFloat, 32, 3};
    write_tensor.shape = write_shape;

    ovstage_write_data_t write_data{};
    write_data.tensors = &write_tensor;
    write_data.tensor_count = 1;
    write_data.is_array = true;

    ovstage_enqueue_result_t wq = ovstage_write_attribute(
        stage_, q.query_handle, attr_ref, /*ordinal=*/2, write_data, OVSTAGE_PRIM_MODE_UPSERT);
    ASSERT_EQ(wq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, wq.op_index);
    docs_ovstage_advance_write_floor(stage_, 2);

    ovstage_ordinal_range_t range{};
    range.end_ordinal = 2;
    ovstage_read_handle_t read_handle = OVSTAGE_INVALID_READ_HANDLE;
    ovstage_enqueue_result_t eq = ovstage_read_attributes(
        stage_, q.query_handle, &q.attr_token, 1, range, &read_handle);
    ASSERT_EQ(eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, eq.op_index);

    ovstage_read_group_t group{};
    ASSERT_EQ(ovstage_fetch_read_next(stage_, read_handle, OVSTAGE_TIMEOUT_INFINITE, &group),
              OVSTAGE_OK);

    DLTensor const& t = group.data.tensors[0];
    EXPECT_EQ(t.ndim, 1);
    EXPECT_EQ(t.shape[0], 1);
    EXPECT_EQ(t.dtype.lanes, 3u);
    float const* data = static_cast<float const*>(t.data);
    EXPECT_FLOAT_EQ(data[0], 1.0f);
    EXPECT_FLOAT_EQ(data[1], 2.0f);
    EXPECT_FLOAT_EQ(data[2], 3.0f);

    ovstage_release_group(stage_, &group);
    ovstage_release_read(stage_, read_handle);
    docs_release_query_and_token(stage_, &q);
}

TEST_F(AttributeShapesTest, Float3Array) {
    docs_load_base();
    if (HasFatalFailure()) return;

    DocsQueryAndToken q;
    docs_make_query_and_token(stage_, "/World/Plane", "points", &q);
    if (HasFatalFailure()) return;
    ovx_string_or_token_t attr_ref{};
    attr_ref.token = q.attr_token;

    // [snippet:doc-shape-float3-array-c]
    // point3f[] is a variable-length array of 3-component float vectors.
    // In the C API, express it as a 1-D tensor with shape=[M],
    // dtype={kDLFloat, 32, 3}. The lane count is the vector dimension.
    float points_data[4][3] = {
        {-50.0f, 0.0f, -50.0f},
        { 50.0f, 0.0f, -50.0f},
        {-50.0f, 0.0f,  50.0f},
        { 50.0f, 0.0f,  50.0f},
    };
    int64_t write_shape[1] = {4};
    DLTensor write_tensor{};
    write_tensor.data = points_data;
    write_tensor.device = {kDLCPU, 0};
    write_tensor.ndim = 1;
    write_tensor.dtype = {kDLFloat, 32, 3};
    write_tensor.shape = write_shape;

    ovstage_write_data_t write_data{};
    write_data.tensors = &write_tensor;
    write_data.tensor_count = 1;
    write_data.is_array = true;

    ovstage_enqueue_result_t wq = ovstage_write_attribute(
        stage_, q.query_handle, attr_ref, /*ordinal=*/2, write_data, OVSTAGE_PRIM_MODE_UPSERT);
    ASSERT_EQ(wq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, wq.op_index);
    docs_ovstage_advance_write_floor(stage_, 2);

    // Read back — expect ndim=1, shape=[4], dtype.lanes=3.
    ovstage_ordinal_range_t range{};
    range.end_ordinal = 2;
    ovstage_read_handle_t read_handle = OVSTAGE_INVALID_READ_HANDLE;
    ovstage_enqueue_result_t eq = ovstage_read_attributes(
        stage_, q.query_handle, &q.attr_token, 1, range, &read_handle);
    ASSERT_EQ(eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, eq.op_index);

    ovstage_read_group_t group{};
    ASSERT_EQ(ovstage_fetch_read_next(stage_, read_handle, OVSTAGE_TIMEOUT_INFINITE, &group),
              OVSTAGE_OK);

    DLTensor const& t = group.data.tensors[0];
    EXPECT_EQ(t.ndim, 1);
    EXPECT_EQ(t.shape[0], 4);
    EXPECT_EQ(t.dtype.lanes, 3u);

    ovstage_release_group(stage_, &group);
    ovstage_release_read(stage_, read_handle);
    // [/snippet:doc-shape-float3-array-c]

    docs_release_query_and_token(stage_, &q);
}

TEST_F(AttributeShapesTest, Mat4Array) {
    docs_load_base();
    if (HasFatalFailure()) return;

    DocsQueryAndToken q;
    docs_make_query_and_token(stage_, "/World/Camera", "omni:xform", &q);
    if (HasFatalFailure()) return;
    ovx_string_or_token_t attr_ref{};
    attr_ref.token = q.attr_token;

    // [snippet:doc-shape-mat4-array-c]
    // A per-prim 4x4 matrix attribute is a 1-D tensor with shape=[N],
    // dtype={kDLFloat, 64, 16}. The lane count is the matrix element count.
    // The USD row-vector convention places translation in the last row of the
    // matrix; ovstage stamps OVSTAGE_SEMANTIC_MATRIX on the column at creation
    // so the semantic round-trips through Fabric.
    double transforms[1][16] = {{
        1.0,  0.0,  0.0, 0.0,
        0.0,  1.0,  0.0, 0.0,
        0.0,  0.0,  1.0, 0.0,
        10.0, 20.0, 30.0, 1.0,
    }};
    int64_t write_shape[1] = {1};
    DLTensor write_tensor{};
    write_tensor.data = transforms;
    write_tensor.device = {kDLCPU, 0};
    write_tensor.ndim = 1;
    write_tensor.dtype = {kDLFloat, 64, 16};
    write_tensor.shape = write_shape;

    ovstage_write_data_t write_data{};
    write_data.tensors = &write_tensor;
    write_data.tensor_count = 1;
    write_data.is_array = false;
    write_data.semantic = OVSTAGE_SEMANTIC_MATRIX;

    ovstage_enqueue_result_t wq = ovstage_write_attribute(
        stage_, q.query_handle, attr_ref, /*ordinal=*/2, write_data, OVSTAGE_PRIM_MODE_UPSERT);
    ASSERT_EQ(wq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, wq.op_index);
    docs_ovstage_advance_write_floor(stage_, 2);

    // Read back — expect ndim=1, shape=[1], dtype.lanes=16.
    ovstage_ordinal_range_t range{};
    range.end_ordinal = 2;
    ovstage_read_handle_t read_handle = OVSTAGE_INVALID_READ_HANDLE;
    ovstage_enqueue_result_t eq = ovstage_read_attributes(
        stage_, q.query_handle, &q.attr_token, 1, range, &read_handle);
    ASSERT_EQ(eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, eq.op_index);

    ovstage_read_group_t group{};
    ASSERT_EQ(ovstage_fetch_read_next(stage_, read_handle, OVSTAGE_TIMEOUT_INFINITE, &group),
              OVSTAGE_OK);

    DLTensor const& t = group.data.tensors[0];
    EXPECT_EQ(t.ndim, 1);
    EXPECT_EQ(t.shape[0], 1);
    EXPECT_EQ(t.dtype.lanes, 16u);

    double const* data = static_cast<double const*>(t.data);
    // Row 3 (last row) holds the translation under USD's row-vector convention.
    EXPECT_DOUBLE_EQ(data[3 * 4 + 0], 10.0);
    EXPECT_DOUBLE_EQ(data[3 * 4 + 1], 20.0);
    EXPECT_DOUBLE_EQ(data[3 * 4 + 2], 30.0);

    ovstage_release_group(stage_, &group);
    ovstage_release_read(stage_, read_handle);
    // [/snippet:doc-shape-mat4-array-c]

    docs_release_query_and_token(stage_, &q);
}
