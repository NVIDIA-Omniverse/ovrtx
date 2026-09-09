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

class VulkanContextTest : public ::testing::Test {
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

CUuuid VulkanContextTest::cuda_uuid = {};
bool VulkanContextTest::cuda_initialized = false;
std::unique_ptr<VulkanContext> VulkanContextTest::vk;

TEST_F(VulkanContextTest, ContextCreationSucceeds) {
    // Context already created in SetUpTestSuite, just verify it exists
    ASSERT_NE(vk, nullptr);
}

TEST_F(VulkanContextTest, HeadlessShouldCloseReturnsFalse) {
    EXPECT_FALSE(vk->should_close());
}

TEST_F(VulkanContextTest, ExportableImageHasNonZeroMemorySize) {
    SampledImageHandle handle = vk->create_sampled_image(128, 128, VK_FORMAT_R16G16B16A16_SFLOAT, VK_FILTER_LINEAR, true);
    EXPECT_GT(vk->sampled_image(handle).size, 0u);
    vk->destroy_sampled_image(handle);
}

TEST_F(VulkanContextTest, TimestampPeriodIsPositive) {
    EXPECT_GT(vk->timestamp_period(), 0.0f);
}

TEST_F(VulkanContextTest, SampledImageLimitIsPositive) {
    EXPECT_GT(vk->sampled_image_limit(), 0u);
}
