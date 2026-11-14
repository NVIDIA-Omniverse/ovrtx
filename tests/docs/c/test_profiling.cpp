// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary

#include <gtest/gtest.h>
#include "helpers.h"

#include <cstdio>
#include <chrono>

/** Keep capture and batch cleanup ahead of renderer teardown even after a failed assertion. */
class ProfilingTest : public DocsOvstageTestBase
{
protected:
    /** Attach a stage so the test uses the public attached-renderer lifecycle. */
    void SetUp() override
    {
        renderer_ = docs_create_suite_renderer("ProfilingTest");
        ASSERT_NE(renderer_, nullptr);
        docs_attach_stage(renderer_);
    }

    /** Release the batch and stop capture while the backend still exists. */
    void TearDown() override
    {
        if (renderer_)
        {
            EXPECT_EQ(ovrtx_release_performance_data_update(&data).status, OVRTX_API_SUCCESS);
            EXPECT_EQ(ovrtx_stop_profiling().status, OVRTX_API_SUCCESS);
            ovrtx_renderer_t* renderer = renderer_;
            docs_detach_stage();
            docs_destroy_suite_renderer(&renderer);
        }
    }

    ovrtx_performance_data_update_t data{};
};

/** Prove retained reads exclude old values and restart discards the previous session. */
TEST_F(ProfilingTest, CaptureAndIncrementalUpdates)
{
    for (int session = 0; session < 2; ++session)
    {
        ovrtx_result_t result = ovrtx_start_profiling(NULL); // Live capture without files.
        ASSERT_EQ(result.status, OVRTX_API_SUCCESS);
        EXPECT_EQ(ovrtx_start_profiling(NULL).status, OVRTX_API_ERROR);
        for (int sampleIndex = 0; sampleIndex < 2; ++sampleIndex)
        {
            const double expected = 101.0 + session * 10 + sampleIndex;
            ovrtx_add_performance_metric_value(OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_FPS, expected);
            // [snippet:doc-profiling-read-c]
            // data is zero-initialized before first use. Reuse it on later reads.
            result = ovrtx_get_performance_data_update(&data);
            if (result.status == OVRTX_API_SUCCESS)
            {
                for (size_t i = 0; i < data.metric_count; ++i)
                {
                    const ovrtx_performance_metric_t* metric = &data.metrics[i];
                    for (size_t j = 0; j < metric->value_count; ++j)
                    {
                        printf("%.*s: %g %.*s\n", (int)metric->name.length, metric->name.ptr,
                               metric->values[j].value, (int)metric->units.length, metric->units.ptr);
                    }
                }
            }
            // [/snippet:doc-profiling-read-c]
            ASSERT_EQ(result.status, OVRTX_API_SUCCESS);
            bool found = false;
            for (size_t i = 0; i < data.metric_count; ++i)
            {
                const ovrtx_performance_metric_t& metric = data.metrics[i];
                for (size_t j = 0; j < metric.value_count; ++j)
                {
                    EXPECT_GT(metric.values[j].timestamp_ns, 0u);
                }
                if (metric.uid == OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_FPS)
                {
                    found = true;
                    ASSERT_EQ(metric.value_count, 1u);
                    EXPECT_DOUBLE_EQ(metric.values[0].value, expected);
                }
            }
            EXPECT_TRUE(found);
        }
        ovrtx_add_performance_metric_value(OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_FPS, 103.0 + session * 10);
        // [snippet:doc-profiling-replay-c]
        // Separate ownership preserves the incremental reader's progress.
        ovrtx_performance_data_update_t history = {};
        result = ovrtx_get_performance_data_update(&history);
        if (result.status == OVRTX_API_SUCCESS)
        {
            printf("History contains %zu metric descriptors\n", history.metric_count);
            // [omit]
            bool found = false;
            for (size_t i = 0; i < history.metric_count; ++i)
            {
                const ovrtx_performance_metric_t& metric = history.metrics[i];
                if (metric.uid == OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_FPS)
                {
                    found = true;
                    EXPECT_EQ(metric.value_count, 3u);
                    if (metric.value_count == 3)
                    {
                        EXPECT_DOUBLE_EQ(metric.values[0].value, 101.0 + session * 10);
                        EXPECT_DOUBLE_EQ(metric.values[1].value, 102.0 + session * 10);
                        EXPECT_DOUBLE_EQ(metric.values[2].value, 103.0 + session * 10);
                    }
                }
            }
            EXPECT_TRUE(found);
            // [/omit]
        }
        const ovrtx_result_t history_released = ovrtx_release_performance_data_update(&history);
        // [omit]
        ASSERT_EQ(result.status, OVRTX_API_SUCCESS);
        ASSERT_EQ(history_released.status, OVRTX_API_SUCCESS);
        // [/omit]

        // Resume the original reader after inspecting history.
        result = ovrtx_get_performance_data_update(&data);
        if (result.status == OVRTX_API_SUCCESS)
        {
            // Process data.metrics before the next read reuses this container.
        }
        // [/snippet:doc-profiling-replay-c]
        ASSERT_EQ(result.status, OVRTX_API_SUCCESS);
        bool foundIncremental = false;
        for (size_t i = 0; i < data.metric_count; ++i)
            if (data.metrics[i].uid == OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_FPS)
            {
                foundIncremental = true;
                ASSERT_EQ(data.metrics[i].value_count, 1u);
                EXPECT_DOUBLE_EQ(data.metrics[i].values[0].value, 103.0 + session * 10);
            }

        EXPECT_TRUE(foundIncremental);

        // [snippet:doc-profiling-json-c]
        result = ovrtx_get_performance_data_update_as_json(&data);
        if (result.status == OVRTX_API_SUCCESS)
        {
            // Consume the UTF-8 view before updating or releasing data.
            fwrite(data.json.ptr, 1, data.json.length, stdout);
        }
        // [/snippet:doc-profiling-json-c]
        ASSERT_EQ(result.status, OVRTX_API_SUCCESS);
        EXPECT_NE(data.json.ptr, nullptr);
        EXPECT_GT(data.json.length, 0u);

        if (session == 0)
        {
            ASSERT_EQ(ovrtx_stop_profiling().status, OVRTX_API_SUCCESS);
            continue; // Retain data to verify automatic progress reset in the next session.
        }
        // [snippet:doc-profiling-stop-c]
        // Release borrowed strings/arrays and flush capture before renderer teardown.
        ovrtx_result_t release_result = ovrtx_release_performance_data_update(&data);
        ovrtx_result_t stop_result = ovrtx_stop_profiling();
        // [/snippet:doc-profiling-stop-c]
        EXPECT_EQ(release_result.status, OVRTX_API_SUCCESS);
        EXPECT_EQ(stop_result.status, OVRTX_API_SUCCESS);
        EXPECT_EQ(data.handle, nullptr);
        EXPECT_EQ(data.metric_count, 0u);
        EXPECT_EQ(ovrtx_stop_profiling().status, OVRTX_API_SUCCESS);
    }
}

/** Exercise the file-capture configuration shown in the guide and verify flush creates all CSVs. */
TEST_F(ProfilingTest, SaveCapture)
{
    const std::string output_path = get_output_dir().string();
    const std::string file_name = "profiling-doc-" + std::to_string(
        std::chrono::steady_clock::now().time_since_epoch().count());
    ovrtx_result_t result{};
    // [snippet:doc-profiling-file-c]
    // output_path names an existing writable directory; file_name has no extension.
    ovrtx_profiling_config_t config = {};
    config.output_path = {output_path.data(), output_path.size()};
    config.file_name = {file_name.data(), file_name.size()};
    result = ovrtx_start_profiling(&config);
    // [/snippet:doc-profiling-file-c]
    ASSERT_EQ(result.status, OVRTX_API_SUCCESS);
    ovrtx_add_performance_metric_value(OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_FPS, 123.0);
    ASSERT_EQ(ovrtx_stop_profiling().status, OVRTX_API_SUCCESS);
    for (const char* suffix : {"info", "data", "summary"})
    {
        const std::filesystem::path path = std::filesystem::path(output_path) /
            (file_name + ".rpm_" + suffix + ".csv");
        ASSERT_TRUE(std::filesystem::exists(path)) << path;
        EXPECT_GT(std::filesystem::file_size(path), 0u);
    }
}

/** Exercise rendering and timed batch reads together, using retained batch progress. */
TEST_F(ProfilingTest, RenderLoop)
{
    docs_load_base();
    if (HasFatalFailure())
        return;
    const ovrtx_enqueue_result_t update = ovrtx_update_from_stage(renderer_, 1);
    ASSERT_EQ(update.status, OVRTX_API_SUCCESS);
    docs_wait_no_errors(renderer_, update.op_index);
    if (HasFatalFailure())
        return;
    ovrtx_renderer_t* renderer = renderer_;
    const ovstage_ordinal_t ordinal = 1;
    std::vector<uint64_t> collectionTimes;
    uint64_t previous = 0;
    size_t rtxSamples = 0;
    // [snippet:doc-profiling-render-loop-c]
    ovrtx_result_t result{};
    // renderer has an attached, updated stage committed at ordinal.
    const ovx_string_t path = {"/Render/Camera", sizeof("/Render/Camera") - 1};
    const ovrtx_render_product_set_t products = {&path, 1};
    ovrtx_performance_data_update_t batch = {};
    std::chrono::steady_clock::time_point next_read = std::chrono::steady_clock::now();

    result = ovrtx_start_profiling(NULL);
    if (result.status == OVRTX_API_SUCCESS)
    {
        for (int frame = 0; frame < 60; ++frame)
        {
            ovrtx_step_result_handle_t step = OVRTX_INVALID_STEP_RESULT_HANDLE;
            const ovrtx_enqueue_result_t queued =
                ovrtx_step_with_stage(renderer, products, 1.0 / 60, ordinal, &step);
            result.status = queued.status;
            if (result.status != OVRTX_API_SUCCESS)
                break;

            ovrtx_op_wait_result_t waited = {};
            result = ovrtx_wait_op(renderer, queued.op_index, ovrtx_timeout_infinite, &waited);
            const ovrtx_result_t destroyed = ovrtx_destroy_results(renderer, step);
            if (result.status != OVRTX_API_SUCCESS || waited.num_error_ops != 0 ||
                destroyed.status != OVRTX_API_SUCCESS)
            {
                result.status = OVRTX_API_ERROR;
                break;
            }

            // Copy at most twice per second, plus once after the last frame.
            const std::chrono::steady_clock::time_point now = std::chrono::steady_clock::now();
            if (now >= next_read || frame == 59)
            {
                result = ovrtx_get_performance_data_update(&batch);
                if (result.status != OVRTX_API_SUCCESS)
                    break;
                next_read = now + std::chrono::milliseconds(500);

                // Consume borrowed values before the next read replaces this batch.
                for (size_t i = 0; i < batch.metric_count; ++i)
                {
                    const ovrtx_performance_metric_t* metric = &batch.metrics[i];
                    for (size_t j = 0; j < metric->value_count; ++j)
                        printf("%.*s: %g %.*s\n", (int)metric->name.length, metric->name.ptr,
                               metric->values[j].value, (int)metric->units.length, metric->units.ptr);
                }
                // [omit]
                collectionTimes.push_back(batch.collection_time_ns);
                for (size_t i = 0; i < batch.metric_count; ++i)
                {
                    const ovrtx_performance_metric_t& metric = batch.metrics[i];
                    for (size_t j = 0; j < metric.value_count; ++j)
                    {
                        EXPECT_GT(metric.values[j].timestamp_ns, 0u);
                        EXPECT_GE(metric.values[j].value, 0.0);
                    }
                    if (std::string_view(metric.name.ptr, metric.name.length).find("RTX Rendering") == 0)
                        rtxSamples += metric.value_count;
                }
                EXPECT_GE(batch.collection_time_ns, previous);
                previous = batch.collection_time_ns;
                // [/omit]
            }
        }

        // Both cleanup calls run even after a failed step or read.
        const ovrtx_result_t released = ovrtx_release_performance_data_update(&batch);
        const ovrtx_result_t stopped = ovrtx_stop_profiling();
        if (result.status == OVRTX_API_SUCCESS)
            result = released.status != OVRTX_API_SUCCESS ? released : stopped;
    }
    // Inspect result.status here, before destroying the renderer.
    // [/snippet:doc-profiling-render-loop-c]
    EXPECT_EQ(result.status, OVRTX_API_SUCCESS);
    EXPECT_GE(collectionTimes.size(), 2u);
    EXPECT_GT(rtxSamples, 0u);
    EXPECT_EQ(batch.handle, nullptr);
}
