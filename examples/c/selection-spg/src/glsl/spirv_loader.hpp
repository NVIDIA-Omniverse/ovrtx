// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

#include <cstdint>
#include <fstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

// Load precompiled SPIR-V from file
inline std::vector<uint32_t> load_spirv(std::string_view spirv_path) {
    std::string path_str(spirv_path);
    std::ifstream file(path_str, std::ios::binary | std::ios::ate);
    if (!file.is_open()) {
        throw std::runtime_error("Failed to open SPIR-V file: " + path_str);
    }

    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);

    if (size % sizeof(uint32_t) != 0) {
        throw std::runtime_error("Invalid SPIR-V file size (not aligned to 4 bytes): " + path_str);
    }

    std::vector<uint32_t> spirv(size / sizeof(uint32_t));
    if (!file.read(reinterpret_cast<char*>(spirv.data()), size)) {
        throw std::runtime_error("Failed to read SPIR-V file: " + path_str);
    }

    return spirv;
}
