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
#include <memory>
#include "cuda/cuda_kernel.hpp"
#include "vk/vulkan_context.hpp"
#include "validation_tracker.hpp"

constexpr int TEST_TEX_WIDTH = 256;
constexpr int TEST_TEX_HEIGHT = 256;
constexpr int SHARED_IMAGE_COUNT = 2;

class CudaInteropTest : public ::testing::Test {
protected:
    static CUuuid cuda_uuid;
    static bool cuda_initialized;
    static std::unique_ptr<VulkanContext> vk;
    static SampledImageHandle shared_images[SHARED_IMAGE_COUNT];
    
    static void SetUpTestSuite() {
        cuda_initialized = cuda_init_standalone(0, &cuda_uuid);
        ASSERT_TRUE(cuda_initialized) << "Failed to initialize CUDA";
        
        VulkanContextConfig config;
        config.window = nullptr;  // headless mode
        config.initial_sampled_image_capacity = 8;
        config.debug_callback = ValidationTracker::instance().callback();
        
        vk = std::make_unique<VulkanContext>(config, cuda_uuid);
        
        // Create exportable shared images
        for (int i = 0; i < SHARED_IMAGE_COUNT; ++i) {
            shared_images[i] = vk->create_sampled_image(TEST_TEX_WIDTH, TEST_TEX_HEIGHT,
                                                         VK_FORMAT_R16G16B16A16_SFLOAT,
                                                         VK_FILTER_LINEAR,
                                                         true);  // exportable
        }
    }
    
    static void TearDownTestSuite() {
        vk.reset();
        if (cuda_initialized) {
            cuda_cleanup();
        }
    }
    
    void TearDown() override {
        ValidationTracker::instance().check_and_clear();
    }
};

CUuuid CudaInteropTest::cuda_uuid = {};
bool CudaInteropTest::cuda_initialized = false;
std::unique_ptr<VulkanContext> CudaInteropTest::vk;
SampledImageHandle CudaInteropTest::shared_images[SHARED_IMAGE_COUNT] = {};

TEST_F(CudaInteropTest, ExportMemoryHandleReturnsValidHandle) {
    auto handle = vk->export_memory_handle(shared_images[0]);
#ifdef _WIN32
    EXPECT_NE(handle, nullptr) << "Memory handle should be non-null";
#else
    EXPECT_GE(handle, 0) << "Memory file descriptor should be non-negative";
#endif
}

TEST_F(CudaInteropTest, ExportTimelineSemaphoreHandleReturnsValidHandle) {
    auto handle = vk->export_timeline_semaphore_handle();
#ifdef _WIN32
    EXPECT_NE(handle, nullptr) << "Timeline semaphore handle should be non-null";
#else
    EXPECT_GE(handle, 0) << "Timeline semaphore file descriptor should be non-negative";
#endif
}

TEST_F(CudaInteropTest, CanImportVulkanImageIntoCuda) {
    SampledImage const& img = vk->sampled_image(shared_images[0]);
    vk->immediate_submit([&img](CommandBuffer cmd) {
        cmd.image_memory_barrier(img.image, VK_IMAGE_ASPECT_COLOR_BIT,
                                 VK_IMAGE_LAYOUT_UNDEFINED, VK_PIPELINE_STAGE_2_TOP_OF_PIPE_BIT, VK_ACCESS_2_NONE,
                                 VK_IMAGE_LAYOUT_GENERAL, VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_WRITE_BIT);
    });
    
    auto memory_handle = vk->export_memory_handle(shared_images[0]);
    VkDeviceSize memory_size = img.size;
    
    CUsurfObject surface = cuda_import_vulkan_image(0, memory_handle, memory_size, TEST_TEX_WIDTH, TEST_TEX_HEIGHT, CudaImageFormat::Half4);
    
    EXPECT_NE(surface, 0u) << "CUDA surface object should be non-zero";
}

TEST_F(CudaInteropTest, CanImportTimelineSemaphoreIntoCuda) {
    auto timeline_handle = vk->export_timeline_semaphore_handle();
    
    // Should not throw
    ASSERT_NO_THROW({
        cuda_import_timeline_semaphore(timeline_handle);
    });
}

TEST_F(CudaInteropTest, CanImportBothSharedImages) {
    // Test that we can import both double-buffered images
    for (int i = 0; i < SHARED_IMAGE_COUNT; ++i) {
        SampledImage const& img = vk->sampled_image(shared_images[i]);
        vk->immediate_submit([&img](CommandBuffer cmd) {
            cmd.image_memory_barrier(img.image, VK_IMAGE_ASPECT_COLOR_BIT,
                                     VK_IMAGE_LAYOUT_UNDEFINED, VK_PIPELINE_STAGE_2_TOP_OF_PIPE_BIT, VK_ACCESS_2_NONE,
                                     VK_IMAGE_LAYOUT_GENERAL, VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_WRITE_BIT);
        });
        
        auto memory_handle = vk->export_memory_handle(shared_images[i]);
        VkDeviceSize memory_size = img.size;
        
        CUsurfObject surface = cuda_import_vulkan_image(i, memory_handle, memory_size, TEST_TEX_WIDTH, TEST_TEX_HEIGHT, CudaImageFormat::Half4);
        
        EXPECT_NE(surface, 0u) << "CUDA surface object for buffer " << i << " should be non-zero";
    }
}

TEST_F(CudaInteropTest, CanRunGradientKernel) {
    // Compile the kernel if not already compiled
    if (!cuda_compile_kernel()) {
        GTEST_SKIP() << "CUDA kernel compilation not available";
    }
    
    // Import image and run kernel
    SampledImage const& img = vk->sampled_image(shared_images[0]);
    auto memory_handle = vk->export_memory_handle(shared_images[0]);
    
    CUsurfObject surface = cuda_import_vulkan_image(0, memory_handle, img.size, TEST_TEX_WIDTH, TEST_TEX_HEIGHT, CudaImageFormat::Half4);
    ASSERT_NE(surface, 0u) << "Failed to import Vulkan image";
    
    // Run the gradient kernel with default stream (nullptr) - should not crash
    ASSERT_NO_THROW({
        cuda_run_gradient_kernel(surface, TEST_TEX_WIDTH, TEST_TEX_HEIGHT, nullptr);
        cuCtxSynchronize();  // Sync default stream
    });
}

TEST_F(CudaInteropTest, KernelRunsMultipleTimes) {
    // Compile the kernel if not already compiled
    if (!cuda_compile_kernel()) {
        GTEST_SKIP() << "CUDA kernel compilation not available";
    }
    
    // Import images and store surfaces
    CUsurfObject surfaces[SHARED_IMAGE_COUNT] = {};
    for (int i = 0; i < SHARED_IMAGE_COUNT; ++i) {
        SampledImage const& img = vk->sampled_image(shared_images[i]);
        auto memory_handle = vk->export_memory_handle(shared_images[i]);
        surfaces[i] = cuda_import_vulkan_image(i, memory_handle, img.size, TEST_TEX_WIDTH, TEST_TEX_HEIGHT, CudaImageFormat::Half4);
        ASSERT_NE(surfaces[i], 0u) << "Failed to import Vulkan image " << i;
    }
    
    // Run kernel multiple times on different buffers
    for (int frame = 0; frame < 5; ++frame) {
        int buffer_idx = frame % SHARED_IMAGE_COUNT;
        ASSERT_NO_THROW({
            cuda_run_gradient_kernel(surfaces[buffer_idx], TEST_TEX_WIDTH, TEST_TEX_HEIGHT, nullptr);
            cuCtxSynchronize();  // Sync default stream
        }) << "Failed on frame " << frame;
    }
}

TEST_F(CudaInteropTest, SharedMemorySizeMatchesTextureSize) {
    VkDeviceSize memory_size = vk->sampled_image(shared_images[0]).size;
    
    // R16G16B16A16_SFLOAT = 8 bytes per pixel
    VkDeviceSize expected_min_size = TEST_TEX_WIDTH * TEST_TEX_HEIGHT * 8;
    
    EXPECT_GE(memory_size, expected_min_size) 
        << "Shared memory size should be at least " << expected_min_size << " bytes";
}
