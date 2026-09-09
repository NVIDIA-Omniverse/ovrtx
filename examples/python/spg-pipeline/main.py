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
import ovstage
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SCENE = SCRIPT_DIR / "pipeline_scene.usda"
OUTPUT_DIR = SCRIPT_DIR / "_output"
RENDER_PRODUCT = "/Render/PipelineDemo"
LDR_COLOR_PATH = f"{RENDER_PRODUCT}/LdrColor"
OUTPUT_VAR_PATH = f"{RENDER_PRODUCT}/LdrInverted"
WARMUP_STEPS = 5
STEP_DT = 1.0 / 60.0


# [snippet:save-render-var]
def save_render_var(frame, render_var_path: str, path: Path) -> None:
    """Map a render var to the CPU and save it as a PNG."""
    mapped = frame.render_vars[render_var_path].map(device=ovrtx.Device.CPU)
    pixels = np.from_dlpack(mapped)
    Image.fromarray(np.ascontiguousarray(pixels)).save(path)
    print(f"Saved {render_var_path} -> {path}", file=sys.stderr)
# [/snippet:save-render-var]


def read_render_var(frame, render_var_path: str) -> np.ndarray:
    """Map a render var to the CPU and return a copy of its pixels."""
    mapped = frame.render_vars[render_var_path].map(device=ovrtx.Device.CPU)
    pixels = np.array(np.from_dlpack(mapped), copy=True)
    del mapped
    return pixels


def check(frame) -> list[str]:
    """Check that both nodes in the chain ran, and in the right order.

    The intermediate grayscale image is never published, so it is recomputed
    here from the input with the kernel's own BT.601 weights. Inverting that at
    full strength is exactly ``255 - grey``, so the final AOV is predictable to
    the byte. Grey but not inverted means the second node did not run; inverted
    but still coloured means the first did not.
    """
    colour = read_render_var(frame, LDR_COLOR_PATH).astype(np.int32)
    result = read_render_var(frame, OUTPUT_VAR_PATH).astype(np.int32)

    failures = []
    grey = np.array_equal(result[..., 0], result[..., 1]) and np.array_equal(
        result[..., 1], result[..., 2]
    )
    if not grey:
        failures.append("the output is not grey: the grayscale node did not run")

    luminance = 0.299 * colour[..., 0] + 0.587 * colour[..., 1] + 0.114 * colour[..., 2]
    expected = 255 - np.clip(luminance, 0.0, 255.0).astype(np.uint8).astype(np.int32)
    worst = int(np.abs(result[..., 0] - expected).max())
    print(f"largest difference from 255 - grey(input): {worst}", file=sys.stderr)
    if worst > 1:
        failures.append(
            "the output is not the inverse of the input's luminance: the invert node did not "
            "run, or the two nodes ran in the wrong order"
        )
    return failures


# [snippet:run-spg-pipeline]
def main() -> int:
    parser = argparse.ArgumentParser(description="ovrtx SPG pipeline (grayscale -> invert) example")
    parser.add_argument("--scene", type=Path, default=DEFAULT_SCENE, help="USDA scene to load")
    args = parser.parse_args()

    # SPG is enabled by default. The first step compiles both CUDA kernels with
    # NVRTC, which can take up to a minute on a fresh shader cache.
    print("Creating renderer...", file=sys.stderr)
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.spg-pipeline")
    renderer.attach_ovstage(stage)

    print(f"Loading {args.scene}...", file=sys.stderr)
    ordinal = 1
    ovstage.population.open_usd(stage, str(args.scene), ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    # Warm up so both kernels are compiled and the image has converged.
    for _ in range(WARMUP_STEPS):
        renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal)
    products = renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal)

    OUTPUT_DIR.mkdir(exist_ok=True)
    frame = products[RENDER_PRODUCT].frames[0]
    save_render_var(frame, LDR_COLOR_PATH, OUTPUT_DIR / "input.png")
    save_render_var(frame, OUTPUT_VAR_PATH, OUTPUT_DIR / "inverted_grayscale.png")

    failures = check(frame)

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
# [/snippet:run-spg-pipeline]


if __name__ == "__main__":
    sys.exit(main())
