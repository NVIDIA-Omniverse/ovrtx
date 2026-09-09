// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include <gtest/gtest.h>
#include "cuda/cuda_kernel.hpp"

class CudaKernelTest : public ::testing::Test {
protected:
    static CUuuid cuda_uuid;
    static bool cuda_initialized;
    static bool kernel_compiled;
    
    static void SetUpTestSuite() {
        // Initialize CUDA once for all tests
        if (!cuda_initialized) {
            cuda_initialized = cuda_init_standalone(0, &cuda_uuid);
        }
        if (cuda_initialized && !kernel_compiled) {
            kernel_compiled = cuda_compile_kernel();
        }
    }
    
    static void TearDownTestSuite() {
        if (cuda_initialized) {
            cuda_cleanup();
            cuda_initialized = false;
            kernel_compiled = false;
        }
    }
};

CUuuid CudaKernelTest::cuda_uuid = {};
bool CudaKernelTest::cuda_initialized = false;
bool CudaKernelTest::kernel_compiled = false;

TEST_F(CudaKernelTest, CudaInitSucceeds) {
    EXPECT_TRUE(cuda_initialized);
}

TEST_F(CudaKernelTest, CudaUuidIsNonZero) {
    ASSERT_TRUE(cuda_initialized);
    
    // Check that UUID is not all zeros
    bool all_zero = true;
    for (int i = 0; i < 16; ++i) {
        if (cuda_uuid.bytes[i] != 0) {
            all_zero = false;
            break;
        }
    }
    EXPECT_FALSE(all_zero) << "CUDA UUID should not be all zeros";
}

TEST_F(CudaKernelTest, CudaUuidUsesMigAwareDriverIdentity) {
    ASSERT_TRUE(cuda_initialized);

    CUdevice device;
    ASSERT_EQ(cuCtxGetDevice(&device), CUDA_SUCCESS);

    CUuuid mig_aware_uuid = {};
    ASSERT_EQ(cuDeviceGetUuid_v2(&mig_aware_uuid, device), CUDA_SUCCESS);
    EXPECT_EQ(memcmp(cuda_uuid.bytes, mig_aware_uuid.bytes, sizeof(cuda_uuid.bytes)), 0)
        << "CUDA/Vulkan matching must use the MIG-aware CUDA device UUID";
}

TEST_F(CudaKernelTest, KernelCompilationSucceeds) {
    ASSERT_TRUE(cuda_initialized);
    EXPECT_TRUE(kernel_compiled);
}

TEST_F(CudaKernelTest, StreamCreationWorks) {
    ASSERT_TRUE(cuda_initialized);
    
    CUstream stream;
    CUresult result = cuStreamCreate(&stream, 0);
    EXPECT_EQ(result, CUDA_SUCCESS);
    
    if (result == CUDA_SUCCESS) {
        cuStreamDestroy(stream);
    }
}

TEST_F(CudaKernelTest, EventCreationWorks) {
    ASSERT_TRUE(cuda_initialized);
    
    CUevent event;
    CUresult result = cuEventCreate(&event, CU_EVENT_DEFAULT);
    EXPECT_EQ(result, CUDA_SUCCESS);
    
    if (result == CUDA_SUCCESS) {
        cuEventDestroy(event);
    }
}

TEST_F(CudaKernelTest, ContextIsValid) {
    ASSERT_TRUE(cuda_initialized);
    
    CUcontext ctx;
    CUresult result = cuCtxGetCurrent(&ctx);
    EXPECT_EQ(result, CUDA_SUCCESS);
    EXPECT_NE(ctx, nullptr);
}

TEST_F(CudaKernelTest, DevicePropertiesAreAccessible) {
    ASSERT_TRUE(cuda_initialized);
    
    CUdevice device;
    CUresult result = cuCtxGetDevice(&device);
    EXPECT_EQ(result, CUDA_SUCCESS);
    
    char name[256];
    result = cuDeviceGetName(name, sizeof(name), device);
    EXPECT_EQ(result, CUDA_SUCCESS);
    EXPECT_GT(strlen(name), 0u);
}

TEST_F(CudaKernelTest, ComputeCapabilityIsValid) {
    ASSERT_TRUE(cuda_initialized);
    
    CUdevice device;
    cuCtxGetDevice(&device);
    
    int major, minor;
    CUresult result1 = cuDeviceGetAttribute(&major, CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MAJOR, device);
    CUresult result2 = cuDeviceGetAttribute(&minor, CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MINOR, device);
    
    EXPECT_EQ(result1, CUDA_SUCCESS);
    EXPECT_EQ(result2, CUDA_SUCCESS);
    EXPECT_GE(major, 5) << "Compute capability should be at least 5.x";
}

TEST_F(CudaKernelTest, MemoryAllocationWorks) {
    ASSERT_TRUE(cuda_initialized);
    
    CUdeviceptr ptr;
    size_t size = 1024;
    
    CUresult result = cuMemAlloc(&ptr, size);
    EXPECT_EQ(result, CUDA_SUCCESS);
    EXPECT_NE(ptr, 0u);
    
    if (result == CUDA_SUCCESS) {
        cuMemFree(ptr);
    }
}
