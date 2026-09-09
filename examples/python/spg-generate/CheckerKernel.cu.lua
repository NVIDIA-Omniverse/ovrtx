-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
-- SPDX-License-Identifier: LicenseRef-NvidiaProprietary
--
-- NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
-- property and proprietary rights in and to this material, related
-- documentation and any modifications thereto. Any use, reproduction,
-- disclosure or distribution of this material and related documentation
-- without an express license agreement from NVIDIA CORPORATION or
-- its affiliates is strictly prohibited.

-- [snippet:checker-launch]
-- Launch script for a node with no resource-input.
--
-- Nothing hands this node a resource, so there is no descriptor to take a shape
-- from. The size comes from typed USD attributes instead, like every other
-- value the node uses.
function checker(inputs, outputs)
    local width  = inputs["width"].value
    local height = inputs["height"].value
    assert(width > 0 and height > 0, "width and height must be positive")
    assert(inputs["squareSize"].value > 0, "squareSize must be positive")

    outputs["Checker"] = cuda.image(width, height, cuda.uchar4)

    return cuda.kernel({
        args = {
            cuda.int(width),                        -- -> int width
            cuda.int(height),                       -- -> int height
            cuda.int(inputs["squareSize"]),         -- -> int squareSize
            cuda.array(inputs["colorA"]),           -- -> const float* colorA
            cuda.array(inputs["colorB"]),           -- -> const float* colorB
            cuda.SurfaceObject(outputs["Checker"]), -- -> cudaSurfaceObject_t output
        },
        block = { 16, 16 },
        grid  = { math.ceil(width / 16), math.ceil(height / 16) },
    })
end
-- [/snippet:checker-launch]
