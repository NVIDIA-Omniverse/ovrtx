# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Validate documented authoring and every composed comparison variant."""

from pathlib import Path

import pytest
from pxr import Sdf, Usd, UsdLux, UsdRender

PUBLIC = Path(__file__).parents[3]
SCENE = PUBLIC / "examples/python/spectral-rendering/spectral.usda"


def test_spectral_authoring_parity():
    """Both documentation tabs must author the same properties and schema application."""
    stage = Usd.Stage.CreateInMemory()
    # [snippet:doc-spectral-authoring-python]
    from pxr import Sdf, UsdLux, UsdRender

    light = UsdLux.RectLight.Define(stage, "/World/RectLight")
    light.GetPrim().ApplyAPI("PhysicalLightIlluminantAPI")
    light.GetPrim().CreateAttribute("physical:illuminant", Sdf.ValueTypeNames.Token).Set("blackbody")
    light.GetColorTemperatureAttr().Set(3000)
    light.GetEnableColorTemperatureAttr().Set(False)

    product = UsdRender.Product.Define(stage, "/Render/Camera")
    product.GetCameraRel().SetTargets(["/World/Camera"])
    prim = product.GetPrim()
    prim.CreateAttribute("omni:rtx:rendermode", Sdf.ValueTypeNames.Token, custom=False).Set("PathTracing")
    # Create the spectral controls explicitly; no applied settings schema defines them.
    prim.CreateAttribute("omni:rtx:pathtracing:spectral:enabled", Sdf.ValueTypeNames.Bool, custom=True).Set(True)
    prim.CreateAttribute("omni:rtx:pathtracing:spectral:wavelengthMin", Sdf.ValueTypeNames.Float, custom=True).Set(360)
    prim.CreateAttribute("omni:rtx:pathtracing:spectral:wavelengthMax", Sdf.ValueTypeNames.Float, custom=True).Set(830)
    prim.CreateAttribute("omni:rtx:pathtracing:spectral:responseCurve", Sdf.ValueTypeNames.UInt, custom=True).Set(0)
    # [/snippet:doc-spectral-authoring-python]
    expected = Usd.Stage.Open(str(Path(__file__).with_name("data") / "spectral_rendering.usda"))
    for path in ("/World/RectLight", "/Render/Camera"):
        actual = stage.GetPrimAtPath(path)
        reference = expected.GetPrimAtPath(path)
        assert actual.GetAppliedSchemas() == reference.GetAppliedSchemas()
        for attribute in reference.GetAuthoredAttributes():
            counterpart = actual.GetAttribute(attribute.GetName())
            assert counterpart.GetTypeName() == attribute.GetTypeName()
            assert counterpart.Get() == attribute.Get()
        for relationship in reference.GetAuthoredRelationships():
            assert actual.GetRelationship(relationship.GetName()).GetTargets() == relationship.GetTargets()


@pytest.mark.parametrize(
    "illuminant,token",
    [
        ("white", "white"),
        ("sodium", "custom"),
        ("mercury", "custom"),
    ],
)
@pytest.mark.parametrize("transport", ["rgb", "spectral"])
def test_comparison_variants(illuminant, token, transport):
    """Selection must change composed controls, without changing exposure or power."""
    stage = Usd.Stage.Open(str(SCENE))
    light = stage.GetPrimAtPath("/World/RectLight")
    product = stage.GetPrimAtPath("/Render/Camera")
    light.GetVariantSet("illuminant").SetVariantSelection(illuminant)
    product.GetVariantSet("transport").SetVariantSelection(transport)
    assert light.GetAttribute("physical:illuminant").Get() == token
    assert light.HasAPI("PhysicalLightIlluminantAPI")
    assert light.GetAttribute("photometric:power").Get() == 6400
    assert product.GetAttribute("omni:rtx:rendermode").Get() == "PathTracing"
    assert product.GetAttribute("omni:rtx:pathtracing:spectral:enabled").Get() == (transport == "spectral")
    assert not stage.GetPrimAtPath("/World/Camera").GetAttribute("omni:rtx:autoExposure:enabled").Get()
    if token == "custom":
        samples = light.GetAttribute("physical:customIlluminant").Get()
        assert len(samples) == (401 if illuminant == "sodium" else 81)
        assert samples[0][0] == 380
        assert samples[-1][0] == 780
        assert all(b[0] > a[0] for a, b in zip(samples, samples[1:]))
        assert all(value >= 0 for _, value in samples)
