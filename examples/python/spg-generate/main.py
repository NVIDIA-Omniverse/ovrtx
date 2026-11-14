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

Loads checker_scene.usda, whose SPG node reads no AOV: every value it needs
arrives as a typed USD attribute. It writes a
checkerboard into its own output, which the scene publishes as an AOV, and
this script saves that image to _output/.
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


def main() -> None:
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

    path = OUTPUT_DIR / "checker.png"
    Image.fromarray(pixels[..., :3]).save(path)
    print(f"Saved {OUTPUT_VAR_PATH} -> {path}", file=sys.stderr)

    del frame, products
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


if __name__ == "__main__":
    main()
