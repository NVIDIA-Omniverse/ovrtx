-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
-- SPDX-License-Identifier: LicenseRef-NvidiaProprietary
--
-- NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
-- property and proprietary rights in and to this material, related
-- documentation and any modifications thereto. Any use, reproduction,
-- disclosure or distribution of this material and related documentation
-- without an express license agreement from NVIDIA CORPORATION or
-- its affiliates is strictly prohibited.

-- Launch script for MarkerOverlayKernel.cu.

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

-- [snippet:scene-query-launch]
function markerOverlay(inputs, outputs)
    local height = inputs["Image"].shape[1]
    local width = inputs["Image"].shape[2]

    local scene = readScene(inputs["settings"].value)

    outputs["Overlay"] = cuda.image(width, height, cuda.uchar4)

    return cuda.kernel({
        args = {
            cuda.int(width),
            cuda.int(height),
            cuda.array(scene.cameraWorld, cuda.float),      -- -> const float* cameraWorld
            cuda.float(scene.focalLength),
            cuda.float(scene.horizontalAperture),
            cuda.float(scene.verticalAperture),
            cuda.array(scene.markerPositions, cuda.float),  -- -> const float* markerPositions
            cuda.int(scene.markerCount),
            cuda.float(scene.crosshairSize),
            cuda.TextureObject(inputs["Image"]),
            cuda.SurfaceObject(outputs["Overlay"]),
        },
    })
end
-- [/snippet:scene-query-launch]
