# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Render the same rect-light scene with RGB or spectral light transport."""

import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image

import ovrtx
import ovstage


def main():
    """Select authored variants and capture one converged PathTracing frame."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--illuminant", choices=("white", "blackbody3200", "daylight", "sodium", "mercury"), default="white"
    )
    parser.add_argument("--camera", choices=("cie1931", "canon5d", "sony_a7iv"), default="cie1931")
    parser.add_argument("--transport", choices=("rgb", "spectral"), default="rgb")
    parser.add_argument("--white-point", type=float, help="Camera white-point temperature in kelvin (spectral only)")
    parser.add_argument("--spp", type=int, default=4096)
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--png", type=Path, help="Save PNG without opening a viewer")
    parser.add_argument("--hdr", type=Path, help="Save linear HdrColor as a NumPy array")
    parser.add_argument("--rrd", type=Path, help="Save a Rerun recording")
    parser.add_argument("--log", type=Path, default=Path("_output/spectral.log"))
    args = parser.parse_args()
    if args.spp < 1 or args.size < 1:
        parser.error("--spp and --size must be positive")
    if args.camera != "cie1931" and args.transport != "spectral":
        parser.error("Custom camera responsivities require --transport spectral")
    if args.white_point is not None and (
        not math.isfinite(args.white_point) or args.white_point <= 0 or args.transport != "spectral"
    ):
        parser.error("--white-point must be finite and positive and requires spectral transport")
    args.log.parent.mkdir(parents=True, exist_ok=True)
    # [snippet:doc-spectral-config-python]
    # Select the process-wide material backend before creating any renderer.
    config = ovrtx.RendererConfig(
        enable_spectral_rendering=args.transport == "spectral",
        log_file_path=str(args.log),
    )
    renderer = ovrtx.Renderer(config=config)
    # [/snippet:doc-spectral-config-python]
    stage = ovstage.Stage("ovrtx.example.spectral")
    renderer.attach_ovstage(stage)
    try:
        # [snippet:doc-spectral-select-python]
        # Camera prims share geometry/exposure; only their spectral response differs.
        camera_path = {"cie1931": "/World/Camera", "canon5d": "/World/Canon5D", "sony_a7iv": "/World/SonyA7IV"}[args.camera]
        # Apply the API only when requested; its default curves provide CIE 1931 responsivity.
        white_point_layer = ""
        if args.white_point is not None:
            camera_name = camera_path.rsplit("/", 1)[1]
            white_point_layer = f'''over "{camera_name}" (prepend apiSchemas = ["PhysicalCameraResponsivityAPI"]) {{
                float physical:responsivity:colorTemperature = {args.white_point}
            }}'''
        scene_path = Path(__file__).with_name("spectral.usda").resolve()
        layer = f"""#usda 1.0
        (
            subLayers = [@{scene_path.as_posix()}@]
        )
        over "World" {{
            {white_point_layer}
            over "RectLight" (variants = {{ string illuminant = "{args.illuminant}" }}) {{}}
        }}
        over "Render" {{
            over "Camera" (variants = {{ string transport = "{args.transport}" }}) {{
                rel camera = <{camera_path}>
                uint omni:rtx:pt:samplesPerPixel = {args.spp}
                int2 resolution = ({args.size}, {args.size})
            }}
        }}
        """
        ordinal = 1
        ovstage.population.open_usd_from_string(stage, layer, ordinal=ordinal)
        stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
        # PathTracing accumulates the requested samples within one step.
        products = renderer.step(render_products={"/Render/Camera"}, delta_time=1 / 60, ordinal=ordinal)
        frame = products["/Render/Camera"].frames[-1]
        mapped = frame.render_vars["/Render/Camera/LdrColor"].map(device=ovrtx.Device.CPU)
        pixels = np.from_dlpack(mapped).copy()
        mapped.unmap()
        del mapped
        # [/snippet:doc-spectral-select-python]
        if args.hdr:
            mapped = frame.render_vars["/Render/Camera/HdrColor"].map(device=ovrtx.Device.CPU)
            hdr = np.from_dlpack(mapped).copy()
            mapped.unmap()
            del mapped
            args.hdr.parent.mkdir(parents=True, exist_ok=True)
            np.save(args.hdr, hdr)
        del frame, products
        if args.png:
            args.png.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(pixels).save(args.png)
        if args.rrd or not args.png:
            import rerun as rr

            rr.init("ovrtx_spectral_rendering", spawn=args.rrd is None)
            if args.rrd:
                args.rrd.parent.mkdir(parents=True, exist_ok=True)
                rr.save(str(args.rrd))
            rr.log(f"{args.illuminant}/{args.transport}/{args.camera}", rr.Image(pixels))
    finally:
        renderer.detach_ovstage()
        stage.destroy()
        renderer.destroy()


if __name__ == "__main__":
    main()
