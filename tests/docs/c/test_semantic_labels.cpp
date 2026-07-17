// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Tests for C semantic label authoring and semantic segmentation outputs.

#include <gtest/gtest.h>
#include "helpers.h"

#include <ovx/dlpack/dlpack.h>

#include <cctype>
#include <cmath>
#include <cstdint>
#include <map>
#include <set>
#include <string>

static constexpr int WIDTH = 1280;
static constexpr int HEIGHT = 720;

static size_t tensor_num_elements(DLTensor const& tensor) {
    size_t count = 1;
    for (int i = 0; i < tensor.ndim; ++i) {
        count *= static_cast<size_t>(tensor.shape[i]);
    }
    return count * static_cast<size_t>(tensor.dtype.lanes);
}

static size_t tensor_byte_size(DLTensor const& tensor) {
    return tensor_num_elements(tensor) * static_cast<size_t>((tensor.dtype.bits + 7) / 8);
}

static uint32_t read_u32_le(uint8_t const* data) {
    return static_cast<uint32_t>(data[0]) |
           (static_cast<uint32_t>(data[1]) << 8) |
           (static_cast<uint32_t>(data[2]) << 16) |
           (static_cast<uint32_t>(data[3]) << 24);
}

static void trim_semantic_label(std::string& label) {
    while (!label.empty()) {
        unsigned char c = static_cast<unsigned char>(label.back());
        if (c != '\0' && !std::isspace(c)) {
            break;
        }
        label.pop_back();
    }
}

// [snippet:doc-interpret-semantic-segmentation-c]
static std::map<uint32_t, std::string> decode_semantic_id_map(DLTensor const& tensor) {
    uint8_t const* data = static_cast<uint8_t const*>(tensor.data) + tensor.byte_offset;
    size_t const byte_count = tensor_byte_size(tensor);
    if (byte_count < sizeof(uint32_t)) {
        return {};
    }

    uint32_t const num_entries = read_u32_le(data + byte_count - sizeof(uint32_t));
    size_t constexpr entry_size = sizeof(uint32_t) * 6;
    if (static_cast<size_t>(num_entries) * entry_size > byte_count - sizeof(uint32_t)) {
        return {};
    }

    std::map<uint32_t, std::string> labels_by_id;
    for (uint32_t i = 0; i < num_entries; ++i) {
        uint8_t const* entry = data + static_cast<size_t>(i) * entry_size;
        uint32_t const semantic_id = read_u32_le(entry);
        uint32_t const label_length = read_u32_le(entry + sizeof(uint32_t) * 4);
        uint32_t const label_offset = read_u32_le(entry + sizeof(uint32_t) * 5);
        size_t const label_end = static_cast<size_t>(label_offset) + label_length;
        if (label_end > byte_count) {
            continue;
        }

        std::string label(
            reinterpret_cast<char const*>(data + label_offset),
            static_cast<size_t>(label_length));
        trim_semantic_label(label);
        labels_by_id[semantic_id] = label;
    }

    return labels_by_id;
}

static std::set<uint32_t> collect_semantic_segmentation_ids(DLTensor const& tensor) {
    EXPECT_EQ(tensor.dtype.bits, 32);
    EXPECT_EQ(tensor.dtype.lanes, 1);
    EXPECT_TRUE(tensor.ndim == 2 || tensor.ndim == 3);
    if (tensor.ndim == 3) {
        EXPECT_EQ(tensor.shape[2], 1);
    }

    int64_t const height = tensor.shape[0];
    int64_t const width = tensor.shape[1];
    int64_t const stride_y = tensor.strides
        ? tensor.strides[0]
        : width * (tensor.ndim == 3 ? tensor.shape[2] : 1);
    int64_t const stride_x = tensor.strides
        ? tensor.strides[1]
        : (tensor.ndim == 3 ? tensor.shape[2] : 1);

    uint8_t const* base = static_cast<uint8_t const*>(tensor.data) + tensor.byte_offset;

    std::set<uint32_t> ids;
    if (tensor.dtype.code == kDLUInt) {
        uint32_t const* values = reinterpret_cast<uint32_t const*>(base);
        for (int64_t y = 0; y < height; ++y) {
            for (int64_t x = 0; x < width; ++x) {
                ids.insert(values[y * stride_y + x * stride_x]);
            }
        }
    } else if (tensor.dtype.code == kDLInt) {
        int32_t const* values = reinterpret_cast<int32_t const*>(base);
        for (int64_t y = 0; y < height; ++y) {
            for (int64_t x = 0; x < width; ++x) {
                ids.insert(static_cast<uint32_t>(values[y * stride_y + x * stride_x]));
            }
        }
    } else {
        ADD_FAILURE() << "SemanticSegmentation must use 32-bit integer pixels";
    }
    return ids;
}
// [/snippet:doc-interpret-semantic-segmentation-c]

class SemanticLabelsTest : public DocsOvstageTestBase {
protected:
    DOCS_OVSTAGE_TEST_SUITE(SemanticLabelsTest)
};

TEST_F(SemanticLabelsTest, SemanticClassesAreRendered) {
    std::string const scene_path = get_docs_test_data_dir() + "/ovrtx-test-base.usda";
    std::string const semantic_labels_path =
        get_docs_test_data_dir() + "/ovrtx-test-base-semantic-labels.usda";

    // [snippet:doc-semantic-class-overrides-c]
    std::string usda = "#usda 1.0\n"
                       "(\n"
                       "    subLayers = [\n"
                       "        @" + semantic_labels_path + "@,\n"
                       "        @" + scene_path + "@\n"
                       "    ]\n"
                       ")\n\n"
                       "def \"Render\"\n"
                       "{\n"
                       "    def RenderProduct \"SemanticCamera\"\n"
                       "    {\n"
                       "        int2 resolution = (1280, 720)\n"
                       "        rel camera = </World/Camera>\n"
                       "        rel orderedVars = [<SemanticSegmentation>, <SemanticIdMap>]\n"
                       "\n"
                       "        def RenderVar \"SemanticSegmentation\"\n"
                       "        {\n"
                       "            string sourceName = \"SemanticSegmentation\"\n"
                       "        }\n"
                       "\n"
                       "        def RenderVar \"SemanticIdMap\"\n"
                       "        {\n"
                       "            string sourceName = \"SemanticIdMap\"\n"
                       "        }\n"
                       "    }\n"
                       "}\n";

    ovstage_population_enqueue_result_t pr = ovstage_population_open_usd_from_string(
        stage_,
        {usda.c_str(), usda.size()},
        /*ordinal=*/1,
        /*time=*/NAN,
        OVSTAGE_POPULATION_DOMAIN_RENDERING);
    ASSERT_EQ(pr.status, OVSTAGE_OK) << format_ovstage_population_last_error();
    docs_wait_ovstage_population_no_errors(stage_, pr.op_index);
    docs_ovstage_advance_write_floor(stage_, 1);
    // [/snippet:doc-semantic-class-overrides-c]

    ovx_string_t render_product_path = ovx_str("/Render/SemanticCamera");
    ovrtx_render_product_set_t render_products{};
    render_products.render_products = &render_product_path;
    render_products.num_render_products = 1;

    for (int i = 0; i < 5; ++i) {
        ovrtx_step_result_handle_t warmup_handle = 0;
        ovrtx_enqueue_result_t warmup_eq = ovrtx_step_with_stage(
            renderer_, render_products, 1.0 / 60.0, /*ordinal=*/1, &warmup_handle);
        ASSERT_API_SUCCESS(warmup_eq.status);
        docs_wait_no_errors(renderer_, warmup_eq.op_index);
        ovrtx_destroy_results(renderer_, warmup_handle);
    }

    ovrtx_step_result_handle_t step_handle = 0;
    ovrtx_enqueue_result_t enqueue_result = ovrtx_step_with_stage(
        renderer_, render_products, 1.0 / 60.0, /*ordinal=*/1, &step_handle);
    ASSERT_API_SUCCESS(enqueue_result.status);
    docs_wait_no_errors(renderer_, enqueue_result.op_index);

    ovrtx_render_product_set_outputs_t outputs{};
    ovrtx_result_t result =
        ovrtx_fetch_results(renderer_, step_handle, ovrtx_timeout_infinite, &outputs);
    ASSERT_API_SUCCESS(result.status);

    ovrtx_map_output_description_t map_desc = {};
    map_desc.device_type = OVRTX_MAP_DEVICE_TYPE_CPU;
    ovrtx_cuda_sync_t no_sync = {};

    ovrtx_render_var_output_handle_t id_map_handle = find_output(outputs, "SemanticIdMap");
    ovrtx_render_var_output_handle_t segmentation_handle =
        find_output(outputs, "SemanticSegmentation");
    ASSERT_NE(id_map_handle, OVRTX_INVALID_HANDLE);
    ASSERT_NE(segmentation_handle, OVRTX_INVALID_HANDLE);

    ovrtx_render_var_output_t id_map_output = {};
    result = ovrtx_map_render_var_output(
        renderer_, id_map_handle, &map_desc, ovrtx_timeout_infinite, &id_map_output);
    ASSERT_API_SUCCESS(result.status);
    std::map<uint32_t, std::string> semantic_id_map =
        decode_semantic_id_map(*id_map_output.tensors[0].dl);
    ovrtx_unmap_render_var_output(renderer_, id_map_output.map_handle, no_sync);

    std::map<std::string, uint32_t> ids_by_label;
    for (auto const& [semantic_id, label] : semantic_id_map) {
        ids_by_label[label] = semantic_id;
    }
    ASSERT_TRUE(ids_by_label.count("class: logo;"));
    ASSERT_TRUE(ids_by_label.count("class: ground;"));
    uint32_t const logo_id = ids_by_label["class: logo;"];
    uint32_t const ground_id = ids_by_label["class: ground;"];

    ovrtx_render_var_output_t segmentation_output = {};
    result = ovrtx_map_render_var_output(
        renderer_, segmentation_handle, &map_desc, ovrtx_timeout_infinite, &segmentation_output);
    ASSERT_API_SUCCESS(result.status);
    DLTensor const& segmentation_tensor = *segmentation_output.tensors[0].dl;
    EXPECT_EQ(segmentation_tensor.shape[0], HEIGHT);
    EXPECT_EQ(segmentation_tensor.shape[1], WIDTH);
    std::set<uint32_t> semantic_ids_in_image =
        collect_semantic_segmentation_ids(segmentation_tensor);
    ovrtx_unmap_render_var_output(renderer_, segmentation_output.map_handle, no_sync);

    EXPECT_TRUE(semantic_ids_in_image.count(logo_id));
    EXPECT_TRUE(semantic_ids_in_image.count(ground_id));

    ovrtx_destroy_results(renderer_, step_handle);
}
