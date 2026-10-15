# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

cmake_minimum_required(VERSION 3.16)
project(decals)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(FETCHCONTENT_QUIET FALSE)
set(FETCHCONTENT_BASE_DIR "${CMAKE_CURRENT_LIST_DIR}/../_deps" CACHE PATH "")

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../cmake")
include(ovrtx)
include(ovstage)
ovrtx_fetch()
ovstage_fetch()

add_executable(decals main.cpp)
target_link_libraries(decals PRIVATE ovrtx::ovrtx_static ovstage::ovstage_static)
target_compile_definitions(decals PRIVATE OVRTX_EXAMPLE_STATIC_LOADERS=1)
target_include_directories(decals PRIVATE "${CMAKE_CURRENT_LIST_DIR}/../minimal")

add_executable(decals-dynamic main.cpp)
target_link_libraries(decals-dynamic PRIVATE ovrtx::ovrtx ovstage::ovstage)
target_include_directories(decals-dynamic PRIVATE "${CMAKE_CURRENT_LIST_DIR}/../minimal")

set_target_properties(decals PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/static")
set_target_properties(decals-dynamic PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/shared")
if(MSVC)
    set_target_properties(decals decals-dynamic PROPERTIES MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")
endif()

ovrtx_setup_runtime(decals)
ovstage_setup_runtime(decals)
ovrtx_setup_runtime(decals-dynamic)
ovstage_setup_runtime(decals-dynamic)

set(DECALS_DATA_DIR "${CMAKE_CURRENT_LIST_DIR}/../../../tests/docs/data")
set(DECALS_ASSETS
    ovrtx-test-decals.usda
    decal-rtx-mask.png
    decal-nvidia-mask.png
    ovrtx-test-base.usda
    ovrtx-test-base-light.usda
    ovrtx-test-base-camera.usda
    ovrtx-test-base-materials.usda
    ovrtx-test-base-geometry.usda
    studio.exr
    lookdev_grid_10k.png
    logo.usd)
foreach(target decals decals-dynamic)
    foreach(asset IN LISTS DECALS_ASSETS)
        add_custom_command(TARGET ${target} POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                "${DECALS_DATA_DIR}/${asset}" "$<TARGET_FILE_DIR:${target}>/${asset}")
    endforeach()
endforeach()
