# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Render the public Minimal DLSS example through the local docs-test runtime.

The shipped example scene references the robot lineup, whose remote payloads do not
load in GitHub CI (see test_camera_feature_examples.py). These tests therefore pass
the example's ``--usd`` override with a local scene that keeps the same RenderProduct.
"""

import json
import os
import subprocess
import sys
from functools import cache
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

EXAMPLE = Path(__file__).resolve().parents[3] / "examples/python/minimal-dlss/main.py"
TEST_SCENE = Path(__file__).resolve().parents[1] / "data" / "minimal_dlss_test_scene.usda"


@pytest.fixture(scope="session")
def render_minimal_dlss(output_dir):
    """Render each configuration once per session, or once per worker under xdist."""
    worker_id = os.environ.get("PYTEST_XDIST_WORKER")
    render_dir = output_dir / worker_id if worker_id else output_dir
    render_dir.mkdir(exist_ok=True)

    @cache
    def render(mode: int, preset: str, repeat: int = 0) -> Path:
        output = render_dir / f"minimal_dlss.mode-{mode}-{preset}-{repeat}.png"
        output.unlink(missing_ok=True)
        subprocess.run(
            [
                sys.executable,
                str(EXAMPLE),
                "--usd",
                str(TEST_SCENE),
                "--dlss-mode",
                str(mode),
                "--exec-mode",
                preset,
                "--frames",
                "32",
                "--no-rr",
                "--png",
                str(output),
                "--log",
                str(output.with_suffix(".log")),
            ],
            check=True,
            timeout=600,
        )
        return output

    return render


@pytest.mark.parametrize("mode,preset", [(0, "quality"), (1, "quality"), (2, "quality"), (1, "rtxaa")])
def test_minimal_dlss_example_output(mode, preset, render_minimal_dlss):
    with Image.open(render_minimal_dlss(mode, preset)) as image:
        assert image.size == (1280, 720)
        pixels = np.asarray(image)[..., :3]
    assert pixels.std() > 5, "Expected visible geometry and texture detail"


@pytest.mark.parametrize("preset", ["quality", "rtxaa"])
def test_minimal_sr_differs_from_disabled(preset, render_minimal_dlss):
    images = []
    for mode, mode_preset in [(0, "quality"), (1, preset)]:
        with Image.open(render_minimal_dlss(mode, mode_preset)) as image:
            images.append(np.asarray(image)[..., :3].astype(np.float32))
    # Check Quality independently of DLAA: either setting can regress alone.
    difference = np.abs(images[0] - images[1]).mean()
    assert difference > 0.1, f"SR {preset} matches disabled DLSS (mean difference {difference:.4f}/255)"


def test_minimal_sr_quality_differs_from_native_dlaa(render_minimal_dlss):
    images = []
    for preset, repeat in [("quality", 0), ("rtxaa", 0), ("rtxaa", 1)]:
        with Image.open(render_minimal_dlss(1, preset, repeat)) as image:
            images.append(np.asarray(image)[..., :3].astype(np.float32))
    quality_difference = np.abs(images[0] - images[1]).mean()
    repeat_difference = np.abs(images[1] - images[2]).mean()
    # Native DLAA is the negative control for a silently ignored Quality preset.
    # The effect must exceed both quantization noise and measured run-to-run drift.
    minimum_difference = max(0.1, 5.0 * repeat_difference)
    assert quality_difference > minimum_difference, (
        f"Quality matches native DLAA: difference {quality_difference:.4f}/255, "
        f"required > {minimum_difference:.4f}/255 (repeat drift {repeat_difference:.4f}/255)"
    )


def test_minimal_sr_quality_matches_reference(render_minimal_dlss):
    # SR Quality render of minimal_dlss_test_scene.usda after 32 frames, captured with
    # `main.py --usd ... --dlss-mode 1 --exec-mode quality --no-rr --png`. A broken blit
    # path cannot pass merely by differing from both disabled DLSS and native DLAA.
    reference_path = Path(__file__).parents[1] / "data" / "minimal_dlss_sr_quality.png"
    with Image.open(reference_path) as image:
        reference = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    errors = {}
    for name, mode, preset in (("disabled", 0, "quality"), ("sr_quality", 1, "quality"), ("dlaa", 1, "rtxaa")):
        with Image.open(render_minimal_dlss(mode, preset)) as image:
            pixels = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
        errors[name] = float(np.square(pixels - reference).mean())
    metrics_path = render_minimal_dlss(1, "quality").with_name("minimal_dlss.sr-reference-metrics.json")
    metrics_path.write_text(json.dumps(errors, indent=2) + "\n", encoding="utf-8")
    assert errors["sr_quality"] < 0.5 * min(
        errors["disabled"], errors["dlaa"]
    ), f"SR Quality must match its reference more closely than either negative control: {errors}"


def test_minimal_rr_denoises_gaussians(output_dir):
    """RR must denoise stochastic transparency beyond SR at the same Quality preset."""
    worker_id = os.environ.get("PYTEST_XDIST_WORKER")
    render_dir = output_dir / worker_id if worker_id else output_dir
    render_dir.mkdir(exist_ok=True)
    sequences = {}
    for mode in (0, 1, 2):
        output = render_dir / f"minimal_dlss.gaussians-mode-{mode}.npz"
        output.unlink(missing_ok=True)
        subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("capture_minimal_dlss_gaussians.py")),
                str(mode),
                str(output),
            ],
            check=True,
            timeout=600,
        )
        with np.load(output) as data:
            sequences[mode] = data["frames"].astype(np.float32) / 255.0
        assert sequences[mode].shape == (128 if mode == 0 else 32, 480, 640, 3)

    # Independent native-resolution samples estimate the noise-free scene.
    reference = sequences[0].mean(axis=0)
    noise = {mode: float(np.diff(frames, axis=0).var() / 2.0) for mode, frames in sequences.items()}
    error = {mode: float(np.square(frames - reference).mean()) for mode, frames in sequences.items()}
    rr_mean_error = float(np.square(sequences[2].mean(axis=0) - reference).mean())
    reference_variance = float(reference.var())
    metrics = {
        "temporal_noise": noise,
        "reference_mse": error,
        "rr_mean_mse": rr_mean_error,
        "reference_variance": reference_variance,
    }
    (render_dir / "minimal_dlss.gaussians-metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
    )
    assert reference.std() > 0.01, "The Gaussian scene has no visible splats"
    assert noise[0] > 0.0001, f"The control must exercise stochastic transparency: {metrics}"
    # A constant/black output has low temporal noise but loses the splats. Its
    # reference MSE is at least the reference variance, so this bound rejects it.
    assert rr_mean_error < 0.25 * reference_variance, f"RR lost the Gaussian image content: {metrics}"
    # Both controls are essential: substituting SR for RR must fail just as
    # disabling reconstruction does. Bounds are ratios, independent of PNG scale.
    for baseline in (0, 1):
        assert noise[2] < 0.5 * noise[baseline], f"RR did not reduce mode-{baseline} noise: {metrics}"
        assert error[2] < 0.5 * error[baseline], f"RR did not improve mode-{baseline} reference error: {metrics}"
