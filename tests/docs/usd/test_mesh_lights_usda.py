# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Validate the USDA snippets used by the Mesh Lights page."""

from pathlib import Path

import pytest
from conftest import validate_usda
from pxr import Sdf, Usd, UsdGeom, UsdShade

DATA_DIR = Path(__file__).parent / "data"
DOC_DATA_DIR = Path(__file__).parents[1] / "data"


def test_mesh_lights_usda():
    scene_path = DATA_DIR / "mesh_lights.usda"
    layer = validate_usda(scene_path.read_text())
    stage = Usd.Stage.Open(str(scene_path))
    assert stage
    assert layer.GetPrimAtPath("/World/Emitter")

    emitter = stage.GetPrimAtPath("/World/Emitter")
    assert emitter.GetTypeName() == "Mesh"
    assert "MeshLightAPI" not in emitter.GetAppliedSchemas()
    mesh = UsdGeom.Mesh(emitter)
    assert mesh.GetFaceVertexCountsAttr().Get() == [4]
    assert mesh.GetFaceVertexIndicesAttr().Get() == [0, 1, 2, 3]
    assert len(mesh.GetPointsAttr().Get()) == 4
    binding = UsdShade.MaterialBindingAPI(emitter).GetDirectBindingRel()
    assert binding.GetTargets() == [Sdf.Path("/World/Looks/Emitter")]

    material = UsdShade.Material(stage.GetPrimAtPath("/World/Looks/Emitter"))
    shader = stage.GetPrimAtPath("/World/Looks/Emitter/Shader")
    assert shader.GetAttribute("info:implementationSource").Get() == "sourceAsset"
    assert shader.GetAttribute("info:mdl:sourceAsset").Get() == Sdf.AssetPath(
        "OmniEmissive.mdl"
    )
    assert shader.GetAttribute("info:mdl:sourceAsset:subIdentifier").Get() == (
        "OmniEmissive"
    )
    assert shader.GetAttribute("inputs:emissive_color").Get() == (1.0, 1.0, 1.0)
    assert shader.GetAttribute("inputs:emission_intensity").Get() == pytest.approx(200)
    assert shader.GetAttribute("outputs:out").GetMetadata("renderType") == "material"
    connected = material.GetSurfaceOutput("mdl").GetConnectedSource()
    assert connected
    assert connected[0].GetPrim() == shader
    assert connected[1] == "out"

    product = stage.GetPrimAtPath("/Render/Camera")
    assert product.GetTypeName() == "RenderProduct"
    assert product.HasAPI("OmniRtxSettingsPtAdvancedAPI_1")
    assert product.GetAttribute("omni:rtx:pt:ris:meshLights").Get() is True
    assert product.GetAttribute("omni:rtx:rtpt:ris:meshLights").Get() is True


def test_runtime_mesh_light_fixture_is_material_driven():
    stage = Usd.Stage.Open(str(DOC_DATA_DIR / "ovrtx-light-test-mesh.usda"))
    assert stage
    emitter = stage.GetPrimAtPath(
        "/World/spiral_cfl/Fluorescent_Tube/Fluorescent_Tube"
    )
    assert emitter.GetTypeName() == "Mesh"
    assert "MaterialBindingAPI" in emitter.GetAppliedSchemas()
    assert "MeshLightAPI" not in emitter.GetAppliedSchemas()

    intrinsic_light_types = {
        "CylinderLight",
        "DiskLight",
        "DistantLight",
        "DomeLight",
        "RectLight",
        "SphereLight",
    }
    assert not any(
        prim.GetTypeName() in intrinsic_light_types for prim in stage.Traverse()
    )
