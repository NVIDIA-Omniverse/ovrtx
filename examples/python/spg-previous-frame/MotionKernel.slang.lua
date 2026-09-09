-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
-- SPDX-License-Identifier: LicenseRef-NvidiaProprietary
--
-- NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
-- property and proprietary rights in and to this material, related
-- documentation and any modifications thereto. Any use, reproduction,
-- disclosure or distribution of this material and related documentation
-- without an express license agreement from NVIDIA CORPORATION or
-- its affiliates is strictly prohibited.

-- [snippet:motion-slang-launch]
function motion(inputs, outputs)
    assert(inputs["Current"].rank == 2, "Current must be a 2D image")
    assert(inputs["Previous"].rank == 2, "Previous must be a 2D image")

    outputs["Difference"] = slang.image(inputs["Current"].shape, inputs["Current"].dtype)

    return slang.dispatch({
        bind = {
            slang.ParameterBlock(
                slang.int(inputs["Current"].shape[2]),   -- -> int   width
                slang.int(inputs["Current"].shape[1]),   -- -> int   height
                slang.float(inputs["gain"])              -- -> float gain
            ),
            slang.Texture2D(inputs["Current"]),          -- -> Texture2D<float4>   g_InCurrent
            slang.Texture2D(inputs["Previous"]),         -- -> Texture2D<float4>   g_InPrevious
            slang.RWTexture2D(outputs["Difference"]),    -- -> RWTexture2D<float4> g_OutDifference
        },
    })
end
-- [/snippet:motion-slang-launch]
