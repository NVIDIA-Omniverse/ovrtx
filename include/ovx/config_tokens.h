/* Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
 *
 * NVIDIA CORPORATION and its licensors retain all intellectual property
 * and proprietary rights in and to this software, related documentation
 * and any modifications thereto.  Any use, reproduction, disclosure or
 * distribution of this software and related documentation without an express
 * license agreement from NVIDIA CORPORATION is strictly prohibited.
 */

/**
 * @file config_tokens.h
 * @brief Tokens recognized in ovstage/ovrtx loader configuration string values.
 */

#ifndef OVX_CONFIG_TOKENS_H
#define OVX_CONFIG_TOKENS_H

/**
 * Substituted by the ovstage/ovrtx static loaders with the absolute directory
 * of the running executable (no trailing separator) when resolving
 * `binary_package_root_path`.
 *
 * Example: OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovstage/bin"
 */
#define OVX_CONFIG_EXECUTABLE_DIR_TOKEN "${executable_dir}"

#endif /* OVX_CONFIG_TOKENS_H */
