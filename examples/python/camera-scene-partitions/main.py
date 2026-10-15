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
from PIL import Image, ImageDraw, ImageFont


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render left, right, and both scene partitions"
    )
    parser.add_argument(
        "--rrd", type=Path, help="Write a Rerun recording instead of opening a viewer"
    )
    parser.add_argument("--png", type=Path, help="Write the three rendered views to one PNG")
    parser.add_argument("--no-rr", action="store_true", help="Do not log images to Rerun")
    args = parser.parse_args()

    # [snippet:doc-render-camera-scene-partitions]
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.camera-scene-partitions")
    renderer.attach_ovstage(stage)

    ordinal = 1
    ovstage.population.open_usd(
        stage,
        str(Path(__file__).with_name("scene_partitions.usda")),
        ordinal=ordinal,
    )
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    render_product_paths = ("/Render/Left", "/Render/Right", "/Render/Both")
    products = None
    for _ in range(40):
        products = renderer.step(
            render_products=set(render_product_paths),
            delta_time=1.0 / 60.0,
            ordinal=ordinal,
        )

    # Verify every partition camera produced output before accessing its first frame.
    if not all(products[path].frames for path in render_product_paths):
        raise RuntimeError("Not all scene-partition cameras produced an image")

    images = {}
    for render_product_path in render_product_paths:
        frame = products[render_product_path].frames[0]
        mapped = frame.render_vars["/Render/LdrColor"].map(device=ovrtx.Device.CPU)
        images[render_product_path] = np.from_dlpack(mapped).copy()
        del mapped, frame
    # [/snippet:doc-render-camera-scene-partitions]

    if not args.no_rr:
        import rerun as rr
        import rerun.blueprint as rrb

        rr.init("ovrtx_camera_scene_partitions", spawn=args.rrd is None)
        if args.rrd:
            rr.save(str(args.rrd))
        rr.send_blueprint(
            rrb.Blueprint(
                rrb.Horizontal(
                    rrb.Spatial2DView(origin="left", name="Left only"),
                    rrb.Spatial2DView(origin="right", name="Right only"),
                    rrb.Spatial2DView(origin="both", name="Both"),
                )
            )
        )
        rr.log("left", rr.Image(images["/Render/Left"]))
        rr.log("right", rr.Image(images["/Render/Right"]))
        rr.log("both", rr.Image(images["/Render/Both"]))

    if args.png:
        args.png.parent.mkdir(parents=True, exist_ok=True)
        combined = np.concatenate(
            (images["/Render/Left"], images["/Render/Right"], images["/Render/Both"]),
            axis=1,
        )
        output = Image.new("RGB", (combined.shape[1], combined.shape[0] + 48), "#18212b")
        output.paste(Image.fromarray(combined), (0, 48))
        draw = ImageDraw.Draw(output)
        font = ImageFont.load_default(size=24)
        for index, label in enumerate(("Left only", "Right only", "Both")):
            draw.text((index * 640 + 320, 24), label, font=font, fill="white", anchor="mm")
        for x in (640, 1280):
            draw.line((x, 48, x, output.height), fill="#18212b", width=3)
        output.save(args.png)

    del products
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


if __name__ == "__main__":
    main()
