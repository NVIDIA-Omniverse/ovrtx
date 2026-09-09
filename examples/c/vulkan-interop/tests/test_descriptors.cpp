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

class DescriptorTest : public ::testing::Test {
protected:
    static CUuuid cuda_uuid;
    static bool cuda_initialized;
    static std::unique_ptr<VulkanContext> vk;
    
    static void SetUpTestSuite() {
        cuda_initialized = cuda_init_standalone(0, &cuda_uuid);
        ASSERT_TRUE(cuda_initialized) << "Failed to initialize CUDA";
        
        VulkanContextConfig config;
        config.window = nullptr;  // headless mode
        config.initial_sampled_image_capacity = 16;
        config.debug_callback = ValidationTracker::instance().callback();
        
        vk = std::make_unique<VulkanContext>(config, cuda_uuid);
    }
    
    static void TearDownTestSuite() {
        vk.reset();
        if (cuda_initialized) {
            cuda_cleanup();
        }
    }
    
    void TearDown() override {
        ValidationTracker::instance().check_and_clear();
        if (vk) {
            vk->reset();
        }
    }
};

CUuuid DescriptorTest::cuda_uuid = {};
bool DescriptorTest::cuda_initialized = false;
std::unique_ptr<VulkanContext> DescriptorTest::vk;

TEST_F(DescriptorTest, CreateSampledImageReturnsValidHandle) {
    size_t initial_count = vk->num_sampled_images();
    
    auto handle = vk->create_sampled_image(64, 64, VK_FORMAT_R8G8B8A8_UNORM, VK_FILTER_LINEAR);
    
    EXPECT_NE(handle.id, 0u);
    EXPECT_EQ(vk->num_sampled_images(), initial_count + 1);
}

TEST_F(DescriptorTest, SampledImageReturnsCorrectData) {
    auto handle = vk->create_sampled_image(32, 64, VK_FORMAT_R8G8B8A8_UNORM, VK_FILTER_NEAREST);
    
    const auto& img = vk->sampled_image(handle);
    
    EXPECT_EQ(img.width, 32);
    EXPECT_EQ(img.height, 64);
    EXPECT_NE(img.image, VK_NULL_HANDLE);
    EXPECT_NE(img.memory, VK_NULL_HANDLE);
    EXPECT_NE(img.view, VK_NULL_HANDLE);
    EXPECT_NE(img.sampler, VK_NULL_HANDLE);
    EXPECT_GT(img.size, 0u);
}

TEST_F(DescriptorTest, NumSampledImagesTracksCount) {
    size_t initial_count = vk->num_sampled_images();
    
    auto handle1 = vk->create_sampled_image(32, 32, VK_FORMAT_R8G8B8A8_UNORM, VK_FILTER_LINEAR);
    EXPECT_EQ(vk->num_sampled_images(), initial_count + 1);
    
    auto handle2 = vk->create_sampled_image(32, 32, VK_FORMAT_R8G8B8A8_UNORM, VK_FILTER_LINEAR);
    EXPECT_EQ(vk->num_sampled_images(), initial_count + 2);
    
    auto handle3 = vk->create_sampled_image(32, 32, VK_FORMAT_R8G8B8A8_UNORM, VK_FILTER_LINEAR);
    EXPECT_EQ(vk->num_sampled_images(), initial_count + 3);
}

TEST_F(DescriptorTest, DestroySampledImageRemovesFromMap) {
    size_t initial_count = vk->num_sampled_images();
    
    auto handle = vk->create_sampled_image(32, 32, VK_FORMAT_R8G8B8A8_UNORM, VK_FILTER_LINEAR);
    EXPECT_EQ(vk->num_sampled_images(), initial_count + 1);
    
    vk->destroy_sampled_image(handle);
    EXPECT_EQ(vk->num_sampled_images(), initial_count);
}

TEST_F(DescriptorTest, InvalidHandleAccessThrows) {
    SampledImageHandle invalid_handle{99999};
    
    EXPECT_THROW(vk->sampled_image(invalid_handle), std::runtime_error);
}

TEST_F(DescriptorTest, DescriptorPoolGrowsWhenExceedingCapacity) {
    // This test needs its own context with small initial capacity to trigger growth
    VulkanContextConfig config;
    config.window = nullptr;  // headless mode
    config.initial_sampled_image_capacity = 4;  // Start with very small capacity
    config.debug_callback = ValidationTracker::instance().callback();
    
    VulkanContext small_vk(config, cuda_uuid);
    
    size_t initial_count = small_vk.num_sampled_images();
    
    std::vector<SampledImageHandle> handles;
    
    // Create enough images to exceed the initial capacity and trigger growth
    // Initial capacity is 4, so creating 4+ additional images should trigger growth
    for (int i = 0; i < 6; ++i) {
        ASSERT_NO_THROW({
            auto h = small_vk.create_sampled_image(16, 16, VK_FORMAT_R8G8B8A8_UNORM, VK_FILTER_LINEAR);
            handles.push_back(h);
        }) << "Failed to create sampled image " << i;
    }
    
    EXPECT_EQ(small_vk.num_sampled_images(), initial_count + 6);
    
    // Verify all handles are still valid after pool growth
    for (const auto& h : handles) {
        EXPECT_NO_THROW({
            const auto& img = small_vk.sampled_image(h);
            EXPECT_NE(img.image, VK_NULL_HANDLE);
        });
    }
}

TEST_F(DescriptorTest, HandleEqualityWorks) {
    SampledImageHandle h1{42};
    SampledImageHandle h2{42};
    SampledImageHandle h3{43};
    
    EXPECT_EQ(h1, h2);
    EXPECT_NE(h1, h3);
}

TEST_F(DescriptorTest, DefaultHandleHasZeroId) {
    SampledImageHandle h;
    EXPECT_EQ(h.id, 0u);
}
