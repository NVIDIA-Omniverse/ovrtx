// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Tests for C support APIs that do not naturally fit a workflow-specific test.
// Loosely mirrors tests/docs/python/test_support_api.py (the Python file also
// covers async ovstage / renderer-config APIs; C snippets here focus on
// version + config, ovrtx op-status polling, and get_last_error).

#include <gtest/gtest.h>
#include "helpers.h"

#include <cstdint>
#include <string>

class SupportApiTest : public DocsOvstageTestBase {
protected:
    DOCS_OVSTAGE_TEST_SUITE(SupportApiTest)
};

TEST_F(SupportApiTest, RollingShutterMotionBvhConfig) {
    // [snippet:doc-create-rolling-shutter-renderer-c]
    ovrtx_config_entry_t entries[] = {
        ovrtx_config_entry_motion_bvh(OVRTX_MOTION_BVH_AUTO),
    };
    ovrtx_config_t config = {entries, 1};

    ovrtx_renderer_t* rolling_shutter_renderer = nullptr;
    ovrtx_result_t result = ovrtx_create_renderer(&config, &rolling_shutter_renderer);
    ASSERT_API_SUCCESS(result.status);
    // [/snippet:doc-create-rolling-shutter-renderer-c]

    ASSERT_NE(rolling_shutter_renderer, nullptr);
    ovrtx_destroy_renderer(rolling_shutter_renderer);
}

TEST_F(SupportApiTest, VersionAndConfigConstruction) {
    // [snippet:doc-version-and-config-c]
    uint32_t major = 0;
    uint32_t minor = 0;
    uint32_t patch = 0;
    ovrtx_get_version(&major, &minor, &patch);

    std::string log_level = "info";
    ovrtx_config_entry_t entries[] = {
        ovrtx_config_entry_log_level({ log_level.data(), log_level.size() }),
        ovrtx_config_entry_sync_mode(true),
    };
    ovrtx_config_t config{entries, 2};

    ovrtx_renderer_t* configured_renderer = nullptr;
    ovrtx_result_t create_result = ovrtx_create_renderer(&config, &configured_renderer);
    ASSERT_API_SUCCESS(create_result.status);
    ASSERT_NE(configured_renderer, nullptr);
    // [/snippet:doc-version-and-config-c]

    // The renderer owns the readback storage; changing the caller's entries
    // after creation cannot change the captured config.
    log_level[0] = 'X';
    entries[1].value.bool_value = false;

    ovrtx_config_t captured_config{};
    const ovrtx_result_t get_result = ovrtx_get_config(configured_renderer, &captured_config);
    EXPECT_API_SUCCESS(get_result.status);
    if (get_result.status == OVRTX_API_SUCCESS)
    {
        EXPECT_EQ(captured_config.entry_count, 2u);
        if (captured_config.entry_count == 2u)
        {
            EXPECT_EQ(captured_config.entries[0].key_type, OVRTX_CONFIG_KEY_TYPE_STRING);
            EXPECT_EQ(captured_config.entries[0].key.string_key, OVRTX_CONFIG_LOG_LEVEL);
            EXPECT_EQ(std::string(captured_config.entries[0].value.string_value.ptr,
                                  captured_config.entries[0].value.string_value.length),
                      "info");
            EXPECT_EQ(captured_config.entries[1].key_type, OVRTX_CONFIG_KEY_TYPE_BOOL);
            EXPECT_EQ(captured_config.entries[1].key.bool_key, OVRTX_CONFIG_SYNC_MODE);
            EXPECT_TRUE(captured_config.entries[1].value.bool_value);
        }
    }

    ovrtx_destroy_renderer(configured_renderer);

    EXPECT_TRUE(major != 0u || minor != 0u || patch != 0u);
    EXPECT_EQ(config.entry_count, 2u);
}

TEST_F(SupportApiTest, QueryOperationStatus) {
    // Populate + seal so ovrtx_update_from_stage has a valid ordinal to
    // consume. The update enqueues on ovrtx (returning an ovrtx_op_id_t) —
    // which is what ovrtx_query_op_status accepts.
    docs_load_base();
    if (HasFatalFailure()) return;

    ovrtx_enqueue_result_t eq = ovrtx_update_from_stage(renderer_, /*stage_ordinal=*/1);
    ASSERT_API_SUCCESS(eq.status);

    // [snippet:doc-query-op-status-c]
    ovrtx_op_status_t status{};
    ASSERT_API_SUCCESS(ovrtx_query_op_status(renderer_, eq.op_index, &status).status);
    ASSERT_EQ(status.op_id, eq.op_index);
    ASSERT_TRUE(status.state == OVRTX_EVENT_PENDING ||
                status.state == OVRTX_EVENT_COMPLETED);
    ASSERT_TRUE(status.progress < 0.0 || (status.progress >= 0.0 && status.progress <= 1.0));
    for (size_t i = 0; i < status.counter_count; ++i) {
        ASSERT_NE(status.counters[i].name.ptr, nullptr);
        ASSERT_GT(status.counters[i].name.length, 0u);
        if (status.counters[i].total != 0u) {
            ASSERT_LE(status.counters[i].current, status.counters[i].total);
        }
    }
    ASSERT_API_SUCCESS(ovrtx_release_op_status(renderer_, &status).status);
    // [/snippet:doc-query-op-status-c]

    docs_wait_no_errors(renderer_, eq.op_index);
}

TEST_F(SupportApiTest, QueryMissingExtensionError)
{
    // [snippet:doc-get-last-error-c]
    const void* vtable = nullptr;
    ovrtx_result_t result = ovrtx_query_extension("ovrtx.docs.missing_extension", &vtable);
    ASSERT_EQ(result.status, OVRTX_API_ERROR);

    ovx_string_t error = ovrtx_get_last_error();
    std::string message(error.ptr, error.length);
    // [/snippet:doc-get-last-error-c]

    EXPECT_EQ(vtable, nullptr);
    EXPECT_FALSE(message.empty());
}
