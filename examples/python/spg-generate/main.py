# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Run the generating Sensor Processing Graph and save its output.

Loads checker_scene.usda, whose SPG node has no resource-input at all: it reads
no AOV, and every value it needs arrives as a typed USD attribute. It writes a
checkerboard into its own output, which the scene publishes as an AOV.

This script saves that image and then checks it, by rebuilding the same
checkerboard on the host from the attributes the scene authored and comparing
the two pixel for pixel.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SCENE = SCRIPT_DIR / "checker_scene.usda"
OUTPUT_DIR = SCRIPT_DIR / "_output"
RENDER_PRODUCT = "/Render/CheckerDemo"
OUTPUT_VAR_PATH = f"{RENDER_PRODUCT}/Checker"
WARMUP_STEPS = 3
STEP_DT = 1.0 / 60.0

# These must match the attributes authored in the scene, because the check below
# rebuilds the same pattern from them.
SQUARE_SIZE = 64
COLOR_A = (1.0, 1.0, 1.0)
COLOR_B = (0.0, 0.0, 0.2)


def expected_checker(height: int, width: int) -> np.ndarray:
    """The image the node should have produced, computed on the host."""
    ys, xs = np.mgrid[0:height, 0:width]
    on_a = (((xs // SQUARE_SIZE) + (ys // SQUARE_SIZE)) % 2) == 0
    # Rounded, not truncated: a uchar4 texture written from a float goes through
    # a unorm conversion on the GPU, and that rounds.
    a = np.array([int(c * 255.0 + 0.5) for c in COLOR_A], dtype=np.uint8)
    b = np.array([int(c * 255.0 + 0.5) for c in COLOR_B], dtype=np.uint8)
    return np.where(on_a[..., None], a, b)


def main() -> int:
    parser = argparse.ArgumentParser(description="ovrtx SPG generating-node example")
    parser.add_argument("--scene", type=Path, default=DEFAULT_SCENE, help="USDA scene to load")
    args = parser.parse_args()

    # [snippet:generate-run]
    print("Creating renderer...", file=sys.stderr)
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.spg-generate")
    renderer.attach_ovstage(stage)

    print(f"Loading {args.scene}...", file=sys.stderr)
    ordinal = 1
    ovstage.population.open_usd(stage, str(args.scene), ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    for _ in range(WARMUP_STEPS):
        renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal)
    products = renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal)
    # [/snippet:generate-run]

    OUTPUT_DIR.mkdir(exist_ok=True)
    frame = products[RENDER_PRODUCT].frames[0]
    mapped = frame.render_vars[OUTPUT_VAR_PATH].map(device=ovrtx.Device.CPU)
    pixels = np.ascontiguousarray(np.from_dlpack(mapped))

    # [snippet:generate-check]
    # Rebuild the same checkerboard on the host from the authored attributes and
    # compare it pixel for pixel. The pattern is exact, so any difference at all
    # means a value did not reach the GPU or the launch did not cover the output.
    height, width = pixels.shape[0], pixels.shape[1]
    expected = expected_checker(height, width)
    mismatched = int(np.count_nonzero(np.any(pixels[..., :3] != expected, axis=-1)))
    print(f"output {width}x{height}, {SQUARE_SIZE}px squares", file=sys.stderr)
    print(f"pixels differing from the host-computed pattern: {mismatched}", file=sys.stderr)
    failures = []
    if mismatched:
        failures.append("the node's output does not match what its attributes describe")
    # [/snippet:generate-check]

    path = OUTPUT_DIR / "checker.png"
    Image.fromarray(pixels[..., :3]).save(path)
    print(f"Saved {OUTPUT_VAR_PATH} -> {path}", file=sys.stderr)

    del frame, products
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
