-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
-- SPDX-License-Identifier: LicenseRef-NvidiaProprietary
--
-- NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
-- property and proprietary rights in and to this material, related
-- documentation and any modifications thereto. Any use, reproduction,
-- disclosure or distribution of this material and related documentation
-- without an express license agreement from NVIDIA CORPORATION or
-- its affiliates is strictly prohibited.

function grayscale(inputs, outputs)
    assert(#inputs["LdrColor"].shape == 2, "Input must be a 2D image")
    assert(inputs["LdrColor"].dtype == cuda.uchar4, "Input must be uchar4")

    local height = inputs["LdrColor"].shape[1]
    local width  = inputs["LdrColor"].shape[2]

    outputs["LdrGrayscale"] = cuda.image(width, height, cuda.uchar4)

    return cuda.kernel({
        args = {
            cuda.int(width),
            cuda.int(height),
            cuda.TextureObject(inputs["LdrColor"]),
            cuda.SurfaceObject(outputs["LdrGrayscale"]),
        },
        block = { 32, 32 },
        grid  = { math.ceil(width / 32), math.ceil(height / 32) },
    })
end
