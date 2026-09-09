# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

# ovstage.cmake - Fetch and configure the ovstage library as its own package
#
# ovstage ships an independent, self-contained C++ package parallel to ovrtx.
# This module fetches that package and exposes both the shared
# ovstage::ovstage loader and the static
# ovstage::ovstage_static imported targets via find_package.
#
# Usage:
#   list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../cmake")
#   include(ovrtx)
#   include(ovstage)
#   ovrtx_fetch()
#   ovstage_fetch()
#
#   add_executable(myapp main.cpp)
#   # Static loaders for both packages (the sample's path): each package is
#   # exposed as a single side-by-side link (ovrtx/ and ovstage/) and main.cpp
#   # hands each loader its own binary package root.
#   target_link_libraries(myapp PRIVATE ovrtx::ovrtx_static ovstage::ovstage_static)
#   # Shared loaders are also supported: link ovrtx::ovrtx and
#   # ovstage::ovstage instead.
#   ovrtx_setup_runtime(myapp)
#   ovstage_setup_runtime(myapp)
#
# Attach mode requires ONE shared USD runtime; see the
# ovstage_setup_runtime() doc below for how that single-runtime guarantee is met.
# Both shared targets defer their runtimes until the first API initialization
# call, so applications can register schema paths before OpenUSD is loaded.

# Capture this file's directory at parse time (before macro expansion);
# CMAKE_CURRENT_LIST_DIR inside a macro would refer to the caller's directory.
set(_OVSTAGE_CMAKE_DIR "${CMAKE_CURRENT_LIST_DIR}")

# ovstage_setup_runtime detects the ovrtx linking model via helpers defined in
# ovrtx.cmake (ovstage is always used in attach mode alongside ovrtx). Pull them
# in if a project included ovstage without ovrtx first.
if(NOT COMMAND _ovrtx_target_uses_static_loader)
    include(ovrtx OPTIONAL)
endif()

# Detect whether TARGET links the static ovstage loader (ovstage::ovstage_static).
# The examples link it directly before calling ovstage_setup_runtime, so it shows
# up in LINK_LIBRARIES. When present we deploy ovstage as a single side-by-side
# ovstage/ link (mirroring ovrtx model #1) instead of the shared-loader deployment
# path. Mirrors _ovrtx_target_uses_static_loader.
function(_ovstage_target_uses_static_loader TARGET_NAME OUT_VAR)
    get_target_property(_libs ${TARGET_NAME} LINK_LIBRARIES)
    if(_libs AND "ovstage::ovstage_static" IN_LIST _libs)
        set(${OUT_VAR} TRUE PARENT_SCOPE)
    else()
        set(${OUT_VAR} FALSE PARENT_SCOPE)
    endif()
endfunction()

# Fetch the ovstage package
macro(ovstage_fetch)
    find_package(ovstage QUIET)

    if (ovstage_FOUND)
        message(STATUS "found ovstage at: ${ovstage_DIR}")
    else()
        set(FETCHCONTENT_QUIET FALSE)

        # Override FetchContent's base directory to share large deps among
        # examples. Uses the directory where ovstage.cmake lives so all examples
        # share the same _deps. If copying this project to your own workspace,
        # delete this line or override it.
        if(NOT DEFINED CACHE{FETCHCONTENT_BASE_DIR})
            set(FETCHCONTENT_BASE_DIR "${_OVSTAGE_CMAKE_DIR}/_deps" CACHE PATH "Shared FetchContent directory")
        endif()

        # Platform-specific package selection. Hashes below are maintained by
        # tools/update_ovrtx_deps.py (which now also propagates ovstage) from
        # deps/ovrtx_deps.yaml; do not hand-edit.
        if(CMAKE_SYSTEM_NAME STREQUAL "Windows")
            set(OVSTAGE_PACKAGE_SYSTEM "windows-x86_64")
            set(OVSTAGE_HASH "2ca9a39310f6a0622166c4bca2affbe11695c592ec6b22e74a7a1b5dacd0cdff")
        elseif(CMAKE_SYSTEM_NAME STREQUAL "Linux")
            if (CMAKE_SYSTEM_PROCESSOR STREQUAL "aarch64")
                set(OVSTAGE_PACKAGE_SYSTEM "manylinux_2_35_aarch64")
                set(OVSTAGE_HASH "1ff3b64ccc17c4cf7f99636d1f8648c98f7de73e0e6308aa5daf5aec3a030994")
            elseif(CMAKE_SYSTEM_PROCESSOR STREQUAL "x86_64")
                set(OVSTAGE_PACKAGE_SYSTEM "manylinux_2_35_x86_64")
                set(OVSTAGE_HASH "e5dc1738d632f35407259d68bf3edb9d012d00900f0fa50e44f730e76a93e4a5")
            else()
                message(FATAL_ERROR "Unsupported system: ${CMAKE_SYSTEM_NAME} ${CMAKE_SYSTEM_PROCESSOR}")
            endif()
        else()
            message(FATAL_ERROR "Unsupported system: ${CMAKE_SYSTEM_NAME} ${CMAKE_SYSTEM_PROCESSOR}")
        endif()

        include(FetchContent)

        # test override: consume a local package
        if(NOT OVSTAGE_LOCAL_PACKAGE AND DEFINED ENV{OVSTAGE_LOCAL_PACKAGE})
            set(OVSTAGE_LOCAL_PACKAGE "$ENV{OVSTAGE_LOCAL_PACKAGE}")
        endif()
        if(OVSTAGE_LOCAL_PACKAGE)
            message(STATUS "ovstage: using local package ${OVSTAGE_LOCAL_PACKAGE}")
            FetchContent_Declare(
                ovstage
                DOWNLOAD_EXTRACT_TIMESTAMP TRUE
                URL "${OVSTAGE_LOCAL_PACKAGE}"
            )
        else()
        FetchContent_Declare(
            ovstage
            DOWNLOAD_EXTRACT_TIMESTAMP TRUE
            URL "https://github.com/NVIDIA-Omniverse/ovstage/releases/download/v0.2.0/ovstage@0.2.0.377349.70d78229.${OVSTAGE_PACKAGE_SYSTEM}.zip"
            URL_HASH SHA256=${OVSTAGE_HASH}
        )

        endif()

        FetchContent_MakeAvailable(ovstage)

        # Make ovstage findable by find_package (ships lib/cmake/ovstage/ovstageConfig.cmake)
        list(APPEND CMAKE_PREFIX_PATH ${ovstage_SOURCE_DIR})

        find_package(ovstage REQUIRED)

    endif()
endmacro()

# Setup ovstage runtime dependencies for a target. Two models, selected from
# whether TARGET links ovstage::ovstage_static:
#
#  * STATIC loader (ovstage::ovstage_static) - the sample's path. Mirrors ovrtx
#    model #1: expose the package as a SINGLE link `ovstage/` next to the exe
#    (junction on Windows, symlink on Linux) -> the package bin/, which main.cpp
#    hands to ovstage_initialize() as the binary package root. The static loader
#    loads the runtime from that link on the first ovstage call and self-locates
#    its plugins/ under it.
#
#  * SHARED loader (ovstage::ovstage). The operating system loads only the small
#    ovstage shared loader at process startup. Its first initialize/create call
#    opens the colocated ovstage runtime, after the application has had a chance
#    to register schema paths. On Windows we copy both loader and runtime beside
#    the executable and junction the required package directories. On Linux an
#    rpath keeps both in the package bin directory.
#
# The plugins/
# name is shared with ovrtx, so its treatment depends on the ovrtx model (detected
# via ovrtx::ovrtx_static on the target):
#   - Model #1: ovrtx's runtime stays under the single `ovrtx/` link, so <exe>/plugins
#     is free and we junction ovstage's own plugins/ closure there.
#   - Model #2: ovrtx replicates its plugins/ at the exe root, so <exe>/plugins is
#     ovrtx's; the ovstage runtime shares that single tree
#     and we do NOT junction a second, colliding plugins/.
#
# OVSTAGE_BINARY_DIR is exported by ovstageConfig.cmake (the package's bin/ dir).
function(ovstage_setup_runtime TARGET_NAME)
    if(NOT DEFINED OVSTAGE_BINARY_DIR)
        message(FATAL_ERROR "OVSTAGE_BINARY_DIR is not set; call ovstage_fetch() before ovstage_setup_runtime()")
    endif()

    # Static loader (ovstage::ovstage_static): a single side-by-side link to the
    # package bin, exactly like ovrtx model #1. main.cpp passes <exe>/ovstage to
    # ovstage_initialize(); the loader loads ovstage.dll and self-locates the rest,
    # so no dll copy / delay-load / schemas / plugins junction is needed here.
    _ovstage_target_uses_static_loader(${TARGET_NAME} _ovstage_uses_static)
    if(_ovstage_uses_static)
        if(CMAKE_SYSTEM_NAME STREQUAL "Windows")
            _ovrtx_add_dir_junction(${TARGET_NAME}
                "$<TARGET_FILE_DIR:${TARGET_NAME}>/ovstage" "${OVSTAGE_BINARY_DIR}"
                "Junctioning the ovstage package bin beside the exe as ovstage/")
        else()
            # -sfnT replaces an existing symlink in place and refuses to descend
            # into a real directory named ovstage, keeping rebuilds idempotent.
            add_custom_command(TARGET ${TARGET_NAME} POST_BUILD
                COMMAND ln -sfnT "${OVSTAGE_BINARY_DIR}" "$<TARGET_FILE_DIR:${TARGET_NAME}>/ovstage"
                COMMENT "Symlinking the ovstage package bin beside the exe as ovstage/"
            )
        endif()
        return()
    endif()

    # --- Shared ovstage::ovstage below ---
    # Under ovrtx model #2 the exe root's plugins/ is ovrtx's; ovstage shares it.
    # Only under model #1 do we junction ovstage's own plugins/ beside the exe.
    _ovrtx_target_uses_static_loader(${TARGET_NAME} _ovstage_static_model)

    if(CMAKE_SYSTEM_NAME STREQUAL "Windows")
        # The executable imports only ovstage-dynamic.dll. Copy the loader and
        # its runtime together so the first ovstage call can resolve the latter.
        add_custom_command(TARGET ${TARGET_NAME} POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                "${OVSTAGE_BINARY_DIR}/ovstage-dynamic.dll"
                "${OVSTAGE_BINARY_DIR}/ovstage.dll"
                "$<TARGET_FILE_DIR:${TARGET_NAME}>"
            COMMENT "Copying the ovstage shared loader and runtime to the build directory"
        )

        # Junction ovstage's own plugins/ closure only under model #1 (model #2
        # shares ovrtx's plugins/). ovstage ships no USD schema data of its own:
        # a consumer that needs extra schema families registers them itself with
        # ovstage_population_register_usd_schemas(), from wherever it keeps them.
        set(OVSTAGE_RUNTIME_DIRS)
        if(_ovstage_static_model)
            list(APPEND OVSTAGE_RUNTIME_DIRS plugins)
        endif()
        foreach(DIR ${OVSTAGE_RUNTIME_DIRS})
            if(EXISTS "${OVSTAGE_BINARY_DIR}/${DIR}")
                _ovrtx_add_dir_junction(${TARGET_NAME}
                    "$<TARGET_FILE_DIR:${TARGET_NAME}>/${DIR}" "${OVSTAGE_BINARY_DIR}/${DIR}"
                    "Junctioning ovstage ${DIR} beside the exe")
            endif()
        endforeach()
    else()
        # Linux consumes the loader and runtime in place. An rpath entry pointing
        # at the package bin/ lets the executable find the loader; the loader then
        # finds the colocated runtime and package closure.
        set_property(TARGET ${TARGET_NAME} APPEND PROPERTY
            BUILD_RPATH "${OVSTAGE_BINARY_DIR}")
        set_property(TARGET ${TARGET_NAME} APPEND PROPERTY
            INSTALL_RPATH "${OVSTAGE_BINARY_DIR}")
    endif()
endfunction()
