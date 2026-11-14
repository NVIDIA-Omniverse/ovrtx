# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Validate USDA files used in radar_wpm_dmat/howto/scan_configurations.rst."""

from pathlib import Path

from pxr import Sdf, Usd

from conftest import validate_usda
from test_usd_python_examples import _author_radar_second_scan

DATA_DIR = Path(__file__).parent / "data"

RADAR = "/World/generic_radar"

# The first scan, s001, comes with the main schema; only s002 is applied explicitly.
API_SCHEMAS = ["OmniSensorGenericRadarWpmDmatAPI", "OmniSensorGenericRadarWpmDmatScanCfgAPI:s002"]
SCAN_VALUES = {
    "omni:sensor:WpmDmat:scan:s001:maxRangeM": 50.0,
    "omni:sensor:WpmDmat:scan:s001:raysPerDeg": 10.0,
    "omni:sensor:WpmDmat:scan:s002:maxRangeM": 300.0,
    "omni:sensor:WpmDmat:scan:s002:raysPerDeg": 8.0,
}


def test_radar_scan_configurations():
    """Validate radar_scan_configurations.usda: a second scan is one more apiSchemas entry plus its attributes."""
    layer = validate_usda((DATA_DIR / "radar_scan_configurations.usda").read_text())

    radar = layer.GetPrimAtPath(RADAR)
    assert radar, f"{RADAR} prim should exist"
    assert radar.typeName == "OmniRadar"
    assert list(radar.GetInfo("apiSchemas").prependedItems) == API_SCHEMAS

    for name, value in SCAN_VALUES.items():
        attribute = radar.attributes.get(name)
        assert attribute, f"{RADAR} should author {name}"
        assert attribute.typeName == Sdf.ValueTypeNames.Float
        assert attribute.default == value
    assert set(radar.attributes.keys()) == set(SCAN_VALUES)


def test_radar_scan_configurations_matches_python():
    """The Python tab of the how-to authors the same prim as the USDA tab."""
    expected = Usd.Stage.Open(str(DATA_DIR / "radar_scan_configurations.usda"))
    authored = expected.GetPrimAtPath(RADAR)

    stage = Usd.Stage.CreateInMemory()
    radar = _author_radar_second_scan(stage)

    assert radar.GetTypeName() == authored.GetTypeName()
    assert radar.GetMetadata("apiSchemas") == authored.GetMetadata("apiSchemas")
    expected_attributes = {attribute.GetName(): attribute for attribute in authored.GetAuthoredAttributes()}
    assert {attribute.GetName() for attribute in radar.GetAuthoredAttributes()} == set(expected_attributes)
    for name, attribute in expected_attributes.items():
        twin = radar.GetAttribute(name)
        assert twin.GetTypeName() == attribute.GetTypeName(), name
        assert twin.Get() == attribute.Get(), name
        assert twin.IsCustom() == attribute.IsCustom(), name
