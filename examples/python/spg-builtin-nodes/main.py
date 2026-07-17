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
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SCENE = SCRIPT_DIR / "stdlib_scene.usda"
OUTPUT_DIR = SCRIPT_DIR / "_output"
RENDER_PRODUCT = "/Render/StdlibDemo"
OUTPUT_VAR = "Downscaled"
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


# [snippet:run-spg-builtin-nodes]
def main() -> None:
    parser = argparse.ArgumentParser(description="ovrtx SPG built-in (Add + Scale) node example")
    parser.add_argument("--scene", type=Path, default=DEFAULT_SCENE, help="USDA scene to load")
    args = parser.parse_args()

    # Built-in factory nodes are resolved by the renderer; no NVRTC compilation
    # is needed for this scene.
    print("Creating renderer...", file=sys.stderr)
    renderer = ovrtx.Renderer()

    print(f"Loading {args.scene}...", file=sys.stderr)
    renderer.open_usd(str(args.scene))

    for _ in range(WARMUP_STEPS):
        renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT)
    products = renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT)

    OUTPUT_DIR.mkdir(exist_ok=True)
    frame = products[RENDER_PRODUCT].frames[0]
    save_render_var(frame, "LdrColor", OUTPUT_DIR / "input.png")
    save_render_var(frame, OUTPUT_VAR, OUTPUT_DIR / "downscaled.png")
# [/snippet:run-spg-builtin-nodes]


if __name__ == "__main__":
    main()
