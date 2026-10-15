#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

import ovrtx
import ovstage


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Minimal mode with optional DLSS")
    parser.add_argument(
        "--dlss-mode", type=int, choices=(0, 1, 2), default=1, help="0: disabled, 1: DLSS-SR, 2: DLSS-RR"
    )
    parser.add_argument(
        "--exec-mode",
        default="quality",
        choices=("auto", "performance", "balanced", "quality", "rtxaa"),
        help="DLSS resolution preset; rtxaa selects native-resolution DLAA",
    )
    parser.add_argument(
        "--frames", type=int, default=32, help="Number of frames to render before saving the final image"
    )
    parser.add_argument("--rrd", type=Path, help="Save a Rerun recording instead of opening a viewer")
    parser.add_argument("--png", type=Path, help="Save the final image to PNG")
    parser.add_argument("--log", type=Path, help="Save renderer diagnostics to a log file")
    parser.add_argument("--no-rr", action="store_true", help="Disable Rerun output")
    parser.add_argument(
        "--usd",
        type=Path,
        help=(
            "Scene to sublayer instead of minimal_dlss.usda; it must define /World/Camera "
            "and a /Render/Camera RenderProduct with an LdrColor RenderVar"
        ),
    )
    args = parser.parse_args()
    if args.frames < 1:
        parser.error("--frames must be positive")
    if args.usd is not None and not args.usd.is_file():
        parser.error(f"--usd file not found: {args.usd}")
    if args.rrd and args.no_rr:
        parser.error("--rrd cannot be combined with --no-rr")

    if not args.no_rr:
        import rerun as rr

        rr.init("ovrtx_minimal_dlss", spawn=args.rrd is None)
        if args.rrd:
            args.rrd.parent.mkdir(parents=True, exist_ok=True)
            rr.save(str(args.rrd))

    if args.log:
        args.log.parent.mkdir(parents=True, exist_ok=True)
    config = ovrtx.RendererConfig(log_file_path=str(args.log) if args.log else None)
    renderer = ovrtx.Renderer(config=config)
    stage = ovstage.Stage("ovrtx.example.minimal-dlss")
    renderer.attach_ovstage(stage)
    pixels = None
    try:
        # [snippet:doc-render-minimal-dlss-python]
        # Compose the scene with the selected settings on its RenderProduct.
        # --usd swaps in a scene that defines /World/Camera and /Render/Camera with LdrColor.
        scene_path = (args.usd or Path(__file__).with_name("minimal_dlss.usda")).resolve()
        scene = f"""#usda 1.0
        (
            subLayers = [@{scene_path.as_posix()}@]
        )
        over "Render"
        {{
            over "Camera"
            {{
                int omni:rtx:minimal:dlss:mode = {args.dlss_mode}
                token omni:rtx:minimal:dlss:execMode = "{args.exec_mode}"
            }}
        }}
        """
        ordinal = 1
        ovstage.population.open_usd_from_string(stage, scene, ordinal=ordinal)
        stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

        # Keep the renderer alive across frames so DLSS can build temporal history.
        for frame_index in range(args.frames):
            products = renderer.step(
                render_products={"/Render/Camera"},
                delta_time=1.0 / 60.0,
                ordinal=ordinal,
            )
            for frame in products["/Render/Camera"].frames:
                mapped = frame.render_vars["/Render/Camera/LdrColor"].map(device=ovrtx.Device.CPU)
                pixels = np.from_dlpack(mapped).copy()
                mapped.unmap()
                del mapped, frame
            del products
            # [/snippet:doc-render-minimal-dlss-python]

            if pixels is not None and not args.no_rr:
                rr.set_time("frame", sequence=frame_index)
                rr.log("camera", rr.Image(pixels))

        if pixels is None:
            raise RuntimeError("The camera did not produce an image")
        if args.png:
            args.png.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(pixels).save(args.png)
    finally:
        renderer.detach_ovstage()
        stage.destroy()
        renderer.destroy()


if __name__ == "__main__":
    main()
