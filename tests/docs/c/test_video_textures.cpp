// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// C counterpart to the runtime workflow in the Python video-textures example.

#include <gtest/gtest.h>
#include "helpers.h"

#include <cstdint>
#include <filesystem>

namespace
{

// The RenderProducts enable blocking video streaming, so each step waits for the decoder.
// Bound every wait so a decode failure fails the test instead of hanging the job.
constexpr uint64_t kVideoTimeoutSeconds = 300;
constexpr ovrtx_timeout_t kVideoTimeout{ kVideoTimeoutSeconds * 1'000'000'000ull };

void wait_no_errors(ovrtx_renderer_t* renderer, ovrtx_op_id_t op_id, double source_time)
{
    ovrtx_op_wait_result_t wait_result{};
    ovrtx_result_t const result = ovrtx_wait_op(renderer, op_id, kVideoTimeout, &wait_result);
    ASSERT_NE(result.status, OVRTX_API_TIMEOUT)
        << "source time " << source_time << ": operation did not complete within " << kVideoTimeoutSeconds << " s";
    ASSERT_API_SUCCESS(result.status);
    ASSERT_NO_OP_ERRORS(wait_result);
}

struct BallCenter
{
    double x;
    double y;
};

void expect_video_frame(ovrtx_renderer_t* renderer,
                        ovrtx_step_result_handle_t step_handle,
                        char const* render_var_path,
                        double source_time,
                        BallCenter expected_center)
{
    ovrtx_render_product_set_outputs_t outputs{};
    ovrtx_result_t result = ovrtx_fetch_results(renderer, step_handle, kVideoTimeout, &outputs);
    ASSERT_NE(result.status, OVRTX_API_TIMEOUT)
        << "source time " << source_time << ": no step results within " << kVideoTimeoutSeconds << " s";
    ASSERT_API_SUCCESS(result.status);

    ovrtx_render_var_output_handle_t ldr_handle = find_output(outputs, render_var_path);
    ASSERT_NE(ldr_handle, OVRTX_INVALID_RENDER_VAR_OUTPUT_HANDLE);

    ovrtx_map_output_description_t map_desc{};
    map_desc.device_type = OVRTX_MAP_DEVICE_TYPE_CPU;
    ovrtx_render_var_output_t ldr_output{};
    result = ovrtx_map_render_var_output(renderer, ldr_handle, &map_desc, kVideoTimeout, &ldr_output);
    ASSERT_NE(result.status, OVRTX_API_TIMEOUT)
        << "source time " << source_time << ": LdrColor not mapped within " << kVideoTimeoutSeconds << " s";
    ASSERT_API_SUCCESS(result.status);
    ASSERT_GT(ldr_output.num_tensors, 0u);

    DLTensor const& tensor = *ldr_output.tensors[0].dl;
    ASSERT_EQ(tensor.ndim, 3);
    ASSERT_EQ(tensor.shape[0], 360);
    ASSERT_EQ(tensor.shape[1], 640);
    ASSERT_GE(tensor.shape[2], 3);
    ASSERT_EQ(tensor.dtype.code, kDLUInt);
    ASSERT_EQ(tensor.dtype.bits, 8);
    ASSERT_EQ(tensor.dtype.lanes, 1);

    auto const* pixels = static_cast<uint8_t const*>(tensor.data) + tensor.byte_offset;
    int64_t const row_stride = tensor.strides ? tensor.strides[0] : tensor.shape[1] * tensor.shape[2];
    int64_t const pixel_stride = tensor.strides ? tensor.strides[1] : tensor.shape[2];
    size_t dark_count = 0;
    size_t white_count = 0;
    size_t orange_count = 0;
    double orange_x_sum = 0.0;
    double orange_y_sum = 0.0;
    for (int64_t y = 0; y < tensor.shape[0]; ++y)
    {
        for (int64_t x = 0; x < tensor.shape[1]; ++x)
        {
            uint8_t const* rgb = pixels + y * row_stride + x * pixel_stride;
            dark_count += rgb[0] < 64 && rgb[1] < 64 && rgb[2] < 64;
            white_count += rgb[0] > 180 && rgb[1] > 180 && rgb[2] > 180;
            bool const orange = rgb[0] > 150 && rgb[1] > 70 && rgb[1] < 200 && rgb[2] < 80;
            if (orange)
            {
                ++orange_count;
                orange_x_sum += x;
                orange_y_sum += y;
            }
        }
    }

    EXPECT_GT(dark_count, 10'000u) << "source time " << source_time;
    EXPECT_GT(white_count, 1'000u) << "source time " << source_time;
    ASSERT_GT(orange_count, 250u) << "source time " << source_time;
    double const actual_x = orange_x_sum / orange_count;
    double const actual_y = orange_y_sum / orange_count;
    EXPECT_NEAR(actual_x, expected_center.x, 8.0) << "source time " << source_time;
    EXPECT_NEAR(actual_y, expected_center.y, 8.0) << "source time " << source_time;

    ovrtx_cuda_sync_t no_sync{};
    EXPECT_API_SUCCESS(ovrtx_unmap_render_var_output(renderer, ldr_output.map_handle, no_sync).status);
    ovrtx_destroy_results(renderer, step_handle);
}

} // namespace

class VideoTexturesTest : public DocsOvstageTestBase
{
protected:
    DOCS_OVSTAGE_TEST_SUITE(VideoTexturesTest)
};

TEST_F(VideoTexturesTest, SelectAndRenderSourceTimes)
{
    std::filesystem::path scene =
        std::filesystem::path(get_docs_test_data_dir()) / "../../../examples/python/video-textures/video_textures.usda";
    scene = scene.lexically_normal();
    docs_open_usd_file(scene.string().c_str());
    if (HasFatalFailure())
        return;

    // [snippet:doc-render-video-texture-source-times-c]
    double const source_times[] = { 0.0, 1.0, 2.0, 3.0 };
    BallCenter const expected_centers[] = {
        { 320.0, 180.0 },
        { 412.7, 248.8 },
        { 496.4, 304.2 },
        { 562.6, 335.5 },
    };

    // This stage has no animation range, so video selection uses simulation time.
    ovrtx_enqueue_result_t reset = ovrtx_reset(renderer_, 0.0);
    ASSERT_API_SUCCESS(reset.status);
    wait_no_errors(renderer_, reset.op_index, 0.0);
    if (HasFatalFailure())
        return;

    double current_time = 0.0;
    for (size_t index = 0; index < 4; ++index)
    {
        ovx_string_t render_product_path = ovx_str(index == 0 ? "/Render/Camera_0" :
                                                   index == 1 ? "/Render/Camera_1" :
                                                   index == 2 ? "/Render/Camera_2" :
                                                                "/Render/Camera_3");
        ovrtx_render_product_set_t render_products{};
        render_products.render_products = &render_product_path;
        render_products.num_render_products = 1;

        ovrtx_step_result_handle_t step_results{};
        ovrtx_enqueue_result_t step = ovrtx_step_with_stage(
            renderer_, render_products, source_times[index] - current_time, /*ordinal=*/1, &step_results);
        ASSERT_API_SUCCESS(step.status);
        wait_no_errors(renderer_, step.op_index, source_times[index]);
        if (HasFatalFailure())
            return;
        current_time = source_times[index];

        std::string render_var_path(render_product_path.ptr, render_product_path.length);
        render_var_path += "/LdrColor";
        expect_video_frame(
            renderer_, step_results, render_var_path.c_str(), source_times[index], expected_centers[index]);
        if (HasFatalFailure())
            return;
    }
    // [/snippet:doc-render-video-texture-source-times-c]
}
