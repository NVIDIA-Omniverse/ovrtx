# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Tests for USD Python API examples shown in doc USDA tabs."""

import shutil
from pathlib import Path

import pytest
from pxr import Ar, Gf, Sdf, Usd, UsdGeom, UsdLux, UsdRender, UsdShade


def test_mesh_lights():
    stage = Usd.Stage.CreateInMemory()

    # [snippet:doc-mesh-light-python]
    emitter = UsdGeom.Mesh.Define(stage, "/World/Emitter")
    emitter.CreateFaceVertexCountsAttr([4])
    emitter.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    emitter.CreatePointsAttr(
        [(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)]
    )

    material = UsdShade.Material.Define(stage, "/World/Looks/Emitter")
    shader = UsdShade.Shader.Define(stage, "/World/Looks/Emitter/Shader")
    shader.GetPrim().CreateAttribute(
        "info:implementationSource", Sdf.ValueTypeNames.Token
    ).Set("sourceAsset")
    shader.GetPrim().CreateAttribute(
        "info:mdl:sourceAsset", Sdf.ValueTypeNames.Asset
    ).Set("OmniEmissive.mdl")
    shader.GetPrim().CreateAttribute(
        "info:mdl:sourceAsset:subIdentifier", Sdf.ValueTypeNames.Token
    ).Set("OmniEmissive")
    shader.CreateInput("emissive_color", Sdf.ValueTypeNames.Color3f).Set((1, 1, 1))
    shader.CreateInput("emission_intensity", Sdf.ValueTypeNames.Float).Set(200)
    shader_output = shader.CreateOutput("out", Sdf.ValueTypeNames.Token)
    shader_output.SetRenderType("material")
    material.CreateSurfaceOutput("mdl").ConnectToSource(shader_output)
    UsdShade.MaterialBindingAPI.Apply(emitter.GetPrim()).Bind(material)
    # [/snippet:doc-mesh-light-python]

    # [snippet:doc-enable-mesh-light-sampling-python]
    product = UsdRender.Product.Define(stage, "/Render/Camera")
    product.GetPrim().ApplyAPI("OmniRtxSettingsPtAdvancedAPI_1")
    product.GetPrim().CreateAttribute(
        "omni:rtx:pt:ris:meshLights", Sdf.ValueTypeNames.Bool
    ).Set(True)
    product.GetPrim().CreateAttribute(
        "omni:rtx:rtpt:ris:meshLights", Sdf.ValueTypeNames.Bool
    ).Set(True)
    # [/snippet:doc-enable-mesh-light-sampling-python]

    assert "MeshLightAPI" not in emitter.GetPrim().GetAppliedSchemas()
    assert emitter.GetFaceVertexCountsAttr().Get() == [4]
    assert emitter.GetFaceVertexIndicesAttr().Get() == [0, 1, 2, 3]
    assert len(emitter.GetPointsAttr().Get()) == 4
    binding = UsdShade.MaterialBindingAPI(emitter).GetDirectBindingRel()
    assert binding.GetTargets() == [Sdf.Path("/World/Looks/Emitter")]
    assert shader.GetPrim().GetAttribute("info:implementationSource").Get() == (
        "sourceAsset"
    )
    assert shader.GetInput("emissive_color").Get() == (1.0, 1.0, 1.0)
    assert shader.GetInput("emission_intensity").Get() == pytest.approx(200)
    assert shader_output.GetRenderType() == "material"
    connected = material.GetSurfaceOutput("mdl").GetConnectedSource()
    assert connected
    assert connected[0].GetPrim() == shader.GetPrim()
    assert connected[1] == "out"
    assert product.GetPrim().HasAPI("OmniRtxSettingsPtAdvancedAPI_1")
    assert product.GetPrim().GetAttribute("omni:rtx:pt:ris:meshLights").Get()
    assert product.GetPrim().GetAttribute("omni:rtx:rtpt:ris:meshLights").Get()


def test_projector_light():
    stage = Usd.Stage.CreateInMemory()

    # [snippet:doc-projector-light-python]
    projector = UsdLux.RectLight.Define(stage, "/World/Projector")
    projector.GetPrim().CreateAttribute("isProjector", Sdf.ValueTypeNames.Bool).Set(
        True
    )
    projector.GetWidthAttr().Set(1.5)
    projector.GetHeightAttr().Set(1.0)
    projector.LightAPI().GetIntensityAttr().Set(10000.0)

    # This is the color image being projected.
    projector.CreateTextureFileAttr("../../data/chelsea.png")

    # This optional direction lookup reshapes the projection.
    projector.GetPrim().CreateAttribute(
        "projector:directionTexture:file", Sdf.ValueTypeNames.Asset
    ).Set("../../data/projector-fisheye-direction.exr")
    # [/snippet:doc-projector-light-python]

    prim = projector.GetPrim()
    assert prim.GetAttribute("isProjector").GetTypeName() == Sdf.ValueTypeNames.Bool
    assert prim.GetAttribute("isProjector").Get() is True
    assert projector.GetWidthAttr().Get() == pytest.approx(1.5)
    assert projector.GetHeightAttr().Get() == pytest.approx(1.0)
    assert projector.LightAPI().GetIntensityAttr().Get() == pytest.approx(10000.0)
    assert projector.GetTextureFileAttr().Get().path == "../../data/chelsea.png"
    direction = prim.GetAttribute("projector:directionTexture:file")
    assert direction.GetTypeName() == Sdf.ValueTypeNames.Asset
    assert direction.Get().path == "../../data/projector-fisheye-direction.exr"


def test_ghost_lights():
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, "/World")

    # [snippet:doc-ghost-lights-python]
    light = UsdLux.RectLight.Define(stage, "/World/Softbox")
    # Keep illuminating the scene, but hide the source from camera rays.
    light.GetPrim().CreateAttribute(
        "visibleInPrimaryRay", Sdf.ValueTypeNames.Bool
    ).Set(False)
    # Suppress the source in specular and glossy interactions.
    light.GetPrim().CreateAttribute("ghostFactor", Sdf.ValueTypeNames.Float).Set(0.5)

    subject = UsdGeom.Sphere.Define(stage, "/World/Subject")
    # Per-object ghosting overrides the light and RenderProduct values.
    UsdGeom.PrimvarsAPI(subject).CreatePrimvar(
        "omni:rtx:ghostFactor",
        Sdf.ValueTypeNames.Float,
        UsdGeom.Tokens.constant,
    ).Set(1.0)

    product = UsdRender.Product.Define(stage, "/Render/Camera")
    product.GetPrim().ApplyAPI("OmniRtxSettingsCommonAPI_1")
    product.GetPrim().GetAttribute("omni:rtx:lights:visibilityOverride").Set(
        "perLight"
    )
    product.GetPrim().GetAttribute(
        "omni:rtx:lights:reflectionVisibleRoughnessThreshold"
    ).Set(0.15)
    product.GetPrim().GetAttribute(
        "omni:rtx:lights:refractionVisibleRoughnessThreshold"
    ).Set(0.8)
    # [/snippet:doc-ghost-lights-python]

    assert light.GetPrim().GetAttribute("visibleInPrimaryRay").Get() is False
    assert light.GetPrim().GetAttribute("visibleInPrimaryRay").GetTypeName() == Sdf.ValueTypeNames.Bool
    assert light.GetPrim().GetAttribute("ghostFactor").Get() == pytest.approx(0.5)
    assert light.GetPrim().GetAttribute("ghostFactor").GetTypeName() == Sdf.ValueTypeNames.Float
    ghost_primvar = UsdGeom.PrimvarsAPI(subject).GetPrimvar("omni:rtx:ghostFactor")
    assert ghost_primvar.GetTypeName() == Sdf.ValueTypeNames.Float
    assert ghost_primvar.Get() == pytest.approx(1.0)
    assert ghost_primvar.GetInterpolation() == UsdGeom.Tokens.constant
    assert product.GetPrim().HasAPI("OmniRtxSettingsCommonAPI_1")
    assert product.GetPrim().GetAttribute("omni:rtx:lights:visibilityOverride").Get() == "perLight"
    assert product.GetPrim().GetAttribute("omni:rtx:lights:reflectionVisibleRoughnessThreshold").Get() == pytest.approx(0.15)
    assert product.GetPrim().GetAttribute("omni:rtx:lights:refractionVisibleRoughnessThreshold").Get() == pytest.approx(0.8)


def test_finite_dome_light():
    stage = Usd.Stage.CreateInMemory()

    # [snippet:doc-finite-dome-light-python]
    dome = UsdLux.DomeLight.Define(stage, "/World/Studio")
    dome.CreateTextureFileAttr("../../data/studio.exr")
    dome.CreateTextureFormatAttr("latlong")

    # OmniFiniteDomeLightAPI is auto-applied to DomeLight prims.
    dome.GetPrim().GetAttribute("omni:rtx:domeLight:mode").Set("sphereWithGround")
    dome.GetPrim().GetAttribute("omni:rtx:domeLight:radius").Set(5.0)
    dome.GetPrim().GetAttribute("omni:rtx:domeLight:size").Set(Gf.Vec3f(10, 6, 8))
    dome.GetPrim().GetAttribute("omni:rtx:domeLight:groundTextureScale").Set(10.0)

    # Use a separate transform to position and scale the finite geometry.
    geometry = UsdGeom.Xform.Define(stage, "/World/DomeGeometry")
    geometry.AddTranslateOp().Set(Gf.Vec3d(0, 2, 0))
    geometry.AddScaleOp().Set(Gf.Vec3d(1, 1, 1))
    dome.GetPrim().GetRelationship("coordSys:domeGeometry:binding").SetTargets(
        [geometry.GetPath()]
    )
    # [/snippet:doc-finite-dome-light-python]

    prim = dome.GetPrim()
    assert prim.HasAPI("OmniFiniteDomeLightAPI")
    assert prim.HasAPI("CoordSysAPI", "domeGeometry")
    assert prim.GetAttribute("inputs:texture:file").Get().path == "../../data/studio.exr"
    assert prim.GetAttribute("inputs:texture:format").Get() == "latlong"
    assert prim.GetAttribute("omni:rtx:domeLight:mode").Get() == "sphereWithGround"
    assert prim.GetAttribute("omni:rtx:domeLight:radius").Get() == 5.0
    assert tuple(prim.GetAttribute("omni:rtx:domeLight:size").Get()) == pytest.approx((10.0, 6.0, 8.0))
    assert prim.GetAttribute("omni:rtx:domeLight:groundTextureScale").Get() == 10.0
    assert prim.GetRelationship("coordSys:domeGeometry:binding").GetTargets() == [
        Sdf.Path("/World/DomeGeometry")
    ]
    assert geometry.GetXformOpOrderAttr().Get() == ["xformOp:translate", "xformOp:scale"]
    assert tuple(geometry.GetPrim().GetAttribute("xformOp:translate").Get()) == pytest.approx((0.0, 2.0, 0.0))
    assert tuple(geometry.GetPrim().GetAttribute("xformOp:scale").Get()) == pytest.approx((1.0, 1.0, 1.0))


def test_physical_lighting():
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, "/World")

    # [snippet:doc-physical-lighting-python]
    panel = UsdLux.RectLight.Define(stage, "/World/LumenPanel")
    panel.GetPrim().ApplyAPI("PhotometricAreaLightAPI")
    # Set total luminous power and use a 3000 K blackbody spectrum.
    panel.GetPrim().GetAttribute("photometric:power").Set(1600.0)
    panel.GetPrim().GetAttribute("physical:illuminant").Set("blackbody")
    panel.GetColorTemperatureAttr().Set(3000.0)

    target = UsdLux.SphereLight.Define(stage, "/World/LuxTarget")
    target.GetPrim().ApplyAPI("PhotometricAreaLightAPI")
    # Target 500 lux two meters from the light instead of using power.
    target.GetPrim().GetAttribute("photometric:power").Set(0.0)
    target.GetPrim().GetAttribute("photometric:illuminance").Set(500.0)
    target.GetPrim().GetAttribute("photometric:illuminance:distance").Set(2.0)

    sun = UsdLux.DistantLight.Define(stage, "/World/Sun")
    sun.GetPrim().ApplyAPI("PhotometricDistantLightAPI")
    # Specify illuminance on a surface perpendicular to the light.
    sun.GetPrim().GetAttribute("photometric:illuminance").Set(10000.0)
    sun.GetPrim().GetAttribute("physical:illuminant").Set("illuminant D")
    sun.GetColorTemperatureAttr().Set(6504.0)
    # [/snippet:doc-physical-lighting-python]

    assert panel.GetPrim().HasAPI("PhysicalLightIlluminantAPI")
    assert panel.GetPrim().GetTypeName() == "RectLight"
    assert panel.GetPrim().GetAttribute("photometric:power").Get() == 1600.0
    assert panel.GetPrim().GetAttribute("photometric:power").HasAuthoredValueOpinion()
    assert panel.GetPrim().GetAttribute("physical:illuminant").Get() == "blackbody"
    assert panel.GetColorTemperatureAttr().Get() == 3000.0
    assert target.GetPrim().GetAttribute("photometric:power").Get() == 0.0
    assert target.GetPrim().GetTypeName() == "SphereLight"
    assert target.GetPrim().HasAPI("PhysicalLightIlluminantAPI")
    assert target.GetPrim().GetAttribute("photometric:illuminance").Get() == 500.0
    assert target.GetPrim().GetAttribute("photometric:illuminance:distance").Get() == 2.0
    assert sun.GetPrim().HasAPI("PhysicalLightIlluminantAPI")
    assert sun.GetPrim().GetTypeName() == "DistantLight"
    assert sun.GetPrim().GetAttribute("photometric:illuminance").Get() == 10000.0
    assert sun.GetPrim().GetAttribute("photometric:illuminance").HasAuthoredValueOpinion()
    assert sun.GetPrim().GetAttribute("physical:illuminant").Get() == "illuminant D"
    assert sun.GetColorTemperatureAttr().Get() == 6504.0


def test_light_linking():
    stage = Usd.Stage.CreateInMemory()

    # [snippet:doc-light-linking-python]
    light = UsdLux.SphereLight.Define(stage, "/World/KeyLight")

    # Illuminate only Subjects and Ground, including their descendants.
    light_link = light.LightAPI().GetLightLinkCollectionAPI()
    light_link.CreateIncludeRootAttr(False)
    light_link.CreateExpansionRuleAttr(Usd.Tokens.expandPrims)
    light_link.CreateIncludesRel().SetTargets(
        [Sdf.Path("/World/Subjects"), Sdf.Path("/World/Ground")]
    )

    # All geometry casts shadows except NoShadow.
    shadow_link = light.LightAPI().GetShadowLinkCollectionAPI()
    shadow_link.CreateIncludeRootAttr(True)
    shadow_link.CreateExcludesRel().SetTargets(
        [Sdf.Path("/World/Subjects/NoShadow")]
    )
    # [/snippet:doc-light-linking-python]

    assert light_link.GetIncludeRootAttr().Get() is False
    assert light_link.GetExpansionRuleAttr().Get() == Usd.Tokens.expandPrims
    assert light_link.GetIncludesRel().GetTargets() == [
        Sdf.Path("/World/Subjects"),
        Sdf.Path("/World/Ground"),
    ]
    light_query = light_link.ComputeMembershipQuery()
    assert light_query.IsPathIncluded(Sdf.Path("/World/Subjects/Linked"))
    assert light_query.IsPathIncluded(Sdf.Path("/World/Subjects/NoShadow"))
    assert light_query.IsPathIncluded(Sdf.Path("/World/Ground"))
    assert not light_query.IsPathIncluded(Sdf.Path("/World/Unlinked"))

    assert shadow_link.GetIncludeRootAttr().Get() is True
    assert shadow_link.GetExcludesRel().GetTargets() == [
        Sdf.Path("/World/Subjects/NoShadow")
    ]
    shadow_query = shadow_link.ComputeMembershipQuery()
    assert shadow_query.IsPathIncluded(Sdf.Path("/World/Subjects/Linked"))
    assert not shadow_query.IsPathIncluded(Sdf.Path("/World/Subjects/NoShadow"))


def test_light_shaping():
    stage = Usd.Stage.CreateInMemory()

    # [snippet:doc-light-shaping-python]
    light = UsdLux.RectLight.Define(stage, "/World/ShapedPanel")
    shaping = UsdLux.ShapingAPI.Apply(light.GetPrim())
    shaping.GetShapingConeAngleAttr().Set(45.0)
    shaping.GetShapingConeSoftnessAttr().Set(0.25)
    shaping.GetShapingFocusAttr().Set(2.0)
    shaping.GetShapingFocusTintAttr().Set(Gf.Vec3f(0.1, 0.2, 1.0))
    light.GetPrim().GetAttribute("omni:rtx:shaping:forwardAxis").Set("-Z")
    # [/snippet:doc-light-shaping-python]

    assert shaping
    assert shaping.GetShapingConeAngleAttr().Get() == pytest.approx(45.0)
    assert shaping.GetShapingConeSoftnessAttr().Get() == pytest.approx(0.25)
    assert shaping.GetShapingFocusAttr().Get() == pytest.approx(2.0)
    assert tuple(shaping.GetShapingFocusTintAttr().Get()) == pytest.approx((0.1, 0.2, 1.0))
    assert light.GetPrim().GetAttribute("omni:rtx:shaping:forwardAxis").Get() == "-Z"


def test_light_shaping_ies(tmp_path):
    stage_dir = tmp_path / "usd/data"
    stage_dir.mkdir(parents=True)
    ies_dir = tmp_path / "data/ies"
    ies_dir.mkdir(parents=True)
    source_ies = Path(__file__).parents[1] / "data/ies/bega-50898.4K3.ies"
    resolved_ies = ies_dir / source_ies.name
    shutil.copyfile(source_ies, resolved_ies)
    stage = Usd.Stage.CreateNew(str(stage_dir / "light_shaping_python.usda"))

    # [snippet:doc-light-shaping-ies-python]
    light = UsdLux.DiskLight.Define(stage, "/World/IesDownlight")
    shaping = UsdLux.ShapingAPI.Apply(light.GetPrim())
    shaping.GetShapingIesAngleScaleAttr().Set(1.0)
    shaping.GetShapingIesFileAttr().Set(
        Sdf.AssetPath("../../data/ies/bega-50898.4K3.ies")
    )
    shaping.GetShapingIesNormalizeAttr().Set(True)
    # [/snippet:doc-light-shaping-ies-python]

    assert shaping
    assert shaping.GetShapingIesAngleScaleAttr().Get() == pytest.approx(1.0)
    assert shaping.GetShapingIesFileAttr().Get() == Sdf.AssetPath(
        "../../data/ies/bega-50898.4K3.ies", str(resolved_ies)
    )
    assert shaping.GetShapingIesNormalizeAttr().Get() is True


def test_common_light_attributes():
    stage = Usd.Stage.CreateInMemory()

    # [snippet:doc-common-light-attributes-python]
    light = UsdLux.SphereLight.Define(stage, "/World/KeyLight")
    light_api = light.LightAPI()
    light_api.GetColorAttr().Set(Gf.Vec3f(1.0, 0.85, 0.7))
    light_api.GetColorTemperatureAttr().Set(4500.0)
    light_api.GetDiffuseAttr().Set(1.0)
    light_api.GetEnableColorTemperatureAttr().Set(True)
    light_api.GetExposureAttr().Set(2.0)
    light_api.GetIntensityAttr().Set(1000.0)
    light_api.GetNormalizeAttr().Set(False)
    light_api.GetSpecularAttr().Set(1.0)
    # [/snippet:doc-common-light-attributes-python]

    expected = {
        light_api.GetColorAttr(): Gf.Vec3f(1.0, 0.85, 0.7),
        light_api.GetColorTemperatureAttr(): 4500.0,
        light_api.GetDiffuseAttr(): 1.0,
        light_api.GetEnableColorTemperatureAttr(): True,
        light_api.GetExposureAttr(): 2.0,
        light_api.GetIntensityAttr(): 1000.0,
        light_api.GetNormalizeAttr(): False,
        light_api.GetSpecularAttr(): 1.0,
    }
    for attribute, value in expected.items():
        assert attribute.HasAuthoredValueOpinion()
        assert attribute.Get() == value


def test_distant_light():
    stage = Usd.Stage.CreateInMemory()

    # [snippet:doc-distant-light-python]
    light = UsdLux.DistantLight.Define(stage, "/World/Sun")
    light.GetAngleAttr().Set(0.53)
    light.LightAPI().GetIntensityAttr().Set(50000.0)
    light.LightAPI().GetNormalizeAttr().Set(True)
    # [/snippet:doc-distant-light-python]

    assert light.GetAngleAttr().Get() == pytest.approx(0.53)
    assert light.GetAngleAttr().HasAuthoredValueOpinion()
    assert light.LightAPI().GetIntensityAttr().Get() == 50000.0
    assert light.LightAPI().GetNormalizeAttr().Get() is True


def test_sphere_light():
    stage = Usd.Stage.CreateInMemory()

    # [snippet:doc-sphere-light-python]
    light = UsdLux.SphereLight.Define(stage, "/World/Bulb")
    light.GetRadiusAttr().Set(0.05)
    light.GetTreatAsPointAttr().Set(False)
    # [/snippet:doc-sphere-light-python]

    assert light.GetRadiusAttr().Get() == pytest.approx(0.05)
    assert light.GetRadiusAttr().HasAuthoredValueOpinion()
    assert light.GetTreatAsPointAttr().Get() is False
    assert light.GetTreatAsPointAttr().HasAuthoredValueOpinion()


def test_rect_light():
    stage = Usd.Stage.CreateInMemory()

    # [snippet:doc-rect-light-python]
    light = UsdLux.RectLight.Define(stage, "/World/Panel")
    light.GetHeightAttr().Set(0.6)
    light.GetWidthAttr().Set(1.2)
    # [/snippet:doc-rect-light-python]

    assert light.GetHeightAttr().Get() == pytest.approx(0.6)
    assert light.GetWidthAttr().Get() == pytest.approx(1.2)
    assert light.GetHeightAttr().HasAuthoredValueOpinion()
    assert light.GetWidthAttr().HasAuthoredValueOpinion()


def test_disk_light():
    stage = Usd.Stage.CreateInMemory()

    # [snippet:doc-disk-light-python]
    light = UsdLux.DiskLight.Define(stage, "/World/Downlight")
    light.GetRadiusAttr().Set(0.25)
    # [/snippet:doc-disk-light-python]

    assert light.GetRadiusAttr().Get() == pytest.approx(0.25)
    assert light.GetRadiusAttr().HasAuthoredValueOpinion()


def test_cylinder_light():
    stage = Usd.Stage.CreateInMemory()

    # [snippet:doc-cylinder-light-python]
    light = UsdLux.CylinderLight.Define(stage, "/World/Tube")
    light.GetLengthAttr().Set(1.2)
    light.GetRadiusAttr().Set(0.025)
    light.GetTreatAsLineAttr().Set(False)
    # [/snippet:doc-cylinder-light-python]

    assert light.GetLengthAttr().Get() == pytest.approx(1.2)
    assert light.GetRadiusAttr().Get() == pytest.approx(0.025)
    assert light.GetLengthAttr().HasAuthoredValueOpinion()
    assert light.GetRadiusAttr().HasAuthoredValueOpinion()
    assert light.GetTreatAsLineAttr().Get() is False
    assert light.GetTreatAsLineAttr().HasAuthoredValueOpinion()


def test_dome_light():
    stage = Usd.Stage.CreateInMemory()

    # [snippet:doc-dome-light-python]
    light = UsdLux.DomeLight.Define(stage, "/World/Environment")
    light.GetTextureFileAttr().Set(Sdf.AssetPath("../../data/studio.exr"))
    light.GetTextureFormatAttr().Set(UsdLux.Tokens.latlong)
    # [/snippet:doc-dome-light-python]

    assert light.GetTextureFileAttr().Get() == Sdf.AssetPath("../../data/studio.exr")
    assert light.GetTextureFileAttr().HasAuthoredValueOpinion()
    assert light.GetTextureFormatAttr().Get() == UsdLux.Tokens.latlong
    assert light.GetTextureFormatAttr().HasAuthoredValueOpinion()


def _author_decal(stage):
    # [snippet:doc-create-decal-python]
    stage.DefinePrim("/World", "Xform")
    stage.DefinePrim("/World/Looks", "Scope")
    stage.DefinePrim("/World/Looks/DecalMaterial", "Material")

    decal = stage.DefinePrim("/World/Decal", "OmniDecal")
    decal.ApplyAPI("MaterialBindingAPI")
    decal.CreateAttribute("extent", Sdf.ValueTypeNames.Float3Array).Set(
        [Gf.Vec3f(-1), Gf.Vec3f(1)]
    )
    decal.CreateRelationship("material:binding").SetTargets(
        ["/World/Looks/DecalMaterial"]
    )
    decal.CreateAttribute("omni:decal:enabled", Sdf.ValueTypeNames.Bool).Set(True)
    decal.CreateAttribute("omni:decal:faceMode", Sdf.ValueTypeNames.Token).Set("front")
    decal.CreateAttribute("omni:decal:outputSpace", Sdf.ValueTypeNames.Int).Set(0)
    decal.CreateAttribute("omni:decal:priority", Sdf.ValueTypeNames.Int).Set(0)
    decal.CreateAttribute("omni:projector:space", Sdf.ValueTypeNames.Token).Set("object")
    decal.CreateAttribute("omni:projector:type", Sdf.ValueTypeNames.Token).Set("planar")
    # [/snippet:doc-create-decal-python]
    return decal


def test_create_decal_python():
    stage = Usd.Stage.CreateInMemory()
    decal = _author_decal(stage)
    assert decal.GetTypeName() == "OmniDecal"
    assert decal.HasAPI("MaterialBindingAPI")
    assert decal.GetAttribute("omni:decal:priority").Get() == 0


def test_bind_decal_python():
    stage = Usd.Stage.CreateInMemory()
    _author_decal(stage)

    # [snippet:doc-bind-decal-python]
    receiver = stage.DefinePrim("/World/Receiver", "Cube")
    receiver.SetMetadata(
        "apiSchemas",
        Sdf.TokenListOp.Create(prependedItems=["OmniCoordSysAPI:Decal"]),
    )
    receiver.CreateRelationship("coordSys:Decal:binding").SetTargets(["/World/Decal"])
    # [/snippet:doc-bind-decal-python]

    assert "OmniCoordSysAPI:Decal" in receiver.GetMetadata(
        "apiSchemas"
    ).GetAddedOrExplicitItems()
    assert receiver.GetRelationship("coordSys:Decal:binding").GetTargets() == [
        Sdf.Path("/World/Decal")
    ]


def test_gaussian_splat_python_matches_usda():
    stage = Usd.Stage.CreateInMemory()
    # [snippet:doc-gaussian-splat-prim-python]
    splat = stage.DefinePrim("/Splat", "ParticleField3DGaussianSplat")
    splat.CreateAttribute("positions", Sdf.ValueTypeNames.Point3fArray, custom=False).Set([(0, 0, 0)])
    splat.CreateAttribute("orientations", Sdf.ValueTypeNames.QuatfArray, custom=False).Set([Gf.Quatf(1)])
    splat.CreateAttribute("scales", Sdf.ValueTypeNames.Float3Array, custom=False).Set([(1, 0.5, 0.25)])
    splat.CreateAttribute("opacities", Sdf.ValueTypeNames.FloatArray, custom=False).Set([0.9])
    splat.CreateAttribute("radiance:sphericalHarmonicsDegree", Sdf.ValueTypeNames.Int,
                          custom=False, variability=Sdf.VariabilityUniform).Set(0)
    splat.CreateAttribute("radiance:sphericalHarmonicsCoefficients", Sdf.ValueTypeNames.Float3Array,
                          custom=False).Set([(1.772454, -0.708982, -1.772454)])
    # [/snippet:doc-gaussian-splat-prim-python]
    expected_stage = Usd.Stage.Open(str(Path(__file__).parent / "data/gaussian_splat.usda"))
    expected = expected_stage.GetPrimAtPath("/Splat")
    assert expected.IsA("ParticleField3DGaussianSplat")
    for attr in expected.GetAuthoredAttributes():
        actual = splat.GetAttribute(attr.GetName())
        assert actual.GetTypeName() == attr.GetTypeName()
        assert actual.Get() == attr.Get()


def test_plugin_physical_light_authoring_matches_usda():
    stage = Usd.Stage.CreateInMemory()
    # [snippet:doc-plugin-physical-light-python]
    light = stage.DefinePrim("/World/Light", "RectLight")
    assert light.ApplyAPI("PhysicalLightIlluminantAPI")
    # [/snippet:doc-plugin-physical-light-python]

    expected_stage = Usd.Stage.Open(str(Path(__file__).parent / "data/plugin_physical_light.usda"))
    expected = expected_stage.GetPrimAtPath("/World/Light")
    assert expected.GetAppliedSchemas() == light.GetAppliedSchemas()
    illuminant = light.GetAttribute("physical:illuminant")
    expected_illuminant = expected.GetAttribute("physical:illuminant")
    assert illuminant.GetTypeName() == expected_illuminant.GetTypeName() == Sdf.ValueTypeNames.Token
    assert illuminant.Get() == expected_illuminant.Get() == "white"
    assert not illuminant.HasAuthoredValueOpinion()
    assert not expected_illuminant.HasAuthoredValueOpinion()


def test_camera_sensor_render_product():
    """Build the camera_sensors.rst RenderProduct using the USD Python API."""
    stage = Usd.Stage.CreateInMemory()

    # [snippet:doc-camera-sensor-render-product-python]
    render_scope = stage.DefinePrim("/Render")
    camera_product = UsdRender.Product.Define(stage, "/Render/Camera")
    camera_product.GetResolutionAttr().Set(Gf.Vec2i(1920, 1080))
    camera_product.GetCameraRel().SetTargets(["/World/Camera"])

    ldr_var = UsdRender.Var.Define(stage, "/Render/Camera/LdrColor")
    ldr_var.GetSourceNameAttr().Set("LdrColor")

    hdr_var = UsdRender.Var.Define(stage, "/Render/Camera/HdrColor")
    hdr_var.GetSourceNameAttr().Set("HdrColor")

    camera_product.GetOrderedVarsRel().SetTargets([
        "/Render/Camera/LdrColor",
        "/Render/Camera/HdrColor",
    ])
    # [/snippet:doc-camera-sensor-render-product-python]

    # Verify
    assert stage.GetPrimAtPath("/Render/Camera").IsValid()
    assert stage.GetPrimAtPath("/Render/Camera/LdrColor").IsValid()
    assert stage.GetPrimAtPath("/Render/Camera/HdrColor").IsValid()
    assert camera_product.GetResolutionAttr().Get() == Gf.Vec2i(1920, 1080)
    assert camera_product.GetCameraRel().GetTargets() == [Sdf.Path("/World/Camera")]


def test_minimal_render_product():
    """Build the sensor_configuration.rst minimal RenderProduct using the USD Python API."""
    stage = Usd.Stage.CreateInMemory()

    # [snippet:doc-minimal-render-product-python]
    render_scope = stage.DefinePrim("/Render")
    camera_product = UsdRender.Product.Define(stage, "/Render/Camera")
    camera_product.GetResolutionAttr().Set(Gf.Vec2i(1920, 1080))
    camera_product.GetCameraRel().SetTargets(["/World/Camera"])

    ldr_var = UsdRender.Var.Define(stage, "/Render/Camera/LdrColor")
    ldr_var.GetSourceNameAttr().Set("LdrColor")

    camera_product.GetOrderedVarsRel().SetTargets(["/Render/Camera/LdrColor"])
    # [/snippet:doc-minimal-render-product-python]

    # Verify
    assert stage.GetPrimAtPath("/Render/Camera").IsValid()
    assert stage.GetPrimAtPath("/Render/Camera/LdrColor").IsValid()
    assert camera_product.GetResolutionAttr().Get() == Gf.Vec2i(1920, 1080)


def test_multi_render_product_shared_vars():
    """Build the sensor_configuration.rst multi-sensor RenderProduct using the USD Python API."""
    stage = Usd.Stage.CreateInMemory()

    # [snippet:doc-multi-render-product-shared-vars-python]
    render_scope = stage.DefinePrim("/Render")

    front_product = UsdRender.Product.Define(stage, "/Render/FrontCamera")
    front_product.GetCameraRel().SetTargets(["/World/FrontCamera"])
    front_product.GetOrderedVarsRel().SetTargets(["/Render/Vars/LdrColor"])

    rear_product = UsdRender.Product.Define(stage, "/Render/RearCamera")
    rear_product.GetCameraRel().SetTargets(["/World/RearCamera"])
    rear_product.GetOrderedVarsRel().SetTargets(["/Render/Vars/LdrColor"])

    vars_scope = stage.DefinePrim("/Render/Vars")
    ldr_var = UsdRender.Var.Define(stage, "/Render/Vars/LdrColor")
    ldr_var.GetSourceNameAttr().Set("LdrColor")
    # [/snippet:doc-multi-render-product-shared-vars-python]

    # Verify
    assert stage.GetPrimAtPath("/Render/FrontCamera").IsValid()
    assert stage.GetPrimAtPath("/Render/RearCamera").IsValid()
    assert stage.GetPrimAtPath("/Render/Vars/LdrColor").IsValid()
    assert front_product.GetCameraRel().GetTargets() == [Sdf.Path("/World/FrontCamera")]
    assert rear_product.GetCameraRel().GetTargets() == [Sdf.Path("/World/RearCamera")]


def _author_lpe_render_vars(stage):
    # [snippet:doc-lpe-render-vars-python]
    render_product = UsdRender.Product.Define(stage, "/Render/Camera")
    render_product.GetPrim().ApplyAPI("OmniRtxSettingsPtAdvancedAPI_1")
    render_product.GetCameraRel().SetTargets(["/World/Camera"])
    render_product.GetPrim().CreateAttribute(
        "omni:rtx:rendermode", Sdf.ValueTypeNames.Token
    ).Set("PathTracing")

    # Cached radiance has no path history, so omit it from an LPE workflow.
    render_product.GetPrim().GetAttribute("omni:rtx:pt:radianceCache:enabled").Set(False)

    hdr_var = UsdRender.Var.Define(stage, "/Render/Camera/HdrColor")
    hdr_var.GetSourceNameAttr().Set("HdrColor")

    diffuse_var = UsdRender.Var.Define(stage, "/Render/Camera/DiffuseReflection")
    diffuse_var.GetSourceNameAttr().Set("E<RD>.*L")
    diffuse_var.GetSourceTypeAttr().Set(UsdRender.Tokens.lpe)

    glossy_var = UsdRender.Var.Define(stage, "/Render/Camera/GlossyReflection")
    glossy_var.GetSourceNameAttr().Set("E<RG>.*L")
    glossy_var.GetSourceTypeAttr().Set(UsdRender.Tokens.lpe)

    render_product.GetOrderedVarsRel().SetTargets(
        [hdr_var.GetPath(), diffuse_var.GetPath(), glossy_var.GetPath()]
    )
    # [/snippet:doc-lpe-render-vars-python]

    return render_product


def test_lpe_render_vars():
    stage = Usd.Stage.CreateInMemory()
    render_product = _author_lpe_render_vars(stage)

    assert render_product.GetCameraRel().GetTargets() == [Sdf.Path("/World/Camera")]
    assert render_product.GetPrim().GetAttribute("omni:rtx:rendermode").Get() == "PathTracing"
    assert render_product.GetPrim().GetAttribute("omni:rtx:pt:radianceCache:enabled").Get() is False
    assert render_product.GetOrderedVarsRel().GetTargets() == [
        Sdf.Path("/Render/Camera/HdrColor"),
        Sdf.Path("/Render/Camera/DiffuseReflection"),
        Sdf.Path("/Render/Camera/GlossyReflection"),
    ]
    assert stage.GetPrimAtPath("/Render/Camera/DiffuseReflection").GetAttribute("sourceName").Get() == "E<RD>.*L"
    assert stage.GetPrimAtPath("/Render/Camera/DiffuseReflection").GetAttribute("sourceType").Get() == "lpe"
    assert stage.GetPrimAtPath("/Render/Camera/GlossyReflection").GetAttribute("sourceName").Get() == "E<RG>.*L"
    assert stage.GetPrimAtPath("/Render/Camera/GlossyReflection").GetAttribute("sourceType").Get() == "lpe"


def _author_example_lpe_render_vars(stage):
    # [snippet:doc-example-lpe-render-vars-python]
    render_product = UsdRender.Product.Define(stage, "/Render/Camera")
    render_product.GetPrim().ApplyAPI("OmniRtxSettingsPtAdvancedAPI_1")
    render_product.GetCameraRel().SetTargets(["/World/Camera"])
    render_product.GetResolutionAttr().Set(Gf.Vec2i(1920, 1080))
    render_product.GetPrim().CreateAttribute(
        "omni:rtx:rendermode", Sdf.ValueTypeNames.Token
    ).Set("PathTracing")
    render_product.GetPrim().GetAttribute("omni:rtx:pt:radianceCache:enabled").Set(False)
    render_product.GetPrim().GetAttribute("omni:rtx:pt:denoising:enabled").Set(True)
    render_product.GetPrim().GetAttribute("omni:rtx:pt:denoising:optix:denoiseAOVs").Set(True)
    render_product.GetPrim().GetAttribute("omni:rtx:pt:samplesPerPixel").Set(128)

    expressions = {
        "DiffuseReflection": "E<RD>.*L",
        "GlossyReflection": "E<RG>.*L",
        "GlossyTransmission": "E<TG>.*L",
        "Caustics": "EDG.*L",
    }
    render_vars = []
    hdr_var = UsdRender.Var.Define(stage, "/Render/Camera/HdrColor")
    hdr_var.GetSourceNameAttr().Set("HdrColor")
    render_vars.append(hdr_var.GetPath())
    for name, expression in expressions.items():
        render_var = UsdRender.Var.Define(stage, f"/Render/Camera/{name}")
        render_var.GetSourceNameAttr().Set(expression)
        render_var.GetSourceTypeAttr().Set(UsdRender.Tokens.lpe)
        render_vars.append(render_var.GetPath())
    render_product.GetOrderedVarsRel().SetTargets(render_vars)
    # [/snippet:doc-example-lpe-render-vars-python]

    return render_product


def test_example_lpe_render_vars():
    stage = Usd.Stage.CreateInMemory()
    render_product = _author_example_lpe_render_vars(stage)

    assert render_product.GetOrderedVarsRel().GetTargets() == [
        Sdf.Path("/Render/Camera/HdrColor"),
        Sdf.Path("/Render/Camera/DiffuseReflection"),
        Sdf.Path("/Render/Camera/GlossyReflection"),
        Sdf.Path("/Render/Camera/GlossyTransmission"),
        Sdf.Path("/Render/Camera/Caustics"),
    ]


def _author_camera_attributes(stage):
    # [snippet:doc-camera-attributes-python]
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    camera = UsdGeom.Camera.Define(stage, "/Camera")
    camera.CreateProjectionAttr(UsdGeom.Tokens.perspective)
    camera.CreateFocalLengthAttr(0.5)
    camera.CreateFocusDistanceAttr(5.0)
    camera.CreateFStopAttr(2.8)
    camera.CreateHorizontalApertureAttr(0.36)
    camera.CreateHorizontalApertureOffsetAttr(0.0)
    camera.CreateVerticalApertureAttr(0.24)
    camera.CreateVerticalApertureOffsetAttr(0.0)
    camera.CreateClippingPlanesAttr([Gf.Vec4f(0.0, 1.0, 0.0, 0.0)])
    camera.CreateClippingRangeAttr(Gf.Vec2f(0.1, 1000.0))
    camera.CreateExposureAttr(0.0)
    camera.CreateExposureFStopAttr(2.8)
    camera.CreateExposureIsoAttr(100.0)
    camera.CreateExposureResponsivityAttr(1.0)
    camera.CreateExposureTimeAttr(1.0 / 120.0)
    # [/snippet:doc-camera-attributes-python]

    return camera


def test_camera_attributes():
    stage = Usd.Stage.CreateInMemory()
    camera = _author_camera_attributes(stage)

    assert UsdGeom.GetStageMetersPerUnit(stage) == 1.0
    assert camera.GetFocalLengthAttr().Get() == 0.5
    assert camera.GetClippingPlanesAttr().Get() == [Gf.Vec4f(0.0, 1.0, 0.0, 0.0)]
    assert camera.GetExposureTimeAttr().Get() == pytest.approx(1.0 / 120.0)


def _author_camera_lens_calibration(stage):
    # [snippet:doc-camera-lens-calibration-python]
    prim = UsdGeom.Camera.Define(stage, "/Camera").GetPrim()
    prim.ApplyAPI("OmniLensDistortionOpenCvPinholeAPI")
    prim.GetAttribute("omni:lensdistortion:model").Set("opencvPinhole")
    prim.GetAttribute("omni:lensdistortion:opencvPinhole:imageSize").Set(Gf.Vec2i(2048, 1024))
    for name, value in {
        "fx": 900.0,
        "fy": 800.0,
        "cx": 1024.0,
        "cy": 512.0,
        "k1": 0.0,
        "k2": 0.0,
        "p1": 0.0,
        "p2": 0.0,
    }.items():
        prim.GetAttribute(f"omni:lensdistortion:opencvPinhole:{name}").Set(value)
    # [/snippet:doc-camera-lens-calibration-python]

    return prim


def test_camera_lens_calibration():
    stage = Usd.Stage.CreateInMemory()
    prim = _author_camera_lens_calibration(stage)

    assert prim.HasAPI("OmniLensDistortionOpenCvPinholeAPI")
    assert prim.GetAttribute("omni:lensdistortion:opencvPinhole:fx").Get() == 900.0


def _author_camera_rolling_shutter(stage):
    # [snippet:doc-camera-rolling-shutter-python]
    prim = UsdGeom.Camera.Define(stage, "/Camera").GetPrim()
    prim.ApplyAPI("OmniRtxRollingShutterAPI")
    prim.GetAttribute("omni:rtx:rollingShutter:scanOrder").Set("topToBottom")
    prim.GetAttribute("omni:rtx:rollingShutter:lineOffset").Set(Gf.Vec2d(40, 1_000_000))
    prim.GetAttribute("omni:rtx:rollingShutter:lineExposure").Set(Gf.Vec2d(1, 32))
    # [/snippet:doc-camera-rolling-shutter-python]

    return prim


def test_camera_rolling_shutter():
    stage = Usd.Stage.CreateInMemory()
    prim = _author_camera_rolling_shutter(stage)

    assert prim.HasAPI("OmniRtxRollingShutterAPI")
    assert prim.GetAttribute("omni:rtx:rollingShutter:scanOrder").Get() == "topToBottom"


def _author_camera_scene_partitions(stage):
    # [snippet:doc-camera-scene-partitions-python]
    UsdGeom.Xform.Define(stage, "/World")

    left = UsdGeom.Xform.Define(stage, "/World/Left")
    left.GetPrim().GetReferences().AddReference("../../../tests/docs/data/cube.usd")
    UsdGeom.PrimvarsAPI(left).CreatePrimvar(
        "omni:scenePartition", Sdf.ValueTypeNames.Token, UsdGeom.Tokens.constant
    ).Set("left")
    left.AddTranslateOp().Set(Gf.Vec3d(-115, 0, 0))
    UsdGeom.Mesh(stage.GetPrimAtPath("/World/Left/Cube")).CreateDisplayColorAttr(
        [(0.9, 0.12, 0.025)]
    )

    right = UsdGeom.Xform.Define(stage, "/World/Right")
    right.GetPrim().GetReferences().AddReference("../../../tests/docs/data/torus.usd")
    UsdGeom.PrimvarsAPI(right).CreatePrimvar(
        "omni:scenePartition", Sdf.ValueTypeNames.Token, UsdGeom.Tokens.constant
    ).Set("right")
    right.AddTranslateOp().Set(Gf.Vec3d(115, 75, 0))
    right.AddRotateXYZOp().Set(Gf.Vec3f(90, 0, 0))
    UsdGeom.Mesh(stage.GetPrimAtPath("/World/Right/Torus")).CreateDisplayColorAttr(
        [(0.025, 0.3, 0.85)]
    )

    ground = UsdGeom.Xform.Define(stage, "/World/Ground")
    ground.GetPrim().GetReferences().AddReference("../../../tests/docs/data/ground.usd")
    ground.AddScaleOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Vec3d(20, 1, 20))

    environment = UsdLux.DomeLight.Define(stage, "/World/Environment")
    environment.CreateIntensityAttr(1000)
    environment.CreateTextureFileAttr("../../../tests/docs/data/studio.exr")
    environment.CreateTextureFormatAttr("latlong")

    for name, partition in (("Left", "left"), ("Right", "right"), ("Both", None)):
        camera = UsdGeom.Camera.Define(stage, f"/World/{name}Camera")
        if partition is not None:
            camera.GetPrim().CreateAttribute(
                "omni:scenePartition", Sdf.ValueTypeNames.Token, custom=True
            ).Set(partition)
        camera.CreateFocalLengthAttr(38)
        camera.CreateClippingRangeAttr(Gf.Vec2f(1, 100000))
        camera.AddTranslateOp().Set(Gf.Vec3d(0, 230, 850))
        camera.AddRotateXYZOp().Set(Gf.Vec3f(-12, 0, 0))
    # [/snippet:doc-camera-scene-partitions-python]

    return stage.GetPrimAtPath("/World")


def _camera_scene_partitions_python_stage():
    example_dir = Path(__file__).parents[3] / "examples/python/camera-scene-partitions"
    context = Ar.ResolverContext(Ar.DefaultResolverContext([str(example_dir)]))
    stage = Usd.Stage.CreateInMemory("scene.usda", pathResolverContext=context)
    _author_camera_scene_partitions(stage)
    return stage


def test_camera_scene_partitions():
    stage = _camera_scene_partitions_python_stage()
    assert stage.GetPrimAtPath("/World/LeftCamera").GetAttribute("omni:scenePartition").Get() == "left"
    assert stage.GetPrimAtPath("/World/RightCamera").GetAttribute("omni:scenePartition").Get() == "right"
    assert not stage.GetPrimAtPath("/World/BothCamera").HasAttribute("omni:scenePartition")
    for path, partition in (("/World/Left/Cube", "left"), ("/World/Right/Torus", "right")):
        inherited = UsdGeom.PrimvarsAPI(stage.GetPrimAtPath(path)).FindPrimvarWithInheritance("omni:scenePartition")
        assert inherited.Get() == partition
    for path in ("/World/Ground/ground", "/World/Environment"):
        assert not UsdGeom.PrimvarsAPI(stage.GetPrimAtPath(path)).FindPrimvarWithInheritance("omni:scenePartition")


def test_multi_rate_lidar_authoring():
    stage = Usd.Stage.CreateInMemory()
    # [snippet:doc-multi-rate-lidar-python]
    lidar = stage.DefinePrim("/World/Lidar40", "OmniLidar")
    lidar.SetMetadata("apiSchemas", Sdf.TokenListOp.Create(prependedItems=["OmniSensorGenericLidarCoreAPI"]))
    # Rational Hz: numerator / denominator. Each scan takes one 1/40-second step.
    lidar.CreateAttribute("omni:sensor:frameRate", Sdf.ValueTypeNames.Double2).Set(Gf.Vec2d(40, 1))
    lidar.CreateAttribute("omni:sensor:Core:partialOutputs", Sdf.ValueTypeNames.Bool).Set(False)
    lidar.CreateAttribute("omni:sensor:Core:includeInvalidPoints", Sdf.ValueTypeNames.Bool).Set(False)
    lidar.CreateAttribute("omni:sensor:Core:elementsCoordsType", Sdf.ValueTypeNames.Token).Set("CARTESIAN")
    # World-space points let both scans share the camera's viewpoint.
    lidar.CreateAttribute("omni:sensor:Core:outputFrameOfReference", Sdf.ValueTypeNames.Token).Set("WORLD")
    lidar.CreateAttribute("omni:sensor:Core:rotPatternFiringResDeg", Sdf.ValueTypeNames.Float).Set(1)
    UsdGeom.Xformable(lidar).AddTranslateOp().Set(Gf.Vec3d(-150, 150, 300))
    # [/snippet:doc-multi-rate-lidar-python]

    scene_path = Path(__file__).parents[3] / "examples/python/multi-rate-sensors/multi_rate.usda"
    authored = Usd.Stage.Open(str(scene_path))
    expected = authored.GetPrimAtPath("/World/Lidar40")
    assert expected.GetTypeName() == lidar.GetTypeName()
    assert expected.GetMetadata("apiSchemas") == lidar.GetMetadata("apiSchemas")
    for attribute in expected.GetAuthoredAttributes():
        equivalent = lidar.GetAttribute(attribute.GetName())
        assert equivalent.GetTypeName() == attribute.GetTypeName()
        assert equivalent.Get() == attribute.Get()


def test_multi_rate_camera_authoring():
    stage = Usd.Stage.CreateInMemory()
    # [snippet:doc-multi-rate-camera-python]
    camera = UsdGeom.Camera.Define(stage, "/World/Camera20")
    sensor = camera.GetPrim()
    sensor.SetMetadata(
        "apiSchemas", Sdf.TokenListOp.Create(prependedItems=["OmniSensorAPI", "OmniRtxRollingShutterAPI"])
    )
    sensor.CreateAttribute("omni:sensor:frameRate", Sdf.ValueTypeNames.Double2).Set(Gf.Vec2d(20, 1))
    # At 240 rows, 239 / 9560 + 1 / 40 = 1 / 20 second: two 25 ms steps.
    sensor.CreateAttribute("omni:rtx:rollingShutter:lineExposure", Sdf.ValueTypeNames.Double2).Set(Gf.Vec2d(1, 40))
    sensor.CreateAttribute("omni:rtx:rollingShutter:lineOffset", Sdf.ValueTypeNames.Double2).Set(Gf.Vec2d(1, 9560))
    sensor.CreateAttribute("omni:rtx:rollingShutter:scanOrder", Sdf.ValueTypeNames.Token).Set("topToBottom")
    camera.AddTranslateOp().Set(Gf.Vec3d(0, 350, 1000))
    camera.AddRotateXYZOp().Set(Gf.Vec3f(-20, 0, 0))
    # [/snippet:doc-multi-rate-camera-python]

    scene_path = Path(__file__).parents[3] / "examples/python/multi-rate-sensors/multi_rate.usda"
    authored = Usd.Stage.Open(str(scene_path))
    expected = authored.GetPrimAtPath("/World/Camera20")
    assert expected.GetMetadata("apiSchemas") == sensor.GetMetadata("apiSchemas")
    for attribute in expected.GetAuthoredAttributes():
        equivalent = sensor.GetAttribute(attribute.GetName())
        assert equivalent.GetTypeName() == attribute.GetTypeName()
        assert equivalent.Get() == attribute.Get()
