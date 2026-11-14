# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Validate USDA files used in set_up_depth_product.rst."""

from pathlib import Path

from pxr import Sdf

from conftest import validate_usda

DATA_DIR = Path(__file__).parent / "data"

PRODUCT = "/Render/CameraDepthSingleView"
CAMERA = "/World/Camera"

# The three camera outputs the model reads, then the five it writes.
RENDER_VARS = (
    "LdrColor",
    "DistanceToImagePlaneSD",
    "Camera3dPositionSD",
    "DepthSensorImager",
    "DepthSensorDistance",
    "DepthSensorPointCloudPosition",
    "DepthSensorPointCloudColor",
    "DepthSensorOutputVisualization",
)


def test_depth_sensor_render_product():
    """Validate depth_sensor_render_product.usda has expected structure."""
    usda_text = (DATA_DIR / "depth_sensor_render_product.usda").read_text()
    layer = validate_usda(usda_text)

    product = layer.GetPrimAtPath(PRODUCT)
    assert product, f"{PRODUCT} prim should exist"

    camera_prim = layer.GetPrimAtPath(CAMERA)
    assert camera_prim, f"{CAMERA} prim should exist"
    api_schemas = camera_prim.GetInfo("apiSchemas").prependedItems
    assert "OmniSensorGenericDepthSensorSingleViewAPI" in api_schemas, (
        f"{CAMERA} should apply OmniSensorGenericDepthSensorSingleViewAPI"
    )
    assert "apiSchemas" not in product.ListInfoKeys(), f"{PRODUCT} carries no depth schema; the camera does"
    assert "omni:sensor:depthSensor:baselineMM" in camera_prim.attributes

    camera = product.relationships["camera"]
    assert camera, f"{PRODUCT} should have a camera relationship"
    assert list(camera.targetPathList.explicitItems) == [Sdf.Path(CAMERA)]

    for name in RENDER_VARS:
        render_var = layer.GetPrimAtPath(f"{PRODUCT}/{name}")
        assert render_var, f"{PRODUCT}/{name} prim should exist"
        assert render_var.attributes["sourceName"].default == name

    ordered_vars = product.relationships["orderedVars"]
    assert ordered_vars, f"{PRODUCT} should have an orderedVars relationship"
    listed = [
        path.MakeAbsolutePath(product.path)
        for path in ordered_vars.targetPathList.explicitItems
    ]
    assert listed == [Sdf.Path(f"{PRODUCT}/{name}") for name in RENDER_VARS], (
        "orderedVars should request all eight RenderVars, inputs first"
    )
