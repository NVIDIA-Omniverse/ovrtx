# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Validate the two-camera scene and equivalent USD authoring."""

from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdGeom

SCENE = Path(__file__).parents[3] / "examples/c/sensor-observer/conveyor.usda"


def test_sensor_observer_scene():
    stage = Usd.Stage.Open(str(SCENE))
    assert UsdGeom.GetStageUpAxis(stage) == "Y"
    assert UsdGeom.GetStageMetersPerUnit(stage) == 0.01
    sensor = stage.GetPrimAtPath("/World/Sensor")
    observer = stage.GetPrimAtPath("/World/Observer")
    assert sensor.GetAttribute("omni:sensor:frameRate").Get() == Gf.Vec2d(30, 1)
    assert not observer.GetAttribute("omni:sensor:frameRate").HasAuthoredValueOpinion()
    for name in ("Sensor", "Observer"):
        product = stage.GetPrimAtPath(f"/Render/{name}")
        assert product.GetRelationship("camera").GetTargets() == [
            Sdf.Path(f"/World/{name}")
        ]
        assert product.GetRelationship("orderedVars").GetTargets() == [
            Sdf.Path(f"/Render/{name}/LdrColor")
        ]
        assert product.GetAttribute("deviceIds").Get() == [0]
    for name in ("Cube", "Sphere", "Cone"):
        assert any(
            prim.IsA(UsdGeom.Mesh)
            for prim in Usd.PrimRange(stage.GetPrimAtPath(f"/World/{name}"))
        )
    for layer in stage.GetUsedLayers():
        if not layer.anonymous:
            assert Path(layer.realPath).is_file()
    texture = (
        stage.GetPrimAtPath("/World/DomeLight")
        .GetAttribute("inputs:texture:file")
        .Get()
    )
    assert Path(texture.resolvedPath).is_file()


def test_author_sensor_observer_cameras():
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, "/World")
    # [snippet:doc-observer-cameras-python]
    sensor = UsdGeom.Camera.Define(stage, "/World/Sensor")
    sensor.GetPrim().AddAppliedSchema("OmniSensorAPI")
    # Only the simulated camera has a fixed capture rate.
    sensor.GetPrim().CreateAttribute(
        "omni:sensor:frameRate", Sdf.ValueTypeNames.Double2
    ).Set(Gf.Vec2d(30, 1))
    sensor.CreateFocalLengthAttr(24)
    sensor.AddTranslateOp().Set(Gf.Vec3d(0, 1000, 0))
    sensor.AddRotateXYZOp().Set(Gf.Vec3f(-90, 0, 0))

    # An ordinary camera with no exposure or fixed rate refreshes on every step.
    observer = UsdGeom.Camera.Define(stage, "/World/Observer")
    observer.CreateFocalLengthAttr(24)
    observer.AddTranslateOp().Set(Gf.Vec3d(900, 700, 1000))
    observer.AddRotateXYZOp().Set(Gf.Vec3f(-28, 42, 0))
    # [/snippet:doc-observer-cameras-python]
    reference = Usd.Stage.Open(str(SCENE))
    for camera in (sensor, observer):
        expected = reference.GetPrimAtPath(camera.GetPath())
        assert camera.GetPrim().GetMetadata("apiSchemas") == expected.GetMetadata(
            "apiSchemas"
        )
        for attribute in camera.GetPrim().GetAuthoredAttributes():
            assert attribute.Get() == expected.GetAttribute(attribute.GetName()).Get()
