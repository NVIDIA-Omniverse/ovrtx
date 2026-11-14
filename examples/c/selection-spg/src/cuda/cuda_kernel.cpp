// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "cuda_kernel.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <vector>

// Global state for CUDA Driver API
static CUdevice g_device = 0;
static CUcontext g_context = nullptr;

// Double-buffered image state imported from Vulkan export handles.
// Each index corresponds to one ping-pong buffer used by main.cpp.
static CUexternalMemory g_external_memory[CUDA_SHARED_IMAGE_COUNT] = {};
static CUmipmappedArray g_mipmap_array[CUDA_SHARED_IMAGE_COUNT] = {};
static CUarray g_cuda_array[CUDA_SHARED_IMAGE_COUNT] = {};

// CUDA-visible handle to Vulkan timeline semaphore used for producer->consumer
// ordering without CPU blocking.
static CUexternalSemaphore g_timeline_semaphore = nullptr;

#define CU_CHECK(call)                                                           \
    do {                                                                         \
        CUresult result = call;                                                  \
        if (result != CUDA_SUCCESS) {                                            \
            const char* err_str;                                                 \
            cuGetErrorString(result, &err_str);                                  \
            fprintf(stderr, "CUDA Driver error at %s:%d: %s\n",                  \
                    __FILE__, __LINE__, err_str);                                \
            return false;                                                        \
        }                                                                        \
    } while (0)

#define CU_CHECK_VOID(call)                                                      \
    do {                                                                         \
        CUresult result = call;                                                  \
        if (result != CUDA_SUCCESS) {                                            \
            const char* err_str;                                                 \
            cuGetErrorString(result, &err_str);                                  \
            fprintf(stderr, "CUDA Driver error at %s:%d: %s\n",                  \
                    __FILE__, __LINE__, err_str);                                \
            return;                                                              \
        }                                                                        \
    } while (0)

// [snippet:cuda-device-max-connections]
// On Linux, a stream-ordered CUDA wait that is outstanding while the renderer
// submits Vulkan work on the same device disturbs how that Vulkan work is
// scheduled. Capping the driver's host-to-device connections at one makes
// submissions across CUDA streams serialize in submission order, which stops
// them forming unintended hardware dependencies against the concurrent graphics
// work. Windows is unaffected, and the lost stream concurrency would be pure
// cost there.
//
// The driver reads the variable when it initializes, so this has to run before
// the process creates its first CUDA context. In this sample that context comes
// from ovrtx_create_renderer(), so the call site is the first statement of
// main(). An externally supplied value always wins, which is how a caller opts
// out without rebuilding.
void cuda_apply_scheduling_workaround() {
#if defined(__linux__)
    char const* const env_var = "CUDA_DEVICE_MAX_CONNECTIONS";

    if (char const* existing = getenv(env_var)) {
        fprintf(stderr, "%s=%s from the environment; leaving it unchanged\n", env_var, existing);
        return;
    }

    if (setenv(env_var, "1", 0) != 0) {
        fprintf(stderr,
                "Failed to set %s; CUDA waits may stall the renderer's Vulkan work\n",
                env_var);
        return;
    }

    fprintf(stderr, "%s=1 applied for CUDA/Vulkan scheduling on Linux\n", env_var);
#endif
}
// [/snippet:cuda-device-max-connections]

// [snippet:resolve-cuda-device-uuid]
bool cuda_get_device_uuid(int32_t device_id, CUuuid* out_uuid) {
    if (!out_uuid) {
        fprintf(stderr, "cuda_get_device_uuid: out_uuid must not be null\n");
        return false;
    }

    CU_CHECK(cuInit(0));

    CUdevice device;
    CU_CHECK(cuDeviceGet(&device, device_id));

    // Unlike the legacy entry point, cuDeviceGetUuid_v2 returns the subscribed
    // MIG compute-instance UUID when device is a MIG device.
    CU_CHECK(cuDeviceGetUuid_v2(out_uuid, device));
    return true;
}
// [/snippet:resolve-cuda-device-uuid]

bool cuda_init(int32_t device_id, CUuuid* out_uuid) {
    // Reuse the context that ovrtx already initialized so mapped ovrtx arrays and
    // imported Vulkan memory are visible in the same CUDA context.
    CU_CHECK(cuCtxGetCurrent(&g_context));

    if (!g_context) {
        fprintf(stderr, "No CUDA context found. Make sure ovrtx is initialized first.\n");
        return false;
    }

    // Confirm the ovrtx-created context uses the configured CUDA ordinal.
    CUdevice context_device;
    CU_CHECK(cuCtxGetDevice(&context_device));
    CU_CHECK(cuDeviceGet(&g_device, device_id));
    if (context_device != g_device) {
        fprintf(stderr,
                "ovrtx CUDA context is on device %d, expected configured device %d\n",
                context_device,
                g_device);
        return false;
    }

    // Get device name
    char device_name[256];
    CU_CHECK(cuDeviceGetName(device_name, sizeof(device_name), g_device));
    printf("CUDA device: %s\n", device_name);

    if (!cuda_get_device_uuid(device_id, out_uuid)) {
        return false;
    }

    return true;
}

// Helper function to complete import after external memory is created
static CUsurfObject cuda_import_vulkan_image_finish(
    int index,
    int width,
    int height,
    CudaImageFormat format
) {
    // Map imported VkDeviceMemory as a CUDA array. This sample always maps a
    // single mip level and writes via surface operations.
    CUDA_EXTERNAL_MEMORY_MIPMAPPED_ARRAY_DESC mipmap_desc = {};
    mipmap_desc.offset = 0;
    mipmap_desc.arrayDesc.Width = width;
    mipmap_desc.arrayDesc.Height = height;
    mipmap_desc.arrayDesc.Depth = 0;
    mipmap_desc.arrayDesc.Format = (format == CudaImageFormat::Half4)
        ? CU_AD_FORMAT_HALF
        : CU_AD_FORMAT_UNSIGNED_INT8;
    mipmap_desc.arrayDesc.NumChannels = 4;
    mipmap_desc.arrayDesc.Flags = CUDA_ARRAY3D_SURFACE_LDST;
    mipmap_desc.numLevels = 1;

    CUresult err = cuExternalMemoryGetMappedMipmappedArray(&g_mipmap_array[index], g_external_memory[index], &mipmap_desc);
    if (err != CUDA_SUCCESS) {
        const char* err_str;
        cuGetErrorString(err, &err_str);
        fprintf(stderr, "Failed to map mipmapped array for buffer %d: %s\n", index, err_str);
        return 0;
    }

    // Get level 0
    err = cuMipmappedArrayGetLevel(&g_cuda_array[index], g_mipmap_array[index], 0);
    if (err != CUDA_SUCCESS) {
        const char* err_str;
        cuGetErrorString(err, &err_str);
        fprintf(stderr, "Failed to get mipmap level for buffer %d: %s\n", index, err_str);
        return 0;
    }

    // Surface object gives kernels/copies a typed write target abstraction over
    // imported image memory.
    CUDA_RESOURCE_DESC res_desc = {};
    res_desc.resType = CU_RESOURCE_TYPE_ARRAY;
    res_desc.res.array.hArray = g_cuda_array[index];

    CUsurfObject surface = 0;
    err = cuSurfObjectCreate(&surface, &res_desc);
    if (err != CUDA_SUCCESS) {
        const char* err_str;
        cuGetErrorString(err, &err_str);
        fprintf(stderr, "Failed to create surface object for buffer %d: %s\n", index, err_str);
        return 0;
    }

    char const* format_str = (format == CudaImageFormat::Half4) ? "Half4" : "UInt8_4";
    printf("Imported Vulkan image %d into CUDA: %dx%d (%s)\n", index, width, height, format_str);
    return surface;
}

#ifdef _WIN32
CUsurfObject cuda_import_vulkan_image(
    int index,
    void* handle,
    size_t allocation_size,
    int width,
    int height,
    CudaImageFormat format
) {
    if (index < 0 || index >= CUDA_SHARED_IMAGE_COUNT) {
        fprintf(stderr, "Invalid buffer index: %d\n", index);
        return 0;
    }

    // Import external memory from Vulkan (Windows)
    CUDA_EXTERNAL_MEMORY_HANDLE_DESC ext_mem_desc = {};
    ext_mem_desc.type = CU_EXTERNAL_MEMORY_HANDLE_TYPE_OPAQUE_WIN32;
    ext_mem_desc.handle.win32.handle = handle;
    ext_mem_desc.size = allocation_size;
    ext_mem_desc.flags = 0;

    CUresult err = cuImportExternalMemory(&g_external_memory[index], &ext_mem_desc);
    if (err != CUDA_SUCCESS) {
        const char* err_str;
        cuGetErrorString(err, &err_str);
        fprintf(stderr, "Failed to import external memory for buffer %d: %s\n", index, err_str);
        return 0;
    }

    return cuda_import_vulkan_image_finish(index, width, height, format);
}

bool cuda_import_timeline_semaphore(void* handle) {
    // Use explicit timeline semaphore handle type so CUDA can signal counter
    // values that Vulkan waits on during submit.
    CUDA_EXTERNAL_SEMAPHORE_HANDLE_DESC sem_desc = {};
    sem_desc.type = CU_EXTERNAL_SEMAPHORE_HANDLE_TYPE_TIMELINE_SEMAPHORE_WIN32;
    sem_desc.handle.win32.handle = handle;
    sem_desc.flags = 0;

    CU_CHECK(cuImportExternalSemaphore(&g_timeline_semaphore, &sem_desc));
    printf("Imported Vulkan timeline semaphore into CUDA\n");
    return true;
}
#else
CUsurfObject cuda_import_vulkan_image(
    int index,
    int fd,
    size_t allocation_size,
    int width,
    int height,
    CudaImageFormat format
) {
    if (index < 0 || index >= CUDA_SHARED_IMAGE_COUNT) {
        fprintf(stderr, "Invalid buffer index: %d\n", index);
        return 0;
    }

    // Import external memory from Vulkan (Linux)
    CUDA_EXTERNAL_MEMORY_HANDLE_DESC ext_mem_desc = {};
    ext_mem_desc.type = CU_EXTERNAL_MEMORY_HANDLE_TYPE_OPAQUE_FD;
    ext_mem_desc.handle.fd = fd;
    ext_mem_desc.size = allocation_size;
    ext_mem_desc.flags = 0;

    CUresult err = cuImportExternalMemory(&g_external_memory[index], &ext_mem_desc);
    if (err != CUDA_SUCCESS) {
        const char* err_str;
        cuGetErrorString(err, &err_str);
        fprintf(stderr, "Failed to import external memory for buffer %d: %s\n", index, err_str);
        return 0;
    }

    return cuda_import_vulkan_image_finish(index, width, height, format);
}

bool cuda_import_timeline_semaphore(int timeline_semaphore_fd) {
    // Must use timeline semaphore FD type (not opaque FD), otherwise CUDA
    // cannot signal monotonically increasing fence values for Vulkan waits.
    CUDA_EXTERNAL_SEMAPHORE_HANDLE_DESC sem_desc = {};
    sem_desc.type = CU_EXTERNAL_SEMAPHORE_HANDLE_TYPE_TIMELINE_SEMAPHORE_FD;
    sem_desc.handle.fd = timeline_semaphore_fd;
    sem_desc.flags = 0;

    CU_CHECK(cuImportExternalSemaphore(&g_timeline_semaphore, &sem_desc));
    printf("Imported Vulkan timeline semaphore into CUDA\n");
    return true;
}
#endif

bool cuda_signal_timeline(uint64_t value, CUstream stream) {
    if (!g_timeline_semaphore) {
        fprintf(stderr, "cuda_signal_timeline: timeline semaphore not imported\n");
        return false;
    }

    // Signal happens on the CUDA stream so it is ordered after queued copies.
    CUDA_EXTERNAL_SEMAPHORE_SIGNAL_PARAMS params = {};
    params.params.fence.value = value;
    params.flags = 0;

    CU_CHECK(cuSignalExternalSemaphoresAsync(&g_timeline_semaphore, &params, 1, stream));
    return true;
}

bool cuda_copy_array_to_surface(
    int buffer_index,
    CUarray src_array,
    int width,
    int height,
    CudaImageFormat format,
    CUstream stream
) {
    if (buffer_index < 0 || buffer_index >= CUDA_SHARED_IMAGE_COUNT) {
        fprintf(stderr, "cuda_copy_array_to_surface: invalid buffer index %d\n", buffer_index);
        return false;
    }

    if (!g_cuda_array[buffer_index]) {
        fprintf(stderr, "cuda_copy_array_to_surface: no destination CUDA array for buffer %d\n", buffer_index);
        return false;
    }

    if (!src_array) {
        fprintf(stderr, "cuda_copy_array_to_surface: no source CUDA array provided\n");
        return false;
    }

    // ovrtx output and imported Vulkan targets are both CUDA arrays; array->array
    // copy avoids intermediate linear allocations and preserves GPU locality.
    CUDA_MEMCPY2D copy_params = {};
    copy_params.srcMemoryType = CU_MEMORYTYPE_ARRAY;
    copy_params.srcArray = src_array;
    copy_params.srcXInBytes = 0;
    copy_params.srcY = 0;

    copy_params.dstMemoryType = CU_MEMORYTYPE_ARRAY;
    copy_params.dstArray = g_cuda_array[buffer_index];
    copy_params.dstXInBytes = 0;
    copy_params.dstY = 0;

    // ovrtx output type determines byte layout. WidthInBytes must match the
    // imported Vulkan format selected in main.cpp.
    int bytes_per_pixel = (format == CudaImageFormat::Half4) ? 8 : 4;
    copy_params.WidthInBytes = width * bytes_per_pixel;
    copy_params.Height = height;

    CUresult err = cuMemcpy2DAsync(&copy_params, stream);
    if (err != CUDA_SUCCESS) {
        char const* err_str;
        cuGetErrorString(err, &err_str);
        fprintf(stderr, "cuMemcpy2DAsync (array-to-array) to buffer %d failed: %s\n", buffer_index, err_str);
        return false;
    }
    return true;
}

void cuda_wait_event(CUevent event, CUstream stream) {
    if (!event) return;

    CUresult err = cuStreamWaitEvent(stream, event, 0);
    if (err != CUDA_SUCCESS) {
        char const* err_str;
        cuGetErrorString(err, &err_str);
        fprintf(stderr, "cuStreamWaitEvent failed: %s\n", err_str);
    }
}

// Convert IEEE 754 half-precision (uint16) to float
static float half_to_float(uint16_t h) {
    uint32_t sign = (h & 0x8000u) << 16;
    uint32_t exp = (h >> 10) & 0x1F;
    uint32_t frac = h & 0x03FF;

    if (exp == 0) {
        // Zero or subnormal
        if (frac == 0) {
            uint32_t bits = sign;
            float f;
            memcpy(&f, &bits, 4);
            return f;
        }
        // Subnormal: normalize
        exp = 1;
        while ((frac & 0x0400) == 0) {
            frac <<= 1;
            exp--;
        }
        frac &= 0x03FF;
        exp = exp + (127 - 15);
    } else if (exp == 31) {
        // Inf or NaN
        uint32_t bits = sign | 0x7F800000u | (frac << 13);
        float f;
        memcpy(&f, &bits, 4);
        return f;
    } else {
        exp = exp + (127 - 15);
    }

    uint32_t bits = sign | (exp << 23) | (frac << 13);
    float f;
    memcpy(&f, &bits, 4);
    return f;
}

// Apply sRGB OETF (linear to sRGB transfer function)
static float linear_to_srgb(float c) {
    if (c <= 0.0f) return 0.0f;
    if (c >= 1.0f) return 1.0f;
    if (c <= 0.0031308f) return 12.92f * c;
    return 1.055f * std::pow(c, 1.0f / 2.4f) - 0.055f;
}

std::vector<uint8_t> cuda_read_surface_rgba8(
    int buffer_index, int width, int height, CudaImageFormat format
) {
    std::vector<uint8_t> rgba8(width * height * 4);

    if (buffer_index < 0 || buffer_index >= CUDA_SHARED_IMAGE_COUNT) {
        fprintf(stderr, "cuda_read_surface_rgba8: invalid buffer index %d\n", buffer_index);
        return {};
    }
    if (!g_cuda_array[buffer_index]) {
        fprintf(stderr, "cuda_read_surface_rgba8: no CUDA array for buffer %d\n", buffer_index);
        return {};
    }

    int bytes_per_pixel = (format == CudaImageFormat::Half4) ? 8 : 4;
    std::vector<uint8_t> raw(width * height * bytes_per_pixel);

    CUDA_MEMCPY2D copy_params = {};
    copy_params.srcMemoryType = CU_MEMORYTYPE_ARRAY;
    copy_params.srcArray = g_cuda_array[buffer_index];
    copy_params.srcXInBytes = 0;
    copy_params.srcY = 0;
    copy_params.dstMemoryType = CU_MEMORYTYPE_HOST;
    copy_params.dstHost = raw.data();
    copy_params.dstPitch = width * bytes_per_pixel;
    copy_params.dstXInBytes = 0;
    copy_params.dstY = 0;
    copy_params.WidthInBytes = width * bytes_per_pixel;
    copy_params.Height = height;

    CUresult err = cuMemcpy2D(&copy_params);
    if (err != CUDA_SUCCESS) {
        char const* err_str;
        cuGetErrorString(err, &err_str);
        fprintf(stderr, "cuda_read_surface_rgba8: cuMemcpy2D failed: %s\n", err_str);
        return {};
    }

    if (format == CudaImageFormat::UInt8_4) {
        // LdrColor path already matches PNG target encoding closely.
        memcpy(rgba8.data(), raw.data(), rgba8.size());
    } else {
        // HdrColor path is half-float linear; convert to 8-bit sRGB for
        // conventional image viewing/output.
        uint16_t const* src = reinterpret_cast<uint16_t const*>(raw.data());
        for (int i = 0; i < width * height; ++i) {
            float r = half_to_float(src[i * 4 + 0]);
            float g = half_to_float(src[i * 4 + 1]);
            float b = half_to_float(src[i * 4 + 2]);
            float a = half_to_float(src[i * 4 + 3]);

            rgba8[i * 4 + 0] = static_cast<uint8_t>(linear_to_srgb(r) * 255.0f + 0.5f);
            rgba8[i * 4 + 1] = static_cast<uint8_t>(linear_to_srgb(g) * 255.0f + 0.5f);
            rgba8[i * 4 + 2] = static_cast<uint8_t>(linear_to_srgb(b) * 255.0f + 0.5f);
            // Alpha: clamp directly, no sRGB curve
            a = (a < 0.0f) ? 0.0f : (a > 1.0f) ? 1.0f : a;
            rgba8[i * 4 + 3] = static_cast<uint8_t>(a * 255.0f + 0.5f);
        }
    }

    return rgba8;
}

void cuda_cleanup() {
    if (g_timeline_semaphore) {
        cuDestroyExternalSemaphore(g_timeline_semaphore);
        g_timeline_semaphore = nullptr;
    }
    for (int i = 0; i < CUDA_SHARED_IMAGE_COUNT; ++i) {
        if (g_mipmap_array[i]) {
            cuMipmappedArrayDestroy(g_mipmap_array[i]);
            g_mipmap_array[i] = nullptr;
            g_cuda_array[i] = nullptr;
        }
        if (g_external_memory[i]) {
            cuDestroyExternalMemory(g_external_memory[i]);
            g_external_memory[i] = nullptr;
        }
    }
    g_context = nullptr;
}
