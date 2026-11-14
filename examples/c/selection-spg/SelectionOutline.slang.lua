-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
-- SPDX-License-Identifier: LicenseRef-NvidiaProprietary
--
-- NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
-- property and proprietary rights in and to this material, related
-- documentation and any modifications thereto. Any use, reproduction,
-- disclosure or distribution of this material and related documentation
-- without an express license agreement from NVIDIA CORPORATION or
-- its affiliates is strictly prohibited.


-- [snippet:selection-spg-launch]
-- Both images use final output resolution. The renderer exports four unsigned 16-bit coverage states.
function selectionOutline(inputs, outputs)
    local color = inputs["Color"]
    local state = inputs["SelectionState"]
    assert(color.rank == 2 and color.dtype == slang.uchar4, "Color must be LdrColor")
    assert(state.rank == 2 and state.dtype == slang.ushort4, "SelectionState must be four uint16 samples")
    assert(state.shape[1] == color.shape[1] and state.shape[2] == color.shape[2],
           "SelectionState must match output resolution")
    -- USD value inputs are wrappers; Lua comparisons need their numeric value.
    assert(inputs["width"].value >= 0 and inputs["width"].value <= 32, "Example outline width must be 0..32")
    assert(inputs["shape"].value >= 0 and inputs["shape"].value <= 2, "Example shape must be circle, square, or diamond")

    outputs["Color"] = slang.image(color.shape, color.dtype)
    return slang.compute({
        bind = {
            slang.ParameterBlock(slang.int(inputs["width"]), slang.int(inputs["shape"]),
                                 slang.float(inputs["fillAlpha"]), slang.int(inputs["dashPeriod"]),
                                 slang.int(inputs["hatchSpacing"]), slang.int(inputs["hatchLineWidth"]),
                                 slang.float(inputs["hiddenFillAlpha"]), slang.int(0)),
            slang.Texture2D(color),
            slang.Texture2D(state),
            slang.RWTexture2D(outputs["Color"]),
        },
    })
end
-- [/snippet:selection-spg-launch]
