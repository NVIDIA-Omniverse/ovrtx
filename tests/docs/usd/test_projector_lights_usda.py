# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Validate the USDA snippet used by the Rect Light projector section."""

from pathlib import Path

import pytest
from pxr import Sdf, Usd

from conftest import validate_usda


DATA_DIR = Path(__file__).parent / "data"


def test_projector_light_usda():
    scene_path = DATA_DIR / "projector_lights.usda"
    layer = validate_usda(scene_path.read_text())
    stage = Usd.Stage.Open(str(scene_path))
    assert stage
    assert layer.GetPrimAtPath("/World/Projector")

    projector = stage.GetPrimAtPath("/World/Projector")
    assert projector.GetTypeName() == "RectLight"
    assert projector.GetAttribute("isProjector").GetTypeName() == Sdf.ValueTypeNames.Bool
    assert projector.GetAttribute("isProjector").Get() is True
    assert projector.GetAttribute("inputs:width").Get() == pytest.approx(1.5)
    assert projector.GetAttribute("inputs:height").Get() == pytest.approx(1.0)
    assert projector.GetAttribute("inputs:intensity").Get() == pytest.approx(10000.0)

    color = projector.GetAttribute("inputs:texture:file")
    direction = projector.GetAttribute("projector:directionTexture:file")
    assert color.GetTypeName() == Sdf.ValueTypeNames.Asset
    assert direction.GetTypeName() == Sdf.ValueTypeNames.Asset
    assert color.Get().path == "../../data/chelsea.png"
    assert direction.Get().path == "../../data/projector-fisheye-direction.exr"
    assert Path(color.Get().resolvedPath).is_file()
    assert Path(direction.Get().resolvedPath).is_file()
