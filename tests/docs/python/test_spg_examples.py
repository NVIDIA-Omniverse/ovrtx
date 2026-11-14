# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Run each public SPG example as shipped and check the images it saved."""

import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

EXAMPLES = Path(__file__).parents[3] / "examples/python"
# The first step compiles the example's kernels, which can take up to 5 minutes on a cold cache.
TIMEOUT_SECONDS = 900
SPG_MESSAGE = re.compile(r"\[(Info|Warning|Error|Fatal)\] \[rtx\.spg")


def run_example(name: str, scene: Path | str, output_dir: Path) -> Path:
    """Run an example on one scene and return the folder it saved its images to.

    The run uses its own copy of the example, so no other run of the example can overwrite its
    images. The run has to succeed and print no SPG message.
    """
    run = f"{name}.{Path(scene).stem}"
    example = output_dir / run
    shutil.rmtree(example, ignore_errors=True)
    shutil.copytree(EXAMPLES / name, example, ignore=shutil.ignore_patterns("_output", ".venv", "__pycache__"))
    log_path = output_dir / f"{run}.log"
    with log_path.open("w", encoding="utf-8") as log:
        subprocess.run(
            [sys.executable, str(example / "main.py"), "--scene", str(example / scene)],
            cwd=example,
            check=True,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=TIMEOUT_SECONDS,
        )
    messages = [line for line in log_path.read_text(encoding="utf-8").splitlines() if SPG_MESSAGE.search(line)]
    assert not messages, f"{name} printed SPG messages:\n" + "\n".join(messages)
    return example / "_output"


def read_png(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image).astype(np.int32)


def is_grey(pixels: np.ndarray) -> bool:
    return bool(np.array_equal(pixels[..., 0], pixels[..., 1]) and np.array_equal(pixels[..., 1], pixels[..., 2]))


def luminance(pixels: np.ndarray) -> np.ndarray:
    """The grey level the example kernels write, with the BT.601 weights they use."""
    value = 0.299 * pixels[..., 0] + 0.587 * pixels[..., 1] + 0.114 * pixels[..., 2]
    return np.clip(value, 0.0, 255.0).astype(np.uint8).astype(np.int32)


def sharpest_edge(pixels: np.ndarray) -> int:
    """The largest step between neighbouring pixels, over RGB."""
    rgb = pixels[..., :3]
    return int(max(np.abs(np.diff(rgb, axis=1)).max(), np.abs(np.diff(rgb, axis=0)).max()))


@pytest.mark.parametrize("scene", ["grayscale_scene.usda", "grayscale_scene_slang.usda"])
def test_grayscale_example_publishes_the_luminance_of_the_colour_image(scene, output_dir):
    saved = run_example("spg-grayscale", scene, output_dir)
    colour = read_png(saved / "input.png")
    grey = read_png(saved / "grayscale.png")
    assert not is_grey(colour), "The scene must render in colour, or a node that never ran would pass."
    assert is_grey(grey)
    assert np.abs(grey[..., 0] - luminance(colour)).max() <= 1


@pytest.mark.parametrize("scene", ["pipeline_scene.usda", "pipeline_scene_slang.usda"])
def test_pipeline_example_publishes_the_inverted_luminance(scene, output_dir):
    saved = run_example("spg-pipeline", scene, output_dir)
    colour = read_png(saved / "input.png")
    result = read_png(saved / "inverted_grayscale.png")
    assert is_grey(result), "The grayscale node did not run."
    assert np.abs(result[..., 0] - (255 - luminance(colour))).max() <= 1, (
        "The invert node did not run, or the two nodes ran in the wrong order."
    )


@pytest.mark.parametrize("scene", ["checker_scene.usda", "checker_scene_slang.usda"])
def test_generate_example_draws_the_authored_checkerboard(scene, output_dir):
    # inputs:squareSize as the scenes author it, and the shader definitions' colours.
    square_size = 64
    colour_a = (255, 255, 255)
    colour_b = (0, 0, 51)

    saved = run_example("spg-generate", scene, output_dir)
    pixels = read_png(saved / "checker.png")[..., :3]
    rows, columns = np.mgrid[0 : pixels.shape[0], 0 : pixels.shape[1]]
    on_a = ((rows // square_size + columns // square_size) % 2) == 0
    expected = np.where(on_a[..., None], colour_a, colour_b)
    assert np.array_equal(pixels, expected)


def test_builtin_nodes_example_adds_then_halves_the_colour_image(output_dir):
    # inputs:scaleX and inputs:scaleY as stdlib_scene.usda authors them.
    scale = 0.5

    saved = run_example("spg-builtin-nodes", "stdlib_scene.usda", output_dir)
    colour = read_png(saved / "input.png")
    result = read_png(saved / "downscaled.png")
    height, width = colour.shape[0], colour.shape[1]
    assert result.shape[:2] == (int(height * scale), int(width * scale)), "The Scale node did not run."
    # Add saturates on uint8, and Scale takes the source pixel under each destination pixel's centre.
    rows = np.clip(((np.arange(result.shape[0]) + 0.5) / scale).astype(int), 0, height - 1)
    columns = np.clip(((np.arange(result.shape[1]) + 0.5) / scale).astype(int), 0, width - 1)
    expected = np.minimum(2 * colour, 255)[np.ix_(rows, columns)]
    assert np.array_equal(result[..., :3], expected[..., :3]), "The Add node did not run, or ran after Scale."


@pytest.mark.parametrize("scene", ["motion_scene.usda", "motion_scene_slang.usda"])
def test_previous_frame_example_lights_up_only_while_the_ball_moves(scene, output_dir):
    changed_level = 24

    saved = run_example("spg-previous-frame", scene, output_dir)
    moving = int((read_png(saved / "motion-moving.png")[..., 0] > changed_level).sum())
    still = int((read_png(saved / "motion-still.png")[..., 0] > changed_level).sum())
    assert moving > 0, "The second input is the live image, not the previous frame."
    assert still * 8 <= moving, f"Holding still has to quiet the difference: {moving} moving, {still} still."


@pytest.mark.parametrize("scene", ["trail_scene.usda", "trail_scene_slang.usda"])
def test_stateful_example_draws_a_tail_behind_the_ball(scene, output_dir):
    lit_level = 40

    saved = run_example("spg-stateful", scene, output_dir)
    live = read_png(saved / "live.png")[..., :3]
    trail = read_png(saved / "trail.png")[..., :3]
    backdrop = int(np.median(live))
    assert abs(int(np.median(trail)) - backdrop) <= 2, "The backdrop has to read at the same level in both images."
    ball = (live.max(axis=-1) > backdrop + lit_level)
    tail = (trail.max(axis=-1) > backdrop + lit_level) & ~ball
    assert ball.sum() > 0
    assert tail.sum() > 4 * ball.sum(), f"The tail covers {tail.sum()} pixels against a ball of {ball.sum()}."


@pytest.mark.parametrize("scene", ["overlay_scene.usda", "overlay_scene_slang.usda"])
def test_scene_query_example_draws_crosshairs_over_the_colour_image(scene, output_dir):
    saved = run_example("spg-scene-query", scene, output_dir)
    colour = read_png(saved / "color.png")[..., :3]
    overlay = read_png(saved / "overlay.png")[..., :3]
    changed = np.any(overlay != colour, axis=-1)
    assert changed.sum() > 0, "No crosshair was drawn."
    assert np.all(overlay[changed] == 255), "Only white crosshair pixels may differ from the colour image."
    assert changed.mean() < 0.05


@pytest.mark.parametrize("scene", ["cornell_box_scene.usda", "cornell_box_pipeline_scene.usda"])
def test_raygen_example_traces_the_room(scene, output_dir):
    saved = run_example("spg-raygen", scene, output_dir)
    image = read_png(saved / "cornell_box.png")[..., :3]
    assert image.any(), "The traced image is empty."


@pytest.mark.parametrize("scene", ["lidar_scene.usda", "lidar_scene_slang.usda"])
def test_composite_aov_example_charts_one_bar_per_box(scene, output_dir):
    # The chart the node draws, as RangeHistogramKernel.usda authors it, and where the example places
    # it on the annotated figure.
    num_bins, max_range = 32, 12.8
    width, height = 512, 256
    left, top = 78, 56
    bar_rgb = (90, 170, 255)
    # The lidar returns from each box's front face, which lidar_scene.usda places at these ranges.
    face_distances = (5.25, 10.5)

    saved = run_example("spg-composite-aov", scene, output_dir)
    chart = read_png(saved / "histogram.png")[top : top + height, left : left + width, :3]
    bar = np.all(chart == bar_rgb, axis=-1)
    columns_per_bin = width // num_bins
    heights = np.array([int(bar[:, b * columns_per_bin].sum()) for b in range(num_bins)])
    filled = np.flatnonzero(heights)
    groups = np.split(filled, np.flatnonzero(np.diff(filled) > 1) + 1) if filled.size else []
    assert len(groups) == len(face_distances), f"Expected one bar per box, got bins {filled.tolist()}."
    bin_width = max_range / num_bins
    for group, distance in zip(groups, face_distances):
        near, far = group[0] * bin_width, (group[-1] + 1) * bin_width
        assert near - bin_width <= distance <= far + bin_width, (
            f"The bar for the face at {distance} m spans {near:.1f} to {far:.1f} m."
        )
        assert heights[group].max() > height // 4, f"The bar for the face at {distance} m is barely filled."


@pytest.mark.parametrize("scene", ["blur_scene.usda", "blur_scene_slang.usda"])
def test_blur_example_softens_the_image_in_two_passes(scene, output_dir):
    saved = run_example("spg-blur", scene, output_dir)
    source = read_png(saved / "input.png")
    one_pass = read_png(saved / "blurred-one-pass.png")
    blurred = read_png(saved / "blurred.png")
    before, between, after = sharpest_edge(source), sharpest_edge(one_pass), sharpest_edge(blurred)
    assert before > between > after, f"The sharpest edges are {before}, {between} and {after}."
    assert after * 2 <= before, "The blur barely softened the image."
    drift = abs(float(source[..., :3].mean()) - float(blurred[..., :3].mean()))
    assert drift <= 1.0, f"The blur changed the brightness by {drift:.3f}: its weights are not normalised."
    # Writing radius 0 at runtime makes both passes the identity on the next steps.
    assert np.array_equal(read_png(saved / "radius-0.png"), read_png(saved / "radius-0-input.png")), (
        "At radius 0 the published AOV has to equal that frame's LdrColor pixel for pixel."
    )
