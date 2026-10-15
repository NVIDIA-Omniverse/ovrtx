# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Validate the USDA snippet used by the Ghost Lights documentation page."""

from pathlib import Path

import pytest
from pxr import Sdf, Usd, UsdGeom, UsdRender

from conftest import validate_usda


DATA_DIR = Path(__file__).parent / "data"


def test_ghost_lights_usda():
    scene_path = DATA_DIR / "ghost_lights.usda"
    layer = validate_usda(scene_path.read_text())
    stage = Usd.Stage.Open(str(scene_path))
    assert stage
    assert layer.GetPrimAtPath("/World/Softbox")

    light = stage.GetPrimAtPath("/World/Softbox")
    assert light.GetTypeName() == "RectLight"
    assert light.GetAttribute("visibleInPrimaryRay").GetTypeName() == Sdf.ValueTypeNames.Bool
    assert light.GetAttribute("visibleInPrimaryRay").Get() is False
    assert light.GetAttribute("visibleInPrimaryRay").HasAuthoredValueOpinion()
    assert light.GetAttribute("ghostFactor").GetTypeName() == Sdf.ValueTypeNames.Float
    assert light.GetAttribute("ghostFactor").Get() == pytest.approx(0.5)
    assert light.GetAttribute("ghostFactor").HasAuthoredValueOpinion()

    subject = UsdGeom.Sphere(stage.GetPrimAtPath("/World/Subject"))
    ghost_primvar = UsdGeom.PrimvarsAPI(subject).GetPrimvar("omni:rtx:ghostFactor")
    assert ghost_primvar
    assert ghost_primvar.GetTypeName() == Sdf.ValueTypeNames.Float
    assert ghost_primvar.Get() == pytest.approx(1.0)
    assert ghost_primvar.GetAttr().HasAuthoredValueOpinion()
    assert ghost_primvar.GetInterpolation() == UsdGeom.Tokens.constant

    product = UsdRender.Product(stage.GetPrimAtPath("/Render/Camera"))
    assert product
    assert product.GetPrim().HasAPI("OmniRtxSettingsCommonAPI_1")
    assert product.GetPrim().GetAttribute("omni:rtx:lights:visibilityOverride").GetTypeName() == Sdf.ValueTypeNames.Token
    assert product.GetPrim().GetAttribute("omni:rtx:lights:reflectionVisibleRoughnessThreshold").GetTypeName() == Sdf.ValueTypeNames.Float
    assert product.GetPrim().GetAttribute("omni:rtx:lights:refractionVisibleRoughnessThreshold").GetTypeName() == Sdf.ValueTypeNames.Float
    assert product.GetPrim().GetAttribute("omni:rtx:lights:visibilityOverride").Get() == "perLight"
    assert product.GetPrim().GetAttribute("omni:rtx:lights:reflectionVisibleRoughnessThreshold").Get() == pytest.approx(0.15)
    assert product.GetPrim().GetAttribute("omni:rtx:lights:refractionVisibleRoughnessThreshold").Get() == pytest.approx(0.8)
