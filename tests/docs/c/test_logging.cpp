// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Test for ovrtx_set_log_callback channel filtering (RUST_LOG-style
// channel-prefix thresholds).
//
// The renderer runs in STANDALONE mode (no ovstage attach) so we can drive
// ovrtx-native scene-load activity to generate reliable log traffic. The
// ovstage population log stream flows through a separate ovstage_set_log_callback
// bridge — the ovrtx callback under test does not capture it, so an
// attached-mode variant would need to trigger ovrtx-side activity through
// ovrtx_step_with_stage. ovrtx_set_log_callback itself is not deprecated;
// only the trigger APIs (ovrtx_open_usd_from_file / ovrtx_reset_stage) are.

#include <gtest/gtest.h>
#include "helpers.h"

#include <atomic>
#include <cstring>
#include <string>

namespace {
std::atomic<int> g_message_count{0};

void count_messages(ovrtx_log_severity_t /*severity*/,
                    double /*timestamp*/,
                    ovx_string_t /*message*/,
                    void* user_data) {
    auto* counter = static_cast<std::atomic<int>*>(user_data);
    counter->fetch_add(1, std::memory_order_relaxed);
}
} // anonymous namespace

class LoggingTest : public ::testing::Test {
protected:
    static void SetUpTestSuite() {
        // Pin the log level to "info" so the test does not depend on the
        // ambient default for assertions on info-level messages.
        TestConfig tc("LoggingTest", "info");
        ovrtx_result_t result = ovrtx_create_renderer(&tc.config, &renderer_);
        ASSERT_API_SUCCESS(result.status);
    }

    static void TearDownTestSuite() {
        if (renderer_) {
            // Clear any active log callback before destroying the renderer.
            ovrtx_set_log_callback(OVRTX_LOG_INFO, nullptr, nullptr, nullptr);
            ovrtx_destroy_renderer(renderer_);
            renderer_ = nullptr;
        }
    }

    // Load the base scene and reset the renderer — a reliable source of log
    // activity (shader/texture/material loading).
    static void do_open_usd() {
        std::string scene = get_docs_test_data_dir() + "/ovrtx-test-base.usda";
        ovrtx_enqueue_result_t eq = ovrtx_open_usd_from_file(renderer_, {scene.c_str(), scene.size()});
        ASSERT_API_SUCCESS(eq.status);
        ovrtx_op_wait_result_t wait_result;
        ASSERT_API_SUCCESS(ovrtx_wait_op(renderer_, eq.op_index, ovrtx_timeout_infinite, &wait_result).status);
    }

    static ovrtx_renderer_t* renderer_;
};

ovrtx_renderer_t* LoggingTest::renderer_ = nullptr;

TEST_F(LoggingTest, LogCallbackPrefixFilter) {
    // [snippet:doc-log-callback-prefix-filter-c]
    // First pass: receive all messages (NULL channel filter).
    g_message_count.store(0);
    ovrtx_result_t r = ovrtx_set_log_callback(OVRTX_LOG_INFO,
                                              nullptr, // NULL = all channels
                                              &count_messages,
                                              &g_message_count);
    ASSERT_API_SUCCESS(r.status);

    // Reset first so the renderer is in a clean state.
    ovrtx_enqueue_result_t eq = ovrtx_reset_stage(renderer_);
    ASSERT_API_SUCCESS(eq.status);
    ovrtx_op_wait_result_t wait_result;
    ASSERT_API_SUCCESS(ovrtx_wait_op(renderer_, eq.op_index, ovrtx_timeout_infinite, &wait_result).status);

    do_open_usd();

    // Ensure pending log messages have been delivered through the callback.
    ovrtx_timeout_t flush_timeout{5'000'000'000ull};
    ovrtx_flush_log(flush_timeout);

    int observed_any_channel = g_message_count.load();

    // Second pass: install a high default threshold and an explicit low
    // threshold for a channel prefix that cannot match any real channel.
    g_message_count.store(0);
    std::string bogus = "this.channel.does.not.exist.42=info";
    ovx_string_t filter{bogus.c_str(), bogus.size()};
    r = ovrtx_set_log_callback(OVRTX_LOG_FATAL, &filter, &count_messages, &g_message_count);
    ASSERT_API_SUCCESS(r.status);

    // Re-run the same work and flush — the callback should not fire.
    eq = ovrtx_reset_stage(renderer_);
    ASSERT_API_SUCCESS(eq.status);
    ASSERT_API_SUCCESS(ovrtx_wait_op(renderer_, eq.op_index, ovrtx_timeout_infinite, &wait_result).status);

    do_open_usd();
    ovrtx_flush_log(flush_timeout);

    int observed_bogus_filter = g_message_count.load();

    // Disable the callback before the renderer is torn down.
    ovrtx_set_log_callback(OVRTX_LOG_INFO, nullptr, nullptr, nullptr);
    // [/snippet:doc-log-callback-prefix-filter-c]

    EXPECT_GT(observed_any_channel, 0) << "expected at least one log message with NULL filter";
    EXPECT_EQ(observed_bogus_filter, 0)
        << "expected the bogus channel prefix to suppress all messages";
}
