# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Run the composite-AOV Sensor Processing Graph and save its output.

Loads lidar_scene.usda, whose SPG node consumes the lidar PointCloud composite
AOV: several named channels published together under one render var. The node
counts the sweep's returns by distance and publishes the result as a bar chart.

This script writes that chart to _output/ and then checks it, by computing the
same histogram on the host from the same channels and comparing bar by bar.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SCENE = SCRIPT_DIR / "lidar_scene.usda"
OUTPUT_DIR = SCRIPT_DIR / "_output"
RENDER_PRODUCT = "/Render/LidarProduct"
POINTCLOUD_PATH = f"{RENDER_PRODUCT}/PointCloud"
OUTPUT_VAR_PATH = f"{RENDER_PRODUCT}/Histogram"
# A second product with an ordinary camera, for the reference picture of the
# scene. The lidar product's camera is the sensor, which has no colour output.
SCENE_PRODUCT = "/Render/SceneView"
SCENE_VAR_PATH = f"{SCENE_PRODUCT}/LdrColor"
WARMUP_STEPS = 12
STEP_DT = 0.1

# The chart the node draws. These must match inputs:numBins, inputs:maxRange and
# inputs:maxCount on RangeHistogramKernel.usda, because the check below rebuilds
# the same histogram on the host.
NUM_BINS = 32
MAX_RANGE = 12.8
MAX_COUNT = 15000.0
BAR_RGB = (90, 170, 255)
BACKGROUND_RGB = (18, 18, 22)

# Margins the annotation needs around the node's chart, in pixels.
MARGIN_LEFT, MARGIN_TOP, MARGIN_RIGHT, MARGIN_BOTTOM = 78, 56, 18, 54
INK = (196, 200, 210)
AXIS = (110, 114, 126)


def annotate(chart: np.ndarray, valid: int, furthest: float) -> Image.Image:
    """Draw axes, ticks and labels around the chart the node published.

    This is presentation, not part of the SPG lesson, and it is deliberately on
    the host rather than in the kernel. What the node publishes is the bare
    chart: an AOV is data, and a downstream consumer wants the bars rather than
    a picture of a figure. Turning that into something a person can read is the
    reader's job, and doing it here keeps a font rasteriser out of the node.
    """
    height, width = chart.shape[0], chart.shape[1]
    figure = Image.new(
        "RGB",
        (MARGIN_LEFT + width + MARGIN_RIGHT, MARGIN_TOP + height + MARGIN_BOTTOM),
        BACKGROUND_RGB,
    )
    figure.paste(Image.fromarray(chart[..., :3]), (MARGIN_LEFT, MARGIN_TOP))
    draw = ImageDraw.Draw(figure)
    label_font = ImageFont.load_default(size=13)
    title_font = ImageFont.load_default(size=17)

    left, right = MARGIN_LEFT, MARGIN_LEFT + width
    top, bottom = MARGIN_TOP, MARGIN_TOP + height

    draw.line([(left - 1, top), (left - 1, bottom)], fill=AXIS)
    draw.line([(left - 1, bottom), (right, bottom)], fill=AXIS)

    # Distance across the bottom, in whole metres.
    for metres in range(0, int(MAX_RANGE) + 1, 4):
        x = left + round(metres / MAX_RANGE * width)
        draw.line([(x, bottom), (x, bottom + 5)], fill=AXIS)
        draw.text((x, bottom + 8), str(metres), fill=INK, font=label_font, anchor="ma")

    # Bin population up the side. The node clips bars at maxCount, so the top of
    # the axis is exactly that.
    for count in range(0, int(MAX_COUNT) + 1, 5000):
        y = bottom - round(count / MAX_COUNT * height)
        draw.line([(left - 6, y), (left - 1, y)], fill=AXIS)
        text = "0" if count == 0 else f"{count // 1000}k"
        draw.text((left - 10, y), text, fill=INK, font=label_font, anchor="rm")

    draw.text((left, 10), "Lidar returns by distance", fill=INK, font=title_font)
    draw.text((left, MARGIN_TOP - 18), "returns per bin", fill=AXIS, font=label_font)
    draw.text(
        ((left + right) // 2, bottom + 30),
        "distance from sensor (m)",
        fill=INK,
        font=label_font,
        anchor="ma",
    )
    draw.text(
        (right, 14),
        f"{valid:,} returns   {NUM_BINS} bins   furthest {furthest:.1f} m",
        fill=AXIS,
        font=label_font,
        anchor="ra",
    )
    return figure


def caption(image: np.ndarray, text: str) -> Image.Image:
    """Add a one-line caption under a rendered image."""
    height, width = image.shape[0], image.shape[1]
    strip = 32
    figure = Image.new("RGB", (width, height + strip), BACKGROUND_RGB)
    figure.paste(Image.fromarray(image[..., :3]), (0, 0))
    ImageDraw.Draw(figure).text(
        (width // 2, height + strip // 2),
        text,
        fill=INK,
        font=ImageFont.load_default(size=13),
        anchor="mm",
    )
    return figure


def main() -> int:
    parser = argparse.ArgumentParser(description="ovrtx SPG composite-AOV example")
    parser.add_argument("--scene", type=Path, default=DEFAULT_SCENE, help="USDA scene to load")
    args = parser.parse_args()

    # [snippet:composite-create-renderer]
    # A lidar sweep is traced across the tick, so the sensor returns no points at
    # all unless the motion BVH is built. Without it Counts is zero and the node
    # produces an empty chart rather than an error.
    print("Creating renderer...", file=sys.stderr)
    renderer = ovrtx.Renderer(ovrtx.RendererConfig(motion_bvh=ovrtx.MotionBvh.ENABLE))
    stage = ovstage.Stage("ovrtx.example.spg-composite-aov")
    renderer.attach_ovstage(stage)
    # [/snippet:composite-create-renderer]

    print(f"Loading {args.scene}...", file=sys.stderr)
    ordinal = 1
    ovstage.population.open_usd(stage, str(args.scene), ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    # [snippet:composite-step-both-products]
    # One step fills both products: the lidar sweep and its histogram, and the
    # camera's view of the same scene. The warm-up is for the camera, which is
    # path traced and needs a few steps to settle.
    for _ in range(WARMUP_STEPS):
        renderer.step(
            render_products={RENDER_PRODUCT, SCENE_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal
        )
    products = renderer.step(
        render_products={RENDER_PRODUCT, SCENE_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal
    )
    # [/snippet:composite-step-both-products]

    OUTPUT_DIR.mkdir(exist_ok=True)
    frame = products[RENDER_PRODUCT].frames[0]

    # [snippet:composite-read-channels]
    # The same composite the SPG node consumed is readable from Python, one
    # tensor per channel, keyed by the names the scene asked for on the
    # RenderVar. Counts bounds how much of the other channels is real.
    with frame.render_vars[POINTCLOUD_PATH].map(device=ovrtx.Device.CPU) as pointcloud:
        counts = np.from_dlpack(pointcloud["Counts"])
        coordinates = np.from_dlpack(pointcloud["Coordinates"])
        intensity = np.from_dlpack(pointcloud["Intensity"])
        # Counts holds one number for the whole sweep: how many entries of the
        # other channels were filled. It is buffer metadata rather than a
        # measurement, and bounding iteration is all it is for.
        valid = int(counts[0])
        print(f"channels: {list(pointcloud.keys())}", file=sys.stderr)
        print(f"Coordinates {list(coordinates.shape)}, Counts {list(counts.shape)} = {valid} "
              f"valid points", file=sys.stderr)
        # Coordinates is [3, Nmax]: all x, then all y, then all z. Taking the
        # first `valid` entries of each run is the host-side form of the bound
        # the kernel applies.
        ranges = np.sqrt((coordinates[:, :valid].astype(np.float64) ** 2).sum(axis=0))
        # Intensity is here because the scene asked for it, not because the node
        # uses it: channels are independent, and the host can read any of them.
        # A sweep that returned nothing has no range to report, and asking NumPy
        # for one raises. The check below turns that into a stated failure.
        intensity_span = (f"{intensity[:valid].min():.4f}..{intensity[:valid].max():.4f}"
                          if valid else "no valid points")
        print(f"Intensity {list(intensity.shape)}, {intensity_span} "
              f"(unused by the node)", file=sys.stderr)
    # [/snippet:composite-read-channels]

    mapped = frame.render_vars[OUTPUT_VAR_PATH].map(device=ovrtx.Device.CPU)
    pixels = np.ascontiguousarray(np.from_dlpack(mapped))

    # [snippet:composite-check]
    # Rebuild the node's histogram on the host from the same channels, and
    # compare it bar by bar with the chart the node drew. Reading Coordinates
    # with the wrong stride, or running past Counts into entries the sweep never
    # filled, both still produce a plausible-looking chart, so comparing against
    # an independent count is what would catch either.
    reference, _ = np.histogram(ranges, bins=NUM_BINS, range=(0.0, MAX_RANGE))
    chart_height = pixels.shape[0]
    expected = np.rint(np.minimum(1.0, reference / MAX_COUNT) * chart_height).astype(int)

    bar = np.all(pixels[..., :3] == np.array(BAR_RGB, dtype=np.uint8), axis=-1)
    columns_per_bin = pixels.shape[1] // NUM_BINS
    drawn = np.array([int(bar[:, b * columns_per_bin].sum()) for b in range(NUM_BINS)])
    worst = int(np.abs(drawn - expected).max())

    range_span = f"{ranges.min():.2f}..{ranges.max():.1f} m" if valid else "none"
    print(f"returns binned: {int(reference.sum())} of {valid}, "
          f"busiest bin {int(reference.max())}, "
          f"returns span {range_span}", file=sys.stderr)
    print(f"bar heights vs an independent count: largest difference {worst} px", file=sys.stderr)
    failures = []
    if worst > 1:
        failures.append("the chart does not match the point cloud it was drawn from")
    if valid == 0:
        failures.append("the sensor returned no points; the chart is empty")
    # [/snippet:composite-check]

    # The check above reads the bars the node published. Only now are axes and
    # labels drawn around them, so nothing measured is measured off an annotated
    # figure.
    path = OUTPUT_DIR / "histogram.png"
    annotate(pixels, valid, float(ranges.max()) if valid else 0.0).save(path)
    print(f"Saved {OUTPUT_VAR_PATH} -> {path}", file=sys.stderr)

    # The reference picture: the same scene, from an ordinary camera.
    scene_frame = products[SCENE_PRODUCT].frames[0]
    scene_mapped = scene_frame.render_vars[SCENE_VAR_PATH].map(device=ovrtx.Device.CPU)
    # Copied while the mapping is still held: the picture is drawn on further down.
    scene = np.array(np.from_dlpack(scene_mapped), copy=True)
    del scene_mapped
    scene_path = OUTPUT_DIR / "scene.png"
    caption(
        scene,
        "the lidar is the orange post; grey box at 6 m, tan box at 12 m and twice as wide",
    ).save(scene_path)
    print(f"Saved {SCENE_VAR_PATH} -> {scene_path}", file=sys.stderr)

    del frame, scene_frame, products
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()

    for failure in failures:
        print(f"FAILED: {failure}", file=sys.stderr)
    if failures:
        return 1
    print("All checks passed.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
