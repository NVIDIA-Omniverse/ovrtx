# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Validate USDA files used in sensors/cameras/versioning.rst."""

from pathlib import Path

from conftest import validate_usda

DATA_DIR = Path(__file__).parent / "data"


def test_camera_core_versioning():
    """Validate camera_core_versioning.usda pins the schema and model version."""
    usda_text = (DATA_DIR / "camera_core_versioning.usda").read_text()
    layer = validate_usda(usda_text)

    camera_prim = layer.GetPrimAtPath("/World/Camera")
    assert camera_prim, "/World/Camera prim should exist"

    # The applied class name is what selects the schema version, so the doc
    # sample is only correct if exactly one OmniSensorGeneric* class is applied.
    applied = [str(name) for name in camera_prim.GetInfo("apiSchemas").prependedItems]
    generic = [name for name in applied if name.startswith("OmniSensorGeneric")]
    assert generic == ["OmniSensorGenericCameraCoreAPI"]

    model_version = camera_prim.attributes["omni:sensor:modelVersion"]
    assert model_version.default == "0"

    assert layer.GetPrimAtPath("/Render/Camera"), "/Render/Camera prim should exist"


def test_depth_sensor_versioning():
    """Validate depth_sensor_versioning.usda pins the schema and model version."""
    usda_text = (DATA_DIR / "depth_sensor_versioning.usda").read_text()
    layer = validate_usda(usda_text)

    camera_prim = layer.GetPrimAtPath("/World/Camera")
    assert camera_prim, "/World/Camera prim should exist"

    applied = [str(name) for name in camera_prim.GetInfo("apiSchemas").prependedItems]
    generic = [name for name in applied if name.startswith("OmniSensorGeneric")]
    assert generic == ["OmniSensorGenericDepthSensorSingleViewAPI"]

    model_version = camera_prim.attributes["omni:sensor:modelVersion"]
    assert model_version.default == "0"

    # The sensor parameters travel with the camera, so they must be authored on
    # the same prim as the request rather than on the render product.
    assert "omni:sensor:depthSensor:baselineMM" in camera_prim.attributes

    assert layer.GetPrimAtPath("/Render/Camera"), "/Render/Camera prim should exist"
