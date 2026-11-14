-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
-- SPDX-License-Identifier: LicenseRef-NvidiaProprietary
--
-- NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
-- property and proprietary rights in and to this material, related
-- documentation and any modifications thereto. Any use, reproduction,
-- disclosure or distribution of this material and related documentation
-- without an express license agreement from NVIDIA CORPORATION or
-- its affiliates is strictly prohibited.

-- Allocating the framebuffer the node feeds back into itself, on the Slang
-- backend.
--
-- The framebuffer is memory of the node: self.memory["History"] is stated with
-- slang.image, the allocator outputs use, and SPG hands the same resource back
-- on every run instead of a fresh one. That resource is history[n-1]: the
-- shader reads it, fades it, adds the current frame, and writes it back for
-- next time.
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
-- [snippet:trail-slang-alloc]
function trail(inputs, outputs)
    local image = inputs["Image"]
    -- The input is HdrColor, linear radiance. Texture2D<float4> converts the
    -- component type on load, so no exact dtype is pinned here.

    -- The feedback framebuffer, kept between executions.
    self.memory["History"] = slang.image(image.shape, slang.float4)
    -- Ordinary outputs: published as AOVs and handed out fresh each frame.
    outputs["Live"] = slang.image(image.shape, slang.uchar4)
    outputs["Trail"] = slang.image(image.shape, slang.uchar4)

    return slang.compute({
        bind = {
            slang.ParameterBlock(
                slang.float(inputs["decay"])          -- -> float decay
            ),
            slang.Texture2D(image),                    -- -> Texture2D<float4>   g_InImage
            slang.RWTexture2D(self.memory["History"]), -- -> RWTexture2D<float4> g_History
            slang.RWTexture2D(outputs["Live"]),        -- -> RWTexture2D<float4> g_OutLive
            slang.RWTexture2D(outputs["Trail"]),       -- -> RWTexture2D<float4> g_OutTrail
        },
    })
end
-- [/snippet:trail-slang-alloc]
