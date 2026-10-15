// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
// All rights reserved. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "camera/orbit_camera.hpp"
#include "cuda/cuda_kernel.hpp"
#include "glsl/spirv_loader.hpp"
#include "vk/vulkan_context.hpp"
#include <cuda.h>
#include <ovrtx/ovrtx.h>
#include <ovrtx/ovrtx_config.h>
#include <ovstage/ovstage.h>
#include <ovx/path_dictionary/path_dictionary.h>

#define GLFW_INCLUDE_VULKAN
#define GLFW_INCLUDE_NONE
#include <GLFW/glfw3.h>

#include <glm/gtc/type_ptr.hpp>
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

#include <algorithm>
#include <array>
#include <chrono>
#include <numeric>
#include <thread>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <iostream>
#include <optional>
#include <string>
#include <string_view>
#include <tuple>
#include <utility>
#include <vector>

// Window dimensions
constexpr int WINDOW_WIDTH = 1920;
constexpr int WINDOW_HEIGHT = 1080;
constexpr int32_t CUDA_DEVICE_ID = 0;
static constexpr char ACTIVE_CUDA_GPUS[] = "0";

// Selection outline group and its style. Picked prims are assigned to this
// group; group 0 clears the outline. The style is the per-group outline and
// translucent fill color registered with the renderer at startup.
constexpr uint8_t SELECTED_OUTLINE_GROUP = 1;
constexpr ovrtx_selection_group_style_t SELECTED_OUTLINE_STYLE = {
    {0.462745f, 0.725490f, 0.000000f, 1.0f},
    {0.462745f, 0.725490f, 0.000000f, 0.1f},
};

// Mouse state for orbit camera and viewport picking.
static bool g_camera_mouse_pressed = false;
static double g_last_mouse_x = 0.0;
static double g_last_mouse_y = 0.0;
static bool g_camera_dirty = false;
static OrbitCamera* g_orbit_camera = nullptr;

struct PickDragState {
    bool left_pressed = false;
    bool dragging = false;
    bool pending_query = false;
    bool pending_is_drag = false;
    double press_x = 0.0;
    double press_y = 0.0;
    double current_x = 0.0;
    double current_y = 0.0;
    double pending_start_x = 0.0;
    double pending_start_y = 0.0;
    double pending_end_x = 0.0;
    double pending_end_y = 0.0;
};

struct PickQueryNdc {
    float left_ndc = 0.0f;
    float top_ndc = 0.0f;
    float right_ndc = 0.0f;
    float bottom_ndc = 0.0f;
};

struct MarqueeOverlay {
    bool visible = false;
    float left = 0.0f;
    float top = 0.0f;
    float right = 0.0f;
    float bottom = 0.0f;
};

struct PickedPrims {
    std::vector<ovx_primpath_t> path_ids;
    std::vector<std::string> paths;
};

struct OverlayPushConstants {
    float rect[4];
    float viewport_size[2];
    float pad[2];
};

static PickDragState g_pick_drag;
static constexpr double PICK_DRAG_THRESHOLD_PIXELS = 4.0;

// Scene units for distance scaling
enum class Units { Centimeters, Meters };

// Default scene configuration
static constexpr char const* DEFAULT_USD_FILE_URL =
    "https://omniverse-content-production.s3.us-west-2.amazonaws.com/Samples/"
    "Robot-OVRTX/robot-ovrtx.usda";
static constexpr char const* DEFAULT_RENDER_PRODUCT_PATH = "/Render/Camera";
static constexpr char const* DEFAULT_CAMERA_PRIM_PATH = "/World/Camera";
static constexpr UpAxis DEFAULT_UP_AXIS = UpAxis::Z;
static constexpr Units DEFAULT_SCENE_UNITS = Units::Meters;

// Interpolated frames inserted per rendered frame when DLSS Frame Generation is
// on. 0 leaves the count up to the renderer; any other value is clamped to what
// the GPU supports (1 on Ada, 3 on Blackwell).
static constexpr int DEFAULT_DLSSG_INTERPOLATED_FRAMES = 0;

static auto get_executable_dir() -> std::filesystem::path;
static void
mouse_button_callback(GLFWwindow* window, int button, int action, int mods);
static void
cursor_position_callback(GLFWwindow* window, double xpos, double ypos);
static void scroll_callback(GLFWwindow* window, double xoffset, double yoffset);
static void print_usage(char const* program_name);
static bool parse_present_mode(std::string_view value, PresentMode& mode);
static bool parse_args(int argc,
                       char* argv[],
                       std::string& usd_file,
                       std::string& render_product,
                       std::string& camera_prim_path,
                       UpAxis& up_axis,
                       Units& units,
                       int& num_frames,
                       bool& headless,
                       bool& dlssg_enabled,
                       int& dlssg_interpolated_frames,
                       PresentMode& present_mode,
                       bool& pace_frames);
static bool print_ovstage_error(ovstage_instance_t* stage,
                                ovstage_api_status_t status,
                                std::string_view operation);
static bool wait_ovstage_op(ovstage_instance_t* stage,
                            ovstage_enqueue_result_t const& enqueue_result,
                            std::string_view operation);
static bool wait_population_op(ovstage_instance_t* stage,
                               ovstage_population_enqueue_result_t const& enqueue_result,
                               std::string_view operation);
static bool commit_ovstage_ordinal(ovstage_instance_t* stage,
                                   ovstage_ordinal_t ordinal);
static bool create_validated_prim_query(ovstage_instance_t* stage,
                                        std::string_view prim_path,
                                        ovstage_query_handle_t* out_query);
static bool write_camera_transform(ovstage_instance_t* stage,
                                   ovstage_query_handle_t camera_query,
                                   ovstage_ordinal_t ordinal,
                                   double const* transform_data);
static bool author_dlssg_settings(ovstage_instance_t* stage,
                                  std::string_view render_product_path,
                                  ovstage_ordinal_t ordinal,
                                  bool enabled,
                                  int interpolated_frames);
static auto find_accumulation_status(
    ovrtx_render_product_set_outputs_t const& outputs,
    std::string_view render_product_path) -> std::optional<ovrtx_accumulation_status_t>;
static auto format_pt_accumulation_feedback(ovrtx_accumulation_status_t const& accumulation_status)
    -> std::string;
static void update_window_title(GLFWwindow* window,
                                ovrtx_accumulation_status_t const& accumulation_status);
static void refresh_render_feedback(GLFWwindow* window,
                                    ovrtx_accumulation_status_t& accumulation_status,
                                    ovrtx_render_product_set_outputs_t const& outputs,
                                    std::string_view render_product_path);
template <typename ResultT>
static bool check_and_print_error(ResultT const& result,
                                  std::string_view operation);

// Output type determines pixel format for CUDA-Vulkan interop
enum class OutputType { HdrColor, LdrColor };

static auto vulkan_format_for_output(OutputType type) -> VkFormat;
static auto cuda_format_for_output(OutputType type) -> CudaImageFormat;
static auto output_type_name(OutputType type) -> char const*;
static void print_frame_time_stats(int total_frames,
                                   std::vector<double> const& cpu_times_ms,
                                   std::vector<double> const& vulkan_times_ms,
                                   std::vector<double> const& cuda_times_ms);
static void record_rendering_state(CommandBuffer& cmd,
                                   VulkanContext& vk,
                                   uint32_t swapchain_image_index,
                                   ShaderHandle vert_shader,
                                   ShaderHandle frag_shader,
                                   ShaderHandle overlay_vert_shader,
                                   ShaderHandle overlay_frag_shader,
                                   SampledImageHandle read_image_handle,
                                   MarqueeOverlay const& marquee);
static void record_marquee_overlay(CommandBuffer& cmd,
                                   VulkanContext& vk,
                                   ShaderHandle overlay_vert_shader,
                                   ShaderHandle overlay_frag_shader,
                                   MarqueeOverlay const& marquee);
static auto current_marquee_overlay(GLFWwindow* window) -> MarqueeOverlay;
static auto pending_pick_query_ndc(GLFWwindow* window,
                                   int tex_width,
                                   int tex_height) -> std::optional<PickQueryNdc>;
static auto find_render_var_output(ovrtx_render_product_set_outputs_t const& outputs,
                                   std::string_view render_var_path)
    -> ovrtx_render_var_output_handle_t;
// Outcome of one pick-output map attempt, mirroring CopyOutputResult. NotReady
// means the pick hit is not mappable yet and the caller should retry later.
enum class PickOutputResult {
    Read,
    NotReady,
    Failed
};

static PickOutputResult process_pick_output(
    ovrtx_renderer_t* renderer,
    path_dictionary_instance_t* path_dictionary,
    ovrtx_render_var_output_handle_t pick_output_handle,
    ovrtx_timeout_t map_timeout,
    std::vector<ovx_primpath_t>& selected_prim_path_ids);
static bool configure_selection_style(ovrtx_renderer_t* renderer);
static bool update_selection_outline(ovrtx_renderer_t* renderer,
                                     std::vector<ovx_primpath_t> const& previous_selection,
                                     std::vector<ovx_primpath_t> const& next_selection);
static bool write_selection_outline_group(ovrtx_renderer_t* renderer,
                                          std::vector<ovx_primpath_t> const& prim_path_ids,
                                          uint8_t group_id);
static PickOutputResult read_picked_prims(
    ovrtx_renderer_t* renderer,
    path_dictionary_instance_t* path_dictionary,
    ovrtx_render_var_output_handle_t pick_output_handle,
    ovrtx_timeout_t map_timeout,
    PickedPrims& picked_prims);
static auto resolve_primpath(path_dictionary_instance_t* path_dictionary,
                             ovx_primpath_t prim_path) -> std::string;
static void print_picked_prims(std::vector<std::string> const& prim_paths);
static bool ovx_string_equals(ovx_string_t value, std::string_view expected);
static auto find_render_var_tensor(ovrtx_render_var_output_t const& output,
                                   std::string_view tensor_name) -> DLTensor const*;
static auto find_render_var_param(ovrtx_render_var_output_t const& output,
                                  std::string_view param_name) -> DLTensor const*;
static auto checksum_pixels(std::vector<uint8_t> const& pixels) -> uint64_t;

// Search ovrtx results for the color output of every frame the render product
// produced, in presentation order, preferring HdrColor over LdrColor. The output
// type is only reported during the startup probe: the Vulkan image format and
// `cuda_format` are fixed from it, so the steady-state loops must not re-derive
// it and silently disagree with the buffers they copy into.
static bool collect_color_outputs(
    ovrtx_render_product_set_outputs_t const& outputs,
    std::string_view render_product_path,
    std::vector<ovrtx_render_var_output_handle_t>& color_outputs,
    OutputType* detected_type = nullptr);
// Outcome of one map-copy attempt. NotReady means the renderer has not finished
// producing that output frame yet and the caller should retry later.
enum class CopyOutputResult {
    Copied,
    NotReady,
    Failed
};

static CopyOutputResult copy_output_to_surface(
    ovrtx_renderer_t* renderer,
    ovrtx_render_var_output_handle_t color_output,
    int image_index,
    CudaImageFormat cuda_format,
    CUstream cuda_stream,
    CUevent copy_done_event,
    ovrtx_timeout_t map_timeout,
    ovrtx_render_var_output_map_handle_t* out_map_handle);
static bool release_mapped_output(
    ovrtx_renderer_t* renderer,
    ovrtx_render_var_output_map_handle_t map_handle,
    CUevent copy_done_event);

// One shared image plus the CUDA and ovrtx state that decides when it may be
// shown and when its mapping may be released.
//
// Writing  - a copy into this image has been queued on the CUDA stream
// Ready    - the copy has landed; the image may be shown
// Showing  - Vulkan is sampling this image
// Free     - available for the next copy
//
// Each slot owns its own copy_done event because several copies are in flight at
// once; a single shared event was only safe while the unmap blocked the loop
// until each copy had landed.
struct FrameSlot {
    // Per-slot events: several copies are in flight at once, so a shared pair
    // could not attribute a duration to a particular frame, and a shared
    // completion event was only safe while the unmap blocked the loop.
    CUevent copy_start = nullptr;
    CUevent copy_done = nullptr;
    ovrtx_render_var_output_map_handle_t map_handle = 0;
    bool mapped = false;
    uint64_t timeline_value = 0;
    // `--num-frames` must save a real rendered frame, never an interpolated one.
    bool holds_real_frame = false;

    enum class State { Free, Writing, Ready, Showing };
    State state = State::Free;
};

// The frames produced by one ovrtx step, consumed one per presented frame. With
// DLSS Frame Generation enabled a step produces several; the next step is only
// enqueued once they have all been copied out.
struct PendingFrames {
    ovrtx_step_result_handle_t step_result = 0;
    std::vector<ovrtx_render_var_output_handle_t> color_outputs;
    size_t next = 0;
    // A step result is fetched before its output frames are necessarily
    // mappable, so the fetch and the per-frame maps are polled as two stages.
    bool results_fetched = false;
    // A pick query is enqueued before the step and its output is read from the
    // step's results, so the flag has to survive until the fetch succeeds. The
    // map is polled like the color one, so it also has to survive however many
    // iterations the pick hit takes to become mappable.
    bool pick_query_submitted = false;
    // Resolved at fetch time and held until the pick is read, because the
    // outputs struct it came from is reused by the next step's fetch.
    ovrtx_render_var_output_handle_t pick_output = OVRTX_INVALID_HANDLE;
    std::chrono::steady_clock::time_point step_start;

    bool in_flight() const { return step_result != 0; }
    bool drained() const {
        return results_fetched && next >= color_outputs.size();
    }
    // The pick output belongs to the step result, so the result has to outlive
    // the pick read as well as the last color copy.
    bool retirable() const { return drained() && !pick_query_submitted; }
};

// State for the one-time report of whether frame generation actually engaged.
// DLSS-G interpolates between two rendered frames, so the steps right after a
// history reset legitimately produce a single frame; only report a failure once
// a short warmup has passed without extra frames appearing.
struct DlssgReport {
    int steps_observed = 0;
    bool reported = false;
};
static constexpr int DLSSG_WARMUP_STEPS = 8;

// A zero timeout turns the blocking ovrtx waits into non-blocking polls that
// report OVRTX_API_TIMEOUT when the result is not ready yet.
static constexpr ovrtx_timeout_t OVRTX_TIMEOUT_POLL = {0};

static void report_dlssg_frame_count(bool dlssg_enabled,
                                     int requested_interpolated_frames,
                                     size_t produced_frames,
                                     DlssgReport& report);

// Where wall-clock time goes in one report interval. `step` covers
// ovrtx_step_with_stage through a successful ovrtx_fetch_results, which is
// where the wait on the renderer is observed to land: by the time the fetch
// reports success, every output frame of that step is already mappable.
// `map_copy` covers copy_output_to_surface, so it is only the map poll plus
// the copy submission, and stays cheap because the frame is already there and
// the unmap is deferred to release_mapped_output. The two are measured apart
// to show that split rather than to assert it, since which of the two calls
// absorbs the wait is a renderer implementation detail.
//
// Steps and presents are counted apart because DLSS Frame Generation makes them
// diverge: one step yields N + 1 presentable frames.
struct LoopMetrics {
    double step_ms = 0.0;
    double map_copy_ms = 0.0;
    int steps = 0;
    int copies = 0;
    // Iterations that found the next output frame still unmappable. These are
    // the stalls the blocking map used to hide inside a single long call.
    int map_polls = 0;
    int promotions = 0;

    // Gaps between successive frame promotions. Pacing aims to make these
    // uniform, so the spread matters more than the mean.
    std::vector<double> promotion_gaps_ms;
    std::chrono::steady_clock::time_point last_promotion;
    bool has_last_promotion = false;

    // map_copy cost split by a frame's position within its step. Interpolated
    // frames occupy the leading slots and the real rendered frame the last one,
    // so this shows whether a step's frames become mappable all at once or
    // progressively, and whether an interpolated frame is cheaper to map.
    std::vector<double> map_copy_ms_by_slot;
    std::vector<int> frames_by_slot;

    // A new frame became visible. Once the map is polled rather than waited on,
    // the loop re-presents the same image while a frame is still rendering, so
    // presents no longer count distinct frames; these promotions do, and their
    // spacing is what smoothness actually depends on.
    void record_frame_promotion(
        std::chrono::steady_clock::time_point const& at) {
        ++promotions;
        if (has_last_promotion) {
            promotion_gaps_ms.push_back(
                std::chrono::duration<double, std::milli>(at - last_promotion)
                    .count());
        }
        last_promotion = at;
        has_last_promotion = true;
    }

    void record_map_copy(size_t slot, double ms) {
        map_copy_ms += ms;
        ++copies;
        if (slot >= map_copy_ms_by_slot.size()) {
            map_copy_ms_by_slot.resize(slot + 1, 0.0);
            frames_by_slot.resize(slot + 1, 0);
        }
        map_copy_ms_by_slot[slot] += ms;
        ++frames_by_slot[slot];
    }

    void reset() {
        step_ms = 0.0;
        map_copy_ms = 0.0;
        steps = 0;
        copies = 0;
        map_polls = 0;
        promotions = 0;
        promotion_gaps_ms.clear();
        std::fill(map_copy_ms_by_slot.begin(), map_copy_ms_by_slot.end(), 0.0);
        std::fill(frames_by_slot.begin(), frames_by_slot.end(), 0);
    }
};

// Spaces frame promotions evenly instead of showing a whole step's frames back
// to back and then idling.
//
// The target spacing is derived from the observed step period divided by the
// number of frames a step produces. Pacing deliberately aims slightly faster
// than that (PACE_SAFETY): promoting a frame is what frees the buffer for the
// next copy, so a target slower than the renderer's actual output rate would
// throttle production, which would in turn lengthen the measured step period
// and feed back on itself. Undershooting keeps the renderer, not the pacer, as
// the rate limiter.
class FramePacer {
public:
    explicit FramePacer(bool enabled) : _enabled(enabled) {}

    // Called once per step enqueue to track how fast steps actually come.
    void on_step(std::chrono::steady_clock::time_point const& at) {
        if (_has_last_step) {
            double const period =
                std::chrono::duration<double, std::milli>(at - _last_step)
                    .count();
            _step_period_ms = (_step_period_ms == 0.0)
                                  ? period
                                  : (1.0 - PERIOD_SMOOTHING) * _step_period_ms +
                                        PERIOD_SMOOTHING * period;
        }
        _last_step = at;
        _has_last_step = true;
    }

    void set_frames_per_step(size_t frames) {
        _frames_per_step = (frames > 0) ? frames : 1;
    }

    void on_promotion(std::chrono::steady_clock::time_point const& at) {
        _last_promotion = at;
        _has_last_promotion = true;
    }

    // Nothing to spread out when a step yields a single frame, so pacing only
    // engages once frame generation is actually producing extra frames.
    bool active() const { return _enabled && _frames_per_step > 1; }

    double target_gap_ms() const {
        if (!active() || _step_period_ms == 0.0) {
            return 0.0;
        }
        return PACE_SAFETY * _step_period_ms /
               static_cast<double>(_frames_per_step);
    }

    bool promotion_due(std::chrono::steady_clock::time_point const& now) const {
        if (!active() || !_has_last_promotion) {
            return true;
        }
        double const gap =
            std::chrono::duration<double, std::milli>(now - _last_promotion)
                .count();
        return gap >= target_gap_ms();
    }

    // How long the caller may idle before the next frame is due, so the loop
    // does not spin at thousands of redundant presents per second.
    double ms_until_due(std::chrono::steady_clock::time_point const& now) const {
        if (!active() || !_has_last_promotion) {
            return 0.0;
        }
        double const gap =
            std::chrono::duration<double, std::milli>(now - _last_promotion)
                .count();
        return std::max(0.0, target_gap_ms() - gap);
    }

private:
    static constexpr double PERIOD_SMOOTHING = 0.2;
    static constexpr double PACE_SAFETY = 0.9;

    bool _enabled = false;
    size_t _frames_per_step = 1;
    double _step_period_ms = 0.0;
    std::chrono::steady_clock::time_point _last_step;
    std::chrono::steady_clock::time_point _last_promotion;
    bool _has_last_step = false;
    bool _has_last_promotion = false;
};

// Milliseconds elapsed since `start`, for the CPU-side loop metrics.
static double elapsed_ms_since(
    std::chrono::steady_clock::time_point const& start) {
    return std::chrono::duration<double, std::milli>(
               std::chrono::steady_clock::now() - start)
        .count();
}

int main(int argc, char* argv[]) {
    // Must stay first: this only takes effect before the first CUDA context.
    cuda_apply_scheduling_workaround();

    // Parse command-line arguments
    std::string usd_file_path;
    std::string render_product_path;
    std::string camera_prim_path;
    UpAxis up_axis;
    Units units;
    int num_frames = 0;
    bool headless = false;
    bool dlssg_enabled = false;
    int dlssg_interpolated_frames = DEFAULT_DLSSG_INTERPOLATED_FRAMES;
    PresentMode present_mode = PresentMode::Fifo;
    bool pace_frames = false;

    if (!parse_args(argc,
                    argv,
                    usd_file_path,
                    render_product_path,
                    camera_prim_path,
                    up_axis,
                    units,
                    num_frames,
                    headless,
                    dlssg_enabled,
                    dlssg_interpolated_frames,
                    present_mode,
                    pace_frames)) {
        return 0; // Help was shown or parse error
    }

    if (headless) {
        if (num_frames == 0) {
            num_frames = 100;
        }
    }

    std::cerr << "USD file: " << usd_file_path << std::endl;
    std::cerr << "Render product: " << render_product_path << std::endl;
    std::cerr << "Orbit camera prim: " << camera_prim_path << std::endl;
    std::cerr << "Up axis: " << (up_axis == UpAxis::Y ? "Y" : "Z") << std::endl;
    std::cerr << "Units: "
              << (units == Units::Meters ? "meters" : "centimeters") << std::endl;
    std::cerr << "Mode: " << (headless ? "headless" : "windowed") << std::endl;
    if (!headless) {
        std::cerr << "Present mode: " << present_mode_name(present_mode)
                  << std::endl;
        std::cerr << "Frame pacing: " << (pace_frames ? "on" : "off")
                  << std::endl;
    }
    std::cerr << "DLSS Frame Generation: ";
    if (!dlssg_enabled) {
        std::cerr << "off" << std::endl;
    } else {
        std::cerr << "requested, " << dlssg_interpolated_frames
                  << " interpolated frame(s) (0 = renderer picks)" << std::endl;
    }

    // =========================================================================
    // Initialize ovrtx
    // =========================================================================
    std::cerr << "Initializing ovrtx..." << std::endl;

    ovrtx_renderer_t* renderer = nullptr;
    ovstage_instance_t* stage = nullptr;
    bool stage_attached = false;
    ovstage_ordinal_t stage_ordinal = 1;
    ovstage_query_handle_t camera_query = OVSTAGE_INVALID_QUERY_HANDLE;
    GLFWwindow* window = nullptr;
    bool glfw_initialized = false;
    auto cleanup_window = [&]() {
        if (window) {
            glfwDestroyWindow(window);
            window = nullptr;
        }
        if (glfw_initialized) {
            glfwTerminate();
            glfw_initialized = false;
        }
    };

    // ovrtx owns scene evaluation and rendering; the rest of this sample
    // bridges those results into Vulkan-presentable images.
    // [snippet:initialize-and-create-renderer]
    // The STATIC ovrtx loader resolves the ${executable_dir} token to the running
    // executable's directory; ovrtx_setup_runtime() links the package bin beside
    // the exe as "ovrtx/", which we hand the loader as the binary package root.
    ovx_string_t ovrtx_package_root = {
        OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx",
        sizeof(OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx") - 1};
    ovx_string_t active_cuda_gpus = {ACTIVE_CUDA_GPUS, sizeof(ACTIVE_CUDA_GPUS) - 1};
    ovrtx_config_entry_t ovrtx_config_entries[] = {
        ovrtx_config_entry_binary_package_root_path(ovrtx_package_root),
        ovrtx_config_entry_active_cuda_gpus(active_cuda_gpus),
        ovrtx_config_entry_selection_outline_enabled(true),
        ovrtx_config_entry_selection_outline_width(4),
        ovrtx_config_entry_selection_fill_mode(OVRTX_SELECTION_FILL_MODE_GROUP_FILL_COLOR),
    };
    ovrtx_config_t ovrtx_config = {};
    ovrtx_config.entries = ovrtx_config_entries;
    ovrtx_config.entry_count =
        sizeof(ovrtx_config_entries) / sizeof(ovrtx_config_entries[0]);

    // Publish OVRTX's USD plugin paths before ovstage initializes the shared USD
    // runtime. The process-wide USD schema registry only discovers plugins once.
    ovrtx_result_t result = ovrtx_register_schema_paths(&ovrtx_config);
    if (check_and_print_error(result, "register_schema_paths")) {
        return 1;
    }

    // The STATIC ovstage loader resolves ${executable_dir} the same way ovrtx does.
    // ovstage_setup_runtime() links the package bin beside the exe as "ovstage/"
    // (next to "ovrtx/").
    ovx_string_t ovstage_package_root = {
        OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovstage",
        sizeof(OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovstage") - 1};
    ovstage_config_entry_t stage_config_entries[] = {
        ovstage_config_entry_binary_package_root_path(ovstage_package_root),
    };
    ovstage_config_t stage_config {};
    stage_config.entries = stage_config_entries;
    stage_config.entry_count = sizeof(stage_config_entries) / sizeof(stage_config_entries[0]);
    ovstage_api_status_t stage_init_status = ovstage_initialize(&stage_config);
    if (stage_init_status != OVSTAGE_OK) {
        print_ovstage_error(nullptr, stage_init_status, "initialize");
        return 1;
    }

    result = ovrtx_create_renderer(&ovrtx_config, &renderer);
    if (check_and_print_error(result, "create_renderer")) {
        ovstage_shutdown();
        return 1;
    }

    auto cleanup = [&](int exit_code) {
        int result_code = exit_code;
        if (camera_query != OVSTAGE_INVALID_QUERY_HANDLE) {
            if (wait_ovstage_op(stage,
                                ovstage_release_query(stage, camera_query),
                                "release_query")) {
                result_code = 1;
            }
            camera_query = OVSTAGE_INVALID_QUERY_HANDLE;
        }
        if (stage_attached) {
            result = ovrtx_detach_ovstage(renderer);
            if (check_and_print_error(result, "detach_ovstage")) {
                result_code = 1;
            }
            stage_attached = false;
        }
        // After a detach failure, only renderer destruction is supported.
        if (renderer) {
            result = ovrtx_destroy_renderer(renderer);
            if (check_and_print_error(result, "destroy_renderer")) {
                result_code = 1;
            } else {
                renderer = nullptr;
            }
        }
        if (stage) {
            ovstage_api_status_t stage_result = ovstage_destroy_instance(stage);
            if (stage_result != OVSTAGE_OK) {
                print_ovstage_error(stage, stage_result, "destroy_instance");
                result_code = 1;
            }
            stage = nullptr;
        }
        // Release the ovstage static loader (unloads ovstage.dll). Safe even if
        // ovstage_initialize failed or was never reached.
        ovstage_shutdown();
        return result_code;
    };

    // Register the per-group outline/fill style before any picking happens.
    if (!configure_selection_style(renderer)) {
        return cleanup(1);
    }
    // [/snippet:initialize-and-create-renderer]

    std::cerr << "Loading USD scene: " << usd_file_path << std::endl;
    path_dictionary_instance_t path_dictionary = {};
    result = ovrtx_get_path_dictionary(renderer, &path_dictionary);
    if (check_and_print_error(result, "get_path_dictionary")) {
        return cleanup(1);
    }

    ovstage_instance_desc_t stage_desc = {};
    stage_desc.name = "vulkan-interop";
    ovstage_api_status_t stage_result = ovstage_create_instance(&stage_desc, &stage);
    if (stage_result != OVSTAGE_OK) {
        print_ovstage_error(stage, stage_result, "create_instance");
        return cleanup(1);
    }

    result = ovrtx_attach_ovstage(renderer, stage);
    if (check_and_print_error(result, "attach_ovstage")) {
        return cleanup(1);
    }
    stage_attached = true;

    ovstage_population_enqueue_result_t populate_result =
        ovstage_population_open_usd_from_file(
            stage,
            {usd_file_path.c_str(), usd_file_path.size()},
            stage_ordinal,
            /* time = */ 0.0,
            OVSTAGE_POPULATION_DOMAIN_RENDERING);
    if (wait_population_op(stage, populate_result, "population_open_usd_from_file") ||
        commit_ovstage_ordinal(stage, stage_ordinal)) {
        return cleanup(1);
    }
    if (create_validated_prim_query(stage, camera_prim_path, &camera_query)) {
        return cleanup(1);
    }

    // Author the DLSS-G opinion before the first step so the renderer allocates
    // interpolated frame slots from the very first frame it produces.
    ++stage_ordinal;
    if (author_dlssg_settings(stage,
                              render_product_path,
                              stage_ordinal,
                              dlssg_enabled,
                              dlssg_interpolated_frames) ||
        commit_ovstage_ordinal(stage, stage_ordinal)) {
        return cleanup(1);
    }

    std::cerr << "USD scene loaded successfully" << std::endl;
    std::cerr << "Render product path: " << render_product_path << std::endl;

    ovx_string_t render_product_str = {};
    render_product_str.ptr = render_product_path.c_str();
    render_product_str.length = render_product_path.size();

    ovrtx_render_product_set_t render_products = {};
    render_products.render_products = &render_product_str;
    render_products.num_render_products = 1;

    // ovrtx creates/uses CUDA internally. Resolve the configured CUDA ordinal
    // through that context so Vulkan selects the exact same MIG device.
    CUuuid cuda_uuid;
    if (!cuda_init(CUDA_DEVICE_ID, &cuda_uuid)) {
        std::cerr << "Failed to get CUDA context" << std::endl;
        return cleanup(1);
    }

    // =========================================================================
    // Do an initial ovrtx step to get render dimensions
    // =========================================================================
    // We need output dimensions and format before allocating shared Vulkan
    // images.
    ovrtx_step_result_handle_t step_result_handle = 0;
    ovrtx_enqueue_result_t enqueue_result =
        ovrtx_step_with_stage(renderer,
                              render_products,
                              0.0,
                              stage_ordinal,
                              &step_result_handle);
    if (check_and_print_error(enqueue_result, "step")) {
        return cleanup(1);
    }

    ovrtx_render_product_set_outputs_t outputs = {};
    result = ovrtx_fetch_results(
        renderer, step_result_handle, ovrtx_timeout_infinite, &outputs);
    if (check_and_print_error(result, "fetch_results")) {
        ovrtx_destroy_results(renderer, step_result_handle);
        return cleanup(1);
    }

    if (outputs.status != OVRTX_EVENT_COMPLETED || outputs.output_count == 0) {
        std::cerr << "Could not get dimensions for RenderProduct \""
                  << render_product_path << "\"" << std::endl;
        ovrtx_destroy_results(renderer, step_result_handle);
        return cleanup(3);
    }

    // Find color output (prefer HdrColor, fall back to LdrColor)
    OutputType output_type;
    std::vector<ovrtx_render_var_output_handle_t> color_outputs;
    if (!collect_color_outputs(
            outputs, render_product_path, color_outputs, &output_type)) {
        std::cerr << "No color output found (HdrColor or LdrColor)" << std::endl;
        ovrtx_destroy_results(renderer, step_result_handle);
        return cleanup(1);
    }
    std::cerr << "Using " << output_type_name(output_type) << " output" << std::endl;

    // Request CUDA-array mapping so ovrtx gives us a GPU-native source buffer
    // that can be copied directly into exported Vulkan memory.
    ovrtx_map_output_description_t map_desc = {};
    map_desc.device_type = OVRTX_MAP_DEVICE_TYPE_CUDA_ARRAY;
    map_desc.sync_stream = 0;

    ovrtx_render_var_output_t rendered_output = {};
    result = ovrtx_map_render_var_output(renderer,
                                       color_outputs.back(),
                                       &map_desc,
                                       ovrtx_timeout_infinite,
                                       &rendered_output);
    if (check_and_print_error(result, "map_render_var_output")) {
        ovrtx_destroy_results(renderer, step_result_handle);
        return cleanup(1);
    }

    if (rendered_output.num_tensors == 0) {
        std::cerr << "color render variable produced no tensors" << std::endl;
        ovrtx_unmap_render_var_output(renderer, rendered_output.map_handle, ovrtx_cuda_sync_t{});
        ovrtx_destroy_results(renderer, step_result_handle);
        return cleanup(1);
    }
    DLTensor const& dl = *rendered_output.tensors[0].dl;
    // [snippet:validate-render-output-cuda-device]
    if (dl.device.device_type != kDLCUDA || dl.device.device_id != CUDA_DEVICE_ID) {
        std::cerr << "Render output is on DLPack device type " << dl.device.device_type
                  << ", device " << dl.device.device_id << "; expected CUDA device "
                  << CUDA_DEVICE_ID << std::endl;
        ovrtx_unmap_render_var_output(renderer, rendered_output.map_handle, ovrtx_cuda_sync_t{});
        ovrtx_destroy_results(renderer, step_result_handle);
        return cleanup(1);
    }
    // [/snippet:validate-render-output-cuda-device]
    int tex_width = static_cast<int>(dl.shape[1]);
    int tex_height = static_cast<int>(dl.shape[0]);

    // Unmap and destroy initial step results (no copy, so no sync needed)
    result = ovrtx_unmap_render_var_output(
        renderer, rendered_output.map_handle, ovrtx_cuda_sync_t{});
    if (check_and_print_error(result, "unmap_render_var_output")) {
        ovrtx_destroy_results(renderer, step_result_handle);
        return cleanup(1);
    }
    result = ovrtx_destroy_results(renderer, step_result_handle);
    if (check_and_print_error(result, "destroy_results")) {
        return cleanup(1);
    }

    std::cerr << "Render output dimensions: " << tex_width << " x "
              << tex_height << std::endl;

    // =========================================================================
    // Initialize GLFW and create window when running the interactive sample.
    // =========================================================================
    if (!headless) {
        if (!glfwInit()) {
            std::cerr << "Failed to initialize GLFW" << std::endl;
            return cleanup(1);
        }
        glfw_initialized = true;

        glfwWindowHint(GLFW_CLIENT_API, GLFW_NO_API);
        glfwWindowHint(GLFW_RESIZABLE, GLFW_TRUE);

        window = glfwCreateWindow(
            WINDOW_WIDTH, WINDOW_HEIGHT, "ovrtx-Vulkan Interop", nullptr, nullptr);
        if (!window) {
            std::cerr << "Failed to create window" << std::endl;
            cleanup_window();
            return cleanup(1);
        }

        update_window_title(window, ovrtx_accumulation_status_t{});

        glfwSetMouseButtonCallback(window, mouse_button_callback);
        glfwSetCursorPosCallback(window, cursor_position_callback);
        glfwSetScrollCallback(window, scroll_callback);
    } else {
        std::cerr << "Running without GLFW window or Vulkan swapchain"
                  << std::endl;
    }

    // Create orbit camera
    // Start with a decent framing on the robot
    // Scale camera distance based on scene units (centimeters need 100x scale)
    float unit_scale = (units == Units::Centimeters) ? 100.0f : 1.0f;
    float distance = 5.0f * unit_scale; // 5 meters or 500 centimeters
    float azimuth = glm::radians(290.0f);
    float elevation =
        std::asin(0.5f / 5.0f);         // camera at ~1.5m looking at 1m target
    glm::vec3 target(0.0f, 0.0f, 1.0f); // 1 meter above ground (Z-up)
    OrbitCamera orbit_camera(distance, azimuth, elevation, target, up_axis);
    g_orbit_camera = &orbit_camera;
    g_camera_dirty = true;

    bool readback_ok = true;

    // Scope for VulkanContext
    try {
        // VulkanContext chooses a Vulkan device that matches the CUDA UUID
        // above.
        VulkanContextConfig vk_config;
        vk_config.window = headless ? nullptr : window;
        vk_config.initial_sampled_image_capacity = 16;
        vk_config.present_mode = present_mode;

        VulkanContext vk(vk_config, cuda_uuid);

        if (!headless && vk.present_mode() != present_mode) {
            std::cerr << "Present mode " << present_mode_name(present_mode)
                      << " is not supported by this surface; using "
                      << present_mode_name(vk.present_mode()) << std::endl;
        }

        // A ring of shared images lets CUDA keep copying while Vulkan samples
        // one of them, and lets a whole step's worth of generated frames wait
        // their turn instead of being shown back to back.
        constexpr int SHARED_IMAGE_COUNT = CUDA_SHARED_IMAGE_COUNT;
        VkFormat vk_format = vulkan_format_for_output(output_type);
        CudaImageFormat cuda_format = cuda_format_for_output(output_type);

        std::array<FrameSlot, SHARED_IMAGE_COUNT> slots;
        SampledImageHandle shared_images[SHARED_IMAGE_COUNT];
        for (int i = 0; i < SHARED_IMAGE_COUNT; ++i) {
            shared_images[i] = vk.create_sampled_image(
                tex_width, tex_height, vk_format, VK_FILTER_LINEAR, true);
        }

        // Load precompiled SPIR-V shaders from next to the executable. These
        // are only needed for windowed presentation, so skip them in headless.
        ShaderHandle vert_shader;
        ShaderHandle frag_shader;
        ShaderHandle overlay_vert_shader;
        ShaderHandle overlay_frag_shader;
        if (!headless) {
            std::filesystem::path shader_dir = get_executable_dir() / "shaders";
            std::string vert_path = (shader_dir / "fullscreen.vert.spv").string();
            std::string frag_path = (shader_dir / "fullscreen.frag.spv").string();
            std::string overlay_vert_path =
                (shader_dir / "overlay.vert.spv").string();
            std::string overlay_frag_path =
                (shader_dir / "overlay.frag.spv").string();
            std::vector<uint32_t> vert_spirv = load_spirv(vert_path);
            std::vector<uint32_t> frag_spirv = load_spirv(frag_path);
            std::vector<uint32_t> overlay_vert_spirv =
                load_spirv(overlay_vert_path);
            std::vector<uint32_t> overlay_frag_spirv =
                load_spirv(overlay_frag_path);

            std::cerr << "Loaded shaders: vertex=" << vert_spirv.size()
                      << " words, fragment=" << frag_spirv.size()
                      << " words, overlay_vertex=" << overlay_vert_spirv.size()
                      << " words, overlay_fragment=" << overlay_frag_spirv.size()
                      << " words" << std::endl;

            auto fullscreen_shaders =
                vk.create_linked_vertex_and_fragment_shaders(vert_spirv,
                                                             frag_spirv);
            vert_shader = fullscreen_shaders.first;
            frag_shader = fullscreen_shaders.second;

            auto overlay_shaders =
                vk.create_linked_vertex_and_fragment_shaders(overlay_vert_spirv,
                                                             overlay_frag_spirv);
            overlay_vert_shader = overlay_shaders.first;
            overlay_frag_shader = overlay_shaders.second;
        }

        // CUDA writes require GENERAL layout and external queue ownership.
        for (int i = 0; i < SHARED_IMAGE_COUNT; ++i) {
            VkImage shared_img = vk.sampled_image(shared_images[i]).image;
            vk.immediate_submit([shared_img](CommandBuffer cmd) {
                cmd.image_memory_barrier(shared_img,
                                         VK_IMAGE_ASPECT_COLOR_BIT,
                                         VK_IMAGE_LAYOUT_UNDEFINED,
                                         VK_PIPELINE_STAGE_2_TOP_OF_PIPE_BIT,
                                         VK_ACCESS_2_NONE,
                                         VK_IMAGE_LAYOUT_GENERAL,
                                         VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                                         VK_ACCESS_2_SHADER_WRITE_BIT);
            });
        }

        // Export VkDeviceMemory and import into CUDA as surface objects, which
        // become copy targets for mapped ovrtx CUDA arrays.
        CUsurfObject cuda_surfaces[SHARED_IMAGE_COUNT];
        for (int i = 0; i < SHARED_IMAGE_COUNT; ++i) {
            SampledImage const& img = vk.sampled_image(shared_images[i]);
            auto memory_handle = vk.export_memory_handle(shared_images[i]);
            cuda_surfaces[i] = cuda_import_vulkan_image(
                i, memory_handle, img.size, tex_width, tex_height, cuda_format);
            if (cuda_surfaces[i] == 0) {
                std::cerr << "Failed to import Vulkan image " << i
                          << " into CUDA" << std::endl;
                cuda_cleanup();
                cleanup_window();
                return cleanup(1);
            }
        }

        // Timeline semaphore synchronizes async CUDA producers with Vulkan
        // consumers without forcing CPU-side blocking.
        auto timeline_handle = vk.export_timeline_semaphore_handle();
        if (!cuda_import_timeline_semaphore(timeline_handle)) {
            cuda_cleanup();
            cleanup_window();
            return cleanup(1);
        }

        // CUDA events track copy completion and provide fence points back to
        // ovrtx.
        CUstream cuda_stream;
        cuStreamCreate(&cuda_stream, 0);

        CUevent cuda_copy_done_event;
        // Used by the priming and headless paths, which copy one frame at a
        // time and release each mapping before starting the next.
        cuEventCreate(&cuda_copy_done_event, CU_EVENT_DISABLE_TIMING);
        for (FrameSlot& slot : slots) {
            cuEventCreate(&slot.copy_start, CU_EVENT_DEFAULT);
            cuEventCreate(&slot.copy_done, CU_EVENT_DEFAULT);
        }

        // Index of the slot Vulkan samples, and the queue of slots whose copy
        // has landed and that are waiting to be shown, oldest first.
        int read_idx = 0;
        std::vector<int> ready_queue;
        ready_queue.reserve(SHARED_IMAGE_COUNT);
        // `--num-frames` saves the buffer Vulkan last presented, so it must stop
        // on a real rendered frame rather than a DLSS-G interpolated one.
        bool read_holds_real_frame = true;
        uint64_t cuda_frame_counter = 0;
        uint64_t read_timeline_value =
            0; // timeline value for current read buffer

        // ovrtx step state
        ovrtx_step_result_handle_t current_step_result = 0;
        PendingFrames pending;

        // A CUDA interop helper failure leaves copies and ovrtx mappings in
        // flight. Finish pending users before releasing mapped outputs or
        // imported resources, and do not submit Vulkan work that waits on a
        // signal that never happened.
        auto fail_cuda_interop = [&]() {
            cuStreamSynchronize(cuda_stream);
            vkDeviceWaitIdle(vk.device());
            for (FrameSlot& slot : slots) {
                if (slot.mapped) {
                    release_mapped_output(
                        renderer, slot.map_handle, slot.copy_done);
                    slot.mapped = false;
                }
            }
            if (pending.step_result != 0) {
                ovrtx_result_t const destroy_result =
                    ovrtx_destroy_results(renderer, pending.step_result);
                check_and_print_error(destroy_result, "destroy_results");
                pending.step_result = 0;
            }
            if (current_step_result != 0) {
                ovrtx_result_t const destroy_result =
                    ovrtx_destroy_results(renderer, current_step_result);
                check_and_print_error(destroy_result, "destroy_results");
                current_step_result = 0;
            }
            cuEventDestroy(cuda_copy_done_event);
            for (FrameSlot& slot : slots) {
                cuEventDestroy(slot.copy_start);
                cuEventDestroy(slot.copy_done);
            }
            cuStreamDestroy(cuda_stream);
            cuda_cleanup();
            cleanup_window();
            return cleanup(1);
        };

        ovrtx_accumulation_status_t accumulation_status{};
        DlssgReport dlssg_report;

        // =====================================================================
        // Prime the first buffer so Vulkan has valid content before
        // steady-state async producer/consumer overlap begins.
        // =====================================================================
        std::cerr << "Priming first frame..." << std::endl;
        {
            enqueue_result = ovrtx_step_with_stage(renderer,
                                                   render_products,
                                                   0.0,
                                                   stage_ordinal,
                                                   &current_step_result);
            if (check_and_print_error(enqueue_result, "step")) {
                cuda_cleanup();
                cleanup_window();
                return cleanup(1);
            }

            result = ovrtx_fetch_results(renderer,
                                         current_step_result,
                                         ovrtx_timeout_infinite,
                                         &outputs);
            if (check_and_print_error(result, "fetch_results")) {
                ovrtx_destroy_results(renderer, current_step_result);
                cuda_cleanup();
                cleanup_window();
                return cleanup(1);
            }

            refresh_render_feedback(
                window, accumulation_status, outputs, render_product_path);

            if (!collect_color_outputs(
                    outputs, render_product_path, color_outputs)) {
                std::cerr << "ERROR: could not find output from "
                          << render_product_path << std::endl;
                ovrtx_destroy_results(renderer, current_step_result);
                cuda_cleanup();
                cleanup_window();
                return cleanup(2);
            }

            // Prime with the real rendered frame, which is always the last one.
            // Priming blocks on purpose: the loop needs valid content before it
            // can present anything.
            ovrtx_render_var_output_map_handle_t prime_map = 0;
            if (copy_output_to_surface(renderer,
                                       color_outputs.back(),
                                       0,
                                       cuda_format,
                                       cuda_stream,
                                       cuda_copy_done_event,
                                       ovrtx_timeout_infinite,
                                       &prime_map) !=
                CopyOutputResult::Copied) {
                ovrtx_destroy_results(renderer, current_step_result);
                cuda_cleanup();
                cleanup_window();
                return cleanup(1);
            }
            cuStreamSynchronize(cuda_stream);
            if (!release_mapped_output(
                    renderer, prime_map, cuda_copy_done_event)) {
                ovrtx_destroy_results(renderer, current_step_result);
                cuda_cleanup();
                cleanup_window();
                return cleanup(1);
            }

            result = ovrtx_destroy_results(renderer, current_step_result);
            if (check_and_print_error(result, "destroy_results")) {
                cuda_cleanup();
                cleanup_window();
                return cleanup(1);
            }
            current_step_result = 0;

            read_idx = 0;
            slots[0].state = FrameSlot::State::Showing;
            slots[0].holds_real_frame = true;
        }

        int total_frames = 1;
        if (headless) {
            // Headless mode drives the ovrtx->CUDA->Vulkan interop path for a
            // fixed number of frames without a swapchain, validating the
            // producer/consumer pipeline in automated environments.
            std::cerr << "Running headless render loop for " << num_frames
                      << " frames..." << std::endl;
            // Headless has no presentation to overlap with, so it keeps the
            // simple ping-pong: copy one frame, release it, move on.
            int write_idx = 1;
            while (total_frames < num_frames) {
                enqueue_result = ovrtx_step_with_stage(renderer,
                                                       render_products,
                                                       1.0 / 60.0,
                                                       stage_ordinal,
                                                       &current_step_result);
                if (check_and_print_error(enqueue_result, "step")) {
                    cuda_cleanup();
                    cleanup_window();
                    return cleanup(1);
                }

                result = ovrtx_fetch_results(renderer,
                                             current_step_result,
                                             ovrtx_timeout_infinite,
                                             &outputs);
                if (check_and_print_error(result, "fetch_results")) {
                    ovrtx_destroy_results(renderer, current_step_result);
                    cuda_cleanup();
                    cleanup_window();
                    return cleanup(1);
                }

                refresh_render_feedback(
                    nullptr, accumulation_status, outputs, render_product_path);

                if (!collect_color_outputs(
                        outputs, render_product_path, color_outputs)) {
                    std::cerr << "ERROR: could not find output from "
                              << render_product_path << std::endl;
                    ovrtx_destroy_results(renderer, current_step_result);
                    cuda_cleanup();
                    cleanup_window();
                    return cleanup(2);
                }
                report_dlssg_frame_count(dlssg_enabled,
                                         dlssg_interpolated_frames,
                                         color_outputs.size(),
                                         dlssg_report);

                // Steps are drained whole, so a multi-frame step can push
                // total_frames past num_frames. Exiting only on a step boundary
                // also leaves read_idx on a real frame for the readback below.
                for (ovrtx_render_var_output_handle_t color_output :
                     color_outputs) {
                    ovrtx_render_var_output_map_handle_t frame_map = 0;
                    if (copy_output_to_surface(renderer,
                                               color_output,
                                               write_idx,
                                               cuda_format,
                                               cuda_stream,
                                               cuda_copy_done_event,
                                               ovrtx_timeout_infinite,
                                               &frame_map) !=
                        CopyOutputResult::Copied) {
                        ovrtx_destroy_results(renderer, current_step_result);
                        cuda_cleanup();
                        cleanup_window();
                        return cleanup(1);
                    }
                    cuStreamSynchronize(cuda_stream);
                    if (!release_mapped_output(
                            renderer, frame_map, cuda_copy_done_event)) {
                        ovrtx_destroy_results(renderer, current_step_result);
                        cuda_cleanup();
                        cleanup_window();
                        return cleanup(1);
                    }

                    read_idx = write_idx;
                    write_idx = (write_idx + 1) % SHARED_IMAGE_COUNT;
                    ++total_frames;
                }

                result = ovrtx_destroy_results(renderer, current_step_result);
                if (check_and_print_error(result, "destroy_results")) {
                    cuda_cleanup();
                    cleanup_window();
                    return cleanup(1);
                }
                current_step_result = 0;
            }

            VkImage read_image = vk.sampled_image(shared_images[read_idx]).image;
            vk.immediate_submit([read_image, &vk](CommandBuffer cmd) {
                cmd.image_memory_barrier(read_image,
                                         VK_IMAGE_ASPECT_COLOR_BIT,
                                         VK_IMAGE_LAYOUT_GENERAL,
                                         VK_PIPELINE_STAGE_2_NONE,
                                         VK_ACCESS_2_NONE,
                                         VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                                         VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT,
                                         VK_ACCESS_2_SHADER_SAMPLED_READ_BIT,
                                         VK_QUEUE_FAMILY_EXTERNAL,
                                         vk.queue_family());
                cmd.image_memory_barrier(read_image,
                                         VK_IMAGE_ASPECT_COLOR_BIT,
                                         VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                                         VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT,
                                         VK_ACCESS_2_SHADER_SAMPLED_READ_BIT,
                                         VK_IMAGE_LAYOUT_GENERAL,
                                         VK_PIPELINE_STAGE_2_NONE,
                                         VK_ACCESS_2_NONE,
                                         vk.queue_family(),
                                         VK_QUEUE_FAMILY_EXTERNAL);
            });
        }

        // Timing accumulators
        double accumulated_cpu_ms = 0.0;
        double accumulated_vulkan_ms = 0.0;
        double accumulated_cuda_ms = 0.0;
        int frame_count = 0;
        int cuda_frame_count = 0;
        LoopMetrics metrics;
        FramePacer pacer(pace_frames);
        bool defer_swapchain_recreate = false;
        auto last_print_time = std::chrono::steady_clock::now();
        auto last_step_time = std::chrono::steady_clock::now();

        // Frame time storage for final statistics (only when num_frames > 0)
        std::vector<double> all_cpu_times_ms;
        std::vector<double> all_vulkan_times_ms;
        std::vector<double> all_cuda_times_ms;

        if (num_frames > 0) {
            all_cuda_times_ms.reserve(num_frames);
        }

        if (headless) {
            std::cerr << "Headless validation rendered " << total_frames
                      << " frames" << std::endl;
        } else {
            std::cerr << "Starting render loop..." << std::endl;
        }
        if (num_frames > 0 && !headless) {
            std::cerr << "Will render " << num_frames
                      << " frames then save out.png and exit" << std::endl;
        }

        if (!headless) {
            total_frames = 0;
        }

        // Persisted viewport selection; the outline follows the latest pick.
        std::vector<ovx_primpath_t> selected_prim_path_ids;

        // =====================================================================
        // Main loop
        // =====================================================================
        // High-level flow:
        // 1) poll UI and camera updates
        // 2) observe CUDA completion and swap read/write roles
        // 3) enqueue next ovrtx->CUDA copy if CUDA is idle
        // 4) render/present last completed buffer in Vulkan
        while (!headless && !glfwWindowShouldClose(window)) {
            glfwPollEvents();

            auto size = vk.framebuffer_size();
            if (size.x == 0 || size.y == 0) {
                glfwWaitEvents();
                continue;
            }

            auto frame_start = std::chrono::steady_clock::now();

            vk.wait_for_fence();

            if (frame_count > 0) {
                double vulkan_ms = vk.vulkan_elapsed_ms();
                accumulated_vulkan_ms += vulkan_ms;
                if (num_frames > 0) {
                    all_vulkan_times_ms.push_back(vulkan_ms);
                }
            }

            // Recreate swapchain only at safe frame boundaries to avoid
            // invalidating in-flight render/present resources.
            if (defer_swapchain_recreate) {
                vk.recreate_swapchain();
                defer_swapchain_recreate = false;
                continue;
            }

            vk.reset_fence();

            uint32_t swapchain_image_index;
            auto acquire_result = vk.acquire_next_image(swapchain_image_index);

            if (acquire_result == AcquireResult::OutOfDate) {
                vk.recreate_swapchain();
                vk.reset_fence_to_signaled();
                continue;
            } else if (acquire_result == AcquireResult::Suboptimal) {
                // Render this frame so acquire semaphore is consumed, then
                // recreate later.
                defer_swapchain_recreate = true;
            } else if (acquire_result == AcquireResult::Minimized) {
                vk.reset_fence_to_signaled();
                continue;
            }

            // Non-blocking poll: once CUDA finishes writing the next frame,
            // swap roles so Vulkan presents fresh data while CUDA starts
            // writing the other image.
            //
            // Retire copies that have landed. Releasing the mapping here rather
            // than inside the copy is what keeps the render wait out of the
            // loop: ovrtx waits for the copy event on the CPU during unmap, and
            // by now that event is already signaled.
            for (int i = 0; i < SHARED_IMAGE_COUNT; ++i) {
                FrameSlot& slot = slots[i];
                if (slot.state != FrameSlot::State::Writing ||
                    cuEventQuery(slot.copy_done) != CUDA_SUCCESS) {
                    continue;
                }
                if (slot.mapped) {
                    if (!release_mapped_output(
                            renderer, slot.map_handle, slot.copy_done)) {
                        cuda_cleanup();
                        cleanup_window();
                        return cleanup(1);
                    }
                    slot.mapped = false;
                }
                slot.state = FrameSlot::State::Ready;
                ready_queue.push_back(i);

                float cuda_elapsed_ms = 0.0f;
                cuEventElapsedTime(
                    &cuda_elapsed_ms, slot.copy_start, slot.copy_done);
                accumulated_cuda_ms += cuda_elapsed_ms;
                cuda_frame_count++;
                if (num_frames > 0) {
                    all_cuda_times_ms.push_back(cuda_elapsed_ms);
                }
            }

            // Show the oldest ready frame once its scheduled slot arrives. A
            // step's frames all become mappable at once, so without pacing they
            // are shown back to back and the loop then idles until the next step
            // lands, which reads as judder even though the counter looks healthy.
            if (!ready_queue.empty() && pacer.promotion_due(frame_start)) {
                int const next_idx = ready_queue.front();
                ready_queue.erase(ready_queue.begin());

                slots[read_idx].state = FrameSlot::State::Free;
                read_idx = next_idx;
                slots[read_idx].state = FrameSlot::State::Showing;
                read_timeline_value = slots[read_idx].timeline_value;
                read_holds_real_frame = slots[read_idx].holds_real_frame;

                ++total_frames;
                metrics.record_frame_promotion(frame_start);
                pacer.on_promotion(frame_start);
            }

            // Camera edits are authored into ovstage so the next attached step
            // renders from the new viewpoint.
            if (g_camera_dirty) {
                // [snippet:write-camera-transform]
                glm::mat4 transform = orbit_camera.transform_matrix();
                double transform_data[16];
                float const* src = glm::value_ptr(transform);
                for (int i = 0; i < 16; ++i) {
                    transform_data[i] = static_cast<double>(src[i]);
                }

                ++stage_ordinal;
                if (write_camera_transform(stage,
                                           camera_query,
                                           stage_ordinal,
                                           transform_data) ||
                    commit_ovstage_ordinal(stage, stage_ordinal)) {
                    cuda_cleanup();
                    cleanup_window();
                    return cleanup(1);
                }
                // [/snippet:write-camera-transform]

                g_camera_dirty = false;
            }

            // Copy into any free ring slot. Production is no longer gated on
            // presentation, so pacing can hold a frame back without also
            // throttling the renderer.
            int free_idx = -1;
            for (int i = 0; i < SHARED_IMAGE_COUNT; ++i) {
                if (slots[i].state == FrameSlot::State::Free) {
                    free_idx = i;
                    break;
                }
            }
            if (free_idx >= 0) {
                // Enqueue a step whenever none is in flight. Nothing below
                // blocks, so a step whose frames are not ready yet simply falls
                // through and the loop presents the previous frame again.
                if (!pending.in_flight()) {
                    std::optional<PickQueryNdc> pick_query =
                        pending_pick_query_ndc(window, tex_width, tex_height);
                    if (pick_query) {
                        ovrtx_pick_query_desc_t pick_desc = {};
                        pick_desc.render_product_path = render_product_str;
                        pick_desc.left_ndc = pick_query->left_ndc;
                        pick_desc.top_ndc = pick_query->top_ndc;
                        pick_desc.right_ndc = pick_query->right_ndc;
                        pick_desc.bottom_ndc = pick_query->bottom_ndc;
                        pick_desc.flags = 0;

                        enqueue_result =
                            ovrtx_enqueue_pick_query(renderer, &pick_desc);
                        if (check_and_print_error(enqueue_result,
                                                  "enqueue_pick_query")) {
                            cuda_cleanup();
                            cleanup_window();
                            return cleanup(1);
                        }
                        pending.pick_query_submitted = true;
                    }

                    // Step ovrtx with real frame delta so simulation/render
                    // timing matches interactive frame pacing.
                    auto now = std::chrono::steady_clock::now();
                    double delta_time =
                        std::chrono::duration<double>(now - last_step_time).count();
                    last_step_time = now;

                    enqueue_result = ovrtx_step_with_stage(renderer,
                                                           render_products,
                                                           delta_time,
                                                           stage_ordinal,
                                                           &pending.step_result);
                    if (check_and_print_error(enqueue_result, "step")) {
                        cuda_cleanup();
                        cleanup_window();
                        return cleanup(1);
                    }
                    pending.step_start = std::chrono::steady_clock::now();
                    pacer.on_step(pending.step_start);
                }

                // Poll for result metadata. The API does not promise the output
                // frames are mappable once this returns, so it is only the
                // first of two polled stages. In practice this renderer makes
                // every frame of the step mappable by the time the fetch
                // succeeds, which is why this is where the render wait is
                // observed to land; the map poll below stays because that
                // ordering is an implementation detail, not a guarantee.
                if (pending.in_flight() && !pending.results_fetched) {
                    result = ovrtx_fetch_results(renderer,
                                                 pending.step_result,
                                                 OVRTX_TIMEOUT_POLL,
                                                 &outputs);
                    if (result.status == OVRTX_API_SUCCESS) {
                        metrics.step_ms += elapsed_ms_since(pending.step_start);
                        ++metrics.steps;

                        refresh_render_feedback(window,
                                                accumulation_status,
                                                outputs,
                                                render_product_path);

                        if (pending.pick_query_submitted) {
                            pending.pick_output = find_render_var_output(
                                outputs, OVRTX_RENDER_VAR_PICK_HIT);
                        }

                        if (!collect_color_outputs(outputs,
                                                   render_product_path,
                                                   pending.color_outputs)) {
                            std::cerr << "ERROR: could not find output from "
                                      << render_product_path << std::endl;
                            ovrtx_destroy_results(renderer, pending.step_result);
                            cuda_cleanup();
                            cleanup_window();
                            return cleanup(2);
                        }
                        pending.next = 0;
                        pending.results_fetched = true;
                        pacer.set_frames_per_step(pending.color_outputs.size());
                        report_dlssg_frame_count(dlssg_enabled,
                                                 dlssg_interpolated_frames,
                                                 pending.color_outputs.size(),
                                                 dlssg_report);
                    } else if (result.status != OVRTX_API_TIMEOUT) {
                        check_and_print_error(result, "fetch_results");
                        ovrtx_destroy_results(renderer, pending.step_result);
                        cuda_cleanup();
                        cleanup_window();
                        return cleanup(1);
                    }
                }

                // Poll the pick hit on the same terms as the color output. It
                // is mapped on the CPU, so a blocking map here would stall
                // presentation for a whole readback; leaving the query pending
                // instead lets the loop keep presenting and retry next
                // iteration. The step stays in flight until it resolves, so no
                // pick is dropped.
                if (pending.results_fetched && pending.pick_query_submitted) {
                    PickOutputResult const pick_result =
                        process_pick_output(renderer,
                                            &path_dictionary,
                                            pending.pick_output,
                                            OVRTX_TIMEOUT_POLL,
                                            selected_prim_path_ids);
                    if (pick_result == PickOutputResult::Failed) {
                        ovrtx_destroy_results(renderer, pending.step_result);
                        cuda_cleanup();
                        cleanup_window();
                        return cleanup(1);
                    }
                    if (pick_result == PickOutputResult::Read) {
                        pending.pick_query_submitted = false;
                        pending.pick_output = OVRTX_INVALID_HANDLE;
                    }
                }

                // Poll the map for the next unconsumed frame of this step. The
                // renderer may still be producing it, in which case the loop
                // presents the previous frame again rather than stalling.
                bool copied_this_iteration = false;
                if (pending.results_fetched && !pending.drained()) {
                    size_t const frame_slot = pending.next;
                    FrameSlot& target = slots[free_idx];
                    auto map_copy_start = std::chrono::steady_clock::now();
                    cuEventRecord(target.copy_start, cuda_stream);
                    CopyOutputResult const copy_result = copy_output_to_surface(
                        renderer,
                        pending.color_outputs[pending.next],
                        free_idx,
                        cuda_format,
                        cuda_stream,
                        target.copy_done,
                        OVRTX_TIMEOUT_POLL,
                        &target.map_handle);
                    if (copy_result == CopyOutputResult::Failed) {
                        return fail_cuda_interop();
                    }
                    if (copy_result == CopyOutputResult::Copied) {
                        metrics.record_map_copy(frame_slot,
                                                elapsed_ms_since(map_copy_start));
                        target.mapped = true;
                        target.state = FrameSlot::State::Writing;
                        // The real rendered frame is the last of a step; the
                        // ones before it are interpolated.
                        ++pending.next;
                        target.holds_real_frame = pending.drained();
                        copied_this_iteration = true;
                    } else {
                        ++metrics.map_polls;
                    }
                }

                // Retire the step once every frame it produced has been copied
                // out and any pick hit has been read. The mappings are already
                // released, so this only frees the result metadata.
                if (pending.retirable()) {
                    result =
                        ovrtx_destroy_results(renderer, pending.step_result);
                    pending.step_result = 0;
                    pending.results_fetched = false;
                    if (check_and_print_error(result, "destroy_results")) {
                        cuda_cleanup();
                        cleanup_window();
                        return cleanup(1);
                    }
                }

                // copy_done was already recorded on the stream by
                // copy_output_to_surface, right after the copy it fences.
                if (copied_this_iteration) {
                    cuda_frame_counter++;
                    // Signal timeline value N for the buffer written this frame;
                    // Vulkan waits on this value before sampling that image.
                    slots[free_idx].timeline_value = cuda_frame_counter;
                    if (!cuda_signal_timeline(cuda_frame_counter,
                                              cuda_stream)) {
                        return fail_cuda_interop();
                    }
                }
            }

            // Render uses read buffer only; barriers below transfer queue
            // ownership between external (CUDA) and graphics queue for safe
            // sampling.
            CommandBuffer cmd = vk.command_buffer();
            cmd.begin();
            cmd.reset_query_pool(vk.timestamp_query_pool(), 0, 2);
            cmd.write_timestamp(VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                                vk.timestamp_query_pool(),
                                0);

            VkImage read_image =
                vk.sampled_image(shared_images[read_idx]).image;
            cmd.image_memory_barrier(read_image,
                                     VK_IMAGE_ASPECT_COLOR_BIT,
                                     VK_IMAGE_LAYOUT_GENERAL,
                                     VK_PIPELINE_STAGE_2_NONE,
                                     VK_ACCESS_2_NONE,
                                     VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                                     VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT,
                                     VK_ACCESS_2_SHADER_SAMPLED_READ_BIT,
                                     VK_QUEUE_FAMILY_EXTERNAL,
                                     vk.queue_family());

            cmd.image_memory_barrier(
                vk.swapchain_image(swapchain_image_index),
                VK_IMAGE_ASPECT_COLOR_BIT,
                VK_IMAGE_LAYOUT_UNDEFINED,
                VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                VK_ACCESS_2_NONE,
                VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
                VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT);

            record_rendering_state(cmd,
                                   vk,
                                   swapchain_image_index,
                                   vert_shader,
                                   frag_shader,
                                   overlay_vert_shader,
                                   overlay_frag_shader,
                                   shared_images[read_idx],
                                   current_marquee_overlay(window));

            cmd.image_memory_barrier(
                vk.swapchain_image(swapchain_image_index),
                VK_IMAGE_ASPECT_COLOR_BIT,
                VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
                VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                VK_IMAGE_LAYOUT_PRESENT_SRC_KHR,
                VK_PIPELINE_STAGE_2_BOTTOM_OF_PIPE_BIT,
                VK_ACCESS_2_NONE);

            cmd.image_memory_barrier(read_image,
                                     VK_IMAGE_ASPECT_COLOR_BIT,
                                     VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                                     VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT,
                                     VK_ACCESS_2_SHADER_SAMPLED_READ_BIT,
                                     VK_IMAGE_LAYOUT_GENERAL,
                                     VK_PIPELINE_STAGE_2_NONE,
                                     VK_ACCESS_2_NONE,
                                     vk.queue_family(),
                                     VK_QUEUE_FAMILY_EXTERNAL);

            cmd.write_timestamp(VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,
                                vk.timestamp_query_pool(),
                                1);
            cmd.end();
            PresentResult present_result = vk.submit_and_present(
                swapchain_image_index, read_timeline_value);
            if (present_result == PresentResult::OutOfDate ||
                present_result == PresentResult::Suboptimal) {
                defer_swapchain_recreate = true;
            }

            auto frame_end = std::chrono::steady_clock::now();
            double cpu_ms = std::chrono::duration<double, std::milli>(
                                frame_end - frame_start)
                                .count();
            accumulated_cpu_ms += cpu_ms;
            if (num_frames > 0) {
                all_cpu_times_ms.push_back(cpu_ms);
            }
            frame_count++;

            // total_frames counts frames that actually became visible, not loop
            // iterations: now that the map is polled, the loop re-presents the
            // same image many times while the next frame renders.
            if (num_frames > 0 && total_frames >= num_frames &&
                read_holds_real_frame) {
                break;
            }

            // Idle until the next frame is due rather than re-presenting the
            // same image as fast as the queue drains. Capped so window events
            // and render progress are still polled promptly.
            if (double const idle_ms =
                    pacer.ms_until_due(std::chrono::steady_clock::now());
                idle_ms > 0.0) {
                std::this_thread::sleep_for(std::chrono::microseconds(
                    static_cast<int64_t>(std::min(idle_ms, 2.0) * 1000.0)));
            }

            auto now = std::chrono::steady_clock::now();
            double elapsed_seconds =
                std::chrono::duration<double>(now - last_print_time).count();
            if (elapsed_seconds >= 1.0) {
                double avg_cpu_ms = accumulated_cpu_ms / frame_count;
                double avg_vulkan_ms = accumulated_vulkan_ms / frame_count;
                double avg_cuda_ms =
                    (cuda_frame_count > 0)
                        ? accumulated_cuda_ms / cuda_frame_count
                        : 0.0;

                double avg_step_ms =
                    (metrics.steps > 0) ? metrics.step_ms / metrics.steps : 0.0;
                double avg_map_copy_ms =
                    (metrics.copies > 0)
                        ? metrics.map_copy_ms / metrics.copies
                        : 0.0;

                std::cerr << "Avg (ms): CPU=" << avg_cpu_ms
                          << "  Step=" << avg_step_ms
                          << "  MapCopy=" << avg_map_copy_ms
                          << "  Vulkan=" << avg_vulkan_ms
                          << "  CUDA=" << avg_cuda_ms
                          << " | Steps/s=" << (metrics.steps / elapsed_seconds)
                          << "  Frames/s="
                          << (metrics.promotions / elapsed_seconds)
                          << "  Presents/s=" << (frame_count / elapsed_seconds)
                          << " | " << format_pt_accumulation_feedback(accumulation_status)
                          << std::endl;

                // Spread of the gaps between visible frames. Judder shows up
                // here as a wide min/max even when the mean looks healthy.
                if (metrics.promotion_gaps_ms.size() > 1) {
                    auto const [gap_min, gap_max] =
                        std::minmax_element(metrics.promotion_gaps_ms.begin(),
                                            metrics.promotion_gaps_ms.end());
                    double const gap_mean =
                        std::accumulate(metrics.promotion_gaps_ms.begin(),
                                        metrics.promotion_gaps_ms.end(),
                                        0.0) /
                        metrics.promotion_gaps_ms.size();
                    std::cerr << "  Frame gap (ms): min=" << *gap_min
                              << "  mean=" << gap_mean
                              << "  max=" << *gap_max
                              << "  | map polls=" << metrics.map_polls
                              << std::endl;
                }

                // With frame generation a step yields several frames; showing
                // the per-slot map cost tells us whether they land together or
                // one at a time.
                if (metrics.map_copy_ms_by_slot.size() > 1) {
                    std::cerr << "  MapCopy by frame-in-step (ms):";
                    for (size_t slot = 0;
                         slot < metrics.map_copy_ms_by_slot.size();
                         ++slot) {
                        int const n = metrics.frames_by_slot[slot];
                        std::cerr << "  [" << slot << "]="
                                  << ((n > 0)
                                          ? metrics.map_copy_ms_by_slot[slot] / n
                                          : 0.0);
                    }
                    std::cerr << std::endl;
                }

                accumulated_cpu_ms = 0.0;
                accumulated_vulkan_ms = 0.0;
                accumulated_cuda_ms = 0.0;
                frame_count = 0;
                cuda_frame_count = 0;
                metrics.reset();
                last_print_time = now;
            }
        }

        cuStreamSynchronize(cuda_stream);
        vk.wait_for_fence();

        // Mappings outlive their step result, so any still held by the ring must
        // be released explicitly. The stream is idle, so the unmap fence is
        // already signaled and this does not block.
        for (FrameSlot& slot : slots) {
            if (slot.mapped) {
                release_mapped_output(
                    renderer, slot.map_handle, slot.copy_done);
                slot.mapped = false;
            }
        }

        // The loop can exit with frames of the last step still unconsumed.
        if (pending.step_result != 0) {
            result = ovrtx_destroy_results(renderer, pending.step_result);
            pending.step_result = 0;
            check_and_print_error(result, "destroy_results");
        }

        // Print frame time statistics if --num-frames was specified
        if (num_frames > 0 && !headless) {
            print_frame_time_stats(total_frames,
                                   all_cpu_times_ms,
                                   all_vulkan_times_ms,
                                   all_cuda_times_ms);
        }

        // Save last rendered frame to PNG if --num-frames was specified. In
        // headless mode this doubles as interop validation via a checksum.
        if (num_frames > 0) {
            std::cerr << "Reading back frame from buffer " << read_idx
                      << "..." << std::endl;
            std::vector<uint8_t> pixels = cuda_read_surface_rgba8(
                read_idx, tex_width, tex_height, cuda_format);
            uint64_t const checksum = checksum_pixels(pixels);
            std::cerr << "Readback checksum: " << checksum << std::endl;
            if (pixels.empty() || checksum == 0) {
                std::cerr << "Readback validation failed" << std::endl;
                readback_ok = false;
            }

            if (!pixels.empty()) {
                int ok = stbi_write_png("out.png",
                                        tex_width,
                                        tex_height,
                                        4,
                                        pixels.data(),
                                        tex_width * 4);
                if (ok) {
                    std::cerr << "Saved out.png (" << tex_width << "x"
                              << tex_height << ")" << std::endl;
                } else {
                    std::cerr << "Failed to write out.png" << std::endl;
                    readback_ok = false;
                }
            } else {
                readback_ok = false;
            }
        }

        cuEventDestroy(cuda_copy_done_event);
        for (FrameSlot& slot : slots) {
            cuEventDestroy(slot.copy_start);
            cuEventDestroy(slot.copy_done);
        }
        cuStreamDestroy(cuda_stream);
        cuda_cleanup();
    } catch (std::exception const& e) {
        std::cerr << "Vulkan interop error: " << e.what() << std::endl;
        g_orbit_camera = nullptr;
        cleanup_window();
        return cleanup(1);
    }

    g_orbit_camera = nullptr;

    cleanup_window();
    int cleanup_result = cleanup(0);
    if (cleanup_result != 0) {
        return cleanup_result;
    }

    if (!readback_ok) {
        return 1;
    }

    std::cerr << "Done!" << std::endl;
    return 0;
}

// Get the directory containing the running executable (cross-platform).
// Used to locate shaders and other resources relative to the binary.
static auto get_executable_dir() -> std::filesystem::path {
#ifdef _WIN32
    wchar_t buf[MAX_PATH];
    DWORD len = GetModuleFileNameW(nullptr, buf, MAX_PATH);
    if (len == 0 || len == MAX_PATH) {
        throw std::runtime_error("GetModuleFileNameW failed");
    }
    return std::filesystem::path(buf).parent_path();
#elif defined(__linux__)
    return std::filesystem::canonical("/proc/self/exe").parent_path();
#else
#error "Unsupported platform"
#endif
}

static void
mouse_button_callback(GLFWwindow* window, int button, int action, int mods) {
    (void)mods;

    if (button == GLFW_MOUSE_BUTTON_RIGHT) {
        g_camera_mouse_pressed = (action == GLFW_PRESS);
        glfwGetCursorPos(window, &g_last_mouse_x, &g_last_mouse_y);
    } else if (button == GLFW_MOUSE_BUTTON_LEFT) {
        double x = 0.0;
        double y = 0.0;
        glfwGetCursorPos(window, &x, &y);

        if (action == GLFW_PRESS) {
            g_pick_drag.left_pressed = true;
            g_pick_drag.dragging = false;
            g_pick_drag.press_x = x;
            g_pick_drag.press_y = y;
            g_pick_drag.current_x = x;
            g_pick_drag.current_y = y;
        } else if (action == GLFW_RELEASE && g_pick_drag.left_pressed) {
            double dx = x - g_pick_drag.press_x;
            double dy = y - g_pick_drag.press_y;
            g_pick_drag.left_pressed = false;
            g_pick_drag.dragging = false;
            g_pick_drag.pending_is_drag =
                (dx * dx + dy * dy) >=
                (PICK_DRAG_THRESHOLD_PIXELS * PICK_DRAG_THRESHOLD_PIXELS);
            g_pick_drag.pending_start_x = g_pick_drag.press_x;
            g_pick_drag.pending_start_y = g_pick_drag.press_y;
            g_pick_drag.pending_end_x = x;
            g_pick_drag.pending_end_y = y;
            g_pick_drag.pending_query = true;
        }
    }
}

static void
cursor_position_callback(GLFWwindow* window, double xpos, double ypos) {
    (void)window;

    if (g_camera_mouse_pressed && g_orbit_camera) {
        float delta_x = static_cast<float>(xpos - g_last_mouse_x);
        float delta_y = static_cast<float>(ypos - g_last_mouse_y);

        g_orbit_camera->update(delta_x, delta_y);
        g_camera_dirty = true;
    }

    if (g_pick_drag.left_pressed) {
        g_pick_drag.current_x = xpos;
        g_pick_drag.current_y = ypos;
        double dx = xpos - g_pick_drag.press_x;
        double dy = ypos - g_pick_drag.press_y;
        g_pick_drag.dragging =
            (dx * dx + dy * dy) >=
            (PICK_DRAG_THRESHOLD_PIXELS * PICK_DRAG_THRESHOLD_PIXELS);
    }

    g_last_mouse_x = xpos;
    g_last_mouse_y = ypos;
}

static void
scroll_callback(GLFWwindow* window, double xoffset, double yoffset) {
    (void)window;
    (void)xoffset;

    if (g_orbit_camera) {
        // Dolly: scroll up = zoom in (decrease distance), scroll down = zoom
        // out
        float const dolly_factor = 0.1f;
        float current_distance = g_orbit_camera->distance();
        float new_distance =
            current_distance *
            (1.0f - static_cast<float>(yoffset) * dolly_factor);

        // Clamp to reasonable range (don't let it go negative or too close)
        float const min_distance = 0.1f;
        new_distance = std::max(new_distance, min_distance);

        g_orbit_camera->set_distance(new_distance);
        g_camera_dirty = true;
    }
}

static bool print_ovstage_error(ovstage_instance_t* stage,
                                ovstage_api_status_t status,
                                std::string_view operation)
{
    ovx_string_t error = ovstage_population_get_last_error();
    if ((!error.ptr || error.length == 0) && stage) {
        error = ovstage_get_last_error();
    }

    std::cerr << "ovstage " << operation << " failed ("
              << static_cast<int>(status) << ")";
    if (error.ptr && error.length > 0) {
        std::cerr << ": " << std::string_view(error.ptr, error.length);
    }
    std::cerr << std::endl;
    return true;
}

static bool wait_ovstage_op(ovstage_instance_t* stage,
                            ovstage_enqueue_result_t const& enqueue_result,
                            std::string_view operation)
{
    if (enqueue_result.status != OVSTAGE_OK) {
        return print_ovstage_error(stage, enqueue_result.status, operation);
    }

    ovstage_op_wait_result_t wait_result = {};
    ovstage_api_status_t status = ovstage_wait_op(stage,
                                                  enqueue_result.op_index,
                                                  OVSTAGE_TIMEOUT_INFINITE,
                                                  &wait_result);
    ovstage_release_op(stage, enqueue_result.op_index);
    if (status != OVSTAGE_OK) {
        return print_ovstage_error(stage, status, operation);
    }
    for (size_t i = 0; i < wait_result.error_op_id_count; ++i) {
        ovstage_op_id_t op_id = wait_result.error_op_ids[i];
        ovx_string_t error = ovstage_get_last_op_error(stage, op_id);
        std::cerr << "ovstage " << operation << ": op " << op_id << " failed";
        if (error.ptr && error.length > 0) {
            std::cerr << ": " << std::string_view(error.ptr, error.length);
        }
        std::cerr << std::endl;
    }
    return wait_result.error_op_id_count != 0;
}

static bool wait_population_op(ovstage_instance_t* stage,
                               ovstage_population_enqueue_result_t const& enqueue_result,
                               std::string_view operation)
{
    if (enqueue_result.status != OVSTAGE_OK) {
        return print_ovstage_error(stage, enqueue_result.status, operation);
    }

    ovstage_population_op_wait_result_t wait_result = {};
    ovstage_api_status_t status = ovstage_population_wait_op(stage,
                                                             enqueue_result.op_index,
                                                             OVSTAGE_TIMEOUT_INFINITE,
                                                             &wait_result);
    if (status != OVSTAGE_OK) {
        return print_ovstage_error(stage, status, operation);
    }
    for (size_t i = 0; i < wait_result.error_op_id_count; ++i) {
        ovstage_population_op_id_t op_id = wait_result.error_op_ids[i];
        ovx_string_t error = ovstage_population_get_last_op_error(op_id);
        std::cerr << "ovstage " << operation << ": op " << op_id << " failed";
        if (error.ptr && error.length > 0) {
            std::cerr << ": " << std::string_view(error.ptr, error.length);
        }
        std::cerr << std::endl;
    }
    return wait_result.error_op_id_count != 0;
}

static bool commit_ovstage_ordinal(ovstage_instance_t* stage,
                                   ovstage_ordinal_t ordinal)
{
    ovstage_write_floor_desc_t write_floor = {};
    write_floor.ordinal = ordinal;
    write_floor.scope = OVSTAGE_SCOPE_ALL;
    return wait_ovstage_op(stage,
                           ovstage_advance_write_floor(stage, &write_floor),
                           "advance_write_floor");
}

// Resolve a single prim by its USD path into a reusable ovstage query handle.
// Fails when the path does not match exactly one prim in the populated scene.
static bool create_validated_prim_query(ovstage_instance_t* stage,
                                        std::string_view prim_path,
                                        ovstage_query_handle_t* out_query)
{
    ovx_string_t path = {prim_path.data(), prim_path.size()};
    ovstage_predicate_t predicate = {};
    predicate.attribute.string = literal_to_ovx_string("usd-path");
    predicate.op = OVSTAGE_FILTER_OP_IN;
    predicate.values = &path;
    predicate.value_count = 1;

    ovstage_filter_t filter = {};
    filter.predicates = &predicate;
    filter.count = 1;

    ovstage_enqueue_result_t query_result =
        ovstage_query(stage, &filter, nullptr, 0, out_query);
    if (wait_ovstage_op(stage, query_result, "query_prim")) {
        if (*out_query != OVSTAGE_INVALID_QUERY_HANDLE) {
            wait_ovstage_op(stage, ovstage_release_query(stage, *out_query), "release_query");
            *out_query = OVSTAGE_INVALID_QUERY_HANDLE;
        }
        return true;
    }

    ovstage_query_result_t fetched = {};
    ovstage_api_status_t status =
        ovstage_fetch_query_result(stage, *out_query, OVSTAGE_TIMEOUT_INFINITE, &fetched);
    if (status != OVSTAGE_OK) {
        wait_ovstage_op(stage, ovstage_release_query(stage, *out_query), "release_query");
        *out_query = OVSTAGE_INVALID_QUERY_HANDLE;
        return print_ovstage_error(stage, status, "fetch_query_result");
    }

    bool failed = false;
    if (fetched.total_prim_count != 1) {
        std::cerr << "Prim '" << prim_path
                  << "' was not found in the populated ovstage scene" << std::endl;
        failed = true;
    }

    status = ovstage_release_query_result(stage, &fetched);
    if (status != OVSTAGE_OK) {
        print_ovstage_error(stage, status, "release_query_result");
        failed = true;
    }

    if (failed &&
        wait_ovstage_op(stage, ovstage_release_query(stage, *out_query), "release_query")) {
        failed = true;
    }
    if (failed) {
        *out_query = OVSTAGE_INVALID_QUERY_HANDLE;
    }
    return failed;
}

static bool write_camera_transform(ovstage_instance_t* stage,
                                   ovstage_query_handle_t camera_query,
                                   ovstage_ordinal_t ordinal,
                                   double const* transform_data)
{
    DLTensor transform_dl = {};
    transform_dl.data = const_cast<double*>(transform_data);
    transform_dl.device.device_type = kDLCPU;
    transform_dl.device.device_id = 0;
    transform_dl.ndim = 1;
    int64_t shape[1] = {1};
    transform_dl.shape = shape;
    transform_dl.strides = nullptr;
    transform_dl.byte_offset = 0;
    transform_dl.dtype.code = kDLFloat;
    transform_dl.dtype.bits = 64;
    transform_dl.dtype.lanes = 16;

    ovstage_write_data_t write_data = {};
    write_data.tensors = &transform_dl;
    write_data.tensor_count = 1;
    write_data.semantic = OVSTAGE_SEMANTIC_MATRIX;

    ovx_string_or_token_t attribute = {};
    attribute.string = literal_to_ovx_string("omni:xform");

    return wait_ovstage_op(
        stage,
        ovstage_write_attribute(stage,
                                camera_query,
                                attribute,
                                ordinal,
                                write_data,
                                OVSTAGE_PRIM_MODE_UPSERT),
        "write_camera_transform");
}

// [snippet:enable-dlssg]
// DLSS Frame Generation is a per-RenderProduct render setting: two attributes on
// the RenderProduct prim, read by the renderer from the runtime scene. Authoring
// them through ovstage is therefore equivalent to declaring them in the USD file,
// and does not require the RTX settings API schema to be applied to the prim.
//
// Both attributes are always written, including when frame generation is off, so
// the command line stays authoritative over whatever the scene authored.
static bool author_dlssg_settings(ovstage_instance_t* stage,
                                  std::string_view render_product_path,
                                  ovstage_ordinal_t ordinal,
                                  bool enabled,
                                  int interpolated_frames)
{
    ovstage_query_handle_t render_product_query = OVSTAGE_INVALID_QUERY_HANDLE;
    if (create_validated_prim_query(
            stage, render_product_path, &render_product_query)) {
        return true;
    }

    uint8_t enabled_value = enabled ? 1 : 0;
    int64_t shape[1] = {1};

    DLTensor enabled_dl = {};
    enabled_dl.data = &enabled_value;
    enabled_dl.device.device_type = kDLCPU;
    enabled_dl.device.device_id = 0;
    enabled_dl.ndim = 1;
    enabled_dl.shape = shape;
    enabled_dl.dtype.code = kDLBool;
    enabled_dl.dtype.bits = 8;
    enabled_dl.dtype.lanes = 1;

    // A count of 0 leaves the interpolated frame count up to the renderer; any
    // other value is clamped to what the GPU supports.
    int32_t frame_count_value = interpolated_frames;
    DLTensor frame_count_dl = enabled_dl;
    frame_count_dl.data = &frame_count_value;
    frame_count_dl.dtype.code = kDLInt;
    frame_count_dl.dtype.bits = 32;

    ovstage_write_data_t enabled_write = {};
    enabled_write.tensors = &enabled_dl;
    enabled_write.tensor_count = 1;

    ovstage_write_data_t frame_count_write = enabled_write;
    frame_count_write.tensors = &frame_count_dl;

    ovx_string_or_token_t enabled_attribute = {};
    enabled_attribute.string =
        literal_to_ovx_string("omni:rtx:dlss:frameGeneration");
    ovx_string_or_token_t frame_count_attribute = {};
    frame_count_attribute.string = literal_to_ovx_string(
        "omni:rtx:dlss:frameGenerationInterpolatedFrameCount");

    // |= rather than ||: the second write and the release must run even if an
    // earlier step failed, so the query handle is never stranded.
    bool failed = wait_ovstage_op(stage,
                                  ovstage_write_attribute(stage,
                                                          render_product_query,
                                                          enabled_attribute,
                                                          ordinal,
                                                          enabled_write,
                                                          OVSTAGE_PRIM_MODE_UPSERT),
                                  "write_dlssg_frame_generation");
    failed |= wait_ovstage_op(stage,
                              ovstage_write_attribute(stage,
                                                      render_product_query,
                                                      frame_count_attribute,
                                                      ordinal,
                                                      frame_count_write,
                                                      OVSTAGE_PRIM_MODE_UPSERT),
                              "write_dlssg_interpolated_frame_count");
    failed |= wait_ovstage_op(stage,
                              ovstage_release_query(stage, render_product_query),
                              "release_query");
    return failed;
}
// [/snippet:enable-dlssg]

static auto find_accumulation_status(
    ovrtx_render_product_set_outputs_t const& outputs,
    std::string_view render_product_path) -> std::optional<ovrtx_accumulation_status_t> {
    for (size_t i = 0; i < outputs.output_count; ++i) {
        ovrtx_render_product_output_t const& product_output = outputs.outputs[i];
        if (product_output.output_frame_count == 0) {
            continue;
        }
        if (!ovx_string_equals(product_output.render_product_path,
                               render_product_path)) {
            continue;
        }
        // The real rendered frame is always last; DLSS-G interpolated frames
        // carry no accumulation status of their own.
        return product_output
            .output_frames[product_output.output_frame_count - 1]
            .accumulation_status;
    }
    return std::nullopt;
}

static auto format_pt_accumulation_feedback(
    ovrtx_accumulation_status_t const& accumulation_status) -> std::string {
    std::string feedback = "Progression: " + std::to_string(accumulation_status.progression);
    if (accumulation_status.converged) {
        feedback += " (converged)";
    }
    return feedback;
}

static void update_window_title(GLFWwindow* window,
                                ovrtx_accumulation_status_t const& accumulation_status) {
    if (!window) {
        return;
    }

    const std::string title =
        "ovrtx-Vulkan Interop | " + format_pt_accumulation_feedback(accumulation_status);
    glfwSetWindowTitle(window, title.c_str());
}

static void refresh_render_feedback(GLFWwindow* window,
                                    ovrtx_accumulation_status_t& accumulation_status,
                                    ovrtx_render_product_set_outputs_t const& outputs,
                                    std::string_view render_product_path) {
    if (auto const acc = find_accumulation_status(outputs, render_product_path)) {
        accumulation_status = *acc;
    }

    update_window_title(window, accumulation_status);
}

static void print_usage(char const* program_name) {
    std::cerr << "Usage: " << program_name << " [options]" << std::endl;
    std::cerr << std::endl << "Options:" << std::endl;
    std::cerr << "  --usd, -u <path>          USD file path or URL (default: "
                 "robot-ovrtx sample)" << std::endl;
    std::cerr
        << "  --render-product, -r <path>  Render product prim path (default: "
        << DEFAULT_RENDER_PRODUCT_PATH << ")" << std::endl;
    std::cerr << "  --up-axis, -a <Y|Z>       Scene up axis (default: Z)" << std::endl;
    std::cerr
        << "  --units <meters|centimeters>  Scene units (default: meters)" << std::endl;
    std::cerr
        << "  --num-frames, -n <N>      Render N frames then save out.png "
           "and exit" << std::endl;
    std::cerr
        << "  --headless, --no-window   Run Vulkan/CUDA interop validation "
           "without GLFW" << std::endl;
    std::cerr << "  --camera, -c <path>       Orbit camera prim (default: "
              << DEFAULT_CAMERA_PRIM_PATH << ")" << std::endl;
    std::cerr
        << "  --dlssg                   Enable DLSS Frame Generation (default: "
           "off)" << std::endl;
    std::cerr
        << "  --present-mode <mode>     fifo | mailbox | immediate "
           "(default: fifo)" << std::endl
        << "                            fifo waits for vsync; mailbox and "
           "immediate do not" << std::endl
        << "  --pace                    Space generated frames evenly instead "
           "of in bursts" << std::endl
        << "  --dlssg-frames <N>        Interpolated frames per rendered frame, "
           "implies --dlssg" << std::endl;
    std::cerr
        << "                            (default: renderer picks, capped by the "
           "GPU)" << std::endl;
    std::cerr << "  --help, -h                Show this help message" << std::endl;
}

static bool parse_args(int argc,
                       char* argv[],
                       std::string& usd_file,
                       std::string& render_product,
                       std::string& camera_prim_path,
                       UpAxis& up_axis,
                       Units& units,
                       int& num_frames,
                       bool& headless,
                       bool& dlssg_enabled,
                       int& dlssg_interpolated_frames,
                       PresentMode& present_mode,
                       bool& pace_frames) {
    // Set defaults
    usd_file = DEFAULT_USD_FILE_URL;
    render_product = DEFAULT_RENDER_PRODUCT_PATH;
    camera_prim_path = DEFAULT_CAMERA_PRIM_PATH;
    up_axis = DEFAULT_UP_AXIS;
    units = DEFAULT_SCENE_UNITS;
    num_frames = 0;
    headless = false;
    dlssg_enabled = false;
    dlssg_interpolated_frames = DEFAULT_DLSSG_INTERPOLATED_FRAMES;
    present_mode = PresentMode::Fifo;
    pace_frames = false;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];

        if (arg == "--help" || arg == "-h") {
            print_usage(argv[0]);
            return false;
        } else if (arg == "--usd" || arg == "-u") {
            if (i + 1 >= argc) {
                std::cerr << "Error: " << arg << " requires an argument" << std::endl;
                return false;
            }
            usd_file = argv[++i];
        } else if (arg == "--render-product" || arg == "-r") {
            if (i + 1 >= argc) {
                std::cerr << "Error: " << arg << " requires an argument" << std::endl;
                return false;
            }
            render_product = argv[++i];
        } else if (arg == "--camera" || arg == "-c") {
            if (i + 1 >= argc) {
                std::cerr << "Error: " << arg << " requires an argument" << std::endl;
                return false;
            }
            camera_prim_path = argv[++i];
            if (camera_prim_path.empty() || camera_prim_path.front() != '/') {
                std::cerr << "Error: camera path must be absolute (e.g. /World/Camera)"
                          << std::endl;
                return false;
            }
        } else if (arg == "--up-axis" || arg == "-a") {
            if (i + 1 >= argc) {
                std::cerr << "Error: " << arg << " requires an argument" << std::endl;
                return false;
            }
            std::string val = argv[++i];
            if (val == "Y" || val == "y") {
                up_axis = UpAxis::Y;
            } else if (val == "Z" || val == "z") {
                up_axis = UpAxis::Z;
            } else {
                std::cerr << "Error: invalid up-axis '" << val
                          << "', must be Y or Z" << std::endl;
                return false;
            }
        } else if (arg == "--units") {
            if (i + 1 >= argc) {
                std::cerr << "Error: " << arg << " requires an argument" << std::endl;
                return false;
            }
            std::string val = argv[++i];
            if (val == "meters" || val == "m") {
                units = Units::Meters;
            } else if (val == "centimeters" || val == "cm") {
                units = Units::Centimeters;
            } else {
                std::cerr << "Error: invalid units '" << val
                          << "', must be 'meters' or 'centimeters'" << std::endl;
                return false;
            }
        } else if (arg == "--num-frames" || arg == "-n") {
            if (i + 1 >= argc) {
                std::cerr << "Error: " << arg << " requires an argument" << std::endl;
                return false;
            }
            num_frames = std::stoi(argv[++i]);
            if (num_frames <= 0) {
                std::cerr << "Error: --num-frames must be a positive integer" << std::endl;
                return false;
            }
        } else if (arg == "--headless" || arg == "--no-window") {
            headless = true;
        } else if (arg == "--dlssg") {
            dlssg_enabled = true;
        } else if (arg == "--dlssg-frames") {
            if (i + 1 >= argc) {
                std::cerr << "Error: " << arg << " requires an argument" << std::endl;
                return false;
            }
            dlssg_interpolated_frames = std::stoi(argv[++i]);
            if (dlssg_interpolated_frames < 1) {
                std::cerr << "Error: --dlssg-frames must be a positive integer"
                          << std::endl;
                return false;
            }
            dlssg_enabled = true;
        } else if (arg == "--pace") {
            pace_frames = true;
        } else if (arg == "--present-mode") {
            if (i + 1 >= argc) {
                std::cerr << "Error: " << arg << " requires an argument" << std::endl;
                return false;
            }
            std::string val = argv[++i];
            if (!parse_present_mode(val, present_mode)) {
                std::cerr << "Error: invalid present mode '" << val
                          << "', must be fifo, mailbox or immediate"
                          << std::endl;
                return false;
            }
        } else {
            std::cerr << "Error: unknown option '" << arg << "'" << std::endl;
            print_usage(argv[0]);
            return false;
        }
    }

    return true;
}

static bool parse_present_mode(std::string_view value, PresentMode& mode) {
    if (value == "fifo") {
        mode = PresentMode::Fifo;
    } else if (value == "mailbox") {
        mode = PresentMode::Mailbox;
    } else if (value == "immediate") {
        mode = PresentMode::Immediate;
    } else {
        return false;
    }
    return true;
}

template <typename ResultT>
static bool check_and_print_error(ResultT const& result,
                                  std::string_view operation) {
    if (result.status != OVRTX_API_SUCCESS) {
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

static auto vulkan_format_for_output(OutputType type) -> VkFormat {
    return (type == OutputType::HdrColor) ? VK_FORMAT_R16G16B16A16_SFLOAT
                                          : VK_FORMAT_R8G8B8A8_SRGB;
}

static auto cuda_format_for_output(OutputType type) -> CudaImageFormat {
    return (type == OutputType::HdrColor) ? CudaImageFormat::Half4
                                          : CudaImageFormat::UInt8_4;
}

static auto output_type_name(OutputType type) -> char const* {
    return (type == OutputType::HdrColor) ? "HdrColor" : "LdrColor";
}

static auto checksum_pixels(std::vector<uint8_t> const& pixels) -> uint64_t {
    uint64_t checksum = 0;
    for (size_t i = 0; i < pixels.size(); ++i) {
        checksum += static_cast<uint64_t>(i + 1) * pixels[i];
    }
    return checksum;
}

// Keep perf reporting separate from the render loop so timing collection logic
// stays focused on sync/render decisions.
static void print_frame_time_stats(int total_frames,
                                   std::vector<double> const& cpu_times_ms,
                                   std::vector<double> const& vulkan_times_ms,
                                   std::vector<double> const& cuda_times_ms) {
    auto compute_stats = [](std::vector<double> const& times)
        -> std::tuple<double, double, double> {
        if (times.empty()) {
            return {0.0, 0.0, 0.0};
        }
        double min_val = *std::min_element(times.begin(), times.end());
        double max_val = *std::max_element(times.begin(), times.end());
        double sum = 0.0;
        for (double t : times) {
            sum += t;
        }
        double mean = sum / static_cast<double>(times.size());
        return {min_val, max_val, mean};
    };

    // The CPU and Vulkan samples are per loop iteration, which is no longer one
    // per visible frame: the loop re-presents the current image while the next
    // one renders. total_frames counts the frames that actually became visible.
    std::cerr << std::endl << "=== Loop Time Statistics (" << total_frames
              << " frames shown) ===" << std::endl;

    auto [cpu_min, cpu_max, cpu_mean] = compute_stats(cpu_times_ms);
    std::cerr << "CPU:    min=" << cpu_min << " ms  max=" << cpu_max
              << " ms  mean=" << cpu_mean << " ms  (n=" << cpu_times_ms.size()
              << ")" << std::endl;

    auto [vk_min, vk_max, vk_mean] = compute_stats(vulkan_times_ms);
    std::cerr << "Vulkan: min=" << vk_min << " ms  max=" << vk_max
              << " ms  mean=" << vk_mean << " ms  (n=" << vulkan_times_ms.size()
              << ")" << std::endl;

    auto [cuda_min, cuda_max, cuda_mean] = compute_stats(cuda_times_ms);
    std::cerr << "CUDA:   min=" << cuda_min << " ms  max=" << cuda_max
              << " ms  mean=" << cuda_mean << " ms  (n=" << cuda_times_ms.size()
              << ")" << std::endl;
}

// Record only the draw-time graphics state for presenting the already-populated
// shared image. Ownership/layout barriers are handled by the caller.
static void record_rendering_state(CommandBuffer& cmd,
                                   VulkanContext& vk,
                                   uint32_t swapchain_image_index,
                                   ShaderHandle vert_shader,
                                   ShaderHandle frag_shader,
                                   ShaderHandle overlay_vert_shader,
                                   ShaderHandle overlay_frag_shader,
                                   SampledImageHandle read_image_handle,
                                   MarqueeOverlay const& marquee) {
    VkRenderingAttachmentInfo color_attachment = {};
    color_attachment.sType = VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO;
    color_attachment.imageView = vk.swapchain_image_view(swapchain_image_index);
    color_attachment.imageLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    color_attachment.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
    color_attachment.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
    color_attachment.clearValue.color = {
        {0.1f, 0.1f, 0.1f, 1.0f}
    };

    VkRenderingInfo rendering_info = {};
    rendering_info.sType = VK_STRUCTURE_TYPE_RENDERING_INFO;
    rendering_info.renderArea.offset = {0, 0};
    rendering_info.renderArea.extent = vk.swapchain_extent();
    rendering_info.layerCount = 1;
    rendering_info.colorAttachmentCount = 1;
    rendering_info.pColorAttachments = &color_attachment;

    cmd.begin_rendering(rendering_info);

    VkExtent2D extent = vk.swapchain_extent();
    cmd.set_viewport(0.0f,
                     0.0f,
                     static_cast<float>(extent.width),
                     static_cast<float>(extent.height));
    cmd.set_scissor(0, 0, extent.width, extent.height);
    cmd.set_rasterizer_discard_enable(false);
    cmd.set_polygon_mode(VK_POLYGON_MODE_FILL);
    cmd.set_cull_mode(VK_CULL_MODE_NONE);
    cmd.set_front_face(VK_FRONT_FACE_COUNTER_CLOCKWISE);
    cmd.set_depth_bias_enable(false);
    cmd.set_primitive_topology(VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST);
    cmd.set_primitive_restart_enable(false);
    cmd.set_depth_test_enable(false);
    cmd.set_depth_write_enable(false);
    cmd.set_depth_bounds_test_enable(false);
    cmd.set_stencil_test_enable(false);
    cmd.set_rasterization_samples(VK_SAMPLE_COUNT_1_BIT);
    cmd.set_sample_mask(VK_SAMPLE_COUNT_1_BIT, 0xFFFFFFFF);
    cmd.set_alpha_to_coverage_enable(false);
    cmd.set_color_blend_enable(0, false);
    cmd.set_color_write_mask(
        0,
        VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
            VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT);
    cmd.set_vertex_input_empty();

    vk.bind_shaders(vert_shader, frag_shader);
    VkDescriptorSet desc_set = vk.descriptor_set();
    cmd.bind_descriptor_sets(
        VK_PIPELINE_BIND_POINT_GRAPHICS, vk.pipeline_layout(), 0, 1, &desc_set);

    uint32_t tex_idx = vk.sampled_image(read_image_handle).descriptor_index;
    cmd.push_constants(vk.pipeline_layout(),
                       VK_SHADER_STAGE_FRAGMENT_BIT,
                       0,
                       sizeof(tex_idx),
                       &tex_idx);

    cmd.draw(3);
    record_marquee_overlay(
        cmd, vk, overlay_vert_shader, overlay_frag_shader, marquee);
    cmd.end_rendering();
}

static void record_marquee_overlay(CommandBuffer& cmd,
                                   VulkanContext& vk,
                                   ShaderHandle overlay_vert_shader,
                                   ShaderHandle overlay_frag_shader,
                                   MarqueeOverlay const& marquee) {
    if (!marquee.visible) {
        return;
    }

    VkExtent2D extent = vk.swapchain_extent();
    if (extent.width == 0 || extent.height == 0) {
        return;
    }

    cmd.set_primitive_topology(VK_PRIMITIVE_TOPOLOGY_LINE_STRIP);
    cmd.set_color_blend_enable(0, false);
    vk.bind_shaders(overlay_vert_shader, overlay_frag_shader);

    OverlayPushConstants push = {};
    push.rect[0] = marquee.left;
    push.rect[1] = marquee.top;
    push.rect[2] = marquee.right;
    push.rect[3] = marquee.bottom;
    push.viewport_size[0] = static_cast<float>(extent.width);
    push.viewport_size[1] = static_cast<float>(extent.height);
    cmd.push_constants(vk.pipeline_layout(),
                       VK_SHADER_STAGE_VERTEX_BIT,
                       0,
                       sizeof(push),
                       &push);
    cmd.draw(5);
}

static auto window_to_framebuffer_point(GLFWwindow* window,
                                        double x,
                                        double y)
    -> std::optional<std::pair<double, double>> {
    int window_width = 0;
    int window_height = 0;
    int framebuffer_width = 0;
    int framebuffer_height = 0;
    glfwGetWindowSize(window, &window_width, &window_height);
    glfwGetFramebufferSize(window, &framebuffer_width, &framebuffer_height);
    if (window_width <= 0 || window_height <= 0 || framebuffer_width <= 0 ||
        framebuffer_height <= 0) {
        return std::nullopt;
    }

    double scale_x =
        static_cast<double>(framebuffer_width) / static_cast<double>(window_width);
    double scale_y = static_cast<double>(framebuffer_height) /
                     static_cast<double>(window_height);
    return std::make_pair(x * scale_x, y * scale_y);
}

static auto current_marquee_overlay(GLFWwindow* window) -> MarqueeOverlay {
    MarqueeOverlay marquee = {};
    if (!g_pick_drag.left_pressed || !g_pick_drag.dragging) {
        return marquee;
    }

    auto press = window_to_framebuffer_point(
        window, g_pick_drag.press_x, g_pick_drag.press_y);
    auto current = window_to_framebuffer_point(
        window, g_pick_drag.current_x, g_pick_drag.current_y);
    if (!press || !current) {
        return marquee;
    }

    int framebuffer_width = 0;
    int framebuffer_height = 0;
    glfwGetFramebufferSize(window, &framebuffer_width, &framebuffer_height);
    double left = std::clamp(std::min(press->first, current->first),
                             0.0,
                             static_cast<double>(framebuffer_width));
    double top = std::clamp(std::min(press->second, current->second),
                            0.0,
                            static_cast<double>(framebuffer_height));
    double right = std::clamp(std::max(press->first, current->first),
                              0.0,
                              static_cast<double>(framebuffer_width));
    double bottom = std::clamp(std::max(press->second, current->second),
                               0.0,
                               static_cast<double>(framebuffer_height));

    if (right <= left || bottom <= top) {
        return marquee;
    }

    marquee.visible = true;
    marquee.left = static_cast<float>(left);
    marquee.top = static_cast<float>(top);
    marquee.right = static_cast<float>(right);
    marquee.bottom = static_cast<float>(bottom);
    return marquee;
}

static auto pending_pick_query_ndc(GLFWwindow* window,
                                   int tex_width,
                                   int tex_height)
    -> std::optional<PickQueryNdc> {
    if (!g_pick_drag.pending_query || tex_width <= 0 || tex_height <= 0) {
        return std::nullopt;
    }

    int window_width = 0;
    int window_height = 0;
    glfwGetWindowSize(window, &window_width, &window_height);
    if (window_width <= 0 || window_height <= 0) {
        return std::nullopt;
    }

    auto to_pixel = [window_width, window_height, tex_width, tex_height](
                        double x, double y) -> std::pair<int32_t, int32_t> {
        double u = std::clamp(x / static_cast<double>(window_width), 0.0, 1.0);
        double v = std::clamp(y / static_cast<double>(window_height), 0.0, 1.0);
        int32_t px = static_cast<int32_t>(std::floor(u * tex_width));
        int32_t py = static_cast<int32_t>(std::floor(v * tex_height));
        px = std::clamp(px, int32_t{0}, static_cast<int32_t>(tex_width - 1));
        py = std::clamp(py, int32_t{0}, static_cast<int32_t>(tex_height - 1));
        return {px, py};
    };

    double end_x =
        g_pick_drag.pending_is_drag ? g_pick_drag.pending_end_x
                                    : g_pick_drag.pending_start_x;
    double end_y =
        g_pick_drag.pending_is_drag ? g_pick_drag.pending_end_y
                                    : g_pick_drag.pending_start_y;
    auto [x0, y0] =
        to_pixel(g_pick_drag.pending_start_x, g_pick_drag.pending_start_y);
    auto [x1, y1] = to_pixel(end_x, end_y);

    PickQueryNdc query = {};
    query.left_ndc = static_cast<float>(std::min(x0, x1)) / static_cast<float>(tex_width);
    query.top_ndc = static_cast<float>(std::min(y0, y1)) / static_cast<float>(tex_height);
    query.right_ndc =
        static_cast<float>(std::min(std::max(x0, x1) + 1, static_cast<int32_t>(tex_width))) /
        static_cast<float>(tex_width);
    query.bottom_ndc =
        static_cast<float>(std::min(std::max(y0, y1) + 1, static_cast<int32_t>(tex_height))) /
        static_cast<float>(tex_height);
    g_pick_drag.pending_query = false;
    return query;
}

static auto find_render_var_output(ovrtx_render_product_set_outputs_t const& outputs,
                                   std::string_view render_var_path)
    -> ovrtx_render_var_output_handle_t {
    for (size_t i = 0; i < outputs.output_count; ++i) {
        ovrtx_render_product_output_t const& product_output =
            outputs.outputs[i];
        for (size_t f = 0; f < product_output.output_frame_count; ++f) {
            ovrtx_render_product_frame_output_t const& frame =
                product_output.output_frames[f];
            for (size_t v = 0; v < frame.render_var_count; ++v) {
                ovrtx_render_product_render_var_output_t const& var =
                    frame.output_render_vars[v];
                if (ovx_string_equals(var.render_var_path, render_var_path)) {
                    return var.output_handle;
                }
            }
        }
    }

    return 0;
}

static PickOutputResult process_pick_output(
    ovrtx_renderer_t* renderer,
    path_dictionary_instance_t* path_dictionary,
    ovrtx_render_var_output_handle_t pick_output_handle,
    ovrtx_timeout_t map_timeout,
    std::vector<ovx_primpath_t>& selected_prim_path_ids) {
    PickedPrims picked_prims;
    PickOutputResult const result = read_picked_prims(
        renderer, path_dictionary, pick_output_handle, map_timeout, picked_prims);
    if (result != PickOutputResult::Read) {
        return result;
    }

    print_picked_prims(picked_prims.paths);
    if (!update_selection_outline(
            renderer, selected_prim_path_ids, picked_prims.path_ids)) {
        return PickOutputResult::Failed;
    }

    selected_prim_path_ids = picked_prims.path_ids;
    return PickOutputResult::Read;
}

static bool configure_selection_style(ovrtx_renderer_t* renderer) {
    const uint8_t group_ids[] = {SELECTED_OUTLINE_GROUP};
    const ovrtx_selection_group_style_t styles[] = {SELECTED_OUTLINE_STYLE};
    ovrtx_enqueue_result_t result =
        ovrtx_set_selection_group_styles(renderer, group_ids, styles, 1);
    return !check_and_print_error(result, "set_selection_group_styles");
}

static bool update_selection_outline(ovrtx_renderer_t* renderer,
                                     std::vector<ovx_primpath_t> const& previous_selection,
                                     std::vector<ovx_primpath_t> const& next_selection) {
    // Clear the previous selection first so prims dropped from the selection
    // lose their outline, then assign the new selection to the outline group.
    if (!write_selection_outline_group(renderer, previous_selection, 0)) {
        return false;
    }
    return write_selection_outline_group(renderer, next_selection, SELECTED_OUTLINE_GROUP);
}

static bool write_selection_outline_group(ovrtx_renderer_t* renderer,
                                          std::vector<ovx_primpath_t> const& prim_path_ids,
                                          uint8_t group_id) {
    if (prim_path_ids.empty()) {
        return true;
    }

    std::vector<uint8_t> group_ids(prim_path_ids.size(), group_id);
    ovrtx_enqueue_result_t result =
        ovrtx_set_selection_outline_group(renderer,
                                          prim_path_ids.data(),
                                          prim_path_ids.size(),
                                          group_ids.data());
    return !check_and_print_error(result, "set_selection_outline_group");
}

static PickOutputResult read_picked_prims(
    ovrtx_renderer_t* renderer,
    path_dictionary_instance_t* path_dictionary,
    ovrtx_render_var_output_handle_t pick_output_handle,
    ovrtx_timeout_t map_timeout,
    PickedPrims& picked_prims) {
    if (pick_output_handle == OVRTX_INVALID_HANDLE) {
        std::cerr << "ERROR: pick query produced no "
                  << OVRTX_RENDER_VAR_PICK_HIT << " output\n";
        return PickOutputResult::Failed;
    }

    ovrtx_map_output_description_t map_desc = {};
    map_desc.device_type = OVRTX_MAP_DEVICE_TYPE_CPU;

    ovrtx_render_var_output_t pick_output = {};
    ovrtx_result_t result = ovrtx_map_render_var_output(renderer,
                                                        pick_output_handle,
                                                        &map_desc,
                                                        map_timeout,
                                                        &pick_output);
    if (result.status == OVRTX_API_TIMEOUT) {
        return PickOutputResult::NotReady;
    }
    if (check_and_print_error(result, "map_pick_output")) {
        return PickOutputResult::Failed;
    }

    bool parsed = true;
    DLTensor const* prim_path_tensor =
        find_render_var_tensor(pick_output, "primPath");
    DLTensor const* magic_param = find_render_var_param(pick_output, "magic");
    DLTensor const* version_param =
        find_render_var_param(pick_output, "version");
    DLTensor const* hit_count_param =
        find_render_var_param(pick_output, "hitCount");

    uint32_t magic = magic_param && magic_param->data ?
        *static_cast<uint32_t const*>(magic_param->data) : 0;
    uint32_t version = version_param && version_param->data ?
        *static_cast<uint32_t const*>(version_param->data) : 0;
    uint32_t hit_count = hit_count_param && hit_count_param->data ?
        *static_cast<uint32_t const*>(hit_count_param->data) : 0;

    if (magic != OVRTX_PICK_HIT_MAGIC ||
        version != OVRTX_PICK_HIT_VERSION) {
        std::cerr << "ERROR: unexpected pick hit schema"
                  << " magic=0x" << std::hex << magic << std::dec
                  << " version=" << version << "\n";
        parsed = false;
    } else if (hit_count == 0) {
        // Miss (sky/background): primPath column is length 0 and data may be null.
        picked_prims = PickedPrims{};
    } else if (!prim_path_tensor || !prim_path_tensor->shape ||
               prim_path_tensor->ndim != 1 ||
               prim_path_tensor->shape[0] < static_cast<int64_t>(hit_count) ||
               !prim_path_tensor->data) {
        std::cerr << "ERROR: unexpected pick hit primPath tensor layout"
                  << " ndim=" << (prim_path_tensor ? prim_path_tensor->ndim : -1)
                  << " shape0="
                  << (prim_path_tensor && prim_path_tensor->shape
                          ? prim_path_tensor->shape[0]
                          : -1)
                  << " hit_count=" << hit_count
                  << " data="
                  << (prim_path_tensor && prim_path_tensor->data ? "set" : "null")
                  << "\n";
        parsed = false;
    } else {
        auto const* prim_paths = reinterpret_cast<ovx_primpath_t const*>(
            reinterpret_cast<uint8_t const*>(prim_path_tensor->data) +
            prim_path_tensor->byte_offset);
        for (uint32_t i = 0; i < hit_count; ++i) {
            if (prim_paths[i] == 0) {
                continue;
            }
            if (std::find(picked_prims.path_ids.begin(),
                          picked_prims.path_ids.end(),
                          prim_paths[i]) != picked_prims.path_ids.end()) {
                continue;
            }
            std::string path =
                resolve_primpath(path_dictionary, prim_paths[i]);
            if (!path.empty()) {
                picked_prims.path_ids.push_back(prim_paths[i]);
                picked_prims.paths.push_back(path);
            }
        }
    }

    ovrtx_cuda_sync_t no_sync = {};
    result = ovrtx_unmap_render_var_output(
        renderer, pick_output.map_handle, no_sync);
    if (check_and_print_error(result, "unmap_pick_output")) {
        return PickOutputResult::Failed;
    }

    return parsed ? PickOutputResult::Read : PickOutputResult::Failed;
}

static auto resolve_primpath(path_dictionary_instance_t* path_dictionary,
                             ovx_primpath_t prim_path) -> std::string {
    std::array<ovx_token_t, 128> token_buffer = {};
    ovx_token_t* tokens = nullptr;
    size_t token_count = 0;
    size_t path_count = 0;
    ovx_api_result_t result =
        path_dictionary_get_tokens_from_paths(path_dictionary,
                                              &prim_path,
                                              1,
                                              token_buffer.data(),
                                              token_buffer.size(),
                                              &tokens,
                                              &token_count,
                                              &path_count);
    if (result.status != OVX_API_SUCCESS || path_count != 1) {
        std::cerr << "WARNING: could not resolve picked primpath id "
                  << prim_path << "\n";
        return {};
    }

    if (token_count == 0) {
        return "/";
    }

    std::string path;
    for (size_t i = 0; i < token_count; ++i) {
        ovx_string_t token_string = {};
        result = path_dictionary_get_strings_from_tokens(
            path_dictionary, &tokens[i], 1, &token_string);
        if (result.status != OVX_API_SUCCESS || !token_string.ptr) {
            std::cerr << "WARNING: could not resolve token for picked primpath id "
                      << prim_path << "\n";
            return {};
        }
        path += "/";
        path.append(token_string.ptr, token_string.length);
    }

    return path;
}

static void print_picked_prims(std::vector<std::string> const& prim_paths) {
    if (prim_paths.empty()) {
        std::cerr << "Picked prims: <none>\n";
        return;
    }

    std::cerr << "Picked prims:\n";
    for (std::string const& path : prim_paths) {
        std::cerr << "  " << path << "\n";
    }
}

static bool ovx_string_equals(ovx_string_t value, std::string_view expected) {
    return value.ptr && value.length == expected.size() &&
           std::string_view(value.ptr, value.length) == expected;
}

static auto find_render_var_tensor(ovrtx_render_var_output_t const& output,
                                   std::string_view tensor_name) -> DLTensor const* {
    for (size_t i = 0; i < output.num_tensors; ++i) {
        ovrtx_render_var_tensor_t const& tensor = output.tensors[i];
        if (tensor.name && ovx_string_equals(*tensor.name, tensor_name)) {
            return tensor.dl;
        }
    }
    return nullptr;
}

static auto find_render_var_param(ovrtx_render_var_output_t const& output,
                                  std::string_view param_name) -> DLTensor const* {
    for (size_t i = 0; i < output.num_params; ++i) {
        ovrtx_render_var_param_t const& param = output.params[i];
        if (ovx_string_equals(param.name, param_name)) {
            return &param.dl;
        }
    }
    return nullptr;
}

// Collect the color output of every frame the render product produced, in
// presentation order. A step normally produces a single frame; with DLSS Frame
// Generation on it produces the interpolated frames first and the real rendered
// frame last.
static bool collect_color_outputs(
    ovrtx_render_product_set_outputs_t const& outputs,
    std::string_view render_product_path,
    std::vector<ovrtx_render_var_output_handle_t>& color_outputs,
    OutputType* detected_type) {
    color_outputs.clear();

    for (size_t i = 0; i < outputs.output_count; ++i) {
        ovrtx_render_product_output_t const& product_output =
            outputs.outputs[i];
        if (!ovx_string_equals(product_output.render_product_path,
                               render_product_path)) {
            continue;
        }

        for (size_t f = 0; f < product_output.output_frame_count; ++f) {
            ovrtx_render_product_frame_output_t const& frame =
                product_output.output_frames[f];
            ovrtx_render_var_output_handle_t hdr_handle = 0;
            ovrtx_render_var_output_handle_t ldr_handle = 0;

            for (size_t v = 0; v < frame.render_var_count; ++v) {
                ovrtx_render_product_render_var_output_t const& var =
                    frame.output_render_vars[v];
                if (!var.render_var_path.ptr) {
                    continue;
                }

                if (ovx_string_equals(var.source_name, "HdrColor")) {
                    hdr_handle = var.output_handle;
                } else if (ovx_string_equals(var.source_name, "LdrColor")) {
                    ldr_handle = var.output_handle;
                }
            }

            // Prefer HdrColor, fall back to LdrColor
            if (hdr_handle != 0) {
                if (detected_type) {
                    *detected_type = OutputType::HdrColor;
                }
                color_outputs.push_back(hdr_handle);
            } else if (ldr_handle != 0) {
                if (detected_type) {
                    *detected_type = OutputType::LdrColor;
                }
                color_outputs.push_back(ldr_handle);
            }
        }
    }

    return !color_outputs.empty();
}

// [snippet:map-rendered-output-cuda-array]
// Map one ovrtx color output as a CUDA array and copy it into the CUDA-imported
// Vulkan image at `image_index`. The copy is stream-ordered: `copy_done_event`
// is recorded on completion and handed back to ovrtx as the unmap fence, so the
// renderer defers reuse of the output until the copy has landed.
//
// A step result can be fetched while its output frames are still being
// produced, so `map_timeout` of 0 turns the map into a non-blocking poll that
// reports CopyOutputResult::NotReady and lets an interactive loop keep
// presenting the previous frame instead of stalling.
//
// On success the mapping is handed back through `out_map_handle` instead of
// being released here. Unmapping waits for `copy_done_event` on the CPU, so
// unmapping immediately would just move the render wait from the map into the
// unmap. Call release_mapped_output() once cuEventQuery reports the copy done.
static CopyOutputResult copy_output_to_surface(
    ovrtx_renderer_t* renderer,
    ovrtx_render_var_output_handle_t color_output,
    int image_index,
    CudaImageFormat cuda_format,
    CUstream cuda_stream,
    CUevent copy_done_event,
    ovrtx_timeout_t map_timeout,
    ovrtx_render_var_output_map_handle_t* out_map_handle) {
    ovrtx_map_output_description_t map_desc = {};
    map_desc.device_type = OVRTX_MAP_DEVICE_TYPE_CUDA_ARRAY;
    map_desc.sync_stream = 0;

    ovrtx_render_var_output_t rendered_output = {};
    ovrtx_result_t result = ovrtx_map_render_var_output(renderer,
                                                        color_output,
                                                        &map_desc,
                                                        map_timeout,
                                                        &rendered_output);
    if (result.status == OVRTX_API_TIMEOUT) {
        return CopyOutputResult::NotReady;
    }
    if (check_and_print_error(result, "map_render_var_output")) {
        return CopyOutputResult::Failed;
    }

    if (rendered_output.num_tensors == 0) {
        std::cerr << "color render variable produced no tensors" << std::endl;
        ovrtx_unmap_render_var_output(
            renderer, rendered_output.map_handle, ovrtx_cuda_sync_t{});
        return CopyOutputResult::Failed;
    }

    DLTensor const& dl = *rendered_output.tensors[0].dl;
    CUarray cuda_array = reinterpret_cast<CUarray>(dl.data);
    CUevent wait_event =
        reinterpret_cast<CUevent>(rendered_output.cuda_sync.wait_event);

    // Ensure ovrtx has finished producing the mapped CUDA array before launching
    // the copy into external Vulkan memory.
    if (wait_event) {
        cuda_wait_event(wait_event, cuda_stream);
    }

    if (!cuda_copy_array_to_surface(image_index,
                                    cuda_array,
                                    static_cast<int>(dl.shape[1]),
                                    static_cast<int>(dl.shape[0]),
                                    cuda_format,
                                    cuda_stream)) {
        // No copy was queued, so the mapping can be released without a fence.
        ovrtx_unmap_render_var_output(
            renderer, rendered_output.map_handle, ovrtx_cuda_sync_t{});
        return CopyOutputResult::Failed;
    }
    cuEventRecord(copy_done_event, cuda_stream);

    *out_map_handle = rendered_output.map_handle;
    return CopyOutputResult::Copied;
}

// Release a mapping produced by copy_output_to_surface. `copy_done_event` is
// passed as the unmap fence so ovrtx does not reuse the output before the copy
// has landed; a zero-copy CUDA-array mapping owns no tensor buffers, so ovrtx
// waits for that event on the CPU inside this call. Call it only once
// cuEventQuery(copy_done_event) reports CUDA_SUCCESS to keep that wait free.
static bool release_mapped_output(
    ovrtx_renderer_t* renderer,
    ovrtx_render_var_output_map_handle_t map_handle,
    CUevent copy_done_event) {
    ovrtx_cuda_sync_t copy_done_sync = {};
    copy_done_sync.wait_event = reinterpret_cast<uintptr_t>(copy_done_event);
    ovrtx_result_t const result = ovrtx_unmap_render_var_output(
        renderer, map_handle, copy_done_sync);
    return !check_and_print_error(result, "unmap_render_var_output");
}
// [/snippet:map-rendered-output-cuda-array]

static void report_dlssg_frame_count(bool dlssg_enabled,
                                     int requested_interpolated_frames,
                                     size_t produced_frames,
                                     DlssgReport& report) {
    if (!dlssg_enabled || report.reported) {
        return;
    }

    ++report.steps_observed;
    bool const engaged = produced_frames > 1;
    if (!engaged && report.steps_observed < DLSSG_WARMUP_STEPS) {
        return;
    }
    report.reported = true;

    if (!engaged) {
        std::cerr << "DLSS Frame Generation did not engage after "
                  << report.steps_observed
                  << " steps. It requires an Ada or newer GPU driving the "
                     "display, the RealTimePathTracing render mode, "
                     "LdrColor/HdrColor as the only render outputs, and a "
                     "render resolution of at least 126 pixels per side."
                  << std::endl;
        return;
    }

    int const interpolated = static_cast<int>(produced_frames) - 1;
    std::cerr << "DLSS Frame Generation engaged: " << interpolated
              << " interpolated frame(s) per rendered frame";
    if (requested_interpolated_frames > 0 &&
        requested_interpolated_frames != interpolated) {
        std::cerr << " (" << requested_interpolated_frames
                  << " requested; the GPU caps the count)";
    }
    std::cerr << std::endl;
}
