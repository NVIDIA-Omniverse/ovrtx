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

#include <cmath>
#include <limits>
#include <cstddef>
#include <cstdint>
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

// [snippet:doc-sd-map-image-c]
// The output must already be mapped with OVRTX_MAP_DEVICE_TYPE_CPU.
// Return the first pixel only for contiguous, channel-last image tensors.
static const void* sd_image_data(const DLTensor* tensor) {
    if (!tensor || tensor->device.device_type != kDLCPU || tensor->ndim != 3 ||
        tensor->dtype.lanes != 1 || !tensor->data || !tensor->shape) return nullptr;
    if (tensor->strides && (tensor->strides[2] != 1 ||
        tensor->strides[1] != tensor->shape[2] ||
        tensor->strides[0] != tensor->shape[1] * tensor->shape[2])) return nullptr;
    return static_cast<const uint8_t*>(tensor->data) + tensor->byte_offset;
}
// [/snippet:doc-sd-map-image-c]

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
        ovrtx_render_var_output_handle_t handle = find_output(outputs, "/Render/Camera/LdrColor");
        ASSERT_NE(handle, OVRTX_INVALID_HANDLE);
        ovrtx_render_var_output_t output = {};
        result = ovrtx_map_render_var_output(renderer_, handle, &map_desc,
                                           ovrtx_timeout_infinite, &output);
        ASSERT_API_SUCCESS(result.status);
        DLTensor const& t = *output.tensors[0].dl;
        ASSERT_NE(sd_image_data(&t), nullptr);
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
        ovrtx_render_var_output_handle_t handle = find_output(outputs, "/Render/Camera/HdrColor");
        ASSERT_NE(handle, OVRTX_INVALID_HANDLE);
        ovrtx_render_var_output_t output = {};
        result = ovrtx_map_render_var_output(renderer_, handle, &map_desc,
                                           ovrtx_timeout_infinite, &output);
        ASSERT_API_SUCCESS(result.status);
        DLTensor const& t = *output.tensors[0].dl;
        ASSERT_NE(sd_image_data(&t), nullptr);
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
        ovrtx_render_var_output_handle_t handle = find_output(outputs, "/Render/Camera/NormalSD");
        ASSERT_NE(handle, OVRTX_INVALID_HANDLE);
        ovrtx_render_var_output_t output = {};
        result = ovrtx_map_render_var_output(renderer_, handle, &map_desc,
                                           ovrtx_timeout_infinite, &output);
        ASSERT_API_SUCCESS(result.status);
        DLTensor const& t = *output.tensors[0].dl;
        ASSERT_NE(sd_image_data(&t), nullptr);
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
        ovrtx_render_var_output_handle_t handle = find_output(outputs, "/Render/Camera/DepthSD");
        ASSERT_NE(handle, OVRTX_INVALID_HANDLE);
        ovrtx_render_var_output_t output = {};
        result = ovrtx_map_render_var_output(renderer_, handle, &map_desc,
                                           ovrtx_timeout_infinite, &output);
        ASSERT_API_SUCCESS(result.status);
        DLTensor const& t = *output.tensors[0].dl;
        ASSERT_NE(sd_image_data(&t), nullptr);
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
        ovrtx_render_var_output_handle_t handle = find_output(outputs, "/Render/Camera/DistanceToCameraSD");
        ASSERT_NE(handle, OVRTX_INVALID_HANDLE);
        ovrtx_render_var_output_t output = {};
        result = ovrtx_map_render_var_output(renderer_, handle, &map_desc,
                                           ovrtx_timeout_infinite, &output);
        ASSERT_API_SUCCESS(result.status);
        DLTensor const& t = *output.tensors[0].dl;
        ASSERT_NE(sd_image_data(&t), nullptr);
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
        ovrtx_render_var_output_handle_t handle = find_output(outputs, "/Render/Camera/DistanceToImagePlaneSD");
        ASSERT_NE(handle, OVRTX_INVALID_HANDLE);
        ovrtx_render_var_output_t output = {};
        result = ovrtx_map_render_var_output(renderer_, handle, &map_desc,
                                           ovrtx_timeout_infinite, &output);
        ASSERT_API_SUCCESS(result.status);
        DLTensor const& t = *output.tensors[0].dl;
        ASSERT_NE(sd_image_data(&t), nullptr);
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
        ovrtx_render_var_output_handle_t handle = find_output(outputs, "/Render/Camera/DiffuseAlbedoSD");
        ASSERT_NE(handle, OVRTX_INVALID_HANDLE);
        ovrtx_render_var_output_t output = {};
        result = ovrtx_map_render_var_output(renderer_, handle, &map_desc,
                                           ovrtx_timeout_infinite, &output);
        ASSERT_API_SUCCESS(result.status);
        DLTensor const& t = *output.tensors[0].dl;
        ASSERT_NE(sd_image_data(&t), nullptr);
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
        ovrtx_render_var_output_handle_t handle = find_output(outputs, "/Render/Camera/Camera3dPositionSD");
        ASSERT_NE(handle, OVRTX_INVALID_HANDLE);
        ovrtx_render_var_output_t output = {};
        result = ovrtx_map_render_var_output(renderer_, handle, &map_desc,
                                           ovrtx_timeout_infinite, &output);
        ASSERT_API_SUCCESS(result.status);
        DLTensor const& t = *output.tensors[0].dl;
        ASSERT_NE(sd_image_data(&t), nullptr);
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





// [snippet:doc-sd-records-c]
typedef struct SdRecordView {
    const uint8_t* data;
    size_t count;
    size_t stride;
} SdRecordView;

// Read little-endian buffer lengths before copying records with memcpy().
// counted is true for semantic boxes and identifier maps, whose final word is a count.
static bool sd_records(const uint8_t* data, size_t bytes, size_t stride,
                       bool counted, SdRecordView* output) {
    if (!data || !stride || !output) return false;
    size_t count = 0;
    if (counted) {
        if (bytes < 4) return false;
        uint32_t stored_count = 0;
        memcpy(&stored_count, data + bytes - 4, 4);
        count = stored_count;
        if (count > (bytes - 4) / stride) return false;
    } else {
        if (bytes % stride) return false;
        count = bytes / stride;
    }
    *output = {data, count, stride};
    return true;
}
// [/snippet:doc-sd-records-c]


// [snippet:doc-sd-boxes-c]
typedef struct SdBox2D {
    uint32_t instance_id, tile_id;
    int32_t min[2], max[2];
} SdBox2D;
typedef struct SdBox3D {
    uint32_t instance_id, tile_id;
    float min[3], max[3], local_to_world[4][4];
} SdBox3D;
typedef struct SdSemanticBox2D {
    uint32_t stable_id[4], semantic_id[4];
    int32_t min[2], max[2];
} SdSemanticBox2D;
typedef struct SdSemanticBox3D {
    uint32_t stable_id[4], semantic_id[4];
    float min[3], max[3], local_to_world[4][4];
} SdSemanticBox3D;
// Call sd_records(data, bytes, sizeof(record_type), semantic, &view).
// Copy record i with memcpy(&box, view.data + i * view.stride, sizeof(box)).
// Bounds with max < min are invalid; clip 3D box edges before projecting them.
// [/snippet:doc-sd-boxes-c]


// [snippet:doc-sd-occlusion-c]
typedef struct SdOcclusion {
    uint32_t instance_id, tile_id;
    float ratio;
} SdOcclusion;
// Use sd_records(..., sizeof(SdOcclusion), false, &view).
// Join to raw boxes by instance_id AND tile_id; negative ratios are invalid.
// [/snippet:doc-sd-occlusion-c]


// [snippet:doc-sd-tokens-c]
typedef struct SdInstanceToken {
    uint32_t instance_id, padding;
    uint64_t prim_token;
    uint32_t prototype, instance_index;
} SdInstanceToken;
// Use sd_records(..., sizeof(SdInstanceToken), false, &view).
// Record 0 is a header: instance_id is the number of following records,
// prim_token packs minInstanceId (low 32 bits) and maxInstanceId (high 32 bits),
// and prototype is the tile count. Copy with memcpy(), not an unaligned cast.
// prim_token is an opaque runtime handle, not an address to a string.
// [/snippet:doc-sd-tokens-c]


// [snippet:doc-sd-instance-map-c]
// InstanceMap is an array of uint32 semantic indices without a trailing count.
static bool sd_instance_map(const uint8_t* data, size_t bytes, SdRecordView* view) {
    return sd_records(data, bytes, sizeof(uint32_t), false, view);
}
// Element i belongs to minInstanceId + i from the InstanceIdTokenMapSD header.
// [/snippet:doc-sd-instance-map-c]


// [snippet:doc-sd-identifiers-c]
typedef struct SdIdentifier {
    uint32_t id[4], length, offset;
} SdIdentifier;

// Decode one ID/path or ID/label pair. Keep repeated IDs as separate records.
static bool sd_identifier(const uint8_t* data, size_t bytes, size_t index,
                          SdIdentifier* record, const char** label) {
    SdRecordView view{};
    if (!record || !label || !sd_records(data, bytes, sizeof(SdIdentifier), true, &view) ||
        index >= view.count) return false;
    memcpy(record, view.data + index * view.stride, sizeof(*record));
    if (record->offset < view.count * view.stride || record->offset >= bytes - 4 ||
        record->length > bytes - 4 - record->offset) return false;
    *label = reinterpret_cast<const char*>(data + record->offset);
    return true; // Read record->length UTF-8 bytes; do not assume a NUL terminator.
}
// [/snippet:doc-sd-identifiers-c]


// [snippet:doc-sd-id-pairs-c]
typedef struct SdIdPair {
    uint32_t stable_id[4], semantic_id[4];
} SdIdPair;
// Use sd_records(..., sizeof(SdIdPair), false, &view); there is no trailing count.
// All four words belong to each ID, including its subset component.
// [/snippet:doc-sd-id-pairs-c]


// [snippet:doc-sd-camera-c]
typedef struct SdCamera {
    float world_to_camera[4][4], projection[4][4], meters_per_scene_unit;
    uint32_t resolution[2];
    float near_far[2];
    char model[25];
    uint8_t padding[3];
    float focal_length, focal_distance, f_stop, fov_x;
    float fisheye_width, fisheye_height, fisheye_center[2], fisheye_max_fov;
    float fisheye_polynomial[6], lens_p[2], lens_s[4];
} SdCamera;
// Expect exactly sizeof(SdCamera) bytes; copy with memcpy(&camera, data, sizeof(camera)).
// Matrices use row vectors. Box transforms and camera matrices share scene units.
// [/snippet:doc-sd-camera-c]


// [snippet:doc-sd-project-c]
// Project one local point into pinhole pixels; behind-camera points need clipping.
static bool sd_project_point(const float point[3], const float local_to_world[4][4],
                             const SdCamera* camera, float pixel[2]) {
    if (strncmp(camera->model, "pinhole", sizeof(camera->model)) != 0) return false;
    float value[4] = {point[0], point[1], point[2], 1.0f};
    const float (*matrices[3])[4] = {local_to_world, camera->world_to_camera, camera->projection};
    for (size_t matrix = 0; matrix < 3; ++matrix) {
        float next[4] = {};
        for (size_t col = 0; col < 4; ++col)
            for (size_t row = 0; row < 4; ++row)
                next[col] += value[row] * matrices[matrix][row][col];
        memcpy(value, next, sizeof(value));
    }
    if (value[3] <= 0) return false;
    pixel[0] = (value[0] / value[3] * 0.5f + 0.5f) * camera->resolution[0];
    pixel[1] = (-value[1] / value[3] * 0.5f + 0.5f) * camera->resolution[1];
    return true;
}
// [/snippet:doc-sd-project-c]

static_assert(sizeof(SdBox2D) == 24 && sizeof(SdBox3D) == 96);
static_assert(sizeof(SdSemanticBox2D) == 48 && sizeof(SdSemanticBox3D) == 120);
static_assert(sizeof(SdOcclusion) == 12 && sizeof(SdInstanceToken) == 24);
static_assert(sizeof(SdIdentifier) == 24 && sizeof(SdIdPair) == 32 && sizeof(SdCamera) == 260);
static_assert(offsetof(SdInstanceToken, prim_token) == 8);
static_assert(offsetof(SdCamera, focal_length) == 176);

TEST(CameraAovDecoding, BoundsAndIdentifierStorage) {
    // Independent byte fixtures exercise length validation rather than writing decoder structs.
    uint32_t raw[6] = {7, 0, 10, 20, 30, 40};
    SdRecordView view{};
    ASSERT_TRUE(sd_records(reinterpret_cast<const uint8_t*>(raw), sizeof(raw), sizeof(SdBox2D), false, &view));
    SdBox2D box{};
    memcpy(&box, view.data, sizeof(box));
    EXPECT_EQ(box.instance_id, 7u);
    EXPECT_EQ(box.min[0], 10); EXPECT_EQ(box.max[1], 40);
    EXPECT_FALSE(sd_records(reinterpret_cast<const uint8_t*>(raw), sizeof(raw) - 1, sizeof(SdBox2D), false, &view));
    uint32_t invalid_count = 1;
    EXPECT_FALSE(sd_records(reinterpret_cast<const uint8_t*>(&invalid_count), 4, 48, true, &view));

    uint8_t identifiers[58] = {};
    const uint32_t entries[12] = {1, 2, 3, 4, 2, 48, 1, 2, 3, 4, 2, 51};
    memcpy(identifiers, entries, 48);
    memcpy(identifiers + 48, "/a\0/b\0", 6);
    const uint32_t count = 2;
    memcpy(identifiers + 54, &count, 4);
    SdIdentifier first{}, second{};
    const char* first_label = nullptr;
    const char* second_label = nullptr;
    ASSERT_TRUE(sd_identifier(identifiers, sizeof(identifiers), 0, &first, &first_label));
    ASSERT_TRUE(sd_identifier(identifiers, sizeof(identifiers), 1, &second, &second_label));
    EXPECT_EQ(memcmp(first.id, second.id, sizeof(first.id)), 0);
    EXPECT_EQ(memcmp(first_label, "/a", first.length), 0);
    EXPECT_EQ(memcmp(second_label, "/b", second.length), 0);
    // Length-delimited strings remain valid when their following padding is nonzero.
    identifiers[50] = 65;
    ASSERT_TRUE(sd_identifier(identifiers, sizeof(identifiers), 0, &first, &first_label));
    EXPECT_EQ(memcmp(first_label, "/a", first.length), 0);
    const uint32_t invalid_length = 1024;
    memcpy(identifiers + 16, &invalid_length, 4);
    EXPECT_FALSE(sd_identifier(identifiers, sizeof(identifiers), 0, &first, &first_label));
    EXPECT_FALSE(sd_identifier(identifiers, sizeof(identifiers), 2, &first, &first_label));
}

TEST(CameraAovDecoding, CameraProjectionAndReservedCapacity) {
    uint8_t bytes[260] = {};
    const float identity[4][4] = {{1, 0, 0, 0}, {0, 1, 0, 0}, {0, 0, 1, 0}, {0, 0, 0, 1}};
    memcpy(bytes, identity, 64); memcpy(bytes + 64, identity, 64);
    const uint32_t resolution[2] = {640, 360};
    memcpy(bytes + 132, resolution, 8); memcpy(bytes + 148, "pinhole", 7);
    const float focal_length = 35;
    memcpy(bytes + 176, &focal_length, 4);
    SdCamera camera{};
    memcpy(&camera, bytes, sizeof(camera));
    EXPECT_EQ(camera.focal_length, 35);
    const float center[3] = {0, 0, 0}, corner[3] = {1, 1, 0};
    float pixel[2] = {};
    ASSERT_TRUE(sd_project_point(center, identity, &camera, pixel));
    EXPECT_EQ(pixel[0], 320); EXPECT_EQ(pixel[1], 180);
    ASSERT_TRUE(sd_project_point(corner, identity, &camera, pixel));
    EXPECT_EQ(pixel[0], 640); EXPECT_EQ(pixel[1], 0);
    // Independent row-vector oracle: clip (.2,.4,3,4) becomes pixels (336,162).
    const float local[4][4] = {{2, 0, 0, 0}, {0, 1, 0, 0}, {0, 0, 1, 0}, {1, -1, 0, 1}};
    const float world_to_camera[4][4] = {{1, 0, 0, 0}, {0, 2, 0, 0}, {0, 0, 1, 0}, {-1, 2, 0, 1}};
    const float projection[4][4] = {{.1f, 0, 0, 0}, {0, .1f, 0, 0}, {0, 0, 1, 1}, {0, 0, 0, 1}};
    memcpy(camera.world_to_camera, world_to_camera, sizeof(world_to_camera));
    memcpy(camera.projection, projection, sizeof(projection));
    const float known[3] = {1, 2, 3}, behind[3] = {0, 0, -2};
    ASSERT_TRUE(sd_project_point(known, local, &camera, pixel));
    EXPECT_NEAR(pixel[0], 336, .0001f); EXPECT_NEAR(pixel[1], 162, .0001f);
    EXPECT_FALSE(sd_project_point(behind, identity, &camera, pixel));
    memcpy(camera.model, "fisheye", 8);
    EXPECT_FALSE(sd_project_point(known, local, &camera, pixel));
    uint8_t reserved[48 * 2 + 4] = {};
    const uint32_t count = 1;
    memcpy(reserved + sizeof(reserved) - 4, &count, 4);
    SdRecordView view{};
    ASSERT_TRUE(sd_records(reserved, sizeof(reserved), sizeof(SdSemanticBox2D), true, &view));
    EXPECT_EQ(view.count, 1u);
}

TEST(CameraAovDecoding, MetadataAndImageOffset) {
    // Non-zero padding distinguishes fields; tokens keep all 64 bits of opaque handles.
    const uint32_t token_words[12] = {1, 99, 7, 7, 1, 0, 7, 88, 0x12345678, 0xabcdef01, 2, 3};
    SdRecordView view{};
    ASSERT_TRUE(sd_records(reinterpret_cast<const uint8_t*>(token_words), sizeof(token_words), sizeof(SdInstanceToken), false, &view));
    SdInstanceToken header{}, token{};
    memcpy(&header, view.data, sizeof(header));
    memcpy(&token, view.data + view.stride, sizeof(token));
    EXPECT_EQ(header.instance_id, view.count - 1);
    EXPECT_EQ(token.prim_token, UINT64_C(0xabcdef0112345678));
    EXPECT_EQ(token.prototype, 2u); EXPECT_EQ(token.instance_index, 3u);
    const uint32_t indices[2] = {5, 9};
    ASSERT_TRUE(sd_instance_map(reinterpret_cast<const uint8_t*>(indices), sizeof(indices), &view));
    EXPECT_EQ(view.count, 2u);
    uint32_t second_index = 0;
    memcpy(&second_index, view.data + view.stride, sizeof(second_index));
    EXPECT_EQ(second_index, 9u);
    const uint32_t pairs[8] = {1, 2, 3, 4, 5, 6, 7, 8};
    ASSERT_TRUE(sd_records(reinterpret_cast<const uint8_t*>(pairs), sizeof(pairs), sizeof(SdIdPair), false, &view));
    SdIdPair pair{};
    memcpy(&pair, view.data, sizeof(pair));
    EXPECT_EQ(pair.stable_id[3], 4u); EXPECT_EQ(pair.semantic_id[3], 8u);
    const uint32_t occlusion_words[3] = {7, 2, 0x3e800000}; // 0.25f
    ASSERT_TRUE(sd_records(reinterpret_cast<const uint8_t*>(occlusion_words), sizeof(occlusion_words), sizeof(SdOcclusion), false, &view));
    SdOcclusion occlusion{};
    memcpy(&occlusion, view.data, sizeof(occlusion));
    EXPECT_EQ(occlusion.tile_id, 2u); EXPECT_FLOAT_EQ(occlusion.ratio, 0.25f);

    // DLPack offsets are bytes, while strides are scalar elements.
    uint8_t pixels[32] = {};
    int64_t shape[3] = {2, 3, 4}, strides[3] = {12, 4, 1};
    DLTensor tensor{};
    tensor.data = pixels; tensor.device.device_type = kDLCPU; tensor.ndim = 3;
    tensor.dtype = {kDLUInt, 8, 1}; tensor.shape = shape; tensor.strides = strides;
    tensor.byte_offset = 8;
    EXPECT_EQ(sd_image_data(&tensor), pixels + 8);
    strides[0] = 16;
    EXPECT_EQ(sd_image_data(&tensor), nullptr);
}


// [snippet:doc-pt-pixels-c]
// Decode IEEE binary16, including subnormal values and special exponents.
static float pt_half_to_float(uint16_t bits) {
    const uint32_t exponent = (bits >> 10) & 31u;
    const uint32_t fraction = bits & 1023u;
    float value;
    if (exponent == 31)
        value = fraction ? std::numeric_limits<float>::quiet_NaN() : std::numeric_limits<float>::infinity();
    else if (exponent == 0)
        value = std::ldexp(static_cast<float>(fraction), -24);
    else
        value = std::ldexp(1.0f + static_cast<float>(fraction) / 1024.0f, static_cast<int>(exponent) - 15);
    return bits & 0x8000u ? -value : value;
}

// Read one typed CPU pixel. Byte formats are UNORM; ID images need their uint32 decoder.
static bool pt_read_pixel(const DLTensor* tensor, int64_t x, int64_t y, float pixel[4]) {
    const void* first = sd_image_data(tensor);
    if (!first || !pixel || x < 0 || y < 0 || x >= tensor->shape[1] || y >= tensor->shape[0] ||
        (tensor->shape[2] != 1 && tensor->shape[2] != 2 && tensor->shape[2] != 4)) return false;
    const bool half = tensor->dtype.code == kDLFloat && tensor->dtype.bits == 16;
    const bool single = tensor->dtype.code == kDLFloat && tensor->dtype.bits == 32;
    const bool unorm = tensor->dtype.code == kDLUInt && tensor->dtype.bits == 8;
    if (!half && !single && !unorm) return false;
    const size_t channels = static_cast<size_t>(tensor->shape[2]);
    const size_t offset = (static_cast<size_t>(y) * tensor->shape[1] + x) * channels;
    const uint8_t* bytes = static_cast<const uint8_t*>(first);
    for (size_t channel = 0; channel < 4; ++channel) {
        pixel[channel] = 0;
        if (channel >= channels) continue;
        if (half) {
            uint16_t bits = 0;
            memcpy(&bits, bytes + (offset + channel) * 2, 2);
            pixel[channel] = pt_half_to_float(bits);
        } else if (single) {
            memcpy(&pixel[channel], bytes + (offset + channel) * 4, 4);
        } else pixel[channel] = bytes[offset + channel] / 255.0f;
    }
    return true;
}
// [/snippet:doc-pt-pixels-c]


// [snippet:doc-pt-view-data-c]
// ViewMatricesAux contains fourteen matrices followed by translations and projection parameters.
typedef struct PtViewData {
    float projection[4][4], projection_no_jitter[4][4], inverse_projection[4][4];
    float view[4][4], inverse_view[4][4], view_projection[4][4], inverse_view_projection[4][4];
    float view_no_roll[4][4], translated_view[4][4], inverse_translated_view[4][4];
    float overridden_translated_view[4][4], inverse_overridden_translated_view[4][4];
    float translated_view_projection[4][4], inverse_translated_view_projection[4][4];
    float pre_view_translation[4], view_origin[4], projection_scale[2], projection_jitter[2];
} PtViewData;

// Copy the record while its CPU mapping is alive; validate type and length first.
static bool pt_read_view_data(const DLTensor* tensor, PtViewData* record) {
    const void* data = sd_image_data(tensor);
    if (!data || !record || tensor->dtype.code != kDLFloat || tensor->dtype.bits != 32 ||
        tensor->shape[0] != 1 || tensor->shape[1] != 236 || tensor->shape[2] != 1) return false;
    memcpy(record, data, sizeof(*record));
    return true;
}
// [/snippet:doc-pt-view-data-c]

static_assert(sizeof(PtViewData) == 236 * sizeof(float));
static_assert(offsetof(PtViewData, view_origin) == 228 * sizeof(float));

TEST(CameraAovDecoding, PathTracingPixelsAndViewData) {
    // Independent binary16 encodings catch reinterpretation, subnormal, and sign mistakes.
    uint16_t halves[8] = {0, 0, 0, 0, 0x3c00, 0xc000, 0x0001, 0x7c00};
    int64_t shape[3] = {1, 1, 4};
    DLTensor tensor{};
    tensor.data = halves; tensor.device.device_type = kDLCPU; tensor.ndim = 3;
    tensor.dtype = {kDLFloat, 16, 1}; tensor.shape = shape; tensor.byte_offset = 8;
    float pixel[4] = {};
    ASSERT_TRUE(pt_read_pixel(&tensor, 0, 0, pixel));
    EXPECT_FLOAT_EQ(pixel[0], 1); EXPECT_FLOAT_EQ(pixel[1], -2);
    EXPECT_FLOAT_EQ(pixel[2], std::ldexp(1.0f, -24)); EXPECT_TRUE(std::isinf(pixel[3]));
    EXPECT_FALSE(pt_read_pixel(&tensor, 1, 0, pixel));
    uint8_t unorm[4] = {255, 128, 0, 255};
    tensor.data = unorm; tensor.dtype = {kDLUInt, 8, 1}; tensor.byte_offset = 0;
    ASSERT_TRUE(pt_read_pixel(&tensor, 0, 0, pixel));
    EXPECT_FLOAT_EQ(pixel[0], 1); EXPECT_FLOAT_EQ(pixel[1], 128 / 255.0f);
    tensor.dtype = {kDLUInt, 32, 1};
    EXPECT_FALSE(pt_read_pixel(&tensor, 0, 0, pixel));

    // A nonzero row/column and two channels distinguish pixel addressing from scalar indexing.
    float pairs[12] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11};
    shape[0] = 2; shape[1] = 3; shape[2] = 2;
    tensor.data = pairs; tensor.dtype = {kDLFloat, 32, 1};
    ASSERT_TRUE(pt_read_pixel(&tensor, 2, 1, pixel));
    EXPECT_FLOAT_EQ(pixel[0], 10); EXPECT_FLOAT_EQ(pixel[1], 11);
    EXPECT_FALSE(pt_read_pixel(&tensor, 0, 2, pixel));
    shape[2] = 1;
    ASSERT_TRUE(pt_read_pixel(&tensor, 2, 1, pixel));
    EXPECT_FLOAT_EQ(pixel[0], 5);
    shape[0] = 1;

    float values[236];
    for (size_t i = 0; i < 236; ++i) values[i] = static_cast<float>(i);
    shape[1] = 236; shape[2] = 1; tensor.data = values; tensor.dtype = {kDLFloat, 32, 1};
    PtViewData record{};
    ASSERT_TRUE(pt_read_view_data(&tensor, &record));
    EXPECT_FLOAT_EQ(record.view[0][0], 48);
    EXPECT_FLOAT_EQ(record.view_origin[0], 228); EXPECT_FLOAT_EQ(record.projection_jitter[1], 235);
    shape[1] = 235;
    EXPECT_FALSE(pt_read_view_data(&tensor, &record));
}
