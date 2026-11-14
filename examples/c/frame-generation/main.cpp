// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
//
// DLSS Frame Generation, headless.
//
// This example exists to make one thing concrete: with frame generation enabled,
// the unscheduled camera used here produces one capture per step and returns
// N + 1 output frames, ordered [interp0 .. interp(N-1), simulated], with the simulated frame
// last. Consumers written against the single-frame shape -- anything that reaches
// for output_frames[0], or that scans frames and takes the first match -- silently
// start reading an interpolated frame instead of the simulated one.
//
// N is requested, not chosen. The renderer clamps the request to what
// the GPU supports and may decline frame generation entirely, without failing the
// step. This example reports what it asked for and what it actually got, which is
// the check every integration needs.
//
// Deliberately out of scope: presentation and frame pacing. Deciding *when* to show
// each frame needs a swapchain and a present loop; see examples/c/vulkan-interop
// for that half of the problem. Everything here runs headless and writes PNGs.

#include <ovrtx/ovrtx_config.h>
#include <ovrtx/ovrtx_types.h>
#include <ovrtx/ovrtx.h>
#include <ovstage/ovstage.h>

#include <charconv>
#include <cerrno>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <iostream>
#include <limits>
#include <string>
#include <string_view>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#endif

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

namespace {

// The scene ships beside this example: RealTimePathTracing, a single LdrColor
// render var, 1280x720. All three matter for frame generation -- see the
// compatibility notes in README.md.
constexpr char const kDefaultUsd[] = "frame-generation.usda";
constexpr char const kRenderProductPath[] = "/Render/Camera";
constexpr char const kRenderVarPath[] = "/Render/LdrColor";

constexpr double kStepDelta = 1.0 / 60.0;

// World units the logo slides along X per step. This produces clear screen-space
// motion between consecutive simulated frames while keeping enough overlapping
// content for frame generation to interpolate.
constexpr double kDefaultSweepDistance = 5.0;

// The logo's scale, orientation, and height live on a child transform in the
// scene. Runtime updates move only this parent along X, preserving that setup.
constexpr char const kLogoPath[] = "/World/Logo";

// Resolve bundled resources relative to the executable, matching the location
// populated by the CMake post-build step rather than relying on the caller's
// working directory.
bool get_executable_dir(std::filesystem::path& executable_dir) {
#ifdef _WIN32
    std::wstring path(MAX_PATH, L'\0');
    while (path.size() < 32768) {
        DWORD const length = GetModuleFileNameW(
            nullptr, path.data(), static_cast<DWORD>(path.size()));
        if (length == 0) {
            std::cerr << "Could not resolve the executable path" << std::endl;
            return false;
        }
        if (length < path.size()) {
            path.resize(length);
            executable_dir = std::filesystem::path(path).parent_path();
            return true;
        }
        path.resize(path.size() * 2);
    }
    std::cerr << "Executable path exceeds the Windows path limit" << std::endl;
    return false;
#elif defined(__linux__)
    std::error_code error;
    std::filesystem::path const executable =
        std::filesystem::canonical("/proc/self/exe", error);
    if (error) {
        std::cerr << "Could not resolve the executable path: " << error.message()
                  << std::endl;
        return false;
    }
    executable_dir = executable.parent_path();
    return true;
#else
#error "Unsupported platform"
#endif
}

// `literal_to_ovx_string(str)` comes from <ovx/types.h>; it wraps a string literal
// as an ovx_string_t without a strlen. Do not redefine it locally.

template <typename ResultT>
bool check_and_print_error(ResultT const& result, std::string_view operation) {
    if (result.status == OVRTX_API_ERROR) {
        ovx_string_t error = ovrtx_get_last_error();
        if (error.ptr && error.length > 0) {
            std::cerr << "ovrtx " << operation << " failed: "
                      << std::string_view(error.ptr, error.length) << std::endl;
        } else {
            std::cerr << "ovrtx " << operation << " failed" << std::endl;
        }
        return true;
    }
    return false;
}

bool print_ovstage_error(ovstage_instance_t* stage,
                         ovstage_api_status_t status,
                         std::string_view operation) {
    ovx_string_t error = ovstage_population_get_last_error();
    if ((!error.ptr || error.length == 0) && stage) {
        error = ovstage_get_last_error();
    }
    std::cerr << "ovstage " << operation << " failed (" << static_cast<int>(status) << ")";
    if (error.ptr && error.length > 0) {
        std::cerr << ": " << std::string_view(error.ptr, error.length);
    }
    std::cerr << std::endl;
    return true;
}

bool wait_population_op(ovstage_instance_t* stage,
                        ovstage_population_enqueue_result_t const& enqueue,
                        std::string_view operation) {
    if (enqueue.status != OVSTAGE_OK) {
        return print_ovstage_error(stage, enqueue.status, operation);
    }
    ovstage_population_op_wait_result_t wait_result{};
    ovstage_api_status_t status = ovstage_population_wait_op(
        stage, enqueue.op_index, OVSTAGE_TIMEOUT_INFINITE, &wait_result);
    if (status != OVSTAGE_OK) {
        return print_ovstage_error(stage, status, operation);
    }
    for (size_t i = 0; i < wait_result.error_op_id_count; ++i) {
        ovx_string_t error =
            ovstage_population_get_last_op_error(wait_result.error_op_ids[i]);
        std::cerr << "ovstage " << operation << ": op failed";
        if (error.ptr && error.length > 0) {
            std::cerr << ": " << std::string_view(error.ptr, error.length);
        }
        std::cerr << std::endl;
    }
    return wait_result.error_op_id_count != 0;
}

bool wait_ovstage_op(ovstage_instance_t* stage,
                     ovstage_enqueue_result_t const& enqueue,
                     std::string_view operation) {
    if (enqueue.status != OVSTAGE_OK) {
        return print_ovstage_error(stage, enqueue.status, operation);
    }
    ovstage_op_wait_result_t wait_result{};
    ovstage_api_status_t status =
        ovstage_wait_op(stage, enqueue.op_index, OVSTAGE_TIMEOUT_INFINITE, &wait_result);
    ovstage_release_op(stage, enqueue.op_index);
    if (status != OVSTAGE_OK) {
        return print_ovstage_error(stage, status, operation);
    }
    for (size_t i = 0; i < wait_result.error_op_id_count; ++i) {
        ovx_string_t error = ovstage_get_last_op_error(stage, wait_result.error_op_ids[i]);
        std::cerr << "ovstage " << operation << ": op failed";
        if (error.ptr && error.length > 0) {
            std::cerr << ": " << std::string_view(error.ptr, error.length);
        }
        std::cerr << std::endl;
    }
    return wait_result.error_op_id_count != 0;
}

bool commit_ovstage_ordinal(ovstage_instance_t* stage, ovstage_ordinal_t ordinal) {
    ovstage_write_floor_desc_t write_floor{};
    write_floor.ordinal = ordinal;
    write_floor.scope = OVSTAGE_SCOPE_ALL;
    return wait_ovstage_op(
        stage, ovstage_advance_write_floor(stage, &write_floor), "advance_write_floor");
}

// Resolve a single prim by USD path into a reusable ovstage query handle.
bool create_validated_prim_query(ovstage_instance_t* stage,
                                 std::string_view prim_path,
                                 ovstage_query_handle_t* out_query) {
    ovx_string_t path = {prim_path.data(), prim_path.size()};
    ovstage_predicate_t predicate{};
    predicate.attribute.string = literal_to_ovx_string("usd-path");
    predicate.op = OVSTAGE_FILTER_OP_IN;
    predicate.values = &path;
    predicate.value_count = 1;

    ovstage_filter_t filter{};
    filter.predicates = &predicate;
    filter.count = 1;

    if (wait_ovstage_op(
            stage, ovstage_query(stage, &filter, nullptr, 0, out_query), "query_prim")) {
        if (*out_query != OVSTAGE_INVALID_QUERY_HANDLE) {
            wait_ovstage_op(stage, ovstage_release_query(stage, *out_query), "release_query");
            *out_query = OVSTAGE_INVALID_QUERY_HANDLE;
        }
        return true;
    }

    ovstage_query_result_t fetched{};
    ovstage_api_status_t status =
        ovstage_fetch_query_result(stage, *out_query, OVSTAGE_TIMEOUT_INFINITE, &fetched);
    if (status != OVSTAGE_OK) {
        wait_ovstage_op(stage, ovstage_release_query(stage, *out_query), "release_query");
        *out_query = OVSTAGE_INVALID_QUERY_HANDLE;
        return print_ovstage_error(stage, status, "fetch_query_result");
    }

    bool failed = false;
    if (fetched.total_prim_count != 1) {
        std::cerr << "Prim '" << prim_path << "' not found in the populated scene" << std::endl;
        failed = true;
    }
    if (ovstage_release_query_result(stage, &fetched) != OVSTAGE_OK) {
        failed = true;
    }
    if (failed) {
        wait_ovstage_op(stage, ovstage_release_query(stage, *out_query), "release_query");
        *out_query = OVSTAGE_INVALID_QUERY_HANDLE;
    }
    return failed;
}

// [snippet:enable-frame-generation]
// Frame generation is a per-RenderProduct render setting: two attributes on the
// RenderProduct prim, read by the renderer out of the runtime scene. Authoring them
// through ovstage is equivalent to declaring them in the USD file, and does NOT
// require the RTX settings API schema to be applied to the prim.
//
// Write both attributes unconditionally, including when disabling. The scene may
// already carry a frameGeneration opinion (several stock Omniverse viewport
// RenderProducts do), so writing only the "on" case leaves you unable to turn it
// back off, and writing nothing leaves the scene in charge rather than your app.
bool author_frame_generation(ovstage_instance_t* stage,
                             ovstage_query_handle_t render_product_query,
                             ovstage_ordinal_t ordinal,
                             bool enabled,
                             int requested_interpolated_frames) {
    uint8_t enabled_value = enabled ? 1 : 0;
    int64_t shape[1] = {1};

    DLTensor enabled_dl{};
    enabled_dl.data = &enabled_value;
    enabled_dl.device.device_type = kDLCPU;
    enabled_dl.device.device_id = 0;
    enabled_dl.ndim = 1;
    enabled_dl.shape = shape;
    enabled_dl.dtype.code = kDLBool;
    enabled_dl.dtype.bits = 8;
    enabled_dl.dtype.lanes = 1;

    // Zero or unset requests one interpolated frame. Explicit larger requests
    // are clamped to the hardware maximum (1 on Ada, 3 on Blackwell), so
    // asking for 3 on Ada yields 1, not an error.
    int32_t frame_count_value = requested_interpolated_frames;
    DLTensor frame_count_dl = enabled_dl;
    frame_count_dl.data = &frame_count_value;
    frame_count_dl.dtype.code = kDLInt;
    frame_count_dl.dtype.bits = 32;

    ovstage_write_data_t enabled_write{};
    enabled_write.tensors = &enabled_dl;
    enabled_write.tensor_count = 1;

    ovstage_write_data_t frame_count_write = enabled_write;
    frame_count_write.tensors = &frame_count_dl;

    ovx_token_or_string_t enabled_attribute{};
    enabled_attribute.string = literal_to_ovx_string("omni:rtx:dlss:frameGeneration");
    ovx_token_or_string_t frame_count_attribute{};
    frame_count_attribute.string =
        literal_to_ovx_string("omni:rtx:dlss:frameGenerationInterpolatedFrameCount");

    // |= rather than ||: the second write must run even if the first failed.
    bool failed = wait_ovstage_op(stage,
                                  ovstage_write_attribute(stage,
                                                          render_product_query,
                                                          enabled_attribute,
                                                          ordinal,
                                                          enabled_write,
                                                          OVSTAGE_PRIM_MODE_UPSERT),
                                  "write_frame_generation");
    failed |= wait_ovstage_op(stage,
                              ovstage_write_attribute(stage,
                                                      render_product_query,
                                                      frame_count_attribute,
                                                      ordinal,
                                                      frame_count_write,
                                                      OVSTAGE_PRIM_MODE_UPSERT),
                              "write_interpolated_frame_count");
    return failed;
}
// [/snippet:enable-frame-generation]

// Animate the scene so consecutive rendered frames differ. Frame generation
// interpolates motion; against a completely static scene there is nothing to
// interpolate and the result is uninteresting even when it is working.
//
// MOVE THE SUBJECT, NOT THE CAMERA. Sweeping the standard documentation logo
// across the shared ground produces unambiguous screen-space motion. The fixed,
// elevated camera keeps the ground visible so the four output frames have a
// stable spatial reference.
bool write_prim_transform(ovstage_instance_t* stage,
                          ovstage_query_handle_t query,
                          ovstage_ordinal_t ordinal,
                          double const transform[16],
                          char const* what) {
    DLTensor transform_dl{};
    transform_dl.data = const_cast<double*>(transform);
    transform_dl.device.device_type = kDLCPU;
    transform_dl.device.device_id = 0;
    transform_dl.ndim = 1;
    int64_t shape[1] = {1};
    transform_dl.shape = shape;
    transform_dl.dtype.code = kDLFloat;
    transform_dl.dtype.bits = 64;
    transform_dl.dtype.lanes = 16;

    ovstage_write_data_t write_data{};
    write_data.tensors = &transform_dl;
    write_data.tensor_count = 1;
    write_data.semantic = OVSTAGE_SEMANTIC_MATRIX;

    ovx_token_or_string_t attribute{};
    attribute.string = literal_to_ovx_string("omni:xform");

    return wait_ovstage_op(stage,
                           ovstage_write_attribute(stage,
                                                   query,
                                                   attribute,
                                                   ordinal,
                                                   write_data,
                                                   OVSTAGE_PRIM_MODE_UPSERT),
                           what);
}

/// Move the logo at constant speed so consecutive captures show different positions.
bool sweep_logo(ovstage_instance_t* stage,
                ovstage_query_handle_t logo_query,
                ovstage_ordinal_t ordinal,
                int step_index,
                double sweep_distance) {
    double const x = sweep_distance * static_cast<double>(step_index);
    double const transform[16] = {1.0, 0.0, 0.0, 0.0,
                                  0.0, 1.0, 0.0, 0.0,
                                  0.0, 0.0, 1.0, 0.0,
                                  x, 0.0, 0.0, 1.0};
    return write_prim_transform(stage, logo_query, ordinal, transform, "write_logo_transform");
}

// [snippet:find-render-product-output]
// Locate one RenderProduct's output by path. Note what this does NOT do: it does
// not descend into output_frames looking for a render var. Under frame generation
// every frame of the product exposes the SAME render var path, so a search that
// returns the first matching var returns interp0 -- an interpolated frame -- and
// never the rendered one. Select the product first, then index frames explicitly.
ovrtx_render_product_output_t const* find_render_product_output(
    ovrtx_render_product_set_outputs_t const& outputs, std::string_view render_product_path) {
    for (size_t i = 0; i < outputs.output_count; ++i) {
        ovrtx_render_product_output_t const& output = outputs.outputs[i];
        if (output.render_product_path.ptr &&
            std::string_view(output.render_product_path.ptr,
                             output.render_product_path.length) == render_product_path) {
            return &output;
        }
    }
    return nullptr;
}
// [/snippet:find-render-product-output]

// [snippet:classify-output-frames]
// All returned frames must belong to one completed capture, as in this example.
// Scheduled cameras can return multiple simulated captures, so their total frame
// count cannot classify interpolation. For one capture, frames [0, N) are
// interpolated in presentation order and the last frame is simulated; N is zero
// when frame generation is off or declined.
//
// Never hardcode N. Derive it from output_frame_count on every step -- the count
// can change at runtime when the renderer starts or stops honouring the request.
/// Frame indices for a result containing exactly one completed camera capture.
struct FrameLayout {
    size_t interpolated_count;  // N
    size_t simulated_frame_index;  // always output_frame_count - 1
    bool frame_generation_active;
};

/// Classify a nonempty, single-capture result; multi-capture steps are unsupported.
FrameLayout classify_output_frames(ovrtx_render_product_output_t const& output) {
    FrameLayout layout{};
    layout.simulated_frame_index = output.output_frame_count - 1;
    layout.interpolated_count = output.output_frame_count - 1;
    layout.frame_generation_active = output.output_frame_count > 1;
    return layout;
}
// [/snippet:classify-output-frames]

// Map one frame's LdrColor to the CPU and write it out as a PNG.
bool save_frame_png(ovrtx_renderer_t* renderer,
                    ovrtx_render_product_frame_output_t const& frame,
                    std::string const& filename) {
    ovrtx_render_var_output_handle_t handle = OVRTX_INVALID_RENDER_VAR_OUTPUT_HANDLE;
    for (size_t v = 0; v < frame.render_var_count; ++v) {
        ovrtx_render_product_render_var_output_t const& var = frame.output_render_vars[v];
        if (var.render_var_path.ptr &&
            std::string_view(var.render_var_path.ptr, var.render_var_path.length) ==
                std::string_view(kRenderVarPath)) {
            handle = var.output_handle;
            break;
        }
    }
    if (handle == OVRTX_INVALID_RENDER_VAR_OUTPUT_HANDLE) {
        std::cerr << "  " << filename << ": LdrColor not present on this frame" << std::endl;
        return true;
    }

    ovrtx_map_output_description_t map_desc{};
    map_desc.device_type = OVRTX_MAP_DEVICE_TYPE_CPU;
    ovrtx_render_var_output_t mapped{};
    if (check_and_print_error(
            ovrtx_map_render_var_output(
                renderer, handle, &map_desc, ovrtx_timeout_infinite, &mapped),
            "map_render_var_output")) {
        return true;
    }

    bool failed = false;
    if (mapped.num_tensors != 1) {
        std::cerr << "  unexpected LdrColor tensor count: " << mapped.num_tensors << std::endl;
        failed = true;
    } else {
        DLTensor const& tensor = *mapped.tensors[0].dl;
        if (tensor.ndim != 3 || !tensor.shape || tensor.shape[2] != 4) {
            std::cerr << "  unexpected LdrColor layout, expected [H, W, 4]" << std::endl;
            failed = true;
        } else {
            int const width = static_cast<int>(tensor.shape[1]);
            int const height = static_cast<int>(tensor.shape[0]);
            if (stbi_write_png(
                    filename.c_str(), width, height, 4, tensor.data, 4 * width) == 0) {
                std::cerr << "  failed to write " << filename << std::endl;
                failed = true;
            } else {
                std::cout << "  wrote " << filename << " (" << width << "x" << height << ")"
                          << std::endl;
            }
        }
    }

    ovrtx_cuda_sync_t no_sync{};
    failed |= check_and_print_error(
        ovrtx_unmap_render_var_output(renderer, mapped.map_handle, no_sync),
        "unmap_render_var_output");
    return failed;
}

void print_usage() {
    std::cout
        << "Usage: frame-generation [options]\n"
        << "  --usd <path>       USD layer to render (default: " << kDefaultUsd << ")\n"
        << "                     Must complete exactly one camera capture per step.\n"
        << "  --frames <n>       Non-negative interpolated-frame count; 0 requests 1.\n"
        << "                     Clamped to the hardware maximum. (default: 0)\n"
        << "  --steps <n>        Steps to render and save (default: 2)\n"
        << "  --sweep <units>    World units the logo slides along X per step\n"
        << "                     (default: 5). This is the motion frame generation\n"
        << "                     interpolates.\n"
        << "  --no-frame-gen     Author frameGeneration=0, for an A/B against the same\n"
        << "                     scene.\n"
        << "  --help             Show this message\n";
}

}  // namespace

int main(int argc, char** argv) {
    std::string usd_path;
    int requested_frames = 0;
    int steps = 2;
    bool frame_generation = true;
    double sweep_distance = kDefaultSweepDistance;

    for (int i = 1; i < argc; ++i) {
        std::string_view arg = argv[i];
        // Reject malformed or overflowing counts before starting either runtime.
        auto next = [&](int& out, int minimum, int maximum) {
            if (i + 1 >= argc) {
                std::cerr << "Missing value for " << arg << std::endl;
                return false;
            }

            std::string_view const value = argv[++i];
            std::from_chars_result const parsed =
                std::from_chars(value.data(), value.data() + value.size(), out);
            if (parsed.ec != std::errc{} || parsed.ptr != value.data() + value.size() ||
                out < minimum || out > maximum) {
                std::cerr << arg << " must be an integer from " << minimum
                          << " to " << maximum << std::endl;
                return false;
            }
            return true;
        };
        if (arg == "--help") {
            print_usage();
            return 0;
        } else if (arg == "--usd" && i + 1 < argc) {
            usd_path = argv[++i];
        } else if (arg == "--frames") {
            if (!next(requested_frames, 0, std::numeric_limits<int>::max())) return 1;
        } else if (arg == "--steps") {
            if (!next(steps, 1, std::numeric_limits<int>::max())) return 1;
        } else if (arg == "--sweep") {
            if (i + 1 >= argc) {
                std::cerr << "Missing value for --sweep" << std::endl;
                return 1;
            }
            char const* value = argv[++i];
            char* end = nullptr;
            errno = 0;
            sweep_distance = std::strtod(value, &end);
            if (end == value || *end != '\0' || errno == ERANGE ||
                !std::isfinite(sweep_distance)) {
                std::cerr << "--sweep must be a finite number" << std::endl;
                return 1;
            }
        } else if (arg == "--no-frame-gen") {
            frame_generation = false;
        } else {
            std::cerr << "Unrecognized argument: " << arg << std::endl;
            print_usage();
            return 1;
        }
    }

    if (usd_path.empty()) {
        std::filesystem::path executable_dir;
        if (!get_executable_dir(executable_dir)) {
            return 1;
        }
        usd_path = (executable_dir / kDefaultUsd).string();
    }

    ovrtx_renderer_t* renderer = nullptr;
    ovstage_instance_t* stage = nullptr;
    bool stage_attached = false;
    ovstage_ordinal_t ordinal = 1;
    ovstage_query_handle_t render_product_query = OVSTAGE_INVALID_QUERY_HANDLE;
    ovstage_query_handle_t logo_query = OVSTAGE_INVALID_QUERY_HANDLE;
    ovrtx_result_t result;

    ovx_string_t ovrtx_package_root = {
        OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx",
        sizeof(OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx") - 1};
    ovrtx_config_entry_t config_entries[] = {
        ovrtx_config_entry_binary_package_root_path(ovrtx_package_root),
    };
    ovrtx_config_t config{};
    config.entries = config_entries;
    config.entry_count = sizeof(config_entries) / sizeof(config_entries[0]);

    std::cerr << "Creating renderer (first run compiles and caches shaders)..." << std::endl;
    result = ovrtx_create_renderer(&config, &renderer);
    if (check_and_print_error(result, "create_renderer")) {
        return 1;
    }

    auto cleanup = [&](int exit_code) {
        int code = exit_code;
        if (render_product_query != OVSTAGE_INVALID_QUERY_HANDLE) {
            wait_ovstage_op(
                stage, ovstage_release_query(stage, render_product_query), "release_query");
        }
        if (logo_query != OVSTAGE_INVALID_QUERY_HANDLE) {
            wait_ovstage_op(stage, ovstage_release_query(stage, logo_query), "release_query");
        }
        if (stage_attached && check_and_print_error(ovrtx_detach_ovstage(renderer), "detach_ovstage")) {
            code = 1;
        }
        if (stage && ovstage_destroy_instance(stage) != OVSTAGE_OK) {
            code = 1;
        }
        if (renderer && check_and_print_error(ovrtx_destroy_renderer(renderer), "destroy_renderer")) {
            code = 1;
        }
        ovstage_shutdown();
        return code;
    };

    ovx_string_t ovstage_package_root = {
        OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovstage",
        sizeof(OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovstage") - 1};
    ovstage_config_entry_t stage_config_entries[] = {
        ovstage_config_entry_binary_package_root_path(ovstage_package_root),
    };
    ovstage_config_t stage_config{};
    stage_config.entries = stage_config_entries;
    stage_config.entry_count = sizeof(stage_config_entries) / sizeof(stage_config_entries[0]);
    ovstage_api_status_t stage_status = ovstage_initialize(&stage_config);
    if (stage_status != OVSTAGE_OK) {
        print_ovstage_error(nullptr, stage_status, "initialize");
        return cleanup(1);
    }

    ovstage_instance_desc_t stage_desc{};
    stage_desc.name = "frame-generation";
    stage_status = ovstage_create_instance(&stage_desc, &stage);
    if (stage_status != OVSTAGE_OK) {
        print_ovstage_error(stage, stage_status, "create_instance");
        return cleanup(1);
    }

    result = ovrtx_attach_ovstage(renderer, stage);
    if (check_and_print_error(result, "attach_ovstage")) {
        return cleanup(1);
    }
    stage_attached = true;

    std::cerr << "Loading " << usd_path << "..." << std::endl;
    if (wait_population_op(stage,
                           ovstage_population_open_usd_from_file(
                               stage,
                               {usd_path.c_str(), usd_path.size()},
                               ordinal,
                               /* time = */ 0.0,
                               OVSTAGE_POPULATION_DOMAIN_RENDERING),
                           "population_open_usd_from_file") ||
        commit_ovstage_ordinal(stage, ordinal)) {
        return cleanup(1);
    }

    if (create_validated_prim_query(stage, kRenderProductPath, &render_product_query) ||
        create_validated_prim_query(stage, kLogoPath, &logo_query)) {
        return cleanup(1);
    }

    ++ordinal;
    if (author_frame_generation(
            stage, render_product_query, ordinal, frame_generation, requested_frames) ||
        commit_ovstage_ordinal(stage, ordinal)) {
        return cleanup(1);
    }

    std::cout << "\nFrame generation: " << (frame_generation ? "requested" : "disabled")
              << ", interpolated frames requested: "
              << (requested_frames == 0 ? std::string("1 (default)")
                                        : std::to_string(requested_frames))
              << std::endl;

    ovrtx_render_product_set_t render_products{};
    ovx_string_t render_product_str = {kRenderProductPath, strlen(kRenderProductPath)};
    render_products.render_products = &render_product_str;
    render_products.num_render_products = 1;

    // [snippet:step-and-inspect-frames]
    // Save every step, including startup when interpolation may be unavailable.
    for (int step_index = 0; step_index < steps; ++step_index) {
        ++ordinal;
        if (sweep_logo(stage, logo_query, ordinal, step_index, sweep_distance) ||
            commit_ovstage_ordinal(stage, ordinal)) {
            return cleanup(1);
        }

        ovrtx_step_result_handle_t step_result = OVRTX_INVALID_STEP_RESULT_HANDLE;
        ovrtx_enqueue_result_t enqueue = ovrtx_step_with_stage(
            renderer, render_products, kStepDelta, ordinal, &step_result);
        if (check_and_print_error(enqueue, "step")) {
            return cleanup(1);
        }

        ovrtx_op_wait_result_t wait_result{};
        if (check_and_print_error(
                ovrtx_wait_op(renderer, enqueue.op_index, ovrtx_timeout_infinite, &wait_result),
                "wait_op")) {
            ovrtx_destroy_results(renderer, step_result);
            return cleanup(1);
        }

        for (size_t i = 0; i < wait_result.num_error_ops; ++i) {
            ovx_string_t const error = ovrtx_get_last_op_error(wait_result.error_op_ids[i]);
            std::cerr << "ovrtx step failed";
            if (error.ptr && error.length > 0) {
                std::cerr << ": " << std::string_view(error.ptr, error.length);
            }
            std::cerr << std::endl;
        }
        if (wait_result.num_error_ops != 0) {
            ovrtx_destroy_results(renderer, step_result);
            return cleanup(1);
        }

        ovrtx_render_product_set_outputs_t outputs{};
        if (check_and_print_error(
                ovrtx_fetch_results(renderer, step_result, ovrtx_timeout_infinite, &outputs),
                "fetch_results")) {
            ovrtx_destroy_results(renderer, step_result);
            return cleanup(1);
        }

        ovrtx_render_product_output_t const* output =
            find_render_product_output(outputs, kRenderProductPath);
        if (!output || output->output_frame_count == 0) {
            std::cerr << "No output for render product " << kRenderProductPath << std::endl;
            ovrtx_destroy_results(renderer, step_result);
            return cleanup(1);
        }

        FrameLayout const layout = classify_output_frames(*output);
        // [/snippet:step-and-inspect-frames]

        bool save_failed = false;
        std::cout << "\nStep " << step_index << ": output_frame_count = "
                  << output->output_frame_count << " ("
                  << layout.interpolated_count << " interpolated + 1 simulated)"
                  << std::endl;

        if (frame_generation && layout.frame_generation_active && requested_frames > 0 &&
                   layout.interpolated_count < static_cast<size_t>(requested_frames)) {
            std::cout << "  Requested " << requested_frames << " interpolated frame(s), got "
                      << layout.interpolated_count
                      << " -- clamped to the hardware maximum." << std::endl;
        }

        // Frames are placed at evenly spaced instants across the step's
        // simulation window, simulated frame last. These timestamps are the
        // input a pacing scheme needs to decide *when* to present each frame;
        // this example only reports them. See examples/c/vulkan-interop for
        // pacing.
        std::cout << "  simulation window [" << outputs.simulation_start_time << ", "
                  << outputs.simulation_end_time << "]" << std::endl;
        for (size_t f = 0; f < output->output_frame_count; ++f) {
            bool const is_simulated = (f == layout.simulated_frame_index);
            std::cout << "    frame " << f << " t=" << output->output_frames[f].frame_end_time
                      << (is_simulated ? "  [simulated]" : "  [interpolated]") << std::endl;
        }

        for (size_t f = 0; f < output->output_frame_count; ++f) {
            bool const is_simulated = (f == layout.simulated_frame_index);
            std::string const name = "step" + std::to_string(step_index) + "_" +
                                     (is_simulated ? "simulated"
                                              : "interp" + std::to_string(f)) +
                                     ".png";
            save_failed |= save_frame_png(renderer, output->output_frames[f], name);
        }

        bool const destroy_failed = check_and_print_error(
            ovrtx_destroy_results(renderer, step_result), "destroy_results");
        if (save_failed || destroy_failed) {
            return cleanup(1);
        }
    }

    return cleanup(0);
}
