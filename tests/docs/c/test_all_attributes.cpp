// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// Round-trip coverage for supported authored USD attribute types via the
// ovstage C API. Mirrors tests/docs/python/test_all_attributes.py — the
// scene is populated through ovstage_population and every read/write goes
// through ovstage_read_attributes / ovstage_write_attribute on an attached
// stage.

#include <gtest/gtest.h>
#include "helpers.h"

#include <cmath>
#include <cstdint>
#include <cstring>
#include <string>
#include <type_traits>
#include <vector>

namespace {

constexpr char kWorld[] = "/World";
constexpr char kExtentLeaf[] = "/World/ExtentTranslate/ExtentScale/ExtentLeaf";

DLDataType dl_type(uint8_t code, uint8_t bits, uint16_t lanes = 1) { return DLDataType{code, bits, lanes}; }

uint16_t half_from_float(float value) {
    uint32_t bits = 0;
    std::memcpy(&bits, &value, sizeof(bits));

    const uint32_t sign = (bits >> 16) & 0x8000u;
    int32_t exp = static_cast<int32_t>((bits >> 23) & 0xffu) - 127 + 15;
    uint32_t mantissa = bits & 0x7fffffu;

    if (exp <= 0) {
        if (exp < -10) {
            return static_cast<uint16_t>(sign);
        }
        mantissa = (mantissa | 0x800000u) >> (1 - exp);
        return static_cast<uint16_t>(sign | ((mantissa + 0x1000u) >> 13));
    }
    if (exp >= 31) {
        return static_cast<uint16_t>(sign | 0x7c00u);
    }
    return static_cast<uint16_t>(sign | (static_cast<uint32_t>(exp) << 10) | ((mantissa + 0x1000u) >> 13));
}

float half_to_float(uint16_t value) {
    const uint32_t sign = (static_cast<uint32_t>(value & 0x8000u)) << 16;
    uint32_t exp = (value >> 10) & 0x1fu;
    uint32_t mantissa = value & 0x03ffu;
    uint32_t bits = 0;

    if (exp == 0) {
        if (mantissa == 0) {
            bits = sign;
        } else {
            exp = 1;
            while ((mantissa & 0x0400u) == 0) {
                mantissa <<= 1;
                --exp;
            }
            mantissa &= 0x03ffu;
            bits = sign | ((exp + 127 - 15) << 23) | (mantissa << 13);
        }
    } else if (exp == 31) {
        bits = sign | 0x7f800000u | (mantissa << 13);
    } else {
        bits = sign | ((exp + 127 - 15) << 23) | (mantissa << 13);
    }

    float out = 0.0f;
    std::memcpy(&out, &bits, sizeof(out));
    return out;
}

std::vector<uint16_t> half_values(std::initializer_list<float> values) {
    std::vector<uint16_t> out;
    out.reserve(values.size());
    for (float value : values) {
        out.push_back(half_from_float(value));
    }
    return out;
}

std::vector<uint8_t> bytes_of(char const *text) { return std::vector<uint8_t>(text, text + std::strlen(text)); }

uint64_t create_token(ovstage_instance_t *stage, char const *text) {
    path_dictionary_instance_t *pd = ovstage_get_path_dictionary(stage);
    EXPECT_NE(pd, nullptr);
    ovx_string_t source = ovx_str(text);
    ovx_token_t token = 0;
    EXPECT_EQ(path_dictionary_create_tokens_from_strings(pd, &source, 1, &token).status, OVX_API_SUCCESS);
    return token;
}

std::string token_to_string(ovstage_instance_t *stage, uint64_t token_value) {
    path_dictionary_instance_t *pd = ovstage_get_path_dictionary(stage);
    EXPECT_NE(pd, nullptr);
    ovx_token_t token = token_value;
    ovx_string_t text{};
    EXPECT_EQ(path_dictionary_get_strings_from_tokens(pd, &token, 1, &text).status, OVX_API_SUCCESS);
    return std::string(text.ptr, text.length);
}

template <typename T> std::vector<T> updated_values(std::vector<T> initial, DLDataType dtype) {
    for (T &value : initial) {
        if (dtype.code == kDLBool) {
            value = value ? T(0) : T(1);
        } else if (dtype.code == kDLFloat && dtype.bits == 16) {
            value = static_cast<T>(half_from_float(half_to_float(static_cast<uint16_t>(value)) + 0.75f));
        } else if (dtype.code == kDLFloat) {
            value = static_cast<T>(value + T(0.75));
        } else {
            value = static_cast<T>(value + T(7));
        }
    }
    return initial;
}

template <typename T>
void expect_values_near(char const *label, std::vector<T> const &actual, std::vector<T> const &expected,
                        DLDataType dtype) {
    ASSERT_EQ(actual.size(), expected.size()) << label;
    for (size_t i = 0; i < actual.size(); ++i) {
        if (dtype.code == kDLFloat && dtype.bits == 16) {
            EXPECT_NEAR(half_to_float(static_cast<uint16_t>(actual[i])),
                        half_to_float(static_cast<uint16_t>(expected[i])), 1e-3f)
                << label << " element " << i;
        } else if constexpr (std::is_floating_point_v<T>) {
            const double tolerance = std::is_same_v<T, float> ? 1e-5 : 1e-8;
            EXPECT_NEAR(static_cast<double>(actual[i]), static_cast<double>(expected[i]), tolerance)
                << label << " element " << i;
        } else {
            EXPECT_EQ(actual[i], expected[i]) << label << " element " << i;
        }
    }
}

} // namespace

class AllAttributesTest : public DocsOvstageTestBase {
  protected:
    DOCS_OVSTAGE_TEST_SUITE(AllAttributesTest)

    // Each test authors a new state under `ordinal_ + 1` and then reads at
    // `latest(ordinal_)`. Populate seeds ordinal 1; write_values bumps ordinal
    // to N+1 and advances the write floor there.
    ovstage_ordinal_t ordinal_ = 1;

    void load_all_attributes() {
        std::string scene = get_docs_test_data_dir() + "/all-attributes.usda";
        docs_open_usd_file(scene.c_str(), /*ordinal=*/1);
        ordinal_ = 1;
    }

    // Read `attribute` off `prim` at latest(ordinal_) and copy the values into
    // `out` as a flat vector of T. Mirrors the pre-port ovrtx read_values<T>
    // helper — asserts is_array kind, one tensor per read, ndim=1, dtype
    // code/bits/lanes, and the expected element count so a backend regression
    // that flips shape/kind cannot silently masquerade as a value mismatch.
    // Copies via memcpy: DLPack guarantees the source data pointer is aligned
    // for its dtype, but reinterpret_cast<T const *>(base) through a uint8_t*
    // trail trips -fsanitize=alignment on ARM32.
    template <typename T>
    void read_values(char const *attribute, DLDataType dtype, bool is_array, size_t expected_elements,
                     std::vector<T> &out, char const *prim = kWorld) {
        DocsQueryAndToken q;
        docs_make_query_and_token(stage_, prim, attribute, &q);
        if (::testing::Test::HasFatalFailure()) return;

        ovstage_ordinal_range_t range{};
        range.end_ordinal = ordinal_;
        ovstage_read_handle_t read_handle = OVSTAGE_INVALID_READ_HANDLE;
        ovstage_enqueue_result_t eq =
            ovstage_read_attributes(stage_, q.query_handle, &q.attr_token, 1, range, &read_handle);
        ASSERT_EQ(eq.status, OVSTAGE_OK) << attribute << ": " << format_ovstage_last_error();
        docs_wait_ovstage_no_errors(stage_, eq.op_index);
        if (::testing::Test::HasFatalFailure()) {
            ovstage_release_read(stage_, read_handle);
            docs_release_query_and_token(stage_, &q);
            return;
        }

        out.clear();
        while (true) {
            ovstage_read_group_t group{};
            ovstage_api_status_t s =
                ovstage_fetch_read_next(stage_, read_handle, OVSTAGE_TIMEOUT_INFINITE, &group);
            if (s == OVSTAGE_ERROR_END_OF_ITERATION) break;
            ASSERT_EQ(s, OVSTAGE_OK) << attribute << ": " << format_ovstage_last_error();

            ASSERT_EQ(group.is_array, is_array) << attribute << ": is_array mismatch";
            ASSERT_GT(group.data.tensor_count, 0u) << attribute;
            if (::testing::Test::HasFatalFailure()) {
                ovstage_release_group(stage_, &group);
                break;
            }
            DLTensor const &t = group.data.tensors[0];
            ASSERT_EQ(t.ndim, 1) << attribute;
            ASSERT_EQ(t.dtype.code, dtype.code) << attribute;
            ASSERT_EQ(t.dtype.bits, dtype.bits) << attribute;
            ASSERT_EQ(t.dtype.lanes, dtype.lanes) << attribute;
            if (::testing::Test::HasFatalFailure()) {
                ovstage_release_group(stage_, &group);
                break;
            }

            size_t const value_count = static_cast<size_t>(t.shape[0]) * dtype.lanes;
            size_t const old_size = out.size();
            out.resize(old_size + value_count);
            uint8_t const *base = static_cast<uint8_t const *>(t.data) + t.byte_offset;
            std::memcpy(out.data() + old_size, base, value_count * sizeof(T));

            ovstage_release_group(stage_, &group);
        }

        if (!::testing::Test::HasFatalFailure()) {
            ASSERT_EQ(out.size(), expected_elements * dtype.lanes) << attribute;
        }

        ovstage_release_read(stage_, read_handle);
        docs_release_query_and_token(stage_, &q);
    }

    // `semantic` defaults to OVSTAGE_SEMANTIC_NONE because every attribute
    // exercised here already has its column semantic stamped by the initial
    // populate (per ovstage_api_types.h:705, "Geometric semantics stamp the
    // Fabric column's AttributeRole at creation and are surfaced back on
    // read"), and later writes with NONE preserve that stamp. The raw
    // `doc-write-usd-quatf-c` snippet elects to pass QUATERNION explicitly
    // as the idiomatic pattern for a fresh quaternion column; both paths
    // round-trip because the backend does not renormalize on QUATERNION.
    // Callers that need semantic overrides (TOKEN_ID, ASSET_STRING) still
    // pass them through this argument.
    template <typename T>
    void write_values(char const *attribute, DLDataType dtype, bool is_array, std::vector<T> const &values,
                      char const *prim = kWorld, ovstage_attribute_semantic_t semantic = OVSTAGE_SEMANTIC_NONE) {
        ASSERT_EQ(values.size() % dtype.lanes, 0u) << attribute;
        const size_t element_count = values.size() / dtype.lanes;

        DocsQueryAndToken q;
        docs_make_query_and_token(stage_, prim, attribute, &q);
        if (::testing::Test::HasFatalFailure()) return;

        int64_t write_shape[1] = {static_cast<int64_t>(element_count)};
        DLTensor write_tensor{};
        write_tensor.data = const_cast<T *>(values.data());
        write_tensor.device = {kDLCPU, 0};
        write_tensor.ndim = 1;
        write_tensor.dtype = dtype;
        write_tensor.shape = write_shape;

        ovstage_write_data_t write_data{};
        write_data.tensors = &write_tensor;
        write_data.tensor_count = 1;
        write_data.is_array = is_array;
        write_data.semantic = semantic;

        ovx_string_or_token_t attr_ref{};
        attr_ref.token = q.attr_token;

        const ovstage_ordinal_t next = ordinal_ + 1;
        ovstage_enqueue_result_t wq = ovstage_write_attribute(stage_, q.query_handle, attr_ref, next, write_data,
                                                              OVSTAGE_PRIM_MODE_UPSERT);
        ASSERT_EQ(wq.status, OVSTAGE_OK) << attribute << ": " << format_ovstage_last_error();
        docs_wait_ovstage_no_errors(stage_, wq.op_index);
        // Guard: a failing wait must not cascade into advance_write_floor +
        // ordinal_ bump — a stale ordinal_ makes every subsequent read in the
        // enclosing test observe old data and bury the root cause.
        if (!::testing::Test::HasFatalFailure()) {
            docs_ovstage_advance_write_floor(stage_, next);
            if (!::testing::Test::HasFatalFailure()) {
                ordinal_ = next;
            }
        }

        docs_release_query_and_token(stage_, &q);
    }

    template <typename T>
    void check_numeric_case(char const *attribute, DLDataType dtype, bool is_array, std::vector<T> const &initial,
                            bool skip_initial_usd_read = false) {
        const size_t expected_elements = initial.size() / dtype.lanes;
        std::vector<T> actual;
        if (!skip_initial_usd_read) {
            read_values(attribute, dtype, is_array, expected_elements, actual);
            if (::testing::Test::HasFatalFailure()) return;
            const std::string label = std::string(attribute) + " initial";
            expect_values_near(label.c_str(), actual, initial, dtype);
        }

        std::vector<T> updated = updated_values(initial, dtype);
        write_values(attribute, dtype, is_array, updated);
        if (::testing::Test::HasFatalFailure()) return;
        read_values(attribute, dtype, is_array, expected_elements, actual);
        if (::testing::Test::HasFatalFailure()) return;
        const std::string label = std::string(attribute) + " updated";
        expect_values_near(label.c_str(), actual, updated, dtype);
    }

    void check_token_case(char const *attribute, char const *initial, char const *updated, bool is_array = false,
                          char const *initial_b = nullptr, char const *updated_b = nullptr) {
        DLDataType dtype = dl_type(kDLUInt, 64, 1);
        const size_t expected_elements = is_array ? 2 : 1;

        std::vector<uint64_t> actual;
        read_values(attribute, dtype, is_array, expected_elements, actual);
        if (::testing::Test::HasFatalFailure()) return;
        EXPECT_EQ(token_to_string(stage_, actual[0]), initial);
        if (is_array) {
            EXPECT_EQ(token_to_string(stage_, actual[1]), initial_b);
        }

        std::vector<uint64_t> updated_tokens = {create_token(stage_, updated)};
        if (is_array) {
            updated_tokens.push_back(create_token(stage_, updated_b));
        }
        write_values(attribute, dtype, is_array, updated_tokens, kWorld, OVSTAGE_SEMANTIC_TOKEN_ID);
        if (::testing::Test::HasFatalFailure()) return;

        read_values(attribute, dtype, is_array, expected_elements, actual);
        if (::testing::Test::HasFatalFailure()) return;
        EXPECT_EQ(token_to_string(stage_, actual[0]), updated);
        if (is_array) {
            EXPECT_EQ(token_to_string(stage_, actual[1]), updated_b);
        }
    }

    // The linked ovstage package may predate the transitional scalar-asset
    // read contract: such packages omit populated scalar assets from
    // single-prim reads (the fetch ends without a group). The asset case
    // skips against such packages and activates once the linked package
    // serves the {kDLUInt, 64, 2} token pair; no test change is needed
    // when it does.
    void probe_asset_pair_contract(bool* available) {
        *available = false;

        DocsQueryAndToken q;
        docs_make_query_and_token(stage_, kWorld, "test:asset", &q);
        if (::testing::Test::HasFatalFailure()) return;

        ovstage_ordinal_range_t range{};
        range.end_ordinal = ordinal_;
        ovstage_read_handle_t read_handle = OVSTAGE_INVALID_READ_HANDLE;
        ovstage_enqueue_result_t eq =
            ovstage_read_attributes(stage_, q.query_handle, &q.attr_token, 1, range, &read_handle);
        ASSERT_EQ(eq.status, OVSTAGE_OK) << format_ovstage_last_error();
        docs_wait_ovstage_no_errors(stage_, eq.op_index);

        ovstage_read_group_t group{};
        if (ovstage_fetch_read_next(stage_, read_handle, OVSTAGE_TIMEOUT_INFINITE, &group) == OVSTAGE_OK) {
            if (group.data.tensor_count > 0) {
                DLDataType dtype = group.data.tensors[0].dtype;
                *available = dtype.code == kDLUInt && dtype.bits == 64 && dtype.lanes == 2;
            }
            ovstage_release_group(stage_, &group);
        }
        ovstage_release_read(stage_, read_handle);
        docs_release_query_and_token(stage_, &q);
    }

    void check_string_case() {
        DLDataType dtype = dl_type(kDLUInt, 8, 1);
        std::vector<uint8_t> actual;
        std::vector<uint8_t> initial = bytes_of("initial string");
        std::vector<uint8_t> updated = bytes_of("updated longer string");

        read_values("test:string", dtype, true, initial.size(), actual);
        if (::testing::Test::HasFatalFailure()) return;
        EXPECT_EQ(std::string(actual.begin(), actual.end()), "initial string");

        write_values("test:string", dtype, true, updated);
        if (::testing::Test::HasFatalFailure()) return;
        read_values("test:string", dtype, true, updated.size(), actual);
        if (::testing::Test::HasFatalFailure()) return;
        EXPECT_EQ(std::string(actual.begin(), actual.end()), "updated longer string");
    }

    // Assert that a given attribute name is not populated on any prim.
    // Mirrors the ovrtx version but issues an ovstage HAS-predicate query.
    void expect_attribute_not_populated(char const *attribute) {
        ovx_string_t attr_str = ovx_str(attribute);
        ovstage_predicate_t predicate{};
        predicate.attribute.string = attr_str;
        predicate.op = OVSTAGE_FILTER_OP_HAS;

        ovstage_filter_t filter{};
        filter.predicates = &predicate;
        filter.count = 1;

        ovstage_query_handle_t query_handle = OVSTAGE_INVALID_QUERY_HANDLE;
        ovstage_enqueue_result_t eq = ovstage_query(stage_, &filter, nullptr, 0, &query_handle);
        ASSERT_EQ(eq.status, OVSTAGE_OK) << attribute << ": " << format_ovstage_last_error();
        docs_wait_ovstage_no_errors(stage_, eq.op_index);

        ovstage_query_result_t qr{};
        ASSERT_EQ(ovstage_fetch_query_result(stage_, query_handle, OVSTAGE_TIMEOUT_INFINITE, &qr), OVSTAGE_OK)
            << attribute << ": " << format_ovstage_last_error();
        EXPECT_EQ(qr.total_prim_count, 0u) << attribute;
        ovstage_release_query_result(stage_, &qr);
        ovstage_release_query(stage_, query_handle);
    }
};

TEST_F(AllAttributesTest, SupportedAuthoredAttributesRoundTrip) {
    load_all_attributes();
    if (HasFatalFailure()) return;

    // The scalar-asset case is exercised by the read half of
    // AssetReadWriteSnippets; writing to a populated scalar asset attribute
    // is not supported in ovstage 0.1.x, so this test covers the other
    // authored attribute types.
    check_numeric_case<uint8_t>("test:bool", dl_type(kDLBool, 8), false, {1});
    check_numeric_case<uint8_t>("test:boolArray", dl_type(kDLBool, 8), true, {1, 0});
    check_numeric_case<double>("test:color3d", dl_type(kDLFloat, 64, 3), false, {1.1, 1.2, 1.3});
    check_numeric_case<double>("test:color3dArray", dl_type(kDLFloat, 64, 3), true, {1.1, 1.2, 1.3, 2.1, 2.2, 2.3});
    check_numeric_case<float>("test:color3f", dl_type(kDLFloat, 32, 3), false, {3.1f, 3.2f, 3.3f});
    check_numeric_case<float>("test:color3fArray", dl_type(kDLFloat, 32, 3), true,
                              {3.1f, 3.2f, 3.3f, 4.1f, 4.2f, 4.3f});
    check_numeric_case<uint16_t>("test:color3h", dl_type(kDLFloat, 16, 3), false, half_values({5.0f, 5.5f, 6.0f}));
    check_numeric_case<uint16_t>("test:color3hArray", dl_type(kDLFloat, 16, 3), true,
                                 half_values({5.0f, 5.5f, 6.0f, 6.5f, 7.0f, 7.5f}));
    check_numeric_case<double>("test:color4d", dl_type(kDLFloat, 64, 4), false, {7.1, 7.2, 7.3, 7.4});
    check_numeric_case<double>("test:color4dArray", dl_type(kDLFloat, 64, 4), true,
                               {7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4});
    check_numeric_case<float>("test:color4f", dl_type(kDLFloat, 32, 4), false, {9.1f, 9.2f, 9.3f, 9.4f});
    check_numeric_case<float>("test:color4fArray", dl_type(kDLFloat, 32, 4), true,
                              {9.1f, 9.2f, 9.3f, 9.4f, 10.1f, 10.2f, 10.3f, 10.4f});
    check_numeric_case<uint16_t>("test:color4h", dl_type(kDLFloat, 16, 4), false,
                                 half_values({11.0f, 11.5f, 12.0f, 12.5f}));
    check_numeric_case<uint16_t>("test:color4hArray", dl_type(kDLFloat, 16, 4), true,
                                 half_values({11.0f, 11.5f, 12.0f, 12.5f, 13.0f, 13.5f, 14.0f, 14.5f}));
    check_numeric_case<double>("test:double", dl_type(kDLFloat, 64), false, {15.25});
    check_numeric_case<double>("test:double2", dl_type(kDLFloat, 64, 2), false, {16.1, 16.2});
    check_numeric_case<double>("test:double2Array", dl_type(kDLFloat, 64, 2), true, {16.1, 16.2, 17.1, 17.2});
    check_numeric_case<double>("test:double3", dl_type(kDLFloat, 64, 3), false, {18.1, 18.2, 18.3});
    check_numeric_case<double>("test:double3Array", dl_type(kDLFloat, 64, 3), true,
                               {18.1, 18.2, 18.3, 19.1, 19.2, 19.3});
    check_numeric_case<double>("test:double4", dl_type(kDLFloat, 64, 4), false, {20.1, 20.2, 20.3, 20.4});
    check_numeric_case<double>("test:double4Array", dl_type(kDLFloat, 64, 4), true,
                               {20.1, 20.2, 20.3, 20.4, 21.1, 21.2, 21.3, 21.4});
    check_numeric_case<double>("test:doubleArray", dl_type(kDLFloat, 64), true, {22.1, 22.2});
    check_numeric_case<float>("test:float", dl_type(kDLFloat, 32), false, {23.5f});
    check_numeric_case<float>("test:float2", dl_type(kDLFloat, 32, 2), false, {24.1f, 24.2f});
    check_numeric_case<float>("test:float2Array", dl_type(kDLFloat, 32, 2), true, {24.1f, 24.2f, 25.1f, 25.2f});
    check_numeric_case<float>("test:float3Array", dl_type(kDLFloat, 32, 3), true,
                              {26.1f, 26.2f, 26.3f, 27.1f, 27.2f, 27.3f});
    check_numeric_case<float>("test:float4", dl_type(kDLFloat, 32, 4), false, {28.1f, 28.2f, 28.3f, 28.4f});
    check_numeric_case<float>("test:float4Array", dl_type(kDLFloat, 32, 4), true,
                              {28.1f, 28.2f, 28.3f, 28.4f, 29.1f, 29.2f, 29.3f, 29.4f});
    check_numeric_case<float>("test:floatArray", dl_type(kDLFloat, 32), true, {30.1f, 30.2f});
    check_numeric_case<double>("test:frame4d", dl_type(kDLFloat, 64, 16), false,
                               {1, 0, 0, 0, 0, 2, 0, 0, 0, 0, 3, 0, 4, 5, 6, 1});
    check_numeric_case<double>(
        "test:frame4dArray", dl_type(kDLFloat, 64, 16), true,
        {1, 0, 0, 0, 0, 2, 0, 0, 0, 0, 3, 0, 4, 5, 6, 1, 2, 0, 0, 0, 0, 3, 0, 0, 0, 0, 4, 0, 5, 6, 7, 1});
    check_numeric_case<uint16_t>("test:half", dl_type(kDLFloat, 16), false, half_values({31.5f}));
    check_numeric_case<uint16_t>("test:half2", dl_type(kDLFloat, 16, 2), false, half_values({32.0f, 32.5f}));
    check_numeric_case<uint16_t>("test:half2Array", dl_type(kDLFloat, 16, 2), true,
                                 half_values({32.0f, 32.5f, 33.0f, 33.5f}));
    check_numeric_case<uint16_t>("test:half3", dl_type(kDLFloat, 16, 3), false, half_values({34.0f, 34.5f, 35.0f}));
    check_numeric_case<uint16_t>("test:half3Array", dl_type(kDLFloat, 16, 3), true,
                                 half_values({34.0f, 34.5f, 35.0f, 35.5f, 36.0f, 36.5f}));
    check_numeric_case<uint16_t>("test:half4", dl_type(kDLFloat, 16, 4), false,
                                 half_values({37.0f, 37.5f, 38.0f, 38.5f}));
    check_numeric_case<uint16_t>("test:half4Array", dl_type(kDLFloat, 16, 4), true,
                                 half_values({37.0f, 37.5f, 38.0f, 38.5f, 39.0f, 39.5f, 40.0f, 40.5f}));
    check_numeric_case<uint16_t>("test:halfArray", dl_type(kDLFloat, 16), true, half_values({41.0f, 41.5f}));
    check_numeric_case<int32_t>("test:int", dl_type(kDLInt, 32), false, {-42});
    check_numeric_case<int32_t>("test:int2", dl_type(kDLInt, 32, 2), false, {-43, 44});
    check_numeric_case<int32_t>("test:int2Array", dl_type(kDLInt, 32, 2), true, {-43, 44, 45, -46});
    check_numeric_case<int32_t>("test:int3", dl_type(kDLInt, 32, 3), false, {-47, 48, -49});
    check_numeric_case<int32_t>("test:int3Array", dl_type(kDLInt, 32, 3), true, {-47, 48, -49, 50, -51, 52});
    check_numeric_case<int32_t>("test:int4", dl_type(kDLInt, 32, 4), false, {-53, 54, -55, 56});
    check_numeric_case<int32_t>("test:int4Array", dl_type(kDLInt, 32, 4), true,
                                {-53, 54, -55, 56, 57, -58, 59, -60});
    check_numeric_case<int64_t>("test:int64", dl_type(kDLInt, 64), false, {-6100000000LL});
    check_numeric_case<int64_t>("test:int64Array", dl_type(kDLInt, 64), true, {-6200000000LL, 6300000000LL});
    check_numeric_case<int32_t>("test:intArray", dl_type(kDLInt, 32), true, {-64, 65});
    check_numeric_case<double>("test:matrix2d", dl_type(kDLFloat, 64, 4), false, {1, 2, 3, 4});
    check_numeric_case<double>("test:matrix2dArray", dl_type(kDLFloat, 64, 4), true, {1, 2, 3, 4, 5, 6, 7, 8});
    check_numeric_case<double>("test:matrix3d", dl_type(kDLFloat, 64, 9), false, {1, 2, 3, 4, 5, 6, 7, 8, 9});
    check_numeric_case<double>("test:matrix3dArray", dl_type(kDLFloat, 64, 9), true,
                               {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18});
    check_numeric_case<double>("test:matrix4d", dl_type(kDLFloat, 64, 16), false,
                               {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16});
    check_numeric_case<double>("test:matrix4dArray", dl_type(kDLFloat, 64, 16), true,
                               {1,  2,  3,  4,  5,  6,  7,  8,  9,  10, 11, 12, 13, 14, 15, 16,
                                17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32});
    check_numeric_case<double>("test:normal3d", dl_type(kDLFloat, 64, 3), false, {66.1, 66.2, 66.3});
    check_numeric_case<double>("test:normal3dArray", dl_type(kDLFloat, 64, 3), true,
                               {66.1, 66.2, 66.3, 67.1, 67.2, 67.3});
    check_numeric_case<float>("test:normal3f", dl_type(kDLFloat, 32, 3), false, {68.1f, 68.2f, 68.3f});
    check_numeric_case<float>("test:normal3fArray", dl_type(kDLFloat, 32, 3), true,
                              {68.1f, 68.2f, 68.3f, 69.1f, 69.2f, 69.3f});
    check_numeric_case<uint16_t>("test:normal3h", dl_type(kDLFloat, 16, 3), false, half_values({70.0f, 70.5f, 71.0f}));
    check_numeric_case<uint16_t>("test:normal3hArray", dl_type(kDLFloat, 16, 3), true,
                                 half_values({70.0f, 70.5f, 71.0f, 71.5f, 72.0f, 72.5f}));
    check_numeric_case<double>("test:point3d", dl_type(kDLFloat, 64, 3), false, {73.1, 73.2, 73.3});
    check_numeric_case<double>("test:point3dArray", dl_type(kDLFloat, 64, 3), true,
                               {73.1, 73.2, 73.3, 74.1, 74.2, 74.3});
    check_numeric_case<float>("test:point3f", dl_type(kDLFloat, 32, 3), false, {75.1f, 75.2f, 75.3f});
    check_numeric_case<float>("test:point3fArray", dl_type(kDLFloat, 32, 3), true,
                              {75.1f, 75.2f, 75.3f, 76.1f, 76.2f, 76.3f});
    check_numeric_case<uint16_t>("test:point3h", dl_type(kDLFloat, 16, 3), false, half_values({77.0f, 77.5f, 78.0f}));
    check_numeric_case<uint16_t>("test:point3hArray", dl_type(kDLFloat, 16, 3), true,
                                 half_values({77.0f, 77.5f, 78.0f, 78.5f, 79.0f, 79.5f}));
    check_numeric_case<double>("test:quatd", dl_type(kDLFloat, 64, 4), false, {80.1, 80.2, 80.3, 1});
    check_numeric_case<double>("test:quatdArray", dl_type(kDLFloat, 64, 4), true,
                               {80.1, 80.2, 80.3, 1, 81.1, 81.2, 81.3, 1});
    check_numeric_case<float>("test:quatf", dl_type(kDLFloat, 32, 4), false, {82.1f, 82.2f, 82.3f, 1.0f});
    check_numeric_case<float>("test:quatfArray", dl_type(kDLFloat, 32, 4), true,
                              {82.1f, 82.2f, 82.3f, 1.0f, 83.1f, 83.2f, 83.3f, 1.0f});
    check_numeric_case<uint16_t>("test:quath", dl_type(kDLFloat, 16, 4), false,
                                 half_values({84.0f, 84.5f, 85.0f, 1.0f}));
    check_numeric_case<uint16_t>("test:quathArray", dl_type(kDLFloat, 16, 4), true,
                                 half_values({84.0f, 84.5f, 85.0f, 1.0f, 85.5f, 86.0f, 86.5f, 1.0f}));
    check_string_case();
    check_numeric_case<float>("test:texCoord2f", dl_type(kDLFloat, 32, 2), false, {87.1f, 87.2f});
    check_numeric_case<float>("test:texCoord2fArray", dl_type(kDLFloat, 32, 2), true,
                              {87.1f, 87.2f, 88.1f, 88.2f});
    check_token_case("test:token", "initialToken", "updatedToken");
    check_token_case("test:tokenArray", "initialTokenA", "updatedTokenA", true, "initialTokenB", "updatedTokenB");
    check_numeric_case<uint8_t>("test:uchar", dl_type(kDLUInt, 8), false, {91});
    check_numeric_case<uint8_t>("test:ucharArray", dl_type(kDLUInt, 8), true, {92, 93});
    check_numeric_case<uint32_t>("test:uint", dl_type(kDLUInt, 32), false, {94});
    check_numeric_case<uint64_t>("test:uint64", dl_type(kDLUInt, 64), false, {9500000000ULL});
    check_numeric_case<uint64_t>("test:uint64Array", dl_type(kDLUInt, 64), true, {9600000000ULL, 9700000000ULL});
    check_numeric_case<uint32_t>("test:uintArray", dl_type(kDLUInt, 32), true, {98, 99});
    check_numeric_case<double>("test:vector3d", dl_type(kDLFloat, 64, 3), false, {100.1, 100.2, 100.3});
    check_numeric_case<double>("test:vector3dArray", dl_type(kDLFloat, 64, 3), true,
                               {100.1, 100.2, 100.3, 101.1, 101.2, 101.3});
    check_numeric_case<float>("test:vector3f", dl_type(kDLFloat, 32, 3), false, {102.1f, 102.2f, 102.3f});
    check_numeric_case<float>("test:vector3fArray", dl_type(kDLFloat, 32, 3), true,
                              {102.1f, 102.2f, 102.3f, 103.1f, 103.2f, 103.3f});
    check_numeric_case<uint16_t>("test:vector3h", dl_type(kDLFloat, 16, 3), false,
                                 half_values({104.0f, 104.5f, 105.0f}));
    check_numeric_case<uint16_t>("test:vector3hArray", dl_type(kDLFloat, 16, 3), true,
                                 half_values({104.0f, 104.5f, 105.0f, 105.5f, 106.0f, 106.5f}));
}

TEST_F(AllAttributesTest, ScalarFloat3PopulationBugIsExplicit) {
    load_all_attributes();
    if (HasFatalFailure()) return;

    DLDataType dtype = dl_type(kDLFloat, 32, 3);
    std::vector<float> values;
    read_values("test:float3", dtype, false, 1, values);
    if (HasFatalFailure()) return;
    expect_values_near("test:float3 populated bug value", values, std::vector<float>{0.0f, 0.0f, 0.0f}, dtype);

    write_values("test:float3", dtype, false, std::vector<float>{26.85f, 26.95f, 27.05f});
    if (HasFatalFailure()) return;
    read_values("test:float3", dtype, false, 1, values);
    if (HasFatalFailure()) return;
    expect_values_near("test:float3 updated", values, std::vector<float>{26.85f, 26.95f, 27.05f}, dtype);
}

TEST_F(AllAttributesTest, UnsupportedAuthoredAttributesAreNotPopulated) {
    load_all_attributes();
    if (HasFatalFailure()) return;

    expect_attribute_not_populated("test:assetArray");
    expect_attribute_not_populated("test:rel");
    expect_attribute_not_populated("test:relArray");
    expect_attribute_not_populated("test:stringArray");
    expect_attribute_not_populated("test:timecode");
    expect_attribute_not_populated("test:timecodeArray");
}

TEST_F(AllAttributesTest, RawReadWriteSnippets) {
    load_all_attributes();
    if (HasFatalFailure()) return;

    // Per-attribute snippets below: each shows the raw ovstage_read_attributes /
    // ovstage_write_attribute + DLTensor pattern for a single authored USD
    // type. Query and interned attribute-token setup lives outside the snippet
    // block so the quote focuses on the read/write call itself.
    DocsQueryAndToken q_float;
    docs_make_query_and_token(stage_, kWorld, "test:float", &q_float);
    if (HasFatalFailure()) return;
    ovx_string_or_token_t float_attr_ref{};
    float_attr_ref.token = q_float.attr_token;

    // [snippet:doc-read-usd-float-c]
    ovstage_ordinal_range_t float_range{};
    float_range.end_ordinal = ordinal_;

    ovstage_read_handle_t float_read_handle = OVSTAGE_INVALID_READ_HANDLE;
    ovstage_enqueue_result_t float_read_eq = ovstage_read_attributes(
        stage_, q_float.query_handle, &q_float.attr_token, 1, float_range, &float_read_handle);
    ASSERT_EQ(float_read_eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, float_read_eq.op_index);

    ovstage_read_group_t float_group{};
    ASSERT_EQ(ovstage_fetch_read_next(stage_, float_read_handle, OVSTAGE_TIMEOUT_INFINITE, &float_group), OVSTAGE_OK)
        << format_ovstage_last_error();
    ASSERT_GT(float_group.data.tensor_count, 0u);
    DLTensor const &float_tensor = float_group.data.tensors[0];
    float const *float_data =
        reinterpret_cast<float const *>(static_cast<uint8_t const *>(float_tensor.data) + float_tensor.byte_offset);
    std::vector<float> float_values(float_data, float_data + float_tensor.shape[0] * float_tensor.dtype.lanes);
    ovstage_release_group(stage_, &float_group);
    ovstage_release_read(stage_, float_read_handle);
    // [/snippet:doc-read-usd-float-c]
    expect_values_near("test:float", float_values, std::vector<float>{23.5f}, dl_type(kDLFloat, 32, 1));

    // [snippet:doc-write-usd-float-c]
    float updated_float[] = {24.25f};
    int64_t float_shape[1] = {1};
    DLTensor float_write_tensor{};
    float_write_tensor.data = updated_float;
    float_write_tensor.device = {kDLCPU, 0};
    float_write_tensor.ndim = 1;
    float_write_tensor.dtype = {kDLFloat, 32, 1};
    float_write_tensor.shape = float_shape;

    ovstage_write_data_t float_write_data{};
    float_write_data.tensors = &float_write_tensor;
    float_write_data.tensor_count = 1;
    float_write_data.is_array = false;

    ovstage_ordinal_t float_write_ordinal = ordinal_ + 1;
    ovstage_enqueue_result_t float_write_eq = ovstage_write_attribute(
        stage_, q_float.query_handle, float_attr_ref, float_write_ordinal, float_write_data, OVSTAGE_PRIM_MODE_UPSERT);
    ASSERT_EQ(float_write_eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, float_write_eq.op_index);
    docs_ovstage_advance_write_floor(stage_, float_write_ordinal);
    ordinal_ = float_write_ordinal;  // advance caller's tracked cursor
    // [/snippet:doc-write-usd-float-c]
    docs_release_query_and_token(stage_, &q_float);

    read_values("test:float", dl_type(kDLFloat, 32, 1), false, 1, float_values);
    expect_values_near("test:float updated", float_values, std::vector<float>{24.25f}, dl_type(kDLFloat, 32, 1));

    DocsQueryAndToken q_point3f;
    docs_make_query_and_token(stage_, kWorld, "test:point3f", &q_point3f);
    if (HasFatalFailure()) return;
    ovx_string_or_token_t point3f_attr_ref{};
    point3f_attr_ref.token = q_point3f.attr_token;

    // [snippet:doc-read-usd-point3f-c]
    ovstage_ordinal_range_t point3f_range{};
    point3f_range.end_ordinal = ordinal_;

    ovstage_read_handle_t point3f_read_handle = OVSTAGE_INVALID_READ_HANDLE;
    ovstage_enqueue_result_t point3f_read_eq = ovstage_read_attributes(
        stage_, q_point3f.query_handle, &q_point3f.attr_token, 1, point3f_range, &point3f_read_handle);
    ASSERT_EQ(point3f_read_eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, point3f_read_eq.op_index);

    ovstage_read_group_t point3f_group{};
    ASSERT_EQ(ovstage_fetch_read_next(stage_, point3f_read_handle, OVSTAGE_TIMEOUT_INFINITE, &point3f_group), OVSTAGE_OK)
        << format_ovstage_last_error();
    ASSERT_GT(point3f_group.data.tensor_count, 0u);
    DLTensor const &point3f_tensor = point3f_group.data.tensors[0];
    // Scalar per-prim point3f: shape=[1], dtype.lanes=3 → 3 floats per prim.
    float const *point3f_data = reinterpret_cast<float const *>(static_cast<uint8_t const *>(point3f_tensor.data) +
                                                                point3f_tensor.byte_offset);
    std::vector<float> point3f_values(point3f_data,
                                      point3f_data + point3f_tensor.shape[0] * point3f_tensor.dtype.lanes);
    ovstage_release_group(stage_, &point3f_group);
    ovstage_release_read(stage_, point3f_read_handle);
    // [/snippet:doc-read-usd-point3f-c]
    expect_values_near("test:point3f", point3f_values, std::vector<float>{75.1f, 75.2f, 75.3f},
                       dl_type(kDLFloat, 32, 3));

    // [snippet:doc-write-usd-point3f-c]
    float updated_point3f[] = {75.85f, 75.95f, 76.05f};
    int64_t point3f_shape[1] = {1};
    DLTensor point3f_write_tensor{};
    point3f_write_tensor.data = updated_point3f;
    point3f_write_tensor.device = {kDLCPU, 0};
    point3f_write_tensor.ndim = 1;
    point3f_write_tensor.dtype = {kDLFloat, 32, 3};
    point3f_write_tensor.shape = point3f_shape;

    ovstage_write_data_t point3f_write_data{};
    point3f_write_data.tensors = &point3f_write_tensor;
    point3f_write_data.tensor_count = 1;
    point3f_write_data.is_array = false;

    ovstage_ordinal_t point3f_write_ordinal = ordinal_ + 1;
    ovstage_enqueue_result_t point3f_write_eq = ovstage_write_attribute(
        stage_, q_point3f.query_handle, point3f_attr_ref, point3f_write_ordinal, point3f_write_data,
        OVSTAGE_PRIM_MODE_UPSERT);
    ASSERT_EQ(point3f_write_eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, point3f_write_eq.op_index);
    docs_ovstage_advance_write_floor(stage_, point3f_write_ordinal);
    ordinal_ = point3f_write_ordinal;  // advance caller's tracked cursor
    // [/snippet:doc-write-usd-point3f-c]
    docs_release_query_and_token(stage_, &q_point3f);

    read_values("test:point3f", dl_type(kDLFloat, 32, 3), false, 1, point3f_values);
    expect_values_near("test:point3f updated", point3f_values, std::vector<float>{75.85f, 75.95f, 76.05f},
                       dl_type(kDLFloat, 32, 3));

    DocsQueryAndToken q_point3f_arr;
    docs_make_query_and_token(stage_, kWorld, "test:point3fArray", &q_point3f_arr);
    if (HasFatalFailure()) return;
    ovx_string_or_token_t point3f_array_attr_ref{};
    point3f_array_attr_ref.token = q_point3f_arr.attr_token;

    // [snippet:doc-read-usd-point3f-array-c]
    ovstage_ordinal_range_t point3f_array_range{};
    point3f_array_range.end_ordinal = ordinal_;

    ovstage_read_handle_t point3f_array_read_handle = OVSTAGE_INVALID_READ_HANDLE;
    ovstage_enqueue_result_t point3f_array_read_eq =
        ovstage_read_attributes(stage_, q_point3f_arr.query_handle, &q_point3f_arr.attr_token, 1,
                                point3f_array_range, &point3f_array_read_handle);
    ASSERT_EQ(point3f_array_read_eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, point3f_array_read_eq.op_index);

    ovstage_read_group_t point3f_array_group{};
    ASSERT_EQ(ovstage_fetch_read_next(stage_, point3f_array_read_handle, OVSTAGE_TIMEOUT_INFINITE, &point3f_array_group),
              OVSTAGE_OK)
        << format_ovstage_last_error();
    ASSERT_TRUE(point3f_array_group.is_array);
    ASSERT_GT(point3f_array_group.data.tensor_count, 0u);
    DLTensor const &point3f_array_tensor = point3f_array_group.data.tensors[0];
    // Array of point3f: shape=[N], dtype.lanes=3 → N tuples of 3 floats.
    float const *point3f_array_data = reinterpret_cast<float const *>(
        static_cast<uint8_t const *>(point3f_array_tensor.data) + point3f_array_tensor.byte_offset);
    std::vector<float> point3f_array_values(
        point3f_array_data, point3f_array_data + point3f_array_tensor.shape[0] * point3f_array_tensor.dtype.lanes);
    ovstage_release_group(stage_, &point3f_array_group);
    ovstage_release_read(stage_, point3f_array_read_handle);
    // [/snippet:doc-read-usd-point3f-array-c]
    expect_values_near("test:point3fArray", point3f_array_values,
                       std::vector<float>{75.1f, 75.2f, 75.3f, 76.1f, 76.2f, 76.3f}, dl_type(kDLFloat, 32, 3));

    // [snippet:doc-write-usd-point3f-array-c]
    float updated_point3f_array[] = {75.85f, 75.95f, 76.05f, 76.85f, 76.95f, 77.05f};
    int64_t point3f_array_shape[1] = {2};
    DLTensor point3f_array_write_tensor{};
    point3f_array_write_tensor.data = updated_point3f_array;
    point3f_array_write_tensor.device = {kDLCPU, 0};
    point3f_array_write_tensor.ndim = 1;
    point3f_array_write_tensor.dtype = {kDLFloat, 32, 3};
    point3f_array_write_tensor.shape = point3f_array_shape;

    ovstage_write_data_t point3f_array_write_data{};
    point3f_array_write_data.tensors = &point3f_array_write_tensor;
    point3f_array_write_data.tensor_count = 1;
    point3f_array_write_data.is_array = true;

    ovstage_ordinal_t point3f_array_write_ordinal = ordinal_ + 1;
    ovstage_enqueue_result_t point3f_array_write_eq = ovstage_write_attribute(
        stage_, q_point3f_arr.query_handle, point3f_array_attr_ref, point3f_array_write_ordinal,
        point3f_array_write_data, OVSTAGE_PRIM_MODE_UPSERT);
    ASSERT_EQ(point3f_array_write_eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, point3f_array_write_eq.op_index);
    docs_ovstage_advance_write_floor(stage_, point3f_array_write_ordinal);
    ordinal_ = point3f_array_write_ordinal;  // advance caller's tracked cursor
    // [/snippet:doc-write-usd-point3f-array-c]
    docs_release_query_and_token(stage_, &q_point3f_arr);

    read_values("test:point3fArray", dl_type(kDLFloat, 32, 3), true, 2, point3f_array_values);
    expect_values_near("test:point3fArray updated", point3f_array_values,
                       std::vector<float>{75.85f, 75.95f, 76.05f, 76.85f, 76.95f, 77.05f}, dl_type(kDLFloat, 32, 3));

    DocsQueryAndToken q_matrix4d;
    docs_make_query_and_token(stage_, kWorld, "test:matrix4d", &q_matrix4d);
    if (HasFatalFailure()) return;
    ovx_string_or_token_t matrix4d_attr_ref{};
    matrix4d_attr_ref.token = q_matrix4d.attr_token;

    // [snippet:doc-read-usd-matrix4d-c]
    ovstage_ordinal_range_t matrix4d_range{};
    matrix4d_range.end_ordinal = ordinal_;

    ovstage_read_handle_t matrix4d_read_handle = OVSTAGE_INVALID_READ_HANDLE;
    ovstage_enqueue_result_t matrix4d_read_eq = ovstage_read_attributes(
        stage_, q_matrix4d.query_handle, &q_matrix4d.attr_token, 1, matrix4d_range, &matrix4d_read_handle);
    ASSERT_EQ(matrix4d_read_eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, matrix4d_read_eq.op_index);

    ovstage_read_group_t matrix4d_group{};
    ASSERT_EQ(ovstage_fetch_read_next(stage_, matrix4d_read_handle, OVSTAGE_TIMEOUT_INFINITE, &matrix4d_group),
              OVSTAGE_OK)
        << format_ovstage_last_error();
    ASSERT_GT(matrix4d_group.data.tensor_count, 0u);
    DLTensor const &matrix4d_tensor = matrix4d_group.data.tensors[0];
    // Per-prim 4x4 double matrix: shape=[1], dtype.lanes=16.
    double const *matrix4d_data = reinterpret_cast<double const *>(
        static_cast<uint8_t const *>(matrix4d_tensor.data) + matrix4d_tensor.byte_offset);
    std::vector<double> matrix4d_values(matrix4d_data,
                                        matrix4d_data + matrix4d_tensor.shape[0] * matrix4d_tensor.dtype.lanes);
    ovstage_release_group(stage_, &matrix4d_group);
    ovstage_release_read(stage_, matrix4d_read_handle);
    // [/snippet:doc-read-usd-matrix4d-c]
    expect_values_near("test:matrix4d", matrix4d_values,
                       std::vector<double>{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16},
                       dl_type(kDLFloat, 64, 16));

    // [snippet:doc-write-usd-matrix4d-c]
    double updated_matrix4d[] = {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17};
    int64_t matrix4d_shape[1] = {1};
    DLTensor matrix4d_write_tensor{};
    matrix4d_write_tensor.data = updated_matrix4d;
    matrix4d_write_tensor.device = {kDLCPU, 0};
    matrix4d_write_tensor.ndim = 1;
    matrix4d_write_tensor.dtype = {kDLFloat, 64, 16};
    matrix4d_write_tensor.shape = matrix4d_shape;

    ovstage_write_data_t matrix4d_write_data{};
    matrix4d_write_data.tensors = &matrix4d_write_tensor;
    matrix4d_write_data.tensor_count = 1;
    matrix4d_write_data.is_array = false;

    ovstage_ordinal_t matrix4d_write_ordinal = ordinal_ + 1;
    ovstage_enqueue_result_t matrix4d_write_eq = ovstage_write_attribute(
        stage_, q_matrix4d.query_handle, matrix4d_attr_ref, matrix4d_write_ordinal, matrix4d_write_data,
        OVSTAGE_PRIM_MODE_UPSERT);
    ASSERT_EQ(matrix4d_write_eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, matrix4d_write_eq.op_index);
    docs_ovstage_advance_write_floor(stage_, matrix4d_write_ordinal);
    ordinal_ = matrix4d_write_ordinal;  // advance caller's tracked cursor
    // [/snippet:doc-write-usd-matrix4d-c]
    docs_release_query_and_token(stage_, &q_matrix4d);

    read_values("test:matrix4d", dl_type(kDLFloat, 64, 16), false, 1, matrix4d_values);
    expect_values_near("test:matrix4d updated", matrix4d_values,
                       std::vector<double>{2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17},
                       dl_type(kDLFloat, 64, 16));

    DocsQueryAndToken q_quatf;
    docs_make_query_and_token(stage_, kWorld, "test:quatf", &q_quatf);
    if (HasFatalFailure()) return;
    ovx_string_or_token_t quatf_attr_ref{};
    quatf_attr_ref.token = q_quatf.attr_token;

    // [snippet:doc-read-usd-quatf-c]
    ovstage_ordinal_range_t quatf_range{};
    quatf_range.end_ordinal = ordinal_;

    ovstage_read_handle_t quatf_read_handle = OVSTAGE_INVALID_READ_HANDLE;
    ovstage_enqueue_result_t quatf_read_eq = ovstage_read_attributes(
        stage_, q_quatf.query_handle, &q_quatf.attr_token, 1, quatf_range, &quatf_read_handle);
    ASSERT_EQ(quatf_read_eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, quatf_read_eq.op_index);

    ovstage_read_group_t quatf_group{};
    ASSERT_EQ(ovstage_fetch_read_next(stage_, quatf_read_handle, OVSTAGE_TIMEOUT_INFINITE, &quatf_group), OVSTAGE_OK)
        << format_ovstage_last_error();
    ASSERT_GT(quatf_group.data.tensor_count, 0u);
    DLTensor const &quatf_tensor = quatf_group.data.tensors[0];
    // Quaternion (i, j, k, real): shape=[1], dtype.lanes=4.
    float const *quatf_data = reinterpret_cast<float const *>(static_cast<uint8_t const *>(quatf_tensor.data) +
                                                              quatf_tensor.byte_offset);
    std::vector<float> quatf_values(quatf_data, quatf_data + quatf_tensor.shape[0] * quatf_tensor.dtype.lanes);
    ovstage_release_group(stage_, &quatf_group);
    ovstage_release_read(stage_, quatf_read_handle);
    // [/snippet:doc-read-usd-quatf-c]
    expect_values_near("test:quatf", quatf_values, std::vector<float>{82.1f, 82.2f, 82.3f, 1.0f},
                       dl_type(kDLFloat, 32, 4));

    // [snippet:doc-write-usd-quatf-c]
    float updated_quatf[] = {82.85f, 82.95f, 83.05f, 1.75f};
    int64_t quatf_shape[1] = {1};
    DLTensor quatf_write_tensor{};
    quatf_write_tensor.data = updated_quatf;
    quatf_write_tensor.device = {kDLCPU, 0};
    quatf_write_tensor.ndim = 1;
    quatf_write_tensor.dtype = {kDLFloat, 32, 4};
    quatf_write_tensor.shape = quatf_shape;

    ovstage_write_data_t quatf_write_data{};
    quatf_write_data.tensors = &quatf_write_tensor;
    quatf_write_data.tensor_count = 1;
    quatf_write_data.is_array = false;
    quatf_write_data.semantic = OVSTAGE_SEMANTIC_QUATERNION;

    ovstage_ordinal_t quatf_write_ordinal = ordinal_ + 1;
    ovstage_enqueue_result_t quatf_write_eq = ovstage_write_attribute(
        stage_, q_quatf.query_handle, quatf_attr_ref, quatf_write_ordinal, quatf_write_data, OVSTAGE_PRIM_MODE_UPSERT);
    ASSERT_EQ(quatf_write_eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, quatf_write_eq.op_index);
    docs_ovstage_advance_write_floor(stage_, quatf_write_ordinal);
    ordinal_ = quatf_write_ordinal;  // advance caller's tracked cursor
    // [/snippet:doc-write-usd-quatf-c]
    docs_release_query_and_token(stage_, &q_quatf);

    read_values("test:quatf", dl_type(kDLFloat, 32, 4), false, 1, quatf_values);
    expect_values_near("test:quatf updated", quatf_values, std::vector<float>{82.85f, 82.95f, 83.05f, 1.75f},
                       dl_type(kDLFloat, 32, 4));

    DocsQueryAndToken q_token;
    docs_make_query_and_token(stage_, kWorld, "test:token", &q_token);
    if (HasFatalFailure()) return;
    ovx_string_or_token_t token_attr_ref{};
    token_attr_ref.token = q_token.attr_token;

    // [snippet:doc-read-usd-token-c]
    ovstage_ordinal_range_t token_range{};
    token_range.end_ordinal = ordinal_;

    ovstage_read_handle_t token_read_handle = OVSTAGE_INVALID_READ_HANDLE;
    ovstage_enqueue_result_t token_read_eq = ovstage_read_attributes(
        stage_, q_token.query_handle, &q_token.attr_token, 1, token_range, &token_read_handle);
    ASSERT_EQ(token_read_eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, token_read_eq.op_index);

    ovstage_read_group_t token_group{};
    ASSERT_EQ(ovstage_fetch_read_next(stage_, token_read_handle, OVSTAGE_TIMEOUT_INFINITE, &token_group), OVSTAGE_OK)
        << format_ovstage_last_error();
    ASSERT_GT(token_group.data.tensor_count, 0u);
    DLTensor const &token_tensor = token_group.data.tensors[0];
    // Scalar token: shape=[1], dtype={kDLUInt, 64, 1}. The uint64 is an interned
    // path-dictionary handle; resolve to a string via the stage's path dictionary.
    uint64_t const *token_ids = reinterpret_cast<uint64_t const *>(
        static_cast<uint8_t const *>(token_tensor.data) + token_tensor.byte_offset);
    path_dictionary_instance_t *token_pd = ovstage_get_path_dictionary(stage_);
    ovx_token_t token_id_first = token_ids[0];
    ovx_string_t token_first_string{};
    ASSERT_EQ(path_dictionary_get_strings_from_tokens(token_pd, &token_id_first, 1, &token_first_string).status,
              OVX_API_SUCCESS);
    ovstage_release_group(stage_, &token_group);
    ovstage_release_read(stage_, token_read_handle);
    // [/snippet:doc-read-usd-token-c]
    EXPECT_EQ(std::string(token_first_string.ptr, token_first_string.length), "initialToken");

    // [snippet:doc-write-usd-token-c]
    // Intern "updatedToken" first so we can write its uint64 handle. Semantic
    // OVSTAGE_SEMANTIC_TOKEN_ID tells ovstage the payload is a token id.
    path_dictionary_instance_t *token_write_pd = ovstage_get_path_dictionary(stage_);
    ovx_string_t updated_token_str = ovx_str("updatedToken");
    ovx_token_t updated_token_id = 0;
    ASSERT_EQ(path_dictionary_create_tokens_from_strings(token_write_pd, &updated_token_str, 1, &updated_token_id).status,
              OVX_API_SUCCESS);
    uint64_t updated_token_value = updated_token_id;

    int64_t token_shape[1] = {1};
    DLTensor token_write_tensor{};
    token_write_tensor.data = &updated_token_value;
    token_write_tensor.device = {kDLCPU, 0};
    token_write_tensor.ndim = 1;
    token_write_tensor.dtype = {kDLUInt, 64, 1};
    token_write_tensor.shape = token_shape;

    ovstage_write_data_t token_write_data{};
    token_write_data.tensors = &token_write_tensor;
    token_write_data.tensor_count = 1;
    token_write_data.is_array = false;
    token_write_data.semantic = OVSTAGE_SEMANTIC_TOKEN_ID;

    ovstage_ordinal_t token_write_ordinal = ordinal_ + 1;
    ovstage_enqueue_result_t token_write_eq = ovstage_write_attribute(
        stage_, q_token.query_handle, token_attr_ref, token_write_ordinal, token_write_data, OVSTAGE_PRIM_MODE_UPSERT);
    ASSERT_EQ(token_write_eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, token_write_eq.op_index);
    docs_ovstage_advance_write_floor(stage_, token_write_ordinal);
    ordinal_ = token_write_ordinal;  // advance caller's tracked cursor
    // [/snippet:doc-write-usd-token-c]
    docs_release_query_and_token(stage_, &q_token);

    std::vector<uint64_t> token_values;
    read_values("test:token", dl_type(kDLUInt, 64, 1), false, 1, token_values);
    EXPECT_EQ(token_to_string(stage_, token_values[0]), "updatedToken");

    DocsQueryAndToken q_token_array;
    docs_make_query_and_token(stage_, kWorld, "test:tokenArray", &q_token_array);
    if (HasFatalFailure()) return;
    ovx_string_or_token_t token_array_attr_ref{};
    token_array_attr_ref.token = q_token_array.attr_token;

    // [snippet:doc-read-usd-token-array-c]
    ovstage_ordinal_range_t token_array_range{};
    token_array_range.end_ordinal = ordinal_;

    ovstage_read_handle_t token_array_read_handle = OVSTAGE_INVALID_READ_HANDLE;
    ovstage_enqueue_result_t token_array_read_eq =
        ovstage_read_attributes(stage_, q_token_array.query_handle, &q_token_array.attr_token, 1, token_array_range,
                                &token_array_read_handle);
    ASSERT_EQ(token_array_read_eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, token_array_read_eq.op_index);

    ovstage_read_group_t token_array_group{};
    ASSERT_EQ(ovstage_fetch_read_next(stage_, token_array_read_handle, OVSTAGE_TIMEOUT_INFINITE, &token_array_group),
              OVSTAGE_OK)
        << format_ovstage_last_error();
    ASSERT_TRUE(token_array_group.is_array);
    ASSERT_GT(token_array_group.data.tensor_count, 0u);
    DLTensor const &token_array_tensor = token_array_group.data.tensors[0];
    // Array of tokens: shape=[N], dtype={kDLUInt, 64, 1}.
    uint64_t const *token_array_ids = reinterpret_cast<uint64_t const *>(
        static_cast<uint8_t const *>(token_array_tensor.data) + token_array_tensor.byte_offset);
    path_dictionary_instance_t *token_array_pd = ovstage_get_path_dictionary(stage_);
    std::vector<std::string> token_array_strings;
    for (int64_t i = 0; i < token_array_tensor.shape[0]; ++i) {
        ovx_token_t token_id = token_array_ids[i];
        ovx_string_t token_string{};
        ASSERT_EQ(path_dictionary_get_strings_from_tokens(token_array_pd, &token_id, 1, &token_string).status,
                  OVX_API_SUCCESS);
        token_array_strings.emplace_back(token_string.ptr, token_string.length);
    }
    ovstage_release_group(stage_, &token_array_group);
    ovstage_release_read(stage_, token_array_read_handle);
    // [/snippet:doc-read-usd-token-array-c]
    EXPECT_EQ(token_array_strings, (std::vector<std::string>{"initialTokenA", "initialTokenB"}));

    // [snippet:doc-write-usd-token-array-c]
    path_dictionary_instance_t *token_array_write_pd = ovstage_get_path_dictionary(stage_);
    ovx_string_t updated_token_array_strings[] = {ovx_str("updatedTokenA"), ovx_str("updatedTokenB")};
    ovx_token_t updated_token_array_ids[2] = {};
    ASSERT_EQ(path_dictionary_create_tokens_from_strings(token_array_write_pd, updated_token_array_strings, 2,
                                                         updated_token_array_ids)
                  .status,
              OVX_API_SUCCESS);
    uint64_t updated_token_array_values[2] = {updated_token_array_ids[0], updated_token_array_ids[1]};

    int64_t token_array_shape[1] = {2};
    DLTensor token_array_write_tensor{};
    token_array_write_tensor.data = updated_token_array_values;
    token_array_write_tensor.device = {kDLCPU, 0};
    token_array_write_tensor.ndim = 1;
    token_array_write_tensor.dtype = {kDLUInt, 64, 1};
    token_array_write_tensor.shape = token_array_shape;

    ovstage_write_data_t token_array_write_data{};
    token_array_write_data.tensors = &token_array_write_tensor;
    token_array_write_data.tensor_count = 1;
    token_array_write_data.is_array = true;
    token_array_write_data.semantic = OVSTAGE_SEMANTIC_TOKEN_ID;

    ovstage_ordinal_t token_array_write_ordinal = ordinal_ + 1;
    ovstage_enqueue_result_t token_array_write_eq =
        ovstage_write_attribute(stage_, q_token_array.query_handle, token_array_attr_ref, token_array_write_ordinal,
                                token_array_write_data, OVSTAGE_PRIM_MODE_UPSERT);
    ASSERT_EQ(token_array_write_eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, token_array_write_eq.op_index);
    docs_ovstage_advance_write_floor(stage_, token_array_write_ordinal);
    ordinal_ = token_array_write_ordinal;  // advance caller's tracked cursor
    // [/snippet:doc-write-usd-token-array-c]
    docs_release_query_and_token(stage_, &q_token_array);

    read_values("test:tokenArray", dl_type(kDLUInt, 64, 1), true, 2, token_values);
    EXPECT_EQ(token_to_string(stage_, token_values[0]), "updatedTokenA");
    EXPECT_EQ(token_to_string(stage_, token_values[1]), "updatedTokenB");

    DocsQueryAndToken q_string;
    docs_make_query_and_token(stage_, kWorld, "test:string", &q_string);
    if (HasFatalFailure()) return;
    ovx_string_or_token_t string_attr_ref{};
    string_attr_ref.token = q_string.attr_token;

    // [snippet:doc-read-usd-string-c]
    ovstage_ordinal_range_t string_range{};
    string_range.end_ordinal = ordinal_;

    ovstage_read_handle_t string_read_handle = OVSTAGE_INVALID_READ_HANDLE;
    ovstage_enqueue_result_t string_read_eq = ovstage_read_attributes(
        stage_, q_string.query_handle, &q_string.attr_token, 1, string_range, &string_read_handle);
    ASSERT_EQ(string_read_eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, string_read_eq.op_index);

    ovstage_read_group_t string_group{};
    ASSERT_EQ(ovstage_fetch_read_next(stage_, string_read_handle, OVSTAGE_TIMEOUT_INFINITE, &string_group), OVSTAGE_OK)
        << format_ovstage_last_error();
    ASSERT_TRUE(string_group.is_array);
    ASSERT_GT(string_group.data.tensor_count, 0u);
    DLTensor const &string_tensor = string_group.data.tensors[0];
    // USD "string" is transported as a variable-length array of bytes: shape=[N],
    // dtype={kDLUInt, 8, 1}. Decode by taking the first N bytes as UTF-8.
    char const *string_bytes =
        static_cast<char const *>(string_tensor.data) + string_tensor.byte_offset;
    std::string string_value(string_bytes, string_bytes + string_tensor.shape[0]);
    ovstage_release_group(stage_, &string_group);
    ovstage_release_read(stage_, string_read_handle);
    // [/snippet:doc-read-usd-string-c]
    EXPECT_EQ(string_value, "initial string");

    // [snippet:doc-write-usd-string-c]
    char const updated_string[] = "updated longer string";
    int64_t string_shape[1] = {static_cast<int64_t>(std::strlen(updated_string))};
    DLTensor string_write_tensor{};
    string_write_tensor.data = const_cast<char *>(updated_string);
    string_write_tensor.device = {kDLCPU, 0};
    string_write_tensor.ndim = 1;
    string_write_tensor.dtype = {kDLUInt, 8, 1};
    string_write_tensor.shape = string_shape;

    ovstage_write_data_t string_write_data{};
    string_write_data.tensors = &string_write_tensor;
    string_write_data.tensor_count = 1;
    string_write_data.is_array = true;

    ovstage_ordinal_t string_write_ordinal = ordinal_ + 1;
    ovstage_enqueue_result_t string_write_eq = ovstage_write_attribute(
        stage_, q_string.query_handle, string_attr_ref, string_write_ordinal, string_write_data,
        OVSTAGE_PRIM_MODE_UPSERT);
    ASSERT_EQ(string_write_eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, string_write_eq.op_index);
    docs_ovstage_advance_write_floor(stage_, string_write_ordinal);
    ordinal_ = string_write_ordinal;  // advance caller's tracked cursor
    // [/snippet:doc-write-usd-string-c]
    docs_release_query_and_token(stage_, &q_string);

    std::vector<uint8_t> string_values;
    read_values("test:string", dl_type(kDLUInt, 8, 1), true, std::strlen(updated_string), string_values);
    EXPECT_EQ(std::string(string_values.begin(), string_values.end()), "updated longer string");

}

TEST_F(AllAttributesTest, AssetReadWriteSnippets) {
    // Transitional scalar-asset read contract (ovstage 0.1.x): one fixed
    // {kDLUInt, 64, 2} element per prim carrying the {authored-path token,
    // resolved-path token} pair (resolved token 0 when unresolved) with
    // attribute semantic NONE, decoded through the shared path dictionary;
    // planned to become canonical ASSET_STRING byte rows in the next minor
    // release. Writing to a populated scalar `asset` attribute is not
    // supported in 0.1.x, so the write half of this test skips
    // below; the write snippet expresses the planned canonical byte-row
    // payload as an intent document.

    load_all_attributes();
    if (HasFatalFailure()) return;

    bool asset_pair_contract = false;
    probe_asset_pair_contract(&asset_pair_contract);
    if (HasFatalFailure()) return;
    if (!asset_pair_contract) {
        GTEST_SKIP() << "linked ovstage package predates the transitional scalar-asset read "
                        "contract ({kDLUInt, 64, 2} token pairs); link ovstage 0.1.1 or later "
                        "to run this test";
    }

    DocsQueryAndToken q_asset;
    docs_make_query_and_token(stage_, kWorld, "test:asset", &q_asset);
    if (HasFatalFailure()) return;
    ovx_string_or_token_t asset_attr_ref{};
    asset_attr_ref.token = q_asset.attr_token;

    // [snippet:doc-read-usd-asset-c]
    ovstage_ordinal_range_t asset_range{};
    asset_range.end_ordinal = ordinal_;

    ovstage_read_handle_t asset_read_handle = OVSTAGE_INVALID_READ_HANDLE;
    ovstage_enqueue_result_t asset_read_eq = ovstage_read_attributes(
        stage_, q_asset.query_handle, &q_asset.attr_token, 1, asset_range, &asset_read_handle);
    ASSERT_EQ(asset_read_eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, asset_read_eq.op_index);

    ovstage_read_group_t asset_group{};
    ASSERT_EQ(ovstage_fetch_read_next(stage_, asset_read_handle, OVSTAGE_TIMEOUT_INFINITE, &asset_group), OVSTAGE_OK)
        << format_ovstage_last_error();
    ASSERT_GT(asset_group.data.tensor_count, 0u);
    DLTensor const &asset_tensor = asset_group.data.tensors[0];
    // Transitional representation (ovstage 0.1.x): a populated scalar asset
    // reads back as one fixed element per prim with dtype={kDLUInt, 64, 2}
    // and semantic NONE. Lane 0 is the authored-path token, lane 1 the
    // resolved-path token (0 when the asset path did not resolve). Decode
    // tokens through the shared path dictionary.
    uint64_t const *asset_pair = reinterpret_cast<uint64_t const *>(
        static_cast<uint8_t const *>(asset_tensor.data) + asset_tensor.byte_offset);
    path_dictionary_instance_t *asset_pd = ovstage_get_path_dictionary(stage_);
    ovx_token_t asset_authored_token = asset_pair[0];
    ovx_string_t asset_authored_string{};
    ASSERT_EQ(path_dictionary_get_strings_from_tokens(asset_pd, &asset_authored_token, 1, &asset_authored_string).status,
              OVX_API_SUCCESS);
    std::string asset_value(asset_authored_string.ptr, asset_authored_string.length);
    uint64_t asset_resolved_token = asset_pair[1];
    ovstage_release_group(stage_, &asset_group);
    ovstage_release_read(stage_, asset_read_handle);
    // [/snippet:doc-read-usd-asset-c]
    EXPECT_EQ(asset_value, "initial_asset.usd");
    // The data directory carries no initial_asset.usd, so the authored path
    // cannot resolve in this environment.
    EXPECT_EQ(asset_resolved_token, 0u);

    docs_release_query_and_token(stage_, &q_asset);
    GTEST_SKIP() << "Writing to a populated scalar asset attribute is not "
                    "supported in ovstage 0.1.x; the write snippet below "
                    "expresses the planned canonical ASSET_STRING byte-row "
                    "payload";

    // [snippet:doc-write-usd-asset-c]
    char const updated_asset[] = "updated_asset.usd";
    int64_t asset_shape[1] = {static_cast<int64_t>(std::strlen(updated_asset))};
    DLTensor asset_write_tensor{};
    asset_write_tensor.data = const_cast<char *>(updated_asset);
    asset_write_tensor.device = {kDLCPU, 0};
    asset_write_tensor.ndim = 1;
    asset_write_tensor.dtype = {kDLUInt, 8, 1};
    asset_write_tensor.shape = asset_shape;

    ovstage_write_data_t asset_write_data{};
    asset_write_data.tensors = &asset_write_tensor;
    asset_write_data.tensor_count = 1;
    asset_write_data.is_array = true;
    asset_write_data.semantic = OVSTAGE_SEMANTIC_ASSET_STRING;

    ovstage_ordinal_t asset_write_ordinal = ordinal_ + 1;
    ovstage_enqueue_result_t asset_write_eq = ovstage_write_attribute(
        stage_, q_asset.query_handle, asset_attr_ref, asset_write_ordinal, asset_write_data, OVSTAGE_PRIM_MODE_UPSERT);
    ASSERT_EQ(asset_write_eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, asset_write_eq.op_index);
    docs_ovstage_advance_write_floor(stage_, asset_write_ordinal);
    ordinal_ = asset_write_ordinal;  // advance caller's tracked cursor
    // [/snippet:doc-write-usd-asset-c]
    docs_release_query_and_token(stage_, &q_asset);

    std::vector<uint8_t> asset_values;
    read_values("test:asset", dl_type(kDLUInt, 8, 1), true, std::strlen(updated_asset), asset_values);
    EXPECT_EQ(std::string(asset_values.begin(), asset_values.end()), "updated_asset.usd");
}

TEST_F(AllAttributesTest, ExtentAndWorldExtentAreReadable) {
    load_all_attributes();
    if (HasFatalFailure()) return;

    DocsQueryAndToken q_extent;
    docs_make_query_and_token(stage_, kExtentLeaf, "extent", &q_extent);
    if (HasFatalFailure()) return;
    // Intern the _worldExtent token on the shared path dictionary so the read
    // below can pass both tokens in a single ovstage_read_attributes call.
    ovx_string_t world_extent_str = ovx_str("_worldExtent");
    ovx_token_t world_extent_token = 0;
    ASSERT_EQ(path_dictionary_create_tokens_from_strings(q_extent.pd, &world_extent_str, 1, &world_extent_token).status,
              OVX_API_SUCCESS);

    // [snippet:doc-extent-world-extent-c]
    // Read both attributes in one enqueue and route each returned group by its
    // group.attribute token. `extent` is per-prim local; `_worldExtent` is the
    // composed world-space extent for the same prim.
    ovx_token_t extent_tokens[2] = {q_extent.attr_token, world_extent_token};
    ovstage_ordinal_range_t extent_range{};
    extent_range.end_ordinal = ordinal_;

    ovstage_read_handle_t extent_read_handle = OVSTAGE_INVALID_READ_HANDLE;
    ovstage_enqueue_result_t extent_read_eq = ovstage_read_attributes(
        stage_, q_extent.query_handle, extent_tokens, 2, extent_range, &extent_read_handle);
    ASSERT_EQ(extent_read_eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage_, extent_read_eq.op_index);

    std::vector<double> local_extent;
    std::vector<double> world_extent;
    while (true) {
        ovstage_read_group_t group{};
        ovstage_api_status_t s =
            ovstage_fetch_read_next(stage_, extent_read_handle, OVSTAGE_TIMEOUT_INFINITE, &group);
        if (s == OVSTAGE_ERROR_END_OF_ITERATION) break;
        ASSERT_EQ(s, OVSTAGE_OK) << format_ovstage_last_error();

        ASSERT_GT(group.data.tensor_count, 0u);
        DLTensor const &t = group.data.tensors[0];
        double const *data =
            reinterpret_cast<double const *>(static_cast<uint8_t const *>(t.data) + t.byte_offset);
        std::vector<double> values(data, data + t.shape[0] * t.dtype.lanes);
        if (group.attribute == q_extent.attr_token) {
            local_extent = std::move(values);
        } else if (group.attribute == world_extent_token) {
            world_extent = std::move(values);
        }
        ovstage_release_group(stage_, &group);
    }
    ovstage_release_read(stage_, extent_read_handle);
    // [/snippet:doc-extent-world-extent-c]

    docs_release_query_and_token(stage_, &q_extent);

    expect_values_near("extent", local_extent, std::vector<double>{-1, -2, -3, 1, 2, 3}, dl_type(kDLFloat, 64, 6));
    expect_values_near("_worldExtent", world_extent, std::vector<double>{8, 14, 18, 12, 26, 42},
                       dl_type(kDLFloat, 64, 6));
}
