// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "ovrtx_engine.hpp"

#include <ovrtx/ovrtx_config.h>
#include <ovrtx/ovrtx_types.h>
#include <ovrtx/ovrtx.h>
#include <ovrtx/ovrtx_attributes.h>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <thread>

// ---------------------------------------------------------------------------
// Helpers (same pattern as the minimal example)
// ---------------------------------------------------------------------------

template <typename ResultT>
static bool check_error(ResultT const &result, std::string_view operation)
{
    if (result.status == OVRTX_API_ERROR) {
        ovx_string_t error = ovrtx_get_last_error();
        if (error.ptr && error.length > 0) {
            std::cerr << "ovrtx " << operation << " failed: "
                      << std::string_view(error.ptr, error.length) << "\n";
        } else {
            std::cerr << "ovrtx " << operation << " failed\n";
        }
        return true;
    }
    return false;
}

static bool check_op_errors(ovrtx_op_wait_result_t const &wait_result,
                            std::string_view operation)
{
    if (wait_result.num_error_ops == 0) {
        return false;
    }

    std::cerr << "ovrtx " << operation << " reported "
              << wait_result.num_error_ops << " async error(s):\n";
    for (size_t i = 0; i < wait_result.num_error_ops; ++i) {
        ovrtx_op_id_t op_id = wait_result.error_op_ids[i];
        ovx_string_t error = ovrtx_get_last_op_error(op_id);
        std::cerr << "  op " << op_id << ": ";
        if (error.ptr && error.length > 0) {
            std::cerr << std::string_view(error.ptr, error.length);
        } else {
            std::cerr << "(no error message)";
        }
        std::cerr << "\n";
    }
    return true;
}

static bool wait_for_op(ovrtx_renderer_t *renderer, ovrtx_op_id_t op_id,
                        ovrtx_timeout_t timeout, std::string_view operation)
{
    ovrtx_op_wait_result_t wait_result{};
    ovrtx_result_t result =
        ovrtx_wait_op(renderer, op_id, timeout, &wait_result);
    if (check_error(result, operation)) {
        return false;
    }
    if (check_op_errors(wait_result, operation)) {
        return false;
    }
    return true;
}

static bool poll_until_complete(ovrtx_renderer_t *renderer, ovrtx_op_id_t op_id,
                                std::string_view operation)
{
    ovrtx_op_wait_result_t wait_result{};
    while (true) {
        ovrtx_result_t result =
            ovrtx_wait_op(renderer, op_id, ovrtx_timeout_t{0}, &wait_result);
        if (result.status == OVRTX_API_TIMEOUT) {
            if (check_op_errors(wait_result, operation)) {
                return false;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            continue;
        }
        if (check_error(result, operation)) {
            return false;
        }
        if (check_op_errors(wait_result, operation)) {
            return false;
        }
        return true;
    }
}

static bool wait_for_enqueued(ovrtx_renderer_t *renderer,
                              ovrtx_enqueue_result_t const &enqueue,
                              std::string_view operation)
{
    if (check_error(enqueue, operation)) {
        return false;
    }

    std::string wait_operation = "wait_op (";
    wait_operation += operation;
    wait_operation += ")";
    return wait_for_op(renderer, enqueue.op_index, ovrtx_timeout_infinite,
                       wait_operation);
}

static bool reset_render_history(ovrtx_renderer_t *renderer)
{
    ovrtx_enqueue_result_t enqueue = ovrtx_reset(renderer, 0.0);
    return wait_for_enqueued(renderer, enqueue, "reset");
}

static ovrtx_render_var_output_handle_t
find_output(ovrtx_render_product_set_outputs_t const &outputs,
            char const *output_to_find)
{
    size_t output_to_find_len = strlen(output_to_find);
    for (size_t i = 0; i < outputs.output_count; ++i) {
        ovrtx_render_product_output_t const &product = outputs.outputs[i];
        for (size_t f = 0; f < product.output_frame_count; ++f) {
            ovrtx_render_product_frame_output_t const &frame =
                product.output_frames[f];
            for (size_t v = 0; v < frame.render_var_count; ++v) {
                ovrtx_render_product_render_var_output_t const &var =
                    frame.output_render_vars[v];
                if (var.render_var_name.ptr &&
                    var.render_var_name.length == output_to_find_len &&
                    strncmp(var.render_var_name.ptr, output_to_find,
                            var.render_var_name.length) == 0) {
                    return var.output_handle;
                }
            }
        }
    }
    return OVRTX_INVALID_HANDLE;
}

// ---------------------------------------------------------------------------
// OvrtxEngine
// ---------------------------------------------------------------------------

OvrtxEngine::OvrtxEngine(QObject *parent)
    : QObject(parent)
{
    render_timer_ = new QTimer(this);
    render_timer_->setInterval(0);
    connect(render_timer_, &QTimer::timeout, this, &OvrtxEngine::onRenderTick);
}

OvrtxEngine::~OvrtxEngine()
{
    shutdown();
}

bool OvrtxEngine::initialize(const std::string &usda_path)
{
    // Create renderer.
    //
    // The STATIC ovrtx loader resolves the ${executable_dir} token to the running
    // executable's directory; ovrtx_setup_runtime() links the package bin beside
    // the exe as "ovrtx/", which we hand the loader as the binary package root.
    ovx_string_t ovrtx_package_root = {
        OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx",
        sizeof(OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx") - 1};
    ovrtx_config_entry_t config_entries[] = {
        ovrtx_config_entry_binary_package_root_path(ovrtx_package_root),
    };
    ovrtx_config_t config{config_entries, 1};
    std::cerr << "Creating renderer...\n";
    ovrtx_result_t result = ovrtx_create_renderer(&config, &renderer_);
    if (check_error(result, "create_renderer")) {
        return false;
    }
    std::cerr << "Renderer created.\n";

    std::cerr << "Loading USD: " << usda_path << "\n";
    ovrtx_enqueue_result_t enqueue =
        ovrtx_open_usd_from_file(renderer_, {usda_path.c_str(), usda_path.size()});
    if (check_error(enqueue, "open_usd_from_file")) {
        shutdown();
        return false;
    }

    if (!poll_until_complete(renderer_, enqueue.op_index,
                             "wait_op (open_usd_from_file)")) {
        shutdown();
        return false;
    }

    std::cerr << "USD loaded.\n";
    return true;
}

void OvrtxEngine::shutdown()
{
    render_timer_->stop();
    if (renderer_) {
        ovrtx_destroy_renderer(renderer_);
        renderer_ = nullptr;
    }
}

// ---------------------------------------------------------------------------
// Async render loop
// ---------------------------------------------------------------------------

void OvrtxEngine::startRender(int iterations)
{
    // Cancel any in-progress render
    render_timer_->stop();

    if (!renderer_ || iterations <= 0) {
        return;
    }

    // Immediate first step for fast feedback
    uint64_t handle = stepOnce();
    if (handle != 0) {
        mapAndEmit(handle);
    }

    // Schedule remaining iterations via timer
    render_iterations_remaining_ = iterations - 1;
    if (render_iterations_remaining_ > 0) {
        render_timer_->start();
    }
}

void OvrtxEngine::onRenderTick()
{
    if (!renderer_ || render_iterations_remaining_ <= 0) {
        render_timer_->stop();
        return;
    }

    int chunk = std::min(kChunkSize, render_iterations_remaining_);
    uint64_t last_handle = 0;

    for (int i = 0; i < chunk; ++i) {
        uint64_t handle = stepOnce();
        if (handle == 0) {
            render_timer_->stop();
            return;
        }
        if (i < chunk - 1) {
            destroyStep(handle);
        } else {
            last_handle = handle;
        }
    }

    render_iterations_remaining_ -= chunk;

    if (last_handle != 0) {
        mapAndEmit(last_handle);
    }

    if (render_iterations_remaining_ <= 0) {
        render_timer_->stop();
    }
}

uint64_t OvrtxEngine::stepOnce()
{
    ovrtx_render_product_set_t render_products{};
    ovx_string_t rp_str = {render_product_path_.c_str(),
                           static_cast<uint64_t>(render_product_path_.size())};
    render_products.render_products = &rp_str;
    render_products.num_render_products = 1;

    ovrtx_step_result_handle_t step_handle = 0;
    ovrtx_enqueue_result_t enqueue =
        ovrtx_step(renderer_, render_products, 1.0 / 60.0, &step_handle);
    if (check_error(enqueue, "step")) {
        return 0;
    }

    if (!wait_for_op(renderer_, enqueue.op_index, ovrtx_timeout_infinite,
                     "wait_op (step)")) {
        ovrtx_destroy_results(renderer_, step_handle);
        return 0;
    }

    return step_handle;
}

void OvrtxEngine::mapAndEmit(uint64_t step_handle)
{
    ovrtx_render_product_set_outputs_t outputs{};
    ovrtx_result_t result = ovrtx_fetch_results(
        renderer_, step_handle, ovrtx_timeout_infinite, &outputs);
    if (check_error(result, "fetch_results")) {
        ovrtx_destroy_results(renderer_, step_handle);
        return;
    }

    ovrtx_render_var_output_handle_t color_handle =
        find_output(outputs, "LdrColor");
    if (color_handle == OVRTX_INVALID_HANDLE) {
        std::cerr << "LdrColor output not found\n";
        ovrtx_destroy_results(renderer_, step_handle);
        return;
    }

    ovrtx_map_output_description_t map_desc{};
    map_desc.device_type = OVRTX_MAP_DEVICE_TYPE_CPU;
    ovrtx_render_var_output_t rendered_output{};
    result = ovrtx_map_render_var_output(renderer_, color_handle, &map_desc,
                                         ovrtx_timeout_infinite,
                                         &rendered_output);
    if (check_error(result, "map_render_var_output")) {
        ovrtx_destroy_results(renderer_, step_handle);
        return;
    }

    if (rendered_output.num_tensors != 1 || !rendered_output.tensors ||
        !rendered_output.tensors[0].dl) {
        std::cerr << "Unexpected LdrColor output: expected one tensor\n";
        ovrtx_cuda_sync_t no_sync{};
        ovrtx_unmap_render_var_output(renderer_, rendered_output.map_handle,
                                      no_sync);
        ovrtx_destroy_results(renderer_, step_handle);
        return;
    }

    DLTensor const &tensor = *rendered_output.tensors[0].dl;
    if (tensor.ndim != 3 || !tensor.shape || tensor.shape[2] != 4 ||
        tensor.dtype.lanes != 1) {
        std::cerr << "Unexpected LdrColor tensor layout; expected [H, W, 4]\n";
        ovrtx_cuda_sync_t no_sync{};
        ovrtx_unmap_render_var_output(renderer_, rendered_output.map_handle,
                                      no_sync);
        ovrtx_destroy_results(renderer_, step_handle);
        return;
    }

    int width = static_cast<int>(tensor.shape[1]);
    int height = static_cast<int>(tensor.shape[0]);

    QImage image(static_cast<const uchar *>(tensor.data), width, height,
                 width * 4, QImage::Format_RGBA8888);
    QImage copy = image.copy();

    ovrtx_cuda_sync_t no_sync{};
    result = ovrtx_unmap_render_var_output(renderer_, rendered_output.map_handle,
                                           no_sync);
    if (check_error(result, "unmap_render_var_output")) {
        ovrtx_destroy_results(renderer_, step_handle);
        return;
    }
    ovrtx_destroy_results(renderer_, step_handle);

    emit frameReady(copy);
}

void OvrtxEngine::destroyStep(uint64_t step_handle)
{
    ovrtx_render_product_set_outputs_t outputs{};
    ovrtx_fetch_results(renderer_, step_handle, ovrtx_timeout_infinite, &outputs);
    ovrtx_destroy_results(renderer_, step_handle);
}

// ---------------------------------------------------------------------------
// Attribute writes
// ---------------------------------------------------------------------------

bool OvrtxEngine::bindMaterial(const std::string &prim_path,
                               const std::string &material_path)
{
    if (!renderer_) {
        return false;
    }

    ovx_string_t prim = {prim_path.c_str(),
                         static_cast<uint64_t>(prim_path.size())};
    ovx_string_t mat = {material_path.c_str(),
                        static_cast<uint64_t>(material_path.size())};

    ovrtx_enqueue_result_t enqueue = ovrtx_set_path_attributes(
        renderer_, &prim, 1, literal_to_ovx_string("material:binding"), &mat);
    if (!wait_for_enqueued(renderer_, enqueue,
                           "set_path_attributes (material:binding)")) {
        return false;
    }

    // Reset renderer history so the path tracer doesn't show ghosting
    // from the previous material's accumulated samples.
    return reset_render_history(renderer_);
}

bool OvrtxEngine::writeFloatAttribute(const std::string &prim_path,
                                      const std::string &attr_name,
                                      float value)
{
    if (!renderer_) {
        return false;
    }

    ovx_string_t prim = {prim_path.c_str(),
                         static_cast<uint64_t>(prim_path.size())};
    ovx_string_t attr = {attr_name.c_str(),
                         static_cast<uint64_t>(attr_name.size())};

    DLDataType dtype{kDLFloat, 32, 1};
    size_t count = 1;
    DLTensor tensor = ovrtx_make_write_cpu_tensor(&value, &count, dtype);

    ovrtx_input_buffer_t buffer{};
    buffer.tensors = &tensor;
    buffer.tensor_count = 1;

    ovrtx_binding_desc_or_handle_t binding =
        ovrtx_make_binding_desc(&prim, count, attr, OVRTX_SEMANTIC_NONE, dtype);
    binding.binding_desc.prim_mode = OVRTX_BINDING_PRIM_MODE_CREATE_NEW;

    ovrtx_enqueue_result_t enqueue =
        ovrtx_write_attribute(renderer_, &binding, &buffer,
                              OVRTX_DATA_ACCESS_SYNC);
    if (!wait_for_enqueued(renderer_, enqueue, "write_attribute (float)")) {
        return false;
    }
    return reset_render_history(renderer_);
}

bool OvrtxEngine::writeColor3fAttribute(const std::string &prim_path,
                                        const std::string &attr_name,
                                        float r, float g, float b)
{
    if (!renderer_) {
        return false;
    }

    ovx_string_t prim = {prim_path.c_str(),
                         static_cast<uint64_t>(prim_path.size())};
    ovx_string_t attr = {attr_name.c_str(),
                         static_cast<uint64_t>(attr_name.size())};

    float color[3] = {r, g, b};
    DLDataType tensor_dtype{kDLFloat, 32, 1};
    DLDataType binding_dtype{kDLFloat, 32, 3};
    int64_t shape[2] = {1, 3};
    DLTensor tensor{};
    tensor.data = color;
    tensor.device = {kDLCPU, 0};
    tensor.ndim = 2;
    tensor.dtype = tensor_dtype;
    tensor.shape = shape;
    tensor.strides = nullptr;
    tensor.byte_offset = 0;

    ovrtx_input_buffer_t buffer{};
    buffer.tensors = &tensor;
    buffer.tensor_count = 1;

    ovrtx_binding_desc_or_handle_t binding =
        ovrtx_make_binding_desc(&prim, 1, attr, OVRTX_SEMANTIC_NONE, binding_dtype);
    binding.binding_desc.prim_mode = OVRTX_BINDING_PRIM_MODE_CREATE_NEW;

    ovrtx_enqueue_result_t enqueue =
        ovrtx_write_attribute(renderer_, &binding, &buffer,
                              OVRTX_DATA_ACCESS_SYNC);
    if (!wait_for_enqueued(renderer_, enqueue, "write_attribute (color3f)")) {
        return false;
    }
    return reset_render_history(renderer_);
}

bool OvrtxEngine::writeIntAttribute(const std::string &prim_path,
                                    const std::string &attr_name,
                                    int value)
{
    if (!renderer_) {
        return false;
    }

    ovx_string_t prim = {prim_path.c_str(),
                         static_cast<uint64_t>(prim_path.size())};
    ovx_string_t attr = {attr_name.c_str(),
                         static_cast<uint64_t>(attr_name.size())};

    int32_t value32 = static_cast<int32_t>(value);
    DLDataType dtype{kDLInt, 32, 1};
    size_t count = 1;
    DLTensor tensor = ovrtx_make_write_cpu_tensor(&value32, &count, dtype);

    ovrtx_input_buffer_t buffer{};
    buffer.tensors = &tensor;
    buffer.tensor_count = 1;

    ovrtx_binding_desc_or_handle_t binding =
        ovrtx_make_binding_desc(&prim, count, attr, OVRTX_SEMANTIC_NONE, dtype);
    binding.binding_desc.prim_mode = OVRTX_BINDING_PRIM_MODE_CREATE_NEW;

    ovrtx_enqueue_result_t enqueue =
        ovrtx_write_attribute(renderer_, &binding, &buffer,
                              OVRTX_DATA_ACCESS_SYNC);
    if (!wait_for_enqueued(renderer_, enqueue, "write_attribute (int)")) {
        return false;
    }
    return reset_render_history(renderer_);
}

bool OvrtxEngine::writeBoolAttribute(const std::string &prim_path,
                                     const std::string &attr_name,
                                     bool value)
{
    if (!renderer_) {
        return false;
    }

    ovx_string_t prim = {prim_path.c_str(),
                         static_cast<uint64_t>(prim_path.size())};
    ovx_string_t attr = {attr_name.c_str(),
                         static_cast<uint64_t>(attr_name.size())};

    uint8_t value_byte = value ? 1 : 0;
    DLDataType dtype{kDLUInt, 8, 1};
    size_t count = 1;
    DLTensor tensor = ovrtx_make_write_cpu_tensor(&value_byte, &count, dtype);

    ovrtx_input_buffer_t buffer{};
    buffer.tensors = &tensor;
    buffer.tensor_count = 1;

    ovrtx_binding_desc_or_handle_t binding =
        ovrtx_make_binding_desc(&prim, count, attr, OVRTX_SEMANTIC_NONE, dtype);
    binding.binding_desc.prim_mode = OVRTX_BINDING_PRIM_MODE_CREATE_NEW;

    ovrtx_enqueue_result_t enqueue =
        ovrtx_write_attribute(renderer_, &binding, &buffer,
                              OVRTX_DATA_ACCESS_SYNC);
    if (!wait_for_enqueued(renderer_, enqueue, "write_attribute (bool)")) {
        return false;
    }
    return reset_render_history(renderer_);
}

bool OvrtxEngine::writeTokenAttribute(const std::string &prim_path,
                                      const std::string &attr_name,
                                      const std::string &value)
{
    if (!renderer_) {
        return false;
    }

    ovx_string_t prim = {prim_path.c_str(),
                         static_cast<uint64_t>(prim_path.size())};
    ovx_string_t token_val = {value.c_str(),
                              static_cast<uint64_t>(value.size())};
    ovx_string_t attr = {attr_name.c_str(),
                         static_cast<uint64_t>(attr_name.size())};

    DLDataType dtype{kDLUInt, 128, 1}; // ovx_string_t = 16 bytes = 128 bits
    size_t count = 1;
    DLTensor tensor = ovrtx_make_write_cpu_tensor(&token_val, &count, dtype);

    ovrtx_input_buffer_t buffer{};
    buffer.tensors = &tensor;
    buffer.tensor_count = 1;

    ovrtx_binding_desc_or_handle_t binding =
        ovrtx_make_binding_desc(&prim, count, attr, OVRTX_SEMANTIC_TOKEN_STRING, dtype);
    binding.binding_desc.prim_mode = OVRTX_BINDING_PRIM_MODE_CREATE_NEW;

    ovrtx_enqueue_result_t enqueue =
        ovrtx_write_attribute(renderer_, &binding, &buffer,
                              OVRTX_DATA_ACCESS_SYNC);
    if (!wait_for_enqueued(renderer_, enqueue, "write_attribute (token)")) {
        return false;
    }
    return reset_render_history(renderer_);
}
