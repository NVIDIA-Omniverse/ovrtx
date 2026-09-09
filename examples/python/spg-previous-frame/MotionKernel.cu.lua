-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
-- SPDX-License-Identifier: LicenseRef-NvidiaProprietary
--
-- NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
-- property and proprietary rights in and to this material, related
-- documentation and any modifications thereto. Any use, reproduction,
-- disclosure or distribution of this material and related documentation
-- without an express license agreement from NVIDIA CORPORATION or
-- its affiliates is strictly prohibited.

-- [snippet:motion-launch]
-- Two resource-inputs, bound the same way. Nothing here says one of them is a
-- past frame: that is settled in the scene, by the RenderVar each is connected
-- to.
function motion(inputs, outputs)
    assert(inputs["Current"].rank == 2, "Current must be a 2D image")
    assert(inputs["Previous"].rank == 2, "Previous must be a 2D image")

    local height = inputs["Current"].shape[1]
    local width = inputs["Current"].shape[2]

    outputs["Difference"] = cuda.image(width, height, cuda.uchar4)

    return cuda.kernel({
        args = {
            cuda.int(width),
            cuda.int(height),
            cuda.float(inputs["gain"]),
            cuda.TextureObject(inputs["Current"]),
            cuda.TextureObject(inputs["Previous"]),
            cuda.SurfaceObject(outputs["Difference"]),
        },
    })
end
-- [/snippet:motion-launch]
