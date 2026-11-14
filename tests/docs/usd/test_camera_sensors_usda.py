# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Validate USDA files used in the camera documentation pages."""

from pathlib import Path

from conftest import validate_usda
from pxr import Gf, Sdf

DATA_DIR = Path(__file__).parent / "data"


def test_camera_sensor_render_product():
    """Validate camera_sensor_render_product.usda has expected structure."""
    usda_text = (DATA_DIR / "camera_sensor_render_product.usda").read_text()
    layer = validate_usda(usda_text)

    camera_prim = layer.GetPrimAtPath("/Render/Camera")
    assert camera_prim, "/Render/Camera prim should exist"

    ldr_prim = layer.GetPrimAtPath("/Render/Camera/LdrColor")
    assert ldr_prim, "/Render/Camera/LdrColor prim should exist"

    hdr_prim = layer.GetPrimAtPath("/Render/Camera/HdrColor")
    assert hdr_prim, "/Render/Camera/HdrColor prim should exist"


def test_camera_core_request():
    """Validate camera_core_request.usda has expected structure.

    The Camera generic core model's Outputs page shows this as the smallest
    complete request: a camera carrying the schema, and a product bound to it
    that requests the input AOV and the full-pipeline terminal.
    """
    usda_text = (DATA_DIR / "camera_core_request.usda").read_text()
    layer = validate_usda(usda_text)

    camera_prim = layer.GetPrimAtPath("/SensorCamera")
    assert camera_prim, "/SensorCamera prim should exist"
    assert "OmniSensorGenericCameraCoreAPI" in camera_prim.GetInfo("apiSchemas").prependedItems

    product_prim = layer.GetPrimAtPath("/Render/SensorCamera")
    assert product_prim, "/Render/SensorCamera prim should exist"
    assert product_prim.attributes["resolution"].default == Gf.Vec2i(1920, 1080)
    assert list(product_prim.relationships["camera"].targetPathList.explicitItems) == [Sdf.Path("/SensorCamera")]

    for name in ("HdrColor", "OmniCameraSensorPostIsp"):
        render_var = layer.GetPrimAtPath(f"/Render/SensorCamera/{name}")
        assert render_var, f"/Render/SensorCamera/{name} prim should exist"
        assert render_var.attributes["sourceName"].default == name

    assert list(product_prim.relationships["orderedVars"].targetPathList.explicitItems) == [
        Sdf.Path("/Render/SensorCamera/HdrColor"),
        Sdf.Path("/Render/SensorCamera/OmniCameraSensorPostIsp"),
    ]
