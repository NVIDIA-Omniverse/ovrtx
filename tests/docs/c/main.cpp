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

#include <ovrtx/ovrtx.h>
#include <ovrtx/ovrtx_config.h>

#include <ovstage/ovstage.h>

#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <string_view>

#if defined(_WIN32)
#    ifndef WIN32_LEAN_AND_MEAN
#        define WIN32_LEAN_AND_MEAN
#    endif
#    include <windows.h>
#endif

int main(int argc, char** argv) {
    testing::InitGoogleTest(&argc, argv);

    // initialize ovrtx once with the binary package root
    // (the `ovrtx/` link beside the exe that ovrtx_setup_runtime created). 
    if (!GTEST_FLAG_GET(list_tests)) {
        ovx_string_t ovrtx_package_root = {
            OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx",
            sizeof(OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx") - 1};
        ovrtx_config_entry_t init_entries[] = {
            ovrtx_config_entry_binary_package_root_path(ovrtx_package_root),
        };
        ovrtx_config_t init_config = {init_entries, 1};
        ovrtx_result_t init_result = ovrtx_initialize(&init_config);
        if (init_result.status != OVRTX_API_SUCCESS) {
            ovx_string_t err = ovrtx_get_last_error();
            std::cerr << "ovrtx_initialize failed";
            if (err.ptr && err.length > 0) {
                std::cerr << ": " << std::string_view(err.ptr, err.length);
            }
            std::cerr << std::endl;
            return 1;
        }

        // Symmetric ovstage initialize with its own side-by-side `ovstage/` link
        // (created by ovstage_setup_runtime). ovstage is delay-loaded and binds
        // to ovrtx's already-loaded USD runtime by base name.
        ovx_string_t ovstage_package_root = {
            OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovstage",
            sizeof(OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovstage") - 1};
        ovstage_config_entry_t stage_init_entries[] = {
            ovstage_config_entry_binary_package_root_path(ovstage_package_root),
        };
        ovstage_config_t stage_init_config = {stage_init_entries, 1};
        ovstage_api_status_t stage_init_status = ovstage_initialize(&stage_init_config);
        if (stage_init_status != OVSTAGE_OK) {
            ovx_string_t err = ovstage_get_last_error();
            std::cerr << "ovstage_initialize failed (" << static_cast<int>(stage_init_status) << ")";
            if (err.ptr && err.length > 0) {
                std::cerr << ": " << std::string_view(err.ptr, err.length);
            }
            std::cerr << std::endl;
            return 1;
        }
    }

    int result = RUN_ALL_TESTS();

    // GTest has written the test result by this point. Exit without running
    // late plugin/static destructors that can turn a passed suite into SIGSEGV.
    std::cout.flush();
    std::cerr.flush();
    std::clog.flush();
    std::fflush(nullptr);
#if defined(_WIN32)
    // std::_Exit still reaches ExitProcess on Windows; static Carbonite hooks
    // that path and can crash during late plugin teardown after GTest is done.
    TerminateProcess(GetCurrentProcess(), static_cast<UINT>(result));
#endif
    std::_Exit(result);
}
