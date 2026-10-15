#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Render pinhole and OpenCV-calibrated projector lights with ovrtx."""

import argparse
import gc
from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from generate_direction_texture import generate_direction_texture
from PIL import Image, ImageDraw, ImageFont

EXAMPLE_DIR = Path(__file__).parent.resolve()
PUBLIC_ROOT = EXAMPLE_DIR.parents[2]
DOC_DATA = PUBLIC_ROOT / "tests/docs/data"
BASE_SCENE = (DOC_DATA / "ovrtx-light-test-rect.usda").resolve()
COLOR_TEXTURE = (DOC_DATA / "chelsea.png").resolve()
RENDER_PRODUCT = (
    "/Render/OmniverseKit/HydraTextures/omni_kit_widget_viewport_ViewportTexture_0"
)
LDR_COLOR = "/Render/Vars/LdrColor"
PANEL_SIZE = 512


def build_projector_layer(direction_texture: Path | None) -> str:
    direction_attribute = ""
    if direction_texture is not None:
        direction_attribute = (
            "        asset projector:directionTexture:file = "
            f"@{direction_texture.as_posix()}@\n"
        )

    return f"""#usda 1.0
(
    subLayers = [@{BASE_SCENE.as_posix()}@]
)

over "World" {{
    over RectLight "RectLight" {{
        bool isProjector = true
        float inputs:width = 1.5
        float inputs:height = 1
        float inputs:intensity = 10000
        asset inputs:texture:file = @{COLOR_TEXTURE.as_posix()}@
        bool visibleInPrimaryRay = false
        double3 xformOp:rotateXYZ = (0, 0, 0)
        double3 xformOp:translate = (0, 50, 100)
{direction_attribute}    }}
}}

over "Render" {{
    over "OmniverseKit" {{
        over "HydraTextures" {{
            over "omni_kit_widget_viewport_ViewportTexture_0" {{
                uniform int2 resolution = ({PANEL_SIZE}, {PANEL_SIZE})
            }}
        }}
    }}
}}
"""


def render_panel(label: str, direction_texture: Path | None, warmup_frames: int):
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage(f"ovrtx.example.projector-light-calibration.{label}")
    renderer.attach_ovstage(stage)
    try:
        layer = build_projector_layer(direction_texture)
        ovstage.population.open_usd_from_string(stage, layer, ordinal=1)
        stage.advance_write_floor(1, ovstage.Scope.ALL).wait()

        products = None
        for _ in range(warmup_frames):
            products = renderer.step(
                render_products={RENDER_PRODUCT},
                delta_time=1.0 / 60.0,
                ordinal=1,
            )

        frame = products[RENDER_PRODUCT].frames[-1]
        mapped = frame.render_vars[LDR_COLOR].map(device=ovrtx.Device.CPU)
        view = np.from_dlpack(mapped)
        pixels = view.copy()
        del view
        mapped.unmap()
        image = Image.fromarray(pixels[..., :3])
        del mapped, frame, products, pixels
        gc.collect()
        return image
    finally:
        renderer.detach_ovstage()
        stage.destroy()
        renderer.destroy()


def make_contact_sheet(images: tuple[tuple[str, Image.Image], ...]) -> Image.Image:
    label_height = 48
    sheet = Image.new(
        "RGB", (PANEL_SIZE * len(images), PANEL_SIZE + label_height), "black"
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(str(DOC_DATA / "fonts/DejaVuSans-Bold.ttf"), 24)
    for index, (label, image) in enumerate(images):
        x = index * PANEL_SIZE
        draw.text((x + 16, 8), label, fill="white", font=font)
        sheet.paste(image, (x, label_height))
    return sheet


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render pinhole and OpenCV-calibrated projector lights"
    )
    parser.add_argument("--png", type=Path, help="Write the comparison PNG")
    parser.add_argument("--rrd", type=Path, help="Write a Rerun recording")
    parser.add_argument("--no-rr", action="store_true", help="Do not log to Rerun")
    parser.add_argument("--texture-size", type=int, default=1024)
    parser.add_argument("--warmup-frames", type=int, default=64)
    args = parser.parse_args()
    if args.no_rr and args.rrd:
        parser.error("--rrd cannot be combined with --no-rr")
    if args.no_rr and args.png is None:
        parser.error("--png is required with --no-rr")
    if args.texture_size < 2:
        parser.error("--texture-size must be at least 2")
    if args.warmup_frames < 1:
        parser.error("--warmup-frames must be at least 1")

    output_dir = args.png.parent if args.png else EXAMPLE_DIR / "_output"
    direction_texture = output_dir / "projector-opencv-direction.exr"

    # [snippet:doc-projector-generate-and-render]
    generate_direction_texture(direction_texture, args.texture_size)
    pinhole = render_panel("pinhole", None, args.warmup_frames)
    calibrated = render_panel(
        "opencv-calibrated", direction_texture, args.warmup_frames
    )
    # [/snippet:doc-projector-generate-and-render]

    images = (("Pinhole", pinhole), ("OpenCV calibration", calibrated))
    comparison = make_contact_sheet(images)
    if args.png:
        args.png.parent.mkdir(parents=True, exist_ok=True)
        comparison.save(args.png)

    if not args.no_rr:
        import rerun as rr
        import rerun.blueprint as rrb

        rr.init("ovrtx_projector_light_calibration", spawn=args.rrd is None)
        if args.rrd:
            args.rrd.parent.mkdir(parents=True, exist_ok=True)
            rr.save(str(args.rrd))
        rr.send_blueprint(
            rrb.Blueprint(
                rrb.Horizontal(
                    rrb.Spatial2DView(origin="pinhole", name="Pinhole"),
                    rrb.Spatial2DView(
                        origin="opencv-calibrated", name="OpenCV calibration"
                    ),
                )
            )
        )
        rr.log("pinhole", rr.Image(np.asarray(pinhole)))
        rr.log("opencv-calibrated", rr.Image(np.asarray(calibrated)))


if __name__ == "__main__":
    main()
