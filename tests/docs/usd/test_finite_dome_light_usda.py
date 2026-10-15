# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Validate finite dome scenes and snippets used by the Dome Light page."""

from pathlib import Path

import pytest
from pxr import Sdf, Usd, UsdGeom

from conftest import validate_usda


DATA_DIR = Path(__file__).parent / "data"
SCENE_DIR = Path(__file__).parents[1] / "data"


def test_finite_dome_light_snippet():
    scene_path = DATA_DIR / "finite_dome_lights.usda"
    layer = validate_usda(scene_path.read_text())
    stage = Usd.Stage.Open(str(scene_path))
    assert stage
    assert layer.GetPrimAtPath("/World/Studio")

    dome = stage.GetPrimAtPath("/World/Studio")
    assert dome.GetTypeName() == "DomeLight"
    assert dome.HasAPI("OmniFiniteDomeLightAPI")
    assert dome.HasAPI("CoordSysAPI", "domeGeometry")
    assert dome.GetAttribute("inputs:texture:file").Get().path == "../../data/studio.exr"
    assert dome.GetAttribute("inputs:texture:format").Get() == "latlong"
    assert dome.GetAttribute("omni:rtx:domeLight:mode").Get() == "sphereWithGround"
    assert dome.GetAttribute("omni:rtx:domeLight:radius").Get() == 5.0
    assert tuple(dome.GetAttribute("omni:rtx:domeLight:size").Get()) == pytest.approx((10.0, 6.0, 8.0))
    assert dome.GetAttribute("omni:rtx:domeLight:groundTextureScale").Get() == 10.0
    assert dome.GetRelationship("coordSys:domeGeometry:binding").GetTargets() == [
        Sdf.Path("/World/DomeGeometry")
    ]
    geometry = UsdGeom.Xformable(stage.GetPrimAtPath("/World/DomeGeometry"))
    assert geometry
    assert geometry.GetXformOpOrderAttr().Get() == ["xformOp:translate", "xformOp:scale"]
    assert tuple(geometry.GetPrim().GetAttribute("xformOp:translate").Get()) == pytest.approx((0.0, 2.0, 0.0))
    assert tuple(geometry.GetPrim().GetAttribute("xformOp:scale").Get()) == pytest.approx((1.0, 1.0, 1.0))


@pytest.mark.parametrize(
    ("mode", "filename", "geometry_scale"),
    (
        ("infinite", "ovrtx-light-test-finite-dome-infinite.usda", 0.4368),
        ("ground", "ovrtx-light-test-finite-dome-ground.usda", 0.4368),
        ("sphere", "ovrtx-light-test-finite-dome-sphere.usda", 0.61152),
        ("box", "ovrtx-light-test-finite-dome-box.usda", 0.4368),
        ("sphereWithGround", "ovrtx-light-test-finite-dome-sphere-with-ground.usda", 0.61152),
        ("boxWithGround", "ovrtx-light-test-finite-dome-box-with-ground.usda", 0.4368),
    ),
)
def test_finite_dome_render_scene(mode, filename, geometry_scale):
    scene_path = SCENE_DIR / filename
    layer = validate_usda(scene_path.read_text())
    assert layer.GetPrimAtPath("/World/DomeLight")

    stage = Usd.Stage.Open(str(scene_path), load=Usd.Stage.LoadNone)
    assert stage
    dome = stage.GetPrimAtPath("/World/DomeLight")
    assert dome.GetTypeName() == "DomeLight"
    assert dome.HasAPI("OmniFiniteDomeLightAPI")
    assert dome.HasAPI("CoordSysAPI", "domeGeometry")
    assert dome.GetAttribute("omni:rtx:domeLight:mode").Get() == mode
    assert dome.GetAttribute("omni:rtx:domeLight:radius").Get() == 100.0
    assert tuple(dome.GetAttribute("omni:rtx:domeLight:size").Get()) == pytest.approx((200.0, 200.0, 200.0))
    assert dome.GetAttribute("inputs:texture:file").Get().path == "./studio.exr"
    assert dome.GetAttribute("inputs:texture:format").Get() == "latlong"
    assert dome.GetRelationship("coordSys:domeGeometry:binding").GetTargets() == [
        Sdf.Path("/World/Xform")
    ]
    geometry = UsdGeom.Xformable(stage.GetPrimAtPath("/World/Xform"))
    assert geometry
    assert tuple(geometry.GetPrim().GetAttribute("xformOp:translate").Get()) == pytest.approx(
        (-34.36327759159764, 43.09919668261778, -1.1859344823036508)
    )
    assert tuple(geometry.GetPrim().GetAttribute("xformOp:scale").Get()) == pytest.approx(
        (geometry_scale, geometry_scale, geometry_scale)
    )
