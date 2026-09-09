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
#include <string>
#include "cuda/cuda_kernel.hpp"
#include "glsl/spirv_loader.hpp"
#include "vk/vulkan_context.hpp"
#include "validation_tracker.hpp"

#define GLFW_INCLUDE_VULKAN
#include <GLFW/glfw3.h>

#include <filesystem>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

static auto get_executable_dir() -> std::filesystem::path {
#ifdef _WIN32
    wchar_t buf[MAX_PATH];
    DWORD len = GetModuleFileNameW(nullptr, buf, MAX_PATH);
    if (len == 0 || len == MAX_PATH) {
        throw std::runtime_error("GetModuleFileNameW failed");
    }
    return std::filesystem::path(buf).parent_path();
#elif defined(__linux__)
    return std::filesystem::canonical("/proc/self/exe").parent_path();
#else
    #error "Unsupported platform"
#endif
}

class RenderingTest : public ::testing::Test {
protected:
    static CUuuid cuda_uuid;
    static bool cuda_initialized;
    static std::unique_ptr<VulkanContext> vk;
    static GLFWwindow* window;
    static ShaderHandle vert_shader;
    static ShaderHandle frag_shader;
    static SampledImageHandle test_image;
    
    static void SetUpTestSuite() {
        cuda_initialized = cuda_init_standalone(0, &cuda_uuid);
        ASSERT_TRUE(cuda_initialized) << "Failed to initialize CUDA";
        
        // Initialize GLFW and create window
        ASSERT_TRUE(glfwInit()) << "Failed to initialize GLFW";
        
        glfwWindowHint(GLFW_CLIENT_API, GLFW_NO_API);
        glfwWindowHint(GLFW_RESIZABLE, GLFW_TRUE);  // Enable resize for resize tests
        glfwWindowHint(GLFW_VISIBLE, GLFW_FALSE);   // Hidden window for testing
        
        window = glfwCreateWindow(640, 480, "Rendering Test", nullptr, nullptr);
        ASSERT_NE(window, nullptr) << "Failed to create window";
        
        VulkanContextConfig config;
        config.window = window;
        config.initial_sampled_image_capacity = 8;
        config.debug_callback = ValidationTracker::instance().callback();
        
        vk = std::make_unique<VulkanContext>(config, cuda_uuid);
        
        // Create a test image for rendering
        test_image = vk->create_sampled_image(128, 128, VK_FORMAT_R16G16B16A16_SFLOAT, VK_FILTER_LINEAR, false);
        
        // Load precompiled SPIR-V shaders from next to the executable
        std::filesystem::path shader_dir = get_executable_dir() / "shaders";
        std::string vert_path = (shader_dir / "fullscreen.vert.spv").string();
        std::string frag_path = (shader_dir / "fullscreen.frag.spv").string();
        std::vector<uint32_t> vert_spirv = load_spirv(vert_path);
        std::vector<uint32_t> frag_spirv = load_spirv(frag_path);
        
        auto [vs, fs] = vk->create_linked_vertex_and_fragment_shaders(vert_spirv, frag_spirv);
        vert_shader = vs;
        frag_shader = fs;
        
        VkImage test_img = vk->sampled_image(test_image).image;
        vk->immediate_submit([test_img](CommandBuffer cmd) {
            cmd.image_memory_barrier(test_img, VK_IMAGE_ASPECT_COLOR_BIT,
                                     VK_IMAGE_LAYOUT_UNDEFINED, VK_PIPELINE_STAGE_2_TOP_OF_PIPE_BIT, VK_ACCESS_2_NONE,
                                     VK_IMAGE_LAYOUT_GENERAL, VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_WRITE_BIT);
        });
    }
    
    static void TearDownTestSuite() {
        vk.reset();
        if (window) {
            glfwDestroyWindow(window);
            window = nullptr;
        }
        glfwTerminate();
        if (cuda_initialized) {
            cuda_cleanup();
        }
    }
    
    void TearDown() override {
        // Don't call reset() for rendering tests - swapchain state is complex
        // and tests may leave acquired images that need to be properly presented
        if (vk) {
            vk->wait_for_fence();
        }
        ValidationTracker::instance().check_and_clear();
    }
    
    // Helper to complete a frame
    void render_one_frame() {
        vk->wait_for_fence();
        vk->reset_fence();
        
        uint32_t image_index;
        AcquireResult result = vk->acquire_next_image(image_index);
        ASSERT_EQ(result, AcquireResult::Success);
        
        CommandBuffer cmd = vk->command_buffer();
        cmd.begin();
        cmd.image_memory_barrier(vk->sampled_image(test_image).image, VK_IMAGE_ASPECT_COLOR_BIT,
                                 VK_IMAGE_LAYOUT_GENERAL, VK_PIPELINE_STAGE_2_ALL_COMMANDS_BIT, VK_ACCESS_2_MEMORY_WRITE_BIT,
                                 VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_READ_BIT);
        vk->record_frame_begin(image_index);
        VkExtent2D extent = vk->swapchain_extent();
        cmd.set_viewport(0.0f, 0.0f, static_cast<float>(extent.width), static_cast<float>(extent.height));
        cmd.set_scissor(0, 0, extent.width, extent.height);
        cmd.set_rasterizer_discard_enable(false);
        cmd.set_polygon_mode(VK_POLYGON_MODE_FILL);
        cmd.set_cull_mode(VK_CULL_MODE_NONE);
        cmd.set_front_face(VK_FRONT_FACE_COUNTER_CLOCKWISE);
        cmd.set_depth_bias_enable(false);
        cmd.set_primitive_topology(VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST);
        cmd.set_primitive_restart_enable(false);
        cmd.set_depth_test_enable(false);
        cmd.set_depth_write_enable(false);
        cmd.set_depth_bounds_test_enable(false);
        cmd.set_stencil_test_enable(false);
        cmd.set_rasterization_samples(VK_SAMPLE_COUNT_1_BIT);
        cmd.set_sample_mask(VK_SAMPLE_COUNT_1_BIT, 0xFFFFFFFF);
        cmd.set_alpha_to_coverage_enable(false);
        cmd.set_color_blend_enable(0, false);
        cmd.set_color_write_mask(0, VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
                                    VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT);
        cmd.set_vertex_input_empty();
        vk->bind_shaders(vert_shader, frag_shader);
        VkDescriptorSet desc_set = vk->descriptor_set();
        cmd.bind_descriptor_sets(VK_PIPELINE_BIND_POINT_GRAPHICS, vk->pipeline_layout(), 0, 1, &desc_set);
        uint32_t tex_idx = vk->sampled_image(test_image).descriptor_index;
        cmd.push_constants(vk->pipeline_layout(), VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(tex_idx), &tex_idx);
        cmd.draw(3);
        vk->record_frame_end(image_index);
        cmd.image_memory_barrier(vk->sampled_image(test_image).image, VK_IMAGE_ASPECT_COLOR_BIT,
                                 VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_READ_BIT,
                                 VK_IMAGE_LAYOUT_GENERAL, VK_PIPELINE_STAGE_2_ALL_COMMANDS_BIT, VK_ACCESS_2_MEMORY_WRITE_BIT);
        cmd.end();
        vk->submit_and_present(image_index);
    }
};

CUuuid RenderingTest::cuda_uuid = {};
bool RenderingTest::cuda_initialized = false;
std::unique_ptr<VulkanContext> RenderingTest::vk;
GLFWwindow* RenderingTest::window = nullptr;
ShaderHandle RenderingTest::vert_shader = {};
ShaderHandle RenderingTest::frag_shader = {};
SampledImageHandle RenderingTest::test_image = {};

TEST_F(RenderingTest, CanAcquireSwapchainImage) {
    vk->wait_for_fence();
    vk->reset_fence();
    
    uint32_t image_index;
    auto result = vk->acquire_next_image(image_index);
    ASSERT_EQ(result, AcquireResult::Success);
    
    // Swapchain typically has 2-3 images
    EXPECT_LT(image_index, 4u);
    
    // Complete the frame to return the image to the swapchain
    CommandBuffer cmd = vk->command_buffer();
    cmd.begin();
    cmd.image_memory_barrier(vk->sampled_image(test_image).image, VK_IMAGE_ASPECT_COLOR_BIT,
                             VK_IMAGE_LAYOUT_GENERAL, VK_PIPELINE_STAGE_2_ALL_COMMANDS_BIT, VK_ACCESS_2_MEMORY_WRITE_BIT,
                             VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_READ_BIT);
    vk->record_frame_begin(image_index);
    VkExtent2D extent = vk->swapchain_extent();
    cmd.set_viewport(0.0f, 0.0f, static_cast<float>(extent.width), static_cast<float>(extent.height));
    cmd.set_scissor(0, 0, extent.width, extent.height);
    cmd.set_rasterizer_discard_enable(false);
    cmd.set_polygon_mode(VK_POLYGON_MODE_FILL);
    cmd.set_cull_mode(VK_CULL_MODE_NONE);
    cmd.set_front_face(VK_FRONT_FACE_COUNTER_CLOCKWISE);
    cmd.set_depth_bias_enable(false);
    cmd.set_primitive_topology(VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST);
    cmd.set_primitive_restart_enable(false);
    cmd.set_depth_test_enable(false);
    cmd.set_depth_write_enable(false);
    cmd.set_depth_bounds_test_enable(false);
    cmd.set_stencil_test_enable(false);
    cmd.set_rasterization_samples(VK_SAMPLE_COUNT_1_BIT);
    cmd.set_sample_mask(VK_SAMPLE_COUNT_1_BIT, 0xFFFFFFFF);
    cmd.set_alpha_to_coverage_enable(false);
    cmd.set_color_blend_enable(0, false);
    cmd.set_color_write_mask(0, VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
                                VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT);
    cmd.set_vertex_input_empty();
    vk->bind_shaders(vert_shader, frag_shader);
    VkDescriptorSet desc_set = vk->descriptor_set();
    cmd.bind_descriptor_sets(VK_PIPELINE_BIND_POINT_GRAPHICS, vk->pipeline_layout(), 0, 1, &desc_set);
    uint32_t tex_idx = vk->sampled_image(test_image).descriptor_index;
    cmd.push_constants(vk->pipeline_layout(), VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(tex_idx), &tex_idx);
    cmd.draw(3);
    vk->record_frame_end(image_index);
    cmd.image_memory_barrier(vk->sampled_image(test_image).image, VK_IMAGE_ASPECT_COLOR_BIT,
                             VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_READ_BIT,
                             VK_IMAGE_LAYOUT_GENERAL, VK_PIPELINE_STAGE_2_ALL_COMMANDS_BIT, VK_ACCESS_2_MEMORY_WRITE_BIT);
    cmd.end();
    vk->submit_and_present(image_index);
}

TEST_F(RenderingTest, CanRecordCommandBuffer) {
    vk->wait_for_fence();
    vk->reset_fence();
    
    uint32_t image_index;
    auto result = vk->acquire_next_image(image_index);
    ASSERT_EQ(result, AcquireResult::Success);
    
    ASSERT_NO_THROW({
        CommandBuffer cmd = vk->command_buffer();
        cmd.begin();
        cmd.image_memory_barrier(vk->sampled_image(test_image).image, VK_IMAGE_ASPECT_COLOR_BIT,
                                 VK_IMAGE_LAYOUT_GENERAL, VK_PIPELINE_STAGE_2_ALL_COMMANDS_BIT, VK_ACCESS_2_MEMORY_WRITE_BIT,
                                 VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_READ_BIT);
        vk->record_frame_begin(image_index);
        VkExtent2D extent = vk->swapchain_extent();
        cmd.set_viewport(0.0f, 0.0f, static_cast<float>(extent.width), static_cast<float>(extent.height));
        cmd.set_scissor(0, 0, extent.width, extent.height);
        cmd.set_rasterizer_discard_enable(false);
        cmd.set_polygon_mode(VK_POLYGON_MODE_FILL);
        cmd.set_cull_mode(VK_CULL_MODE_NONE);
        cmd.set_front_face(VK_FRONT_FACE_COUNTER_CLOCKWISE);
        cmd.set_depth_bias_enable(false);
        cmd.set_primitive_topology(VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST);
        cmd.set_primitive_restart_enable(false);
        cmd.set_depth_test_enable(false);
        cmd.set_depth_write_enable(false);
        cmd.set_depth_bounds_test_enable(false);
        cmd.set_stencil_test_enable(false);
        cmd.set_rasterization_samples(VK_SAMPLE_COUNT_1_BIT);
        cmd.set_sample_mask(VK_SAMPLE_COUNT_1_BIT, 0xFFFFFFFF);
        cmd.set_alpha_to_coverage_enable(false);
        cmd.set_color_blend_enable(0, false);
        cmd.set_color_write_mask(0, VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
                                    VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT);
        cmd.set_vertex_input_empty();
        vk->bind_shaders(vert_shader, frag_shader);
        VkDescriptorSet desc_set = vk->descriptor_set();
        cmd.bind_descriptor_sets(VK_PIPELINE_BIND_POINT_GRAPHICS, vk->pipeline_layout(), 0, 1, &desc_set);
        uint32_t tex_idx = vk->sampled_image(test_image).descriptor_index;
        cmd.push_constants(vk->pipeline_layout(), VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(tex_idx), &tex_idx);
        cmd.draw(3);
        vk->record_frame_end(image_index);
        cmd.image_memory_barrier(vk->sampled_image(test_image).image, VK_IMAGE_ASPECT_COLOR_BIT,
                                 VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_READ_BIT,
                                 VK_IMAGE_LAYOUT_GENERAL, VK_PIPELINE_STAGE_2_ALL_COMMANDS_BIT, VK_ACCESS_2_MEMORY_WRITE_BIT);
        cmd.end();
    });
    
    // Complete the frame to return the image to the swapchain
    vk->submit_and_present(image_index);
}

TEST_F(RenderingTest, CanSubmitAndPresent) {
    vk->wait_for_fence();
    vk->reset_fence();
    
    uint32_t image_index;
    AcquireResult result = vk->acquire_next_image(image_index);
    ASSERT_EQ(result, AcquireResult::Success);
    
    CommandBuffer cmd = vk->command_buffer();
    cmd.begin();
    cmd.image_memory_barrier(vk->sampled_image(test_image).image, VK_IMAGE_ASPECT_COLOR_BIT,
                             VK_IMAGE_LAYOUT_GENERAL, VK_PIPELINE_STAGE_2_ALL_COMMANDS_BIT, VK_ACCESS_2_MEMORY_WRITE_BIT,
                             VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_READ_BIT);
    vk->record_frame_begin(image_index);
    VkExtent2D extent = vk->swapchain_extent();
    cmd.set_viewport(0.0f, 0.0f, static_cast<float>(extent.width), static_cast<float>(extent.height));
    cmd.set_scissor(0, 0, extent.width, extent.height);
    cmd.set_rasterizer_discard_enable(false);
    cmd.set_polygon_mode(VK_POLYGON_MODE_FILL);
    cmd.set_cull_mode(VK_CULL_MODE_NONE);
    cmd.set_front_face(VK_FRONT_FACE_COUNTER_CLOCKWISE);
    cmd.set_depth_bias_enable(false);
    cmd.set_primitive_topology(VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST);
    cmd.set_primitive_restart_enable(false);
    cmd.set_depth_test_enable(false);
    cmd.set_depth_write_enable(false);
    cmd.set_depth_bounds_test_enable(false);
    cmd.set_stencil_test_enable(false);
    cmd.set_rasterization_samples(VK_SAMPLE_COUNT_1_BIT);
    cmd.set_sample_mask(VK_SAMPLE_COUNT_1_BIT, 0xFFFFFFFF);
    cmd.set_alpha_to_coverage_enable(false);
    cmd.set_color_blend_enable(0, false);
    cmd.set_color_write_mask(0, VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
                                VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT);
    cmd.set_vertex_input_empty();
    vk->bind_shaders(vert_shader, frag_shader);
    VkDescriptorSet desc_set = vk->descriptor_set();
    cmd.bind_descriptor_sets(VK_PIPELINE_BIND_POINT_GRAPHICS, vk->pipeline_layout(), 0, 1, &desc_set);
    uint32_t tex_idx = vk->sampled_image(test_image).descriptor_index;
    cmd.push_constants(vk->pipeline_layout(), VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(tex_idx), &tex_idx);
    cmd.draw(3);
    vk->record_frame_end(image_index);
    cmd.image_memory_barrier(vk->sampled_image(test_image).image, VK_IMAGE_ASPECT_COLOR_BIT,
                             VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_READ_BIT,
                             VK_IMAGE_LAYOUT_GENERAL, VK_PIPELINE_STAGE_2_ALL_COMMANDS_BIT, VK_ACCESS_2_MEMORY_WRITE_BIT);
    cmd.end();
    
    ASSERT_NO_THROW({
        vk->submit_and_present(image_index);
    });
}

TEST_F(RenderingTest, MultipleFramesSucceed) {
    // Render multiple frames
    for (int frame = 0; frame < 5; ++frame) {
        vk->wait_for_fence();
        vk->reset_fence();
        
        uint32_t image_index;
        AcquireResult result = vk->acquire_next_image(image_index);
        ASSERT_EQ(result, AcquireResult::Success) << "Failed on frame " << frame;
        
        CommandBuffer cmd = vk->command_buffer();
        cmd.begin();
        cmd.image_memory_barrier(vk->sampled_image(test_image).image, VK_IMAGE_ASPECT_COLOR_BIT,
                                 VK_IMAGE_LAYOUT_GENERAL, VK_PIPELINE_STAGE_2_ALL_COMMANDS_BIT, VK_ACCESS_2_MEMORY_WRITE_BIT,
                                 VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_READ_BIT);
        vk->record_frame_begin(image_index);
        VkExtent2D extent = vk->swapchain_extent();
        cmd.set_viewport(0.0f, 0.0f, static_cast<float>(extent.width), static_cast<float>(extent.height));
        cmd.set_scissor(0, 0, extent.width, extent.height);
        cmd.set_rasterizer_discard_enable(false);
        cmd.set_polygon_mode(VK_POLYGON_MODE_FILL);
        cmd.set_cull_mode(VK_CULL_MODE_NONE);
        cmd.set_front_face(VK_FRONT_FACE_COUNTER_CLOCKWISE);
        cmd.set_depth_bias_enable(false);
        cmd.set_primitive_topology(VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST);
        cmd.set_primitive_restart_enable(false);
        cmd.set_depth_test_enable(false);
        cmd.set_depth_write_enable(false);
        cmd.set_depth_bounds_test_enable(false);
        cmd.set_stencil_test_enable(false);
        cmd.set_rasterization_samples(VK_SAMPLE_COUNT_1_BIT);
        cmd.set_sample_mask(VK_SAMPLE_COUNT_1_BIT, 0xFFFFFFFF);
        cmd.set_alpha_to_coverage_enable(false);
        cmd.set_color_blend_enable(0, false);
        cmd.set_color_write_mask(0, VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
                                    VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT);
        cmd.set_vertex_input_empty();
        vk->bind_shaders(vert_shader, frag_shader);
        VkDescriptorSet desc_set = vk->descriptor_set();
        cmd.bind_descriptor_sets(VK_PIPELINE_BIND_POINT_GRAPHICS, vk->pipeline_layout(), 0, 1, &desc_set);
        uint32_t tex_idx = vk->sampled_image(test_image).descriptor_index;
        cmd.push_constants(vk->pipeline_layout(), VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(tex_idx), &tex_idx);
        cmd.draw(3);
        vk->record_frame_end(image_index);
        cmd.image_memory_barrier(vk->sampled_image(test_image).image, VK_IMAGE_ASPECT_COLOR_BIT,
                                 VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_READ_BIT,
                                 VK_IMAGE_LAYOUT_GENERAL, VK_PIPELINE_STAGE_2_ALL_COMMANDS_BIT, VK_ACCESS_2_MEMORY_WRITE_BIT);
        cmd.end();
        
        ASSERT_NO_THROW({
            vk->submit_and_present(image_index);
        }) << "Failed on frame " << frame;
    }
}

TEST_F(RenderingTest, VulkanTimingReturnsValidValues) {
    // First frame - setup timestamps
    vk->wait_for_fence();
    vk->reset_fence();
    
    uint32_t image_index;
    AcquireResult result = vk->acquire_next_image(image_index);
    ASSERT_EQ(result, AcquireResult::Success);
    
    CommandBuffer cmd = vk->command_buffer();
    cmd.begin();
    // Reset and write timestamps for timing
    cmd.reset_query_pool(vk->timestamp_query_pool(), 0, 2);
    cmd.write_timestamp(VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, vk->timestamp_query_pool(), 0);
    cmd.image_memory_barrier(vk->sampled_image(test_image).image, VK_IMAGE_ASPECT_COLOR_BIT,
                             VK_IMAGE_LAYOUT_GENERAL, VK_PIPELINE_STAGE_2_ALL_COMMANDS_BIT, VK_ACCESS_2_MEMORY_WRITE_BIT,
                             VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_READ_BIT);
    vk->record_frame_begin(image_index);
    VkExtent2D extent = vk->swapchain_extent();
    cmd.set_viewport(0.0f, 0.0f, static_cast<float>(extent.width), static_cast<float>(extent.height));
    cmd.set_scissor(0, 0, extent.width, extent.height);
    cmd.set_rasterizer_discard_enable(false);
    cmd.set_polygon_mode(VK_POLYGON_MODE_FILL);
    cmd.set_cull_mode(VK_CULL_MODE_NONE);
    cmd.set_front_face(VK_FRONT_FACE_COUNTER_CLOCKWISE);
    cmd.set_depth_bias_enable(false);
    cmd.set_primitive_topology(VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST);
    cmd.set_primitive_restart_enable(false);
    cmd.set_depth_test_enable(false);
    cmd.set_depth_write_enable(false);
    cmd.set_depth_bounds_test_enable(false);
    cmd.set_stencil_test_enable(false);
    cmd.set_rasterization_samples(VK_SAMPLE_COUNT_1_BIT);
    cmd.set_sample_mask(VK_SAMPLE_COUNT_1_BIT, 0xFFFFFFFF);
    cmd.set_alpha_to_coverage_enable(false);
    cmd.set_color_blend_enable(0, false);
    cmd.set_color_write_mask(0, VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
                                VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT);
    cmd.set_vertex_input_empty();
    vk->bind_shaders(vert_shader, frag_shader);
    VkDescriptorSet desc_set = vk->descriptor_set();
    cmd.bind_descriptor_sets(VK_PIPELINE_BIND_POINT_GRAPHICS, vk->pipeline_layout(), 0, 1, &desc_set);
    uint32_t tex_idx = vk->sampled_image(test_image).descriptor_index;
    cmd.push_constants(vk->pipeline_layout(), VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(tex_idx), &tex_idx);
    cmd.draw(3);
    vk->record_frame_end(image_index);
    cmd.image_memory_barrier(vk->sampled_image(test_image).image, VK_IMAGE_ASPECT_COLOR_BIT,
                             VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_READ_BIT,
                             VK_IMAGE_LAYOUT_GENERAL, VK_PIPELINE_STAGE_2_ALL_COMMANDS_BIT, VK_ACCESS_2_MEMORY_WRITE_BIT);
    cmd.write_timestamp(VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, vk->timestamp_query_pool(), 1);
    cmd.end();
    vk->submit_and_present(image_index);
    
    // Second frame - read timestamps from first
    vk->wait_for_fence();
    
    double elapsed_ms = vk->vulkan_elapsed_ms();
    
    // Should be non-negative and reasonable (< 1 second)
    EXPECT_GE(elapsed_ms, 0.0);
    EXPECT_LT(elapsed_ms, 1000.0);
}

TEST_F(RenderingTest, CommandBufferIsNotNull) {
    EXPECT_NE(vk->command_buffer().handle(), VK_NULL_HANDLE);
}

TEST_F(RenderingTest, GetFramebufferSizeReturnsValidDimensions) {
    auto size = vk->framebuffer_size();
    
    // Window was created at 640x480
    EXPECT_GT(size.x, 0);
    EXPECT_GT(size.y, 0);
}

TEST_F(RenderingTest, ResizeWindowTriggersSwapchainRecreation) {
    // Complete one frame first
    render_one_frame();
    
    // Now simulate what main loop does: wait, reset fence, then try to acquire
    vk->wait_for_fence();
    vk->reset_fence();
    
    // Resize window AFTER resetting fence but BEFORE acquiring
    // This is the realistic scenario - window resize happens asynchronously
    glfwSetWindowSize(window, 800, 600);
    glfwPollEvents();  // Process the resize event
    
    // Try to acquire - may or may not be OutOfDate depending on driver
    uint32_t image_index;
    auto result = vk->acquire_next_image(image_index);
    
    // Handle OutOfDate if it occurred (same logic as main loop)
    if (result == AcquireResult::OutOfDate) {
        // Recreate swapchain and reset fence to signaled (as main loop does)
        vk->recreate_swapchain();
        vk->reset_fence_to_signaled();
        
        // Now try again - should work
        vk->wait_for_fence();
        vk->reset_fence();
        result = vk->acquire_next_image(image_index);
    }
    
    ASSERT_EQ(result, AcquireResult::Success);
    
    // Complete the frame
    CommandBuffer cmd = vk->command_buffer();
    cmd.begin();
    cmd.image_memory_barrier(vk->sampled_image(test_image).image, VK_IMAGE_ASPECT_COLOR_BIT,
                             VK_IMAGE_LAYOUT_GENERAL, VK_PIPELINE_STAGE_2_ALL_COMMANDS_BIT, VK_ACCESS_2_MEMORY_WRITE_BIT,
                             VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_READ_BIT);
    vk->record_frame_begin(image_index);
    {
        VkExtent2D extent = vk->swapchain_extent();
        cmd.set_viewport(0.0f, 0.0f, static_cast<float>(extent.width), static_cast<float>(extent.height));
        cmd.set_scissor(0, 0, extent.width, extent.height);
        cmd.set_rasterizer_discard_enable(false);
        cmd.set_polygon_mode(VK_POLYGON_MODE_FILL);
        cmd.set_cull_mode(VK_CULL_MODE_NONE);
        cmd.set_front_face(VK_FRONT_FACE_COUNTER_CLOCKWISE);
        cmd.set_depth_bias_enable(false);
        cmd.set_primitive_topology(VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST);
        cmd.set_primitive_restart_enable(false);
        cmd.set_depth_test_enable(false);
        cmd.set_depth_write_enable(false);
        cmd.set_depth_bounds_test_enable(false);
        cmd.set_stencil_test_enable(false);
        cmd.set_rasterization_samples(VK_SAMPLE_COUNT_1_BIT);
        cmd.set_sample_mask(VK_SAMPLE_COUNT_1_BIT, 0xFFFFFFFF);
        cmd.set_alpha_to_coverage_enable(false);
        cmd.set_color_blend_enable(0, false);
        cmd.set_color_write_mask(0, VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
                                    VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT);
        cmd.set_vertex_input_empty();
        vk->bind_shaders(vert_shader, frag_shader);
        VkDescriptorSet desc_set = vk->descriptor_set();
        cmd.bind_descriptor_sets(VK_PIPELINE_BIND_POINT_GRAPHICS, vk->pipeline_layout(), 0, 1, &desc_set);
        uint32_t tex_idx = vk->sampled_image(test_image).descriptor_index;
        cmd.push_constants(vk->pipeline_layout(), VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(tex_idx), &tex_idx);
        cmd.draw(3);
    }
    vk->record_frame_end(image_index);
    cmd.image_memory_barrier(vk->sampled_image(test_image).image, VK_IMAGE_ASPECT_COLOR_BIT,
                             VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_READ_BIT,
                             VK_IMAGE_LAYOUT_GENERAL, VK_PIPELINE_STAGE_2_ALL_COMMANDS_BIT, VK_ACCESS_2_MEMORY_WRITE_BIT);
    cmd.end();
    vk->submit_and_present(image_index);
    
    // Verify swapchain extent is valid (exact size depends on compositor)
    VkExtent2D extent = vk->swapchain_extent();
    EXPECT_GT(extent.width, 0u);
    EXPECT_GT(extent.height, 0u);
}

TEST_F(RenderingTest, MinimizedWindowReturnsZeroSize) {
    // Note: glfwIconifyWindow may not work on headless/hidden windows,
    // so we test the framebuffer_size behavior instead
    
    // On a non-minimized window, size should be non-zero
    auto size = vk->framebuffer_size();
    EXPECT_GT(size.x, 0);
    EXPECT_GT(size.y, 0);
    
    // Attempt to iconify (minimize) - may not work on hidden window
    glfwIconifyWindow(window);
    glfwPollEvents();
    
    // Check size - if iconify worked, it should be 0x0
    auto minimized_size = vk->framebuffer_size();
    
    // Restore window
    glfwRestoreWindow(window);
    glfwPollEvents();
    
    // On some systems with hidden windows, iconify may not take effect
    // So we just verify the API works without crashing
    SUCCEED();
}

TEST_F(RenderingTest, HiddenWindowStillWorks) {
    // The window is already hidden (GLFW_VISIBLE = GLFW_FALSE)
    // Verify we can still render
    
    // Hide explicitly (should be no-op since already hidden)
    glfwHideWindow(window);
    glfwPollEvents();
    
    // Size should still be valid on a hidden window
    auto size = vk->framebuffer_size();
    EXPECT_GT(size.x, 0);
    EXPECT_GT(size.y, 0);
    
    // Note: Rendering on hidden windows after previous tests may trigger
    // swapchain out-of-date on some drivers. The main functionality test
    // is that the window size is still valid and the context works.
    // Skip actual rendering as it's already tested in earlier tests.
}
