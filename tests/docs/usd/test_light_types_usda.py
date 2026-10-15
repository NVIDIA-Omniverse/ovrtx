# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Validate USDA snippets used by the Lights documentation pages."""

from pathlib import Path

import pytest
from pxr import Sdf, Usd, UsdLux

from conftest import validate_usda


DATA_DIR = Path(__file__).parent / "data"


def test_light_types():
    scene_path = DATA_DIR / "light_types.usda"
    layer = validate_usda(scene_path.read_text())
    stage = Usd.Stage.Open(str(scene_path))
    assert stage

    expected_types = {
        "/World/KeyLight": "SphereLight",
        "/World/Sun": "DistantLight",
        "/World/Bulb": "SphereLight",
        "/World/Panel": "RectLight",
        "/World/Downlight": "DiskLight",
        "/World/Tube": "CylinderLight",
        "/World/Environment": "DomeLight",
    }
    for path, type_name in expected_types.items():
        prim = layer.GetPrimAtPath(path)
        assert prim, f"{path} prim should exist"
        assert prim.typeName == type_name

    common = UsdLux.SphereLight(stage.GetPrimAtPath("/World/KeyLight")).LightAPI()
    common_values = {
        common.GetColorAttr(): (1.0, 0.85, 0.7),
        common.GetColorTemperatureAttr(): 4500.0,
        common.GetDiffuseAttr(): 1.0,
        common.GetEnableColorTemperatureAttr(): True,
        common.GetExposureAttr(): 2.0,
        common.GetIntensityAttr(): 1000.0,
        common.GetNormalizeAttr(): False,
        common.GetSpecularAttr(): 1.0,
    }
    for attribute, expected in common_values.items():
        assert attribute.HasAuthoredValueOpinion()
        if isinstance(expected, tuple):
            assert tuple(attribute.Get()) == pytest.approx(expected)
        else:
            assert attribute.Get() == expected

    distant = UsdLux.DistantLight(stage.GetPrimAtPath("/World/Sun"))
    assert distant.GetAngleAttr().Get() == pytest.approx(0.53)
    assert distant.LightAPI().GetIntensityAttr().Get() == 50000.0
    assert distant.LightAPI().GetNormalizeAttr().Get() is True

    sphere = UsdLux.SphereLight(stage.GetPrimAtPath("/World/Bulb"))
    assert sphere.GetRadiusAttr().Get() == pytest.approx(0.05)
    assert sphere.GetTreatAsPointAttr().Get() is False
    assert sphere.GetTreatAsPointAttr().HasAuthoredValueOpinion()

    rect = UsdLux.RectLight(stage.GetPrimAtPath("/World/Panel"))
    assert rect.GetHeightAttr().Get() == pytest.approx(0.6)
    assert rect.GetWidthAttr().Get() == pytest.approx(1.2)

    disk = UsdLux.DiskLight(stage.GetPrimAtPath("/World/Downlight"))
    assert disk.GetRadiusAttr().Get() == pytest.approx(0.25)

    cylinder = UsdLux.CylinderLight(stage.GetPrimAtPath("/World/Tube"))
    assert cylinder.GetLengthAttr().Get() == pytest.approx(1.2)
    assert cylinder.GetRadiusAttr().Get() == pytest.approx(0.025)
    assert cylinder.GetTreatAsLineAttr().Get() is False
    assert cylinder.GetTreatAsLineAttr().HasAuthoredValueOpinion()

    dome = UsdLux.DomeLight(stage.GetPrimAtPath("/World/Environment"))
    texture = dome.GetTextureFileAttr().Get()
    assert texture == Sdf.AssetPath(
        "../../data/studio.exr",
        str((DATA_DIR.parent.parent / "data/studio.exr").resolve()),
    )
    assert dome.GetTextureFormatAttr().Get() == UsdLux.Tokens.latlong
