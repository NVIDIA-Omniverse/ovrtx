// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Tests for ovstage attribute reads used with an attached renderer. Mirrors
// tests/docs/python/test_attribute_read.py.
// - Scalar test: write-then-read omni:rtx:rtpt:maxBounces on /Render/Camera.
// - Array test: read the authored "points" attribute from /World/Plane.

#include <gtest/gtest.h>
#include "helpers.h"

#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

class AttributeReadTest : public DocsOvstageTestBase {
protected:
    DOCS_OVSTAGE_TEST_SUITE(AttributeReadTest)
};

TEST_F(AttributeReadTest, ReadScalarAttribute) {
    docs_load_base();
    if (HasFatalFailure()) return;

    // Setup a single-prim query on /Render/Camera and intern the attribute
    // token. Both are kept alive across the write and the read.
    path_dictionary_instance_t* pd = ovstage_get_path_dictionary(stage_);
    ASSERT_NE(pd, nullptr);

    ovx_string_t prim_path = ovx_str("/Render/Camera");
    ovx_primpath_list_t path_list{};
    ASSERT_EQ(path_dictionary_create_path_list_from_strings(pd, &prim_path, 1, &path_list).status,
              OVX_API_SUCCESS);

    ovstage_query_handle_t query_handle = OVSTAGE_INVALID_QUERY_HANDLE;
    ASSERT_EQ(ovstage_query_from_path_list(stage_, path_list, &query_handle), OVSTAGE_OK)
        << format_ovstage_last_error();

    ovx_string_t attr_name = ovx_str("omni:rtx:rtpt:maxBounces");
    ovx_token_t attr_token{};
    ASSERT_EQ(path_dictionary_create_tokens_from_strings(pd, &attr_name, 1, &attr_token).status,
              OVX_API_SUCCESS);

    // Write 17 to maxBounces at ordinal 2, then seal so a subsequent read at
    // latest(2) has committed data to observe.
    uint32_t write_value = 17;
    int64_t write_shape[1] = {1};
    DLTensor write_tensor{};
    write_tensor.data = &write_value;
    write_tensor.device = {kDLCPU, 0};
    write_tensor.ndim = 1;
    write_tensor.dtype = {kDLUInt, 32, 1};
    write_tensor.shape = write_shape;
    write_tensor.strides = nullptr;
    write_tensor.byte_offset = 0;

    ovstage_write_data_t write_data{};
    write_data.tensors = &write_tensor;
    write_data.tensor_count = 1;
    write_data.is_array = false;

    ovx_string_or_token_t attr_ref{};
    attr_ref.token = attr_token;

    ovstage_enqueue_result_t wq = ovstage_write_attribute(
        stage_, query_handle, attr_ref, /*ordinal=*/2, write_data, OVSTAGE_PRIM_MODE_UPSERT);
    ASSERT_EQ(wq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, wq.op_index);
    docs_ovstage_advance_write_floor(stage_, 2);

    // [snippet:doc-read-attribute-scalar-c]
    // Enqueue a read for a schema-known attribute over one prim, at latest(2).
    // The read handle is reserved synchronously — pass it to fetch_read_next
    // once the returned op_index completes.
    ovstage_ordinal_range_t range{};
    range.has_start_ordinal = false;
    range.end_ordinal = 2;

    ovstage_read_handle_t read_handle = OVSTAGE_INVALID_READ_HANDLE;
    ovstage_enqueue_result_t eq = ovstage_read_attributes(
        stage_, query_handle, &attr_token, 1, range, &read_handle);
    ASSERT_EQ(eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, eq.op_index);

    // Fetch the first (and, for a single-prim scalar read, only) group. The
    // group's tensor is a DLPack view into the sealed attribute storage —
    // valid until release_group.
    ovstage_read_group_t group{};
    ASSERT_EQ(ovstage_fetch_read_next(stage_, read_handle, OVSTAGE_TIMEOUT_INFINITE, &group),
              OVSTAGE_OK)
        << format_ovstage_last_error();
    ASSERT_GT(group.data.tensor_count, 0u);
    uint32_t value = *static_cast<uint32_t const*>(group.data.tensors[0].data);

    // Release the fetched storage (synchronous) then the read handle (async;
    // the release is per-handle-ordered so any in-flight fetch drains first).
    ovstage_release_group(stage_, &group);
    ovstage_release_read(stage_, read_handle);
    // [/snippet:doc-read-attribute-scalar-c]

    EXPECT_EQ(value, 17u);

    ovstage_release_query(stage_, query_handle);
    path_dictionary_release_path_list_reference(pd, path_list);
}

TEST_F(AttributeReadTest, ReadArrayAttribute) {
    docs_load_base();
    if (HasFatalFailure()) return;

    // Setup: single-prim query on /World/Plane and the "points" token.
    path_dictionary_instance_t* pd = ovstage_get_path_dictionary(stage_);
    ASSERT_NE(pd, nullptr);

    ovx_string_t prim_path = ovx_str("/World/Plane");
    ovx_primpath_list_t path_list{};
    ASSERT_EQ(path_dictionary_create_path_list_from_strings(pd, &prim_path, 1, &path_list).status,
              OVX_API_SUCCESS);

    ovstage_query_handle_t query_handle = OVSTAGE_INVALID_QUERY_HANDLE;
    ASSERT_EQ(ovstage_query_from_path_list(stage_, path_list, &query_handle), OVSTAGE_OK)
        << format_ovstage_last_error();

    ovx_string_t attr_name = ovx_str("points");
    ovx_token_t attr_token{};
    ASSERT_EQ(path_dictionary_create_tokens_from_strings(pd, &attr_name, 1, &attr_token).status,
              OVX_API_SUCCESS);

    // [snippet:doc-read-array-attribute-c]
    // Array attributes are variable-length per prim. Read semantics are the
    // same as for scalars — enqueue, wait, fetch — but the DLTensor's shape
    // reflects the per-prim element count; for `points` (float3 array) the
    // dtype.lanes carries the tuple width and the leading shape dim carries
    // the element (point) count.
    ovstage_ordinal_range_t range{};
    range.has_start_ordinal = false;
    range.end_ordinal = 1;

    ovstage_read_handle_t read_handle = OVSTAGE_INVALID_READ_HANDLE;
    ovstage_enqueue_result_t eq = ovstage_read_attributes(
        stage_, query_handle, &attr_token, 1, range, &read_handle);
    ASSERT_EQ(eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, eq.op_index);

    ovstage_read_group_t group{};
    ASSERT_EQ(ovstage_fetch_read_next(stage_, read_handle, OVSTAGE_TIMEOUT_INFINITE, &group),
              OVSTAGE_OK)
        << format_ovstage_last_error();
    ASSERT_GT(group.data.tensor_count, 0u);
    ASSERT_TRUE(group.is_array);

    DLTensor const& t = group.data.tensors[0];
    // ovrtx-test-base-geometry.usda authors 4 float3 points on the Plane.
    ASSERT_EQ(t.dtype.code, kDLFloat);
    ASSERT_EQ(t.dtype.bits, 32u);
    ASSERT_EQ(t.dtype.lanes, 3u);
    ASSERT_EQ(t.ndim, 1);
    ASSERT_EQ(t.shape[0], 4);
    int64_t element_count = t.shape[0] * t.dtype.lanes;

    ovstage_release_group(stage_, &group);
    ovstage_release_read(stage_, read_handle);
    // [/snippet:doc-read-array-attribute-c]

    EXPECT_EQ(element_count, 12);

    ovstage_release_query(stage_, query_handle);
    path_dictionary_release_path_list_reference(pd, path_list);
}
