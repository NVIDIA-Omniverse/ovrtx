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
project(minimal)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(FETCHCONTENT_QUIET FALSE)
# Override FetchContent's base directory to share large deps among examples.
# If copying this project to your own workspace, delete this line or override it.
set(FETCHCONTENT_BASE_DIR "${CMAKE_CURRENT_LIST_DIR}/../_deps" CACHE PATH "")

# Fetch ovrtx and ovstage libraries (each is its own independent package)
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../cmake")
include(ovrtx)
include(ovstage)
ovrtx_fetch()
ovstage_fetch()

add_executable(minimal main.cpp)
# Static-loader model for BOTH packages: link the static ovrtx and ovstage
# loaders. main.cpp / *_setup_runtime hand each loader its own package root at
# runtime (a side-by-side `ovrtx/` and `ovstage/` link beside the exe) instead of
# replicating either package next to the exe.
target_link_libraries(minimal PRIVATE ovrtx::ovrtx_static ovstage::ovstage_static)

# The ovrtx/ovstage packages ship release-only static loaders (compiled /MD).
# Force the release CRT so the Debug config links cleanly.
if(MSVC)
    set_target_properties(minimal PROPERTIES MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")
endif()

# Setup runtime dependencies (DLL copying, junctions, rpath)
ovrtx_setup_runtime(minimal)
ovstage_setup_runtime(minimal)
