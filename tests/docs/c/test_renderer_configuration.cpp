// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary

#include <gtest/gtest.h>
#include <ovrtx/ovrtx.h>
#include <ovrtx/ovrtx_config.h>
#include <cstdlib>

namespace
{
int createMinimalOnlyRenderer()
{
    // main.cpp initializes the library before renderer creation.
    // [snippet:doc-create-minimal-only-renderer-c]
    ovrtx_config_entry_t entries[] = {
        ovrtx_config_entry_enable_minimal(true),
        ovrtx_config_entry_enable_realtimepathtracing(false),
        ovrtx_config_entry_enable_pathtracing(false),
        // Retain shared graphics resources even after this instance is destroyed.
        ovrtx_config_entry_keep_system_alive(true),
    };
    ovrtx_config_t config = {entries, sizeof(entries) / sizeof(entries[0])};
    ovrtx_renderer_t* renderer = nullptr;
    ovrtx_result_t result = ovrtx_create_renderer(&config, &renderer);
    // [/snippet:doc-create-minimal-only-renderer-c]
    if (result.status != OVRTX_API_SUCCESS || !renderer)
    {
        return 1;
    }
    // [snippet:doc-reset-render-mode-availability-c]
    // Omit enable_* to inherit Minimal-only availability and clear keep-alive retention.
    ovrtx_config_entry_t releaseEntry = ovrtx_config_entry_keep_system_alive(false);
    ovrtx_config_t releaseConfig = {&releaseEntry, 1};
    ovrtx_renderer_t* releaseRetention = nullptr;
    result = ovrtx_create_renderer(&releaseConfig, &releaseRetention);
    if (result.status != OVRTX_API_SUCCESS)
    {
        return 1;
    }
    result = ovrtx_destroy_renderer(renderer);
    if (result.status != OVRTX_API_SUCCESS)
    {
        return 1;
    }
    // Destroy any other ovrtx renderer instances before this final destroy.
    result = ovrtx_destroy_renderer(releaseRetention);
    if (result.status != OVRTX_API_SUCCESS)
    {
        return 1;
    }

    // No instance or keep-alive reference remains: initialize graphics again.
    ovrtx_config_entry_t allModesEntries[] = {
        ovrtx_config_entry_enable_minimal(true),
        ovrtx_config_entry_enable_realtimepathtracing(true),
        ovrtx_config_entry_enable_pathtracing(true),
        ovrtx_config_entry_keep_system_alive(false),
    };
    ovrtx_config_t allModesConfig = {allModesEntries, sizeof(allModesEntries) / sizeof(allModesEntries[0])};
    result = ovrtx_create_renderer(&allModesConfig, &renderer);
    if (result.status != OVRTX_API_SUCCESS)
    {
        return 1;
    }
    // [/snippet:doc-reset-render-mode-availability-c]
    return ovrtx_destroy_renderer(renderer).status == OVRTX_API_SUCCESS ? 0 : 1;
}
} // namespace

TEST(RendererConfigurationTest, CreateMinimalOnlyRenderer)
{
    // The CI runner also executes the entire suite in one process. Re-execute
    // this case in a fresh process so other tests' retained modes cannot interfere.
    GTEST_FLAG_SET(death_test_style, "threadsafe");
    ASSERT_EXIT(std::_Exit(createMinimalOnlyRenderer()), testing::ExitedWithCode(0), "");
}
