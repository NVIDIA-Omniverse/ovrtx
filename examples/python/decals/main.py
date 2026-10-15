#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Render logo decals and display or save the result."""

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

import ovrtx
import ovstage

SCRIPT_DIR = Path(__file__).parent.resolve()
SCENE_PATH = (SCRIPT_DIR / "../../../tests/docs/data/ovrtx-test-decals.usda").resolve()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--png", type=Path, nargs="?", const=SCRIPT_DIR / "_output/decals.png",
                        help="Save a PNG; optionally choose its path")
    parser.add_argument("--rrd", type=Path, help="Save a Rerun recording instead of opening its viewer")
    args = parser.parse_args()

    # [snippet:doc-decals-python-render]
    # ovstage owns the scene; ovrtx renders the attached runtime stage.
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.decals")
    renderer.attach_ovstage(stage)

    ordinal = 1
    ovstage.population.open_usd(stage, SCENE_PATH, ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    # Warm up material loading and temporal accumulation before saving.
    for _ in range(40):
        renderer.step({"/Render/Camera"}, 1.0 / 60.0, ordinal=ordinal)

    products = renderer.step({"/Render/Camera"}, 1.0 / 60.0, ordinal=ordinal)
    # [/snippet:doc-decals-python-render]

    # [snippet:doc-decals-python-save]
    product = products["/Render/Camera"]
    frame = product.frames[-1]
    mapped = frame.render_vars["/Render/Camera/LdrColor"].map(device=ovrtx.Device.CPU)
    view = np.from_dlpack(mapped)
    pixels = view.copy()  # Keep pixels valid after the mapped output is released.
    del view
    mapped.unmap()
    del mapped
    if args.png:
        args.png.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(pixels).save(args.png)
        print(f"Saved {args.png}", file=sys.stderr)
    # [/snippet:doc-decals-python-save]

    if args.rrd or not args.png:
        import rerun as rr

        rr.init("ovrtx_decals", spawn=args.rrd is None)
        if args.rrd:
            args.rrd.parent.mkdir(parents=True, exist_ok=True)
            rr.save(str(args.rrd))
        rr.log("render/decals", rr.Image(pixels[:, :, :3]))

    del frame, product, products
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


if __name__ == "__main__":
    main()
