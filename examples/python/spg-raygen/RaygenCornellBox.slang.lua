-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
-- SPDX-License-Identifier: LicenseRef-NvidiaProprietary
--
-- NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
-- property and proprietary rights in and to this material, related
-- documentation and any modifications thereto. Any use, reproduction,
-- disclosure or distribution of this material and related documentation
-- without an express license agreement from NVIDIA CORPORATION or
-- its affiliates is strictly prohibited.

-- Companion launch script for the SPG raygen Cornell-box showcase. The output shape drives the ray
-- dispatch, so an NxN image casts one primary ray per pixel. Only the scene and its camera transform are
-- bound -- both implicit from the node's RenderProduct; the shader needs nothing else.

-- [snippet:raygen-launch]
function rayGenCornellBox(inputs, outputs)
    local n = 256
    outputs["image"] = slang.image(n, n, slang.uchar4) -- RGBA image; one primary ray per pixel

    return slang.rayQuery({
        bind = {
            slang.ParameterBlock(
                slang.float4x4(inputs["sceneTransform"]),      -- auto-provided from the scene binding
                slang.float3(inputs["lightPosCamera"]),
                slang.float(inputs["sceneRenderScaleFactor"]), -- auto-provided unit factor
                slang.float(inputs["tanHalfFov"]),
                slang.float(inputs["maxRange"]),
                slang.float(inputs["shadowFactor"]),
                slang.float(inputs["ambient"]),
                slang.float(inputs["normalEpsilon"])
            ),
            slang.binding("scene", inputs["scene"]), -- scene TLAS, implicit from the RenderProduct
            slang.RWTexture2D(outputs["image"]),
        },
    })
end
-- [/snippet:raygen-launch]
