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
# The Scale node's factors, as the scene authors them. The check below rebuilds
# the node's result on the host, so these two have to agree with the scene.
SCALE_X = 0.5
SCALE_Y = 0.5


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
    """Rebuild what the two built-in nodes must produce, and compare.

    Add feeds ``LdrColor`` to both of its inputs, and on uint8 it saturates, so
    every channel comes back at ``min(2v, 255)``. Scale then resizes by nearest
    neighbour, taking the source pixel under the destination pixel's centre.
    Both operations are exact in integers, so the comparison admits no
    tolerance: a value that did not double means Add never ran, and a size that
    did not halve means Scale never ran.
    """
    colour = read_render_var(frame, LDR_COLOR_PATH).astype(np.int32)
    result = read_render_var(frame, OUTPUT_VAR_PATH).astype(np.int32)

    failures = []
    source_height, source_width = colour.shape[0], colour.shape[1]
    height, width = result.shape[0], result.shape[1]
    wanted = (max(1, int(source_height * SCALE_Y)), max(1, int(source_width * SCALE_X)))
    print(f"output {width}x{height} from {source_width}x{source_height}", file=sys.stderr)
    if (height, width) != wanted:
        failures.append(
            f"the output is {width}x{height} where {wanted[1]}x{wanted[0]} was wanted: "
            "the Scale node did not run"
        )
        return failures

    rows = np.clip(((np.arange(height) + 0.5) / SCALE_Y).astype(int), 0, source_height - 1)
    columns = np.clip(((np.arange(width) + 0.5) / SCALE_X).astype(int), 0, source_width - 1)
    expected = np.minimum(2 * colour, 255)[np.ix_(rows, columns)]
    worst = int(np.abs(result[..., :3] - expected[..., :3]).max())
    print(f"largest difference from the host-computed result: {worst}", file=sys.stderr)
    if worst:
        failures.append(
            "the output does not match min(2v, 255) resampled: the Add node did not run, or "
            "the two nodes ran in the wrong order"
        )
    return failures


# [snippet:run-spg-builtin-nodes]
def main() -> int:
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
# [/snippet:run-spg-builtin-nodes]


if __name__ == "__main__":
    sys.exit(main())
