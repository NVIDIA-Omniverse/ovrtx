# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Validate the public projector-light calibration example."""

import importlib.util
import subprocess
import sys
import textwrap
from pathlib import Path

import Imath
import numpy as np
import OpenEXR
from PIL import Image

EXAMPLE_DIR = Path(__file__).parents[3] / "examples/python/projector-light-calibration"
GENERATOR_PATH = EXAMPLE_DIR / "generate_direction_texture.py"
MAIN_PATH = EXAMPLE_DIR / "main.py"


def load_generator():
    spec = importlib.util.spec_from_file_location(
        "projector_direction_texture", GENERATOR_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_example():
    sys.path.insert(0, str(EXAMPLE_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "projector_light_example", MAIN_PATH
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def extract_snippet(path: Path, name: str) -> str:
    text = path.read_text()
    start = text.index(f"# [snippet:{name}]")
    start = text.index("\n", start) + 1
    end = text.index(f"# [/snippet:{name}]", start)
    return textwrap.dedent(text[start:end]).strip()


def test_projector_direction_texture_contract(tmp_path):
    generator = load_generator()

    directions = generator.create_octahedral_directions(texture_size=3)
    assert np.allclose(directions[1, 1], [0.0, 0.0, 1.0])
    assert np.allclose(
        directions[1, 2],
        [2.0 / np.sqrt(5.0), 0.0, 1.0 / np.sqrt(5.0)],
    )
    assert np.allclose(
        directions[2, 1],
        [0.0, 2.0 / np.sqrt(5.0), 1.0 / np.sqrt(5.0)],
    )

    simple_image_size = (100, 80)
    simple_matrix = np.array([[50.0, 0.0, 40.0], [0.0, 60.0, 30.0], [0.0, 0.0, 1.0]])
    sample_directions = np.array([[[0.0, 0.0, 1.0], [0.2, -0.1, 1.0]]])
    simple_uv = generator.project_directions_to_uv(
        sample_directions,
        simple_image_size,
        simple_matrix,
        np.zeros(5),
    )
    assert np.allclose(simple_uv[0, 0], [0.4, 0.375])
    assert np.allclose(simple_uv[0, 1], [0.5, 0.3])

    off_axis = np.array([[[0.55, -0.25, 0.8]]], dtype=np.float64)
    off_axis /= np.linalg.norm(off_axis, axis=-1, keepdims=True)
    distorted_uv = generator.project_directions_to_uv(
        off_axis,
        generator.IMAGE_SIZE,
        generator.CAMERA_MATRIX,
        generator.DISTORTION,
    )
    undistorted_uv = generator.project_directions_to_uv(
        off_axis,
        generator.IMAGE_SIZE,
        generator.CAMERA_MATRIX,
        np.zeros_like(generator.DISTORTION),
    )
    assert np.allclose(distorted_uv[0, 0], [0.8586487, 0.24744262], atol=1.0e-6)
    assert np.allclose(undistorted_uv[0, 0], [0.9244792, 0.20529515], atol=1.0e-6)
    assert np.linalg.norm(distorted_uv - undistorted_uv) > 0.05

    output_path = tmp_path / "direction.exr"
    generated_uv = generator.generate_direction_texture(output_path, texture_size=64)

    exr = OpenEXR.InputFile(str(output_path))
    header = exr.header()
    assert set(header["channels"]) == {"R", "G"}
    assert all(
        channel.type == Imath.PixelType(Imath.PixelType.FLOAT)
        for channel in header["channels"].values()
    )
    assert header["dataWindow"].max.x == 63
    assert header["dataWindow"].max.y == 63

    pixel_type = Imath.PixelType(Imath.PixelType.FLOAT)
    stored_uv = np.stack(
        [
            np.frombuffer(exr.channel("R", pixel_type), dtype=np.float32),
            np.frombuffer(exr.channel("G", pixel_type), dtype=np.float32),
        ],
        axis=-1,
    ).reshape(64, 64, 2)
    exr.close()

    assert np.array_equal(stored_uv, generated_uv)
    valid = np.all((stored_uv > 0.0) & (stored_uv < 1.0), axis=-1)
    invalid = np.all(stored_uv == -1.0, axis=-1)
    assert np.all(valid | invalid)
    assert np.any(valid)
    assert np.any(invalid)

    central_uv = stored_uv[31:33, 31:33].mean(axis=(0, 1))
    principal_uv = np.array(
        [
            generator.CAMERA_MATRIX[0, 2] / generator.IMAGE_SIZE[0],
            generator.CAMERA_MATRIX[1, 2] / generator.IMAGE_SIZE[1],
        ]
    )
    assert np.allclose(central_uv, principal_uv, atol=0.02)


def test_projector_light_example_readme_snippets_match():
    readme = (EXAMPLE_DIR / "README.md").read_text()
    for name in (
        "doc-projector-opencv-calibration",
        "doc-projector-octahedral-directions",
        "doc-projector-opencv-project",
        "doc-projector-write-direction-texture",
    ):
        assert extract_snippet(GENERATOR_PATH, name) in readme
    assert extract_snippet(MAIN_PATH, "doc-projector-generate-and-render") in readme


def test_projector_light_calibration_example(tmp_path):
    example = load_example()
    direction_path = tmp_path / "expected-direction.exr"
    layer = example.build_projector_layer(direction_path)
    assert f"@{example.BASE_SCENE.as_posix()}@" in layer
    assert (
        f"asset projector:directionTexture:file = @{direction_path.as_posix()}@"
        in layer
    )

    output_path = tmp_path / "projector-light-calibration.png"
    subprocess.run(
        [
            sys.executable,
            str(MAIN_PATH),
            "--no-rr",
            "--png",
            str(output_path),
            "--texture-size",
            "256",
            "--warmup-frames",
            "16",
        ],
        check=True,
        timeout=300,
    )

    assert (tmp_path / "projector-opencv-direction.exr").is_file()
    with Image.open(output_path) as image:
        assert image.size == (1024, 560)
        pixels = np.asarray(image)

    left = pixels[48:, :512, :3]
    right = pixels[48:, 512:, :3]
    assert np.any(left)
    assert np.any(right)
    difference = left.astype(np.float32) - right.astype(np.float32)
    rmse = float(np.sqrt(np.mean(difference * difference)))
    assert rmse > 10.0
    assert float(np.mean(right[:80])) > 2.0 * float(np.mean(left[:80]))
