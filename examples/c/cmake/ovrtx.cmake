# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

# ovrtx.cmake - Fetch and configure ovrtx library
#
# Usage:
#   list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../cmake")
#   include(ovrtx)
#   ovrtx_fetch()
#
#   add_executable(myapp main.cpp)
#   # Model #1 (recommended): link the static loader and pass the package root at
#   # runtime; ovrtx_setup_runtime links ovrtx/ beside the exe for main.cpp to resolve.
#   target_link_libraries(myapp PRIVATE ovrtx::ovrtx_static)
#   # Model #2: link ovrtx::ovrtx instead; ovrtx_setup_runtime then replicates the
#   # package (DLLs + junctions on Windows, rpath on Linux) beside the exe.
#   ovrtx_setup_runtime(myapp)

# [snippet:ovrtx_fetch]
# Capture this file's directory at parse time (before macro expansion)
# CMAKE_CURRENT_LIST_DIR inside a macro would refer to the caller's directory
set(_OVRTX_CMAKE_DIR "${CMAKE_CURRENT_LIST_DIR}")

# Fetch ovrtx package
macro(ovrtx_fetch)
    find_package(ovrtx QUIET)

    if (ovrtx_FOUND)
        message(STATUS "found ovrtx at: ${ovrtx_DIR}")
    else()
        set(FETCHCONTENT_QUIET FALSE)

        # Override FetchContent's base directory to share large deps among examples.
        # Uses the directory where ovrtx.cmake lives, ensuring all examples share the same _deps.
        # If copying this project to your own workspace, delete this line or override it.
        if(NOT DEFINED CACHE{FETCHCONTENT_BASE_DIR})
            set(FETCHCONTENT_BASE_DIR "${_OVRTX_CMAKE_DIR}/_deps" CACHE PATH "Shared FetchContent directory")
        endif()

        # Platform-specific package selection
        if(CMAKE_SYSTEM_NAME STREQUAL "Windows")
            set(OVRTX_PACKAGE_SYSTEM "windows-x86_64")
            set(OVRTX_HASH "cecbc2bd727e0ce032bf1965b572bfb7084109d35b5ee42894f8d6d4e5cbac42")
        elseif(CMAKE_SYSTEM_NAME STREQUAL "Linux")
            if (CMAKE_SYSTEM_PROCESSOR STREQUAL "aarch64")
                set(OVRTX_PACKAGE_SYSTEM "manylinux_2_35_aarch64")
                set(OVRTX_HASH "159345c4b9467bad03989172de10742402419156050fbc4bf2cbe65af4efc2c8")
            elseif(CMAKE_SYSTEM_PROCESSOR STREQUAL "x86_64")
                set(OVRTX_PACKAGE_SYSTEM "manylinux_2_35_x86_64")
                set(OVRTX_HASH "4cd49249ad3a08f02c3bebaba5f88c6a117ef073b08e39b9220bbfc671cd88cd")
            else()
                message(FATAL_ERROR "Unsupported system: ${CMAKE_SYSTEM_NAME} ${CMAKE_SYSTEM_PROCESSOR}")
            endif()
        else()
            message(FATAL_ERROR "Unsupported system: ${CMAKE_SYSTEM_NAME} ${CMAKE_SYSTEM_PROCESSOR}")
        endif()

        include(FetchContent)

        # test override: consume a local package
        if(NOT OVRTX_LOCAL_PACKAGE AND DEFINED ENV{OVRTX_LOCAL_PACKAGE})
            set(OVRTX_LOCAL_PACKAGE "$ENV{OVRTX_LOCAL_PACKAGE}")
        endif()
        if(OVRTX_LOCAL_PACKAGE)
            message(STATUS "ovrtx: using local package ${OVRTX_LOCAL_PACKAGE}")
            FetchContent_Declare(
                ovrtx
                DOWNLOAD_EXTRACT_TIMESTAMP TRUE
                URL "${OVRTX_LOCAL_PACKAGE}"
            )
        else()
        FetchContent_Declare(
            ovrtx
            DOWNLOAD_EXTRACT_TIMESTAMP TRUE
            URL "https://github.com/NVIDIA-Omniverse/ovrtx/releases/download/v0.4.1/ovrtx@0.4.1.364340.7f330117.${OVRTX_PACKAGE_SYSTEM}.zip"
            URL_HASH SHA256=${OVRTX_HASH}
        )

        endif()

        FetchContent_MakeAvailable(ovrtx)

        # Make ovrtx findable by find_package
        list(APPEND CMAKE_PREFIX_PATH ${ovrtx_SOURCE_DIR})

        find_package(ovrtx REQUIRED)

    endif()
endmacro()
# [/snippet:ovrtx_fetch]

# Detect whether TARGET links the static ovrtx loader (model #1). Both
# ovrtx_setup_runtime and ovstage_setup_runtime branch on this: only under model #1
# does ovrtx leave the exe root free (its runtime lives under the single ovrtx/
# link), which changes how ovstage stages its own plugins/.
#
# Detection is by DIRECT link: the examples all `target_link_libraries(<tgt>
# PRIVATE ovrtx::ovrtx_static ...)` before calling *_setup_runtime, so the target
# name shows up in LINK_LIBRARIES. A consumer that pulls the static loader only
# transitively should link it directly (or split its own setup) so the model is
# unambiguous.
function(_ovrtx_target_uses_static_loader TARGET_NAME OUT_VAR)
    get_target_property(_libs ${TARGET_NAME} LINK_LIBRARIES)
    if(_libs AND "ovrtx::ovrtx_static" IN_LIST _libs)
        set(${OUT_VAR} TRUE PARENT_SCOPE)
    else()
        set(${OUT_VAR} FALSE PARENT_SCOPE)
    endif()
endfunction()

# Emit a POST_BUILD command that (re)creates LINK_PATH as a Windows directory
# junction pointing at TARGET_PATH. It refreshes a stale junction (so a changed
# package path or a switch between linking models is picked up) and fails clearly
# if a real, non-junction file/dir already occupies LINK_PATH instead of silently
# leaving it (or letting New-Item throw a cryptic error). Windows-only; Linux uses
# symlinks/rpath directly.
function(_ovrtx_add_dir_junction TARGET_NAME LINK_PATH TARGET_PATH COMMENT_TEXT)
    add_custom_command(TARGET ${TARGET_NAME} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E env powershell -NoProfile -Command
            "$link='${LINK_PATH}'; $i=Get-Item $link -Force -ErrorAction SilentlyContinue; if ($i) { if ($i.LinkType -eq 'Junction') { $i.Delete() } else { Write-Error 'link path exists and is not a junction; remove it and rebuild'; exit 1 } }; New-Item -ItemType Junction -Path $link -Target '${TARGET_PATH}' | Out-Null"
        COMMENT "${COMMENT_TEXT}"
    )
endfunction()

# Setup ovrtx runtime consumption for a target. Supports both linking models,
# selected automatically from whether TARGET links ovrtx::ovrtx_static:
#
#  * Model #1 (STATIC loader, ovrtx::ovrtx_static). The loader has no built-in
#    notion of where the package lives, so the app passes the "binary package
#    root" to ovrtx_create_renderer via ovrtx_config_entry_binary_package_root_path()
#    and the loader resolves ovrtx-dynamic and all runtime resources relative to it.
#    To keep the exe dir self-contained without baking an absolute path into the
#    binary, we expose the package as a SINGLE link `ovrtx/` next to the exe
#    (junction on Windows, symlink on Linux) -> the package bin/, which main.cpp
#    resolves at runtime as <dir of exe>/ovrtx.
#
#  * Model #2 (DYNAMIC, ovrtx::ovrtx). ovrtx-dynamic.(dll|so) is resolved by the
#    OS loader beside the exe, so we replicate the package there: copy the root
#    DLLs and junction the runtime dirs (Windows), or set rpath (Linux).
#
# OVRTX_BINARY_DIR is the package bin/ dir (exported by ovrtxConfig.cmake) where
# ovrtx-dynamic lives, i.e. the root the loader expects.
function(ovrtx_setup_runtime TARGET_NAME)
    if(NOT DEFINED OVRTX_BINARY_DIR)
        message(FATAL_ERROR "OVRTX_BINARY_DIR is not set; call ovrtx_fetch() before ovrtx_setup_runtime()")
    endif()

    _ovrtx_target_uses_static_loader(${TARGET_NAME} _ovrtx_static_model)

    if(_ovrtx_static_model)
        # Model #1: a single link to the package bin; main.cpp passes <exe>/ovrtx.
        if(CMAKE_SYSTEM_NAME STREQUAL "Windows")
            _ovrtx_add_dir_junction(${TARGET_NAME}
                "$<TARGET_FILE_DIR:${TARGET_NAME}>/ovrtx" "${OVRTX_BINARY_DIR}"
                "Junctioning the ovrtx package bin beside the exe as ovrtx/")
        else()
            # -sfnT replaces an existing symlink in place and refuses to descend
            # into a real directory named ovrtx, keeping rebuilds idempotent.
            add_custom_command(TARGET ${TARGET_NAME} POST_BUILD
                COMMAND ln -sfnT "${OVRTX_BINARY_DIR}" "$<TARGET_FILE_DIR:${TARGET_NAME}>/ovrtx"
                COMMENT "Symlinking the ovrtx package bin beside the exe as ovrtx/"
            )
        endif()
    else()
        # Model #2: replicate the package next to the exe (dynamic loader anchor).
        if(CMAKE_SYSTEM_NAME STREQUAL "Windows")
            file(GLOB OVRTX_PACKAGE_ROOT_DLLS CONFIGURE_DEPENDS "${OVRTX_BINARY_DIR}/*.dll")
            if(NOT OVRTX_PACKAGE_ROOT_DLLS)
                message(FATAL_ERROR "No ovrtx package root DLLs found in ${OVRTX_BINARY_DIR}")
            endif()
            add_custom_command(TARGET ${TARGET_NAME} POST_BUILD
                COMMAND ${CMAKE_COMMAND} -E copy_if_different
                    ${OVRTX_PACKAGE_ROOT_DLLS}
                    "$<TARGET_FILE_DIR:${TARGET_NAME}>"
                COMMENT "Copying ovrtx package root DLLs to build directory"
            )
            set(OVRTX_RUNTIME_DIRS cache library libs mdl plugins rendering-data usd_plugins)
            foreach(DIR ${OVRTX_RUNTIME_DIRS})
                _ovrtx_add_dir_junction(${TARGET_NAME}
                    "$<TARGET_FILE_DIR:${TARGET_NAME}>/${DIR}" "${OVRTX_BINARY_DIR}/${DIR}"
                    "Junctioning ovrtx ${DIR} beside the exe")
            endforeach()
        else()
            set_target_properties(${TARGET_NAME} PROPERTIES
                BUILD_RPATH "${OVRTX_BINARY_DIR}"
                INSTALL_RPATH "${OVRTX_BINARY_DIR}"
            )
        endif()
    endif()
endfunction()
