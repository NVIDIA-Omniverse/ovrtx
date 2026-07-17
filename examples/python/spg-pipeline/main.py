# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Run a two-shader SPG pipeline (grayscale -> invert) and save the result.

pipeline_scene.usda chains GrayscaleKernel into InvertKernel by connecting one
shader's output directly to the next shader's input. Only the final result is
published as the LdrInverted AOV.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import ovrtx
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SCENE = SCRIPT_DIR / "pipeline_scene.usda"
OUTPUT_DIR = SCRIPT_DIR / "_output"
RENDER_PRODUCT = "/Render/PipelineDemo"
OUTPUT_VAR = "LdrInverted"
WARMUP_STEPS = 5
STEP_DT = 1.0 / 60.0


# [snippet:save-render-var]
def save_render_var(frame, name: str, path: Path) -> None:
    """Map a render var to the CPU and save it as a PNG."""
    mapped = frame.render_vars[name].map(device=ovrtx.Device.CPU)
    pixels = np.from_dlpack(mapped)
    Image.fromarray(np.ascontiguousarray(pixels)).save(path)
    print(f"Saved {name} -> {path}", file=sys.stderr)
# [/snippet:save-render-var]


# [snippet:run-spg-pipeline]
def main() -> None:
    parser = argparse.ArgumentParser(description="ovrtx SPG pipeline (grayscale -> invert) example")
    parser.add_argument("--scene", type=Path, default=DEFAULT_SCENE, help="USDA scene to load")
    args = parser.parse_args()

    # SPG is enabled by default. The first step compiles both CUDA kernels with
    # NVRTC, which can take up to a minute on a fresh shader cache.
    print("Creating renderer...", file=sys.stderr)
    renderer = ovrtx.Renderer()

    print(f"Loading {args.scene}...", file=sys.stderr)
    renderer.open_usd(str(args.scene))

    # Warm up so both kernels are compiled and the image has converged.
    for _ in range(WARMUP_STEPS):
        renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT)
    products = renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT)

    OUTPUT_DIR.mkdir(exist_ok=True)
    frame = products[RENDER_PRODUCT].frames[0]
    save_render_var(frame, "LdrColor", OUTPUT_DIR / "input.png")
    save_render_var(frame, OUTPUT_VAR, OUTPUT_DIR / "inverted_grayscale.png")
# [/snippet:run-spg-pipeline]


if __name__ == "__main__":
    main()
