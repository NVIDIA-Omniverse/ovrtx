# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""Keep the runtime-texture USDA, authoring example, and README excerpts in sync."""
from pathlib import Path
import textwrap
import pytest
from pxr import Gf, Sdf, Usd, UsdShade, Vt

PUBLIC = Path(__file__).resolve().parents[3]


def test_runtime_texture_authoring():
    stage = Usd.Stage.CreateInMemory()
    # [snippet:doc-runtime-texture-usd-python]
    texture = stage.DefinePrim("/Texture", "OmniRuntimeTexture")
    texture.CreateAttribute("texture:uri", Sdf.ValueTypeNames.String, custom=False).Set("dynamic://runtimeTextureExample")
    texture.CreateAttribute("texture:dimension", Sdf.ValueTypeNames.Token, custom=False).Set("2d")
    texture.CreateAttribute("texture:extent", Sdf.ValueTypeNames.Int3, custom=False).Set(Gf.Vec3i(1, 1, 1))
    texture.CreateAttribute("texture:format", Sdf.ValueTypeNames.Token, custom=False).Set("rgba8unorm")
    texture.CreateAttribute("texture:colorSpace", Sdf.ValueTypeNames.Token, custom=False).Set("linear")
    texture.CreateAttribute("texture:data", Sdf.ValueTypeNames.UCharArray, custom=False).Set(Vt.UCharArray([255, 0, 0, 255]))

    material = UsdShade.Material.Define(stage, "/RuntimeMaterial")
    surface = UsdShade.Shader.Define(stage, "/RuntimeMaterial/Surface")
    surface.CreateIdAttr("UsdPreviewSurface")
    surface.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(1)
    surface.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    material.CreateSurfaceOutput().ConnectToSource(surface.ConnectableAPI(), "surface")
    tex = UsdShade.Shader.Define(stage, "/RuntimeMaterial/Tex")
    tex.CreateIdAttr("UsdUVTexture")
    tex.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath("dynamic://runtimeTextureExample"))
    tex.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
    surface.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(tex.ConnectableAPI(), "rgb")
    uv = UsdShade.Shader.Define(stage, "/RuntimeMaterial/UV")
    uv.CreateIdAttr("UsdPrimvarReader_float2")
    uv.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    uv.CreateOutput("result", Sdf.ValueTypeNames.Float2)
    tex.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(uv.ConnectableAPI(), "result")
    # [/snippet:doc-runtime-texture-usd-python]
    reference = Usd.Stage.Open(str(PUBLIC / "tests/docs/data/ovrtx-test-runtime-textures.usda"))
    assert not reference.GetCompositionErrors()
    definition = Usd.SchemaRegistry().FindConcretePrimDefinition("OmniRuntimeTexture")
    assert definition, "The package must register the runtime texture schema"
    for name, value in (("dimension", "2d"), ("extent", Gf.Vec3i(1, 1, 1)),
                        ("format", "rgba8unorm"), ("colorSpace", "linear")):
        assert definition.GetSchemaAttributeSpec("texture:" + name).default == value
    for prim in stage.Traverse():
        other = reference.GetPrimAtPath(prim.GetPath())
        assert other.GetTypeName() == prim.GetTypeName()
        assert {a.GetName() for a in other.GetAuthoredAttributes()} == {a.GetName() for a in prim.GetAuthoredAttributes()}
        for attr in prim.GetAuthoredAttributes():
            expected = other.GetAttribute(attr.GetName())
            assert attr.GetTypeName() == expected.GetTypeName()
            assert attr.Get() == expected.Get()
            assert attr.GetConnections() == expected.GetConnections()
    assert reference.GetPrimAtPath("/World/Plane").GetRelationship("material:binding").GetTargets() == [Sdf.Path("/RuntimeMaterial")]


@pytest.mark.parametrize("language,filename,marker", [
    ("c", "main.cpp", "doc-runtime-texture-c-update"),
    ("python", "main.py", "doc-runtime-texture-luminance"),
    ("python", "main.py", "doc-runtime-texture-camera-feedback"),
    ("python", "main.py", "doc-runtime-texture-carter-motion"),
])
def test_readme_snippets(language, filename, marker):
    directory = PUBLIC / "examples" / language / "runtime-textures"
    source = (directory / filename).read_text()
    prefix = "//" if language == "c" else "#"
    body = source.split(f"{prefix} [snippet:{marker}]\n")[1].split(f"{prefix} [/snippet:{marker}]")[0]
    body = textwrap.dedent(body).rstrip()
    assert body in (directory / "README.md").read_text()


def test_carter_monitor_scene():
    """The copied lineup retains only Carter and warehouse payloads, with a child camera and monitor."""
    scene = PUBLIC / "examples/python/runtime-textures/carter_monitor.usda"
    stage = Usd.Stage.Open(str(scene), load=Usd.Stage.LoadNone)
    original = Sdf.Layer.FindOrOpen(str(PUBLIC / "examples/python/semantic-segmentation/ovrtx-robot-lineup.usda"))
    layer = stage.GetRootLayer()
    payload_prims = [p for p in stage.TraverseAll() if p.HasAuthoredPayloads()]
    assert {str(p.GetPath()) for p in payload_prims} == {"/World/warehouse", "/World/carter_v1"}
    for prim in payload_prims:
        assert layer.GetPrimAtPath(prim.GetPath()).payloadList.prependedItems == original.GetPrimAtPath(prim.GetPath()).payloadList.prependedItems
    assert stage.GetPrimAtPath("/World/carter_v1/Camera").GetTypeName() == "Camera"
    assert stage.GetPrimAtPath("/Render/Robot").GetRelationship("camera").GetTargets() == [Sdf.Path("/World/carter_v1/Camera")]
    assert stage.GetPrimAtPath("/Texture").GetAttribute("texture:colorSpace").Get() == "sRGB"
    assert stage.GetPrimAtPath("/Texture").GetAttribute("texture:data").Get() == Vt.UCharArray([0, 0, 0, 255])
    shader = stage.GetPrimAtPath("/World/Monitor/Material/Tex")
    assert shader.GetAttribute("inputs:file").Get().path == "dynamic://carterMonitor"
    assert stage.GetPrimAtPath("/World/Monitor/Screen").GetRelationship("material:binding").GetTargets() == [Sdf.Path("/World/Monitor/Material")]
