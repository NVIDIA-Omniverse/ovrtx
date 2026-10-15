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
project(minimal-dlss LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(FETCHCONTENT_BASE_DIR "${CMAKE_CURRENT_LIST_DIR}/../_deps" CACHE PATH "")
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../cmake")
include(ovrtx)
include(ovstage)
ovrtx_fetch()
ovstage_fetch()

add_executable(minimal-dlss main.cpp)
target_link_libraries(minimal-dlss PRIVATE ovrtx::ovrtx ovstage::ovstage)
if(MSVC)
    set_target_properties(minimal-dlss PROPERTIES MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")
endif()

ovrtx_setup_runtime(minimal-dlss)
ovstage_setup_runtime(minimal-dlss)
