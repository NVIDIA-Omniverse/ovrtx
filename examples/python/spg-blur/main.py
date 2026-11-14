# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Run the separable-blur Sensor Processing Graph and save what it produced.

Two chained nodes blur LdrColor, first along x and then along y, with the tap
weights built in the launch script and uploaded once per radius. The first
node's output is published as well, so the half-finished blur can be read back.

The radius is a USD attribute. The run renders at radius 8, then rewrites the
attribute to 0, which turns the blur into the identity, and renders again. Every
image goes to _output/.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SCENE = SCRIPT_DIR / "blur_scene.usda"
OUTPUT_DIR = SCRIPT_DIR / "_output"
RENDER_PRODUCT = "/Render/BlurDemo"
LDR_COLOR_PATH = f"{RENDER_PRODUCT}/LdrColor"
HALF_BLURRED_PATH = f"{RENDER_PRODUCT}/LdrBlurH"
BLURRED_PATH = f"{RENDER_PRODUCT}/LdrBlurred"
BLUR_NODES = [f"{RENDER_PRODUCT}/BlurH", f"{RENDER_PRODUCT}/BlurV"]
WARMUP_STEPS = 12
STEP_DT = 1.0 / 60.0

BLUR_RADIUS = 8


def save_render_var(frame, render_var_path: str, path: Path) -> None:
    """Map a render var to the CPU and save it as a PNG."""
    mapped = frame.render_vars[render_var_path].map(device=ovrtx.Device.CPU)
    pixels = np.from_dlpack(mapped)
    Image.fromarray(np.ascontiguousarray(pixels)).save(path)
    print(f"Saved {render_var_path} -> {path}", file=sys.stderr)


# [snippet:blur-write-radius]
def set_radius(stage, ordinal: int, radius: int) -> None:
    """Write inputs:radius on both blur nodes and publish the edit.

    The attribute is connected to nothing, so the value on the prim is the value
    the node reads. Each node is written separately because each carries its own
    copy of the attribute.
    """
    value = np.array([radius], dtype=np.int32)
    tensor = ovstage.make_dltensor(
        value, dtype=ovstage.numpy_to_dldatatype(value.dtype, lanes=1), shape=[1], ndim=1
    )
    with ovstage.PathDictionary(stage) as paths:
        attribute = paths.intern_token("inputs:radius")
        for node in BLUR_NODES:
            path_list = paths.create_path_list_from_strings([node])
            with stage.query_from_path_list(path_list) as query:
                stage.write_attribute(
                    query, attribute, ordinal=ordinal, tensors=tensor, is_array=False
                ).wait()
            paths.destroy_path_list(path_list)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
# [/snippet:blur-write-radius]


def render_at_radius(stage, renderer, ordinal: int, radius: int):
    """Set the radius, let the image settle, and return one frame's render vars."""
    set_radius(stage, ordinal, radius)
    for _ in range(WARMUP_STEPS):
        renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal)
    return renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal)


def main() -> None:
    parser = argparse.ArgumentParser(description="ovrtx SPG separable blur example")
    parser.add_argument("--scene", type=Path, default=DEFAULT_SCENE, help="USDA scene to load")
    args = parser.parse_args()

    print("Creating renderer...", file=sys.stderr)
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.spg-blur")
    renderer.attach_ovstage(stage)

    print(f"Loading {args.scene}...", file=sys.stderr)
    ordinal = 1
    ovstage.population.open_usd(stage, str(args.scene), ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    OUTPUT_DIR.mkdir(exist_ok=True)
    ordinal += 1
    products = render_at_radius(stage, renderer, ordinal, BLUR_RADIUS)
    frame = products[RENDER_PRODUCT].frames[0]
    save_render_var(frame, LDR_COLOR_PATH, OUTPUT_DIR / "input.png")
    save_render_var(frame, HALF_BLURRED_PATH, OUTPUT_DIR / "blurred-one-pass.png")
    save_render_var(frame, BLURRED_PATH, OUTPUT_DIR / "blurred.png")
    del frame, products

    # [snippet:blur-runtime-radius]
    # inputs:radius is unconnected, so a write takes effect on the next step
    # with no reset. At 0 the weight table is {1.0} and the blur is the
    # identity, so the published AOV matches the frame's LdrColor exactly.
    ordinal += 1
    products = render_at_radius(stage, renderer, ordinal, 0)
    frame = products[RENDER_PRODUCT].frames[0]
    save_render_var(frame, LDR_COLOR_PATH, OUTPUT_DIR / "radius-0-input.png")
    save_render_var(frame, BLURRED_PATH, OUTPUT_DIR / "radius-0.png")
    del frame, products
    # [/snippet:blur-runtime-radius]

    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


if __name__ == "__main__":
    main()
