// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Tests for non-transform attribute convenience helpers in ovrtx_attributes.h.

#include <gtest/gtest.h>
#include "helpers.h"

#include <ovrtx/ovrtx_attributes.h>

#include <set>
#include <string>

class AttributeHelpersTest : public ::testing::Test {
protected:
    static void SetUpTestSuite() {
        TestConfig tc("AttributeHelpersTest");
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

ovrtx_renderer_t* AttributeHelpersTest::renderer_ = nullptr;

TEST_F(AttributeHelpersTest, SetTokenAttributes) {
    load_base();

    // [snippet:doc-set-token-attributes-c]
    ovx_string_t prim = ovx_str("/World/Plane");
    ovx_string_t purpose = ovx_str("guide");
    ovrtx_enqueue_result_t eq =
        ovrtx_set_token_attributes(renderer_, &prim, 1, ovx_str("purpose"), &purpose);
    ASSERT_API_SUCCESS(eq.status);
    docs_wait_no_errors(renderer_, eq.op_index);
    // [/snippet:doc-set-token-attributes-c]

    ovx_token_or_string_t attr_name{};
    attr_name.string = ovx_str("purpose");

    ovrtx_filter_t filter{};
    filter.kind = OVRTX_FILTER_HAS_ATTRIBUTE;
    filter.name = attr_name;
    ovrtx_query_desc_t desc{};
    desc.require_all = &filter;
    desc.require_all_count = 1;
    desc.attribute_filter.mode = OVRTX_ATTRIBUTE_FILTER_SPECIFIC;
    desc.attribute_filter.attribute_names = &attr_name;
    desc.attribute_filter.attribute_name_count = 1;

    ovrtx_query_handle_t query_handle{};
    eq = ovrtx_query_prims(renderer_, &desc, &query_handle);
    ASSERT_API_SUCCESS(eq.status);
    docs_wait_no_errors(renderer_, eq.op_index);

    ovrtx_query_result_t qr{};
    ASSERT_API_SUCCESS(ovrtx_fetch_query_results(renderer_, query_handle, ovrtx_timeout_infinite, &qr).status);
    path_dictionary_instance_t pd{};
    ASSERT_API_SUCCESS(ovrtx_get_path_dictionary(renderer_, &pd).status);
    std::set<std::string> paths = docs_collect_query_paths(qr, &pd);
    EXPECT_TRUE(paths.count("/World/Plane"));
    bool saw_token_attribute = false;
    for (size_t g = 0; g < qr.group_count; ++g) {
        for (size_t a = 0; a < qr.groups[g].attribute_count; ++a) {
            ovrtx_attribute_type_t const& type = qr.groups[g].attributes[a].type;
            if (type.semantic == OVRTX_SEMANTIC_TOKEN_ID && !type.is_array) {
                saw_token_attribute = true;
            }
        }
    }
    EXPECT_TRUE(saw_token_attribute);
    ASSERT_API_SUCCESS(ovrtx_release_query_results(renderer_, query_handle).status);
}
