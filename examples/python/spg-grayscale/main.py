# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Run the grayscale Sensor Processing Graph and save its output AOV.

Loads grayscale_scene.usda, which renders a simple scene and runs the
GrayscaleKernel SPG shader over the LdrColor AOV, then writes the input and
the SPG output to _output/.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import ovrtx
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SCENE = SCRIPT_DIR / "grayscale_scene.usda"
OUTPUT_DIR = SCRIPT_DIR / "_output"
RENDER_PRODUCT = "/Render/GrayscaleDemo"
# The SPG output AOV produced by GrayscaleKernel (see grayscale_scene.usda).
OUTPUT_VAR = "LdrGrayscale"
WARMUP_STEPS = 5
STEP_DT = 1.0 / 60.0


def save_render_var(frame, name: str, path: Path) -> None:
    """Map a render var to the CPU and save it as a PNG."""
    mapped = frame.render_vars[name].map(device=ovrtx.Device.CPU)
    pixels = np.from_dlpack(mapped)
    Image.fromarray(np.ascontiguousarray(pixels)).save(path)
    print(f"Saved {name} -> {path}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="ovrtx SPG grayscale example")
    parser.add_argument("--scene", type=Path, default=DEFAULT_SCENE, help="USDA scene to load")
    args = parser.parse_args()

    # [snippet:spg-create-renderer]
    # SPG is enabled by default. The first step compiles the CUDA kernel with
    # NVRTC, which can take up to a minute on a fresh shader cache.
    print("Creating renderer...", file=sys.stderr)
    renderer = ovrtx.Renderer()
    # [/snippet:spg-create-renderer]

    # [snippet:spg-open-scene]
    print(f"Loading {args.scene}...", file=sys.stderr)
    renderer.open_usd(str(args.scene))
    # [/snippet:spg-open-scene]

    # [snippet:spg-warmup-and-step]
    # Warm up so the kernel is compiled and the image has converged, then render.
    for _ in range(WARMUP_STEPS):
        renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT)
    products = renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT)
    # [/snippet:spg-warmup-and-step]

    # [snippet:spg-read-output-aov]
    # An SPG output AOV is read exactly like any built-in render var.
    OUTPUT_DIR.mkdir(exist_ok=True)
    frame = products[RENDER_PRODUCT].frames[0]
    save_render_var(frame, "LdrColor", OUTPUT_DIR / "input.png")
    save_render_var(frame, OUTPUT_VAR, OUTPUT_DIR / "grayscale.png")
    # [/snippet:spg-read-output-aov]


if __name__ == "__main__":
    main()
