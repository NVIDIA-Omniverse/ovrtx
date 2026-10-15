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

--- SPG rtx module: what a launch script can read about the frame it runs in and the scene it
--- runs over. The same in either language.
--- This file provides type annotations for IDE IntelliSense only; it is NOT executed at runtime.

---@class SpgPrim  A prim of the stage, read on demand. prim["focalLength"] or prim.focalLength reads that attribute, nil when the prim does not carry it. Read-only.
---@field [string] any                Any attribute of the prim, by name
---@field path string                 Absolute prim path
---@field local_matrix number[]|nil   Local transform, 16 numbers row-major, or nil when the prim has none
---@field world_matrix number[]|nil   World transform, 16 numbers row-major, or nil when the prim has none

---@class SpgProductTiling  How the target is divided when the product is bound to several cameras
---@field count_x integer  Tiles across
---@field count_y integer  Tiles down
---@field count integer    Tiles that hold an image, one per bound camera
---@field width integer    Width of one tile in pixels
---@field height integer   Height of one tile in pixels

---@class SpgProduct : SpgPrim  The RenderProduct the node's prim sits under. Any other key, resolution included, reads the product prim's own attribute.
---@field tiling SpgProductTiling          The renderer's tile grid
---@field cameras SpgPrim[]                The cameras the product is bound to, in authored order
---@field render_vars SpgPrim[]            The RenderVars the product publishes, in orderedVars order

---@class SpgStage  The prims of the scene as published for the renderer
---@field prim fun(path: string|table, relative?: string): SpgPrim|nil  One prim by absolute path, or by a path relative to a base path or prim table; nil, with a logged error, when no prim is there
---@field query_attributes fun(paths: string|string[], names?: string|string[]): table<string, table>  The named attributes of every path, keyed by path; prims not on the stage are left out

---@class rtx
---@field frameId integer         The current rendered frame, counted by the renderer
---@field product SpgProduct|nil  The RenderProduct the node's prim sits under, or nil when the prim is not under one
---@field stage SpgStage          One prim by path, or many prims' attributes in one call
rtx = {}
