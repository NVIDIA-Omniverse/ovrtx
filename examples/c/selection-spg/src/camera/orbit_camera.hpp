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

#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>

// Up axis for coordinate system convention
enum class UpAxis { Y, Z };

// Orbit camera controller using spherical coordinates
class OrbitCamera {
public:
    // Initialize with distance from target, azimuth (horizontal angle), elevation (vertical angle)
    // up_axis specifies whether Y or Z is the vertical axis
    OrbitCamera(float distance, float azimuth, float elevation,
                glm::vec3 target = glm::vec3(0.0f), UpAxis up_axis = UpAxis::Y);

    // Update orbit angles from mouse delta (in pixels)
    // sensitivity controls how many radians per pixel
    void update(float delta_x, float delta_y, float sensitivity = 0.005f);

    // Get the camera-to-world transform matrix
    glm::mat4 transform_matrix() const;

    // Get camera position in world space
    glm::vec3 position() const;

    // Accessors
    float distance() const { return _distance; }
    float azimuth() const { return _azimuth; }
    float elevation() const { return _elevation; }
    glm::vec3 target() const { return _target; }
    UpAxis up_axis() const { return _up_axis; }

    // Setters
    void set_distance(float d) { _distance = d; }
    void set_target(glm::vec3 t) { _target = t; }

private:
    float _distance;    // Distance from target
    float _azimuth;     // Horizontal angle (radians, 0 = +X, π/2 = +Y or +Z depending on up_axis)
    float _elevation;   // Vertical angle (radians, 0 = horizontal, +π/2 = up)
    glm::vec3 _target;  // Point to orbit around
    UpAxis _up_axis;    // Which axis is "up" (Y or Z)
};
