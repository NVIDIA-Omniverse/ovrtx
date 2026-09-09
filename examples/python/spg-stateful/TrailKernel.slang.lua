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
-- slang.stateful is the trailing argument of slang.image, in the same position
-- cuda.stateful takes in cuda.image and cuda.empty. It marks the output as
-- persistent, so SPG hands the same resource back next frame instead of a fresh
-- one. That resource is history[n-1]: the shader reads it, fades it, adds the
-- current frame, and writes it back for next time.
--
-- Two things worth noting about the allocation. It is never published, so it
-- needs no RenderVar: a stateful output is scratch space for the node rather
-- than something the scene has to know about. And it is float4 while the two
-- published images are uchar4, because a stateful output may use whatever format
-- the algorithm needs. Here the feedback runs on linear radiance, which would
-- not survive being rounded into 8 bits and re-scaled every frame.
--
-- SPG clears a stateful allocation on first use, so the first execution reads
-- zeros rather than whatever was in memory and the node needs no special case
-- for the first frame.
-- [snippet:trail-slang-alloc]
function trail(inputs, outputs)
    local image = inputs["Image"]
    assert(image.rank == 2, "Input must be a 2D image")
    -- The input is HdrColor, linear radiance. Texture2D<float4> converts the
    -- component type on load, so no exact dtype is pinned here.

    -- The feedback framebuffer, and the only reason the effect exists.
    outputs["History"] = slang.image(image.shape, slang.float4, slang.stateful)
    -- Ordinary outputs: published as AOVs and handed out fresh each frame.
    outputs["Live"] = slang.image(image.shape, slang.uchar4)
    outputs["Trail"] = slang.image(image.shape, slang.uchar4)

    return slang.dispatch({
        bind = {
            slang.ParameterBlock(
                slang.float(inputs["decay"])          -- -> float decay
            ),
            slang.Texture2D(image),                    -- -> Texture2D<float4>   g_InImage
            slang.RWTexture2D(outputs["History"]),     -- -> RWTexture2D<float4> g_History
            slang.RWTexture2D(outputs["Live"]),        -- -> RWTexture2D<float4> g_OutLive
            slang.RWTexture2D(outputs["Trail"]),       -- -> RWTexture2D<float4> g_OutTrail
        },
    })
end
-- [/snippet:trail-slang-alloc]
