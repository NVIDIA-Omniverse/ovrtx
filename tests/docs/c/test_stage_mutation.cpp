// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Tests for additive USD references, removal, and cloning through the ovstage C
// API. Mirrors tests/docs/python/test_stage_mutation.py.

#include <gtest/gtest.h>
#include "helpers.h"

#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

namespace {

constexpr char kRootUsda[] = R"(#usda 1.0
def Xform "World" {
}
)";

constexpr char kReferenceUsda[] = R"(#usda 1.0
(
    defaultPrim = "Referenced"
)

def Xform "Referenced" {
    def Cube "KnownChild" {
    }
}
)";

} // namespace

class StageMutationTest : public DocsOvstageTestBase {
protected:
    DOCS_OVSTAGE_TEST_SUITE(StageMutationTest)

    // Populate the tiny "/World" root layer at ordinal 1. Mirrors the setup
    // block in the Python file/string-reference tests.
    void open_root() {
        docs_open_usd_string(kRootUsda, sizeof(kRootUsda) - 1);
    }
};

TEST_F(StageMutationTest, AttachedUpdateLoop) {
    docs_load_base();
    if (HasFatalFailure()) return;

    constexpr ovstage_ordinal_t ordinal = 2;
    ovx_string_t source = ovx_str("/World/Plane");
    ovx_string_t target = ovx_str("/World/PlaneClone");
    ovx_string_t render_product = ovx_str("/Render/Camera");
    ovrtx_render_product_set_t products{};
    products.render_products = &render_product;
    products.num_render_products = 1;

    // [snippet:doc-attached-update-loop-c]
    ovstage_enqueue_result_t mutation =
        ovstage_clone(stage_, source, &target, 1, ordinal);
    ASSERT_EQ(mutation.status, OVSTAGE_OK);

    ovstage_write_floor_desc_t floor{
        ordinal, OVSTAGE_SCOPE_ALL, nullptr, 0};
    ovstage_enqueue_result_t floor_op =
        ovstage_advance_write_floor(stage_, &floor);
    ASSERT_EQ(floor_op.status, OVSTAGE_OK);

    ovstage_op_wait_result_t floor_wait{};
    ovstage_api_status_t floor_status = ovstage_wait_op(
        stage_, floor_op.op_index, OVSTAGE_TIMEOUT_INFINITE, &floor_wait);
    ASSERT_EQ(floor_status, OVSTAGE_OK);
    ASSERT_EQ(floor_wait.error_op_id_count, 0u);

    ovrtx_enqueue_result_t update =
        ovrtx_update_from_stage(renderer_, ordinal);
    ASSERT_API_SUCCESS(update.status);

    ovrtx_step_result_handle_t step_results = OVRTX_INVALID_HANDLE;
    ovrtx_enqueue_result_t step = ovrtx_step_with_stage(
        renderer_, products, 1.0 / 60.0, ordinal, &step_results);
    ASSERT_API_SUCCESS(step.status);

    ovrtx_op_wait_result_t step_wait{};
    ovrtx_result_t step_wait_status = ovrtx_wait_op(
        renderer_, step.op_index, ovrtx_timeout_infinite, &step_wait);
    ASSERT_API_SUCCESS(step_wait_status.status);
    ASSERT_NO_OP_ERRORS(step_wait);

    ovrtx_destroy_results(renderer_, step_results);
    ovstage_release_op(stage_, mutation.op_index);
    ovstage_release_op(stage_, floor_op.op_index);
    // [/snippet:doc-attached-update-loop-c]
}

TEST_F(StageMutationTest, AddRemoveUsdReferenceFromFile) {
    open_root();
    if (HasFatalFailure()) return;
    std::filesystem::path reference_path = get_output_dir() / "stage-mutation-reference.usda";
    std::ofstream(reference_path) << kReferenceUsda;
    std::string reference_path_str = reference_path.string();

    // [snippet:doc-add-remove-usd-reference-c]
    ovstage_population_usd_reference_handle_t handle =
        OVSTAGE_POPULATION_INVALID_USD_REFERENCE_HANDLE;
    ovstage_population_enqueue_result_t pr = ovstage_population_add_usd_reference_from_file(
        stage_,
        {reference_path_str.c_str(), reference_path_str.size()},
        ovx_str("/World/LoadedBase"),
        &handle);
    ASSERT_EQ(pr.status, OVSTAGE_OK) << format_ovstage_population_last_error();
    docs_wait_ovstage_population_no_errors(stage_, pr.op_index);

    pr = ovstage_population_apply_usd_changes(stage_, /*ordinal=*/2);
    ASSERT_EQ(pr.status, OVSTAGE_OK) << format_ovstage_population_last_error();
    docs_wait_ovstage_population_no_errors(stage_, pr.op_index);
    docs_ovstage_advance_write_floor(stage_, 2);

    pr = ovstage_population_remove_usd_reference(stage_, handle);
    ASSERT_EQ(pr.status, OVSTAGE_OK) << format_ovstage_population_last_error();
    docs_wait_ovstage_population_no_errors(stage_, pr.op_index);

    pr = ovstage_population_apply_usd_changes(stage_, /*ordinal=*/3);
    ASSERT_EQ(pr.status, OVSTAGE_OK) << format_ovstage_population_last_error();
    docs_wait_ovstage_population_no_errors(stage_, pr.op_index);
    docs_ovstage_advance_write_floor(stage_, 3);
    // [/snippet:doc-add-remove-usd-reference-c]

    EXPECT_EQ(docs_query_prefix_count(stage_, "/World/LoadedBase"), 0u);
}

// Verify that the file-reference add actually composed prims into the runtime
// stage. Kept out of the doc snippet above so the rendered example stays focused
// on the add/remove cadence; this test-only check guards against a regression
// where add succeeds at the API level but silently composes nothing (leaving
// a trivial add→remove no-op, which the post-remove count==0 alone can't
// distinguish from a working roundtrip).
TEST_F(StageMutationTest, AddUsdReferenceFromFileLoadsPrims) {
    open_root();
    if (HasFatalFailure()) return;
    std::filesystem::path reference_path = get_output_dir() / "stage-mutation-reference.usda";
    std::ofstream(reference_path) << kReferenceUsda;
    std::string reference_path_str = reference_path.string();

    ovstage_population_usd_reference_handle_t handle =
        OVSTAGE_POPULATION_INVALID_USD_REFERENCE_HANDLE;
    ovstage_population_enqueue_result_t pr = ovstage_population_add_usd_reference_from_file(
        stage_,
        {reference_path_str.c_str(), reference_path_str.size()},
        ovx_str("/World/LoadedBase"),
        &handle);
    ASSERT_EQ(pr.status, OVSTAGE_OK) << format_ovstage_population_last_error();
    docs_wait_ovstage_population_no_errors(stage_, pr.op_index);

    pr = ovstage_population_apply_usd_changes(stage_, /*ordinal=*/2);
    ASSERT_EQ(pr.status, OVSTAGE_OK) << format_ovstage_population_last_error();
    docs_wait_ovstage_population_no_errors(stage_, pr.op_index);
    docs_ovstage_advance_write_floor(stage_, 2);

    // Referenced.KnownChild composes under the target prim.
    EXPECT_GE(docs_query_prefix_count(stage_, "/World/LoadedBase"), 1u);
    EXPECT_EQ(docs_query_prefix_count(stage_, "/World/LoadedBase/KnownChild"), 1u);
}

TEST_F(StageMutationTest, AddRemoveUsdReferenceFromString) {
    open_root();
    if (HasFatalFailure()) return;

    // [snippet:doc-add-usd-reference-from-string-c]
    ovstage_population_usd_reference_handle_t handle =
        OVSTAGE_POPULATION_INVALID_USD_REFERENCE_HANDLE;
    ovstage_population_enqueue_result_t pr = ovstage_population_add_usd_reference_from_string(
        stage_,
        {kReferenceUsda, sizeof(kReferenceUsda) - 1},
        ovx_str("/World/Injected"),
        &handle);
    ASSERT_EQ(pr.status, OVSTAGE_OK) << format_ovstage_population_last_error();
    docs_wait_ovstage_population_no_errors(stage_, pr.op_index);

    pr = ovstage_population_apply_usd_changes(stage_, /*ordinal=*/2);
    ASSERT_EQ(pr.status, OVSTAGE_OK) << format_ovstage_population_last_error();
    docs_wait_ovstage_population_no_errors(stage_, pr.op_index);
    docs_ovstage_advance_write_floor(stage_, 2);

    pr = ovstage_population_remove_usd_reference(stage_, handle);
    ASSERT_EQ(pr.status, OVSTAGE_OK) << format_ovstage_population_last_error();
    docs_wait_ovstage_population_no_errors(stage_, pr.op_index);

    pr = ovstage_population_apply_usd_changes(stage_, /*ordinal=*/3);
    ASSERT_EQ(pr.status, OVSTAGE_OK) << format_ovstage_population_last_error();
    docs_wait_ovstage_population_no_errors(stage_, pr.op_index);
    docs_ovstage_advance_write_floor(stage_, 3);
    // [/snippet:doc-add-usd-reference-from-string-c]

    EXPECT_EQ(docs_query_prefix_count(stage_, "/World/Injected"), 0u);
}

// Companion to AddRemoveUsdReferenceFromString — see the file variant above for
// why this is a separate test (keeps the snippet focused).
TEST_F(StageMutationTest, AddUsdReferenceFromStringLoadsPrims) {
    open_root();
    if (HasFatalFailure()) return;

    ovstage_population_usd_reference_handle_t handle =
        OVSTAGE_POPULATION_INVALID_USD_REFERENCE_HANDLE;
    ovstage_population_enqueue_result_t pr = ovstage_population_add_usd_reference_from_string(
        stage_,
        {kReferenceUsda, sizeof(kReferenceUsda) - 1},
        ovx_str("/World/Injected"),
        &handle);
    ASSERT_EQ(pr.status, OVSTAGE_OK) << format_ovstage_population_last_error();
    docs_wait_ovstage_population_no_errors(stage_, pr.op_index);

    pr = ovstage_population_apply_usd_changes(stage_, /*ordinal=*/2);
    ASSERT_EQ(pr.status, OVSTAGE_OK) << format_ovstage_population_last_error();
    docs_wait_ovstage_population_no_errors(stage_, pr.op_index);
    docs_ovstage_advance_write_floor(stage_, 2);

    EXPECT_GE(docs_query_prefix_count(stage_, "/World/Injected"), 1u);
    EXPECT_EQ(docs_query_prefix_count(stage_, "/World/Injected/KnownChild"), 1u);
}

TEST_F(StageMutationTest, CloneUsd) {
    docs_load_base();
    if (HasFatalFailure()) return;
    std::vector<uint8_t> source_points;
    docs_read_attribute(stage_, "/World/Plane", "points", /*ordinal=*/1, &source_points);
    if (HasFatalFailure()) return;

    // [snippet:doc-clone-usd-c]
    ovx_string_t source = ovx_str("/World/Plane");
    ovx_string_t targets[] = {
        ovx_str("/World/PlaneCloneA"),
        ovx_str("/World/PlaneCloneB"),
    };

    ovstage_enqueue_result_t eq = ovstage_clone(stage_, source, targets, 2, /*ordinal=*/2);
    ASSERT_EQ(eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, eq.op_index);
    docs_ovstage_advance_write_floor(stage_, 2);
    // [/snippet:doc-clone-usd-c]

    EXPECT_EQ(docs_query_prefix_count(stage_, "/World/PlaneCloneA"), 1u);
    EXPECT_EQ(docs_query_prefix_count(stage_, "/World/PlaneCloneB"), 1u);

    std::vector<uint8_t> clone_points;
    docs_read_attribute(stage_, "/World/PlaneCloneA", "points", /*ordinal=*/2, &clone_points);
    EXPECT_EQ(clone_points, source_points);
}

TEST_F(StageMutationTest, CloneUsdAsync) {
    docs_load_base();
    if (HasFatalFailure()) return;

    // [snippet:doc-clone-usd-async-c]
    ovx_string_t source = ovx_str("/World/Plane");
    ovx_string_t targets[] = {ovx_str("/World/PlaneCloneAsync")};

    ovstage_enqueue_result_t eq = ovstage_clone(stage_, source, targets, 1, /*ordinal=*/2);
    ASSERT_EQ(eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, eq.op_index);
    docs_ovstage_advance_write_floor(stage_, 2);
    // [/snippet:doc-clone-usd-async-c]

    EXPECT_EQ(docs_query_prefix_count(stage_, "/World/PlaneCloneAsync"), 1u);
}
