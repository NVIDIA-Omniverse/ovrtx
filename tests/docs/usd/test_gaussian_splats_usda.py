# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from pathlib import Path
import pytest
from pxr import Sdf, Usd, UsdGeom, UsdRender, UsdShade


def test_public_scene_references_upright_cactus():
    """Check the external asset and upright placement without requiring an HTTP resolver."""
    scene = Path(__file__).parents[3] / "examples/python/gaussian-splats/gaussian_splats.usda"
    layer = Sdf.Layer.FindOrOpen(str(scene))
    splats = layer.GetPrimAtPath("/World/Splats")
    references = splats.referenceList.GetAppliedItems()
    assert len(references) == 1
    assert references[0].assetPath == (
        "https://huggingface.co/buckets/nvidia/ovrtx-storage/resolve/cactus-100.usdc"
    )
    assert splats.attributes["xformOp:rotateX"].default == 180
    assert list(splats.attributes["xformOpOrder"].default) == [
        "xformOp:translate", "xformOp:rotateX", "xformOp:scale"
    ]


def test_stochastic_overlay_disables_only_non_stochastic_compositing():
    """Keep the off/on comparison on the same camera with compatible sampling settings."""
    example = Path(__file__).parents[3] / "examples/python/gaussian-splats"
    stage = Usd.Stage.Open(str(example / "stochastic.usda"))
    product = stage.GetPrimAtPath("/Render/Camera")
    assert product.GetAttribute("omni:rtx:rtpt:gaussian:nonStochastic:enabled").Get() is False
    assert product.GetAttribute("omni:rtx:rtpt:adaptiveSampling:disocclusion:enabled").Get() is False
    assert product.GetAttribute("omni:rtx:rendermode").Get() == "RealTimePathTracing"
    assert product.GetRelationship("camera").GetTargets() == [Sdf.Path("/World/Camera_close")]
    assert stage.GetPrimAtPath("/World/Camera_close").IsA(UsdGeom.Camera)
    assert not UsdShade.MaterialBindingAPI(stage.GetPrimAtPath("/World/Splats")).ComputeBoundMaterial()[0]

    # The off layer must inherit the on layer and author just the one differing setting.
    layer = stage.GetRootLayer()
    assert list(layer.subLayerPaths) == ["non_stochastic.usda"]
    properties = []
    layer.Traverse(Sdf.Path.absoluteRootPath, lambda path: properties.append(path) if path.IsPropertyPath() else None)
    assert properties == [Sdf.Path("/Render/Camera.omni:rtx:rtpt:gaussian:nonStochastic:enabled")]


@pytest.mark.parametrize("variant", ["non_stochastic", "sh_diffuse"])
def test_gaussian_variant_authoring(variant):
    """Check both documentation tabs compose onto the runnable example identically."""
    example = Path(__file__).parents[3] / "examples/python/gaussian-splats"
    authored = Usd.Stage.Open(str(example / f"{variant}.usda"))
    stage = Usd.Stage.CreateInMemory()
    stage.GetRootLayer().subLayerPaths.append(str(example / "gaussian_splats.usda"))

    if variant == "non_stochastic":
        # [snippet:doc-gaussian-non-stochastic-python]
        product = UsdRender.Product.Get(stage, "/Render/Camera")
        product.GetCameraRel().SetTargets(["/World/Camera_close"])
        prim = product.GetPrim()
        prim.CreateAttribute("omni:rtx:rendermode", Sdf.ValueTypeNames.Token).Set("RealTimePathTracing")
        prim.CreateAttribute("omni:rtx:rtpt:gaussian:nonStochastic:enabled", Sdf.ValueTypeNames.Bool).Set(True)
        # Adaptive disocclusion sampling would force stochastic rendering.
        prim.CreateAttribute(
            "omni:rtx:rtpt:adaptiveSampling:disocclusion:enabled", Sdf.ValueTypeNames.Bool
        ).Set(False)
        # [/snippet:doc-gaussian-non-stochastic-python]
    else:
        # [snippet:doc-gaussian-sh-diffuse-python]
        material = UsdShade.Material.Define(stage, "/World/SHDiffuse")
        shader = UsdShade.Shader.Define(stage, "/World/SHDiffuse/Shader")
        shader.SetSourceAsset(Sdf.AssetPath("ParticleFieldSHDiffuse.mdl"), "mdl")
        shader.SetSourceAssetSubIdentifier("ParticleFieldSHDiffuse", "mdl")
        output = shader.CreateOutput("out", Sdf.ValueTypeNames.Token)
        output.SetRenderType("material")
        material.CreateSurfaceOutput("mdl").ConnectToSource(output)
        # Bind to the existing ParticleField; its SH0 data becomes diffuse albedo.
        splats = stage.GetPrimAtPath("/World/Splats")
        UsdShade.MaterialBindingAPI.Apply(splats).Bind(material)
        product = stage.GetPrimAtPath("/Render/Camera")
        # Render scene-lit color through the normal color pipeline.
        product.CreateAttribute("omni:rtx:gaussian:skipTonemapping:enabled", Sdf.ValueTypeNames.Bool).Set(False)
        product.CreateAttribute("omni:rtx:rtpt:gaussian:nonStochastic:enabled", Sdf.ValueTypeNames.Bool).Set(False)
        # [/snippet:doc-gaussian-sh-diffuse-python]

    # Compare composed values and connections, not serialized whitespace or ordering.
    # This validates USD authoring only; it does not prove renderer consumption.
    for candidate in (authored, stage):
        splats = candidate.GetPrimAtPath("/World/Splats")
        product = candidate.GetPrimAtPath("/Render/Camera")
        assert splats.HasAuthoredReferences()
        assert splats.GetAttribute("xformOp:rotateX").Get() == 180
        camera_targets = product.GetRelationship("camera").GetTargets()
        assert camera_targets and candidate.GetPrimAtPath(camera_targets[0])
        assert product.GetAttribute("omni:rtx:rendermode").Get() == "RealTimePathTracing"
        assert product.GetAttribute("omni:rtx:rtpt:gaussian:nonStochastic:enabled").Get() == (variant == "non_stochastic")
        if variant == "non_stochastic":
            assert product.GetAttribute("omni:rtx:rtpt:adaptiveSampling:disocclusion:enabled").Get() is False
            assert not UsdShade.MaterialBindingAPI(splats).ComputeBoundMaterial()[0]
        else:
            material, _ = UsdShade.MaterialBindingAPI(splats).ComputeBoundMaterial()
            assert material.GetPath() == Sdf.Path("/World/SHDiffuse")
            source = material.ComputeSurfaceSource("mdl")[0]
            assert source.GetSourceAsset("mdl").path == "ParticleFieldSHDiffuse.mdl"
            assert source.GetSourceAssetSubIdentifier("mdl") == "ParticleFieldSHDiffuse"
            assert source.GetOutput("out").GetRenderType() == "material"
            assert product.GetAttribute("omni:rtx:gaussian:skipTonemapping:enabled").Get() is False

    # Every authored overlay attribute and relationship must have the same effective value.
    for prim in authored.GetRootLayer().rootPrims:
        pending = [prim]
        while pending:
            spec = pending.pop()
            pending.extend(spec.nameChildren.values())
            for prop in spec.properties:
                a = authored.GetPropertyAtPath(prop.path)
                b = stage.GetPropertyAtPath(prop.path)
                assert b, prop.path
                if isinstance(a, Usd.Attribute):
                    assert a.GetTypeName() == b.GetTypeName(), prop.path
                    assert a.Get() == b.Get(), prop.path
                    assert a.GetConnections() == b.GetConnections(), prop.path
                else:
                    assert a.GetTargets() == b.GetTargets(), prop.path
