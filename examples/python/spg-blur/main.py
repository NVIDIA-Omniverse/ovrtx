# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Run the separable-blur Sensor Processing Graph and check what it produced.

Two chained nodes blur LdrColor, first along x and then along y, with the tap
weights built in the launch script and uploaded once. The radius is a USD
attribute this script rewrites between renders, which is what makes the
checks below exact:

  radius 0  the weight table is {1.0}, so the blur is the identity and the
            published AOV must equal LdrColor byte for byte
  radius 8  the image must be measurably smoother, and no brighter or darker

The weight table is built once per distinct radius rather than once per frame,
which the launch script announces in the renderer log. This script counts those
lines.
"""

import argparse
import contextlib
import os
import re
import sys
import tempfile
from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SCENE = SCRIPT_DIR / "blur_scene.usda"
OUTPUT_DIR = SCRIPT_DIR / "_output"
RENDER_PRODUCT = "/Render/BlurDemo"
LDR_COLOR_PATH = f"{RENDER_PRODUCT}/LdrColor"
HALF_BLURRED_PATH = f"{RENDER_PRODUCT}/LdrBlurH"
BLURRED_PATH = f"{RENDER_PRODUCT}/LdrBlurred"
BLUR_NODES = [f"{RENDER_PRODUCT}/BlurH", f"{RENDER_PRODUCT}/BlurV"]
WARMUP_STEPS = 12
STEP_DT = 1.0 / 60.0

BLUR_RADIUS = 8
WEIGHTS_BUILT = re.compile(r"blur: building the weight table for radius (\d+)")


@contextlib.contextmanager
def captured_log(collected: list):
    """Collect the renderer's log, then replay it.

    The launch script's ``warning`` calls reach the renderer's log, which the
    renderer writes to standard output. Redirecting the file descriptor catches
    what native code writes as well as what Python does, and everything is
    written back out afterwards so nothing is lost.
    """
    with tempfile.TemporaryFile("w+") as sink:
        sys.stdout.flush()
        saved = os.dup(1)
        os.dup2(sink.fileno(), 1)
        try:
            yield
        finally:
            sys.stdout.flush()
            os.dup2(saved, 1)
            os.close(saved)
            sink.seek(0)
            text = sink.read()
            sys.stdout.write(text)
            collected.append(text)


def read_var(frame, render_var_path: str) -> np.ndarray:
    """Map a render var to the CPU and return a copy of its pixels."""
    mapped = frame.render_vars[render_var_path].map(device=ovrtx.Device.CPU)
    return np.from_dlpack(mapped).copy()


def save_png(pixels: np.ndarray, path: Path) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    Image.fromarray(np.ascontiguousarray(pixels)).save(path)
    print(f"Saved {path}")


def sharpest_edge(pixels: np.ndarray) -> int:
    """The largest step between neighbouring pixels, over RGB.

    A blur replaces each pixel with a weighted average of its neighbours, so no
    step can survive it at full height. This is the sharpest silhouette in the
    image, and watching it collapse is the plainest evidence the filter ran.
    """
    rgb = pixels[..., :3].astype(np.int32)
    return int(max(np.abs(np.diff(rgb, axis=1)).max(), np.abs(np.diff(rgb, axis=0)).max()))


# [snippet:blur-write-radius]
def set_radius(stage, ordinal: int, radius: int) -> None:
    """Write inputs:radius on both blur nodes and publish the edit.

    The attribute is connected to nothing, so the value on the prim is the value
    the node reads. Each node is written separately because each carries its own
    copy of the attribute.
    """
    value = np.array([radius], dtype=np.int32)
    tensor = ovstage.make_dltensor(
        value, dtype=ovstage.numpy_to_dldatatype(value.dtype, lanes=1), shape=[1], ndim=1
    )
    with ovstage.PathDictionary(stage) as paths:
        attribute = paths.intern_token("inputs:radius")
        for node in BLUR_NODES:
            path_list = paths.create_path_list_from_strings([node])
            with stage.query_from_path_list(path_list) as query:
                stage.write_attribute(
                    query, attribute, ordinal=ordinal, tensors=tensor, is_array=False
                ).wait()
            paths.destroy_path_list(path_list)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
# [/snippet:blur-write-radius]


def render_at_radius(stage, renderer, ordinal: int, radius: int):
    """Set the radius, let the image settle, and return one frame's render vars."""
    set_radius(stage, ordinal, radius)
    for _ in range(WARMUP_STEPS):
        renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal)
    return renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal)


def main() -> int:
    parser = argparse.ArgumentParser(description="ovrtx SPG separable blur example")
    parser.add_argument("--scene", type=Path, default=DEFAULT_SCENE, help="USDA scene to load")
    args = parser.parse_args()

    failures = []

    log_pages: list = []
    with captured_log(log_pages):
        print(f"Loading {args.scene}...")
        renderer = ovrtx.Renderer()
        stage = ovstage.Stage("ovrtx.example.spg-blur")
        renderer.attach_ovstage(stage)
        ordinal = 1
        ovstage.population.open_usd(stage, str(args.scene), ordinal=ordinal)
        stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

        # Blurred first, then the identity, so both run on a settled image.
        ordinal += 1
        products = render_at_radius(stage, renderer, ordinal, BLUR_RADIUS)
        frame = products[RENDER_PRODUCT].frames[0]
        source = read_var(frame, LDR_COLOR_PATH)
        half_blurred = read_var(frame, HALF_BLURRED_PATH)
        blurred = read_var(frame, BLURRED_PATH)
        del frame, products

        # [snippet:blur-runtime-radius]
        # inputs:radius is unconnected, so a write takes effect on the next step
        # with no reset. At 0 the weight table is {1.0} and the blur is exactly
        # the identity, which makes the comparison below byte-exact.
        ordinal += 1
        products = render_at_radius(stage, renderer, ordinal, 0)
        frame = products[RENDER_PRODUCT].frames[0]
        identity_source = read_var(frame, LDR_COLOR_PATH)
        identity = read_var(frame, BLURRED_PATH)
        del frame, products
        # [/snippet:blur-runtime-radius]

        renderer.detach_ovstage()
        stage.destroy()
        renderer.destroy()

    log_text = "".join(log_pages)

    save_png(source, OUTPUT_DIR / "input.png")
    save_png(half_blurred, OUTPUT_DIR / "blurred-one-pass.png")
    save_png(blurred, OUTPUT_DIR / "blurred.png")

    print()

    # The identity pass: every byte has to survive two nodes and two uploads.
    differing = int(np.count_nonzero(np.any(identity != identity_source, axis=-1)))
    print(f"radius 0, pixels differing from the input: {differing}")
    if differing:
        failures.append(f"radius 0 must be the identity, but {differing} pixels differ")

    # The blur pass: softer edges, and neither brighter nor darker.
    before = sharpest_edge(source)
    after = sharpest_edge(blurred)
    print(f"radius {BLUR_RADIUS}, sharpest edge: {before} -> {after}")
    if after * 2 > before:
        failures.append(
            f"radius {BLUR_RADIUS} barely softened the image: the sharpest edge went {before} -> {after}"
        )

    # The fan-out: BlurH feeds BlurV and a RenderVar of its own, so the
    # half-finished blur is readable and is neither of the other two.
    blurred_one_way = sharpest_edge(half_blurred)
    print(f"radius {BLUR_RADIUS}, sharpest edge after one pass: {blurred_one_way}")
    if not before > blurred_one_way > after:
        failures.append(
            f"the horizontal-only output should sit between the input and the final result, "
            f"but the three sharpest edges are {before}, {blurred_one_way}, {after}"
        )

    drift = abs(float(source[..., :3].mean()) - float(blurred[..., :3].mean()))
    print(f"radius {BLUR_RADIUS}, mean brightness drift: {drift:.3f}")
    if drift > 1.0:
        failures.append(f"the weights are not normalised: brightness moved by {drift:.3f}")

    # The cache: one line per distinct radius, not one per rendered frame.
    radii_built = WEIGHTS_BUILT.findall(log_text)
    print(f"weight tables built: {len(radii_built)} (radii {', '.join(radii_built) or 'none'})")
    if sorted(set(radii_built)) != sorted({str(BLUR_RADIUS), "0"}):
        failures.append(f"expected the table built for radius {BLUR_RADIUS} and 0, got {radii_built}")
    if len(radii_built) != 2:
        failures.append(
            f"expected 2 weight tables over the run, one per radius, got {len(radii_built)}: "
            "the cache key is changing when it should not"
        )

    print()
    for failure in failures:
        print(f"FAILED: {failure}", file=sys.stderr)
    if failures:
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
