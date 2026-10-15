// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary

#include <gtest/gtest.h>
#include <ovrtx/ovrtx.h>
#include <vector>
#include <string_view>

TEST(UsdPluginPaths, CountTruncationAndBorrowedLifetime) {
    const size_t count = ovrtx_get_usd_plugin_path_count(nullptr);
    ASSERT_GT(count, 0u);
    std::vector<ovx_string_t> paths(count);
    EXPECT_EQ(ovrtx_get_usd_plugin_paths(nullptr, paths.data(), count), count);
    ovx_string_t first{};
    EXPECT_EQ(ovrtx_get_usd_plugin_paths(nullptr, &first, 1), count);
    EXPECT_EQ(ovrtx_get_usd_plugin_paths(nullptr, nullptr, 0), count);
    EXPECT_EQ(first.ptr, paths[0].ptr);
    EXPECT_EQ(first.length, paths[0].length);
    EXPECT_EQ(ovrtx_register_schema_paths(nullptr).status, OVRTX_API_SUCCESS);
    std::vector<ovx_string_t> again(count);
    EXPECT_EQ(ovrtx_get_usd_plugin_paths(nullptr, again.data(), count), count);
    for (size_t i = 0; i < count; ++i) {
        EXPECT_EQ(paths[i].ptr, again[i].ptr);
        EXPECT_EQ(std::string_view(paths[i].ptr, paths[i].length),
                  std::string_view(again[i].ptr, again[i].length));
    }
}
