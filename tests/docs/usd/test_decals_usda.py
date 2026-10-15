# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Validate USDA files used in materials/decals.rst."""

from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdShade

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


def test_decals_example_scene():
    """Validate the shared scene used by the Python and C examples."""
    scene = DATA_DIR.parent.parent / "data/ovrtx-test-decals.usda"
    stage = Usd.Stage.Open(str(scene))
    assert stage.GetPrimAtPath("/Render/Camera").GetAttribute("omni:rtx:rendermode").Get() == "PathTracing"
    receiver = stage.GetPrimAtPath("/World/logo/logo/logo")
    assert receiver.GetTypeName() == "Mesh"
    assert stage.GetPrimAtPath("/World/logo").GetAttribute("visibility").Get() != "invisible"
    for name in ("RedRTXA", "RedRTXB", "RedRTXC", "SilverLogoA", "SilverLogoB", "SilverLogoC"):
        assert receiver.GetRelationship(f"coordSys:{name}:binding").GetTargets() == [Sdf.Path(f"/World/{name}")]
        decal = stage.GetPrimAtPath(f"/World/{name}")
        assert decal.GetTypeName() == "OmniDecal"
        assert decal.GetAttribute("omni:decal:priority").Get() == (0 if name.startswith("RedRTX") else 10)
        assert len(decal.GetAttribute("extent").Get()) == 2
        # Width and height are twice the original example; depth stays at 12.
        width = 16 if name == "RedRTXA" else 13 if name.startswith("RedRTX") else 10.6
        assert decal.GetAttribute("xformOp:scale").Get() == Gf.Vec3f(width, width, 12)
    # The ground must not receive any sticker bindings.
    assert not any("Decal" in str(r.GetName()) or "Logo" in str(r.GetName())
                   for r in stage.GetPrimAtPath("/World/Plane").GetRelationships())
    for material, mask in (("RedMaterial", "decal-rtx-mask.png"), ("SilverMaterial", "decal-nvidia-mask.png")):
        shader = stage.GetPrimAtPath(f"/World/Looks/{material}/Shader")
        assert shader.GetAttribute("inputs:enable_opacity").Get()
        texture = shader.GetAttribute("inputs:geometry_opacity_image").Get()
        assert Path(texture.resolvedPath) == scene.parent / mask
    assert stage.GetPrimAtPath("/World/Looks/SilverMaterial/Shader").GetAttribute("inputs:metalness").Get() == 1


def test_decal_ordering_python_matches_usda():
    """Changing priority alone reverses the two material groups' ordering."""
    data = DATA_DIR.parent.parent / "data"
    stage = Usd.Stage.CreateInMemory()
    stage.GetRootLayer().subLayerPaths = [str(data / "ovrtx-test-decals.usda")]
    # [snippet:doc-decal-ordering-python]
    decal = stage.OverridePrim("/World/RedRTXA")
    # Silver stays at 10. Raising red from 0 to 20 puts red on top.
    # RedRTXB and RedRTXC inherit this value from RedRTXA.
    decal.CreateAttribute("omni:decal:priority", Sdf.ValueTypeNames.Int, custom=False).Set(20)
    # [/snippet:doc-decal-ordering-python]
    authored = Usd.Stage.Open(str(data / "ovrtx-test-decals-red-on-top.usda"))
    baseline = Usd.Stage.Open(str(data / "ovrtx-test-decals.usda"))
    for name in ("RedRTXA", "RedRTXB", "RedRTXC", "SilverLogoA", "SilverLogoB", "SilverLogoC"):
        path = f"/World/{name}"
        for attr in stage.GetPrimAtPath(path).GetAuthoredAttributes():
            assert attr.Get() == authored.GetPrimAtPath(path).GetAttribute(attr.GetName()).Get()
            if attr.GetName() != "omni:decal:priority":
                assert attr.Get() == baseline.GetPrimAtPath(path).GetAttribute(attr.GetName()).Get()
        assert authored.GetPrimAtPath(path).GetAttribute("omni:decal:priority").Get() == (
            20 if name.startswith("RedRTX") else 10
        )


def test_silver_mask_python_matches_usda():
    """Keep the material-parameter authoring tabs equivalent."""
    stage = Usd.Stage.CreateInMemory()
    shader = UsdShade.Shader.Define(stage, "/World/Looks/SilverMaterial/Shader")
    # [snippet:doc-decal-silver-mask-python]
    shader.CreateInput("diffuse_reflection_color", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.95))
    shader.CreateInput("metalness", Sdf.ValueTypeNames.Float).Set(1.0)
    shader.CreateInput("specular_reflection_roughness", Sdf.ValueTypeNames.Float).Set(0.55)
    shader.CreateInput("enable_opacity", Sdf.ValueTypeNames.Bool).Set(True)
    shader.CreateInput("geometry_opacity_image", Sdf.ValueTypeNames.Asset).Set("./decal-nvidia-mask.png")
    # Read the mask's red channel, not a missing alpha channel.
    shader.CreateInput("geometry_opacity_image_alpha_mode", Sdf.ValueTypeNames.Int).Set(1)
    # [/snippet:doc-decal-silver-mask-python]
    scene = Usd.Stage.Open(str(DATA_DIR.parent.parent / "data/ovrtx-test-decals.usda"))
    authored = scene.GetPrimAtPath(shader.GetPath())
    for attribute in shader.GetPrim().GetAuthoredAttributes():
        expected = authored.GetAttribute(attribute.GetName())
        assert attribute.GetTypeName() == expected.GetTypeName()
        actual_value, expected_value = attribute.Get(), expected.Get()
        if isinstance(actual_value, Sdf.AssetPath):
            assert actual_value.path == expected_value.path
        else:
            assert actual_value == expected_value
