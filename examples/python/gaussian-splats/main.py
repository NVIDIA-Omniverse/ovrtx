# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Render the same Gaussian scene with one selected renderer mode."""
import argparse
from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("rtpt", "pt", "minimal"), default="rtpt")
    parser.add_argument("--scene", type=Path, default=Path(__file__).with_name("gaussian_splats.usda"))
    parser.add_argument("--steps", type=int, default=1)
    parser.add_argument("--png", type=Path, help="Save a PNG instead of opening the viewer")
    parser.add_argument("--rrd", type=Path, help="Save a Rerun recording")
    args = parser.parse_args()
    if args.steps < 1:
        parser.error("--steps must be positive")
    mode = {"rtpt": "RealTimePathTracing", "pt": "PathTracing", "minimal": "MinimalRendering"}[args.mode]
    # [snippet:gaussian-render-python]
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.gaussian-splats")
    try:
        renderer.attach_ovstage(stage)
        # Layer a mode override over the same scene; render one mode per run.
        layer = ('#usda 1.0\n(subLayers = [@' + args.scene.resolve().as_posix() + '@])\n'
                 'over "Render" {\n over "Camera" {\n token omni:rtx:rendermode = "' + mode + '"\n }\n }\n')
        ovstage.population.open_usd_from_string(stage, layer, ordinal=1)
        stage.advance_write_floor(1, ovstage.Scope.ALL).wait()
        # Render one frame by default; --steps can request later frames.
        for _ in range(args.steps):
            products = renderer.step(render_products={"/Render/Camera"}, delta_time=1/60, ordinal=1)
        output = products["/Render/Camera"].frames[0].render_vars["/Render/Camera/LdrColor"]
        mapped = output.map(device=ovrtx.Device.CPU)
        view = np.from_dlpack(mapped)
        pixels = view.copy()
        del view
        mapped.unmap()
        del mapped, output, products
    finally:
        renderer.detach_ovstage()
        renderer.destroy()
        stage.destroy()
    # [/snippet:gaussian-render-python]
    if args.png:
        args.png.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(pixels).save(args.png)
    if args.rrd or not args.png:
        import rerun as rr
        rr.init("ovrtx-gaussian-splats", spawn=not args.rrd)
        if args.rrd:
            args.rrd.parent.mkdir(parents=True, exist_ok=True)
            rr.save(str(args.rrd))
        rr.log(args.mode, rr.Image(pixels))


if __name__ == "__main__":
    main()
