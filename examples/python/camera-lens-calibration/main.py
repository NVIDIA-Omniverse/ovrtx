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
import sys
from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare OpenCV pinhole, OpenCV fisheye, and omni-directional stereo cameras"
    )
    parser.add_argument(
        "--rrd", type=Path, help="Write a Rerun recording instead of opening a viewer"
    )
    parser.add_argument(
        "--png",
        type=Path,
        help="Write a contact sheet and individual views using this PNG filename as a base",
    )
    parser.add_argument("--no-rr", action="store_true", help="Do not log images to Rerun")
    args = parser.parse_args()

    # [snippet:doc-render-calibrated-cameras]
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.camera-lens-calibration")
    renderer.attach_ovstage(stage)

    ordinal = 1
    # OVStage is silent without a callback, including USD payload-loading warnings.
    ovstage.set_log_callback(
        lambda severity, timestamp, message: print(f"{severity.name}: {message}", file=sys.stderr),
    )
    try:
        ovstage.population.open_usd(
            stage,
            str(Path(__file__).with_name("camera_lens_calibration.usda")),
            ordinal=ordinal,
        )
    finally:
        # Clearing the callback also flushes queued diagnostics.
        ovstage.set_log_callback(None)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    mesh_filter = ovstage.Filter([ovstage.Predicate("usd-prim-type", ovstage.FilterOp.IN, ["Mesh"])])
    with stage.query(filter=mesh_filter) as meshes:
        mesh_count = meshes.result().total_prim_count
    if not mesh_count:
        raise RuntimeError("The robot-lineup scene contains no meshes; check that its USD payloads loaded successfully")
    print(f"Loaded {mesh_count} meshes for camera calibration")

    render_product_paths = (
        "/Render/Pinhole",
        "/Render/Fisheye",
        "/Render/OmniDirectionalStereo",
    )
    products = None
    # Allow texture streaming and real-time path-tracing accumulation to warm up.
    for _ in range(40):
        products = renderer.step(
            render_products=set(render_product_paths),
            delta_time=1.0 / 60.0,
            ordinal=ordinal,
        )

    # Verify every calibrated camera produced output before accessing its first frame.
    if not all(products[path].frames for path in render_product_paths):
        raise RuntimeError("Not all calibrated cameras produced an image")

    images = {}
    for render_product_path in render_product_paths:
        frame = products[render_product_path].frames[0]
        mapped = frame.render_vars["/Render/LdrColor"].map(device=ovrtx.Device.CPU)
        images[render_product_path] = np.from_dlpack(mapped).copy()
        del mapped, frame
    # [/snippet:doc-render-calibrated-cameras]

    if not args.no_rr:
        import rerun as rr
        import rerun.blueprint as rrb

        rr.init("ovrtx_camera_lens_calibration", spawn=args.rrd is None)
        if args.rrd:
            rr.save(str(args.rrd))
        rr.send_blueprint(
            rrb.Blueprint(
                rrb.Horizontal(
                    rrb.Spatial2DView(origin="pinhole", name="OpenCV Pinhole"),
                    rrb.Spatial2DView(origin="fisheye", name="OpenCV Fisheye"),
                    rrb.Spatial2DView(
                        origin="omnidirectional-stereo", name="Omni-Directional Stereo"
                    ),
                )
            )
        )
        rr.log("pinhole", rr.Image(images["/Render/Pinhole"]))
        rr.log("fisheye", rr.Image(images["/Render/Fisheye"]))
        rr.log(
            "omnidirectional-stereo",
            rr.Image(images["/Render/OmniDirectionalStereo"]),
        )

    if args.png:
        args.png.parent.mkdir(parents=True, exist_ok=True)
        named_images = {
            "pinhole": images["/Render/Pinhole"],
            "fisheye": images["/Render/Fisheye"],
            "omnidirectional-stereo": images["/Render/OmniDirectionalStereo"],
        }
        for name, pixels in named_images.items():
            path = args.png.with_name(f"{args.png.stem}-{name}{args.png.suffix}")
            Image.fromarray(pixels).save(path)

        contact_sheet = Image.new(
            "RGBA",
            (
                sum(pixels.shape[1] for pixels in named_images.values()),
                max(pixels.shape[0] for pixels in named_images.values()),
            ),
            (0, 0, 0, 255),
        )
        x = 0
        for pixels in named_images.values():
            image = Image.fromarray(pixels)
            contact_sheet.paste(image, (x, (contact_sheet.height - image.height) // 2))
            x += image.width
        contact_sheet.save(args.png)

    del products
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


if __name__ == "__main__":
    main()
