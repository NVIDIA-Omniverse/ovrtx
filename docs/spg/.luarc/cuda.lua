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

--- SPG CUDA module
--- This file provides type annotations for IDE IntelliSense only; it is NOT executed at runtime.

---@class SpgDtype
---@field code integer  DataType enum value
---@field bits integer  Bits per lane (8, 16, 32, 64)
---@field lanes integer Number of lanes (1 = scalar, 2-4 = vector, 9/16 = matrix)
---@field name string   Human-readable name
---@operator call(any): SpgArgWrapper  Wrap a value for kernel args (e.g., `cuda.int(42)`)

---@class SpgArgWrapper  Wrapped kernel argument (returned by dtype call, TextureObject, SurfaceObject, array)

---@class SpgResourceDesc  Describes a GPU resource (texture/buffer) shape and type
---@field shape integer[]   Dimensions in [height, width] order (tensor convention)
---@field dtype SpgDtype    Data type of the resource
---@field rank integer      Number of dimensions
---@field bufferType string "TEXTURE" or "BUFFER"
---@field isOutput boolean  Whether this is an output descriptor
---@field isValid boolean   Whether construction succeeded

---@class SpgKernelConfig  Kernel launch configuration returned by cuda.kernel()
---@field isValid boolean
---@field order string[]    Argument ordering
---@field args table        Argument map

---@class cuda
---@field bool SpgDtype      Boolean (8-bit, 1 lane)
---@field uchar SpgDtype     Unsigned char (8-bit, 1 lane)
---@field uchar4 SpgDtype    Unsigned char x4 (8-bit, 4 lanes) — most common image format
---@field float SpgDtype     Float (32-bit, 1 lane)
---@field float2 SpgDtype    Float x2 (32-bit, 2 lanes)
---@field float3 SpgDtype    Float x3 (32-bit, 3 lanes)
---@field float4 SpgDtype    Float x4 (32-bit, 4 lanes)
---@field int SpgDtype       Int (32-bit, 1 lane)
---@field int2 SpgDtype      Int x2 (32-bit, 2 lanes)
---@field int3 SpgDtype      Int x3 (32-bit, 3 lanes)
---@field int4 SpgDtype      Int x4 (32-bit, 4 lanes)
---@field uint SpgDtype      Unsigned int (32-bit, 1 lane)
---@field uint2 SpgDtype     Unsigned int x2 (32-bit, 2 lanes)
---@field uint3 SpgDtype     Unsigned int x3 (32-bit, 3 lanes)
---@field uint4 SpgDtype     Unsigned int x4 (32-bit, 4 lanes)
---@field double SpgDtype    Double (64-bit, 1 lane)
---@field double2 SpgDtype   Double x2 (64-bit, 2 lanes)
---@field double3 SpgDtype   Double x3 (64-bit, 3 lanes)
---@field double4 SpgDtype   Double x4 (64-bit, 4 lanes)
---@field half SpgDtype      Half (16-bit float, 1 lane)
---@field half2 SpgDtype     Half x2 (16-bit float, 2 lanes)
---@field half3 SpgDtype     Half x3 (16-bit float, 3 lanes)
---@field half4 SpgDtype     Half x4 (16-bit float, 4 lanes) — HDR image format
---@field int64 SpgDtype     Int64 (64-bit, 1 lane)
---@field uint64 SpgDtype    Unsigned int64 (64-bit, 1 lane)
cuda = {}

--- Create a 2D output image descriptor. Shape is stored as [height, width] (tensor convention).
---@param width integer   Image width in pixels
---@param height integer  Image height in pixels
---@param dtype SpgDtype  Pixel data type (e.g., `cuda.uchar4`)
---@return SpgResourceDesc
function cuda.image(width, height, dtype) end

--- Create an output tensor descriptor from a shape table.
---@param shape integer[]  Dimensions (e.g., `{height, width}` for 2D)
---@param dtype SpgDtype   Element data type
---@return SpgResourceDesc
function cuda.empty(shape, dtype) end

--- Define the CUDA kernel launch configuration.
---@param config { args: SpgArgWrapper[], block: integer[], grid: integer[] }
---@return SpgKernelConfig
function cuda.kernel(config) end

--- Wrap an input resource as a CUDA texture object for read access.
---@param input SpgResourceDesc  Input resource descriptor (from `inputs["name"]`)
---@return SpgArgWrapper
function cuda.TextureObject(input) end

--- Wrap an output resource as a CUDA surface object for write access.
---@param output SpgResourceDesc  Output resource descriptor (from `outputs["name"]`)
---@return SpgArgWrapper
function cuda.SurfaceObject(output) end

--- Create an array argument. Two modes:
--- - `cuda.array(resourceDesc)` — wrap a resource as a raw device pointer
--- - `cuda.array(luaTable, dtype)` — create an array from Lua data (uploaded to GPU)
---@param data table|SpgResourceDesc  Lua table of values, or a resource descriptor
---@param dtype? SpgDtype             Element type (required for Lua table mode)
---@return SpgArgWrapper
function cuda.array(data, dtype) end

--- Cache the result of a function call. Re-evaluates only when arguments change.
--- Useful for precomputing kernel weights (e.g., Gaussian coefficients).
---@param fn function  Function to call and cache
---@param ... any      Arguments to pass to the function
---@return any         Cached return value
function cuda.static(fn, ...) end

--- Create a zero-filled array.
---@param shape integer[]  Array shape
---@param dtype SpgDtype   Element type
---@return SpgArgWrapper
function cuda.zeros(shape, dtype) end

--- Create an array filled with ones.
---@param shape integer[]  Array shape
---@param dtype SpgDtype   Element type
---@return SpgArgWrapper
function cuda.ones(shape, dtype) end

--- Create an array filled with a custom value.
---@param shape integer[]   Array shape
---@param value number      Fill value
---@param dtype SpgDtype    Element type
---@return SpgArgWrapper
function cuda.full(shape, value, dtype) end
