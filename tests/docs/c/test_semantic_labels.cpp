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

#include <array>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <stdexcept>

static constexpr int WIDTH = 1280;
static constexpr int HEIGHT = 720;

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
static std::map<std::array<uint32_t, 4>, std::string> decode_semantic_id_map(ovrtx_render_var_output_t const& output) {
    auto field = [&](char const* name, uint8_t bits, int ndim) -> DLTensor const& {
        for (size_t i = 0; i < output.num_tensors; ++i) {
            auto const& entry = output.tensors[i];
            if (!entry.name || !entry.name->ptr || entry.name->length != strlen(name) ||
                memcmp(entry.name->ptr, name, entry.name->length)) continue;
            if (!entry.dl || entry.dl->device.device_type != kDLCPU || entry.dl->dtype.code != kDLUInt ||
                entry.dl->dtype.bits != bits || entry.dl->dtype.lanes != 1 || entry.dl->ndim != ndim ||
                !entry.dl->shape) throw std::invalid_argument("Invalid semantic identifier field");
            for (int dim = 0; dim < ndim; ++dim)
                if (entry.dl->shape[dim] < 0 || (entry.dl->strides && entry.dl->strides[dim] < 0))
                    throw std::invalid_argument("Invalid semantic identifier shape or stride");
            return *entry.dl;
        }
        throw std::invalid_argument("Missing named semantic identifier field");
    };
    DLTensor const& ids = field("id", 32, 2);
    DLTensor const& offsets = field("label_offsets", 64, 1);
    DLTensor const& data = field("label_data", 8, 1);
    if (ids.shape[1] != 4 || offsets.shape[0] < 1 || offsets.shape[0] - 1 != ids.shape[0] ||
        (ids.shape[0] && !ids.data) || !offsets.data || (data.shape[0] && !data.data) ||
        (data.strides && data.strides[0] != 1))
        throw std::invalid_argument("Invalid semantic identifier field shapes");
    auto offset = [&](int64_t index) {
        uint64_t value;
        size_t const stride = offsets.strides ? size_t(offsets.strides[0]) : 1;
        memcpy(&value, static_cast<uint8_t const*>(offsets.data) + offsets.byte_offset +
                       size_t(index) * stride * sizeof(value), sizeof(value));
        return value;
    };
    if (offset(0) != 0 || offset(ids.shape[0]) != uint64_t(data.shape[0]))
        throw std::invalid_argument("Invalid semantic label spans");
    std::map<std::array<uint32_t, 4>, std::string> labels_by_id;
    for (int64_t i = 0; i < ids.shape[0]; ++i) {
        uint64_t const start = offset(i), end = offset(i + 1);
        if (start > end || end > uint64_t(data.shape[0]))
            throw std::invalid_argument("Invalid semantic label spans");
        std::array<uint32_t, 4> id{};
        for (size_t word = 0; word < 4; ++word) {
            size_t const index = size_t(i) * (ids.strides ? size_t(ids.strides[0]) : 4) +
                                 word * (ids.strides ? size_t(ids.strides[1]) : 1);
            memcpy(&id[word], static_cast<uint8_t const*>(ids.data) + ids.byte_offset + index * sizeof(uint32_t), 4);
        }
        char const* text = data.data ? static_cast<char const*>(data.data) + data.byte_offset + start : "";
        std::string label(text, size_t(end - start));
        trim_semantic_label(label);
        labels_by_id[id] = label;
    }
    return labels_by_id;
}

static std::set<std::array<uint32_t, 4>> collect_semantic_segmentation_ids(DLTensor const& tensor) {
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

    // Scalar class pixels occupy the first word of the full semantic map ID.
    std::set<std::array<uint32_t, 4>> ids;
    if (tensor.dtype.code == kDLUInt) {
        uint32_t const* values = reinterpret_cast<uint32_t const*>(base);
        for (int64_t y = 0; y < height; ++y) {
            for (int64_t x = 0; x < width; ++x) {
                ids.insert({values[y * stride_y + x * stride_x], 0, 0, 0});
            }
        }
    } else if (tensor.dtype.code == kDLInt) {
        int32_t const* values = reinterpret_cast<int32_t const*>(base);
        for (int64_t y = 0; y < height; ++y) {
            for (int64_t x = 0; x < width; ++x) {
                ids.insert({static_cast<uint32_t>(values[y * stride_y + x * stride_x]), 0, 0, 0});
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
        ovrtx_step_result_handle_t warmup_handle{};
        ovrtx_enqueue_result_t warmup_eq = ovrtx_step_with_stage(
            renderer_, render_products, 1.0 / 60.0, /*ordinal=*/1, &warmup_handle);
        ASSERT_API_SUCCESS(warmup_eq.status);
        docs_wait_no_errors(renderer_, warmup_eq.op_index);
        ovrtx_destroy_results(renderer_, warmup_handle);
    }

    ovrtx_step_result_handle_t step_handle{};
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

    ovrtx_render_var_output_handle_t id_map_handle = find_output(outputs, "/Render/SemanticCamera/SemanticIdMap");
    ovrtx_render_var_output_handle_t segmentation_handle =
        find_output(outputs, "/Render/SemanticCamera/SemanticSegmentation");
    ASSERT_NE(id_map_handle, OVRTX_INVALID_RENDER_VAR_OUTPUT_HANDLE);
    ASSERT_NE(segmentation_handle, OVRTX_INVALID_RENDER_VAR_OUTPUT_HANDLE);

    ovrtx_render_var_output_t id_map_output = {};
    result = ovrtx_map_render_var_output(
        renderer_, id_map_handle, &map_desc, ovrtx_timeout_infinite, &id_map_output);
    ASSERT_API_SUCCESS(result.status);
    std::map<std::array<uint32_t, 4>, std::string> semantic_id_map =
        decode_semantic_id_map(id_map_output);
    ovrtx_unmap_render_var_output(renderer_, id_map_output.map_handle, no_sync);

    std::map<std::string, std::array<uint32_t, 4>> ids_by_label;
    for (auto const& [semantic_id, label] : semantic_id_map) {
        ids_by_label[label] = semantic_id;
    }
    ASSERT_TRUE(ids_by_label.count("class: logo;"));
    ASSERT_TRUE(ids_by_label.count("class: ground;"));
    auto const logo_id = ids_by_label["class: logo;"];
    auto const ground_id = ids_by_label["class: ground;"];

    ovrtx_render_var_output_t segmentation_output = {};
    result = ovrtx_map_render_var_output(
        renderer_, segmentation_handle, &map_desc, ovrtx_timeout_infinite, &segmentation_output);
    ASSERT_API_SUCCESS(result.status);
    DLTensor const& segmentation_tensor = *segmentation_output.tensors[0].dl;
    EXPECT_EQ(segmentation_tensor.shape[0], HEIGHT);
    EXPECT_EQ(segmentation_tensor.shape[1], WIDTH);
    std::set<std::array<uint32_t, 4>> semantic_ids_in_image =
        collect_semantic_segmentation_ids(segmentation_tensor);
    ovrtx_unmap_render_var_output(renderer_, segmentation_output.map_handle, no_sync);

    EXPECT_TRUE(semantic_ids_in_image.count(logo_id));
    EXPECT_TRUE(semantic_ids_in_image.count(ground_id));

    ovrtx_destroy_results(renderer_, step_handle);
}


TEST(SemanticLabelsDecoding, NamedFieldsAndBounds) {
    uint32_t ids_data[12] = {99, 7, 0, 0, 0, 99, 99, 9, 0, 0, 0, 99};
    char labels[] = "class: logo; class: caf\xc3\xa9; ";
    uint64_t offsets_data[3] = {0, 13, sizeof(labels) - 1};
    int64_t ids_shape[2] = {2, 4}, ids_strides[2] = {6, 1};
    int64_t offsets_shape[1] = {3}, data_shape[1] = {sizeof(labels) - 1};
    DLTensor ids{ids_data, {kDLCPU, 0}, 2, {kDLUInt, 32, 1}, ids_shape, ids_strides, 4};
    DLTensor offsets{offsets_data, {kDLCPU, 0}, 1, {kDLUInt, 64, 1}, offsets_shape, nullptr, 0};
    DLTensor data{labels, {kDLCPU, 0}, 1, {kDLUInt, 8, 1}, data_shape, nullptr, 0};
    ovx_string_t names[] = {{"label_data", 10}, {"id", 2}, {"label_offsets", 13}};
    // Deliberately change slot order: names, not tensor zero, define the contract.
    ovrtx_render_var_tensor_t fields[] = {{&data, &names[0], nullptr}, {&ids, &names[1], nullptr},
                                        {&offsets, &names[2], nullptr}};
    ovrtx_render_var_output_t output{};
    output.num_tensors = 3; output.tensors = fields;
    auto decoded = decode_semantic_id_map(output);
    EXPECT_EQ(decoded.at({7, 0, 0, 0}), "class: logo;");
    EXPECT_EQ(decoded.at({9, 0, 0, 0}), "class: caf\xc3\xa9;");
    offsets_data[2] = 1000;
    EXPECT_THROW(decode_semantic_id_map(output), std::invalid_argument);
    offsets_data[2] = sizeof(labels) - 1;
    ids_data[7] = 7; ids_data[8] = 2; ids_data[9] = 3; ids_data[10] = 4;
    decoded = decode_semantic_id_map(output);
    EXPECT_EQ(decoded.at({7, 0, 0, 0}), "class: logo;");
    EXPECT_EQ(decoded.at({7, 2, 3, 4}), "class: caf\xc3\xa9;");
    ids_shape[0] = 0; offsets_shape[0] = 1; data_shape[0] = 0;
    EXPECT_TRUE(decode_semantic_id_map(output).empty());
}
