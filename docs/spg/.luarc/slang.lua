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

--- SPG Slang table, used by .slang.lua launch scripts.
--- This file provides type annotations for IDE IntelliSense only; it is NOT executed at runtime.

---@class SpgSlangBinding  A single entry of the dispatch bind list

---@class SpgSlangBindGroup  One descriptor set, from slang.bind()

---@class SpgStateful  The slang.stateful marker

---@class SpgMatrixOrder  A matrix storage-order marker

---@class SpgDispatchConfig  Dispatch configuration returned by slang.dispatch()
---@field isValid boolean
---@field order string[]  Binding order
---@field args table      Binding map

---@class slang
---@field bool SpgDtype      Boolean (8-bit, 1 lane)
---@field bool2 SpgDtype     Boolean x2 (8-bit, 2 lanes)
---@field bool3 SpgDtype     Boolean x3 (8-bit, 3 lanes)
---@field bool4 SpgDtype     Boolean x4 (8-bit, 4 lanes)
---@field char SpgDtype      Signed char (8-bit, 1 lane)
---@field char2 SpgDtype     Signed char x2 (8-bit, 2 lanes)
---@field char3 SpgDtype     Signed char x3 (8-bit, 3 lanes) — no texture format
---@field char4 SpgDtype     Signed char x4 (8-bit, 4 lanes)
---@field uchar SpgDtype     Unsigned char (8-bit, 1 lane)
---@field uchar2 SpgDtype    Unsigned char x2 (8-bit, 2 lanes)
---@field uchar3 SpgDtype    Unsigned char x3 (8-bit, 3 lanes) — no texture format
---@field uchar4 SpgDtype    Unsigned char x4 (8-bit, 4 lanes) — most common image format, normalised
---@field short SpgDtype     Short (16-bit, 1 lane)
---@field short2 SpgDtype    Short x2 (16-bit, 2 lanes)
---@field short3 SpgDtype    Short x3 (16-bit, 3 lanes) — no texture format
---@field short4 SpgDtype    Short x4 (16-bit, 4 lanes)
---@field ushort SpgDtype    Unsigned short (16-bit, 1 lane)
---@field ushort2 SpgDtype   Unsigned short x2 (16-bit, 2 lanes)
---@field ushort3 SpgDtype   Unsigned short x3 (16-bit, 3 lanes) — no texture format
---@field ushort4 SpgDtype   Unsigned short x4 (16-bit, 4 lanes)
---@field half SpgDtype      Half (16-bit float, 1 lane)
---@field half2 SpgDtype     Half x2 (16-bit float, 2 lanes)
---@field half3 SpgDtype     Half x3 (16-bit float, 3 lanes) — no texture format
---@field half4 SpgDtype     Half x4 (16-bit float, 4 lanes) — HDR image format
---@field float SpgDtype     Float (32-bit, 1 lane)
---@field float2 SpgDtype    Float x2 (32-bit, 2 lanes)
---@field float3 SpgDtype    Float x3 (32-bit, 3 lanes)
---@field float4 SpgDtype    Float x4 (32-bit, 4 lanes)
---@field float2x2 SpgDtype  Float 2x2 matrix (32-bit, 4 lanes)
---@field float3x3 SpgDtype  Float 3x3 matrix (32-bit, 9 lanes)
---@field float4x4 SpgDtype  Float 4x4 matrix (32-bit, 16 lanes)
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
---@field double2x2 SpgDtype Double 2x2 matrix (64-bit, 4 lanes)
---@field double3x3 SpgDtype Double 3x3 matrix (64-bit, 9 lanes)
---@field double4x4 SpgDtype Double 4x4 matrix (64-bit, 16 lanes)
---@field int64 SpgDtype     Int64 (64-bit, 1 lane) — a shader cannot use it; shaderInt64 is off
---@field uint64 SpgDtype    Unsigned int64 (64-bit, 1 lane) — a shader cannot use it
---@field quatf SpgDtype     Float quaternion (32-bit, 4 lanes)
---@field quatd SpgDtype     Double quaternion (64-bit, 4 lanes)
---@field quath SpgDtype     Half quaternion (16-bit, 4 lanes)
---@field stateful SpgStateful  Marker: keep an output's memory across frames
---@field row_major SpgMatrixOrder     Marker: row-major matrix storage
---@field column_major SpgMatrixOrder  Marker: column-major matrix storage
slang = {}

--- A dtype constructor takes an optional second argument stating where the value
--- sits in the parameter block: a bare number is a byte offset, and the long form
--- `{ offset, order, stride }` also states how a matrix is stored. Offsets are
--- derived when every value in the block is a single four-byte number, and
--- required as soon as any vector or matrix appears. For example:
---     slang.uint(inputs["key"], 0)
---     slang.float4x4(inputs["xform"], { offset = 16, order = slang.column_major, stride = 16 })

--- Create a texture-backed output descriptor, the counterpart of `cuda.image`.
--- Pass `slang.stateful` to keep the resource across frames.
---@param width integer     Texture width
---@param height integer    Texture height
---@param dtype SpgDtype    Element data type
---@param flag? SpgStateful Pass `slang.stateful` for a persistent output
---@return SpgResourceDesc
---@overload fun(shape: integer[], dtype: SpgDtype, flag?: SpgStateful): SpgResourceDesc
function slang.image(width, height, dtype, flag) end

--- Create a buffer-backed output descriptor from a shape table, the counterpart
--- of `cuda.empty`. Use `slang.image` for texture-backed outputs.
---@param shape integer[]   Dimensions in [height, width] order (tensor convention)
---@param dtype SpgDtype    Element data type
---@param flag? SpgStateful Pass `slang.stateful` for a persistent output
---@return SpgResourceDesc
function slang.empty(shape, dtype, flag) end

--- Create an output filled with zeros.
---@param shape integer[]  Dimensions
---@param dtype SpgDtype   Element data type
---@return SpgResourceDesc
function slang.zeros(shape, dtype) end

--- Create an output filled with ones.
---@param shape integer[]  Dimensions
---@param dtype SpgDtype   Element data type
---@return SpgResourceDesc
function slang.ones(shape, dtype) end

--- Create an output filled with a custom value.
---@param shape integer[]  Dimensions
---@param value number     Fill value
---@param dtype SpgDtype   Element data type
---@return SpgResourceDesc
function slang.full(shape, value, dtype) end

--- Pack value-inputs into the shader's constant buffer. Arguments are listed in
--- the order the shader's struct declares its fields, wrapped with a dtype
--- constructor (for example `slang.float(inputs["strength"])`).
---@param ... any  Wrapped values
---@return SpgSlangBinding
function slang.ParameterBlock(...) end

--- Bind a resource-input as a read-only 1D texture (Texture1D). Rejects a
--- resource whose rank is not 1, an output, or a buffer-backed resource.
---@param input SpgResourceDesc  Input resource descriptor (from `inputs["name"]`)
---@return SpgSlangBinding
function slang.Texture1D(input) end

--- Bind a resource-input as a read-only 2D texture (Texture2D). Rejects a
--- resource whose rank is not 2, an output, or a buffer-backed resource.
---@param input SpgResourceDesc  Input resource descriptor (from `inputs["name"]`)
---@return SpgSlangBinding
function slang.Texture2D(input) end

--- Bind a resource-input as a read-only 3D texture (Texture3D). Rejects a
--- resource whose rank is not 3, an output, or a buffer-backed resource.
---@param input SpgResourceDesc  Input resource descriptor (from `inputs["name"]`)
---@return SpgSlangBinding
function slang.Texture3D(input) end

--- Bind an output as a read/write 1D texture (RWTexture1D). Rejects a resource
--- whose rank is not 1, an input, or a buffer-backed resource.
---@param output SpgResourceDesc  Output resource descriptor (from `outputs["name"]`)
---@return SpgSlangBinding
function slang.RWTexture1D(output) end

--- Bind an output as a read/write 2D texture (RWTexture2D). Rejects a resource
--- whose rank is not 2, an input, or a buffer-backed resource.
---@param output SpgResourceDesc  Output resource descriptor (from `outputs["name"]`)
---@return SpgSlangBinding
function slang.RWTexture2D(output) end

--- Bind an output as a read/write 3D texture (RWTexture3D). Rejects a resource
--- whose rank is not 3, an input, or a buffer-backed resource.
---@param output SpgResourceDesc  Output resource descriptor (from `outputs["name"]`)
---@return SpgSlangBinding
function slang.RWTexture3D(output) end

--- Bind a read-only storage buffer, addressed by element (StructuredBuffer).
--- Accepts a resource-input or the result of `slang.array(...)`. Rejects an
--- output, a texture-backed resource, or a typed buffer.
---@param input SpgResourceDesc|SpgSlangBinding  Buffer resource or uploaded array
---@return SpgSlangBinding
function slang.StructuredBuffer(input) end

--- Bind a read-only storage buffer, addressed by byte offset (ByteAddressBuffer).
--- Backed the same way as `slang.StructuredBuffer`; the two differ only in how
--- the shader addresses it.
---@param input SpgResourceDesc|SpgSlangBinding  Buffer resource or uploaded array
---@return SpgSlangBinding
function slang.ByteAddressBuffer(input) end

--- Bind a read-only typed buffer (`Buffer<T>`), which carries its element format
--- so the hardware converts on access. Only a buffer written through
--- `slang.RWBuffer` can be read this way.
---@param input SpgResourceDesc  Input resource descriptor (from `inputs["name"]`)
---@return SpgSlangBinding
function slang.Buffer(input) end

--- Bind a buffer-backed output as a read/write storage buffer, addressed by
--- element (RWStructuredBuffer). Rejects an input or a texture-backed resource.
---@param output SpgResourceDesc  Output resource descriptor (from `outputs["name"]`)
---@return SpgSlangBinding
function slang.RWStructuredBuffer(output) end

--- Bind a buffer-backed output as a read/write storage buffer, addressed by byte
--- offset (RWByteAddressBuffer).
---@param output SpgResourceDesc  Output resource descriptor (from `outputs["name"]`)
---@return SpgSlangBinding
function slang.RWByteAddressBuffer(output) end

--- Bind a buffer-backed output as a typed buffer (`RWBuffer<T>`). This is what
--- creates one: the element format is the output's dtype, so the shader's element
--- type has to match it and every consumer has to read it with `slang.Buffer`.
---@param output SpgResourceDesc  Output resource descriptor (from `outputs["name"]`)
---@return SpgSlangBinding
function slang.RWBuffer(output) end

--- Group resources into one descriptor set. Pass one call per set in the array
--- part of `slang.dispatch`. A single group may leave the space unstated, in
--- which case it comes from shader reflection; two or more groups must each
--- state one.
---@param resources SpgSlangBinding[]  Bindings for this descriptor set
---@param space? integer               Descriptor space, required with two or more groups
---@return SpgSlangBindGroup
function slang.bind(resources, space) end

--- Create an array to upload as buffer data. Four modes:
--- - `slang.array(luaTable, dtype)` — upload Lua data to a GPU buffer
--- - `slang.array(resourceDesc)` — reference an existing buffer, such as a composite channel
--- - `slang.array(assetInput, dtype)` — upload an `asset` value-input's raw bytes
--- - `slang.array(tokenInput)` — a `token` value-input as a null-terminated `char` array
--- Wrap the result in a buffer binder where the shader declares a buffer.
---@param data table|SpgResourceDesc  Lua table of values, a resource descriptor, or a value-input
---@param dtype? SpgDtype             Element type (required for Lua table and asset modes)
---@return SpgSlangBinding
function slang.array(data, dtype) end

--- Cache the result of a function call. Re-evaluates only when arguments change.
---@param fn function  Function to call and cache
---@param ... any      Arguments to pass to the function
---@return any         Cached return value
function slang.static(fn, ...) end

--- Define a ray-generation dispatch. The node's entry point must be a
--- `[shader("raygeneration")]` function. The ray grid is the output AOV's shape,
--- so there is no `numthreads`. Bind the scene acceleration structure like any
--- other resource, with `slang.binding("scene", inputs["scene"])`.
---@param config { bind: SpgSlangBinding[] }
---@return SpgDispatchConfig
function slang.rayQuery(config) end

--- Define a ray-generation dispatch that drives a full ray-tracing pipeline with
--- a shader binding table, so shading happens in separate entry points in the same
--- source file. The ray grid is the output AOV's shape, so there is no `numthreads`.
--- Exactly one hit group is supported; `miss` may hold several. `payloadSize` and
--- `attributeSize` are byte counts you work out yourself.
---@param config { bind: SpgSlangBinding[], miss?: string[], hit?: { closesthit: string, anyhit?: string }[], payloadSize?: integer, attributeSize?: integer }
---@return SpgDispatchConfig
function slang.traceRays(config) end

--- Bind an input port to a named binding provider. The scene acceleration
--- structure is the built-in "scene" provider and is bound implicitly for a
--- shader living under a RenderProduct, so this works with no authored input.
---@param provider string  Registered provider name (for example "scene")
---@param input SpgResourceDesc  Input descriptor (from `inputs["name"]`)
---@return SpgSlangBinding
function slang.binding(provider, input) end

--- Define the dispatch configuration. `bind` is matched positionally against
--- the resources declared in the shader. Resources may instead be grouped per
--- descriptor set by passing `slang.bind(...)` calls in the array part.
--- `numthreads` is for a shader that carries no reflection, meaning a `.spv`: a
--- shader that declares `[numthreads]` overrides it and the disagreement is reported.
---@param config { bind?: SpgSlangBinding[], numthreads?: integer[], grid?: integer[], stage?: string }
---@return SpgDispatchConfig
function slang.dispatch(config) end
