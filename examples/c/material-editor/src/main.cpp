// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "main_window.hpp"

#include <ovrtx/ovrtx_config.h>
#include <ovrtx/ovrtx.h>

#include <QApplication>
#include <QPalette>
#include <QStyleFactory>

#include <iostream>
#include <string>
#include <string_view>

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);
    app.setApplicationName("ovrtx Material Editor");

    // Dark theme matching the QtNodes node graph background (#353535).
    app.setStyle(QStyleFactory::create("Fusion"));
    QPalette dark;
    dark.setColor(QPalette::Window,          QColor(53, 53, 53));
    dark.setColor(QPalette::WindowText,      QColor(208, 208, 208));
    dark.setColor(QPalette::Base,            QColor(42, 42, 42));
    dark.setColor(QPalette::AlternateBase,   QColor(53, 53, 53));
    dark.setColor(QPalette::ToolTipBase,     QColor(53, 53, 53));
    dark.setColor(QPalette::ToolTipText,     QColor(208, 208, 208));
    dark.setColor(QPalette::Text,            QColor(208, 208, 208));
    dark.setColor(QPalette::Button,          QColor(53, 53, 53));
    dark.setColor(QPalette::ButtonText,      QColor(208, 208, 208));
    dark.setColor(QPalette::BrightText,      QColor(255, 51, 51));
    dark.setColor(QPalette::Link,            QColor(42, 130, 218));
    dark.setColor(QPalette::Highlight,       QColor(42, 130, 218));
    dark.setColor(QPalette::HighlightedText, QColor(240, 240, 240));
    dark.setColor(QPalette::Disabled, QPalette::Text,       QColor(128, 128, 128));
    dark.setColor(QPalette::Disabled, QPalette::ButtonText, QColor(128, 128, 128));
    app.setPalette(dark);

    // Initialize ovrtx before any USD calls — ovrtx bootstraps the USD
    // runtime and plugin registry that OpenUSD needs. The static loader resolves
    // the package through the side-by-side `ovrtx/` link created by
    // ovrtx_setup_runtime().
    ovx_string_t ovrtx_package_root = {
        OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx",
        sizeof(OVX_CONFIG_EXECUTABLE_DIR_TOKEN "/ovrtx") - 1};
    ovrtx_config_entry_t config_entries[] = {
        ovrtx_config_entry_binary_package_root_path(ovrtx_package_root),
    };
    ovrtx_config_t config{config_entries, 1};
    ovrtx_result_t result = ovrtx_initialize(&config);
    if (result.status != OVRTX_API_SUCCESS) {
        ovx_string_t error = ovrtx_get_last_error();
        if (error.ptr && error.length > 0) {
            std::cerr << "Failed to initialize ovrtx: "
                      << std::string_view(error.ptr, error.length) << "\n";
        } else {
            std::cerr << "Failed to initialize ovrtx\n";
        }
        return 1;
    }

    std::string usda_path;
    if (argc > 1) {
        usda_path = argv[1];
    } else {
        // Default: relative path to the test base scene
        usda_path = "data/material-editor-ball.usda";
    }

    std::cerr << "Loading USD stage: " << usda_path << "\n";

    {
        MainWindow window(usda_path);
        window.resize(1600, 900);
        window.show();
        app.exec();
    }

    ovrtx_shutdown();
    return 0;
}
