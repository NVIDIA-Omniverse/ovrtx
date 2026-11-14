# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Run the framebuffer feedback Sensor Processing Graph and save its two AOVs.

Loads trail_scene.usda and drives one ball around a circle. The SPG node feeds
its own previous output back in, fading it a little each frame, so the ball drags
a comet tail behind it.

The two images this writes are meant to be looked at as a pair: live.png is the
frame the node was handed, trail.png is what it published from that same frame.
Both come out of one render step through one tone map, so anything that differs
between them came from the previous frame.
"""

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SCENE = SCRIPT_DIR / "trail_scene.usda"
OUTPUT_DIR = SCRIPT_DIR / "_output"
RENDER_PRODUCT = "/Render/TrailDemo"
LIVE_PATH = f"{RENDER_PRODUCT}/LdrLive"
TRAIL_PATH = f"{RENDER_PRODUCT}/LdrTrail"
BALL_PRIM = "/World/Ball"

STEP_DT = 1.0 / 60.0
WARMUP_STEPS = 8

# The ball is driven around a circle so its tail curves through a large arc.
ORBIT_CENTRE = (0.0, 110.0)
ORBIT_RADIUS = 170.0
STEPS_PER_TURN = 36
ORBIT_STEPS = 40  # a full turn and a little, long enough for the tail to settle
START_ANGLE = math.pi / 2  # top of the circle, matching the scene file
DEPTH_Z = 0.0


def ball_transform(step: int) -> np.ndarray:
    """One row-major 4x4 per prim, with the translation in the last row."""
    angle = START_ANGLE + 2.0 * math.pi * step / STEPS_PER_TURN
    m = np.eye(4, dtype=np.float64)
    m[3, 0] = ORBIT_CENTRE[0] + ORBIT_RADIUS * math.cos(angle)
    m[3, 1] = ORBIT_CENTRE[1] + ORBIT_RADIUS * math.sin(angle)
    m[3, 2] = DEPTH_Z
    return m.reshape(1, 4, 4)


def save_render_var(frame, render_var_path: str, path: Path) -> None:
    """Map a render var to the CPU and save it as a PNG."""
    mapped = frame.render_vars[render_var_path].map(device=ovrtx.Device.CPU)
    # Copied, not borrowed: the pixels outlive the mapping they are read from.
    pixels = np.array(np.from_dlpack(mapped), copy=True)
    del mapped
    Image.fromarray(pixels).save(path)
    print(f"Saved {render_var_path} -> {path}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="ovrtx SPG framebuffer feedback example")
    parser.add_argument("--scene", type=Path, default=DEFAULT_SCENE, help="USDA scene to load")
    args = parser.parse_args()

    print("Creating renderer...", file=sys.stderr)
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.spg-stateful")
    renderer.attach_ovstage(stage)

    print(f"Loading {args.scene}...", file=sys.stderr)
    ordinal = 1
    ovstage.population.open_usd(stage, str(args.scene), ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    for _ in range(WARMUP_STEPS):
        renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal)

    # [snippet:trail-move-and-step]
    # Drive the ball around the circle a step at a time. Each step is a
    # render of the ball at one position; the tail exists only because the
    # node feeds its own previous output back in.
    #
    # Each move is a scene edit, so it gets its own ordinal: write the new
    # transform, publish it by advancing the write floor, then render that
    # ordinal. The query and the interned attribute name are made once and
    # reused, since only the matrix changes from step to step.
    products = None
    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings([BALL_PRIM])
        attribute = paths.intern_token("omni:xform")
        with stage.query_from_path_list(path_list) as query:
            for step in range(ORBIT_STEPS):
                ordinal += 1
                matrix = ball_transform(step)
                tensor = ovstage.make_dltensor(
                    matrix,
                    dtype=ovstage.numpy_to_dldatatype(matrix.dtype, lanes=16),
                    shape=[1],
                    ndim=1,
                )
                stage.write_attribute(
                    query, attribute, ordinal=ordinal, tensors=tensor, is_array=False
                ).wait()
                stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
                products = renderer.step(
                    render_products={RENDER_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal
                )
        paths.destroy_path_list(path_list)
    # [/snippet:trail-move-and-step]

    OUTPUT_DIR.mkdir(exist_ok=True)
    frame = products[RENDER_PRODUCT].frames[0]
    save_render_var(frame, LIVE_PATH, OUTPUT_DIR / "live.png")
    save_render_var(frame, TRAIL_PATH, OUTPUT_DIR / "trail.png")

    del frame, products
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


if __name__ == "__main__":
    main()
