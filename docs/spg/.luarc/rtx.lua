---@meta

-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
-- SPDX-License-Identifier: LicenseRef-NvidiaProprietary
--
-- NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
-- property and proprietary rights in and to this material, related
-- documentation and any modifications thereto. Any use, reproduction,
-- disclosure or distribution of this material and related documentation
-- without an express license agreement from NVIDIA CORPORATION or
-- its affiliates is strictly prohibited.

--- SPG rtx module: what a launch script can read about the frame it runs in.
--- The same in either language.
--- This file provides type annotations for IDE IntelliSense only; it is NOT executed at runtime.

---@class rtx
---@field frameId integer  The current rendered frame, counted by the renderer
rtx = {}
