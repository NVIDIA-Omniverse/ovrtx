# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Validate USDA files used in lidar_wpm/howto/firing_pattern.rst."""

from pathlib import Path

from pxr import Gf, Sdf

from conftest import validate_usda

DATA_DIR = Path(__file__).parent / "data"

LIDAR = "/Sensor/Lidar"
PRODUCT = "/Sensor/Outputs/Product"
POINT_CLOUD = "/Sensor/Outputs/PointCloud"
WPM = "omni:sensor:LidarWpm:"

# The four required arrays of a firing pattern, then rangeId, which may be empty.
PATTERN_ARRAYS = ("azimuthDeg", "elevationDeg", "fireTimeNs", "channelId", "rangeId")


def _load(name):
    """Parse one data file and return its layer and lidar prim, checking what both stages share."""
    layer = validate_usda((DATA_DIR / name).read_text())

    lidar = layer.GetPrimAtPath(LIDAR)
    assert lidar, f"{LIDAR} prim should exist in {name}"
    assert "OmniSensorGenericLidarWpmAPI" in lidar.GetInfo("apiSchemas").prependedItems
    assert lidar.attributes["visibility"].default == "invisible"
    assert lidar.attributes["omni:sensor:frameRate"].default == Gf.Vec2d(10, 1)
    assert lidar.attributes[f"{WPM}maxReturns"].default == 2
    return layer, lidar


def _pattern(lidar, instance):
    """Return the arrays of one pattern instance as lists, checking the length rule."""
    arrays = {}
    for name in PATTERN_ARRAYS:
        attribute = lidar.attributes.get(f"{WPM}firingPattern:{instance}:{name}")
        assert attribute, f"{LIDAR} should author firingPattern:{instance}:{name}"
        arrays[name] = list(attribute.default)

    rows = len(arrays["azimuthDeg"])
    assert rows, f"firingPattern:{instance} should have at least one row"
    for name in ("elevationDeg", "fireTimeNs", "channelId"):
        assert len(arrays[name]) == rows, f"firingPattern:{instance}:{name} should have {rows} rows"
    assert len(arrays["rangeId"]) in (0, rows), (
        f"firingPattern:{instance}:rangeId should be empty or have {rows} rows"
    )
    return arrays


def _requested_channels(layer):
    """Check the RenderProduct is bound to the lidar and return the PointCloud channel list."""
    product = layer.GetPrimAtPath(PRODUCT)
    assert product, f"{PRODUCT} prim should exist"
    assert list(product.relationships["camera"].targetPathList.explicitItems) == [Sdf.Path(LIDAR)]
    assert list(product.relationships["orderedVars"].targetPathList.explicitItems) == [
        Sdf.Path(POINT_CLOUD)
    ]

    point_cloud = layer.GetPrimAtPath(POINT_CLOUD)
    assert point_cloud, f"{POINT_CLOUD} prim should exist"
    assert point_cloud.attributes["sourceName"].default == "PointCloud"
    return list(point_cloud.attributes["channels"].default)


def test_rotary_firing_pattern():
    """Validate lidar_wpm_firing_pattern_rotary.usda: one pattern applied at every one-degree tick."""
    layer, lidar = _load("lidar_wpm_firing_pattern_rotary.usda")

    # The first pattern, p001, comes with OmniSensorGenericLidarWpmAPI itself.
    assert list(lidar.GetInfo("apiSchemas").prependedItems) == ["OmniSensorGenericLidarWpmAPI"]
    assert lidar.attributes[f"{WPM}scanType"].default == "rotary"
    assert lidar.attributes[f"{WPM}rotPatternFiringResDeg"].default == 1
    assert lidar.attributes.get(f"{WPM}firingPatternDwellTicks") is None

    p001 = _pattern(lidar, "p001")
    assert p001["azimuthDeg"] == [0, 0]
    assert p001["elevationDeg"] == [-1, 1]
    assert p001["fireTimeNs"] == [0, 1000]
    assert p001["channelId"] == [1, 2]
    assert p001["rangeId"] == []
    assert lidar.attributes.get(f"{WPM}firingPattern:p002:azimuthDeg") is None

    # An empty channel list requests every channel the model produces.
    assert _requested_channels(layer) == []


def test_solid_state_firing_patterns():
    """Validate lidar_wpm_firing_pattern_solid_state.usda: two patterns, each held for two scans."""
    layer, lidar = _load("lidar_wpm_firing_pattern_solid_state.usda")

    assert list(lidar.GetInfo("apiSchemas").prependedItems) == [
        "OmniSensorGenericLidarWpmAPI",
        "OmniSensorGenericLidarWpmFiringPatternAPI:p002",
    ]
    assert lidar.attributes[f"{WPM}scanType"].default == "solidState"
    assert lidar.attributes[f"{WPM}firingPatternDwellTicks"].default == 2

    p001 = _pattern(lidar, "p001")
    assert p001["azimuthDeg"] == [-1, 1]
    assert p001["elevationDeg"] == [0, 0]
    assert p001["fireTimeNs"] == [0, 1000]
    assert p001["channelId"] == [1, 2]
    assert p001["rangeId"] == []

    # The two patterns need not have the same row count.
    p002 = _pattern(lidar, "p002")
    assert p002["azimuthDeg"] == [0]
    assert p002["elevationDeg"] == [0]
    assert p002["fireTimeNs"] == [0]
    assert p002["channelId"] == [2]
    assert p002["rangeId"] == []

    # Six channels named explicitly; MaterialId and EchoId are left out.
    assert _requested_channels(layer) == [
        "Coordinates", "Intensity", "TimeOffsetNs", "Flags", "ChannelId", "FiringPatternIndex",
    ]
