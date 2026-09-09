-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
-- SPDX-License-Identifier: LicenseRef-NvidiaProprietary
--
-- NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
-- property and proprietary rights in and to this material, related
-- documentation and any modifications thereto. Any use, reproduction,
-- disclosure or distribution of this material and related documentation
-- without an express license agreement from NVIDIA CORPORATION or
-- its affiliates is strictly prohibited.

-- [snippet:invert-slang-launch]
-- Launch script for InvertKernel.slang. The function name must equal the
-- subIdentifier ("invert").
function invert(inputs, outputs)
    assert(inputs["Image"].rank == 2, "Input must be a 2D image")

    outputs["Inverted"] = slang.image(inputs["Image"].shape, inputs["Image"].dtype)

    return slang.dispatch({
        -- The bind list is positional. The parameter block comes first and
        -- carries the value-inputs in the order the shader's Params struct
        -- declares them; the resources follow in declaration order.
        bind = {
            slang.ParameterBlock(
                slang.float(inputs["strength"])      -- -> float strength
            ),
            slang.Texture2D(inputs["Image"]),        -- -> Texture2D<float4> g_InImage
            slang.RWTexture2D(outputs["Inverted"]),  -- -> RWTexture2D<float4> g_OutInverted
        },
        -- The shader's [numthreads(32, 32, 1)] places the dispatch; the grid
        -- follows from the output's shape.
    })
end
-- [/snippet:invert-slang-launch]
