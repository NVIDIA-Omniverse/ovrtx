# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Validate the USDA snippet used by the Physical Lighting documentation."""

from pathlib import Path

from pxr import Usd, UsdLux

from conftest import validate_usda


DATA_DIR = Path(__file__).parent / "data"


def test_physical_lighting_usda():
    scene_path = DATA_DIR / "physical_lighting.usda"
    layer = validate_usda(scene_path.read_text())
    stage = Usd.Stage.Open(str(scene_path))
    assert stage
    assert layer.GetPrimAtPath("/World/LumenPanel")

    panel = stage.GetPrimAtPath("/World/LumenPanel")
    assert panel.GetTypeName() == "RectLight"
    assert panel.HasAPI("PhotometricAreaLightAPI")
    assert panel.HasAPI("PhysicalLightIlluminantAPI")
    assert panel.GetAttribute("photometric:power").Get() == 1600.0
    assert panel.GetAttribute("photometric:power").HasAuthoredValueOpinion()
    assert panel.GetAttribute("physical:illuminant").Get() == "blackbody"
    assert panel.GetAttribute("inputs:colorTemperature").Get() == 3000.0

    target = stage.GetPrimAtPath("/World/LuxTarget")
    assert target.GetTypeName() == "SphereLight"
    assert target.HasAPI("PhotometricAreaLightAPI")
    assert target.HasAPI("PhysicalLightIlluminantAPI")
    assert target.GetAttribute("photometric:power").Get() == 0.0
    assert target.GetAttribute("photometric:illuminance").Get() == 500.0
    assert target.GetAttribute("photometric:illuminance:distance").Get() == 2.0

    sun = stage.GetPrimAtPath("/World/Sun")
    assert sun.GetTypeName() == "DistantLight"
    assert sun.HasAPI("PhotometricDistantLightAPI")
    assert sun.HasAPI("PhysicalLightIlluminantAPI")
    assert sun.GetAttribute("photometric:illuminance").Get() == 10000.0
    assert sun.GetAttribute("photometric:illuminance").HasAuthoredValueOpinion()
    assert sun.GetAttribute("physical:illuminant").Get() == "illuminant D"
    assert sun.GetAttribute("inputs:colorTemperature").Get() == 6504.0


def test_photometric_schemas_auto_apply_physical_illuminant():
    stage = Usd.Stage.CreateInMemory()
    lights_and_schemas = (
        (UsdLux.RectLight.Define(stage, "/Area"), "PhotometricAreaLightAPI"),
        (UsdLux.DomeLight.Define(stage, "/Dome"), "PhotometricDomeLightAPI"),
        (UsdLux.DistantLight.Define(stage, "/Distant"), "PhotometricDistantLightAPI"),
    )
    for light, schema_name in lights_and_schemas:
        prim = light.GetPrim()
        assert prim.ApplyAPI(schema_name)
        assert prim.HasAPI(schema_name)
        assert prim.HasAPI("PhysicalLightIlluminantAPI")
