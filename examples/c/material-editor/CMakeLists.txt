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
project(material-editor)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

set(FETCHCONTENT_QUIET FALSE)
# Override FetchContent's base directory to share large deps among examples.
# If copying this project to your own workspace, delete this line or override it.
set(FETCHCONTENT_BASE_DIR "${CMAKE_CURRENT_LIST_DIR}/../_deps" CACHE PATH "")

# --- Dependencies ---

# Qt6
find_package(Qt6 REQUIRED COMPONENTS Widgets)

# OpenUSD
find_package(pxr REQUIRED)

# ovrtx
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../cmake")
include(ovrtx)
ovrtx_fetch()

# QtNodes (nodeeditor)
include(FetchContent)
FetchContent_Declare(
    nodeeditor
    GIT_REPOSITORY https://github.com/paceholder/nodeeditor.git
    GIT_TAG        master
    GIT_SHALLOW    TRUE
)
set(BUILD_TESTING OFF CACHE BOOL "" FORCE)
set(BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(USE_QT6 ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(nodeeditor)

# --- Target ---

add_executable(material-editor
    src/main.cpp
    src/main_window.cpp
    src/ovrtx_engine.cpp
    src/viewport_widget.cpp
    src/material_list_widget.cpp
    src/node_graph_widget.cpp
    src/property_panel_widget.cpp
    src/usd_material_graph.cpp
)

target_link_libraries(material-editor PRIVATE
    Qt6::Widgets
    QtNodes
    # Static-loader model: link the static ovrtx loader. ovrtx_engine.cpp hands the
    # loader its package root at runtime (a side-by-side `ovrtx/` link beside the
    # exe, created by ovrtx_setup_runtime) instead of replicating the package.
    ovrtx::ovrtx_static
    usd
    usdShade
    sdf
    sdr
    tf
)

target_include_directories(material-editor PRIVATE src)

if(MSVC)
    target_compile_definitions(material-editor PRIVATE NOMINMAX)
    # The ovrtx package ships a release-only static loader (compiled /MD). Force
    # the release CRT so the Debug config links cleanly.
    set_target_properties(material-editor PROPERTIES MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")
endif()

# Setup runtime dependencies (DLL copying, junctions, rpath)
ovrtx_setup_runtime(material-editor)

# Copy QtNodes DLL next to the executable on Windows
if(CMAKE_SYSTEM_NAME STREQUAL "Windows")
    add_custom_command(TARGET material-editor POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            $<TARGET_FILE:QtNodes>
            $<TARGET_FILE_DIR:material-editor>
        COMMENT "Copying QtNodes DLL to build directory"
    )
endif()

# Generate a launcher script on Windows that sets PATH for Qt6 and OpenUSD DLLs
if(CMAKE_SYSTEM_NAME STREQUAL "Windows")
    # Qt6: DLLs are in <prefix>/bin, Qt6_DIR is <prefix>/lib/cmake/Qt6
    get_filename_component(_QT_BIN_DIR "${Qt6_DIR}/../../../bin" ABSOLUTE)

    # OpenUSD: resolve the DLL directory from the imported 'usd' target
    set(_USD_LIB_DIR "")
    foreach(_prop
        IMPORTED_LOCATION_RELEASE
        IMPORTED_LOCATION_RELWITHDEBINFO
        IMPORTED_LOCATION_MINSIZEREL
        IMPORTED_LOCATION_DEBUG
        IMPORTED_LOCATION
    )
        get_target_property(_loc usd ${_prop})
        if(_loc)
            get_filename_component(_USD_LIB_DIR "${_loc}" DIRECTORY)
            break()
        endif()
    endforeach()
    if(NOT _USD_LIB_DIR)
        # Fallback: pxr_DIR is typically <prefix>/lib/cmake/pxr
        get_filename_component(_USD_LIB_DIR "${pxr_DIR}/../../../lib" ABSOLUTE)
    endif()

    file(TO_NATIVE_PATH "${_QT_BIN_DIR}" _QT_BIN_DIR_NATIVE)
    file(TO_NATIVE_PATH "${_USD_LIB_DIR}" _USD_LIB_DIR_NATIVE)

    configure_file(
        "${CMAKE_CURRENT_SOURCE_DIR}/run-material-editor.bat.in"
        "${CMAKE_BINARY_DIR}/run-material-editor.bat"
        @ONLY
    )
endif()
