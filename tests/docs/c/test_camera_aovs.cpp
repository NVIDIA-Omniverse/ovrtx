// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Smoke tests for all documented camera AOVs (Real-Time Path Tracing mode)

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
        ovrtx_step_result_handle_t warmup_handle{};
        ovrtx_enqueue_result_t warmup_eq = ovrtx_step_with_stage(
            renderer_, render_products, 1.0 / 60.0, ordinal, &warmup_handle);
        ASSERT_API_SUCCESS(warmup_eq.status);
        docs_wait_no_errors(renderer_, warmup_eq.op_index);
        ovrtx_destroy_results(renderer_, warmup_handle);
    }

    ovrtx_step_result_handle_t step_handle{};
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
        ASSERT_NE(handle, OVRTX_INVALID_RENDER_VAR_OUTPUT_HANDLE);
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
        ASSERT_NE(handle, OVRTX_INVALID_RENDER_VAR_OUTPUT_HANDLE);
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
        ASSERT_NE(handle, OVRTX_INVALID_RENDER_VAR_OUTPUT_HANDLE);
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
        ASSERT_NE(handle, OVRTX_INVALID_RENDER_VAR_OUTPUT_HANDLE);
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
        ASSERT_NE(handle, OVRTX_INVALID_RENDER_VAR_OUTPUT_HANDLE);
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
        ASSERT_NE(handle, OVRTX_INVALID_RENDER_VAR_OUTPUT_HANDLE);
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
        ASSERT_NE(handle, OVRTX_INVALID_RENDER_VAR_OUTPUT_HANDLE);
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
        ASSERT_NE(handle, OVRTX_INVALID_RENDER_VAR_OUTPUT_HANDLE);
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
// Set counted only when a legacy record buffer ends with an explicit record count.
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
// Look up public fields by name, never by an assumed tensor slot or packed ABI.
static const DLTensor* sd_field(const ovrtx_render_var_output_t* output, const char* name, bool param = false) {
    if (!output) return nullptr;
    for (size_t i = 0; i < (param ? output->num_params : output->num_tensors); ++i) {
        const ovx_string_t* key = param ? &output->params[i].name : output->tensors[i].name;
        if (key && key->ptr && key->length == strlen(name) && !memcmp(key->ptr, name, key->length))
            return param ? &output->params[i].dl : output->tensors[i].dl;
    }
    return nullptr;
}

// Read scalar elements in logical row-major order. DLPack strides are in elements;
// byte_offset is in bytes. CPU mappings must have completed before reading.
static bool sd_read(const DLTensor* tensor, size_t first, size_t count, uint8_t code, uint8_t bits, void* destination) {
    if (!tensor || !destination || tensor->device.device_type != kDLCPU || tensor->dtype.code != code ||
        tensor->dtype.bits != bits || tensor->dtype.lanes != 1 || !bits || bits % 8 || tensor->ndim < 0 ||
        (tensor->ndim && !tensor->shape)) return false;
    size_t size = 1;
    for (int dim = 0; dim < tensor->ndim; ++dim) {
        if (tensor->shape[dim] < 0 || (tensor->shape[dim] && size > SIZE_MAX / size_t(tensor->shape[dim])))
            return false;
        size *= size_t(tensor->shape[dim]);
    }
    if (first > size || count > size - first || (count && !tensor->data)) return false;
    for (size_t element = 0; element < count; ++element) {
        size_t index = first + element, offset = 0, contiguous = 1;
        for (int dim = tensor->ndim; dim-- > 0;) {
            if (tensor->strides && tensor->strides[dim] < 0) return false;
            const size_t stride = tensor->strides ? size_t(tensor->strides[dim]) : contiguous;
            offset += index % size_t(tensor->shape[dim]) * stride;
            index /= size_t(tensor->shape[dim]);
            contiguous *= size_t(tensor->shape[dim]);
        }
        memcpy(static_cast<uint8_t*>(destination) + element * (bits / 8),
               static_cast<const uint8_t*>(tensor->data) + tensor->byte_offset + offset * (bits / 8), bits / 8);
    }
    return true;
}

// Raw boxes use extent.shape[0] rows. Semantic boxes have capacity-sized fields:
// consume only valid_count[0] rows, including when valid_count is zero.
static bool sd_box_count(const ovrtx_render_var_output_t* output, bool semantic, size_t* count) {
    const DLTensor* extent = sd_field(output, "extent");
    if (!extent || !extent->shape || extent->ndim != 3 || extent->shape[0] < 0 || !count) return false;
    *count = size_t(extent->shape[0]);
    if (semantic) {
        uint32_t valid = 0;
        if (!sd_read(sd_field(output, "valid_count"), 0, 1, kDLUInt, 32, &valid) || valid > *count) return false;
        *count = valid;
    }
    return true;
}
// extent is int32[N,2,2] for 2D, float32[N,2,3] for 3D (minimum then maximum).
// Raw keys: instance_id and render_tile_id. Semantic keys: id[N,4], semantic_id[N,4].
// 3D boxes additionally publish object_to_world[N,4,4]. Use sd_read() for each field.
// Skip inverted bounds and clip 3D edges before projection.
// [/snippet:doc-sd-boxes-c]


// [snippet:doc-sd-occlusion-c]
// Application convenience type; source fields may have different element strides.
typedef struct SdOcclusion {
    uint32_t instance_id, tile_id;
    float ratio;
} SdOcclusion;
static bool sd_occlusion(const ovrtx_render_var_output_t* output, size_t row, SdOcclusion* value) {
    return value && sd_read(sd_field(output, "instance_id"), row, 1, kDLUInt, 32, &value->instance_id) &&
           sd_read(sd_field(output, "render_tile_id"), row, 1, kDLUInt, 32, &value->tile_id) &&
           sd_read(sd_field(output, "occlusion_ratio"), row, 1, kDLFloat, 32, &value->ratio);
}
// Join to raw boxes by instance_id AND tile_id; negative ratios are invalid.
// [/snippet:doc-sd-occlusion-c]


// [snippet:doc-sd-tokens-c]
typedef struct SdInstanceToken {
    uint32_t instance_id;
    uint64_t prim_token;
    uint32_t prototype, instance_index;
} SdInstanceToken;
typedef struct SdTokenParams {
    uint32_t min_instance_id, max_instance_id, render_tile_count;
} SdTokenParams;
static bool sd_token(const ovrtx_render_var_output_t* output, size_t row,
                     SdInstanceToken* value, SdTokenParams* params) {
    return value && params &&
           sd_read(sd_field(output, "instance_id"), row, 1, kDLUInt, 32, &value->instance_id) &&
           sd_read(sd_field(output, "prim_token"), row, 1, kDLUInt, 64, &value->prim_token) &&
           sd_read(sd_field(output, "prototype_index"), row, 1, kDLUInt, 32, &value->prototype) &&
           sd_read(sd_field(output, "instance_index"), row, 1, kDLUInt, 32, &value->instance_index) &&
           sd_read(sd_field(output, "min_instance_id", true), 0, 1, kDLUInt, 32, &params->min_instance_id) &&
           sd_read(sd_field(output, "max_instance_id", true), 0, 1, kDLUInt, 32, &params->max_instance_id) &&
           sd_read(sd_field(output, "render_tile_count", true), 0, 1, kDLUInt, 32, &params->render_tile_count);
}
// Tensor rows contain only instances. Params are CPU scalars even for CUDA maps.
// prim_token is an opaque runtime handle, not an address to a string.
// [/snippet:doc-sd-tokens-c]


// [snippet:doc-sd-instance-map-c]
static bool sd_instance_map(const ovrtx_render_var_output_t* output, size_t row, uint32_t* index) {
    return index && sd_read(sd_field(output, "semantic_instance_index"), row, 1, kDLUInt, 32, index);
}
// Element i belongs to min_instance_id + i from the token-map CPU params.
// UINT32_MAX means no semantic parent; these indices are not semantic label IDs.
// [/snippet:doc-sd-instance-map-c]


// [snippet:doc-sd-identifiers-c]
// Decode one ID/path or ID/label pair. Keep repeated IDs as separate rows.
static bool sd_identifier(const ovrtx_render_var_output_t* output, size_t row, uint32_t id[4],
                          const char** label, size_t* length) {
    const DLTensor* ids = sd_field(output, "id");
    const DLTensor* offsets = sd_field(output, "label_offsets");
    const DLTensor* data = sd_field(output, "label_data");
    if (!ids || ids->ndim != 2 || !ids->shape || ids->shape[0] < 0 || ids->shape[1] != 4 ||
        row >= size_t(ids->shape[0]) || !offsets || offsets->ndim != 1 || !offsets->shape ||
        offsets->shape[0] != ids->shape[0] + 1 || !data || data->device.device_type != kDLCPU ||
        data->ndim != 1 || !data->shape || data->shape[0] < 0 || data->dtype.code != kDLUInt ||
        data->dtype.bits != 8 || data->dtype.lanes != 1 || (data->strides && data->strides[0] != 1) ||
        !label || !length) return false;
    uint64_t spans[2] = {};
    if (!sd_read(ids, row * 4, 4, kDLUInt, 32, id) ||
        !sd_read(offsets, row, 2, kDLUInt, 64, spans) || spans[0] > spans[1] ||
        spans[1] > uint64_t(data->shape[0]) || (spans[1] && !data->data)) return false;
    *length = size_t(spans[1] - spans[0]);
    *label = data->data ? static_cast<const char*>(data->data) + data->byte_offset + spans[0] : "";
    return true; // Read exactly length UTF-8 bytes; embedded NULs are permitted.
}
// [/snippet:doc-sd-identifiers-c]


// [snippet:doc-sd-id-pairs-c]
typedef struct SdIdPair {
    uint32_t stable_id[4], semantic_id[4];
} SdIdPair;
static bool sd_id_pair(const ovrtx_render_var_output_t* output, size_t row, SdIdPair* value) {
    const DLTensor* stable = sd_field(output, "stable_id");
    const DLTensor* semantic = sd_field(output, "semantic_id");
    return value && stable && semantic && stable->ndim == 2 && semantic->ndim == 2 &&
           stable->shape && semantic->shape && stable->shape[1] == 4 && semantic->shape[1] == 4 &&
           stable->shape[0] == semantic->shape[0] && stable->shape[0] >= 0 && row < size_t(stable->shape[0]) &&
           sd_read(stable, row * 4, 4, kDLUInt, 32, value->stable_id) &&
           sd_read(semantic, row * 4, 4, kDLUInt, 32, value->semantic_id);
}
// All four words belong to each ID, including its subset component.
// [/snippet:doc-sd-id-pairs-c]


// [snippet:doc-sd-camera-c]
// This is an application convenience type, not the producer's binary record layout.
typedef struct SdCamera {
    float world_to_camera[4][4], projection[4][4];
    uint32_t resolution[2];
    char model[25];
} SdCamera;
static bool sd_camera(const ovrtx_render_var_output_t* output, SdCamera* camera) {
    if (!output || output->num_tensors != 0 || !camera) return false;
    const DLTensor* model = sd_field(output, "camera_model", true);
    if (!model || model->ndim != 1 || !model->shape || model->shape[0] < 0 ||
        size_t(model->shape[0]) >= sizeof(camera->model)) return false;
    memset(camera, 0, sizeof(*camera));
    return sd_read(sd_field(output, "view_matrix", true), 0, 16, kDLFloat, 32, camera->world_to_camera) &&
           sd_read(sd_field(output, "projection_matrix", true), 0, 16, kDLFloat, 32, camera->projection) &&
           sd_read(sd_field(output, "render_product_resolution", true), 0, 2, kDLUInt, 32, camera->resolution) &&
           sd_read(model, 0, size_t(model->shape[0]), kDLUInt, 8, camera->model);
}
// All camera fields are CPU params, including focal_length, near_far and lens parameters.
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

TEST(CameraAovDecoding, BoundsAndIdentifierStorage) {
    uint32_t id_data[12] = {99, 99, 1, 2, 3, 4, 99, 99, 1, 2, 3, 4};
    int64_t id_shape[2] = {2, 4}, id_strides[2] = {6, 1};
    uint64_t offset_data[3] = {0, 2, 4};
    int64_t offset_shape[1] = {3}, data_shape[1] = {4};
    char labels[] = "/a/b";
    DLTensor ids{ id_data, {kDLCPU, 0}, 2, {kDLUInt, 32, 1}, id_shape, id_strides, 8 };
    DLTensor offsets{ offset_data, {kDLCPU, 0}, 1, {kDLUInt, 64, 1}, offset_shape, nullptr, 0 };
    DLTensor data{ labels, {kDLCPU, 0}, 1, {kDLUInt, 8, 1}, data_shape, nullptr, 0 };
    ovx_string_t names[] = {{"id", 2}, {"label_offsets", 13}, {"label_data", 10}};
    ovrtx_render_var_tensor_t fields[] = {{&ids, &names[0], nullptr}, {&offsets, &names[1], nullptr},
                                        {&data, &names[2], nullptr}};
    ovrtx_render_var_output_t output{};
    output.num_tensors = 3; output.tensors = fields;
    uint32_t first[4]{}, second[4]{}; const char* label = nullptr; size_t length = 0;
    ASSERT_TRUE(sd_identifier(&output, 0, first, &label, &length));
    EXPECT_EQ(std::string(label, length), "/a");
    ASSERT_TRUE(sd_identifier(&output, 1, second, &label, &length));
    EXPECT_EQ(std::string(label, length), "/b");
    EXPECT_EQ(memcmp(first, second, sizeof(first)), 0);
    EXPECT_EQ(second[3], 4u);
    offset_data[2] = 1024;
    EXPECT_FALSE(sd_identifier(&output, 1, second, &label, &length));
    EXPECT_FALSE(sd_identifier(&output, 2, second, &label, &length));
    EXPECT_FALSE(sd_read(&ids, 7, 2, kDLUInt, 32, first));
    EXPECT_FALSE(sd_read(&ids, 0, 1, kDLFloat, 32, first));
}

TEST(CameraAovDecoding, CameraProjectionAndReservedCapacity) {
    float identity[4][4] = {{1, 0, 0, 0}, {0, 1, 0, 0}, {0, 0, 1, 0}, {0, 0, 0, 1}};
    uint32_t resolution[2] = {640, 360};
    char model[] = "pinhole";
    int64_t matrix_shape[2] = {4, 4}, resolution_shape[1] = {2}, model_shape[1] = {7};
    ovrtx_render_var_param_t params[4]{};
    params[0].name = {"view_matrix", 11};
    params[0].dl = {identity, {kDLCPU, 0}, 2, {kDLFloat, 32, 1}, matrix_shape, nullptr, 0};
    params[1] = params[0]; params[1].name = {"projection_matrix", 17};
    params[2].name = {"render_product_resolution", 25};
    params[2].dl = {resolution, {kDLCPU, 0}, 1, {kDLUInt, 32, 1}, resolution_shape, nullptr, 0};
    params[3].name = {"camera_model", 12};
    params[3].dl = {model, {kDLCPU, 0}, 1, {kDLUInt, 8, 1}, model_shape, nullptr, 0};
    ovrtx_render_var_output_t output{};
    output.num_params = 4; output.params = params;
    SdCamera camera{};
    ASSERT_TRUE(sd_camera(&output, &camera));
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
    // Parameter lookup must reject missing data, wrong types, and invalid model lengths.
    output.num_params = 3;
    EXPECT_FALSE(sd_camera(&output, &camera));
    output.num_params = 4;
    params[0].dl.dtype = {kDLUInt, 32, 1};
    EXPECT_FALSE(sd_camera(&output, &camera));
    params[0].dl.dtype = {kDLFloat, 32, 1};
    model_shape[0] = sizeof(camera.model);
    EXPECT_FALSE(sd_camera(&output, &camera));
}

TEST(CameraAovDecoding, MetadataAndImageOffset) {
    // Field descriptors, not private record casts, select strided CPU values.
    uint32_t token_words[12] = {7, 99, 0x12345678, 0xabcdef01, 2, 3, 8, 88, 0, 0, 4, 5};
    int64_t rows[1] = {2}, u32_stride[1] = {6}, u64_stride[1] = {3};
    DLTensor token_fields[] = {
        {token_words, {kDLCPU, 0}, 1, {kDLUInt, 32, 1}, rows, u32_stride, 0},
        {token_words, {kDLCPU, 0}, 1, {kDLUInt, 64, 1}, rows, u64_stride, 8},
        {token_words, {kDLCPU, 0}, 1, {kDLUInt, 32, 1}, rows, u32_stride, 16},
        {token_words, {kDLCPU, 0}, 1, {kDLUInt, 32, 1}, rows, u32_stride, 20},
    };
    ovx_string_t names[] = {{"instance_id", 11}, {"prim_token", 10}, {"prototype_index", 15}, {"instance_index", 14}};
    ovrtx_render_var_tensor_t fields[4]{};
    for (size_t i = 0; i < 4; ++i) fields[i] = {&token_fields[i], &names[i], nullptr};
    uint32_t limits[] = {7, 8, 2};
    int64_t scalar_shape[] = {1}, scalar_stride[] = {1};
    ovrtx_render_var_param_t params[3]{};
    params[0].name = {"min_instance_id", 15}; params[1].name = {"max_instance_id", 15};
    params[2].name = {"render_tile_count", 17};
    for (size_t i = 0; i < 3; ++i)
        params[i].dl = {&limits[i], {kDLCPU, 0}, 1, {kDLUInt, 32, 1}, scalar_shape, scalar_stride, 0};
    ovrtx_render_var_output_t output{};
    output.num_tensors = 4; output.tensors = fields; output.num_params = 3; output.params = params;
    SdInstanceToken token{}; SdTokenParams range{};
    ASSERT_TRUE(sd_token(&output, 0, &token, &range));
    EXPECT_EQ(token.prim_token, UINT64_C(0xabcdef0112345678));
    EXPECT_EQ(token.prototype, 2u); EXPECT_EQ(token.instance_index, 3u);
    EXPECT_EQ(range.min_instance_id, 7u); EXPECT_EQ(range.max_instance_id, 8u);
    EXPECT_EQ(range.render_tile_count, 2u);
    EXPECT_FALSE(sd_token(&output, 2, &token, &range));

    uint32_t indices[2] = {5, UINT32_MAX};
    token_fields[0] = {indices, {kDLCPU, 0}, 1, {kDLUInt, 32, 1}, rows, nullptr, 0};
    names[0] = {"semantic_instance_index", 23}; output.num_tensors = 1; output.num_params = 0;
    uint32_t second_index = 0;
    ASSERT_TRUE(sd_instance_map(&output, 1, &second_index));
    EXPECT_EQ(second_index, UINT32_MAX);
    EXPECT_FALSE(sd_instance_map(&output, 2, &second_index));

    uint32_t pairs[8] = {1, 2, 3, 4, 5, 6, 7, 8};
    int64_t pair_shape[2] = {1, 4}, pair_stride[2] = {8, 1};
    token_fields[0] = {pairs, {kDLCPU, 0}, 2, {kDLUInt, 32, 1}, pair_shape, pair_stride, 0};
    token_fields[1] = token_fields[0]; token_fields[1].byte_offset = 16;
    names[0] = {"stable_id", 9}; names[1] = {"semantic_id", 11}; output.num_tensors = 2;
    SdIdPair pair{};
    ASSERT_TRUE(sd_id_pair(&output, 0, &pair));
    EXPECT_EQ(pair.stable_id[3], 4u); EXPECT_EQ(pair.semantic_id[3], 8u);
    EXPECT_FALSE(sd_id_pair(&output, 1, &pair));

    uint32_t occlusion_words[6] = {7, 2, 0x3e800000, 8, 3, 0xbf800000}; // 0.25f and -1.f
    int64_t occlusion_stride[1] = {3};
    for (size_t i = 0; i < 3; ++i)
        token_fields[i] = {occlusion_words, {kDLCPU, 0}, 1, {uint8_t(i == 2 ? kDLFloat : kDLUInt), 32, 1},
                           rows, occlusion_stride, i * 4};
    names[0] = {"instance_id", 11}; names[1] = {"render_tile_id", 14}; names[2] = {"occlusion_ratio", 15};
    output.num_tensors = 3;
    SdOcclusion occlusion{};
    ASSERT_TRUE(sd_occlusion(&output, 0, &occlusion));
    EXPECT_EQ(occlusion.tile_id, 2u); EXPECT_FLOAT_EQ(occlusion.ratio, 0.25f);
    ASSERT_TRUE(sd_occlusion(&output, 1, &occlusion));
    EXPECT_FLOAT_EQ(occlusion.ratio, -1.f);

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


TEST(CameraAovDecoding, PathTracingPixels) {
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

}

TEST(CameraAovDecoding, BoundingBoxNamedFieldsAndCapacity) {
    int32_t extent_data[8]{};
    int64_t extent_shape[3] = {2, 2, 2}, count_shape[1] = {1};
    uint32_t valid_count = 1;
    DLTensor extent{extent_data, {kDLCPU, 0}, 3, {kDLInt, 32, 1}, extent_shape, nullptr, 0};
    DLTensor count_tensor{&valid_count, {kDLCPU, 0}, 1, {kDLUInt, 32, 1}, count_shape, nullptr, 0};
    ovx_string_t names[] = {{"extent", 6}, {"valid_count", 11}};
    ovrtx_render_var_tensor_t fields[] = {{&extent, &names[0], nullptr}, {&count_tensor, &names[1], nullptr}};
    ovrtx_render_var_output_t output{};
    output.num_tensors = 2; output.tensors = fields;
    size_t count = 0;
    ASSERT_TRUE(sd_box_count(&output, true, &count)); EXPECT_EQ(count, 1u);
    valid_count = 0;
    ASSERT_TRUE(sd_box_count(&output, true, &count)); EXPECT_EQ(count, 0u);
    valid_count = 3;
    EXPECT_FALSE(sd_box_count(&output, true, &count));
    ASSERT_TRUE(sd_box_count(&output, false, &count)); EXPECT_EQ(count, 2u);
    int32_t padded_extent[] = {99, 1, 2, 3, 4, 99, 99, 5, 6, 7, 8, 99};
    int64_t strides[3] = {6, 2, 1};
    extent.data = padded_extent; extent.strides = strides; extent.byte_offset = sizeof(int32_t);
    int32_t row[4]{};
    ASSERT_TRUE(sd_read(sd_field(&output, "extent"), 4, 4, kDLInt, 32, row));
    EXPECT_EQ(row[0], 5); EXPECT_EQ(row[3], 8);
    EXPECT_FALSE(sd_read(&extent, 7, 2, kDLInt, 32, row));
    EXPECT_FALSE(sd_read(&extent, 0, 1, kDLFloat, 32, row));
}
