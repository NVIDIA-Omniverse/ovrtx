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

--- Print values to the SPG log (verbose level). Concatenates all arguments with spaces.
---@param ... any
function print(...) end

--- Assert a condition. Throws an SPG error if the condition is false.
---@param condition boolean
---@param msg? string  Optional error message
---@return boolean     Returns true if assertion passed
function assert(condition, msg) end

--- Names a prim's local transform wherever rtx.stage.query_attributes takes an attribute
--- name. The same value a prim table reads as .local_matrix.
---@type string
LOCAL_MATRIX = nil

--- Names a prim's world transform wherever rtx.stage.query_attributes takes an attribute
--- name. The same value a prim table reads as .world_matrix.
---@type string
WORLD_MATRIX = nil

---@class SpgSelf  What the launch states about the node itself; a new table on every call
---@field memory table<string, SpgResourceDesc>  The node's memory by name: a descriptor from `image` or `empty` under a string key, kept across frames and zeroed when created; not a port
---@field stateful boolean  Set to true to mark every output of the node stateful

--- The node itself: `self.memory["acc"] = cuda.empty({ n }, cuda.float)` gives the node memory it keeps
--- across frames, passed to the kernel with the wrappers an output takes.
---@type SpgSelf
self = nil
