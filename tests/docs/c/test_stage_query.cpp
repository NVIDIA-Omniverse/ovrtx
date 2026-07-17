// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Tests for the ovstage query API used with an attached renderer, plus
// coverage of the deprecated ovrtx_query_prims OR/NOT/ALL semantics that
// ovstage's single-conjunction filter cannot yet express. Mirrors
// tests/docs/python/test_stage_query.py (mixed stage/renderer fixtures).

#include <gtest/gtest.h>
#include "helpers.h"

#include <ovrtx/ovrtx_attributes.h>
#include <ovx/path_dictionary/path_dictionary_utils.h>

#include <cstring>
#include <set>
#include <string>
#include <vector>

// ────────────────────────────────────────────────────────────────────────────
// Ovstage-side query tests. Attached-mode; snippets show the ovstage_query /
// fetch_query_result / release_query lifecycle.
// ────────────────────────────────────────────────────────────────────────────

class StageQueryTest : public DocsOvstageTestBase {
protected:
    DOCS_OVSTAGE_TEST_SUITE(StageQueryTest)
};

TEST_F(StageQueryTest, QueryAllPrimsBasic) {
    docs_load_base();
    if (HasFatalFailure()) return;

    // [snippet:doc-query-prims-basic-c]
    // Issue a query with no filter — matches every populated prim on the
    // stage. `query()` is asynchronous; the returned handle is reserved
    // synchronously and can be used as input to reads/writes immediately.
    ovstage_query_handle_t query_handle = OVSTAGE_INVALID_QUERY_HANDLE;
    ovstage_enqueue_result_t eq =
        ovstage_query(stage_, /*filter=*/nullptr, /*attrs=*/nullptr, 0, &query_handle);
    ASSERT_EQ(eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, eq.op_index);

    ovstage_query_result_t qr{};
    ASSERT_EQ(ovstage_fetch_query_result(stage_, query_handle, OVSTAGE_TIMEOUT_INFINITE, &qr),
              OVSTAGE_OK)
        << format_ovstage_last_error();
    printf("matched %zu prims\n", qr.total_prim_count);

    // Always release the fetched result then the query handle when done —
    // the discovered attribute list and the query itself are separate resources.
    ovstage_release_query_result(stage_, &qr);
    ovstage_release_query(stage_, query_handle);
    // [/snippet:doc-query-prims-basic-c]

    EXPECT_GT(qr.total_prim_count, 0u);
}

TEST_F(StageQueryTest, QueryByPrimType) {
    docs_load_base();
    if (HasFatalFailure()) return;

    // [snippet:doc-query-prims-by-type-c]
    // Filter prims by their populated USD type (matched against the built-in
    // usd-prim-type metadata column). ovstage's filter is a conjunction of
    // predicates; each predicate tests one attribute against one operator +
    // a value list.
    ovx_string_t mesh_value = ovx_str("Mesh");
    ovx_string_t attr_name = ovx_str("usd-prim-type");
    ovstage_predicate_t predicate{};
    predicate.attribute.string = attr_name;
    predicate.op = OVSTAGE_FILTER_OP_IN;
    predicate.values = &mesh_value;
    predicate.value_count = 1;

    ovstage_filter_t filter{};
    filter.predicates = &predicate;
    filter.count = 1;

    ovstage_query_handle_t query_handle = OVSTAGE_INVALID_QUERY_HANDLE;
    ovstage_enqueue_result_t eq =
        ovstage_query(stage_, &filter, /*attrs=*/nullptr, 0, &query_handle);
    ASSERT_EQ(eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, eq.op_index);

    ovstage_query_result_t qr{};
    ASSERT_EQ(ovstage_fetch_query_result(stage_, query_handle, OVSTAGE_TIMEOUT_INFINITE, &qr),
              OVSTAGE_OK)
        << format_ovstage_last_error();
    // [/snippet:doc-query-prims-by-type-c]

    EXPECT_GT(qr.total_prim_count, 0u) << "expected at least one Mesh prim";

    std::set<std::string> paths = docs_ovstage_collect_paths(stage_, query_handle, /*ordinal=*/1);
    EXPECT_TRUE(paths.count("/World/Plane") == 1u) << "expected /World/Plane in mesh query";

    ovstage_release_query_result(stage_, &qr);
    ovstage_release_query(stage_, query_handle);
}

TEST_F(StageQueryTest, QueryHasAttribute) {
    docs_load_base();
    if (HasFatalFailure()) return;

    // [snippet:doc-query-has-attribute-c]
    // Match prims that expose an attribute of interest (here "points").
    // FILTER_OP_HAS is the schema-existence test — values must be NULL.
    ovx_string_t attr_name = ovx_str("points");
    ovstage_predicate_t predicate{};
    predicate.attribute.string = attr_name;
    predicate.op = OVSTAGE_FILTER_OP_HAS;

    ovstage_filter_t filter{};
    filter.predicates = &predicate;
    filter.count = 1;
    // [/snippet:doc-query-has-attribute-c]

    ovstage_query_handle_t query_handle = OVSTAGE_INVALID_QUERY_HANDLE;
    ovstage_enqueue_result_t eq =
        ovstage_query(stage_, &filter, /*attrs=*/nullptr, 0, &query_handle);
    ASSERT_EQ(eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, eq.op_index);

    ovstage_query_result_t qr{};
    ASSERT_EQ(ovstage_fetch_query_result(stage_, query_handle, OVSTAGE_TIMEOUT_INFINITE, &qr),
              OVSTAGE_OK)
        << format_ovstage_last_error();

    std::set<std::string> paths = docs_ovstage_collect_paths(stage_, query_handle, /*ordinal=*/1);
    EXPECT_TRUE(paths.count("/World/Plane") == 1u);

    ovstage_release_query_result(stage_, &qr);
    ovstage_release_query(stage_, query_handle);
}

TEST_F(StageQueryTest, PathDictionaryResolve) {
    docs_load_base();
    if (HasFatalFailure()) return;

    // Query the scene's Camera so we have a small, known prim list to resolve.
    ovx_string_t camera_value = ovx_str("Camera");
    ovx_string_t attr_name = ovx_str("usd-prim-type");
    ovstage_predicate_t predicate{};
    predicate.attribute.string = attr_name;
    predicate.op = OVSTAGE_FILTER_OP_IN;
    predicate.values = &camera_value;
    predicate.value_count = 1;

    ovstage_filter_t filter{};
    filter.predicates = &predicate;
    filter.count = 1;

    ovstage_query_handle_t query_handle = OVSTAGE_INVALID_QUERY_HANDLE;
    ovstage_enqueue_result_t eq =
        ovstage_query(stage_, &filter, /*attrs=*/nullptr, 0, &query_handle);
    ASSERT_EQ(eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, eq.op_index);

    ovstage_query_result_t qr{};
    ASSERT_EQ(ovstage_fetch_query_result(stage_, query_handle, OVSTAGE_TIMEOUT_INFINITE, &qr),
              OVSTAGE_OK)
        << format_ovstage_last_error();

    // [snippet:doc-path-dictionary-resolve-c]
    // The stage's path dictionary converts between string paths and internal
    // handles. It is owned by ovstage and valid for the instance's lifetime —
    // no release is required.
    path_dictionary_instance_t* pd = ovstage_get_path_dictionary(stage_);
    ASSERT_NE(pd, nullptr);

    // 1) Enumerate the prims matched by the query. Read usd-prim-type (any
    //    schema-known attribute every populated prim carries would work) and
    //    pull the prim list handle off the returned group.
    ovx_string_t attr_str = ovx_str("usd-prim-type");
    ovx_token_t attr_read_token{};
    ASSERT_EQ(path_dictionary_create_tokens_from_strings(pd, &attr_str, 1, &attr_read_token)
                  .status,
              OVX_API_SUCCESS);

    ovstage_ordinal_range_t range{};
    range.end_ordinal = 1;
    ovstage_read_handle_t read_handle = OVSTAGE_INVALID_READ_HANDLE;
    ovstage_enqueue_result_t reads = ovstage_read_attributes(
        stage_, query_handle, &attr_read_token, 1, range, &read_handle);
    ASSERT_EQ(reads.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, reads.op_index);

    ovstage_read_group_t group{};
    ASSERT_EQ(ovstage_fetch_read_next(stage_, read_handle, OVSTAGE_TIMEOUT_INFINITE, &group),
              OVSTAGE_OK);

    // Pull the prim list handle from the group. Each entry is an
    // ovx_primpath_t handle; decompose to tokens, then to strings.
    ovx_primpath_list_t list_handle = group.prims.list;
    size_t num_paths = 0;
    ASSERT_EQ(path_dictionary_get_num_paths_from_path_list(pd, list_handle, &num_paths).status,
              OVX_API_SUCCESS);
    std::vector<ovx_primpath_t> prim_paths(num_paths);
    size_t out_num = 0;
    ASSERT_EQ(path_dictionary_get_paths_from_path_list(pd, list_handle, 0, num_paths,
                                                        prim_paths.data(), &out_num)
                  .status,
              OVX_API_SUCCESS);

    std::vector<std::string> path_strings;
    for (size_t i = 0; i < out_num; ++i) {
        ovx_token_t token_buf[64];
        ovx_token_t* tokens_out = nullptr;
        size_t num_tokens = 0;
        size_t num_processed = 0;
        ASSERT_EQ(path_dictionary_get_tokens_from_paths(pd, &prim_paths[i], 1, token_buf, 64,
                                                        &tokens_out, &num_tokens, &num_processed)
                      .status,
                  OVX_API_SUCCESS);
        std::string s;
        for (size_t t = 0; t < num_tokens; ++t) {
            ovx_string_t tok_s{};
            ASSERT_EQ(path_dictionary_get_strings_from_tokens(pd, &tokens_out[t], 1, &tok_s).status,
                      OVX_API_SUCCESS);
            s += "/";
            s.append(tok_s.ptr, tok_s.length);
        }
        path_strings.push_back(s);
    }

    // 2) Round-trip: rebuild a path list from the resolved strings and
    //    verify the same count comes back.
    std::vector<ovx_string_t> str_views(path_strings.size());
    for (size_t i = 0; i < path_strings.size(); ++i) {
        str_views[i] = {path_strings[i].c_str(), path_strings[i].size()};
    }
    ovx_primpath_list_t rebuilt{};
    ASSERT_EQ(path_dictionary_create_path_list_from_strings(pd, str_views.data(),
                                                             str_views.size(), &rebuilt)
                  .status,
              OVX_API_SUCCESS);
    size_t rebuilt_num = 0;
    ASSERT_EQ(path_dictionary_get_num_paths_from_path_list(pd, rebuilt, &rebuilt_num).status,
              OVX_API_SUCCESS);
    EXPECT_EQ(rebuilt_num, out_num);
    ASSERT_EQ(path_dictionary_release_path_list_reference(pd, rebuilt).status, OVX_API_SUCCESS);

    ovstage_release_group(stage_, &group);
    ovstage_release_read(stage_, read_handle);
    // [/snippet:doc-path-dictionary-resolve-c]

    // The single Camera prim in the base scene is /World/Camera.
    ASSERT_GE(path_strings.size(), 1u);
    EXPECT_EQ(path_strings[0], "/World/Camera");

    ovstage_release_query_result(stage_, &qr);
    ovstage_release_query(stage_, query_handle);
}

// ────────────────────────────────────────────────────────────────────────────
// Legacy fixture: covers ovrtx_query_prims OR / NOT / ALL semantics that
// ovstage's single-conjunction filter cannot yet express. Mirrors the Python
// tests that are decorated with @pytest.mark.filterwarnings for the same
// reason. The renderer runs in standalone mode here — no ovstage attach.
// ────────────────────────────────────────────────────────────────────────────

class StageQueryLegacyTest : public ::testing::Test {
protected:
    static void SetUpTestSuite() {
        TestConfig tc("StageQueryLegacyTest");
        ovrtx_result_t result = ovrtx_create_renderer(&tc.config, &renderer_);
        ASSERT_API_SUCCESS(result.status);
    }

    static void TearDownTestSuite() {
        if (renderer_) {
            ovrtx_destroy_renderer(renderer_);
            renderer_ = nullptr;
        }
    }

    static void load_base_legacy() {
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

ovrtx_renderer_t* StageQueryLegacyTest::renderer_ = nullptr;

TEST_F(StageQueryLegacyTest, QueryRequireAnyExcludeAllAttrs) {
    load_base_legacy();

    // [snippet:doc-query-require-any-exclude-c]
    // Match Mesh or Camera prims, then exclude Camera. The exclusion removes
    // a prim that would otherwise match the OR clause. ovrtx_query_prims is
    // deprecated in 0.4 but retained for OR / NOT / ALL-attributes queries
    // that ovstage's conjunction-only filter cannot yet express.
    ovx_string_t mesh_type = ovx_str("Mesh");
    ovx_string_t camera_type = ovx_str("Camera");
    ovrtx_filter_t any_filters[2]{};
    any_filters[0].kind = OVRTX_FILTER_PRIM_TYPE;
    any_filters[0].name.string = mesh_type;
    any_filters[1].kind = OVRTX_FILTER_PRIM_TYPE;
    any_filters[1].name.string = camera_type;

    ovrtx_filter_t exclude_filter{};
    exclude_filter.kind = OVRTX_FILTER_PRIM_TYPE;
    exclude_filter.name.string = camera_type;

    ovrtx_query_desc_t desc{};
    desc.require_any = any_filters;
    desc.require_any_count = 2;
    desc.exclude = &exclude_filter;
    desc.exclude_count = 1;
    desc.attribute_filter.mode = OVRTX_ATTRIBUTE_FILTER_ALL;
    // [/snippet:doc-query-require-any-exclude-c]

    ovrtx_query_handle_t query_handle = 0;
    ovrtx_enqueue_result_t eq = ovrtx_query_prims(renderer_, &desc, &query_handle);
    ASSERT_API_SUCCESS(eq.status);
    docs_wait_no_errors(renderer_, eq.op_index);

    ovrtx_query_result_t qr{};
    ASSERT_API_SUCCESS(
        ovrtx_fetch_query_results(renderer_, query_handle, ovrtx_timeout_infinite, &qr).status);

    path_dictionary_instance_t pd{};
    ASSERT_API_SUCCESS(ovrtx_get_path_dictionary(renderer_, &pd).status);
    std::set<std::string> paths = docs_collect_query_paths(qr, &pd);
    EXPECT_TRUE(paths.count("/World/Plane") == 1u);
    EXPECT_FALSE(paths.count("/World/Camera") == 1u);
    ASSERT_GT(qr.group_count, 0u);
    EXPECT_GT(qr.groups[0].attribute_count, 0u);

    ASSERT_API_SUCCESS(ovrtx_release_query_results(renderer_, query_handle).status);
}

TEST_F(StageQueryLegacyTest, QuerySpecificEmptyAttributes) {
    load_base_legacy();

    // [snippet:doc-query-specific-empty-attributes-c]
    // SPECIFIC with an empty attribute list returns matching prims without
    // any attribute descriptors. This attribute-filter mode has no ovstage
    // counterpart today — ovstage's query slot takes explicit tokens.
    ovx_string_t mesh_type = ovx_str("Mesh");
    ovrtx_filter_t filter{};
    filter.kind = OVRTX_FILTER_PRIM_TYPE;
    filter.name.string = mesh_type;

    ovrtx_query_desc_t desc{};
    desc.require_all = &filter;
    desc.require_all_count = 1;
    desc.attribute_filter.mode = OVRTX_ATTRIBUTE_FILTER_SPECIFIC;
    desc.attribute_filter.attribute_names = nullptr;
    desc.attribute_filter.attribute_name_count = 0;
    // [/snippet:doc-query-specific-empty-attributes-c]

    ovrtx_query_handle_t query_handle = 0;
    ovrtx_enqueue_result_t eq = ovrtx_query_prims(renderer_, &desc, &query_handle);
    ASSERT_API_SUCCESS(eq.status);
    docs_wait_no_errors(renderer_, eq.op_index);

    ovrtx_query_result_t qr{};
    ASSERT_API_SUCCESS(
        ovrtx_fetch_query_results(renderer_, query_handle, ovrtx_timeout_infinite, &qr).status);

    path_dictionary_instance_t pd{};
    ASSERT_API_SUCCESS(ovrtx_get_path_dictionary(renderer_, &pd).status);
    std::set<std::string> paths = docs_collect_query_paths(qr, &pd);
    EXPECT_TRUE(paths.count("/World/Plane") == 1u);
    for (size_t g = 0; g < qr.group_count; ++g) {
        EXPECT_EQ(qr.groups[g].attribute_count, 0u);
    }

    ASSERT_API_SUCCESS(ovrtx_release_query_results(renderer_, query_handle).status);
}
