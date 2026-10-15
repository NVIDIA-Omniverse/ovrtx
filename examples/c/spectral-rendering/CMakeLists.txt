# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

cmake_minimum_required(VERSION 3.16)
project(spectral-rendering LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(FETCHCONTENT_BASE_DIR "${CMAKE_CURRENT_LIST_DIR}/../_deps" CACHE PATH "")
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../cmake")
include(ovrtx)
include(ovstage)
ovrtx_fetch()
ovstage_fetch()

add_executable(spectral-rendering main.cpp)
target_link_libraries(spectral-rendering PRIVATE ovrtx::ovrtx ovstage::ovstage)
if(MSVC)
    set_target_properties(spectral-rendering PROPERTIES MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")
endif()

ovrtx_setup_runtime(spectral-rendering)
ovstage_setup_runtime(spectral-rendering)

# Stage the shared layer and its local asset closure beside the executable.
set(SPECTRAL_DATA "${CMAKE_CURRENT_LIST_DIR}/../../../tests/docs/data")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CMAKE_CURRENT_LIST_DIR}/../../python/spectral-rendering/spectral.usda")
file(READ "${CMAKE_CURRENT_LIST_DIR}/../../python/spectral-rendering/spectral.usda" SPECTRAL_LAYER)
string(REPLACE "../../../tests/docs/data/" "data/" SPECTRAL_LAYER "${SPECTRAL_LAYER}")
file(GENERATE OUTPUT "$<TARGET_FILE_DIR:spectral-rendering>/spectral.usda" CONTENT "${SPECTRAL_LAYER}")
add_custom_command(TARGET spectral-rendering POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:spectral-rendering>/data"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${SPECTRAL_DATA}/ovrtx-light-test-rect.usda" "${SPECTRAL_DATA}/ground.usd"
        "${SPECTRAL_DATA}/lookdev_grid_10k.png"
        "${SPECTRAL_DATA}/diamond.usd" "${SPECTRAL_DATA}/simple_surface_materials.mdl"
        "$<TARGET_FILE_DIR:spectral-rendering>/data"
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${SPECTRAL_DATA}/balls" "$<TARGET_FILE_DIR:spectral-rendering>/data/balls"
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${SPECTRAL_DATA}/colorchecker" "$<TARGET_FILE_DIR:spectral-rendering>/data/colorchecker")

# Stage camera curves and source notices with the shared spectral scene.
foreach(CAMERA_FILE camera_responsivity.usda RAWTOACES-LICENSE CAMERA_RESPONSIVITY.md COLOUR-LICENSE SPECTRA.md)
    set(CAMERA_SOURCE "${CMAKE_CURRENT_LIST_DIR}/../../python/spectral-rendering/${CAMERA_FILE}")
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${CAMERA_SOURCE}")
    file(READ "${CAMERA_SOURCE}" CAMERA_CONTENT)
    file(GENERATE OUTPUT "$<TARGET_FILE_DIR:spectral-rendering>/${CAMERA_FILE}" CONTENT "${CAMERA_CONTENT}")
endforeach()
