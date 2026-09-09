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

# The ball is driven around a circle rather than in a straight line: a tail that
# curves through a large arc cannot be mistaken for blur within one frame.
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


def save_render_var(frame, render_var_path: str, path: Path) -> np.ndarray:
    """Map a render var to the CPU, save it as a PNG, and return the pixels."""
    mapped = frame.render_vars[render_var_path].map(device=ovrtx.Device.CPU)
    # Copied, not borrowed: the pixels outlive the mapping they are read from.
    pixels = np.array(np.from_dlpack(mapped), copy=True)
    del mapped
    Image.fromarray(pixels).save(path)
    print(f"Saved {render_var_path} -> {path}", file=sys.stderr)
    return pixels


def lit_area(pixels: np.ndarray) -> tuple[int, int]:
    """Pixels meaningfully brighter than the backdrop, and the backdrop level.

    Most of the frame is backdrop, so its median is the backdrop level. Anything
    clear of it is the ball or what the ball left behind.
    """
    brightness = pixels[..., :3].astype(np.int32).max(axis=-1)
    backdrop = int(np.median(brightness))
    return int((brightness > backdrop + 8).sum()), backdrop


def main() -> int:
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
    # Drive the ball around the circle a step at a time. Each step is an
    # ordinary render of the ball at one position -- nothing here accumulates
    # anything, and no step is told about any step before it. The tail exists
    # only because the node feeds its own previous output back in.
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
    # Both images come out of the same render step, the same node and the same
    # tone map. The only difference between them is history[n-1].
    live = save_render_var(frame, LIVE_PATH, OUTPUT_DIR / "live.png")
    trailed = save_render_var(frame, TRAIL_PATH, OUTPUT_DIR / "trail.png")

    # [snippet:trail-check]
    # With the feedback running, Trail carries the ball plus the fading tail of
    # everywhere it just was, so it lights many times the area the ball covers,
    # over a backdrop at the same level as the live frame. Without it,
    # history[n-1] reads back empty every frame and the recursion collapses to
    # history[n] = current[n]: the lit area drops back to just the ball, and the
    # backdrop drops with it because nothing is left for the exposure scale to
    # bring back up.
    live_lit, live_backdrop = lit_area(live)
    trail_lit, trail_backdrop = lit_area(trailed)
    print(f"lit area:       {live_lit:6d} px live, {trail_lit:6d} px with the tail "
          f"({trail_lit / max(1, live_lit):.1f}x)", file=sys.stderr)
    print(f"backdrop level: {live_backdrop:6d}    live, {trail_backdrop:6d}    with the tail",
          file=sys.stderr)

    failures = []
    if live_lit == 0:
        # Checked first and on its own: with nothing rendered, every comparison
        # below reads 0 against 0 and passes without meaning anything.
        failures.append(
            "the live frame is empty, so nothing was rendered and no comparison below carries "
            "any weight"
        )
    elif trail_lit < 2 * live_lit:
        failures.append("no tail: history[n-1] is not carrying into this frame")
    elif trail_backdrop != live_backdrop:
        failures.append(
            "the backdrop does not match: the exposure scale is not undoing the feedback gain"
        )
    # [/snippet:trail-check]

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


if __name__ == "__main__":
    sys.exit(main())
