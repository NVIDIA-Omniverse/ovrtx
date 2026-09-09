// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

#include <cuda.h>
#include <cstdint>
#include <vector>

// Image format for CUDA-Vulkan interop
// Half4: 4 channels of 16-bit float (HdrColor) - 8 bytes per pixel
// UInt8_4: 4 channels of 8-bit unsigned int (LdrColor) - 4 bytes per pixel
enum class CudaImageFormat { Half4, UInt8_4 };

// Work around the Linux CUDA/Vulkan scheduling interaction by capping the CUDA
// driver's host-to-device connections. Must be called before the process creates
// its first CUDA context; no-op on platforms other than Linux.
void cuda_apply_scheduling_workaround();

// Resolve a process-visible CUDA device ordinal to its MIG-aware CUDA UUID.
bool cuda_get_device_uuid(int32_t device_id, CUuuid* out_uuid);

// Initialize CUDA Driver API using existing context (created by ovrtx) and return the device UUID
// Returns true on success, false on failure
bool cuda_init(int32_t device_id, CUuuid* out_uuid);

// Initialize CUDA Driver API by creating a new context (for tests without ovrtx)
// Returns true on success, false on failure
bool cuda_init_standalone(int32_t device_id, CUuuid* out_uuid);

// Compile the UV gradient kernel using NVRTC
// Must be called after cuda_init()
bool cuda_compile_kernel();

// Number of double-buffered images
constexpr int CUDA_SHARED_IMAGE_COUNT = 2;

// Import Vulkan external memory into CUDA at a specific buffer index
// Returns a CUDA surface object for writing
#ifdef _WIN32
CUsurfObject cuda_import_vulkan_image(
    int index,
    void* handle,
    size_t allocation_size,
    int width,
    int height,
    CudaImageFormat format
);

// Import Vulkan timeline semaphore into CUDA
void cuda_import_timeline_semaphore(void* handle);
#else
CUsurfObject cuda_import_vulkan_image(
    int index,
    int fd,
    size_t allocation_size,
    int width,
    int height,
    CudaImageFormat format
);

// Import Vulkan timeline semaphore into CUDA
void cuda_import_timeline_semaphore(int timeline_semaphore_fd);
#endif

// Query the current value of the timeline semaphore (non-blocking)
auto cuda_query_timeline_value() -> uint64_t;

// Signal the timeline semaphore with a specific value (async)
void cuda_signal_timeline(uint64_t value, CUstream stream);

// Run the UV gradient kernel
void cuda_run_gradient_kernel(
    CUsurfObject surface,
    int width,
    int height,
    CUstream stream
);

// Copy from linear CUDA memory to the imported Vulkan surface
// buffer_index: which double-buffer slot to write to (0 or 1)
// src_ptr: source device pointer (linear memory)
// src_pitch: row pitch in bytes of source
// width, height: dimensions in pixels
// stream: CUDA stream to use
void cuda_copy_to_surface(
    int buffer_index,
    CUdeviceptr src_ptr,
    int src_pitch,
    int width,
    int height,
    CUstream stream
);

// Copy from CUDA array to the imported Vulkan surface (array-to-array)
// buffer_index: which double-buffer slot to write to (0 or 1)
// src_array: source CUDA array
// width, height: dimensions in pixels
// format: pixel format (determines bytes per pixel)
// stream: CUDA stream to use
void cuda_copy_array_to_surface(
    int buffer_index,
    CUarray src_array,
    int width,
    int height,
    CudaImageFormat format,
    CUstream stream
);

// Wait on an external CUDA event before proceeding
void cuda_wait_event(CUevent event, CUstream stream);


// Read back the shared image at buffer_index as sRGB RGBA8 pixels (for PNG output).
// Half4 (HdrColor, lin_rec709) data is converted to sRGB.
// UInt8_4 (LdrColor) data is already sRGB and is copied directly.
// Returns a vector of width*height*4 bytes.
std::vector<uint8_t> cuda_read_surface_rgba8(
    int buffer_index, int width, int height, CudaImageFormat format);

// Cleanup CUDA resources
void cuda_cleanup();
