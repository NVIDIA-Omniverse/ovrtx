-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
-- SPDX-License-Identifier: LicenseRef-NvidiaProprietary
--
-- NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
-- property and proprietary rights in and to this material, related
-- documentation and any modifications thereto. Any use, reproduction,
-- disclosure or distribution of this material and related documentation
-- without an express license agreement from NVIDIA CORPORATION or
-- its affiliates is strictly prohibited.

-- [snippet:checker-slang-launch]
-- Launch script for a node with no resource-input, on Slang.
--
-- Nothing hands this node a resource, so there is no descriptor to take a shape
-- from. The size comes from typed USD attributes instead. The values are packed
-- into one parameter block, in the order the shader's Params struct declares.
function checker(inputs, outputs)
    local width  = inputs["width"].value
    local height = inputs["height"].value
    assert(width > 0 and height > 0, "width and height must be positive")
    assert(inputs["squareSize"].value > 0, "squareSize must be positive")

    outputs["Checker"] = slang.image(width, height, slang.uchar4)

    return slang.dispatch({
        bind = {
            slang.ParameterBlock(
                slang.int(inputs["width"]),            -- -> int    width
                slang.int(inputs["height"]),           -- -> int    height
                slang.int(inputs["squareSize"]),       -- -> int    squareSize
                slang.float3(inputs["colorA"]),        -- -> float3 colorA
                slang.float3(inputs["colorB"])         -- -> float3 colorB
            ),
            slang.RWTexture2D(outputs["Checker"]),     -- -> RWTexture2D<float4> g_OutChecker
        },
        -- The shader's [numthreads(16, 16, 1)] places the dispatch.
    })
end
-- [/snippet:checker-slang-launch]
