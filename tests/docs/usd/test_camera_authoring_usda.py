# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Validate USDA camera-authoring snippets used by the public docs."""

from pathlib import Path

import conftest as docs_conftest
import pytest
from conftest import validate_usda
from pxr import Gf, Sdf, Usd, UsdGeom
from test_usd_python_examples import (
    _author_camera_attributes,
    _author_camera_lens_calibration,
    _author_camera_rolling_shutter,
    _camera_scene_partitions_python_stage,
)


DATA_DIR = Path(__file__).parent / "data"


def test_schema_plugin_dir_uses_packaged_root(monkeypatch, tmp_path):
    plugin_root = tmp_path / "usd_plugins"
    monkeypatch.setenv(docs_conftest._PACKAGED_SCHEMA_ROOT_ENV, str(plugin_root))

    assert docs_conftest._schema_plugin_dir("omni_lens_distortion") == plugin_root / "omni_lens_distortion"


def test_schema_plugin_dir_uses_source_tree_without_package_override(monkeypatch, tmp_path):
    monkeypatch.delenv(docs_conftest._PACKAGED_SCHEMA_ROOT_ENV, raising=False)
    source_root = tmp_path / "source"
    conftest_path = source_root / "projects/sdk/tests/docs/usd/conftest.py"
    plugin_dir = source_root / "schemas/rtx_settings/usd_plugins"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugInfo.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(docs_conftest, "__file__", str(conftest_path))

    assert docs_conftest._schema_plugin_dir("rtx_settings") == plugin_dir


def test_schema_plugin_dir_reports_missing_standalone_sdk(monkeypatch, tmp_path):
    monkeypatch.delenv(docs_conftest._PACKAGED_SCHEMA_ROOT_ENV, raising=False)
    monkeypatch.setattr(docs_conftest, "__file__", str(tmp_path / "public/conftest.py"))

    with pytest.raises(RuntimeError, match="Set OVRTX_DOCS_USD_PLUGIN_ROOT"):
        docs_conftest._schema_plugin_dir("nonexistent_schema")


def test_conftest_imports_from_shallow_public_layout(monkeypatch, tmp_path):
    source = Path(docs_conftest.__file__).read_text(encoding="utf-8")
    # A virtual root-level filename reproduces the shallow-checkout bug on both
    # operating systems without writing outside the test's workspace.
    public_path = Path(Path.cwd().anchor) / "conftest.py"
    packaged_root = tmp_path / "sdk/bin/usd_plugins"
    for schema in ("omni_lens_distortion", "omni_light_shaping", "physical_lighting", "omni_dome_light", "rtx_settings"):
        plugin_dir = packaged_root / schema
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "plugInfo.json").write_text('{"Plugins": []}', encoding="utf-8")
    monkeypatch.setenv(docs_conftest._PACKAGED_SCHEMA_ROOT_ENV, str(packaged_root))
    namespace = {"__file__": str(public_path)}
    exec(compile(source, str(public_path), "exec"), namespace)

    assert namespace["_schema_plugin_dir"]("omni_lens_distortion") == packaged_root / "omni_lens_distortion"


def _load_data_layer(name: str) -> Sdf.Layer:
    return validate_usda((DATA_DIR / name).read_text())


def _canonical_value(value):
    if isinstance(value, float):
        return round(value, 8)
    if isinstance(value, str) or value is None:
        return value
    try:
        return tuple(_canonical_value(item) for item in value)
    except TypeError:
        return value


def _authored_snapshot(prim):
    return {
        attribute.GetName(): (
            attribute.GetTypeName(),
            attribute.GetVariability(),
            _canonical_value(attribute.Get()),
        )
        for attribute in prim.GetAuthoredAttributes()
    }


def _authored_api_schemas(prim):
    operation = prim.GetPrimStack()[0].GetInfo("apiSchemas")
    return tuple(operation.prependedItems) if operation else ()


def _assert_schema_attribute(definition, name, type_name, default):
    attribute = definition.GetSchemaAttributeSpec(name)
    assert attribute.typeName == type_name
    if isinstance(default, float):
        assert attribute.default == pytest.approx(default)
    else:
        assert attribute.default == default


def test_usd_camera_attribute_schema_tables():
    stage = Usd.Stage.CreateInMemory()
    camera = UsdGeom.Camera.Define(stage, "/Camera")
    expected = {
        "focalLength": (Sdf.ValueTypeNames.Float, 50.0, Sdf.VariabilityVarying),
        "focusDistance": (Sdf.ValueTypeNames.Float, 0.0, Sdf.VariabilityVarying),
        "fStop": (Sdf.ValueTypeNames.Float, 0.0, Sdf.VariabilityVarying),
        "projection": (Sdf.ValueTypeNames.Token, "perspective", Sdf.VariabilityVarying),
        "horizontalAperture": (Sdf.ValueTypeNames.Float, 20.955, Sdf.VariabilityVarying),
        "horizontalApertureOffset": (Sdf.ValueTypeNames.Float, 0.0, Sdf.VariabilityVarying),
        "verticalAperture": (Sdf.ValueTypeNames.Float, 15.2908, Sdf.VariabilityVarying),
        "verticalApertureOffset": (Sdf.ValueTypeNames.Float, 0.0, Sdf.VariabilityVarying),
        "clippingPlanes": (Sdf.ValueTypeNames.Float4Array, [], Sdf.VariabilityVarying),
        "clippingRange": (Sdf.ValueTypeNames.Float2, Gf.Vec2f(1, 1_000_000), Sdf.VariabilityVarying),
        "exposure": (Sdf.ValueTypeNames.Float, 0.0, Sdf.VariabilityVarying),
        "exposure:fStop": (Sdf.ValueTypeNames.Float, 1.0, Sdf.VariabilityVarying),
        "exposure:iso": (Sdf.ValueTypeNames.Float, 100.0, Sdf.VariabilityVarying),
        "exposure:responsivity": (Sdf.ValueTypeNames.Float, 1.0, Sdf.VariabilityVarying),
        "exposure:time": (Sdf.ValueTypeNames.Float, 1.0, Sdf.VariabilityVarying),
    }
    for name, (type_name, default, variability) in expected.items():
        attribute = camera.GetPrim().GetAttribute(name)
        assert attribute.GetTypeName() == type_name
        assert attribute.GetVariability() == variability
        if isinstance(default, float):
            assert attribute.Get() == pytest.approx(default)
        else:
            assert attribute.Get() == default


def test_camera_attributes_usda():
    layer = _load_data_layer("camera_attributes.usda")
    stage = Usd.Stage.Open(layer)
    camera = stage.GetPrimAtPath("/Camera")
    assert camera
    python_stage = Usd.Stage.CreateInMemory()
    python_camera = _author_camera_attributes(python_stage).GetPrim()
    assert UsdGeom.GetStageMetersPerUnit(stage) == UsdGeom.GetStageMetersPerUnit(python_stage)
    assert _authored_snapshot(camera) == _authored_snapshot(python_camera)


def test_camera_lens_calibration_usda():
    registry = Usd.SchemaRegistry()
    pinhole = registry.FindAppliedAPIPrimDefinition("OmniLensDistortionOpenCvPinholeAPI")
    fisheye = registry.FindAppliedAPIPrimDefinition("OmniLensDistortionOpenCvFisheyeAPI")
    lut = registry.FindAppliedAPIPrimDefinition("OmniLensDistortionLutAPI")
    ods = registry.FindAppliedAPIPrimDefinition("OmniLensDistortionOmniDirectionalStereoAPI")

    assert set(pinhole.GetPropertyNames()) == {
        "omni:lensdistortion:model",
        "omni:lensdistortion:opencvPinhole:imageSize",
        *{f"omni:lensdistortion:opencvPinhole:{name}" for name in ("fx", "fy", "cx", "cy")},
        *{f"omni:lensdistortion:opencvPinhole:k{i}" for i in range(1, 7)},
        *{f"omni:lensdistortion:opencvPinhole:p{i}" for i in range(1, 3)},
        *{f"omni:lensdistortion:opencvPinhole:s{i}" for i in range(1, 5)},
    }
    assert set(fisheye.GetPropertyNames()) == {
        "omni:lensdistortion:model",
        "omni:lensdistortion:opencvFisheye:imageSize",
        *{f"omni:lensdistortion:opencvFisheye:{name}" for name in ("fx", "fy", "cx", "cy")},
        *{f"omni:lensdistortion:opencvFisheye:k{i}" for i in range(1, 5)},
    }
    assert set(lut.GetPropertyNames()) == {
        "omni:lensdistortion:model",
        "omni:lensdistortion:lut:nominalWidth",
        "omni:lensdistortion:lut:nominalHeight",
        "omni:lensdistortion:lut:opticalCenter",
        "omni:lensdistortion:lut:rayEnterDirectionTexture",
        "omni:lensdistortion:lut:rayExitPositionTexture",
    }
    assert set(ods.GetPropertyNames()) == {
        "omni:lensdistortion:model",
        "omni:lensdistortion:omniDirectionalStereo:isLeftEye",
        "omni:lensdistortion:omniDirectionalStereo:interpupillaryDistance",
    }
    for name in (
        "OmniLensDistortionFthetaAPI",
        "OmniLensDistortionKannalaBrandtK3API",
        "OmniLensDistortionRadTanThinPrismAPI",
    ):
        assert registry.FindAppliedAPIPrimDefinition(name)

    pinhole_prefix = "omni:lensdistortion:opencvPinhole:"
    _assert_schema_attribute(pinhole, "omni:lensdistortion:model", Sdf.ValueTypeNames.Token, "opencvPinhole")
    _assert_schema_attribute(pinhole, pinhole_prefix + "imageSize", Sdf.ValueTypeNames.Int2, Gf.Vec2i(2048, 1024))
    for name, default in {"fx": 900.0, "fy": 800.0, "cx": 1024.0, "cy": 512.0}.items():
        _assert_schema_attribute(pinhole, pinhole_prefix + name, Sdf.ValueTypeNames.Float, default)
    for name in [*(f"k{i}" for i in range(1, 7)), "p1", "p2", *(f"s{i}" for i in range(1, 5))]:
        _assert_schema_attribute(pinhole, pinhole_prefix + name, Sdf.ValueTypeNames.Float, 0.0)

    fisheye_prefix = "omni:lensdistortion:opencvFisheye:"
    _assert_schema_attribute(fisheye, "omni:lensdistortion:model", Sdf.ValueTypeNames.Token, "opencvFisheye")
    _assert_schema_attribute(fisheye, fisheye_prefix + "imageSize", Sdf.ValueTypeNames.Int2, Gf.Vec2i(2048, 1024))
    for name, default in {"fx": 900.0, "fy": 800.0, "cx": 1024.0, "cy": 512.0}.items():
        _assert_schema_attribute(fisheye, fisheye_prefix + name, Sdf.ValueTypeNames.Float, default)
    for index, default in enumerate((0.00245, 0.0, 0.0, 0.0), start=1):
        _assert_schema_attribute(fisheye, fisheye_prefix + f"k{index}", Sdf.ValueTypeNames.Float, default)

    lut_prefix = "omni:lensdistortion:lut:"
    _assert_schema_attribute(lut, "omni:lensdistortion:model", Sdf.ValueTypeNames.Token, "lut")
    _assert_schema_attribute(lut, lut_prefix + "nominalWidth", Sdf.ValueTypeNames.Float, 1936.0)
    _assert_schema_attribute(lut, lut_prefix + "nominalHeight", Sdf.ValueTypeNames.Float, 1216.0)
    _assert_schema_attribute(
        lut,
        lut_prefix + "opticalCenter",
        Sdf.ValueTypeNames.Float2,
        Gf.Vec2f(970.94244, 600.3748),
    )
    _assert_schema_attribute(lut, lut_prefix + "rayEnterDirectionTexture", Sdf.ValueTypeNames.Asset, Sdf.AssetPath())
    _assert_schema_attribute(lut, lut_prefix + "rayExitPositionTexture", Sdf.ValueTypeNames.Asset, Sdf.AssetPath())

    ods_prefix = "omni:lensdistortion:omniDirectionalStereo:"
    _assert_schema_attribute(ods, "omni:lensdistortion:model", Sdf.ValueTypeNames.Token, "omniDirectionalStereo")
    _assert_schema_attribute(ods, ods_prefix + "isLeftEye", Sdf.ValueTypeNames.Bool, False)
    _assert_schema_attribute(ods, ods_prefix + "interpupillaryDistance", Sdf.ValueTypeNames.Float, 0.064)

    layer = _load_data_layer("camera_lens_calibration.usda")
    stage = Usd.Stage.Open(layer)
    camera = stage.GetPrimAtPath("/Camera")
    assert camera.HasAPI("OmniLensDistortionOpenCvPinholeAPI")
    python_stage = Usd.Stage.CreateInMemory()
    python_camera = _author_camera_lens_calibration(python_stage)
    assert _authored_api_schemas(camera) == _authored_api_schemas(python_camera)
    assert _authored_snapshot(camera) == _authored_snapshot(python_camera)


def test_camera_rolling_shutter_usda():
    definition = Usd.SchemaRegistry().FindAppliedAPIPrimDefinition("OmniRtxRollingShutterAPI")
    assert definition
    assert set(definition.GetPropertyNames()) == {
        "omni:rtx:rollingShutter:scanOrder",
        "omni:rtx:rollingShutter:lineOffset",
        "omni:rtx:rollingShutter:lineExposure",
    }
    scan_order = definition.GetSchemaAttributeSpec("omni:rtx:rollingShutter:scanOrder")
    line_offset = definition.GetSchemaAttributeSpec("omni:rtx:rollingShutter:lineOffset")
    line_exposure = definition.GetSchemaAttributeSpec("omni:rtx:rollingShutter:lineExposure")
    assert scan_order.default == "none"
    assert scan_order.typeName == Sdf.ValueTypeNames.Token
    assert scan_order.variability == Sdf.VariabilityVarying
    assert list(scan_order.GetInfo("allowedTokens")) == [
        "none",
        "topToBottom",
        "bottomToTop",
        "leftToRight",
        "rightToLeft",
    ]
    assert line_offset.typeName == Sdf.ValueTypeNames.Double2
    assert line_offset.default == Gf.Vec2d(0, 1)
    assert line_exposure.typeName == Sdf.ValueTypeNames.Double2
    assert line_exposure.default == Gf.Vec2d(0, 1)

    layer = _load_data_layer("camera_rolling_shutter.usda")
    stage = Usd.Stage.Open(layer)
    camera = stage.GetPrimAtPath("/Camera")
    assert camera.HasAPI("OmniRtxRollingShutterAPI")
    python_stage = Usd.Stage.CreateInMemory()
    python_camera = _author_camera_rolling_shutter(python_stage)
    assert _authored_api_schemas(camera) == _authored_api_schemas(python_camera)
    assert _authored_snapshot(camera) == _authored_snapshot(python_camera)


def test_camera_scene_partitions_usda():
    example = DATA_DIR / "../../../../examples/python/camera-scene-partitions/scene_partitions.usda"
    stage = Usd.Stage.Open(str(example.resolve()))
    python_stage = _camera_scene_partitions_python_stage()
    for prim in Usd.PrimRange(stage.GetPrimAtPath("/World")):
        python_prim = python_stage.GetPrimAtPath(prim.GetPath())
        assert python_prim, str(prim.GetPath())
        assert prim.GetTypeName() == python_prim.GetTypeName()
        assert _authored_snapshot(prim) == _authored_snapshot(python_prim), str(prim.GetPath())


@pytest.mark.parametrize(
    ("relative_path", "camera_paths", "product_paths"),
    [
        (
            "../../../../examples/python/camera-lens-calibration/camera_lens_calibration.usda",
            (
                "/World/Camera",
                "/World/FisheyeCamera",
                "/World/OmniDirectionalStereoCamera",
            ),
            (
                "/Render/Pinhole",
                "/Render/Fisheye",
                "/Render/OmniDirectionalStereo",
            ),
        ),
        (
            "../../../../examples/python/camera-scene-partitions/scene_partitions.usda",
            ("/World/LeftCamera", "/World/RightCamera", "/World/BothCamera"),
            ("/Render/Left", "/Render/Right", "/Render/Both"),
        ),
        (
            "../../../../examples/python/camera-rolling-shutter/rolling_shutter.usda",
            ("/World/Camera", "/World/GlobalShutterCamera"),
            ("/Render/Camera", "/Render/GlobalShutterCamera"),
        ),
    ],
)
def test_camera_example_scene(relative_path, camera_paths, product_paths):
    # Preserve the file's anchor for local sublayers without loading remote payloads.
    stage = Usd.Stage.Open(str((DATA_DIR / relative_path).resolve()), load=Usd.Stage.LoadNone)
    for path in (*camera_paths, *product_paths):
        assert stage.GetPrimAtPath(path).IsDefined()
    for path in camera_paths:
        assert stage.GetPrimAtPath(path).IsA(UsdGeom.Camera)

    if relative_path.endswith("camera_lens_calibration.usda"):
        assert UsdGeom.GetStageMetersPerUnit(stage) == 1
        assert UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.z
        ods_camera = stage.GetPrimAtPath("/World/OmniDirectionalStereoCamera")
        assert ods_camera.HasAPI("OmniLensDistortionOmniDirectionalStereoAPI")
        ods_product = stage.GetPrimAtPath("/Render/OmniDirectionalStereo")
        assert ods_product.GetAttribute("resolution").Get() == Gf.Vec2i(1024, 512)
