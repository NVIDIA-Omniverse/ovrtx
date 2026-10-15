# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

cmake_minimum_required(VERSION 3.18)
project(sensor-observer LANGUAGES CXX)

# Find required packages
find_package(CUDAToolkit REQUIRED)

find_package(Vulkan REQUIRED)
# Find glslc compiler (e.g. from the Vulkan SDK)
find_program(GLSLC_EXECUTABLE glslc
    HINTS
        $ENV{VULKAN_1_2_SDK_BIN}
)
if(GLSLC_EXECUTABLE)
    set(SHADER_COMPILER ${GLSLC_EXECUTABLE} -O --target-env=vulkan1.2 --target-spv=spv1.5)
else()
    find_program(GLSLANG_VALIDATOR glslangValidator REQUIRED)
    set(SHADER_COMPILER ${GLSLANG_VALIDATOR} -V --target-env vulkan1.2)
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Fetch ovrtx package
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../cmake")
include(ovrtx)
include(ovstage)
ovrtx_fetch()
ovstage_fetch()

# FetchContent for other dependencies
set(FETCHCONTENT_QUIET FALSE)
# Override FetchContent's base directory to share large deps among examples.
# If copying this project to your own workspace, delete this line or override it.
set(FETCHCONTENT_BASE_DIR "${CMAKE_CURRENT_LIST_DIR}/../_deps" CACHE PATH "")
include(FetchContent)

find_package(glfw3 QUIET)
if (glfw3_FOUND)
    message(STATUS "glfw3 found at: ${glfw3_DIR}")
else()
    message(STATUS "glfw3 not found. Building from source")
    FetchContent_Declare(
        glfw3
        DOWNLOAD_EXTRACT_TIMESTAMP TRUE
        URL https://github.com/glfw/glfw/releases/download/3.4/glfw-3.4.zip
    )
    FetchContent_MakeAvailable(glfw3)
endif()

# Download unordered_dense (header-only)
FetchContent_Declare(
    unordered_dense
    GIT_REPOSITORY https://github.com/martinus/unordered_dense.git
    GIT_TAG v4.4.0
    GIT_SHALLOW TRUE
)
FetchContent_MakeAvailable(unordered_dense)

# Download GLM
FetchContent_Declare(
    glm
    GIT_REPOSITORY https://github.com/g-truc/glm.git
    GIT_TAG 1.0.3
    GIT_SHALLOW TRUE
)
FetchContent_MakeAvailable(glm)

# Download volk (Vulkan meta-loader)
FetchContent_Declare(
    volk
    GIT_REPOSITORY https://github.com/zeux/volk.git
    GIT_TAG 1.4.304
    GIT_SHALLOW TRUE
)
FetchContent_MakeAvailable(volk)

# Shader source and output directories
# Reuse the CUDA/Vulkan plumbing from the interop example.
set(INTEROP_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../vulkan-interop)
set(SHADER_SOURCE_DIR ${INTEROP_DIR}/shaders)
set(SHADER_OUTPUT_DIR ${CMAKE_CURRENT_BINARY_DIR}/shaders)
file(MAKE_DIRECTORY ${SHADER_OUTPUT_DIR})

# Compile GLSL shaders to SPIR-V at build time
set(SHADER_SOURCES
    ${SHADER_SOURCE_DIR}/fullscreen.vert
    ${SHADER_SOURCE_DIR}/fullscreen.frag
)

foreach(SHADER_SOURCE ${SHADER_SOURCES})
    get_filename_component(SHADER_NAME ${SHADER_SOURCE} NAME)
    set(SHADER_OUTPUT ${SHADER_OUTPUT_DIR}/${SHADER_NAME}.spv)
    add_custom_command(
        OUTPUT ${SHADER_OUTPUT}
        COMMAND ${SHADER_COMPILER} ${SHADER_SOURCE} -o ${SHADER_OUTPUT}
        DEPENDS ${SHADER_SOURCE}
        COMMENT "Compiling ${SHADER_NAME} to SPIR-V"
        VERBATIM
    )
    list(APPEND SHADER_OUTPUTS ${SHADER_OUTPUT})
endforeach()

add_custom_target(sensor-observer-shaders DEPENDS ${SHADER_OUTPUTS})

# Main executable (using Driver API, no nvcc needed)
add_executable(sensor-observer
    main.cpp
    ${INTEROP_DIR}/src/cuda/cuda_kernel.cpp
    ${INTEROP_DIR}/src/vk/vulkan_context.cpp
    ${INTEROP_DIR}/src/vk/sampled_image.cpp
    ${INTEROP_DIR}/src/vk/shader.cpp
    ${INTEROP_DIR}/src/vk/command_buffer.cpp
    ${INTEROP_DIR}/src/camera/orbit_camera.cpp
)

add_dependencies(sensor-observer sensor-observer-shaders)

target_include_directories(sensor-observer PRIVATE
    ${INTEROP_DIR}/src
    ${Vulkan_INCLUDE_DIRS}
    ${CUDAToolkit_INCLUDE_DIRS}
    ${unordered_dense_SOURCE_DIR}/include
)

target_link_libraries(sensor-observer PRIVATE
    Vulkan::Vulkan
    glfw
    CUDA::cuda_driver
    CUDA::nvrtc
    glm::glm
    volk
    # Static-loader model: link the static ovrtx loader. main.cpp hands the loader
    # its package root at runtime (a side-by-side `ovrtx/` link beside the exe,
    # created by ovrtx_setup_runtime) instead of replicating the package next to it.
    ovrtx::ovrtx_static
    ovstage::ovstage_static
)

target_compile_definitions(sensor-observer PRIVATE
    SENSOR_OBSERVER_SCENE="${CMAKE_CURRENT_SOURCE_DIR}/conveyor.usda"
)

# The ovrtx package ships a release-only static loader (compiled /MD). Force the
# release CRT so the Debug config links cleanly.
if(MSVC)
    set_target_properties(sensor-observer PROPERTIES MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")
endif()

# Copy compiled shaders next to the executable so they can be found regardless
# of working directory. Uses generator expressions to handle both single-config
# (Ninja/Make) and multi-config (MSVC) generators correctly.
add_custom_command(TARGET sensor-observer POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:sensor-observer>/shaders"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        ${SHADER_OUTPUTS}
        "$<TARGET_FILE_DIR:sensor-observer>/shaders/"
    COMMENT "Copying compiled shaders next to executable"
)

# Setup runtime dependencies (DLL copying, junctions, rpath)
ovrtx_setup_runtime(sensor-observer)
ovstage_setup_runtime(sensor-observer)

# The headless executable checks capture cadence and the zero-time clock contract.
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    enable_testing()
    foreach(OBSERVER_STEPS 0 2)
        add_test(NAME sensor-observer-cadence-${OBSERVER_STEPS}
            COMMAND sensor-observer --headless --num-steps 30 --observer-steps ${OBSERVER_STEPS}
                --png ${CMAKE_CURRENT_BINARY_DIR}/observer-${OBSERVER_STEPS}.png
                --report ${CMAKE_CURRENT_BINARY_DIR}/observer-${OBSERVER_STEPS}.csv)
        set_tests_properties(sensor-observer-cadence-${OBSERVER_STEPS} PROPERTIES TIMEOUT 600 RUN_SERIAL TRUE)
    endforeach()
endif()
