-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
-- SPDX-License-Identifier: LicenseRef-NvidiaProprietary
--
-- NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
-- property and proprietary rights in and to this material, related
-- documentation and any modifications thereto. Any use, reproduction,
-- disclosure or distribution of this material and related documentation
-- without an express license agreement from NVIDIA CORPORATION or
-- its affiliates is strictly prohibited.

-- Launch script for MarkerOverlayKernel.slang.
--
-- The scene is read exactly as in MarkerOverlayKernel.cu.lua; the scene query API is the same
-- in both launch-script languages. Only the dispatch differs: scalars go into the parameter
-- block in the order the shader's struct declares them, and the two float lists become
-- read-only buffers.

-- Read everything the kernel needs about the scene and return it: the camera as a prim table,
-- its lens values and world transform, the crosshair size, and one flat list of marker
-- positions in the order the settings prim lists them.
local function readScene(settingsPath)
    -- [snippet:scene-query-camera]
    -- The render product this node sits under, and the camera it is bound to. The camera is a
    -- prim table: its attributes read by name, its two transforms by field.
    local product = rtx.product
    local camera = product.cameras[1]
    local cameraWorld = camera.world_matrix
    local focalLength = camera["focalLength"]
    local horizontalAperture = camera["horizontalAperture"]
    local verticalAperture = camera["verticalAperture"]
    -- [/snippet:scene-query-camera]

    -- [snippet:scene-query-prim]
    -- A prim of the scene's own, by the path a value-input carries. Its relationship reads as
    -- a list of path strings, its float as a number.
    local settings = rtx.stage.prim(settingsPath)
    local markerPaths = settings["markers"]
    local crosshairSize = settings["crosshairSize"]
    -- [/snippet:scene-query-prim]

    -- [snippet:scene-query-batch]
    -- Many prims, one attribute each: a batch query reads exactly what it names. A world
    -- transform is flat and row-major, so a prim's position is entries 13 to 15.
    local markers = rtx.stage.query_attributes(markerPaths, { WORLD_MATRIX })
    local markerPositions = {}
    for _, path in ipairs(markerPaths) do
        local marker = markers[path]
        local world = marker[WORLD_MATRIX]
        markerPositions[#markerPositions + 1] = world[13]
        markerPositions[#markerPositions + 1] = world[14]
        markerPositions[#markerPositions + 1] = world[15]
    end
    -- [/snippet:scene-query-batch]

    return {
        cameraWorld = cameraWorld,
        focalLength = focalLength,
        horizontalAperture = horizontalAperture,
        verticalAperture = verticalAperture,
        crosshairSize = crosshairSize,
        markerCount = #markerPaths,
        markerPositions = markerPositions,
    }
end

-- [snippet:scene-query-slang-launch]
function markerOverlay(inputs, outputs)
    local height = inputs["Image"].shape[1]
    local width = inputs["Image"].shape[2]

    local scene = readScene(inputs["settings"].value)

    outputs["Overlay"] = slang.image(width, height, inputs["Image"].dtype)

    return slang.dispatch({
        bind = {
            slang.ParameterBlock(
                slang.int(width),                          -- -> int   width
                slang.int(height),                         -- -> int   height
                slang.float(scene.focalLength),            -- -> float focalLength
                slang.float(scene.horizontalAperture),     -- -> float horizontalAperture
                slang.float(scene.verticalAperture),       -- -> float verticalAperture
                slang.int(scene.markerCount),              -- -> int   markerCount
                slang.float(scene.crosshairSize)           -- -> float crosshairSize
            ),
            slang.StructuredBuffer(slang.array(scene.cameraWorld, slang.float)),      -- -> g_CameraWorld
            slang.StructuredBuffer(slang.array(scene.markerPositions, slang.float)),  -- -> g_MarkerPositions
            slang.Texture2D(inputs["Image"]),                                         -- -> g_Image
            slang.RWTexture2D(outputs["Overlay"]),                                    -- -> g_Overlay
        },
        -- The shader's [numthreads(16, 16, 1)] places the dispatch; the grid follows from the
        -- output's shape.
    })
end
-- [/snippet:scene-query-slang-launch]
