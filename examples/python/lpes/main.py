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

"""Render HdrColor plus diffuse and glossy reflection LPEs and log them to Rerun."""

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import ovrtx
import ovstage

EXAMPLE_DIR = Path(__file__).resolve().parent


def build_render_layer_usda(
    scene_path: Path, resolution: tuple[int, int], samples_per_pixel: int
) -> str:
    layer = (EXAMPLE_DIR / "lpe-layer.usda").read_text()
    layer = layer.replace("@./ovrtx-robot-lineup.usda@", f"@{scene_path.as_posix()}@")
    layer = layer.replace(
        "int2 resolution = (1920, 1080)", f"int2 resolution = {resolution}"
    )
    return layer.replace(
        "uint omni:rtx:pt:samplesPerPixel = 128",
        f"uint omni:rtx:pt:samplesPerPixel = {samples_per_pixel}",
    )


def _linear_rec709_to_srgb_uint8(values: np.ndarray) -> np.ndarray:
    linear = np.nan_to_num(np.asarray(values, dtype=np.float32), copy=False)
    linear_rgb = np.clip(linear[..., :3], 0.0, 1.0)
    srgb = np.where(
        linear_rgb <= 0.0031308,
        12.92 * linear_rgb,
        1.055 * np.power(linear_rgb, 1.0 / 2.4) - 0.055,
    )
    return (np.clip(srgb, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def _map_render_var(render_var) -> np.ndarray:
    mapped = render_var.map(device=ovrtx.Device.CPU)
    view = np.from_dlpack(mapped)
    pixels = view.copy()
    del view
    mapped.unmap()
    del mapped
    return pixels


# [snippet:doc-read-lpe-outputs]
def read_lpe_outputs(frame) -> dict[str, np.ndarray]:
    images = {}
    for render_var_path, render_var in frame.render_vars.items():
        # Copy before unmapping so each image remains valid after this iteration.
        pixels = _map_render_var(render_var)
        if pixels.dtype == np.uint8:
            image = np.ascontiguousarray(pixels[..., :3])
        elif np.issubdtype(pixels.dtype, np.floating):
            # HdrColor and LPE outputs are linear Rec.709 floating-point images.
            image = _linear_rec709_to_srgb_uint8(pixels)
        else:
            raise TypeError(
                f"Unsupported image dtype for {render_var_path}: {pixels.dtype}"
            )

        print(
            f"  {render_var_path}: shape={pixels.shape}, dtype={pixels.dtype}",
            file=sys.stderr,
        )
        images[render_var_path] = image
    return images


# [/snippet:doc-read-lpe-outputs]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--usd",
        type=Path,
        default=Path("ovrtx-robot-lineup.usda"),
        help="Scene USD to sublayer",
    )
    parser.add_argument(
        "--resolution",
        type=int,
        nargs=2,
        metavar=("WIDTH", "HEIGHT"),
        default=(1920, 1080),
    )
    parser.add_argument(
        "--spp", type=int, default=128, help="Path Tracing samples per pixel"
    )
    parser.add_argument("--step-dt", type=float, default=1.0 / 60.0)
    parser.add_argument(
        "--rrd", type=Path, help="Write a Rerun recording instead of opening a viewer"
    )
    parser.add_argument(
        "--png", type=Path, help="Write an output contact sheet and individual PNGs"
    )
    parser.add_argument(
        "--no-rr", action="store_true", help="Do not log images to Rerun"
    )
    parser.add_argument("--no-spawn", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.no_rr and args.rrd:
        parser.error("--rrd cannot be combined with --no-rr")
    return args


def main() -> None:
    args = parse_args()
    scene_path = args.usd.expanduser()
    if not scene_path.is_absolute():
        scene_path = EXAMPLE_DIR / scene_path
    scene_path = scene_path.resolve()
    if not scene_path.exists():
        raise SystemExit(f"USD file not found: {scene_path}")

    # [snippet:doc-lpe-create-renderer]
    print(
        "Creating renderer. First launch can take time while shaders compile...",
        file=sys.stderr,
    )
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.lpes")
    renderer.attach_ovstage(stage)
    # [/snippet:doc-lpe-create-renderer]

    # [snippet:doc-lpe-load-scene]
    ordinal = 1
    ovstage.population.open_usd_from_string(
        stage,
        build_render_layer_usda(scene_path, tuple(args.resolution), args.spp),
        ordinal=ordinal,
    )
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    # [/snippet:doc-lpe-load-scene]

    # [snippet:doc-lpe-step]
    products = renderer.step(
        render_products={"/Render/Camera"}, delta_time=args.step_dt, ordinal=ordinal
    )
    # [/snippet:doc-lpe-step]

    images = {}
    for product in products.values():
        for frame in product.frames:
            images.update(read_lpe_outputs(frame))

    if not images:
        raise RuntimeError("The LPE RenderProduct produced no images")

    if not args.no_rr:
        try:
            import rerun as rr
        except ImportError as exc:
            raise SystemExit(
                "rerun-sdk is required. Run this example with `uv run main.py`."
            ) from exc

        # [snippet:doc-lpe-initialize-rerun]
        rr.init("ovrtx_lpes", spawn=args.rrd is None and not args.no_spawn)
        if args.rrd:
            args.rrd.parent.mkdir(parents=True, exist_ok=True)
            rr.save(str(args.rrd))
        # [/snippet:doc-lpe-initialize-rerun]

        for render_var_path, image in images.items():
            rr.log(f"render/{render_var_path.removeprefix('/')}", rr.Image(image))

    if args.png:
        args.png.parent.mkdir(parents=True, exist_ok=True)
        labels = {
            "/Render/Camera/HdrColor": "Beauty (HdrColor)",
            "/Render/Camera/DiffuseReflection": "Diffuse reflection",
            "/Render/Camera/GlossyReflection": "Glossy reflection",
            "/Render/Camera/GlossyTransmission": "Glossy transmission",
            "/Render/Camera/Caustics": "Caustics",
        }
        ordered_images = [(path, images[path]) for path in labels if path in images]
        if not ordered_images:
            raise RuntimeError("None of the expected LPE example outputs were produced")

        image_height, image_width = ordered_images[0][1].shape[:2]
        title_height = max(40, image_height // 9)
        columns = 3
        rows = (len(ordered_images) + columns - 1) // columns
        contact_sheet = Image.new(
            "RGB",
            (columns * image_width, rows * (image_height + title_height)),
            "#18212b",
        )
        draw = ImageDraw.Draw(contact_sheet)
        font = ImageFont.load_default(size=max(22, image_height // 13))
        for index, (render_var_path, pixels) in enumerate(ordered_images):
            row, column = divmod(index, columns)
            items_in_row = min(columns, len(ordered_images) - row * columns)
            row_offset = (columns - items_in_row) * image_width // 2
            x = row_offset + column * image_width
            y = row * (image_height + title_height)
            draw.text(
                (x + image_width // 2, y + title_height // 2),
                labels[render_var_path],
                font=font,
                fill="white",
                anchor="mm",
            )
            contact_sheet.paste(Image.fromarray(pixels), (x, y + title_height))
            individual_path = args.png.with_name(
                f"{args.png.stem}-{render_var_path.rsplit('/', 1)[-1]}{args.png.suffix}"
            )
            Image.fromarray(pixels).save(individual_path)
        contact_sheet.save(args.png)

    print(f"Produced {len(images)} images.", file=sys.stderr)
    del frame, product, products
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


if __name__ == "__main__":
    main()
