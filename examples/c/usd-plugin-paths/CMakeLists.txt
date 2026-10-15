# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

# [snippet:plugin-c-project-setup]
cmake_minimum_required(VERSION 3.16)
project(usd-plugin-paths)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(FETCHCONTENT_QUIET FALSE)
# Share large dependencies with the other C examples.
set(FETCHCONTENT_BASE_DIR "${CMAKE_CURRENT_LIST_DIR}/../_deps" CACHE PATH "")
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../cmake")
include(ovrtx)
ovrtx_fetch()
# [/snippet:plugin-c-project-setup]

# [snippet:plugin-c-linking-models]
add_executable(usd-plugin-paths main.cpp)
target_link_libraries(usd-plugin-paths PRIVATE ovrtx::ovrtx_static)
target_compile_definitions(usd-plugin-paths PRIVATE OVRTX_EXAMPLE_STATIC_LOADERS=1)

add_executable(usd-plugin-paths-dynamic main.cpp)
target_link_libraries(usd-plugin-paths-dynamic PRIVATE ovrtx::ovrtx)

# Keep each loader model's deployment separate.
set_target_properties(usd-plugin-paths PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/static")
set_target_properties(usd-plugin-paths-dynamic PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/shared")

# The published static loader uses the release CRT.
if(MSVC)
    set_target_properties(usd-plugin-paths usd-plugin-paths-dynamic PROPERTIES
        MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")
endif()

ovrtx_setup_runtime(usd-plugin-paths)
ovrtx_setup_runtime(usd-plugin-paths-dynamic)
# [/snippet:plugin-c-linking-models]
