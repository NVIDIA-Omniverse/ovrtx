// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "orbit_camera.hpp"

#include <cmath>
#include <algorithm>

OrbitCamera::OrbitCamera(float distance, float azimuth, float elevation, glm::vec3 target, UpAxis up_axis)
    : _distance(distance)
    , _azimuth(azimuth)
    , _elevation(elevation)
    , _target(target)
    , _up_axis(up_axis) {
}

void OrbitCamera::update(float delta_x, float delta_y, float sensitivity) {
    // Horizontal mouse movement rotates azimuth (inverted for natural feel)
    _azimuth -= delta_x * sensitivity;

    // Vertical mouse movement rotates elevation
    _elevation += delta_y * sensitivity;

    // Clamp elevation to avoid gimbal lock (keep slightly away from poles)
    float const max_elevation = glm::radians(89.0f);
    _elevation = std::clamp(_elevation, -max_elevation, max_elevation);

    // Wrap azimuth to [0, 2π)
    float const two_pi = 2.0f * glm::pi<float>();
    while (_azimuth < 0.0f) _azimuth += two_pi;
    while (_azimuth >= two_pi) _azimuth -= two_pi;
}

glm::vec3 OrbitCamera::position() const {
    // Convert spherical to Cartesian coordinates
    float cos_elev = std::cos(_elevation);
    float sin_elev = std::sin(_elevation);
    float cos_azim = std::cos(_azimuth);
    float sin_azim = std::sin(_azimuth);

    glm::vec3 offset;
    if (_up_axis == UpAxis::Y) {
        // Y-up convention:
        // - azimuth 0 points along +X
        // - elevation 0 is horizontal (XZ plane)
        // - elevation +90° points up (+Y)
        offset = glm::vec3(
            _distance * cos_elev * cos_azim,
            _distance * sin_elev,
            _distance * cos_elev * sin_azim
        );
    } else {
        // Z-up convention:
        // - azimuth 0 points along +X
        // - elevation 0 is horizontal (XY plane)
        // - elevation +90° points up (+Z)
        offset = glm::vec3(
            _distance * cos_elev * cos_azim,
            _distance * cos_elev * sin_azim,
            _distance * sin_elev
        );
    }

    return _target + offset;
}

glm::mat4 OrbitCamera::transform_matrix() const {
    glm::vec3 eye = position();

    // Look at target
    glm::vec3 forward = glm::normalize(_target - eye);
    glm::vec3 world_up = (_up_axis == UpAxis::Y)
        ? glm::vec3(0.0f, 1.0f, 0.0f)
        : glm::vec3(0.0f, 0.0f, 1.0f);
    glm::vec3 right = glm::normalize(glm::cross(forward, world_up));
    glm::vec3 up = glm::cross(right, forward);

    // Build camera-to-world transform matrix
    // Camera convention: -Z is forward, +Y is up, +X is right
    glm::mat4 transform(1.0f);

    // Set rotation (columns are camera axes in world space)
    transform[0] = glm::vec4(right, 0.0f);
    transform[1] = glm::vec4(up, 0.0f);
    transform[2] = glm::vec4(-forward, 0.0f);  // Camera looks down -Z
    transform[3] = glm::vec4(eye, 1.0f);

    return transform;
}
