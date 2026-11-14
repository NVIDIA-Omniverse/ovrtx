# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Run built-in SPG factory nodes (stdlib Add + Scale) and save the output AOV.

stdlib_scene.usda chains two built-in nodes addressed by info:id, with no .cu or
.cu.lua of their own. Add brightens the LdrColor AOV by adding it to itself, then
Scale downscales that result to half resolution and publishes it as Downscaled.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SCENE = SCRIPT_DIR / "stdlib_scene.usda"
OUTPUT_DIR = SCRIPT_DIR / "_output"
RENDER_PRODUCT = "/Render/StdlibDemo"
LDR_COLOR_PATH = f"{RENDER_PRODUCT}/LdrColor"
OUTPUT_VAR_PATH = f"{RENDER_PRODUCT}/Downscaled"
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


# [snippet:run-spg-builtin-nodes]
def main() -> None:
    parser = argparse.ArgumentParser(description="ovrtx SPG built-in (Add + Scale) node example")
    parser.add_argument("--scene", type=Path, default=DEFAULT_SCENE, help="USDA scene to load")
    args = parser.parse_args()

    # Built-in factory nodes are resolved by the renderer; no NVRTC compilation
    # is needed for this scene.
    print("Creating renderer...", file=sys.stderr)
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.spg-builtin-nodes")
    renderer.attach_ovstage(stage)

    print(f"Loading {args.scene}...", file=sys.stderr)
    ordinal = 1
    ovstage.population.open_usd(stage, str(args.scene), ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    for _ in range(WARMUP_STEPS):
        renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal)
    products = renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal)

    OUTPUT_DIR.mkdir(exist_ok=True)
    frame = products[RENDER_PRODUCT].frames[0]
    save_render_var(frame, LDR_COLOR_PATH, OUTPUT_DIR / "input.png")
    save_render_var(frame, OUTPUT_VAR_PATH, OUTPUT_DIR / "downscaled.png")

    del frame, products
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()
# [/snippet:run-spg-builtin-nodes]


if __name__ == "__main__":
    main()
