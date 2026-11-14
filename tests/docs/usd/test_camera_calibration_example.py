# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Run calibration in its CPU environment and compose both reference examples."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from pxr import Usd, UsdGeom

EXAMPLE = Path(__file__).resolve().parents[3] / "examples/python/camera-calibration"


@pytest.fixture(scope="module")
def calibrated(tmp_path_factory):
    work = tmp_path_factory.mktemp("calibration")
    output = work / "_out/calibrated_camera.usda"
    photos = sorted((EXAMPLE / "input_images").glob("*.png"))
    assert len(photos) == 8
    for photo in photos:
        assert photo.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), f"hydrate LFS image: {photo}"
    subprocess.run(
        [os.environ.get("UV", "uv"), "run", "--project", str(EXAMPLE), str(EXAMPLE / "main.py"),
         "--fisheye", "--pattern", "20x14", "--output-usd", str(output)],
        cwd=work, check=True, timeout=300,
    )
    return work, output


def test_calibrated_attributes_match_documented_excerpt(calibrated):
    _, output = calibrated
    stage = Usd.Stage.Open(str(output))
    camera = stage.GetDefaultPrim()
    assert camera and camera.IsA(UsdGeom.Camera), "defaultPrim must support asset references"
    assert camera.GetAttribute("calibration:reprojectionRmsPixels").Get() < 1.0
    shown = Usd.Stage.Open(str(EXAMPLE / "doc_snippets/camera_attributes.usda"))
    expected = shown.GetPrimAtPath("/CalibratedCamera")
    assert expected.GetMetadata("apiSchemas") == camera.GetMetadata("apiSchemas")
    for attr in expected.GetAuthoredAttributes():
        actual = camera.GetAttribute(attr.GetName())
        assert actual and actual.GetTypeName() == attr.GetTypeName()
        if attr.GetName().endswith(":imageSize"):
            assert actual.Get() == attr.Get()
        else:
            # Allow solver rounding, not stale displayed calibration coefficients.
            assert actual.Get() == pytest.approx(attr.Get(), rel=1e-4, abs=1e-6), attr.GetName()


def test_documented_reference_forms_compose_calibration(calibrated):
    work, output = calibrated
    subprocess.run(
        [os.environ.get("UV", "uv"), "run", "--project", str(EXAMPLE),
         str(EXAMPLE / "doc_snippets/reference_camera.py")],
        cwd=work, check=True, timeout=60,
    )
    usd_path = output.parent / "reference.usda"
    shutil.copyfile(EXAMPLE / "doc_snippets/reference_camera.usda", usd_path)
    source = Usd.Stage.Open(str(output))
    for path in (output.parent / "scene.usda", usd_path):
        stage = Usd.Stage.Open(str(path))
        camera = stage.GetPrimAtPath("/World/Camera")
        assert camera and camera.IsA(UsdGeom.Camera)
        assert camera.GetAttribute("omni:lensdistortion:opencvFisheye:fx").Get() == \
            source.GetDefaultPrim().GetAttribute("omni:lensdistortion:opencvFisheye:fx").Get()
        assert camera.GetAttribute("omni:lensdistortion:opencvFisheye:imageSize").Get() == (1920, 1536)
