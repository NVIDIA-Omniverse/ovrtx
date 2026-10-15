# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Validate the public mixed-sensor scene."""

from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdGeom


def test_multi_rate_scene_has_independent_products_and_local_assets():
    scene_path = Path(__file__).parents[3] / "examples/python/multi-rate-sensors/multi_rate.usda"
    stage = Usd.Stage.Open(str(scene_path))
    assert UsdGeom.GetStageUpAxis(stage) == "Y"
    assert UsdGeom.GetStageMetersPerUnit(stage) == 0.01
    for name, hz, output in (
        ("Lidar40", 40, "PointCloud"),
        ("Lidar20", 20, "PointCloud"),
        ("Camera10", 10, "LdrColor"),
        ("Camera20", 20, "LdrColor"),
    ):
        sensor = stage.GetPrimAtPath(f"/World/{name}")
        assert sensor.GetAttribute("omni:sensor:frameRate").Get() == Gf.Vec2d(hz, 1)
        if name.startswith("Lidar"):
            assert sensor.GetAttribute("omni:sensor:Core:partialOutputs").Get() is False
        product = stage.GetPrimAtPath(f"/Render/{name}")
        assert product.GetRelationship("camera").GetTargets() == [sensor.GetPath()]
        assert product.GetRelationship("orderedVars").GetTargets() == [Sdf.Path(f"/Render/{name}/{output}")]
        assert stage.GetPrimAtPath(f"/Render/{name}/{output}").GetAttribute("sourceName").Get() == output
    assert stage.GetPrimAtPath("/World/MovingCube/Cube")
    assert len(stage.GetPrimAtPath("/World/MovingCube").GetAttribute("xformOp:translate").GetTimeSamples()) == 3
    for layer in stage.GetUsedLayers():
        if not layer.anonymous:
            assert Path(layer.realPath).is_file()
    texture = stage.GetPrimAtPath("/World/DomeLight").GetAttribute("inputs:texture:file").Get()
    assert Path(texture.resolvedPath).is_file()
