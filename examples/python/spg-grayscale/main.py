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
import ovstage
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SCENE = SCRIPT_DIR / "grayscale_scene.usda"
OUTPUT_DIR = SCRIPT_DIR / "_output"
RENDER_PRODUCT = "/Render/GrayscaleDemo"
LDR_COLOR_PATH = f"{RENDER_PRODUCT}/LdrColor"
OUTPUT_VAR_PATH = f"{RENDER_PRODUCT}/LdrGrayscale"
WARMUP_STEPS = 5
STEP_DT = 1.0 / 60.0


def save_render_var(frame, render_var_path: str, path: Path) -> None:
    """Map a render var to the CPU and save it as a PNG."""
    mapped = frame.render_vars[render_var_path].map(device=ovrtx.Device.CPU)
    pixels = np.from_dlpack(mapped)
    Image.fromarray(np.ascontiguousarray(pixels)).save(path)
    print(f"Saved {render_var_path} -> {path}", file=sys.stderr)


def is_grey(frame, render_var_path: str) -> bool:
    """True when every pixel of that render var has R == G == B."""
    mapped = frame.render_vars[render_var_path].map(device=ovrtx.Device.CPU)
    pixels = np.array(np.from_dlpack(mapped), copy=True)
    del mapped
    return bool(np.array_equal(pixels[..., 0], pixels[..., 1])
                and np.array_equal(pixels[..., 1], pixels[..., 2]))


def check(frame) -> list[str]:
    """Check the invariant only this node's output can satisfy.

    R == G == B in every pixel is what grayscale means, and the renderer's own
    LdrColor does not satisfy it. Testing the input as well is what makes the
    first test worth anything: on a scene that was already grey, a node that
    never ran would pass.
    """
    failures = []
    if not is_grey(frame, OUTPUT_VAR_PATH):
        failures.append(
            f"{OUTPUT_VAR_PATH} is not grey: R, G and B differ, so the node did not run "
            "and this AOV is the renderer's own output under that name"
        )
    if is_grey(frame, LDR_COLOR_PATH):
        failures.append(
            f"{LDR_COLOR_PATH} is already grey, so the check above proves nothing about the node"
        )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="ovrtx SPG grayscale example")
    parser.add_argument("--scene", type=Path, default=DEFAULT_SCENE, help="USDA scene to load")
    args = parser.parse_args()

    # [snippet:spg-create-renderer]
    # SPG is enabled by default. The first step compiles the CUDA kernel with
    # NVRTC, which can take up to a minute on a fresh shader cache.
    print("Creating renderer...", file=sys.stderr)
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.spg-grayscale")
    renderer.attach_ovstage(stage)
    # [/snippet:spg-create-renderer]

    # [snippet:spg-open-scene]
    print(f"Loading {args.scene}...", file=sys.stderr)
    ordinal = 1
    ovstage.population.open_usd(stage, str(args.scene), ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    # [/snippet:spg-open-scene]

    # [snippet:spg-warmup-and-step]
    # Warm up so the kernel is compiled and the image has converged, then render.
    for _ in range(WARMUP_STEPS):
        renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal)
    products = renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal)
    # [/snippet:spg-warmup-and-step]

    # [snippet:spg-read-output-aov]
    # An SPG output AOV is read exactly like any built-in render var.
    OUTPUT_DIR.mkdir(exist_ok=True)
    frame = products[RENDER_PRODUCT].frames[0]
    save_render_var(frame, LDR_COLOR_PATH, OUTPUT_DIR / "input.png")
    save_render_var(frame, OUTPUT_VAR_PATH, OUTPUT_DIR / "grayscale.png")

    # [omit]
    failures = check(frame)
    # [/omit]

    del frame, products
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()
    # [/snippet:spg-read-output-aov]

    for failure in failures:
        print(f"FAILED: {failure}", file=sys.stderr)
    if failures:
        return 1
    print("All checks passed.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
