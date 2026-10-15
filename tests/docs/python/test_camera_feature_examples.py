# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Run the public Camera feature examples against the active OVRTX build."""

import subprocess
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

EXAMPLE_ROOT = Path(__file__).parents[3] / "examples" / "python"
DOC_DATA = Path(__file__).parents[1] / "data"


def test_lpe_example_rejects_rrd_when_rerun_is_disabled(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(EXAMPLE_ROOT / "lpes" / "main.py"),
            "--rrd",
            str(tmp_path / "lpes.rrd"),
            "--no-rr",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "--rrd cannot be combined with --no-rr" in result.stderr

DEBUG_VIEW_SELECTORS = (
    "depth",
    "worldPosition",
    "barycentrics",
    "texcoord0",
    "texcoord1",
    "triangleNormal",
    "normal",
    "tangentu",
    "tangentv",
    "instanceId",
    "stableId",
    "nonVisualMaterialId",
    "targetMotion",
    "targetMotionArrows",
    "wire",
)


@pytest.mark.parametrize(
    "example_name",
    (
        pytest.param(
            "camera-lens-calibration",
            marks=pytest.mark.xfail(
                reason=(
                    "The remote robot-lineup payloads do not reliably load in GitHub CI; "
                    "issues/90"
                ),
                strict=False,
            ),
            id="camera-lens-calibration",
        ),
        "camera-rolling-shutter",
        "camera-scene-partitions",
        "lpes",
    ),
)
def test_camera_feature_example(example_name, output_dir):
    # Keep the individual views and contact sheets in CI's uploaded artifacts.
    output_path = output_dir / f"{example_name}.png"
    for previous_output in output_dir.glob(f"{example_name}*.png"):
        previous_output.unlink()
    command = [
        sys.executable,
        str(EXAMPLE_ROOT / example_name / "main.py"),
        "--no-rr",
        "--png",
        str(output_path),
    ]
    if example_name == "lpes":
        command.extend(
            [
                "--usd",
                str(DOC_DATA / "lpe_test_scene.usda"),
                "--resolution",
                "320",
                "180",
                "--spp",
                "16",
            ]
        )
    subprocess.run(
        command,
        check=True,
    )

    if example_name == "camera-lens-calibration":
        expected_views = {
            "pinhole": (752, 480),
            "fisheye": (640, 512),
            "omnidirectional-stereo": (1024, 512),
        }
        views = {}
        for name, expected_size in expected_views.items():
            view_path = output_path.with_name(f"{output_path.stem}-{name}.png")
            with Image.open(view_path) as image:
                assert image.size == expected_size
                pixels = np.asarray(image.convert("RGB"))
            assert np.any(pixels), f"{name} produced a black image: {view_path}"
            assert np.any(pixels != pixels[0, 0]), f"{name} produced a uniform image: {view_path}"
            views[name] = pixels

        with Image.open(output_path) as image:
            assert image.size == (2416, 512)

        # Compare the common crop so every calibrated projection participates
        # even though the authored RenderProducts use different resolutions.
        for (left_name, left), (right_name, right) in combinations(views.items(), 2):
            assert not np.array_equal(left[:480, :640], right[:480, :640]), (
                f"{left_name} and {right_name} produced identical calibrated views"
            )
        return

    if example_name == "camera-scene-partitions":
        with Image.open(output_path) as image:
            assert image.size == (1920, 528)
            pixels = np.asarray(image)[48:, :, :3]
        left, right, both = np.split(pixels, 3, axis=1)
        assert np.any(left)
        assert np.any(right)
        assert np.any(both)
        assert not np.array_equal(left, right)
        assert not np.array_equal(left, both)
        assert not np.array_equal(right, both)
        return

    if example_name == "lpes":
        expected_names = (
            "HdrColor",
            "DiffuseReflection",
            "GlossyReflection",
            "GlossyTransmission",
            "Caustics",
        )
        images = {}
        for name in expected_names:
            image_path = output_path.with_name(f"{output_path.stem}-{name}.png")
            with Image.open(image_path) as image:
                assert image.size == (320, 180)
                pixels = np.asarray(image)
            assert np.any(pixels)
            images[name] = pixels

        with Image.open(output_path) as image:
            assert image.size == (960, 440)

        # The LPEs must not silently alias beauty or each other.
        image_values = list(images.values())
        for left_index, left in enumerate(image_values):
            for right in image_values[left_index + 1 :]:
                assert not np.array_equal(left, right)

        # The left block is diffuse-dominant, while the center glass sphere is
        # transmission-dominant. These fixed regions verify LPE meaning without
        # relying on external scene contents.
        diffuse_block = np.s_[30:140, 10:100, :3]
        glass_sphere = np.s_[110:165, 165:218, :3]
        diffuse_on_block = float(np.mean(images["DiffuseReflection"][diffuse_block]))
        glossy_on_block = float(np.mean(images["GlossyReflection"][diffuse_block]))
        transmission_on_block = float(
            np.mean(images["GlossyTransmission"][diffuse_block])
        )
        diffuse_on_sphere = float(np.mean(images["DiffuseReflection"][glass_sphere]))
        transmission_on_sphere = float(
            np.mean(images["GlossyTransmission"][glass_sphere])
        )
        assert diffuse_on_block > 1.8 * glossy_on_block
        assert transmission_on_block < 0.05 * diffuse_on_block
        assert transmission_on_sphere > 1.1 * diffuse_on_sphere

        return

    with Image.open(output_path) as image:
        assert image.width == 1280
        assert image.height == 480
        pixels = np.asarray(image)

    left, right = np.split(pixels[..., :3], 2, axis=1)
    assert np.any(left)
    assert np.any(right)
    assert not np.array_equal(left, right)

@pytest.mark.skip(reason="Temporarily disabled: issues/140")
def test_debug_views_example(tmp_path):
    output_path = tmp_path / "debug-views.png"
    subprocess.run(
        [
            sys.executable,
            str(EXAMPLE_ROOT / "debug-views" / "main.py"),
            "--no-rr",
            "--png",
            str(output_path),
            "--resolution",
            "320",
            "180",
            "--warmup-frames",
            "1",
        ],
        check=True,
    )

    with Image.open(output_path) as image:
        assert image.size == (960, 1248)
        assert np.any(np.asarray(image))

    views = {}
    for selector in DEBUG_VIEW_SELECTORS:
        view_path = output_path.with_name(f"{output_path.stem}-{selector}.png")
        with Image.open(view_path) as image:
            assert image.size == (320, 180)
            views[selector] = np.array(image.convert("RGB"))

    continuous_views = (
        "worldPosition",
        "barycentrics",
        "texcoord0",
        "texcoord1",
        "triangleNormal",
        "normal",
        "tangentu",
        "tangentv",
    )
    unique_colors = {
        selector: len(np.unique(pixels.reshape(-1, 3), axis=0))
        for selector, pixels in views.items()
    }

    assert all(unique_colors[selector] > 100 for selector in continuous_views)
    assert len({views[selector].tobytes() for selector in continuous_views}) == len(
        continuous_views
    )

    assert unique_colors["depth"] == 1
    assert np.any(views["depth"])
    assert unique_colors["nonVisualMaterialId"] == 1
    assert np.any(views["nonVisualMaterialId"])

    assert 1 < unique_colors["instanceId"] < 4096
    assert np.any(views["instanceId"])

    # Stable IDs are disabled in the public example, so this scene can only smoke-test
    # that the selector renders and writes its correctly sized output file above.

    assert 1 < unique_colors["wire"] < 100
    assert np.any(views["wire"])
    assert unique_colors["targetMotion"] < 100
    assert np.any(views["targetMotion"])
    assert unique_colors["targetMotionArrows"] < 100
    assert np.any(views["targetMotionArrows"])
