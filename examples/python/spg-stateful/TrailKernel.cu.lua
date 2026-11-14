-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
-- SPDX-License-Identifier: LicenseRef-NvidiaProprietary
--
-- NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
-- property and proprietary rights in and to this material, related
-- documentation and any modifications thereto. Any use, reproduction,
-- disclosure or distribution of this material and related documentation
-- without an express license agreement from NVIDIA CORPORATION or
-- its affiliates is strictly prohibited.

-- Allocating the framebuffer the node feeds back into itself.
--
-- The framebuffer is memory of the node: self.memory["History"] is stated with
-- cuda.image, the allocator outputs use, and SPG hands the same resource back
-- on every run instead of a fresh one. That resource is history[n-1]: the node
-- reads it, fades it, adds the current frame, and writes it back for next time.
--
-- Two things about the allocation. It is not an output: no outputs: attribute
-- on the shader prim, no
-- RenderVar. And it is float4 while the two published images are uchar4,
-- because memory may use whatever format the algorithm needs. Here the feedback
-- runs on linear radiance, which would not survive being rounded into 8 bits
-- and re-scaled every frame.
--
-- SPG clears memory when it creates it, so the first execution reads zeros
-- rather than whatever was in GPU memory and the node needs no special case
-- for the first frame.
-- [snippet:trail-alloc]
function trail(inputs, outputs)
    local image = inputs["Image"]
    -- The input is HdrColor, linear radiance, so no exact dtype is pinned here.

    -- shape is 1-indexed: [1] = height (rows), [2] = width (columns).
    local height = image.shape[1]
    local width  = image.shape[2]

    -- The feedback framebuffer, kept between executions.
    self.memory["History"] = cuda.image(width, height, cuda.float4)
    -- Ordinary outputs: published as AOVs and handed out fresh each frame.
    outputs["Live"] = cuda.image(width, height, cuda.uchar4)
    outputs["Trail"] = cuda.image(width, height, cuda.uchar4)

    return cuda.kernel({
        args = {
            cuda.int(width),                            -- -> int width
            cuda.int(height),                           -- -> int height
            cuda.float(inputs["decay"]),                -- -> float decay
            cuda.TextureObject(image),                  -- -> cudaTextureObject_t inputImage
            cuda.SurfaceObject(self.memory["History"]), -- -> cudaSurfaceObject_t history
            cuda.SurfaceObject(outputs["Live"]),        -- -> cudaSurfaceObject_t liveImage
            cuda.SurfaceObject(outputs["Trail"]),       -- -> cudaSurfaceObject_t trailImage
        },
        block = { 32, 32 },
        grid  = { math.ceil(width / 32), math.ceil(height / 32) },
    })
end
-- [/snippet:trail-alloc]
