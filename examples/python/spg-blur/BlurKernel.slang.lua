-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
-- SPDX-License-Identifier: LicenseRef-NvidiaProprietary
--
-- NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
-- property and proprietary rights in and to this material, related
-- documentation and any modifications thereto. Any use, reproduction,
-- disclosure or distribution of this material and related documentation
-- without an express license agreement from NVIDIA CORPORATION or
-- its affiliates is strictly prohibited.

-- Launch script for BlurKernel.slang, one function per entry point. The weights
-- are built exactly as on CUDA; only the binding differs, because Slang binds by
-- declared type.

local THREADS = 256

-- [snippet:blur-slang-weights]
local function gaussianWeights(radius)
    warning("blur: building the weight table for radius " .. radius)

    if radius == 0 then
        return slang.array({ 1.0 }, slang.float)
    end

    local sigma = radius / 3.0
    local taps, total = {}, 0.0
    for t = -radius, radius do
        local w = math.exp(-0.5 * (t / sigma) ^ 2)
        taps[#taps + 1] = w
        total = total + w
    end
    for i = 1, #taps do
        taps[i] = taps[i] / total
    end
    return slang.array(taps, slang.float)
end
-- [/snippet:blur-slang-weights]

-- [snippet:blur-slang-horizontal-launch]
function blurHorizontal(inputs, outputs)
    assert(inputs["Image"].rank == 2, "Input must be a 2D image")

    local height = inputs["Image"].shape[1]
    local width = inputs["Image"].shape[2]
    local radius = inputs["radius"].value

    outputs["Blurred"] = slang.image(inputs["Image"].shape, inputs["Image"].dtype)

    return slang.dispatch({
        bind = {
            slang.ParameterBlock(
                slang.int(width),                       -- -> int width
                slang.int(height),                      -- -> int height
                slang.int(radius)                       -- -> int radius
            ),
            -- Built once rather than on every frame, then bound as a
            -- read-only buffer.
            slang.StructuredBuffer(slang.static(gaussianWeights, radius)),
            slang.Texture2D(inputs["Image"]),           -- -> Texture2D<float4>   g_InImage
            slang.RWTexture2D(outputs["Blurred"]),      -- -> RWTexture2D<float4> g_OutBlurred
        },
        -- No grid: the shader's [numthreads(16, 16, 1)] and the output's shape
        -- give one invocation per pixel.
    })
end
-- [/snippet:blur-slang-horizontal-launch]

-- [snippet:blur-slang-vertical-launch]
function blurVertical(inputs, outputs)
    assert(inputs["Image"].rank == 2, "Input must be a 2D image")

    local height = inputs["Image"].shape[1]
    local width = inputs["Image"].shape[2]
    local radius = inputs["radius"].value

    outputs["Blurred"] = slang.image(inputs["Image"].shape, inputs["Image"].dtype)

    return slang.dispatch({
        bind = {
            slang.ParameterBlock(
                slang.int(width),
                slang.int(height),
                slang.int(radius)
            ),
            slang.StructuredBuffer(slang.static(gaussianWeights, radius)),
            slang.Texture2D(inputs["Image"]),
            slang.RWTexture2D(outputs["Blurred"]),
        },
        -- One invocation per column, so the domain is the width alone. Left out,
        -- the grid would be derived from the output's shape and launch a group
        -- for every row as well.
        grid = { math.ceil(width / THREADS), 1, 1 },
    })
end
-- [/snippet:blur-slang-vertical-launch]
