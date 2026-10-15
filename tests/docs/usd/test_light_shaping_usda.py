# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Validate USDA snippets used by the Shaping & IES documentation page."""

from pathlib import Path

import pytest
from pxr import Sdf, Usd, UsdLux

from conftest import validate_usda


DATA_DIR = Path(__file__).parent / "data"


def test_light_shaping():
    scene_path = DATA_DIR / "light_shaping.usda"
    validate_usda(scene_path.read_text())
    stage = Usd.Stage.Open(str(scene_path))
    assert stage

    shaped_light = UsdLux.RectLight(stage.GetPrimAtPath("/World/ShapedPanel"))
    shaping = UsdLux.ShapingAPI(shaped_light.GetPrim())
    assert shaping
    assert shaping.GetShapingConeAngleAttr().Get() == pytest.approx(45)
    assert shaping.GetShapingConeSoftnessAttr().Get() == pytest.approx(0.25)
    assert shaping.GetShapingFocusAttr().Get() == pytest.approx(2)
    assert tuple(shaping.GetShapingFocusTintAttr().Get()) == pytest.approx((0.1, 0.2, 1))
    assert shaped_light.GetPrim().GetAttribute("omni:rtx:shaping:forwardAxis").Get() == "-Z"

    ies_light = UsdLux.DiskLight(stage.GetPrimAtPath("/World/IesDownlight"))
    ies_shaping = UsdLux.ShapingAPI(ies_light.GetPrim())
    assert ies_shaping.GetShapingIesAngleScaleAttr().Get() == pytest.approx(1)
    assert ies_shaping.GetShapingIesNormalizeAttr().Get() is True

    ies_asset = ies_shaping.GetShapingIesFileAttr().Get()
    expected_path = (DATA_DIR.parent.parent / "data/ies/bega-50898.4K3.ies").resolve()
    assert ies_asset == Sdf.AssetPath("../../data/ies/bega-50898.4K3.ies", str(expected_path))
