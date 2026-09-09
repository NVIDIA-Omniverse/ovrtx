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

--- SPG sandbox globals
--- This file provides type annotations for IDE IntelliSense only; it is NOT executed at runtime.

--- Log an info-level message to the SPG logger.
---@param msg string
function info(msg) end

--- Log a warning-level message to the SPG logger.
---@param msg string
function warning(msg) end

--- Print values to the SPG log (info level). Concatenates all arguments with tabs.
---@param ... any
function print(...) end

--- Assert a condition. Throws an SPG error if the condition is false.
---@param condition boolean
---@param msg? string  Optional error message
---@return boolean     Returns true if assertion passed
function assert(condition, msg) end
