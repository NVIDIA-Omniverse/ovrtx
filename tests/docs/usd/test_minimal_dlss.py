# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Validate the Minimal DLSS scene and the equivalent USD authoring snippet."""

from pathlib import Path

from pxr import Gf, Pcp, Sdf, Usd, UsdGeom, UsdRender

SCENE = Path(__file__).resolve().parents[3] / "examples/python/minimal-dlss/minimal_dlss.usda"
TEST_SCENE = Path(__file__).resolve().parents[1] / "data" / "minimal_dlss_test_scene.usda"


def test_minimal_dlss_schema_default_and_overrides():
    definition = Usd.SchemaRegistry().FindAppliedAPIPrimDefinition("OmniRtxSettingsMinimalAPI_1")
    assert definition
    mode_spec = definition.GetSchemaAttributeSpec("omni:rtx:minimal:dlss:mode")
    assert mode_spec, "Minimal DLSS mode must be declared in the Minimal API schema"
    assert mode_spec.typeName == Sdf.ValueTypeNames.Int
    assert mode_spec.default == 0

    stage = Usd.Stage.CreateInMemory()
    prim = UsdRender.Product.Define(stage, "/Render/Camera").GetPrim()
    assert prim.ApplyAPI("OmniRtxSettingsMinimalAPI_1")
    mode = prim.GetAttribute("omni:rtx:minimal:dlss:mode")
    assert mode and not mode.IsCustom()
    assert not mode.HasAuthoredValueOpinion()
    assert mode.Get() == 0

    for value in (0, 1, 2):
        assert mode.Set(value)
        assert mode.HasAuthoredValueOpinion()
        assert mode.Get() == value

    assert mode.Clear()
    assert not mode.HasAuthoredValueOpinion()
    assert mode.Get() == 0


def test_minimal_dlss_usd_python():
    stage = Usd.Stage.CreateInMemory()

    # [snippet:doc-minimal-dlss-render-product-python]
    from pxr import Gf, Sdf, UsdRender

    stage.DefinePrim("/Render", "Scope")
    product = UsdRender.Product.Define(stage, "/Render/Camera")
    prim = product.GetPrim()
    prim.AddAppliedSchema("OmniRtxSettingsMinimalAPI_1")
    product.CreateCameraRel().SetTargets(["/World/Camera"])
    product.CreateResolutionAttr(Gf.Vec2i(1280, 720))
    product.CreateOrderedVarsRel().SetTargets(["/Render/Camera/LdrColor"])
    prim.CreateAttribute("omni:rtx:rendermode", Sdf.ValueTypeNames.Token, custom=False).Set("MinimalRendering")
    prim.CreateAttribute("omni:rtx:minimal:mode", Sdf.ValueTypeNames.Int, custom=False).Set(2)

    # DLSS selection is an integer; the resolution preset is a token.
    prim.CreateAttribute("omni:rtx:minimal:dlss:mode", Sdf.ValueTypeNames.Int, custom=False).Set(1)
    prim.CreateAttribute("omni:rtx:minimal:dlss:execMode", Sdf.ValueTypeNames.Token, custom=False).Set("quality")
    # Keep small robots visible inside the warehouse.
    prim.CreateAttribute("omni:rtx:minimal:castShadows", Sdf.ValueTypeNames.Bool, custom=False).Set(False)

    render_var = UsdRender.Var.Define(stage, "/Render/Camera/LdrColor")
    render_var.CreateSourceNameAttr("LdrColor")
    # [/snippet:doc-minimal-dlss-render-product-python]

    authored = Usd.Stage.Open(str(SCENE), load=Usd.Stage.LoadNone)
    reference = authored.GetPrimAtPath("/Render/Camera")
    assert reference.GetTypeName() == prim.GetTypeName() == "RenderProduct"
    assert reference.GetMetadata("apiSchemas") == prim.GetMetadata("apiSchemas")
    # Compare the attribute name sets first so drift in either direction is reported by name.
    reference_names = {attr.GetName() for attr in reference.GetAuthoredAttributes()}
    python_names = {attr.GetName() for attr in prim.GetAuthoredAttributes()}
    assert reference_names == python_names, (
        f"USDA only: {sorted(reference_names - python_names)}, "
        f"Python only: {sorted(python_names - reference_names)}"
    )
    for attr in reference.GetAuthoredAttributes():
        equivalent = prim.GetAttribute(attr.GetName())
        assert equivalent.GetTypeName() == attr.GetTypeName()
        assert equivalent.Get() == attr.Get()
    for rel in reference.GetAuthoredRelationships():
        assert prim.GetRelationship(rel.GetName()).GetTargets() == rel.GetTargets()
    assert authored.GetPrimAtPath("/World/Camera").GetTypeName() == "Camera"
    assert UsdRender.Var(authored.GetPrimAtPath("/Render/Camera/LdrColor")).GetSourceNameAttr().Get() == "LdrColor"


def _used_layer_paths(stage):
    # Compare resolved Paths rather than strings so separator or drive-letter case
    # differences between Ar's resolved paths and pathlib cannot cause false mismatches.
    return {Path(layer.realPath).resolve() for layer in stage.GetUsedLayers() if layer.realPath}


def test_minimal_dlss_assets_resolve():
    # usd-core validates local composition; the runtime tests load the remote payloads.
    stage = Usd.Stage.Open(str(SCENE), load=Usd.Stage.LoadNone)
    assert stage.GetMetadata("metersPerUnit") == 1
    assert stage.GetMetadata("upAxis") == "Z"
    lineup = SCENE.parent / "../semantic-segmentation/ovrtx-robot-lineup.usda"
    assert lineup.resolve() in _used_layer_paths(stage)
    assert [str(prim.GetPath()) for prim in stage.Traverse() if prim.IsA(UsdRender.Product)] == ["/Render/Camera"]
    for name in ("warehouse", "spot", "jetbot", "kaya"):
        prim = stage.GetPrimAtPath(f"/World/{name}")
        assert prim and prim.HasAuthoredPayloads(), f"Missing lineup asset: {name}"


def test_minimal_dlss_test_scene_replaces_remote_payloads_with_local_geometry():
    # GitHub CI cannot load the robot lineup's remote payloads, so the runtime tests
    # render this local scene. It must keep the shipped RenderProduct and camera path.
    stage = Usd.Stage.Open(str(TEST_SCENE), load=Usd.Stage.LoadAll)
    used = _used_layer_paths(stage)
    assert SCENE in used, "The test scene must sublayer the shipped example scene"
    lineup = (SCENE.parent / "../semantic-segmentation/ovrtx-robot-lineup.usda").resolve()
    assert lineup not in used, "The test scene must replace the robot lineup reference"
    # Unopenable remote layers never appear in GetUsedLayers, so check the
    # composed prims instead: only the local logo payload may remain.
    assert not stage.GetCompositionErrors()
    payload_prims = [str(prim.GetPath()) for prim in stage.Traverse() if prim.HasAuthoredPayloads()]
    assert payload_prims == ["/World/logo"], payload_prims
    assert stage.GetMetadata("upAxis") == "Y"
    assert stage.GetMetadata("metersPerUnit") == 0.01
    assert any(prim.IsA(UsdGeom.Mesh) for prim in stage.Traverse()), "The test scene has no local geometry"
    # /World must compose exactly one local reference; `prepend references` would keep the lineup too.
    arcs = Usd.PrimCompositionQuery(stage.GetPrimAtPath("/World")).GetCompositionArcs()
    refs = [arc for arc in arcs if arc.GetArcType() == Pcp.ArcTypeReference]
    assert len(refs) == 1
    assert Path(refs[0].GetTargetNode().layerStack.identifier.rootLayer.realPath).resolve() == (
        TEST_SCENE.parent / "ovrtx-test-base-no-light.usda"
    )
    camera = stage.GetPrimAtPath("/World/Camera")
    assert camera.GetTypeName() == "Camera"
    # The focal length override frames the reference image; the test base authors 40.
    assert UsdGeom.Camera(camera).GetFocalLengthAttr().Get() == 28

    product = UsdRender.Product(stage.GetPrimAtPath("/Render/Camera"))
    assert product.GetCameraRel().GetTargets() == [Sdf.Path("/World/Camera")]
    assert [str(prim.GetPath()) for prim in stage.Traverse() if prim.IsA(UsdRender.Product)] == ["/Render/Camera"]
    prim = product.GetPrim()
    shipped_stage = Usd.Stage.Open(str(SCENE), load=Usd.Stage.LoadNone)
    shipped = shipped_stage.GetPrimAtPath("/Render/Camera")
    for attr in shipped.GetAuthoredAttributes():
        assert prim.GetAttribute(attr.GetName()).Get() == attr.Get(), attr.GetName()
    # The local test base has no lights; ambient light keeps the comparison visible.
    assert prim.GetAttribute("omni:rtx:sceneDb:ambientLightIntensity").Get() == 1


def test_minimal_dlss_readme_snippet_matches_example_source():
    # README.md duplicates the literalinclude'd snippet by hand; keep the copy in sync.
    import textwrap

    source = (SCENE.parent / "main.py").read_text()
    start = source.index("# [snippet:doc-render-minimal-dlss-python]\n")
    start = source.index("\n", start) + 1
    end = source.index("# [/snippet:doc-render-minimal-dlss-python]", start)
    source_snippet = textwrap.dedent(source[start:end]).rstrip()

    readme = (SCENE.parent / "README.md").read_text()
    start = readme.index("```python\n") + len("```python\n")
    end = readme.index("\n```", start)
    assert readme[start:end] == source_snippet
