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
project(ovrtx_docs_tests_c)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(FETCHCONTENT_QUIET FALSE)
# Share large deps with the C examples.
set(FETCHCONTENT_BASE_DIR "${CMAKE_CURRENT_LIST_DIR}/../../../examples/c/_deps" CACHE PATH "")

# Fetch ovrtx + ovstage libraries (reuse the cmake modules from examples/c/)
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../../../examples/c/cmake")
include(ovrtx)
include(ovstage)
ovrtx_fetch()
ovstage_fetch()

# Compile every header shipped by the ovrtx package as the first and only
# include in isolated C11 and C++17 translation units. This catches language
# incompatibilities and hidden include-order dependencies in the public API.
file(GLOB_RECURSE OVRTX_PUBLIC_HEADERS
    LIST_DIRECTORIES FALSE
    RELATIVE "${OVRTX_INCLUDE_DIR}"
    "${OVRTX_INCLUDE_DIR}/*.h")
list(SORT OVRTX_PUBLIC_HEADERS)

set(OVRTX_HEADER_SWEEP_DIR "${CMAKE_CURRENT_BINARY_DIR}/header-standalone")
file(MAKE_DIRECTORY "${OVRTX_HEADER_SWEEP_DIR}")

foreach(header IN LISTS OVRTX_PUBLIC_HEADERS)
    string(MAKE_C_IDENTIFIER "${header}" header_id)
    set(c_source "${OVRTX_HEADER_SWEEP_DIR}/${header_id}.c")
    set(cxx_source "${OVRTX_HEADER_SWEEP_DIR}/${header_id}.cpp")
    file(WRITE "${c_source}" "#include <${header}>\n")
    file(WRITE "${cxx_source}" "#include <${header}>\n")
    list(APPEND OVRTX_HEADER_C_SOURCES "${c_source}")
    list(APPEND OVRTX_HEADER_CXX_SOURCES "${cxx_source}")
endforeach()

add_library(ovrtx_public_headers_c OBJECT ${OVRTX_HEADER_C_SOURCES})
target_include_directories(ovrtx_public_headers_c PRIVATE "${OVRTX_INCLUDE_DIR}")
set_target_properties(ovrtx_public_headers_c PROPERTIES
    C_STANDARD 11
    C_STANDARD_REQUIRED ON
    C_EXTENSIONS OFF)

add_library(ovrtx_public_headers_cxx OBJECT ${OVRTX_HEADER_CXX_SOURCES})
target_include_directories(ovrtx_public_headers_cxx PRIVATE "${OVRTX_INCLUDE_DIR}")
set_target_properties(ovrtx_public_headers_cxx PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF)

# Fetch GoogleTest
include(FetchContent)
FetchContent_Declare(
    googletest
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE
    URL https://github.com/google/googletest/archive/refs/tags/v1.15.2.tar.gz
    URL_HASH SHA256=7b42b4d6ed48810c5362c265a17faebe90dc2373c885e5216439d37927f02926
)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

enable_testing()

add_executable(ovrtx_docs_tests
    main.cpp
    test_base.cpp
    test_camera_aovs.cpp
    test_camera_sensors.cpp
    test_sensor_configuration.cpp
    test_stage_query.cpp
    test_stage_mutation.cpp
    test_attribute_bindings.cpp
    test_attribute_read.cpp
    test_attribute_helpers.cpp
    test_attribute_shapes.cpp
    test_error_handling.cpp
    test_logging.cpp
    test_semantic_labels.cpp
    test_support_api.cpp
    test_all_attributes.cpp
    test_transform_helpers.cpp
    test_picking_selection.cpp
    stb_impl.cpp
    helpers.h
)
# Static-loader model: link the static ovrtx loader. main.cpp calls
# ovrtx_initialize() once with the package root (a side-by-side `ovrtx/` link
# beside the exe, created by ovrtx_setup_runtime), so the system stays up and the
# per-test ovrtx_create_renderer() calls inherit it without repeating the root.
target_link_libraries(ovrtx_docs_tests PRIVATE ovrtx::ovrtx_static ovstage::ovstage_static GTest::gtest)
target_include_directories(ovrtx_docs_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

# The ovrtx package ships a release-only static loader (compiled /MD). Force the
# release CRT so the Debug config links cleanly.
if(MSVC)
    set_target_properties(ovrtx_docs_tests PROPERTIES MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")
endif()

# Setup runtime dependencies. Under ovrtx's model #1 the exe root's plugins/
# is free, so both loaders can stage side-by-side links (ovrtx/ and ovstage/).
ovrtx_setup_runtime(ovrtx_docs_tests)
ovstage_setup_runtime(ovrtx_docs_tests)

include(GoogleTest)
gtest_discover_tests(ovrtx_docs_tests TEST_FILTER "*-PickingSelectionTest.*:SelectionStyleTest.*:PickingSelectionLegacyTest.*")

# Add picking tests manually so CTest reports fixture setup failures as
# failures instead of converting GoogleTest's skipped child-test lines into a
# skipped CTest result.
foreach(test_name
    PickingSelectionTest.PickCenterPixel
    PickingSelectionTest.MarqueePicksMultiplePrims
    PickingSelectionTest.SelectionOutlineGroupRenders
    SelectionStyleTest.SelectionStyleGroupsControlOutlineAndFill
    PickingSelectionLegacyTest.PickableFalseExcludesPrim
)
    add_test(NAME ${test_name}
        COMMAND ovrtx_docs_tests
            --gtest_filter=${test_name}
            --gtest_also_run_disabled_tests
    )
    set_tests_properties(${test_name} PROPERTIES
        WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
    )
endforeach()
