// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Tests for the ovrtx_wait_op error-retrieval semantics:
// the wait result returns the list of op ids that errored plus the lowest
// still-pending op id; per-op error strings are fetched via
// ovrtx_get_last_op_error().
//
// The renderer runs in STANDALONE mode (no ovstage attach) so we can use a
// deprecated ovrtx_open_usd_from_file call with a nonexistent path as the
// guaranteed failure trigger. ovrtx_wait_op itself is not deprecated in 0.4
// and its error-retrieval semantics apply identically to ops enqueued via
// ovrtx_step_with_stage / ovrtx_update_from_stage; the snippet story is the
// same either way, only the trigger changes.

#include <gtest/gtest.h>
#include "helpers.h"

#include <cstring>
#include <string>

class ErrorHandlingTest : public ::testing::Test {
protected:
    static void SetUpTestSuite() {
        TestConfig tc("ErrorHandlingTest");
        ovrtx_result_t result = ovrtx_create_renderer(&tc.config, &renderer_);
        ASSERT_API_SUCCESS(result.status);
    }

    static void TearDownTestSuite() {
        if (renderer_) {
            ovrtx_destroy_renderer(renderer_);
            renderer_ = nullptr;
        }
    }

    static ovrtx_renderer_t* renderer_;
};

ovrtx_renderer_t* ErrorHandlingTest::renderer_ = nullptr;

TEST_F(ErrorHandlingTest, WaitOpErrorRetrieval) {
    // Enqueue an op that is guaranteed to fail: open_usd with a non-existent file.
    std::string bogus_path = get_docs_test_data_dir() + "/this-file-does-not-exist.usda";

    ovrtx_enqueue_result_t eq = ovrtx_open_usd_from_file(renderer_, {bogus_path.c_str(), bogus_path.size()});
    ASSERT_API_SUCCESS(eq.status);

    // [snippet:doc-wait-op-error-retrieval-c]
    // Wait for the op. The new 0.3.0 shape of ovrtx_op_wait_result_t carries:
    //   - error_op_ids[0..num_error_ops) : ids that errored since the last wait
    //   - lowest_pending_op_id           : 0 if everything is resolved
    // Both error_op_ids and the strings returned by ovrtx_get_last_op_error()
    // are thread-local and are invalidated by the next wait on this thread.
    ovrtx_op_wait_result_t wait_result{};
    ovrtx_result_t r = ovrtx_wait_op(renderer_, eq.op_index, ovrtx_timeout_infinite, &wait_result);
    ASSERT_API_SUCCESS(r.status);

    ASSERT_GT(wait_result.num_error_ops, 0u) << "expected the failing op to be reported";

    for (size_t i = 0; i < wait_result.num_error_ops; ++i) {
        ovx_string_t err = ovrtx_get_last_op_error(wait_result.error_op_ids[i]);
        // Prefer the explicit length field over the null terminator.
        ASSERT_GT(err.length, 0u);
        printf("op %llu error: %.*s\n",
               (unsigned long long)wait_result.error_op_ids[i],
               (int)err.length, err.ptr);
    }

    // Nothing is still in flight → lowest_pending_op_id is 0.
    EXPECT_EQ(wait_result.lowest_pending_op_id, 0u);
    // [/snippet:doc-wait-op-error-retrieval-c]

    // Sanity: the failed op id itself shows up in error_op_ids.
    bool found = false;
    for (size_t i = 0; i < wait_result.num_error_ops; ++i) {
        if (wait_result.error_op_ids[i] == eq.op_index) {
            found = true;
            break;
        }
    }
    EXPECT_TRUE(found) << "expected the failing op_index to appear in error_op_ids";
}

TEST_F(ErrorHandlingTest, NoReleaseErrorsStep) {
    // [snippet:doc-wait-op-no-release-errors-c]
    // In 0.3.0 the per-thread error data is transient: it lives until the next
    // ovrtx_wait_op() on the same thread, which implicitly recycles it. There is
    // no ovrtx_release_errors() call to make anymore.
    std::string bogus = get_docs_test_data_dir() + "/another-missing-file.usda";

    ovrtx_enqueue_result_t eq = ovrtx_open_usd_from_file(renderer_, {bogus.c_str(), bogus.size()});
    ASSERT_API_SUCCESS(eq.status);

    ovrtx_op_wait_result_t wr1{};
    ASSERT_API_SUCCESS(ovrtx_wait_op(renderer_, eq.op_index, ovrtx_timeout_infinite, &wr1).status);
    ASSERT_GT(wr1.num_error_ops, 0u);

    // Do another wait on the same thread — this invalidates wr1's error_op_ids.
    // No explicit release step is required or supported.
    ovrtx_enqueue_result_t eq2 = ovrtx_reset_stage(renderer_);
    ASSERT_API_SUCCESS(eq2.status);
    ovrtx_op_wait_result_t wr2{};
    ASSERT_API_SUCCESS(ovrtx_wait_op(renderer_, eq2.op_index, ovrtx_timeout_infinite, &wr2).status);
    ASSERT_NO_OP_ERRORS(wr2);
    // [/snippet:doc-wait-op-no-release-errors-c]
}
