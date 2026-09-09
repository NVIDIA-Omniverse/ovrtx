-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
-- SPDX-License-Identifier: LicenseRef-NvidiaProprietary
--
-- NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
-- property and proprietary rights in and to this material, related
-- documentation and any modifications thereto. Any use, reproduction,
-- disclosure or distribution of this material and related documentation
-- without an express license agreement from NVIDIA CORPORATION or
-- its affiliates is strictly prohibited.

-- [snippet:histogram-launch]
-- Reading a composite AOV.
--
-- A sensor publishes a composite: a table of named channels under one render
-- var, rather than the single resource a camera AOV gives you. Test
-- inputs["X"].isComposite to tell the two apart, then take a channel out of
-- .tensors by name. Each one is an ordinary resource descriptor and binds like
-- any other buffer. .channelNames lists what the composite actually carries,
-- which follows from the channels authored on the RenderVar in the scene.
local WIDTH, HEIGHT = 512, 256
local THREADS = 256

function rangeHistogram(inputs, outputs)
    local pc = inputs["PointCloud"]
    assert(pc.isComposite, "PointCloud must be connected to a composite AOV")

    local coordinates = pc.tensors["Coordinates"]
    local counts = pc.tensors["Counts"]
    assert(coordinates ~= nil, "composite has no Coordinates channel")
    assert(counts ~= nil, "composite has no Counts channel")
    assert(#coordinates.shape == 2, "Coordinates must be [3, Nmax]")
    assert(coordinates.shape[1] == 3, "Coordinates must hold x, y and z runs")

    -- Nmax, the capacity Coordinates is allocated for. Counts says how many of
    -- those entries the sweep actually filled, but a launch script sees
    -- descriptors rather than data, so it cannot read that number. Counts is
    -- passed to the kernel instead and the bound is applied there.
    local maxPoints = coordinates.shape[2]

    -- The sensor publishes scalars alongside the channels. maxPoints is the same
    -- capacity the Coordinates shape reports, so reading it is a cheap check that
    -- this port is carrying the composite the node expects.
    assert(pc.params["maxPoints"] ~= nil, "composite has no maxPoints parameter")

    -- numBins splits the chart width into bars in the kernel, so it has to divide it.
    local numBins = inputs["numBins"].value
    assert(numBins > 0 and WIDTH % numBins == 0, "numBins must divide the chart width evenly")

    -- [/snippet:histogram-launch]
    -- [snippet:histogram-binding]
    outputs["Histogram"] = cuda.image(WIDTH, HEIGHT, cuda.uchar4)

    return cuda.kernel({
        args = {
            cuda.int(WIDTH),                          -- -> int width
            cuda.int(HEIGHT),                         -- -> int height
            cuda.int(maxPoints),                      -- -> int maxPoints
            cuda.int(numBins),                        -- -> int numBins
            cuda.float(inputs["maxRange"]),           -- -> float maxRange
            cuda.float(inputs["maxCount"]),           -- -> float maxCount
            cuda.array(coordinates),                  -- -> const float* coordinates
            cuda.array(counts),                       -- -> const int* counts
            cuda.SurfaceObject(outputs["Histogram"]), -- -> cudaSurfaceObject_t histogram
        },
        -- One thread per output column, each counting its own bin.
        block = { THREADS },
        grid  = { math.ceil(WIDTH / THREADS) },
    })
    -- [/snippet:histogram-binding]
end
