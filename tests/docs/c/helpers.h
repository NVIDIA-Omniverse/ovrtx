// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

#include <ovrtx/ovrtx.h>
#include <ovrtx/ovrtx_config.h>
#include <ovrtx/ovrtx_types.h>

#include <ovstage/ovstage.h>
#include <ovstage/ovstage_population.h>

#include <cmath>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <set>
#include <string>
#include <string_view>
#include <vector>

#include "stb_image_write.h"
#include <ovx/path_dictionary/path_dictionary_utils.h>

// Return the path to tests/data/. Prefer the OVRTX_TEST_DATA_DIR environment
// variable (set by CI when build and test run on different machines) and fall
// back to a path relative to this source file for local development.
static std::string get_test_data_dir() {
    if (const char* env = std::getenv("OVRTX_TEST_DATA_DIR")) {
        return env;
    }
    std::filesystem::path src(__FILE__);
    return (src.parent_path() / "../../../tests/data").lexically_normal().string();
}

// Return the path to tests/docs/data/. Prefer the OVRTX_DOCS_TEST_DATA_DIR
// environment variable and fall back to a path relative to this source file.
static std::string get_docs_test_data_dir() {
    if (const char* env = std::getenv("OVRTX_DOCS_TEST_DATA_DIR")) {
        return env;
    }
    std::filesystem::path src(__FILE__);
    return (src.parent_path() / "../data").lexically_normal().string();
}

// Helper to make an ovx_string_t from a C string literal.
static ovx_string_t ovx_str(char const* s) {
    return {s, strlen(s)};
}

// Find a named render var output handle within a single render product's output.
static ovrtx_render_var_output_handle_t
find_product_output(ovrtx_render_product_output_t const& product_output,
                    char const* output_to_find) {
    for (size_t f = 0; f < product_output.output_frame_count; ++f) {
        ovrtx_render_product_frame_output_t const& frame =
            product_output.output_frames[f];
        for (size_t v = 0; v < frame.render_var_count; ++v) {
            ovrtx_render_product_render_var_output_t const& var =
                frame.output_render_vars[v];
            if (var.render_var_name.ptr &&
                strncmp(var.render_var_name.ptr, output_to_find,
                        var.render_var_name.length) == 0) {
                return var.output_handle;
            }
        }
    }
    return OVRTX_INVALID_HANDLE;
}

// Find a named render var output handle across all render products.
static ovrtx_render_var_output_handle_t
find_output(ovrtx_render_product_set_outputs_t const& outputs,
            char const* output_to_find) {
    for (size_t i = 0; i < outputs.output_count; ++i) {
        ovrtx_render_var_output_handle_t handle = find_product_output(outputs.outputs[i], output_to_find);
        if (handle != OVRTX_INVALID_HANDLE) {
            return handle;
        }
    }
    return OVRTX_INVALID_HANDLE;
}

// Return the _output directory. Prefer the OVRTX_TEST_OUTPUT_DIR environment
// variable (set by CI when build and test run on different machines) and fall
// back to a path relative to this source file for local development.
static std::filesystem::path get_output_dir() {
    std::filesystem::path dir;
    if (const char* env = std::getenv("OVRTX_TEST_OUTPUT_DIR")) {
        dir = env;
    } else {
        dir = std::filesystem::path(__FILE__).parent_path() / "_output";
    }
    std::filesystem::create_directories(dir);
    return dir;
}

// RAII wrapper that builds an ovrtx_config_t directing the log to
// _output/<test_name>-ovrtx.log.  Owns the backing storage so the config
// stays valid for the lifetime of the object.  An optional log_level
// (e.g. "info", "warn", "error") can be supplied to pin the threshold.
struct TestConfig {
    std::string log_path_str;
    ovx_string_t log_path;
    std::string log_level_str;
    ovx_string_t log_level;
    ovrtx_config_entry_t entries[2]{};
    ovrtx_config_t config;

    TestConfig(TestConfig const&) = delete;
    TestConfig& operator=(TestConfig const&) = delete;

    explicit TestConfig(char const* test_name, char const* log_level_value = nullptr) {
        log_path_str = (get_output_dir() / (std::string(test_name) + "-ovrtx.log")).string();
        log_path = {log_path_str.c_str(), log_path_str.size()};
        entries[0] = ovrtx_config_entry_log_file_path(log_path);
        size_t entry_count = 1;
        if (log_level_value && *log_level_value) {
            log_level_str = log_level_value;
            log_level = {log_level_str.c_str(), log_level_str.size()};
            entries[1] = ovrtx_config_entry_log_level(log_level);
            entry_count = 2;
        }
        config = {entries, entry_count};
    }
};

// Print all op errors from a wait result, then return the error count.
// Call immediately after ovrtx_wait_op() and before any assertion on
// num_error_ops so that failure messages include the actual error strings.
static std::string format_op_errors(ovrtx_op_wait_result_t const& wr) {
    std::string msg;
    for (size_t i = 0; i < wr.num_error_ops; ++i) {
        ovx_string_t err = ovrtx_get_last_op_error(wr.error_op_ids[i]);
        msg += "  op " + std::to_string(wr.error_op_ids[i]) + ": ";
        msg += std::string(err.ptr, err.length) + "\n";
    }
    return msg;
}

// Format the last per-thread API error string. Use after any enqueue- or
// synchronous-call failure (status != OVRTX_API_SUCCESS) to surface the
// underlying reason. The string is valid until the next API call on this
// thread, so capture it immediately.
static std::string format_api_error() {
    ovx_string_t err = ovrtx_get_last_error();
    if (err.ptr && err.length > 0) {
        return "  ovrtx_get_last_error: " + std::string(err.ptr, err.length) + "\n";
    }
    return "  (ovrtx_get_last_error returned empty)\n";
}

static char const* api_status_name(ovrtx_api_status_t status) {
    switch (status) {
        case OVRTX_API_SUCCESS:
            return "OVRTX_API_SUCCESS";
        case OVRTX_API_ERROR:
            return "OVRTX_API_ERROR";
        case OVRTX_API_TIMEOUT:
            return "OVRTX_API_TIMEOUT";
    }
    return "OVRTX_API_UNKNOWN";
}

static std::string format_api_status_error(ovrtx_api_status_t status) {
    std::string msg = "  ovrtx status: ";
    msg += api_status_name(status);
    msg += " (";
    msg += std::to_string(static_cast<int>(status));
    msg += ")\n";
    msg += format_api_error();
    return msg;
}

// Convenience macro: assert no op errors, printing the error strings on failure.
#define ASSERT_NO_OP_ERRORS(wr) \
    do {                                                                     \
        ovrtx_op_wait_result_t const& wr__ = (wr);                           \
        std::string const op_errors__ = format_op_errors(wr__);              \
        ASSERT_EQ(wr__.num_error_ops, 0u) << op_errors__;                    \
    } while (false)

// Convenience macros: assert/expect that an API call returned OVRTX_API_SUCCESS,
// printing ovrtx_get_last_error() on failure so the runtime reason is visible.
// Works for any call site whose status field is `ovrtx_api_status_t`
// (ovrtx_enqueue_result_t::status, ovrtx_result_t::status, etc.).
#define ASSERT_API_SUCCESS(status_expr)                                      \
    do {                                                                     \
        ovrtx_api_status_t const status__ = (status_expr);                   \
        std::string const api_error__ =                                      \
            status__ == OVRTX_API_SUCCESS ? std::string() : format_api_status_error(status__); \
        ASSERT_EQ(status__, OVRTX_API_SUCCESS) << api_error__;               \
    } while (false)

#define EXPECT_API_SUCCESS(status_expr)                                      \
    do {                                                                     \
        ovrtx_api_status_t const status__ = (status_expr);                   \
        std::string const api_error__ =                                      \
            status__ == OVRTX_API_SUCCESS ? std::string() : format_api_status_error(status__); \
        EXPECT_EQ(status__, OVRTX_API_SUCCESS) << api_error__;               \
    } while (false)

// Save an RGBA uint8 LdrColor buffer to _output/<name>.png.
static void save_ldr_png(char const* name, void const* data, int width, int height) {
    auto path = get_output_dir() / (std::string(name) + ".png");
    int ok = stbi_write_png(path.string().c_str(), width, height, 4, data, width * 4);
    if (ok) {
        printf("Saved %s\n", path.string().c_str());
    } else {
        printf("WARNING: failed to write %s\n", path.string().c_str());
    }
}

// Build an inline USDA string that sublayers a scene file and adds a
// RenderProduct with the given render vars.
static std::string make_sublayer_usda(
    std::string_view scene_path,
    std::string_view render_product_body) {
    std::string usda;
    usda += "#usda 1.0\n";
    usda += "(\n";
    usda += "    subLayers = [\n";
    usda += "        @";
    usda += scene_path;
    usda += "@\n";
    usda += "    ]\n";
    usda += ")\n\n";
    usda += render_product_body;
    usda += "\n";
    return usda;
}

// Resolve a single ovx_primpath_t into a "/A/B/C" string via the path dictionary.
// [snippet:doc-resolve-primpath-helper-c]
static std::string docs_resolve_primpath(path_dictionary_instance_t* pd, ovx_primpath_t p) {
    ovx_token_t token_buf[64];
    ovx_token_t* tokens_out = nullptr;
    size_t num_tokens = 0;
    size_t num_processed = 0;
    ovx_api_result_t r = path_dictionary_get_tokens_from_paths(
        pd, &p, 1, token_buf, 64, &tokens_out, &num_tokens, &num_processed);
    if (r.status != OVX_API_SUCCESS || num_processed == 0) {
        return "";
    }
    std::string out;
    for (size_t i = 0; i < num_tokens; ++i) {
        ovx_string_t s{};
        if (path_dictionary_get_strings_from_tokens(pd, &tokens_out[i], 1, &s).status ==
            OVX_API_SUCCESS) {
            out += "/";
            out.append(s.ptr, s.length);
        }
    }
    return out;
}
// [/snippet:doc-resolve-primpath-helper-c]

// Collect every resolved prim path from an ovrtx query result. The query result
// must still be alive while this runs because the group prim-list handles are
// owned by the query result.
static std::set<std::string> docs_collect_query_paths(ovrtx_query_result_t const& qr,
                                                      path_dictionary_instance_t* pd) {
    std::set<std::string> paths;
    for (size_t g = 0; g < qr.group_count; ++g) {
        ovrtx_query_prim_group_t const& group = qr.groups[g];
        size_t num_paths = 0;
        if (path_dictionary_get_num_paths_from_path_list(pd, group.prim_list_handle, &num_paths)
                .status != OVX_API_SUCCESS) {
            continue;
        }
        std::vector<ovx_primpath_t> prim_paths(num_paths);
        size_t out_num = 0;
        if (path_dictionary_get_paths_from_path_list(pd, group.prim_list_handle, 0, num_paths,
                                                     prim_paths.data(), &out_num)
                .status != OVX_API_SUCCESS) {
            continue;
        }
        for (size_t i = 0; i < out_num; ++i) {
            paths.insert(docs_resolve_primpath(pd, prim_paths[i]));
        }
    }
    return paths;
}

// Query all prim paths currently visible to the runtime stage.
static std::set<std::string> docs_query_all_paths(ovrtx_renderer_t* renderer) {
    ovrtx_query_desc_t desc{};
    desc.attribute_filter.mode = OVRTX_ATTRIBUTE_FILTER_NONE;

    ovrtx_query_handle_t query_handle = 0;
    ovrtx_enqueue_result_t eq = ovrtx_query_prims(renderer, &desc, &query_handle);
    if (eq.status != OVRTX_API_SUCCESS) {
        return {};
    }

    ovrtx_op_wait_result_t wait_result{};
    if (ovrtx_wait_op(renderer, eq.op_index, ovrtx_timeout_infinite, &wait_result).status !=
        OVRTX_API_SUCCESS) {
        return {};
    }
    if (wait_result.num_error_ops != 0) {
        return {};
    }

    ovrtx_query_result_t qr{};
    if (ovrtx_fetch_query_results(renderer, query_handle, ovrtx_timeout_infinite, &qr).status !=
        OVRTX_API_SUCCESS) {
        return {};
    }

    path_dictionary_instance_t pd{};
    std::set<std::string> paths;
    if (ovrtx_get_path_dictionary(renderer, &pd).status == OVRTX_API_SUCCESS) {
        paths = docs_collect_query_paths(qr, &pd);
    }
    ovrtx_release_query_results(renderer, query_handle);
    return paths;
}

static void docs_wait_no_errors(ovrtx_renderer_t* renderer, ovrtx_op_id_t op_id) {
    ovrtx_op_wait_result_t wait_result{};
    ASSERT_API_SUCCESS(ovrtx_wait_op(renderer, op_id, ovrtx_timeout_infinite, &wait_result).status);
    ASSERT_NO_OP_ERRORS(wait_result);
}

// ────────────────────────────────────────────────────────────────────────────
// ovstage helpers
//
// Mirrors of the pytest conftest / _query_prefix_count / _read_attribute helpers
// in tests/docs/python/, adapted to the C API. Every C doc test that drives an
// attached ovstage goes through these — keep them the single source of truth for
// wait-and-check + prim/attribute lookup patterns in the doc tests.
// ────────────────────────────────────────────────────────────────────────────

// Shared "  <label>: <err>\n" formatter — used by every last-error printer in
// this header. The C-string label is embedded verbatim so failure messages
// still name the accessor that produced the error.
static std::string format_last_error_str(ovx_string_t err, char const* label) {
    if (err.ptr && err.length > 0) {
        return std::string("  ") + label + ": " + std::string(err.ptr, err.length) + "\n";
    }
    return std::string("  (") + label + " returned empty)\n";
}

static std::string format_ovstage_last_error() {
    return format_last_error_str(ovstage_get_last_error(),
                                 "ovstage_get_last_error");
}

static std::string format_ovstage_population_last_error() {
    return format_last_error_str(ovstage_population_get_last_error(),
                                 "ovstage_population_get_last_error");
}

// Wait on an ovstage data-plane op (advance_write_floor, clone, query, read, ...).
// Mirrors docs_wait_no_errors but goes through the ovstage_wait_op path.
static void docs_wait_ovstage_no_errors(ovstage_instance_t* stage, ovstage_op_id_t op_id) {
    ovstage_op_wait_result_t wait_result{};
    ovstage_api_status_t status =
        ovstage_wait_op(stage, op_id, OVSTAGE_TIMEOUT_INFINITE, &wait_result);
    if (status != OVSTAGE_OK) {
        FAIL() << "ovstage_wait_op status=" << static_cast<int>(status) << "\n"
               << format_ovstage_last_error();
    }
    std::string msg;
    for (size_t i = 0; i < wait_result.error_op_id_count; ++i) {
        ovx_string_t err = ovstage_get_last_op_error(stage, wait_result.error_op_ids[i]);
        msg += "  op " + std::to_string(wait_result.error_op_ids[i]) + ": ";
        msg += std::string(err.ptr ? err.ptr : "", err.length) + "\n";
    }
    ASSERT_EQ(wait_result.error_op_id_count, 0u) << msg;
}

// Wait on an ovstage population op (open_usd_*, add_usd_reference_*, remove_usd,
// apply_usd_changes, reset_usd, apply_usd_time). Population has its own wait_op
// with distinct op-id and error-detail namespaces.
static void docs_wait_ovstage_population_no_errors(ovstage_instance_t* stage,
                                                    ovstage_population_op_id_t op_id) {
    ovstage_population_op_wait_result_t wait_result{};
    ovstage_api_status_t status = ovstage_population_wait_op(
        stage, op_id, OVSTAGE_TIMEOUT_INFINITE, &wait_result);
    if (status != OVSTAGE_OK) {
        FAIL() << "ovstage_population_wait_op status=" << static_cast<int>(status) << "\n"
               << format_ovstage_population_last_error();
    }
    std::string msg;
    for (size_t i = 0; i < wait_result.error_op_id_count; ++i) {
        ovx_string_t err = ovstage_population_get_last_op_error(wait_result.error_op_ids[i]);
        msg += "  pop op " + std::to_string(wait_result.error_op_ids[i]) + ": ";
        msg += std::string(err.ptr ? err.ptr : "", err.length) + "\n";
    }
    ASSERT_EQ(wait_result.error_op_id_count, 0u) << msg;
}

// Advance the ovstage global write floor to `ordinal` and wait for the advance
// to seal. The canonical end-of-tick barrier the doc tests use between
// population/write work and the next render / read step.
static void docs_ovstage_advance_write_floor(ovstage_instance_t* stage,
                                              ovstage_ordinal_t ordinal) {
    ovstage_write_floor_desc_t desc{};
    desc.ordinal = ordinal;
    desc.scope = OVSTAGE_SCOPE_ALL;
    ovstage_enqueue_result_t eq = ovstage_advance_write_floor(stage, &desc);
    ASSERT_EQ(eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage, eq.op_index);
}

// Count prims whose usd-path starts with `prefix`. Mirrors the Python
// _query_prefix_count helper in tests/docs/python/test_stage_mutation.py.
// Returns SIZE_MAX on any error, so a broken query cannot masquerade as
// "0 matching prims" and quietly satisfy an EXPECT_EQ(..., 0u).
static size_t docs_query_prefix_count(ovstage_instance_t* stage, char const* prefix) {
    ovx_string_t prefix_str = ovx_str(prefix);
    ovx_string_t attr_name = ovx_str("usd-path");
    ovstage_predicate_t predicate{};
    predicate.attribute.string = attr_name;
    predicate.op = OVSTAGE_FILTER_OP_PREFIX;
    predicate.values = &prefix_str;
    predicate.value_count = 1;

    ovstage_filter_t filter{};
    filter.predicates = &predicate;
    filter.count = 1;

    ovstage_query_handle_t query_handle = OVSTAGE_INVALID_QUERY_HANDLE;
    ovstage_enqueue_result_t eq = ovstage_query(stage, &filter, nullptr, 0, &query_handle);
    if (eq.status != OVSTAGE_OK) {
        ADD_FAILURE() << "ovstage_query status=" << static_cast<int>(eq.status) << "\n"
                      << format_ovstage_last_error();
        return SIZE_MAX;
    }

    docs_wait_ovstage_no_errors(stage, eq.op_index);
    if (::testing::Test::HasFatalFailure()) {
        ovstage_release_query(stage, query_handle);
        return SIZE_MAX;
    }

    ovstage_query_result_t qr{};
    ovstage_api_status_t s =
        ovstage_fetch_query_result(stage, query_handle, OVSTAGE_TIMEOUT_INFINITE, &qr);
    size_t total = SIZE_MAX;
    if (s == OVSTAGE_OK) {
        total = qr.total_prim_count;
        ovstage_release_query_result(stage, &qr);
    } else {
        ADD_FAILURE() << "ovstage_fetch_query_result status=" << static_cast<int>(s) << "\n"
                      << format_ovstage_last_error();
    }
    ovstage_release_query(stage, query_handle);
    return total;
}

// Collect the string prim-paths of every prim matched by `query_handle`.
// Enumerates via a read of the built-in usd-path attribute at latest(ordinal)
// — the fabric-side authoritative source of prim identity. Groups' prims are
// walked with the standard offset/count/index_map subsetting semantics so a
// backend that returns non-contiguous prim groups is handled correctly.
static std::set<std::string> docs_ovstage_collect_paths(
    ovstage_instance_t* stage,
    ovstage_query_handle_t query_handle,
    ovstage_ordinal_t ordinal) {
    std::set<std::string> paths;
    path_dictionary_instance_t* pd = ovstage_get_path_dictionary(stage);
    if (!pd) return paths;

    // Reading usd-path directly is not currently supported by the Fabric
    // backend even though it is filter-usable — use usd-prim-type which every
    // populated prim carries. We do not care about the tensor data; the
    // enumeration comes from group.prims.list.
    ovx_string_t attr_str = ovx_str("usd-prim-type");
    ovx_token_t attr_token{};
    if (path_dictionary_create_tokens_from_strings(pd, &attr_str, 1, &attr_token).status
        != OVX_API_SUCCESS) return paths;

    ovstage_ordinal_range_t range{};
    range.has_start_ordinal = false;
    range.end_ordinal = ordinal;

    ovstage_read_handle_t read_handle = OVSTAGE_INVALID_READ_HANDLE;
    ovstage_enqueue_result_t eq =
        ovstage_read_attributes(stage, query_handle, &attr_token, 1, range, &read_handle);
    if (eq.status != OVSTAGE_OK) return paths;

    ovstage_op_wait_result_t wait_result{};
    if (ovstage_wait_op(stage, eq.op_index, OVSTAGE_TIMEOUT_INFINITE, &wait_result) != OVSTAGE_OK) {
        return paths;
    }
    if (wait_result.error_op_id_count != 0) return paths;

    while (true) {
        ovstage_read_group_t group{};
        ovstage_api_status_t s =
            ovstage_fetch_read_next(stage, read_handle, OVSTAGE_TIMEOUT_INFINITE, &group);
        if (s == OVSTAGE_ERROR_END_OF_ITERATION) break;
        if (s != OVSTAGE_OK) break;

        size_t list_len = 0;
        if (path_dictionary_get_num_paths_from_path_list(pd, group.prims.list, &list_len).status
            == OVX_API_SUCCESS) {
            std::vector<ovx_primpath_t> list_paths(list_len);
            size_t out_num = 0;
            if (path_dictionary_get_paths_from_path_list(
                    pd, group.prims.list, 0, list_len, list_paths.data(), &out_num).status
                == OVX_API_SUCCESS) {
                for (uint32_t i = 0; i < group.prims.count; ++i) {
                    uint32_t src_idx = group.prims.index_map
                                           ? group.prims.index_map[i]
                                           : group.prims.offset + i;
                    if (src_idx < out_num) {
                        paths.insert(docs_resolve_primpath(pd, list_paths[src_idx]));
                    }
                }
            }
        }

        ovstage_release_group(stage, &group);
    }

    ovstage_release_read(stage, read_handle);
    return paths;
}

// Read `attribute_name` from a single prim at latest(ordinal) into out_bytes.
// Copies raw DLTensor bytes so byte-wise equality works for the doc test's
// source-vs-clone comparison. Mirrors the Python _read_attribute helper.
static void docs_read_attribute(ovstage_instance_t* stage,
                                char const* prim_path,
                                char const* attribute_name,
                                ovstage_ordinal_t ordinal,
                                std::vector<uint8_t>* out_bytes) {
    out_bytes->clear();

    path_dictionary_instance_t* pd = ovstage_get_path_dictionary(stage);
    ASSERT_NE(pd, nullptr);

    ovx_string_t path_str = ovx_str(prim_path);
    ovx_primpath_list_t path_list{};
    ASSERT_EQ(path_dictionary_create_path_list_from_strings(pd, &path_str, 1, &path_list).status,
              OVX_API_SUCCESS);

    ovstage_query_handle_t query_handle = OVSTAGE_INVALID_QUERY_HANDLE;
    ASSERT_EQ(ovstage_query_from_path_list(stage, path_list, &query_handle), OVSTAGE_OK)
        << format_ovstage_last_error();

    ovx_string_t attr_str = ovx_str(attribute_name);
    ovx_token_t attr_token{};
    ASSERT_EQ(path_dictionary_create_tokens_from_strings(pd, &attr_str, 1, &attr_token).status,
              OVX_API_SUCCESS);

    ovstage_ordinal_range_t range{};
    range.has_start_ordinal = false;
    range.end_ordinal = ordinal;

    ovstage_read_handle_t read_handle = OVSTAGE_INVALID_READ_HANDLE;
    ovstage_enqueue_result_t eq =
        ovstage_read_attributes(stage, query_handle, &attr_token, 1, range, &read_handle);
    ASSERT_EQ(eq.status, OVSTAGE_OK) << format_ovstage_last_error();
    docs_wait_ovstage_no_errors(stage, eq.op_index);

    // Drain the read: ovstage may split results across groups (fetch_read_next
    // returns END_OF_ITERATION when there are no more). We accumulate every
    // tensor's bytes so a chunked backend can't silently truncate. For each
    // tensor we honor the DLPack contract: data + byte_offset for the start,
    // (bits*lanes+7)/8 (ceil) for the per-element byte size, and reject
    // non-contiguous strides — this helper is a byte-copy so a stride pattern
    // would just corrupt out_bytes.
    while (true) {
        ovstage_read_group_t group{};
        ovstage_api_status_t s =
            ovstage_fetch_read_next(stage, read_handle, OVSTAGE_TIMEOUT_INFINITE, &group);
        if (s == OVSTAGE_ERROR_END_OF_ITERATION) {
            break;
        }
        ASSERT_EQ(s, OVSTAGE_OK) << format_ovstage_last_error();

        for (uint32_t i = 0; i < group.data.tensor_count; ++i) {
            DLTensor const& t = group.data.tensors[i];
            if (t.strides != nullptr) {
                int64_t expected = 1;
                bool contiguous = true;
                for (int d = t.ndim - 1; d >= 0; --d) {
                    if (t.strides[d] != expected) {
                        contiguous = false;
                        break;
                    }
                    expected *= t.shape[d];
                }
                if (!contiguous) {
                    ovstage_release_group(stage, &group);
                    FAIL() << "docs_read_attribute: non-contiguous DLTensor strides "
                              "not supported (attribute=" << attribute_name << ")";
                    return;
                }
            }
            int64_t element_count = 1;
            for (int d = 0; d < t.ndim; ++d) {
                element_count *= t.shape[d];
            }
            size_t byte_count = (static_cast<size_t>(element_count)
                                    * t.dtype.lanes * t.dtype.bits + 7) / 8;
            uint8_t const* base =
                static_cast<uint8_t const*>(t.data) + t.byte_offset;
            out_bytes->insert(out_bytes->end(), base, base + byte_count);
        }
        ovstage_release_group(stage, &group);
    }

    ovstage_release_read(stage, read_handle);
    ovstage_release_query(stage, query_handle);
    path_dictionary_release_path_list_reference(pd, path_list);
}

// ────────────────────────────────────────────────────────────────────────────
// DocsQueryAndToken
//
// Reserve a single-prim query handle + an interned attribute token in one
// call. The pair (query_handle, attr_token) is the ovstage-side equivalent
// of the deprecated ovrtx_attribute_binding_t — both identify "one attribute
// on one prim" and are reusable across many reads/writes until released.
// Doc tests that walk a single /World-scoped attribute per call use this
// helper to keep the query + intern boilerplate out of the [snippet:] blocks.
// Callers must pair every docs_make_query_and_token with a matching
// docs_release_query_and_token — no RAII destructor, so the release must sit
// on the happy path OR be guarded by an if (HasFatalFailure()) return path.
// ────────────────────────────────────────────────────────────────────────────
struct DocsQueryAndToken {
    path_dictionary_instance_t* pd = nullptr;
    ovx_primpath_list_t path_list{};
    ovstage_query_handle_t query_handle = OVSTAGE_INVALID_QUERY_HANDLE;
    ovx_token_t attr_token{};
};

static void docs_make_query_and_token(ovstage_instance_t* stage, char const* prim_path, char const* attr_name,
                                       DocsQueryAndToken* out) {
    out->pd = ovstage_get_path_dictionary(stage);
    ASSERT_NE(out->pd, nullptr);

    ovx_string_t prim_str = ovx_str(prim_path);
    ASSERT_EQ(path_dictionary_create_path_list_from_strings(out->pd, &prim_str, 1, &out->path_list).status,
              OVX_API_SUCCESS);

    ASSERT_EQ(ovstage_query_from_path_list(stage, out->path_list, &out->query_handle), OVSTAGE_OK)
        << format_ovstage_last_error();

    ovx_string_t attr_str = ovx_str(attr_name);
    ASSERT_EQ(path_dictionary_create_tokens_from_strings(out->pd, &attr_str, 1, &out->attr_token).status,
              OVX_API_SUCCESS);
}

static void docs_release_query_and_token(ovstage_instance_t* stage, DocsQueryAndToken* q) {
    if (q->query_handle != OVSTAGE_INVALID_QUERY_HANDLE) {
        ovstage_release_query(stage, q->query_handle);
        q->query_handle = OVSTAGE_INVALID_QUERY_HANDLE;
    }
    if (q->pd) {
        path_dictionary_release_path_list_reference(q->pd, q->path_list);
        q->pd = nullptr;
    }
}

// ────────────────────────────────────────────────────────────────────────────
// docs_step_once
//
// Advance the renderer by one frame against /Render/Camera. Modes:
//   ordinal_or_zero == 0 → standalone-mode ovrtx_step (legacy fixture)
//   ordinal_or_zero != 0 → attached-mode ovrtx_step_with_stage(..., ordinal)
// Returns the step handle for the caller to fetch/destroy. Both paths wait
// on the enqueue and assert no op errors; a failing step returns 0 and the
// caller can detect it via HasFatalFailure().
// ────────────────────────────────────────────────────────────────────────────
static ovrtx_step_result_handle_t docs_step_once(ovrtx_renderer_t* renderer,
                                                  ovstage_ordinal_t ordinal_or_zero) {
    ovx_string_t rp_path = ovx_str("/Render/Camera");
    ovrtx_render_product_set_t products{};
    products.render_products = &rp_path;
    products.num_render_products = 1;

    ovrtx_step_result_handle_t step_handle = 0;
    ovrtx_enqueue_result_t eq;
    if (ordinal_or_zero == 0) {
        eq = ovrtx_step(renderer, products, 1.0 / 60.0, &step_handle);
    } else {
        eq = ovrtx_step_with_stage(renderer, products, 1.0 / 60.0, ordinal_or_zero, &step_handle);
    }
    EXPECT_API_SUCCESS(eq.status);
    if (eq.status == OVRTX_API_SUCCESS) {
        docs_wait_no_errors(renderer, eq.op_index);
    }
    return step_handle;
}

// ────────────────────────────────────────────────────────────────────────────
// Shared test fixture for C doc-tests that render through an attached ovstage.
//
// Provides:
//   - Per-suite ovrtx_renderer_t* (matches the pre-ovstage-port pattern used
//     by every C doc test — one renderer per test suite).
//   - Per-test ovstage_instance_t* attached to that renderer in SetUp,
//     detached and destroyed in TearDown. Matches the Python conftest.stage
//     fixture shape: renderer session-scoped, stage per-test.
//   - Convenience helpers for populating and sealing an ordinal.
//
// A derived test class wires the fixture with one line:
//
//     class MyDocsTest : public DocsOvstageTestBase {
//     protected:
//         DOCS_OVSTAGE_TEST_SUITE(MyDocsTest)
//     };
//
// Test bodies use stage_ (per-test) and suite_renderer_ (per-suite).
//
// Because gtest's ASSERT_* inside a member function only aborts that function,
// callers should follow the codebase convention (see test_base.cpp:535) and
// guard with `if (HasFatalFailure()) return;` after a setup helper if
// continuation would produce misleading cascade failures.
// ────────────────────────────────────────────────────────────────────────────

class DocsOvstageTestBase : public ::testing::Test {
protected:
    // Suite-wide renderer factory. Returns nullptr on failure; caller
    // (SetUpTestSuite) ASSERT_NEs against the result so the suite fails fast.
    static ovrtx_renderer_t* docs_create_suite_renderer(char const* suite_name) {
        TestConfig tc(suite_name);
        ovrtx_renderer_t* renderer = nullptr;
        ovrtx_result_t result = ovrtx_create_renderer(&tc.config, &renderer);
        if (result.status != OVRTX_API_SUCCESS) {
            // SetUpTestSuite runs before per-test SetUp, so print the reason
            // to stderr — otherwise the suite failure surfaces with no context.
            ovx_string_t err = ovrtx_get_last_error();
            std::fprintf(stderr,
                         "ovrtx_create_renderer failed for %s: %.*s\n",
                         suite_name,
                         static_cast<int>(err.length),
                         err.ptr ? err.ptr : "");
            return nullptr;
        }
        return renderer;
    }

    static void docs_destroy_suite_renderer(ovrtx_renderer_t** renderer) {
        if (renderer && *renderer) {
            ovrtx_destroy_renderer(*renderer);
            *renderer = nullptr;
        }
    }

    // Attach a fresh ovstage instance to `renderer` for this test. Named after
    // the test (ovrtx.docs.<Suite>.<Test>) so ovstage logs stay traceable.
    void docs_attach_stage(ovrtx_renderer_t* renderer) {
        const ::testing::TestInfo* info =
            ::testing::UnitTest::GetInstance()->current_test_info();
        stage_name_ = std::string("ovrtx.docs.")
                    + info->test_suite_name() + "." + info->name();
        ovstage_instance_desc_t desc{};
        desc.name = stage_name_.c_str();
        ovstage_api_status_t s = ovstage_create_instance(&desc, &stage_);
        ASSERT_EQ(s, OVSTAGE_OK) << format_ovstage_last_error();
        ASSERT_API_SUCCESS(ovrtx_attach_ovstage(renderer, stage_).status);
        renderer_ = renderer;
    }

    void docs_detach_stage() {
        if (stage_) {
            ovrtx_detach_ovstage(renderer_);
            ovstage_destroy_instance(stage_);
            stage_ = nullptr;
            renderer_ = nullptr;
        }
    }

    // Populate the stage from an inline USDA string at `ordinal` and seal.
    void docs_open_usd_string(char const* usda,
                              size_t usda_len,
                              ovstage_ordinal_t ordinal = 1) {
        ovstage_population_enqueue_result_t pr =
            ovstage_population_open_usd_from_string(
                stage_,
                {usda, usda_len},
                ordinal,
                /*time=*/NAN,
                OVSTAGE_POPULATION_DOMAIN_RENDERING);
        ASSERT_EQ(pr.status, OVSTAGE_OK) << format_ovstage_population_last_error();
        docs_wait_ovstage_population_no_errors(stage_, pr.op_index);
        docs_ovstage_advance_write_floor(stage_, ordinal);
    }

    // Populate the stage from a USD file at `ordinal` and seal.
    void docs_open_usd_file(char const* path,
                            ovstage_ordinal_t ordinal = 1) {
        ovstage_population_enqueue_result_t pr =
            ovstage_population_open_usd_from_file(
                stage_,
                {path, strlen(path)},
                ordinal,
                /*time=*/NAN,
                OVSTAGE_POPULATION_DOMAIN_RENDERING);
        ASSERT_EQ(pr.status, OVSTAGE_OK) << format_ovstage_population_last_error();
        docs_wait_ovstage_population_no_errors(stage_, pr.op_index);
        docs_ovstage_advance_write_floor(stage_, ordinal);
    }

    // Populate from ovrtx-test-base.usda (the canonical doc-test scene).
    void docs_load_base() {
        std::string scene = get_docs_test_data_dir() + "/ovrtx-test-base.usda";
        docs_open_usd_file(scene.c_str());
    }

    ovrtx_renderer_t*    renderer_ = nullptr;
    ovstage_instance_t*  stage_    = nullptr;
    std::string          stage_name_;
};

// Boilerplate wiring for a derived doc-test suite: per-suite renderer, per-test
// attached stage. Place inside the derived class's protected: section. The
// stringified SuiteClass name is used as the log-file basename and the ovstage
// instance name prefix.
#define DOCS_OVSTAGE_TEST_SUITE(SuiteClass)                                    \
    inline static ovrtx_renderer_t* suite_renderer_ = nullptr;                 \
    static void SetUpTestSuite() {                                             \
        suite_renderer_ = docs_create_suite_renderer(#SuiteClass);             \
        ASSERT_NE(suite_renderer_, nullptr);                                   \
    }                                                                          \
    static void TearDownTestSuite() {                                          \
        docs_destroy_suite_renderer(&suite_renderer_);                         \
    }                                                                          \
    void SetUp() override { docs_attach_stage(suite_renderer_); }              \
    void TearDown() override { docs_detach_stage(); }
