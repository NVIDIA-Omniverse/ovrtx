// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
// All rights reserved. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

#include "camera/orbit_camera.hpp"
#include "cuda/cuda_kernel.hpp"
#include "glsl/spirv_loader.hpp"
#include "vk/vulkan_context.hpp"
#include <glm/gtc/type_ptr.hpp>
#include <ovrtx/ovrtx.h>
#include <ovrtx/ovrtx_config.h>
#include <ovstage/ovstage.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

namespace {
constexpr double simulation_dt = 1.0 / 30.0;
constexpr int view_width = 1280;
constexpr int view_height = 720;
constexpr int sensor_width = 480;
constexpr int sensor_height = 360;

template <size_t N> constexpr ovx_string_t text(const char (&value)[N]) {
    return {value, N - 1};
}

template <typename T> void check_rtx(const T& result) {
    if (result.status != OVRTX_API_SUCCESS) {
        const auto error = ovrtx_get_last_error();
        throw std::runtime_error(error.ptr
                                     ? std::string(error.ptr, error.length)
                                     : "ovrtx operation failed");
    }
}

void check_stage(ovstage_api_status_t status) {
    if (status != OVSTAGE_OK) {
        const auto error = ovstage_get_last_error();
        throw std::runtime_error(
            "ovstage status " + std::to_string(status) + ": " +
            (error.ptr ? std::string(error.ptr, error.length)
                       : "operation failed"));
    }
}

void wait_stage(ovstage_instance_t* stage, ovstage_enqueue_result_t operation) {
    check_stage(operation.status);
    ovstage_op_wait_result_t result{};
    const auto status = ovstage_wait_op(
        stage, operation.op_index, OVSTAGE_TIMEOUT_INFINITE, &result);
    const bool failed = result.error_op_id_count != 0;
    std::string error;
    if (failed) {
        const auto message =
            ovstage_get_last_op_error(stage, result.error_op_ids[0]);
        if (message.ptr) {
            error.assign(message.ptr, message.length);
        }
    }
    ovstage_release_op(stage, operation.op_index);
    check_stage(status);
    if (failed) {
        throw std::runtime_error("ovstage operation failed: " + error);
    }
}

void publish(ovstage_instance_t* stage, ovstage_ordinal_t ordinal) {
    ovstage_write_floor_desc_t floor{};
    floor.ordinal = ordinal;
    floor.scope = OVSTAGE_SCOPE_ALL;
    wait_stage(stage, ovstage_advance_write_floor(stage, &floor));
}

void check_cuda(CUresult status) {
    if (status != CUDA_SUCCESS) {
        const char* message = nullptr;
        cuGetErrorString(status, &message);
        throw std::runtime_error(message ? message : "CUDA operation failed");
    }
}

// Own resources across exceptions; the setup and simulation sequence remain in
// main().
struct Runtime {
    ovrtx_renderer_t* renderer = nullptr;
    ovstage_instance_t* stage = nullptr;
    std::array<ovstage_query_handle_t, 3> queries{};
    bool rtx_initialized = false;
    bool stage_initialized = false;
    Runtime() = default;
    Runtime(const Runtime&) = delete;
    Runtime& operator=(const Runtime&) = delete;
    ~Runtime() {
        for (auto query : queries) {
            if (stage && query != OVSTAGE_INVALID_QUERY_HANDLE) {
                const auto release = ovstage_release_query(stage, query);
                if (release.status == OVSTAGE_OK) {
                    ovstage_op_wait_result_t result{};
                    ovstage_wait_op(stage,
                                    release.op_index,
                                    OVSTAGE_TIMEOUT_INFINITE,
                                    &result);
                    ovstage_release_op(stage, release.op_index);
                }
            }
        }
        if (renderer) {
            ovrtx_detach_ovstage(renderer);
            ovrtx_destroy_renderer(renderer);
        }
        if (stage) {
            ovstage_destroy_instance(stage);
        }
        if (stage_initialized) {
            ovstage_shutdown();
        }
        if (rtx_initialized) {
            ovrtx_shutdown();
        }
    }
};

struct Results {
    ovrtx_renderer_t* renderer;
    ovrtx_step_result_handle_t handle = OVRTX_INVALID_HANDLE;
    explicit Results(ovrtx_renderer_t* owner) : renderer(owner) {}
    Results(const Results&) = delete;
    Results& operator=(const Results&) = delete;
    ~Results() {
        if (handle != OVRTX_INVALID_HANDLE) {
            ovrtx_destroy_results(renderer, handle);
        }
    }
};

struct CudaResources {
    CUstream stream = nullptr;
    CudaResources() = default;
    CudaResources(const CudaResources&) = delete;
    CudaResources& operator=(const CudaResources&) = delete;
    ~CudaResources() {
        if (stream) {
            cuStreamSynchronize(stream);
            cuStreamDestroy(stream);
        }
        cuda_cleanup();
    }
};

struct Mapping {
    ovrtx_renderer_t* renderer;
    CUstream stream;
    ovrtx_render_var_output_t output{};
    Mapping(ovrtx_renderer_t* owner, CUstream copy_stream)
        : renderer(owner), stream(copy_stream) {}
    Mapping(const Mapping&) = delete;
    Mapping& operator=(const Mapping&) = delete;
    ~Mapping() {
        if (output.map_handle != OVRTX_INVALID_HANDLE) {
            cuStreamSynchronize(stream);
            ovrtx_unmap_render_var_output(renderer, output.map_handle, {});
        }
    }
};

struct Window {
    GLFWwindow* handle = nullptr;
    bool initialized = false;
    Window() = default;
    Window(const Window&) = delete;
    Window& operator=(const Window&) = delete;
    ~Window() {
        if (handle) {
            glfwDestroyWindow(handle);
        }
        if (initialized) {
            glfwTerminate();
        }
    }
};

struct Controls {
    OrbitCamera camera{
        1500, glm::radians(48.0f), glm::radians(30.0f), {0, 40, 0},
           UpAxis::Y
    };
    bool dirty = true;
    bool paused = false;
    bool dragging = false;
    double x = 0;
    double y = 0;
};

struct Options {
    bool headless = false;
    int num_steps = 0;
    int observer_steps = 2;
    std::filesystem::path png;
    std::filesystem::path report;
    std::filesystem::path scene = SENSOR_OBSERVER_SCENE;
};

Options parse_options(int argc, char** argv) {
    Options options;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--help" || arg == "-h") {
            std::cout << "Usage: sensor-observer [--headless] [--num-steps N] "
                         "[--observer-steps N]\n"
                         "                       [--png PATH] [--report PATH] "
                         "[--usd PATH]\n"
                         "Right-drag: orbit; wheel: zoom; Space: pause/resume; "
                         "Escape: exit.\n"
                         "Headless mode inserts observer updates and a pause "
                         "at the midpoint.\n";
            std::exit(0);
        }
        if (arg == "--headless") {
            options.headless = true;
            continue;
        }
        if (++i == argc) {
            throw std::runtime_error("Missing value for " + arg);
        }
        if (arg == "--num-steps" || arg == "--observer-steps") {
            const std::string value = argv[i];
            size_t used = 0;
            const int count = std::stoi(value, &used);
            if (used != value.size() || count < 0) {
                throw std::runtime_error("Invalid count: " + value);
            }
            if (arg == "--num-steps") {
                options.num_steps = count;
            } else {
                options.observer_steps = count;
            }
        } else if (arg == "--png") {
            options.png = argv[i];
        } else if (arg == "--report") {
            options.report = argv[i];
        } else if (arg == "--usd") {
            options.scene = argv[i];
        } else {
            throw std::runtime_error("Unknown option: " + arg);
        }
    }
    if (options.headless && options.num_steps == 0) {
        options.num_steps = 30;
    }
    return options;
}

std::filesystem::path executable_dir() {
#ifdef _WIN32
    std::array<wchar_t, 32768> path{};
    const auto length = GetModuleFileNameW(
        nullptr, path.data(), static_cast<DWORD>(path.size()));
    if (!length || length == path.size()) {
        throw std::runtime_error("Cannot locate executable");
    }
    return std::filesystem::path(path.data()).parent_path();
#else
    return std::filesystem::canonical("/proc/self/exe").parent_path();
#endif
}

void write_transforms(ovstage_instance_t* stage,
                      ovstage_query_handle_t query,
                      ovstage_ordinal_t ordinal,
                      double* matrices,
                      int64_t count) {
    DLTensor tensor{};
    tensor.data = matrices;
    tensor.device = {kDLCPU, 0};
    tensor.ndim = 1;
    tensor.shape = &count;
    tensor.dtype = {kDLFloat, 64, 16};
    ovstage_write_data_t data{};
    data.tensors = &tensor;
    data.tensor_count = 1;
    data.semantic = OVSTAGE_SEMANTIC_MATRIX;
    wait_stage(stage,
               ovstage_write_attribute(stage,
                                       query,
                                       {0, text("omni:xform")},
                                       ordinal,
                                       data,
                                       OVSTAGE_PRIM_MODE_UPSERT));
}

// The existing interop sample owns these graphics helpers. Only composition
// differs here.
void draw_views(VulkanContext& vk,
                uint32_t swapchain_index,
                ShaderHandle vertex,
                ShaderHandle fragment,
                const std::array<SampledImageHandle, 2>& images,
                bool have_sensor) {
    auto cmd = vk.command_buffer();
    cmd.begin();
    for (int i = 0; i < 2; ++i) {
        if (i == 1 && !have_sensor) {
            continue;
        }
        cmd.image_memory_barrier(vk.sampled_image(images[i]).image,
                                 VK_IMAGE_ASPECT_COLOR_BIT,
                                 VK_IMAGE_LAYOUT_GENERAL,
                                 VK_PIPELINE_STAGE_2_NONE,
                                 VK_ACCESS_2_NONE,
                                 VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                                 VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT,
                                 VK_ACCESS_2_SHADER_SAMPLED_READ_BIT,
                                 VK_QUEUE_FAMILY_EXTERNAL,
                                 vk.queue_family());
    }
    cmd.image_memory_barrier(vk.swapchain_image(swapchain_index),
                             VK_IMAGE_ASPECT_COLOR_BIT,
                             VK_IMAGE_LAYOUT_UNDEFINED,
                             VK_PIPELINE_STAGE_2_NONE,
                             VK_ACCESS_2_NONE,
                             VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
                             VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                             VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT);
    VkRenderingAttachmentInfo attachment{};
    attachment.sType = VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO;
    attachment.imageView = vk.swapchain_image_view(swapchain_index);
    attachment.imageLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    attachment.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
    attachment.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
    VkRenderingInfo info{};
    info.sType = VK_STRUCTURE_TYPE_RENDERING_INFO;
    info.renderArea.extent = vk.swapchain_extent();
    info.layerCount = 1;
    info.colorAttachmentCount = 1;
    info.pColorAttachments = &attachment;
    cmd.begin_rendering(info);
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
    cmd.set_sample_mask(VK_SAMPLE_COUNT_1_BIT, 0xffffffff);
    cmd.set_alpha_to_coverage_enable(false);
    cmd.set_color_blend_enable(0, false);
    cmd.set_color_write_mask(
        0,
        VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
            VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT);
    cmd.set_vertex_input_empty();
    vk.bind_shaders(vertex, fragment);
    const auto descriptors = vk.descriptor_set();
    cmd.bind_descriptor_sets(VK_PIPELINE_BIND_POINT_GRAPHICS,
                             vk.pipeline_layout(),
                             0,
                             1,
                             &descriptors);
    const auto extent = vk.swapchain_extent();
    for (int i = 0; i < 2; ++i) {
        if (i == 1 && !have_sensor) {
            continue;
        }
        // Fit each fixed-resolution image without changing its aspect ratio.
        // Center the observer; anchor the sensor inset at the window's lower left.
        const float image_width = i == 0 ? view_width : sensor_width;
        const float image_height = i == 0 ? view_height : sensor_height;
        const float available_width =
            i == 0 ? static_cast<float>(extent.width) : extent.width / 3.0f;
        const float available_height =
            i == 0 ? static_cast<float>(extent.height) : extent.height / 2.0f;
        const float scale = std::min(available_width / image_width,
                                     available_height / image_height);
        const float width = image_width * scale;
        const float height = image_height * scale;
        const float x = i == 0 ? (extent.width - width) / 2.0f : 0.0f;
        const float y =
            i == 0 ? (extent.height - height) / 2.0f : extent.height - height;
        cmd.set_viewport(x, y, width, height);
        cmd.set_scissor(0, 0, extent.width, extent.height);
        const auto index = vk.sampled_image(images[i]).descriptor_index;
        cmd.push_constants(vk.pipeline_layout(),
                           VK_SHADER_STAGE_FRAGMENT_BIT,
                           0,
                           sizeof(index),
                           &index);
        cmd.draw(3);
    }
    cmd.end_rendering();
    for (int i = 0; i < 2; ++i) {
        if (i == 1 && !have_sensor) {
            continue;
        }
        cmd.image_memory_barrier(vk.sampled_image(images[i]).image,
                                 VK_IMAGE_ASPECT_COLOR_BIT,
                                 VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                                 VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT,
                                 VK_ACCESS_2_SHADER_SAMPLED_READ_BIT,
                                 VK_IMAGE_LAYOUT_GENERAL,
                                 VK_PIPELINE_STAGE_2_NONE,
                                 VK_ACCESS_2_NONE,
                                 vk.queue_family(),
                                 VK_QUEUE_FAMILY_EXTERNAL);
    }
    cmd.image_memory_barrier(vk.swapchain_image(swapchain_index),
                             VK_IMAGE_ASPECT_COLOR_BIT,
                             VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
                             VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT,
                             VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT,
                             VK_IMAGE_LAYOUT_PRESENT_SRC_KHR,
                             VK_PIPELINE_STAGE_2_NONE,
                             VK_ACCESS_2_NONE);
    cmd.end();
}
} // namespace

int main(int argc, char** argv) {
    cuda_apply_scheduling_workaround();
    try {
        const auto options = parse_options(argc, argv);
        Runtime runtime;
        ovrtx_config_entry_t entries[] = {
            ovrtx_config_entry_binary_package_root_path(
                text(OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx")),
            ovrtx_config_entry_active_cuda_gpus(text("0")),
        };
        ovrtx_config_t config{entries, 2};
        check_rtx(ovrtx_register_schema_paths(&config));
        check_rtx(ovrtx_initialize(&config));
        runtime.rtx_initialized = true;
        ovstage_config_entry_t stage_entry =
            ovstage_config_entry_binary_package_root_path(
                text(OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovstage"));
        ovstage_config_t stage_config{&stage_entry, 1};
        check_stage(ovstage_initialize(&stage_config));
        runtime.stage_initialized = true;
        check_rtx(ovrtx_create_renderer(&config, &runtime.renderer));
        ovstage_instance_desc_t description{};
        description.name = "sensor-observer";
        check_stage(ovstage_create_instance(&description, &runtime.stage));
        auto* renderer = runtime.renderer;
        auto* stage = runtime.stage;
        check_rtx(ovrtx_attach_ovstage(renderer, stage));
        ovstage_ordinal_t ordinal = 1;
        const auto scene = std::filesystem::absolute(options.scene).string();
        const auto open = ovstage_population_open_usd_from_file(
            stage,
            {scene.data(), scene.size()},
            ordinal,
            0.0,
            OVSTAGE_POPULATION_DOMAIN_RENDERING);
        check_stage(open.status);
        ovstage_population_op_wait_result_t loaded{};
        check_stage(ovstage_population_wait_op(
            stage, open.op_index, OVSTAGE_TIMEOUT_INFINITE, &loaded));
        if (loaded.error_op_id_count) {
            throw std::runtime_error("Could not populate " + scene);
        }
        publish(stage, ordinal);
        auto* dictionary = ovstage_get_path_dictionary(stage);
        const ovx_string_t paths[] = {text("/World/Sensor"),
                                      text("/World/Observer"),
                                      text("/World/Cube/Cube"),
                                      text("/World/Sphere/Sphere"),
                                      text("/World/Cone/Cone")};
        for (int i = 0; i < 3; ++i) {
            ovx_primpath_list_t path_list = OVX_INVALID_PRIMPATH_LIST;
            if (path_dictionary_create_path_list_from_strings(
                    dictionary, paths + i, i == 2 ? 3 : 1, &path_list)
                    .status != OVX_API_SUCCESS) {
                throw std::runtime_error("Cannot create prim path list");
            }
            const auto status = ovstage_query_from_path_list(
                stage, path_list, &runtime.queries[i]);
            path_dictionary_release_path_list_reference(dictionary, path_list);
            check_stage(status);
        }
        const auto sensor_query = runtime.queries[0];
        const auto observer_query = runtime.queries[1];
        const auto object_query = runtime.queries[2];

        // [snippet:doc-observer-output-policy-c]
        /* Test the camera's authored USDA policy without a runtime override.
        // Write the camera delivery policy to the runtime stage before
        // rendering.
        ++ordinal;
        bool partial_outputs = false;
        int64_t shape = 1;
        DLTensor tensor{};
        tensor.data = &partial_outputs;
        tensor.device = {kDLCPU, 0};
        tensor.ndim = 1;
        tensor.shape = &shape;
        tensor.dtype = {kDLBool, 8, 1};
        ovstage_write_data_t data{};
        data.tensors = &tensor;
        data.tensor_count = 1;
        wait_stage(stage,
                   ovstage_write_attribute(
                       stage,
                       sensor_query,
                       {0, text("omni:sensor:Core:partialOutputs")},
                       ordinal,
                       data,
                       OVSTAGE_PRIM_MODE_UPSERT));
        publish(stage, ordinal);
        */
        // [/snippet:doc-observer-output-policy-c]

        CUuuid uuid{};
        if (!cuda_init(0, &uuid)) {
            throw std::runtime_error("Cannot use ovrtx CUDA device 0");
        }
        Window window;
        Controls controls;
        if (!options.headless) {
            if (!glfwInit()) {
                throw std::runtime_error("GLFW initialization failed; use "
                                         "--headless without a display");
            }
            window.initialized = true;
            glfwWindowHint(GLFW_CLIENT_API, GLFW_NO_API);
            window.handle =
                glfwCreateWindow(view_width,
                                 view_height,
                                 "Sensor 30 Hz | Observer | Space: pause",
                                 nullptr,
                                 nullptr);
            if (!window.handle) {
                throw std::runtime_error("Cannot create window");
            }
            glfwSetWindowUserPointer(window.handle, &controls);
            glfwSetFramebufferSizeCallback(
                window.handle, [](GLFWwindow* win, int, int) {
                    static_cast<Controls*>(glfwGetWindowUserPointer(win))
                        ->dirty = true;
                });
            glfwSetMouseButtonCallback(
                window.handle,
                [](GLFWwindow* win, int button, int action, int) {
                    auto& c =
                        *static_cast<Controls*>(glfwGetWindowUserPointer(win));
                    if (button == GLFW_MOUSE_BUTTON_RIGHT) {
                        c.dragging = action == GLFW_PRESS;
                        glfwGetCursorPos(win, &c.x, &c.y);
                    }
                });
            glfwSetCursorPosCallback(
                window.handle, [](GLFWwindow* win, double x, double y) {
                    auto& c =
                        *static_cast<Controls*>(glfwGetWindowUserPointer(win));
                    if (c.dragging) {
                        // Reverse horizontal input for the Y-up orbit so the
                        // scene follows the drag direction.
                        c.camera.update(static_cast<float>(c.x - x),
                                        static_cast<float>(y - c.y));
                        c.dirty = true;
                    }
                    c.x = x;
                    c.y = y;
                });
            glfwSetScrollCallback(
                window.handle, [](GLFWwindow* win, double, double y) {
                    auto& c =
                        *static_cast<Controls*>(glfwGetWindowUserPointer(win));
                    c.camera.set_distance(
                        std::clamp(c.camera.distance() *
                                       std::exp(static_cast<float>(-y) * 0.1f),
                                   100.0f,
                                   6000.0f));
                    c.dirty = true;
                });
            glfwSetKeyCallback(
                window.handle,
                [](GLFWwindow* win, int key, int, int action, int) {
                    if (action != GLFW_PRESS) {
                        return;
                    }
                    auto& c =
                        *static_cast<Controls*>(glfwGetWindowUserPointer(win));
                    if (key == GLFW_KEY_SPACE) {
                        c.paused = !c.paused;
                        c.dirty = true;
                    }
                    if (key == GLFW_KEY_ESCAPE) {
                        glfwSetWindowShouldClose(win, GLFW_TRUE);
                    }
                });
        }
        VulkanContextConfig vk_config{};
        vk_config.window = window.handle;
        vk_config.initial_sampled_image_capacity = 2;
        VulkanContext vk(vk_config, uuid);
        CudaResources cuda;
        check_cuda(cuStreamCreate(&cuda.stream, CU_STREAM_NON_BLOCKING));
        std::array<SampledImageHandle, 2> images{};
        for (int i = 0; i < 2; ++i) {
            const int width = i == 0 ? view_width : sensor_width;
            const int height = i == 0 ? view_height : sensor_height;
            images[i] = vk.create_sampled_image(
                width, height, VK_FORMAT_R8G8B8A8_SRGB, VK_FILTER_LINEAR, true);
            const auto& image = vk.sampled_image(images[i]);
            vk.immediate_submit([&](CommandBuffer cmd) {
                cmd.image_memory_barrier(image.image,
                                         VK_IMAGE_ASPECT_COLOR_BIT,
                                         VK_IMAGE_LAYOUT_UNDEFINED,
                                         VK_PIPELINE_STAGE_2_TOP_OF_PIPE_BIT,
                                         VK_ACCESS_2_NONE,
                                         VK_IMAGE_LAYOUT_GENERAL,
                                         VK_PIPELINE_STAGE_2_NONE,
                                         VK_ACCESS_2_NONE,
                                         vk.queue_family(),
                                         VK_QUEUE_FAMILY_EXTERNAL);
            });
            if (!cuda_import_vulkan_image(i,
                                          vk.export_memory_handle(images[i]),
                                          image.size,
                                          width,
                                          height,
                                          CudaImageFormat::UInt8_4)) {
                throw std::runtime_error("CUDA image import failed");
            }
        }
        if (!cuda_import_timeline_semaphore(
                vk.export_timeline_semaphore_handle())) {
            throw std::runtime_error("CUDA timeline import failed");
        }
        ShaderHandle vertex{}, fragment{};
        if (window.handle) {
            const auto dir = executable_dir() / "shaders";
            const auto shaders = vk.create_linked_vertex_and_fragment_shaders(
                load_spirv((dir / "fullscreen.vert.spv").string()),
                load_spirv((dir / "fullscreen.frag.spv").string()));
            vertex = shaders.first;
            fragment = shaders.second;
        }
        std::ofstream report;
        if (!options.report.empty()) {
            if (options.report.has_parent_path()) {
                std::filesystem::create_directories(
                    options.report.parent_path());
            }
            report.open(options.report);
            if (!report) {
                throw std::runtime_error("Cannot open timing report");
            }
            report << "kind,ordinal,simulation_time,product,capture_start,"
                      "capture_end,wall_time\n"
                   << std::setprecision(12);
        }
        int step_index = 0;
        int pending_observer_updates = 0;
        int sensor_frames = 0;
        int observer_frames = 0;
        uint64_t timeline = 0;
        bool have_sensor = false;
        using Clock = std::chrono::steady_clock;
        const auto tick_period = std::chrono::duration_cast<Clock::duration>(
            std::chrono::duration<double>(simulation_dt));
        const auto run_started = Clock::now();
        auto next_tick = run_started;
        auto fps_started = run_started;
        int fps_frames = 0;
        double observer_fps = 0;
        std::cout << "30 Hz simulation, 30 Hz sensor; observer refreshes use "
                     "dt=0.\n";
        while ((!window.handle || !glfwWindowShouldClose(window.handle)) &&
               (options.num_steps == 0 || step_index < options.num_steps ||
                pending_observer_updates)) {
            if (window.handle) {
                glfwPollEvents();
            }
            const auto now = Clock::now();
            // Due simulation ticks also consume camera input, so dragging
            // cannot starve simulation. Start with a positive step: t=0 has a
            // special sensor trigger.
            const bool simulate =
                step_index == 0 ||
                (options.headless
                     ? pending_observer_updates == 0
                     : !controls.paused && now >= next_tick);
            if (controls.paused) {
                next_tick = now + tick_period;
            }
            // Render the observer every display frame, including without input
            // and while paused. Only due simulation ticks advance sensor time.
            // A single image per view keeps the example small: finish
            // presentation before overwriting it.
            if (window.handle) {
                vk.wait_for_fence();
            }
            ++ordinal;
            if (simulate) {
                ++step_index;
                std::array<double, 48> matrices{};
                for (int i = 0; i < 3; ++i) {
                    auto* m = matrices.data() + 16 * i;
                    m[0] = m[5] = m[10] = m[15] = 1;
                    // Move each mesh relative to its fixed placement prim.
                    const double placement_x = -300.0 + i * 300.0;
                    m[12] =
                        std::fmod(placement_x + 450.0 +
                                      step_index * simulation_dt * 180.0,
                                  900.0) -
                        450.0 - placement_x;
                    m[13] = 50;
                }
                write_transforms(
                    stage, object_query, ordinal, matrices.data(), 3);
                // Advance the deadline, not "now", to avoid accumulating
                // display-frame rounding in the 30 Hz simulation clock.
                next_tick += tick_period;
                if (options.headless) {
                    pending_observer_updates =
                        options.observer_steps +
                        (options.observer_steps &&
                                 step_index == options.num_steps / 2
                             ? 12
                             : 0);
                }
            } else if (options.headless) {
                --pending_observer_updates;
                controls.camera.update(1.5f, 0.0f);
                controls.dirty = true;
            }
            if (controls.dirty) {
                const auto matrix = controls.camera.transform_matrix();
                std::array<double, 16> values{};
                std::copy_n(
                    glm::value_ptr(matrix), values.size(), values.begin());
                write_transforms(
                    stage, observer_query, ordinal, values.data(), 1);
                controls.dirty = false;
            }

            // [snippet:doc-observer-step-c]
            // Publish scene/camera changes. An ordinal does not itself advance
            // simulation time.
            publish(stage, ordinal);
            ovx_string_t product_paths[] = {text("/Render/Sensor"),
                                            text("/Render/Observer")};
            ovrtx_render_product_set_t products{};
            products.render_products = product_paths;
            products.num_render_products = 2;
            // Keep both products selected even for a view-only refresh,
            // preserving sensor history.
            const double delta_time = simulate ? simulation_dt : 0.0;
            Results results(renderer);
            check_rtx(ovrtx_step_with_stage(
                renderer, products, delta_time, ordinal, &results.handle));
            ovrtx_render_product_set_outputs_t outputs{};
            check_rtx(ovrtx_fetch_results(
                renderer, results.handle, ovrtx_timeout_infinite, &outputs));
            // [/snippet:doc-observer-step-c]

            const double wall_time =
                std::chrono::duration<double>(Clock::now() - run_started).count();
            if (std::abs(outputs.simulation_end_time -
                         step_index * simulation_dt) > 1e-6) {
                throw std::runtime_error(
                    "Observer refresh advanced simulation time");
            }
            int current_observer_frames = 0;
            for (size_t p = 0; p < outputs.output_count; ++p) {
                const auto& product = outputs.outputs[p];
                const std::string_view path(product.render_product_path.ptr,
                                            product.render_product_path.length);
                const bool is_sensor = path == "/Render/Sensor";
                for (size_t f = 0; f < product.output_frame_count; ++f) {
                    const auto& frame = product.output_frames[f];
                    if (is_sensor) {
                        if (!simulate) {
                            throw std::runtime_error(
                                "Sensor produced an extra frame during dt=0 "
                                "refresh");
                        }
                        ++sensor_frames;
                        if (std::abs(frame.frame_start_time -
                                     sensor_frames / 30.0) > 1e-6 ||
                            std::abs(frame.frame_end_time -
                                     sensor_frames / 30.0) > 1e-6) {
                            throw std::runtime_error(
                                "Sensor capture cadence changed");
                        }
                    } else {
                        ++observer_frames;
                        ++current_observer_frames;
                        if (std::abs(frame.frame_start_time -
                                     outputs.simulation_end_time) > 1e-6 ||
                            std::abs(frame.frame_end_time -
                                     outputs.simulation_end_time) > 1e-6) {
                            throw std::runtime_error(
                                "Observer capture time changed");
                        }
                    }
                    if (report.is_open()) {
                        report << (simulate ? "simulation" : "observer") << ','
                               << ordinal << ',' << outputs.simulation_end_time
                               << ',' << path << ',' << frame.frame_start_time
                               << ',' << frame.frame_end_time << ',' << wall_time
                               << '\n';
                    }

                    // [snippet:doc-observer-copy-outputs-c]
                    // Only replace the sensor texture when a newly completed
                    // image is returned.
                    for (size_t v = 0; v < frame.render_var_count; ++v) {
                        Mapping mapping(renderer, cuda.stream);
                        ovrtx_map_output_description_t map_desc{};
                        map_desc.device_type = OVRTX_MAP_DEVICE_TYPE_CUDA_ARRAY;
                        check_rtx(ovrtx_map_render_var_output(
                            renderer,
                            frame.output_render_vars[v].output_handle,
                            &map_desc,
                            ovrtx_timeout_infinite,
                            &mapping.output));
                        const auto& output = mapping.output;
                        if (output.cuda_sync.wait_event) {
                            check_cuda(cuStreamWaitEvent(
                                cuda.stream,
                                reinterpret_cast<CUevent>(
                                    output.cuda_sync.wait_event),
                                0));
                        }
                        const int width = is_sensor ? sensor_width : view_width;
                        const int height =
                            is_sensor ? sensor_height : view_height;
                        if (!output.num_tensors ||
                            output.tensors[0].dl->device.device_id != 0 ||
                            output.tensors[0].dl->shape[0] != height ||
                            output.tensors[0].dl->shape[1] != width) {
                            throw std::runtime_error(
                                "Unexpected image dimensions");
                        }
                        if (!cuda_copy_array_to_surface(
                                is_sensor ? 1 : 0,
                                reinterpret_cast<CUarray>(
                                    output.tensors[0].dl->data),
                                width,
                                height,
                                CudaImageFormat::UInt8_4,
                                cuda.stream)) {
                            throw std::runtime_error("CUDA image copy failed");
                        }
                        check_cuda(cuStreamSynchronize(cuda.stream));
                        // Mapping releases the output after the copy; Results
                        // releases step metadata.
                    }
                    if (is_sensor) {
                        have_sensor = true;
                    }
                    // [/snippet:doc-observer-copy-outputs-c]
                }
            }
            if (current_observer_frames != 1) {
                throw std::runtime_error(
                    "Expected one observer image per update");
            }
            if (!cuda_signal_timeline(++timeline, cuda.stream)) {
                throw std::runtime_error("CUDA timeline signal failed");
            }
            if (simulate && step_index == 1) {
                // Initial shader compilation is not elapsed simulation time.
                next_tick = Clock::now() + tick_period;
                fps_started = Clock::now();
            }
            if (window.handle) {
                // Wayland can keep presenting a resized surface without an
                // out-of-date result, stretching the old swapchain image.
                const auto framebuffer = vk.framebuffer_size();
                const auto extent = vk.swapchain_extent();
                if (framebuffer.x > 0 && framebuffer.y > 0 &&
                    (static_cast<uint32_t>(framebuffer.x) != extent.width ||
                     static_cast<uint32_t>(framebuffer.y) != extent.height)) {
                    vk.recreate_swapchain();
                }
                uint32_t index = 0;
                const auto acquired = vk.acquire_next_image(index);
                if (acquired == AcquireResult::OutOfDate ||
                    acquired == AcquireResult::Minimized) {
                    controls.dirty = true;
                    if (acquired == AcquireResult::Minimized) {
                        glfwWaitEventsTimeout(0.1);
                    }
                    if (acquired == AcquireResult::OutOfDate) {
                        vk.recreate_swapchain();
                    }
                    continue;
                }
                vk.reset_fence();
                draw_views(vk, index, vertex, fragment, images, have_sensor);
                const auto presented = vk.submit_and_present(index, timeline);
                if (presented != PresentResult::Success ||
                    acquired == AcquireResult::Suboptimal) {
                    vk.recreate_swapchain();
                    controls.dirty = true;
                }
                if (presented != PresentResult::OutOfDate) {
                    ++fps_frames;
                }
                const auto frame_finished = Clock::now();
                const double fps_elapsed =
                    std::chrono::duration<double>(frame_finished - fps_started)
                        .count();
                if (fps_elapsed >= 1.0) {
                    observer_fps = fps_frames / fps_elapsed;
                    fps_frames = 0;
                    fps_started = frame_finished;
                }
                const auto title =
                    std::string(controls.paused ? "PAUSED" : "RUNNING") +
                    " | sim " + std::to_string(step_index * simulation_dt) +
                    " s | sensor " + std::to_string(sensor_frames) +
                    " frames | observer " +
                    std::to_string(std::lround(observer_fps)) +
                    " FPS | Space: pause/resume | Right-drag: orbit";
                glfwSetWindowTitle(window.handle, title.c_str());
            }
        }
        check_cuda(cuStreamSynchronize(cuda.stream));
        vkDeviceWaitIdle(vk.device());
        if (sensor_frames != step_index) {
            throw std::runtime_error("Unexpected sensor output count");
        }
        if (!options.png.empty()) {
            if (!have_sensor) {
                throw std::runtime_error("No sensor image to save");
            }
            auto pixels = cuda_read_surface_rgba8(
                0, view_width, view_height, CudaImageFormat::UInt8_4);
            const auto sensor = cuda_read_surface_rgba8(
                1, sensor_width, sensor_height, CudaImageFormat::UInt8_4);
            if (pixels.size() != view_width * view_height * 4 ||
                sensor.size() != sensor_width * sensor_height * 4) {
                throw std::runtime_error("CUDA image readback failed");
            }
            constexpr int width = view_width / 3;
            constexpr int height = width * 3 / 4;
            for (int y = 0; y < height; ++y) {
                for (int x = 0; x < width; ++x) {
                    std::copy_n(
                        sensor.data() +
                            ((y * sensor_height / height) * sensor_width +
                             x * sensor_width / width) *
                                4,
                        4,
                        pixels.data() +
                            ((view_height - height + y) * view_width + x) * 4);
                }
            }
            if (options.png.has_parent_path()) {
                std::filesystem::create_directories(options.png.parent_path());
            }
            if (!stbi_write_png(options.png.string().c_str(),
                                view_width,
                                view_height,
                                4,
                                pixels.data(),
                                view_width * 4)) {
                throw std::runtime_error("Could not save PNG");
            }
        }
        if (report.is_open()) {
            report.flush();
            if (!report) {
                throw std::runtime_error("Cannot write timing report");
            }
        }
        std::cout << "simulation_time=" << step_index * simulation_dt
                  << " sensor_frames=" << sensor_frames
                  << " observer_frames=" << observer_frames << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "sensor-observer: " << error.what() << '\n';
        return 1;
    }
}
