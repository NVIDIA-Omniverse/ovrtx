# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Run the ray-generation Sensor Processing Graph and save its output.

Loads cornell_box_scene.usda, whose SPG node traces the scene itself rather than
post-processing an AOV: one primary ray per pixel, the geometric normal recovered
from two probe rays, and a shadow ray toward the light. This script writes the
render to _output/.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SCENE = SCRIPT_DIR / "cornell_box_scene.usda"
OUTPUT_DIR = SCRIPT_DIR / "_output"
RENDER_PRODUCT = "/Render/CornellBox"
# The RenderVar is addressed by its prim name, which need not match its sourceName.
OUTPUT_VAR_PATH = f"{RENDER_PRODUCT}/Cornell"
WARMUP_STEPS = 5
STEP_DT = 1.0 / 60.0


def main() -> None:
    parser = argparse.ArgumentParser(description="ovrtx SPG ray-generation example")
    parser.add_argument("--scene", type=Path, default=DEFAULT_SCENE, help="USDA scene to load")
    args = parser.parse_args()

    print("Creating renderer...", file=sys.stderr)
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.spg-raygen")
    renderer.attach_ovstage(stage)

    print(f"Loading {args.scene}...", file=sys.stderr)
    ordinal = 1
    ovstage.population.open_usd(stage, str(args.scene), ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    for _ in range(WARMUP_STEPS):
        renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal)
    products = renderer.step(
        render_products={RENDER_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal
    )

    OUTPUT_DIR.mkdir(exist_ok=True)
    frame = products[RENDER_PRODUCT].frames[0]
    # The copy is not optional. np.from_dlpack borrows the mapped buffer, so the
    # array has to own its pixels before the mapping is released.
    mapped = frame.render_vars[OUTPUT_VAR_PATH].map(device=ovrtx.Device.CPU)
    image = np.array(np.from_dlpack(mapped), copy=True)
    del mapped

    path = OUTPUT_DIR / "cornell_box.png"
    Image.fromarray(image[..., :3]).save(path)
    print(f"Saved {OUTPUT_VAR_PATH} -> {path}", file=sys.stderr)

    del frame, products
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


if __name__ == "__main__":
    main()
