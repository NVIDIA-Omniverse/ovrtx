# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Run the previous-frame Sensor Processing Graph and check what it produced.

One node takes two images: LdrColor as the renderer produced it this frame, and
LdrColor as it was one frame ago. It publishes the difference, so anything that
moved lights up and anything that held still goes dark.

The check is the contrast between the two halves of the run:

  moving   the ball is driven around a circle, one step at a time, and the
           difference has to light up where it moved
  still    the ball is left where it is for the same number of steps, and the
           difference has to collapse

A node reading the live AOV twice would produce a black image in both halves, so
the first half is what proves the ``:-1`` binding resolved to a past frame.
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
DEFAULT_SCENE = SCRIPT_DIR / "motion_scene.usda"
OUTPUT_DIR = SCRIPT_DIR / "_output"
RENDER_PRODUCT = "/Render/MotionDemo"
LDR_COLOR_PATH = f"{RENDER_PRODUCT}/LdrColor"
MOTION_PATH = f"{RENDER_PRODUCT}/Motion"
BALL_PRIM = "/World/Ball"

STEP_DT = 1.0 / 60.0
WARMUP_STEPS = 8

# The ball is driven around a circle so that every step moves it somewhere the
# previous step did not cover.
ORBIT_CENTRE = (0.0, 110.0)
ORBIT_RADIUS = 170.0
STEPS_PER_TURN = 36
MOVING_STEPS = 12
STILL_STEPS = 12
START_ANGLE = math.pi / 2  # top of the circle, matching the scene file

# A pixel is "changed" when the node's difference clears this, well above the
# sampling noise of a converged render.
CHANGED_LEVEL = 24


def ball_transform(step: int) -> np.ndarray:
    """One row-major 4x4 per prim, with the translation in the last row."""
    angle = START_ANGLE + 2.0 * math.pi * step / STEPS_PER_TURN
    m = np.eye(4, dtype=np.float64)
    m[3, 0] = ORBIT_CENTRE[0] + ORBIT_RADIUS * math.cos(angle)
    m[3, 1] = ORBIT_CENTRE[1] + ORBIT_RADIUS * math.sin(angle)
    return m.reshape(1, 4, 4)


def read_var(frame, render_var_path: str) -> np.ndarray:
    """Map a render var to the CPU and return a copy of its pixels.

    The copy is not optional. np.from_dlpack borrows the mapped buffer, and
    ascontiguousarray hands back that same array when it is already contiguous,
    so returning it would leave the caller reading a released mapping.
    """
    mapped = frame.render_vars[render_var_path].map(device=ovrtx.Device.CPU)
    pixels = np.array(np.from_dlpack(mapped), copy=True)
    del mapped
    return pixels


def save_png(pixels: np.ndarray, path: Path) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    Image.fromarray(pixels).save(path)
    print(f"Saved {path}")


# [snippet:previous-frame-changed-pixels]
def changed_pixels(motion: np.ndarray) -> int:
    """How many pixels the node reported as different from the frame before."""
    return int((motion[..., 0] > CHANGED_LEVEL).sum())
# [/snippet:previous-frame-changed-pixels]


def main() -> int:
    parser = argparse.ArgumentParser(description="ovrtx SPG previous-frame example")
    parser.add_argument("--scene", type=Path, default=DEFAULT_SCENE, help="USDA scene to load")
    args = parser.parse_args()

    print(f"Loading {args.scene}...")
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.spg-previous-frame")
    renderer.attach_ovstage(stage)

    ordinal = 1
    ovstage.population.open_usd(stage, str(args.scene), ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    for _ in range(WARMUP_STEPS):
        renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal)

    moving_counts = []
    still_counts = []
    moving_motion = None
    still_motion = None
    colour = None

    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings([BALL_PRIM])
        attribute = paths.intern_token("omni:xform")
        with stage.query_from_path_list(path_list) as query:

            def place(step: int) -> None:
                """Move the ball to its position for this step and publish the edit."""
                nonlocal ordinal
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

            # [snippet:previous-frame-moving-and-still]
            # Moving: a new position every step, so consecutive frames differ.
            for step in range(MOVING_STEPS):
                place(step)
                products = renderer.step(
                    render_products={RENDER_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal
                )
                frame = products[RENDER_PRODUCT].frames[0]
                moving_motion = read_var(frame, MOTION_PATH)
                colour = read_var(frame, LDR_COLOR_PATH)
                moving_counts.append(changed_pixels(moving_motion))
                del frame, products

            # Still: the same position every step, so consecutive frames agree.
            for _ in range(STILL_STEPS):
                place(MOVING_STEPS - 1)
                products = renderer.step(
                    render_products={RENDER_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal
                )
                frame = products[RENDER_PRODUCT].frames[0]
                still_motion = read_var(frame, MOTION_PATH)
                still_counts.append(changed_pixels(still_motion))
                del frame, products
            # [/snippet:previous-frame-moving-and-still]

        paths.destroy_path_list(path_list)

    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()

    save_png(colour, OUTPUT_DIR / "colour.png")
    save_png(moving_motion, OUTPUT_DIR / "motion-moving.png")
    save_png(still_motion, OUTPUT_DIR / "motion-still.png")

    # The last frame of each half is the settled one: the moving half has been
    # moving for a while, and the still half has been still for a while.
    moving = moving_counts[-1]
    still = still_counts[-1]
    print()
    print(f"pixels changed while moving: {moving}")
    print(f"pixels changed while still:  {still}")

    failures = []
    if moving == 0:
        failures.append(
            "nothing changed while the ball was moving: the ':-1' suffix did not resolve, "
            "so the node is comparing the live AOV with itself"
        )
    if still * 8 > moving:
        failures.append(
            f"holding still did not quiet the difference ({moving} moving against {still} still): "
            "the second input is not one frame behind the first"
        )

    print()
    for failure in failures:
        print(f"FAILED: {failure}", file=sys.stderr)
    if failures:
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
