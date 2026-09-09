-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
-- SPDX-License-Identifier: LicenseRef-NvidiaProprietary
--
-- NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
-- property and proprietary rights in and to this material, related
-- documentation and any modifications thereto. Any use, reproduction,
-- disclosure or distribution of this material and related documentation
-- without an express license agreement from NVIDIA CORPORATION or
-- its affiliates is strictly prohibited.

-- Launch script for BlurKernel.cu. It carries one function per entry point,
-- because both Shader prims point at the same source asset and the launch
-- script is found from that path.

local BLOCK = 256

-- [snippet:blur-weights]
-- One row of Gaussian taps for the stated radius, normalised so the blur keeps
-- the image's brightness. It depends on nothing but the radius, so it is built
-- here rather than recomputed by every GPU thread.
--
-- The warning is what makes the caching visible: this line appears once per
-- distinct radius over a run, not once per frame.
local function gaussianWeights(radius)
    warning("blur: building the weight table for radius " .. radius)

    if radius == 0 then
        return cuda.array({ 1.0 }, cuda.float)
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
    return cuda.array(taps, cuda.float)
end
-- [/snippet:blur-weights]

-- [snippet:blur-horizontal-launch]
function blurHorizontal(inputs, outputs)
    assert(inputs["Image"].rank == 2, "Input must be a 2D image")

    local height = inputs["Image"].shape[1]
    local width = inputs["Image"].shape[2]
    local radius = inputs["radius"].value

    outputs["Blurred"] = cuda.image(width, height, cuda.uchar4)

    return cuda.kernel({
        args = {
            cuda.int(width),
            cuda.int(height),
            cuda.int(radius),
            -- Built once rather than on every frame: cuda.static caches the
            -- call against its arguments, and this script runs per frame.
            cuda.static(gaussianWeights, radius),
            cuda.TextureObject(inputs["Image"]),
            cuda.SurfaceObject(outputs["Blurred"]),
        },
        -- No block and no grid. One thread per output pixel is what SPG derives
        -- from the output's shape, and that is the mapping this kernel wants.
    })
end
-- [/snippet:blur-horizontal-launch]

-- [snippet:blur-vertical-launch]
function blurVertical(inputs, outputs)
    assert(inputs["Image"].rank == 2, "Input must be a 2D image")

    local height = inputs["Image"].shape[1]
    local width = inputs["Image"].shape[2]
    local radius = inputs["radius"].value

    outputs["Blurred"] = cuda.image(width, height, cuda.uchar4)

    return cuda.kernel({
        args = {
            cuda.int(width),
            cuda.int(height),
            cuda.int(radius),
            cuda.static(gaussianWeights, radius),
            cuda.TextureObject(inputs["Image"]),
            cuda.SurfaceObject(outputs["Blurred"]),
        },
        -- One thread per column, so the domain is the width alone. The derived
        -- geometry would cover width x height and launch a thread for every
        -- pixel, each of which would then walk the whole column.
        block = { BLOCK },
        grid = { math.ceil(width / BLOCK) },
    })
end
-- [/snippet:blur-vertical-launch]
