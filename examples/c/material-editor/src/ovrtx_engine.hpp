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

#include <QObject>
#include <QImage>
#include <QTimer>
#include <string>
#include <cstdint>

#include <ovrtx/ovrtx_types.h>

/// Encapsulates the ovrtx renderer lifecycle: initialization, USD loading,
/// stepping/rendering, material binding, and attribute writing.
///
/// Rendering is asynchronous: startRender() does one immediate step for fast
/// feedback, then continues in timer-driven chunks of kChunkSize frames,
/// emitting frameReady after each chunk.  Calling startRender() again cancels
/// any in-progress render and restarts.
class OvrtxEngine : public QObject {
    Q_OBJECT
public:
    explicit OvrtxEngine(QObject *parent = nullptr);
    ~OvrtxEngine() override;

    /// Initialize the renderer and load the given USD file.
    bool initialize(const std::string &usda_path);

    /// Shut down the renderer and release resources.
    void shutdown();

    /// Kick off an async render.  Does 1 immediate step for fast feedback,
    /// then continues in chunks via QTimer until target iterations reached.
    /// Calling again cancels any in-progress render and restarts.
    void startRender(int iterations = 50);

    /// Bind a material to a prim.
    bool bindMaterial(const std::string &prim_path, const std::string &material_path);

    /// Write a float attribute on a shader prim.
    bool writeFloatAttribute(const std::string &prim_path,
                             const std::string &attr_name, float value);

    /// Write a color3f attribute on a shader prim.
    bool writeColor3fAttribute(const std::string &prim_path,
                               const std::string &attr_name,
                               float r, float g, float b);

    /// Write an int attribute on a shader prim.
    bool writeIntAttribute(const std::string &prim_path,
                           const std::string &attr_name, int value);

    /// Write a bool attribute on a shader prim.
    bool writeBoolAttribute(const std::string &prim_path,
                            const std::string &attr_name, bool value);

    /// Write a token attribute on a shader prim.
    bool writeTokenAttribute(const std::string &prim_path,
                             const std::string &attr_name,
                             const std::string &value);

signals:
    void frameReady(QImage image);

private slots:
    void onRenderTick();

private:
    /// Run a single step+wait cycle.  Returns the step result handle,
    /// or a zero handle on failure.
    ovrtx_step_result_handle_t stepOnce();

    /// Map the LdrColor output from a step result, emit frameReady, then
    /// unmap and destroy the result.
    void mapAndEmit(ovrtx_step_result_handle_t step_handle);

    /// Destroy a step result without mapping.
    void destroyStep(ovrtx_step_result_handle_t step_handle);

    ovrtx_renderer_t *renderer_ = nullptr;
    std::string render_product_path_ = "/Render/Camera";

    QTimer *render_timer_ = nullptr;
    int render_iterations_remaining_ = 0;
    static constexpr int kChunkSize = 4;
};
