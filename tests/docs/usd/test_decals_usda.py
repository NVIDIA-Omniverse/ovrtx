# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Validate USDA files used in materials/decals.rst."""

from pathlib import Path

from pxr import Sdf

from conftest import validate_usda

DATA_DIR = Path(__file__).parent / "data"


def _validate_decal(layer):
    decal = layer.GetPrimAtPath("/World/Decal")
    assert decal, "/World/Decal prim should exist"
    assert decal.typeName == "OmniDecal"
    assert "MaterialBindingAPI" in decal.GetInfo("apiSchemas").GetAddedOrExplicitItems()

    material = layer.GetPrimAtPath("/World/Looks/DecalMaterial")
    assert material, "/World/Looks/DecalMaterial prim should exist"
    assert material.typeName == "Material"

    material_binding = decal.relationships["material:binding"]
    assert material_binding.targetPathList.GetAddedOrExplicitItems() == (
        Sdf.Path("/World/Looks/DecalMaterial"),
    )

    extent = decal.attributes["extent"]
    assert extent.typeName == Sdf.ValueTypeNames.Float3Array
    assert len(extent.default) == 2

    expected_attributes = {
        "omni:decal:enabled": (Sdf.ValueTypeNames.Bool, True),
        "omni:decal:faceMode": (Sdf.ValueTypeNames.Token, "front"),
        "omni:decal:outputSpace": (Sdf.ValueTypeNames.Int, 0),
        "omni:decal:priority": (Sdf.ValueTypeNames.Int, 0),
        "omni:projector:space": (Sdf.ValueTypeNames.Token, "object"),
        "omni:projector:type": (Sdf.ValueTypeNames.Token, "planar"),
    }
    for name, (type_name, value) in expected_attributes.items():
        attribute = decal.attributes[name]
        assert attribute.typeName == type_name
        assert attribute.default == value


def test_create_decal():
    """Validate the authored OmniDecal, material binding, and attributes."""
    usda_text = (DATA_DIR / "decal.usda").read_text()
    layer = validate_usda(usda_text)
    _validate_decal(layer)


def test_bind_decal():
    """Validate the Cube's coordinate-system binding to the decal."""
    usda_text = (DATA_DIR / "decal_binding.usda").read_text()
    layer = validate_usda(usda_text)
    _validate_decal(layer)

    cube = layer.GetPrimAtPath("/World/Cube")
    assert cube, "/World/Cube prim should exist"
    assert cube.typeName == "Cube"
    assert "OmniCoordSysAPI:Decal" in cube.GetInfo("apiSchemas").GetAddedOrExplicitItems()
    binding = cube.relationships["coordSys:Decal:binding"]
    assert binding.targetPathList.GetAddedOrExplicitItems() == (Sdf.Path("/World/Decal"),)
