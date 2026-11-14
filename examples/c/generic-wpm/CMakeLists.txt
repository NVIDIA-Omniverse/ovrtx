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
project(generic-wpm LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(FETCHCONTENT_BASE_DIR "${CMAKE_CURRENT_LIST_DIR}/../_deps" CACHE PATH "")
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../cmake")
include(ovrtx)
include(ovstage)
ovrtx_fetch()
ovstage_fetch()

add_executable(generic-wpm main.cpp)
target_link_libraries(generic-wpm PRIVATE ovrtx::ovrtx ovstage::ovstage)
if(MSVC)
    set_target_properties(generic-wpm PROPERTIES MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")
endif()
ovrtx_setup_runtime(generic-wpm)
ovstage_setup_runtime(generic-wpm)

enable_testing()
get_filename_component(public_root "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
add_test(NAME generic-wpm-depth COMMAND generic-wpm "${public_root}" depth "${CMAKE_CURRENT_BINARY_DIR}/_output/depth.csv")
add_test(NAME generic-wpm-live-edits COMMAND generic-wpm "${public_root}" mixed "${CMAKE_CURRENT_BINARY_DIR}/_output/mixed.csv" --live-edits)
add_test(NAME generic-wpm-bloom COMMAND generic-wpm "${public_root}" gaussian_bloom "${CMAKE_CURRENT_BINARY_DIR}/_output/bloom.csv")
set_tests_properties(generic-wpm-depth generic-wpm-live-edits generic-wpm-bloom PROPERTIES TIMEOUT 600 RUN_SERIAL TRUE)
