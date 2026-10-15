// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include <ovrtx/ovrtx.h>
#include <ovrtx/ovrtx_config.h>

#include <filesystem>
#include <iostream>
#include <string>
#include <string_view>
#include <vector>

int main() {
    ovrtx_config_t config{};
#ifdef OVRTX_EXAMPLE_STATIC_LOADERS
    // The static loader needs the package root linked beside the executable.
    const ovx_string_t package_root = {
        OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx",
        sizeof(OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx") - 1};
    ovrtx_config_entry_t entries[] = {
        ovrtx_config_entry_binary_package_root_path(package_root),
    };
    config.entries = entries;
    config.entry_count = 1;
#endif

    // [snippet:plugin-paths-enumerate-c]
    // Returned strings belong to ovrtx and remain valid for this process.
    const size_t count = ovrtx_get_usd_plugin_path_count(&config);
    std::vector<ovx_string_t> paths(count);
    const size_t total = ovrtx_get_usd_plugin_paths(&config, paths.data(), paths.size());
    if (total != count || count == 0) return 1;
    for (auto path : paths) std::cout << std::string_view(path.ptr, path.length) << "\n";
    // [/snippet:plugin-paths-enumerate-c]

    // [snippet:plugin-paths-validate-c]
    // Enumeration and registration do not check the filesystem.
    for (auto path : paths) {
        const auto descriptor = std::filesystem::path(std::string(path.ptr, path.length)) / "plugInfo.json";
        std::error_code error;
        if (!std::filesystem::is_regular_file(descriptor, error)) {
            std::cerr << "Schema plugin descriptor missing: " << descriptor.string() << "\n";
            return 1;
        }
    }
    // [/snippet:plugin-paths-validate-c]

    // [snippet:plugin-paths-register-c]
    // Publish paths before the bundled USD runtime first reads its registry.
    const ovrtx_result_t result = ovrtx_register_schema_paths(&config);
    if (result.status != OVRTX_API_SUCCESS) {
        std::cerr << "Could not register ovrtx schema paths.\n";
        return 1;
    }
    // [/snippet:plugin-paths-register-c]

    std::cout << "Published " << count << " schema directories for the bundled USD runtime.\n";
    return 0;
}
