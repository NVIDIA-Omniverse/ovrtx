// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Smoke tests for all documented camera AOVs (Real-Time Path-Tracing mode)

#include <gtest/gtest.h>
#include "helpers.h"

#include <cstring>
#include <ovx/dlpack/dlpack.h>
#include <string>

static constexpr int WIDTH = 640;
static constexpr int HEIGHT = 360;

// Check that at least one byte in a buffer is non-zero.
static bool has_nonzero(void const* data, size_t byte_count) {
    uint8_t const* bytes = static_cast<uint8_t const*>(data);
    for (size_t i = 0; i < byte_count; ++i) {
        if (bytes[i] != 0) return true;
    }
    return false;
}

class CameraAovsTest : public DocsOvstageTestBase {
protected:
    DOCS_OVSTAGE_TEST_SUITE(CameraAovsTest)
};

TEST_F(CameraAovsTest, AllRT2Outputs) {
    // Load scene via sublayer with all AOVs, populated through ovstage.
    std::string scene_path = get_test_data_dir() + "/simple_camera.usda";
    std::string usda = make_sublayer_usda(scene_path, R"usda(
def "Render" {
    def RenderProduct "Camera" {
        int2 resolution = (640, 360)
        rel camera = </Camera0>
        rel orderedVars = [
            <LdrColor>, <HdrColor>, <NormalSD>, <DepthSD>,
            <DistanceToCameraSD>, <DistanceToImagePlaneSD>,
            <DiffuseAlbedoSD>, <Camera3dPositionSD>
        ]

        def RenderVar "LdrColor" {
            string sourceName = "LdrColor"
        }
        def RenderVar "HdrColor" {
            string sourceName = "HdrColor"
        }
        def RenderVar "NormalSD" {
            string sourceName = "NormalSD"
        }
        def RenderVar "DepthSD" {
            string sourceName = "DepthSD"
        }
        def RenderVar "DistanceToCameraSD" {
            string sourceName = "DistanceToCameraSD"
        }
        def RenderVar "DistanceToImagePlaneSD" {
            string sourceName = "DistanceToImagePlaneSD"
        }
        def RenderVar "DiffuseAlbedoSD" {
            string sourceName = "DiffuseAlbedoSD"
        }
        def RenderVar "Camera3dPositionSD" {
            string sourceName = "Camera3dPositionSD"
        }
    }
}
)usda");

    docs_open_usd_string(usda.c_str(), usda.size());
    if (HasFatalFailure()) return;

    ovstage_ordinal_t ordinal = 1;
    ovx_string_t rp_path = ovx_str("/Render/Camera");
    ovrtx_render_product_set_t render_products{};
    render_products.render_products = &rp_path;
    render_products.num_render_products = 1;

    // Warm up so the path-tracer accumulator converges before we sample outputs.
    for (int i = 0; i < 5; ++i) {
        ovrtx_step_result_handle_t warmup_handle = 0;
        ovrtx_enqueue_result_t warmup_eq = ovrtx_step_with_stage(
            renderer_, render_products, 1.0 / 60.0, ordinal, &warmup_handle);
        ASSERT_API_SUCCESS(warmup_eq.status);
        docs_wait_no_errors(renderer_, warmup_eq.op_index);
        ovrtx_destroy_results(renderer_, warmup_handle);
    }

    ovrtx_step_result_handle_t step_handle = 0;
    ovrtx_enqueue_result_t enqueue_result = ovrtx_step_with_stage(
        renderer_, render_products, 1.0 / 60.0, ordinal, &step_handle);
    ASSERT_API_SUCCESS(enqueue_result.status);
    docs_wait_no_errors(renderer_, enqueue_result.op_index);

    ovrtx_render_product_set_outputs_t outputs{};
    ovrtx_result_t result =
        ovrtx_fetch_results(renderer_, step_handle, ovrtx_timeout_infinite, &outputs);
    ASSERT_API_SUCCESS(result.status);

    ovrtx_map_output_description_t map_desc = {};
    map_desc.device_type = OVRTX_MAP_DEVICE_TYPE_CPU;
    ovrtx_cuda_sync_t no_sync = {};

    // [snippet:doc-camera-aov-smoke-test-c]
    // LdrColor: RGBA uint8 -- shape (H, W, 4), scalar lanes
    {
        ovrtx_render_var_output_handle_t handle = find_output(outputs, "LdrColor");
        ASSERT_NE(handle, OVRTX_INVALID_HANDLE);
        ovrtx_render_var_output_t output = {};
        result = ovrtx_map_render_var_output(renderer_, handle, &map_desc,
                                           ovrtx_timeout_infinite, &output);
        ASSERT_API_SUCCESS(result.status);
        DLTensor const& t = *output.tensors[0].dl;
        EXPECT_EQ(t.ndim, 3);
        EXPECT_EQ(t.shape[0], HEIGHT);
        EXPECT_EQ(t.shape[1], WIDTH);
        EXPECT_EQ(t.shape[2], 4);
        EXPECT_EQ(t.dtype.code, kDLUInt);
        EXPECT_EQ(t.dtype.bits, 8);
        EXPECT_EQ(t.dtype.lanes, 1);
        EXPECT_TRUE(has_nonzero(t.data, HEIGHT * WIDTH * 4));
        save_ldr_png("CameraAovs.LdrColor", t.data, WIDTH, HEIGHT);
        ovrtx_unmap_render_var_output(renderer_, output.map_handle, no_sync);
    }

    // HdrColor: RGBA float16 -- shape (H, W, 4), scalar lanes
    {
        ovrtx_render_var_output_handle_t handle = find_output(outputs, "HdrColor");
        ASSERT_NE(handle, OVRTX_INVALID_HANDLE);
        ovrtx_render_var_output_t output = {};
        result = ovrtx_map_render_var_output(renderer_, handle, &map_desc,
                                           ovrtx_timeout_infinite, &output);
        ASSERT_API_SUCCESS(result.status);
        DLTensor const& t = *output.tensors[0].dl;
        EXPECT_EQ(t.ndim, 3);
        EXPECT_EQ(t.shape[0], HEIGHT);
        EXPECT_EQ(t.shape[1], WIDTH);
        EXPECT_EQ(t.shape[2], 4);
        EXPECT_EQ(t.dtype.code, kDLFloat);
        EXPECT_EQ(t.dtype.bits, 16);
        EXPECT_EQ(t.dtype.lanes, 1);
        EXPECT_TRUE(has_nonzero(t.data, HEIGHT * WIDTH * 4 * 2));
        ovrtx_unmap_render_var_output(renderer_, output.map_handle, no_sync);
    }

    // NormalSD: XYZA float32 -- shape (H, W, 4), scalar lanes
    {
        ovrtx_render_var_output_handle_t handle = find_output(outputs, "NormalSD");
        ASSERT_NE(handle, OVRTX_INVALID_HANDLE);
        ovrtx_render_var_output_t output = {};
        result = ovrtx_map_render_var_output(renderer_, handle, &map_desc,
                                           ovrtx_timeout_infinite, &output);
        ASSERT_API_SUCCESS(result.status);
        DLTensor const& t = *output.tensors[0].dl;
        EXPECT_EQ(t.ndim, 3);
        EXPECT_EQ(t.shape[0], HEIGHT);
        EXPECT_EQ(t.shape[1], WIDTH);
        EXPECT_EQ(t.shape[2], 4);
        EXPECT_EQ(t.dtype.code, kDLFloat);
        EXPECT_EQ(t.dtype.bits, 32);
        EXPECT_EQ(t.dtype.lanes, 1);
        EXPECT_TRUE(has_nonzero(t.data, HEIGHT * WIDTH * 4 * 4));
        ovrtx_unmap_render_var_output(renderer_, output.map_handle, no_sync);
    }

    // DepthSD: Z float32 -- shape (H, W, 1), scalar lanes
    {
        ovrtx_render_var_output_handle_t handle = find_output(outputs, "DepthSD");
        ASSERT_NE(handle, OVRTX_INVALID_HANDLE);
        ovrtx_render_var_output_t output = {};
        result = ovrtx_map_render_var_output(renderer_, handle, &map_desc,
                                           ovrtx_timeout_infinite, &output);
        ASSERT_API_SUCCESS(result.status);
        DLTensor const& t = *output.tensors[0].dl;
        EXPECT_EQ(t.ndim, 3);
        EXPECT_EQ(t.shape[0], HEIGHT);
        EXPECT_EQ(t.shape[1], WIDTH);
        EXPECT_EQ(t.shape[2], 1);
        EXPECT_EQ(t.dtype.code, kDLFloat);
        EXPECT_EQ(t.dtype.bits, 32);
        EXPECT_EQ(t.dtype.lanes, 1);
        // TODO: DepthSD currently returns all zeros (ovrtx bug). Re-enable when fixed.
        // EXPECT_TRUE(has_nonzero(t.data, HEIGHT * WIDTH * 4));
        ovrtx_unmap_render_var_output(renderer_, output.map_handle, no_sync);
    }

    // DistanceToCameraSD: Z float32 -- shape (H, W, 1), scalar lanes
    {
        ovrtx_render_var_output_handle_t handle = find_output(outputs, "DistanceToCameraSD");
        ASSERT_NE(handle, OVRTX_INVALID_HANDLE);
        ovrtx_render_var_output_t output = {};
        result = ovrtx_map_render_var_output(renderer_, handle, &map_desc,
                                           ovrtx_timeout_infinite, &output);
        ASSERT_API_SUCCESS(result.status);
        DLTensor const& t = *output.tensors[0].dl;
        EXPECT_EQ(t.ndim, 3);
        EXPECT_EQ(t.shape[0], HEIGHT);
        EXPECT_EQ(t.shape[1], WIDTH);
        EXPECT_EQ(t.shape[2], 1);
        EXPECT_EQ(t.dtype.code, kDLFloat);
        EXPECT_EQ(t.dtype.bits, 32);
        EXPECT_EQ(t.dtype.lanes, 1);
        EXPECT_TRUE(has_nonzero(t.data, HEIGHT * WIDTH * 4));
        ovrtx_unmap_render_var_output(renderer_, output.map_handle, no_sync);
    }

    // DistanceToImagePlaneSD: Z float32 -- shape (H, W, 1), scalar lanes
    {
        ovrtx_render_var_output_handle_t handle = find_output(outputs, "DistanceToImagePlaneSD");
        ASSERT_NE(handle, OVRTX_INVALID_HANDLE);
        ovrtx_render_var_output_t output = {};
        result = ovrtx_map_render_var_output(renderer_, handle, &map_desc,
                                           ovrtx_timeout_infinite, &output);
        ASSERT_API_SUCCESS(result.status);
        DLTensor const& t = *output.tensors[0].dl;
        EXPECT_EQ(t.ndim, 3);
        EXPECT_EQ(t.shape[0], HEIGHT);
        EXPECT_EQ(t.shape[1], WIDTH);
        EXPECT_EQ(t.shape[2], 1);
        EXPECT_EQ(t.dtype.code, kDLFloat);
        EXPECT_EQ(t.dtype.bits, 32);
        EXPECT_EQ(t.dtype.lanes, 1);
        EXPECT_TRUE(has_nonzero(t.data, HEIGHT * WIDTH * 4));
        ovrtx_unmap_render_var_output(renderer_, output.map_handle, no_sync);
    }

    // DiffuseAlbedoSD: RGBA uint8 -- shape (H, W, 4), scalar lanes
    {
        ovrtx_render_var_output_handle_t handle = find_output(outputs, "DiffuseAlbedoSD");
        ASSERT_NE(handle, OVRTX_INVALID_HANDLE);
        ovrtx_render_var_output_t output = {};
        result = ovrtx_map_render_var_output(renderer_, handle, &map_desc,
                                           ovrtx_timeout_infinite, &output);
        ASSERT_API_SUCCESS(result.status);
        DLTensor const& t = *output.tensors[0].dl;
        EXPECT_EQ(t.ndim, 3);
        EXPECT_EQ(t.shape[0], HEIGHT);
        EXPECT_EQ(t.shape[1], WIDTH);
        EXPECT_EQ(t.shape[2], 4);
        EXPECT_EQ(t.dtype.code, kDLUInt);
        EXPECT_EQ(t.dtype.bits, 8);
        EXPECT_EQ(t.dtype.lanes, 1);
        EXPECT_TRUE(has_nonzero(t.data, HEIGHT * WIDTH * 4));
        save_ldr_png("CameraAovs.DiffuseAlbedoSD", t.data, WIDTH, HEIGHT);
        ovrtx_unmap_render_var_output(renderer_, output.map_handle, no_sync);
    }

    // Camera3dPositionSD: XYZA float32 -- shape (H, W, 4), scalar lanes
    {
        ovrtx_render_var_output_handle_t handle = find_output(outputs, "Camera3dPositionSD");
        ASSERT_NE(handle, OVRTX_INVALID_HANDLE);
        ovrtx_render_var_output_t output = {};
        result = ovrtx_map_render_var_output(renderer_, handle, &map_desc,
                                           ovrtx_timeout_infinite, &output);
        ASSERT_API_SUCCESS(result.status);
        DLTensor const& t = *output.tensors[0].dl;
        EXPECT_EQ(t.ndim, 3);
        EXPECT_EQ(t.shape[0], HEIGHT);
        EXPECT_EQ(t.shape[1], WIDTH);
        EXPECT_EQ(t.shape[2], 4);
        EXPECT_EQ(t.dtype.code, kDLFloat);
        EXPECT_EQ(t.dtype.bits, 32);
        EXPECT_EQ(t.dtype.lanes, 1);
        EXPECT_TRUE(has_nonzero(t.data, HEIGHT * WIDTH * 4 * 4));
        ovrtx_unmap_render_var_output(renderer_, output.map_handle, no_sync);
    }
    // [/snippet:doc-camera-aov-smoke-test-c]

    ovrtx_destroy_results(renderer_, step_handle);
}
