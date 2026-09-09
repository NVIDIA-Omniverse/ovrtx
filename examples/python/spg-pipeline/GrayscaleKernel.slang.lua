-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
-- SPDX-License-Identifier: LicenseRef-NvidiaProprietary
--
-- NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
-- property and proprietary rights in and to this material, related
-- documentation and any modifications thereto. Any use, reproduction,
-- disclosure or distribution of this material and related documentation
-- without an express license agreement from NVIDIA CORPORATION or
-- its affiliates is strictly prohibited.

-- Launch script for GrayscaleKernel.slang. SPG calls this once per frame.
-- The function name must equal the subIdentifier ("grayscale").
--
-- Same job as GrayscaleKernel.cu.lua: validate the input, allocate the output,
-- describe the launch. The differences are the `slang` table (in place of
-- `cuda`) and that resources are bound as a list instead of kernel arguments.
function grayscale(inputs, outputs)
    assert(inputs["LdrColor"].rank == 2, "Input must be a 2D image")

    -- Allocate the output AOV. Grayscale keeps the input's shape and dtype.
    outputs["LdrGrayscale"] = slang.image(inputs["LdrColor"].shape, inputs["LdrColor"].dtype)

    return slang.dispatch({
        -- bind order must match the resource declaration order in the shader.
        bind = {
            slang.Texture2D(inputs["LdrColor"]),        -- -> Texture2D<float4> g_InLdrColor
            slang.RWTexture2D(outputs["LdrGrayscale"]), -- -> RWTexture2D<float4> g_OutLdrGrayscale
        },
        -- No numthreads and no grid: the shader declares [numthreads(32, 32, 1)]
        -- and SPG divides the output's shape by it, one invocation per pixel.
    })
end
