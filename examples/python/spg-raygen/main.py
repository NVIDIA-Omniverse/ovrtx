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
from two probe rays, and a shadow ray toward the light.

This script writes the render to _output/ and then checks it, without a golden
image, from what the shader encodes into the two channels.
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
DEFAULT_SCENE = SCRIPT_DIR / "cornell_box_scene.usda"
OUTPUT_DIR = SCRIPT_DIR / "_output"
RENDER_PRODUCT = "/Render/CornellBox"
# The RenderVar is addressed by its prim name, which need not match its sourceName.
OUTPUT_VAR_PATH = f"{RENDER_PRODUCT}/Cornell"
WARMUP_STEPS = 5
STEP_DT = 1.0 / 60.0

# Encoding a normal as a colour compresses angles. The two blocks are rotated 18
# and 20 degrees about Y, which is 6.8 and 7.5 degrees apart from the nearest
# axis once encoded, while the flat walls sit at zero. 4 degrees separates them,
# and a room with the blocks removed scores under half a percent.
OFF_AXIS_DEGREES = 4.0
MIN_OFF_AXIS = 0.05

# Sample bands, each well clear of the blocks and the room's corners.
BANDS = {
    "floor": ((216, 236), (110, 146)),
    "ceiling": ((20, 40), (110, 146)),
    "left wall": ((110, 146), (20, 40)),
    "right wall": ((110, 146), (216, 236)),
    "back wall": ((120, 136), (120, 136)),
}


def check(image: np.ndarray) -> list[str]:
    """Check the render from what the shader encodes, with no reference image.

    Colour is the recovered surface normal, so each wall's dominant channel
    states its orientation. That ordering survives any lighting level, which is
    what makes it checkable: it is immune to brightness but fails on a wrong or
    flipped normal. Alpha carries visibility, so shadowing is checked separately
    from colour.
    """
    height, width = image.shape[:2]
    rgb = image[:, :, :3].astype(np.int32)
    alpha = image[:, :, 3]

    # The camera looks fully into the room, so every ray must land on a surface.
    misses = int(np.count_nonzero(alpha == 0))
    print(f"rays that escaped the room: {misses}", file=sys.stderr)

    def band(name):
        (r0, r1), (c0, c1) = BANDS[name]
        return rgb[r0:r1, c0:c1].reshape(-1, 3).mean(axis=0)

    floor, ceiling = band("floor"), band("ceiling")
    left, right, back = band("left wall"), band("right wall"), band("back wall")
    # [snippet:raygen-wall-orientation]
    checks = {
        "floor +Y reads green-dominant": floor[1] > floor[0] and floor[1] > floor[2],
        "ceiling -Y reads green-minimal": ceiling[1] < ceiling[0] and ceiling[1] < ceiling[2],
        "left wall +X reads red-dominant": left[0] > left[1] and left[0] > left[2],
        "right wall -X reads red-minimal": right[0] < right[1] and right[0] < right[2],
        "back wall +Z reads blue-dominant": back[2] > back[0] and back[2] > back[1],
    }
    # [/snippet:raygen-wall-orientation]
    failures = [label for label, ok in checks.items() if not ok]
    for label, ok in checks.items():
        print(f"  {'ok  ' if ok else 'FAIL'} {label}", file=sys.stderr)

    # [snippet:raygen-off-axis]
    # The blocks are rotated about Y, so their faces are not axis aligned. A real
    # population of off-axis normals is what proves the recovery resolves
    # per-triangle orientation rather than only flat, axis-aligned walls.
    #
    # Compare the colours as written, without decoding them. The shader scales the
    # encoded normal by the lighting, and decoding with ``* 2 - 1`` inverts that
    # only where the pixel is fully lit. Anywhere darker the result swings toward
    # (-1, -1, -1), so a flat wall in shadow reads as steeply tilted and the count
    # measures shading instead of geometry. Scaling never changes the direction a
    # colour points in, so comparing encoded directions divides the lighting out.
    encoded = rgb.reshape(-1, 3).astype(np.float32)
    lengths = np.linalg.norm(encoded, axis=1)
    keep = lengths > 0.0  # a miss is black and carries no direction
    unit = encoded[keep] / lengths[keep, None]
    axes = np.array(
        [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], dtype=np.float32
    )
    encoded_axes = axes * 0.5 + 0.5
    encoded_axes /= np.linalg.norm(encoded_axes, axis=1, keepdims=True)
    closest = np.max(unit @ encoded_axes.T, axis=1)
    off_axis = np.count_nonzero(
        closest < math.cos(math.radians(OFF_AXIS_DEGREES))
    ) / float(unit.shape[0])
    # [/snippet:raygen-off-axis]

    # Shadow rays have to darken a real part of the room, and most of it has to
    # stay lit: a uniformly dark image would satisfy the hue ordering too.
    total = float(height * width)
    shadowed = np.count_nonzero((alpha > 70) & (alpha < 110)) / total
    lit = np.count_nonzero(alpha > 200) / total

    print(f"surfaces more than {OFF_AXIS_DEGREES:g} degrees off every axis: {off_axis:.1%}",
          file=sys.stderr)
    print(f"shadowed {shadowed:.1%} of pixels, lit {lit:.1%}", file=sys.stderr)
    if misses:
        failures.append("some rays escaped: the camera framing or the scene changed")
    if off_axis <= MIN_OFF_AXIS:
        failures.append("the rotated blocks' faces were not resolved")
    if shadowed <= 0.01:
        failures.append("no ray-traced shadows: the shadow ray is not occluding")
    if lit <= 0.01:
        failures.append("nothing is lit: the room is uniformly dark and the hue checks above "
                        "would pass on a black image")
    return failures


def main() -> int:
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

    failures = check(image)

    path = OUTPUT_DIR / "cornell_box.png"
    Image.fromarray(image[..., :3]).save(path)
    print(f"Saved {OUTPUT_VAR_PATH} -> {path}", file=sys.stderr)

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
