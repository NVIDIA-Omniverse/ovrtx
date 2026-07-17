// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Tests for the ovstage "binding" pattern (query handle + interned attribute
// token) and zero-copy map/unmap writes. Mirrors the query-as-binding shape
// of tests/docs/python/test_attribute_bindings.py. The old ovrtx binding-
// handle model (ovrtx_create_attribute_binding / ovrtx_destroy_attribute_binding)
// is deprecated in 0.4; ovstage's query handles play that role directly.

#include <gtest/gtest.h>
#include "helpers.h"

#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

namespace {

// Read /World/Plane's omni:xform translation X back for verification. Kept
// out of the snippet blocks — the docs render the write path only.
void read_xform_translation_x(ovstage_instance_t* stage,
                              char const* prim_path,
                              ovstage_ordinal_t ordinal,
                              double* out_x) {
    std::vector<uint8_t> bytes;
    docs_read_attribute(stage, prim_path, "omni:xform", ordinal, &bytes);
    ASSERT_GE(bytes.size(), sizeof(double) * 16u);
    // 4x4 matrix, USD row-vector convention — translation in the last row,
    // so translation.x is at flat index 3*4 + 0 = 12.
    double const* matrix = reinterpret_cast<double const*>(bytes.data());
    *out_x = matrix[12];
}

} // namespace

class AttributeBindingsTest : public DocsOvstageTestBase {
protected:
    DOCS_OVSTAGE_TEST_SUITE(AttributeBindingsTest)
};

TEST_F(AttributeBindingsTest, CreateWriteDestroyBinding) {
    docs_load_base();
    if (HasFatalFailure()) return;

    // [snippet:doc-create-attribute-binding-c]
    // The ovstage "binding" is the pair (query handle, interned attribute
    // token). The query identifies the target prims; the token identifies the
    // attribute. Both are reserved synchronously and reusable across many
    // writes/reads until released.
    path_dictionary_instance_t* pd = ovstage_get_path_dictionary(stage_);
    ovx_string_t prim_path = ovx_str("/World/Plane");
    ovx_primpath_list_t path_list{};
    ASSERT_EQ(path_dictionary_create_path_list_from_strings(pd, &prim_path, 1, &path_list).status,
              OVX_API_SUCCESS);

    ovstage_query_handle_t query_handle = OVSTAGE_INVALID_QUERY_HANDLE;
    ASSERT_EQ(ovstage_query_from_path_list(stage_, path_list, &query_handle), OVSTAGE_OK)
        << format_ovstage_last_error();

    ovx_string_t attr_str = ovx_str("omni:xform");
    ovx_token_t attr_token{};
    ASSERT_EQ(path_dictionary_create_tokens_from_strings(pd, &attr_str, 1, &attr_token).status,
              OVX_API_SUCCESS);
    // [/snippet:doc-create-attribute-binding-c]

    // [snippet:doc-write-bound-attribute-c]
    // Write through the (query, token) binding. omni:xform is a per-prim 4x4
    // double matrix — shape=[1], lanes=16, with OVSTAGE_SEMANTIC_MATRIX.
    // Translation lives in the last row (USD row-vector convention).
    double matrix[16] = {
        1.0,  0.0,  0.0, 0.0,
        0.0,  1.0,  0.0, 0.0,
        0.0,  0.0,  1.0, 0.0,
        14.0, 0.0,  0.0, 1.0,
    };
    int64_t write_shape[1] = {1};
    DLTensor write_tensor{};
    write_tensor.data = matrix;
    write_tensor.device = {kDLCPU, 0};
    write_tensor.ndim = 1;
    write_tensor.dtype = {kDLFloat, 64, 16};
    write_tensor.shape = write_shape;

    ovstage_write_data_t write_data{};
    write_data.tensors = &write_tensor;
    write_data.tensor_count = 1;
    write_data.is_array = false;
    write_data.semantic = OVSTAGE_SEMANTIC_MATRIX;

    ovx_string_or_token_t attr_ref{};
    attr_ref.token = attr_token;

    ovstage_enqueue_result_t wq = ovstage_write_attribute(
        stage_, query_handle, attr_ref, /*ordinal=*/2, write_data, OVSTAGE_PRIM_MODE_UPSERT);
    ASSERT_EQ(wq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, wq.op_index);
    docs_ovstage_advance_write_floor(stage_, 2);
    // [/snippet:doc-write-bound-attribute-c]

    double x = 0.0;
    read_xform_translation_x(stage_, "/World/Plane", 2, &x);
    EXPECT_DOUBLE_EQ(x, 14.0);

    // [snippet:doc-destroy-attribute-binding-c]
    // Release the query handle (per-handle-ordered: waits for in-flight
    // reads/writes to complete) and drop the path-list refcount.
    ovstage_release_query(stage_, query_handle);
    path_dictionary_release_path_list_reference(pd, path_list);
    // [/snippet:doc-destroy-attribute-binding-c]
}

TEST_F(AttributeBindingsTest, MapAndUnmapAttribute) {
    docs_load_base();
    if (HasFatalFailure()) return;

    // Set up the (query, token) binding — same shape as CreateWriteDestroyBinding.
    path_dictionary_instance_t* pd = ovstage_get_path_dictionary(stage_);
    ovx_string_t prim_path = ovx_str("/World/Plane");
    ovx_primpath_list_t path_list{};
    ASSERT_EQ(path_dictionary_create_path_list_from_strings(pd, &prim_path, 1, &path_list).status,
              OVX_API_SUCCESS);
    ovstage_query_handle_t query_handle = OVSTAGE_INVALID_QUERY_HANDLE;
    ASSERT_EQ(ovstage_query_from_path_list(stage_, path_list, &query_handle), OVSTAGE_OK)
        << format_ovstage_last_error();
    ovx_string_t attr_str = ovx_str("omni:xform");
    ovx_token_t attr_token{};
    ASSERT_EQ(path_dictionary_create_tokens_from_strings(pd, &attr_str, 1, &attr_token).status,
              OVX_API_SUCCESS);

    // [snippet:doc-map-attribute-cpu-c]
    // Zero-copy write via map/unmap: map_attribute hands back writable
    // storage for each matched prim; the caller fills it, then unmap_attribute
    // commits and releases the map session.
    ovx_string_or_token_t attr_ref{};
    attr_ref.token = attr_token;
    ovstage_map_desc_t map_desc{};
    map_desc.attribute = attr_ref;
    map_desc.dtype = {kDLFloat, 64, 16};
    map_desc.semantic = OVSTAGE_SEMANTIC_MATRIX;
    map_desc.prim_mode = OVSTAGE_PRIM_MODE_UPSERT;

    ovstage_map_handle_t map_handle = OVSTAGE_INVALID_MAP_HANDLE;
    ovstage_enqueue_result_t mq = ovstage_map_attribute(
        stage_, query_handle, &map_desc, /*ordinal=*/2,
        /*element_sizes=*/nullptr, /*element_count=*/0, &map_handle);
    ASSERT_EQ(mq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, mq.op_index);

    ovstage_map_group_t map_group{};
    ASSERT_EQ(ovstage_fetch_map_next(stage_, map_handle, OVSTAGE_TIMEOUT_INFINITE, &map_group),
              OVSTAGE_OK);
    double* matrix = static_cast<double*>(map_group.data.tensors[0].data);
    matrix[0] = 1.0;
    matrix[5] = 1.0;
    matrix[10] = 1.0;
    matrix[15] = 1.0;
    matrix[12] = 15.0; // translation.x under USD row-vector convention

    // Commit all pending groups and release the map handle.
    ovstage_cuda_sync_t no_sync{};
    ovstage_enqueue_result_t uq = ovstage_unmap_attribute(stage_, map_handle, no_sync);
    ASSERT_EQ(uq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, uq.op_index);
    docs_ovstage_advance_write_floor(stage_, 2);
    // [/snippet:doc-map-attribute-cpu-c]

    double x = 0.0;
    read_xform_translation_x(stage_, "/World/Plane", 2, &x);
    EXPECT_DOUBLE_EQ(x, 15.0);

    ovstage_release_query(stage_, query_handle);
    path_dictionary_release_path_list_reference(pd, path_list);
}
