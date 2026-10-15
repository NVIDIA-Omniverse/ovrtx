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
import ovrtx
import ovstage
from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser(description="Render an animated rolling-shutter camera")
    parser.add_argument(
        "--rrd", type=Path, help="Write a Rerun recording instead of opening a viewer"
    )
    parser.add_argument("--png", type=Path, help="Write the final rendered frame to PNG")
    parser.add_argument("--no-rr", action="store_true", help="Do not log images to Rerun")
    args = parser.parse_args()

    # [snippet:doc-render-rolling-shutter]
    renderer = ovrtx.Renderer(
        ovrtx.RendererConfig(motion_bvh=ovrtx.MotionBvh.AUTO)
    )
    stage = ovstage.Stage("ovrtx.example.camera-rolling-shutter")
    renderer.attach_ovstage(stage)

    ordinal = 1
    ovstage.population.open_usd(
        stage,
        str(Path(__file__).with_name("rolling_shutter.usda")),
        ordinal=ordinal,
    )
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    # For 480 rows, match the step to the rolling shutter's 50.41 ms exposure span.
    step_time = (480 - 1) * (40 / 1_000_000) + (1 / 32)
    pixels = None
    for frame_number in range(1, 11):
        ordinal += 1
        ovstage.population.update_from_usd_time(
            stage,
            ordinal,
            frame_number * step_time,
        )
        stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
        products = renderer.step(
            render_products={"/Render/Camera", "/Render/GlobalShutterCamera"},
            delta_time=step_time,
            ordinal=ordinal,
        )
        if (
            products["/Render/Camera"].frames
            and products["/Render/GlobalShutterCamera"].frames
        ):
            rolling_frame = products["/Render/Camera"].frames[0]
            rolling_mapped = rolling_frame.render_vars["/Render/LdrColor"].map(
                device=ovrtx.Device.CPU
            )
            rolling_pixels = np.from_dlpack(rolling_mapped).copy()
            global_frame = products["/Render/GlobalShutterCamera"].frames[0]
            global_mapped = global_frame.render_vars["/Render/LdrColor"].map(
                device=ovrtx.Device.CPU
            )
            global_pixels = np.from_dlpack(global_mapped).copy()
            pixels = np.concatenate((global_pixels, rolling_pixels), axis=1)
            del rolling_mapped, rolling_frame, global_mapped, global_frame

    if pixels is None:
        raise RuntimeError("The rolling-shutter camera did not produce an image")
    # [/snippet:doc-render-rolling-shutter]

    if not args.no_rr:
        import rerun as rr
        import rerun.blueprint as rrb

        rr.init("ovrtx_camera_rolling_shutter", spawn=args.rrd is None)
        if args.rrd:
            rr.save(str(args.rrd))
        rr.send_blueprint(
            rrb.Blueprint(
                rrb.Horizontal(
                    rrb.Spatial2DView(origin="global_shutter", name="Global shutter"),
                    rrb.Spatial2DView(origin="rolling_shutter", name="Rolling shutter"),
                )
            )
        )
        rr.log("global_shutter", rr.Image(global_pixels))
        rr.log("rolling_shutter", rr.Image(rolling_pixels))

    if args.png:
        args.png.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(pixels).save(args.png)

    del products
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


if __name__ == "__main__":
    main()
