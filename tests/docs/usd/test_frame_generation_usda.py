# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Validate USDA used in frame_generation.rst."""

from pathlib import Path

from conftest import validate_usda

DATA_FILE = Path(__file__).parent / "data" / "frame_generation_render_product.usda"


def test_frame_generation_render_product():
    """Validate the frame-generation RenderProduct and settings."""
    layer = validate_usda(DATA_FILE.read_text())
    camera_prim = layer.GetPrimAtPath("/Render/Camera")
    assert camera_prim, "/Render/Camera prim should exist"
    assert camera_prim.properties["omni:rtx:rendermode"].default == "RealTimePathTracing"
    assert camera_prim.properties["omni:rtx:dlss:frameGeneration"].default is True
    assert (
        camera_prim.properties[
            "omni:rtx:dlss:frameGenerationInterpolatedFrameCount"
        ].default
        == 3
    )
    assert layer.GetPrimAtPath("/Render/Camera/LdrColor")
