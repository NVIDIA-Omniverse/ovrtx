# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Check the documented DLSS-NR configuration; this does not render an image."""

from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdRender


def test_dlss_nr_render_product_authoring():
    """Keep USDA and Python configuration equivalent and verify the enabling contract."""
    stage = Usd.Stage.CreateInMemory()
    stage.DefinePrim("/World/Camera", "Camera")

    # [snippet:doc-dlss-nr-render-product-python]
    from pxr import Gf, Sdf, UsdRender

    stage.DefinePrim("/Render", "Scope")
    product = UsdRender.Product.Define(stage, "/Render/Camera")
    product.CreateResolutionAttr(Gf.Vec2i(1280, 720))
    product.CreateCameraRel().SetTargets(["/World/Camera"])
    product.CreateOrderedVarsRel().SetTargets(["/Render/Camera/LdrColor"])

    # Neural rendering requires real-time path tracing and an LDR output.
    prim = product.GetPrim()
    prim.CreateAttribute("omni:rtx:rendermode", Sdf.ValueTypeNames.Token, custom=False).Set("RealTimePathTracing")
    # OmniRtxPostDlssNrAPI_1 is automatically applied to RenderProducts.
    prim.GetAttribute("omni:rtx:dlssnr:enabled").Set(True)

    render_var = UsdRender.Var.Define(stage, "/Render/Camera/LdrColor")
    render_var.CreateSourceNameAttr("LdrColor")
    # [/snippet:doc-dlss-nr-render-product-python]

    reference = Usd.Stage.Open(str(Path(__file__).with_name("data") / "dlss_nr.usda"))
    assert reference and not reference.GetCompositionErrors()
    # Check both directions so added or removed attributes and relationships cannot drift silently.
    for path in ("/Render", "/Render/Camera", "/Render/Camera/LdrColor"):
        actual = stage.GetPrimAtPath(path)
        expected = reference.GetPrimAtPath(path)
        assert actual.GetTypeName() == expected.GetTypeName()
        assert actual.GetAppliedSchemas() == expected.GetAppliedSchemas()
        assert {attr.GetName() for attr in actual.GetAuthoredAttributes()} == {
            attr.GetName() for attr in expected.GetAuthoredAttributes()
        }
        for attr in expected.GetAuthoredAttributes():
            counterpart = actual.GetAttribute(attr.GetName())
            assert counterpart.GetTypeName() == attr.GetTypeName()
            assert counterpart.IsCustom() == attr.IsCustom()
            assert counterpart.Get() == attr.Get()
        assert {rel.GetName() for rel in actual.GetAuthoredRelationships()} == {
            rel.GetName() for rel in expected.GetAuthoredRelationships()
        }
        for rel in expected.GetAuthoredRelationships():
            assert actual.GetRelationship(rel.GetName()).GetTargets() == rel.GetTargets()

    # Independently assert the public feature gates, not just agreement between two snippets.
    assert prim.HasAPI("OmniRtxPostDlssNrAPI_1")
    assert prim.GetAttribute("omni:rtx:rendermode").Get() == "RealTimePathTracing"
    enabled = prim.GetAttribute("omni:rtx:dlssnr:enabled")
    assert enabled.GetTypeName() == Sdf.ValueTypeNames.Bool and not enabled.IsCustom()
    assert enabled.Get() is True
    assert product.GetCameraRel().GetTargets() == [Sdf.Path("/World/Camera")]
    assert stage.GetPrimAtPath("/World/Camera").GetTypeName() == "Camera"
    assert product.GetOrderedVarsRel().GetTargets() == [render_var.GetPath()]
    assert render_var.GetSourceNameAttr().Get() == "LdrColor"
