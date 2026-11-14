# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

cmake_minimum_required(VERSION 3.18)
project(runtime-textures)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(FETCHCONTENT_QUIET FALSE)
set(FETCHCONTENT_BASE_DIR "${CMAKE_CURRENT_LIST_DIR}/../_deps" CACHE PATH "")

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../cmake")
include(ovrtx)
include(ovstage)
ovrtx_fetch()
ovstage_fetch()

add_executable(runtime-textures main.cpp)
target_link_libraries(runtime-textures PRIVATE ovrtx::ovrtx_static ovstage::ovstage_static)
target_compile_definitions(runtime-textures PRIVATE OVRTX_EXAMPLE_STATIC_LOADERS=1)
target_include_directories(runtime-textures PRIVATE "${CMAKE_CURRENT_LIST_DIR}/../minimal")

add_executable(runtime-textures-dynamic main.cpp)
target_link_libraries(runtime-textures-dynamic PRIVATE ovrtx::ovrtx ovstage::ovstage)
target_include_directories(runtime-textures-dynamic PRIVATE "${CMAKE_CURRENT_LIST_DIR}/../minimal")

set_target_properties(runtime-textures PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/static")
set_target_properties(runtime-textures-dynamic PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/shared")
if(MSVC)
    set_target_properties(runtime-textures runtime-textures-dynamic PROPERTIES MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")
endif()

ovrtx_setup_runtime(runtime-textures)
ovstage_setup_runtime(runtime-textures)
ovrtx_setup_runtime(runtime-textures-dynamic)
ovstage_setup_runtime(runtime-textures-dynamic)

set(RUNTIME_TEXTURES_DATA_DIR "${CMAKE_CURRENT_LIST_DIR}/../../../tests/docs/data")
set(RUNTIME_TEXTURES_ASSETS
    ovrtx-test-runtime-textures.usda
    ovrtx-test-base-light.usda
    ovrtx-test-base-camera.usda
    ovrtx-test-base-geometry.usda
    studio.exr
    logo.usd)
foreach(target runtime-textures runtime-textures-dynamic)
    foreach(asset IN LISTS RUNTIME_TEXTURES_ASSETS)
        add_custom_command(TARGET ${target} POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                "${RUNTIME_TEXTURES_DATA_DIR}/${asset}" "$<TARGET_FILE_DIR:${target}>/${asset}")
    endforeach()
endforeach()

find_package(CUDAToolkit REQUIRED)
foreach(target runtime-textures runtime-textures-dynamic)
    target_link_libraries(${target} PRIVATE CUDA::cuda_driver)
endforeach()
