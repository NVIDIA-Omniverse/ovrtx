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

"""Render the RT2 G-buffer and heat map debug views and log them together to Rerun."""

import argparse
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import ovrtx
import ovstage

EXAMPLE_DIR = Path(__file__).resolve().parent
DEFAULT_USD = Path("../semantic-segmentation/ovrtx-robot-lineup.usda")

DEBUG_VIEWS = (
    ("Depth", "depth"),
    ("World Position", "worldPosition"),
    ("Barycentrics", "barycentrics"),
    ("Texture Coordinates 0", "texcoord0"),
    ("Texture Coordinates 1", "texcoord1"),
    ("Triangle Normal", "triangleNormal"),
    ("Interpolated Normal", "normal"),
    ("Tangent U", "tangentu"),
    ("Tangent V", "tangentv"),
    ("Instance ID", "instanceId"),
    ("Stable ID", "stableId"),
    ("Non-Visual Material ID", "nonVisualMaterialId"),
    ("3D Motion Vectors", "targetMotion"),
    ("3D Motion Vector Arrows", "targetMotionArrows"),
    ("Wireframe", "wire"),
    ("Any-Hit Calls", "anyHitCountHeatMap"),
)


def _resolve_scene_path(path: Path) -> Path:
    expanded = path.expanduser()
    if expanded.is_absolute():
        return expanded.resolve()
    return (EXAMPLE_DIR / expanded).resolve()


def _scene_asset_path(path: Path) -> Path:
    expanded = path.expanduser()
    if expanded.is_absolute():
        return expanded.resolve()
    return Path(os.path.relpath(_resolve_scene_path(expanded), Path.cwd()))


def _usd_asset_path(path: Path) -> str:
    asset_path = path.as_posix()
    if "@" in asset_path:
        raise ValueError(
            f"USD asset paths containing '@' are not supported: {asset_path}"
        )
    return asset_path


# [snippet:doc-author-gbuffer-debug-views]
def build_render_layer_usda(scene_path: Path, resolution: tuple[int, int]) -> str:
    """Compose the scene with one two-output RenderProduct per debug view."""
    width, height = resolution
    render_products = []
    for _, selector in DEBUG_VIEWS:
        # Count calls in the RTPT Path Tracing kernel; leave display controls at their defaults.
        heat_map_pass = "\n        int omni:rtx:debug:view:heatMapPass = 2" if selector == "anyHitCountHeatMap" else ""
        render_products.append(
            f'''    def RenderProduct "{selector}"
    {{
        rel camera = </World/Camera>
        int2 resolution = ({width}, {height})
        token omni:rtx:rendermode = "RealTimePathTracing"
        string omni:rtx:debug:view:target = "{selector}"{heat_map_pass}
        rel orderedVars = [<LdrColor>, <HdrColor>]

        def RenderVar "LdrColor"
        {{
            string sourceName = "LdrColor"
        }}

        def RenderVar "HdrColor"
        {{
            string sourceName = "HdrColor"
        }}
    }}'''
        )

    return f"""#usda 1.0
(
    subLayers = [
        @{_usd_asset_path(scene_path)}@
    ]
)

def "Render"
{{
{chr(10).join(render_products)}
}}
"""


# [/snippet:doc-author-gbuffer-debug-views]


def _map_hdr_debug_view(frame, render_product_path: str) -> np.ndarray:
    mapped = frame.render_vars[f"{render_product_path}/HdrColor"].map(
        device=ovrtx.Device.CPU
    )
    view = np.from_dlpack(mapped)
    pixels = view.copy()
    del view, mapped
    return pixels


def _to_uint8(pixels: np.ndarray) -> np.ndarray:
    """Convert the display-encoded debug view directly to 8-bit RGB."""
    rgb = np.nan_to_num(
        np.asarray(pixels[..., :3], dtype=np.float32),
        nan=0.0,
        posinf=1.0,
        neginf=0.0,
    )
    return (np.clip(rgb, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def _build_blueprint(rrb, grid_columns: int):
    views = [
        rrb.Spatial2DView(origin=f"debug_views/{selector}", name=label)
        for label, selector in DEBUG_VIEWS
    ]
    return rrb.Blueprint(
        rrb.Grid(*views, grid_columns=grid_columns, name="RT2 Debug Views"),
        collapse_panels=True,
    )


def _log_to_rerun(
    images: dict[str, np.ndarray], rrd_path: Path | None, grid_columns: int
) -> None:
    import rerun as rr
    import rerun.blueprint as rrb

    blueprint = _build_blueprint(rrb, grid_columns)
    rr.init("ovrtx_debug_views", spawn=rrd_path is None, default_blueprint=blueprint)
    if rrd_path:
        rrd_path.parent.mkdir(parents=True, exist_ok=True)
        rr.save(str(rrd_path))
    rr.send_blueprint(blueprint, make_active=True, make_default=True)

    # Rendering is complete before anything is logged, so all views appear together.
    for _, selector in DEBUG_VIEWS:
        rr.log(f"debug_views/{selector}", rr.Image(images[selector]))


def _save_contact_sheet(
    images: dict[str, np.ndarray], output_path: Path, grid_columns: int
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = (len(DEBUG_VIEWS) + grid_columns - 1) // grid_columns
    image_height, image_width = next(iter(images.values())).shape[:2]
    label_height = 28
    sheet = Image.new(
        "RGB",
        (grid_columns * image_width, rows * (image_height + label_height)),
        "black",
    )
    draw = ImageDraw.Draw(sheet)

    for index, (label, selector) in enumerate(DEBUG_VIEWS):
        column = index % grid_columns
        row = index // grid_columns
        x = column * image_width
        y = row * (image_height + label_height)
        sheet.paste(Image.fromarray(images[selector]), (x, y))
        draw.text((x + 8, y + image_height + 7), f"{label} ({selector})", fill="white")

        individual_path = output_path.with_name(
            f"{output_path.stem}-{selector}{output_path.suffix}"
        )
        Image.fromarray(images[selector]).save(individual_path)

    sheet.save(output_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--usd",
        type=Path,
        default=DEFAULT_USD,
        help=f"Scene USD (default: {DEFAULT_USD})",
    )
    parser.add_argument(
        "--resolution",
        type=int,
        nargs=2,
        metavar=("WIDTH", "HEIGHT"),
        default=(640, 360),
        help="Render resolution (default: 640 360)",
    )
    parser.add_argument(
        "--warmup-frames",
        type=int,
        default=2,
        help="Warmup frames rendered for each debug view (default: 2)",
    )
    parser.add_argument(
        "--step-dt", type=float, default=1.0 / 60.0, help="Step delta in seconds"
    )
    parser.add_argument(
        "--grid-columns", type=int, default=3, help="Rerun/contact-sheet columns"
    )
    parser.add_argument(
        "--rrd", type=Path, help="Write a Rerun recording instead of opening a viewer"
    )
    parser.add_argument(
        "--png", type=Path, help="Write a contact sheet and individual debug-view PNGs"
    )
    parser.add_argument(
        "--no-rr", action="store_true", help="Do not log images to Rerun"
    )
    args = parser.parse_args()
    if args.no_rr and args.rrd:
        parser.error("--no-rr and --rrd cannot be used together")
    return args


def main() -> None:
    args = parse_args()
    scene_path = _resolve_scene_path(args.usd)
    if not scene_path.exists():
        raise SystemExit(f"USD file not found: {scene_path}")

    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.debug-views")
    renderer.attach_ovstage(stage)

    ordinal = 1
    ovstage.population.open_usd_from_string(
        stage,
        build_render_layer_usda(_scene_asset_path(args.usd), tuple(args.resolution)),
        ordinal=ordinal,
    )
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    # [snippet:doc-render-gbuffer-debug-views]
    images = {}
    for label, selector in DEBUG_VIEWS:
        render_product_path = f"/Render/{selector}"
        print(f"Rendering {label} ({selector})...")

        products = None
        # Each RenderProduct has independent temporal state, so warm it up before capture.
        for _ in range(max(args.warmup_frames, 0) + 1):
            products = renderer.step(
                render_products={render_product_path},
                delta_time=args.step_dt,
                ordinal=ordinal,
            )

        if not products[render_product_path].frames:
            raise RuntimeError(f"{render_product_path} did not produce an image")

        frame = products[render_product_path].frames[0]
        # Debug views already contain display colors; copy them without HDR tonemapping.
        pixels = _map_hdr_debug_view(frame, render_product_path)
        images[selector] = _to_uint8(pixels)
        del frame, products

    # Capture motion views after all static views so movement cannot change their images.
    motion_selectors = ("targetMotion", "targetMotionArrows")
    robot_paths = [
        "/World/GR1T2_fourier_hand_6dof", "/World/spot", "/World/forklift_c", "/World/forklift_b",
        "/World/carter_v1", "/World/jetbot", "/World/kaya",
    ]
    velocities = np.array(
        [(3, 0, 0), (-3, 0, 0), (2, 0, 1), (-2, 0, 1), (3, 0, 1), (-3, 0, 1), (2, 0, 1)],
        dtype=np.float64,
    )
    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(robot_paths)
        with stage.query_from_path_list(path_list) as query:
            attribute = paths.intern_token("omni:xform")
            transforms = np.full((len(robot_paths), 4, 4), np.nan, dtype=np.float64)
            # Preserve orientation and scale, including the centimetre-scaled forklift payload.
            with stage.read_attributes(query, [attribute], ovstage.OrdinalRange.latest(ordinal)) as read:
                while (group := read.fetch_next()) is not None:
                    column = group.columns[0]
                    values = np.from_dlpack(column.dlpack(0)).reshape(-1, 4, 4)
                    for index in range(group.prim_count):
                        transforms[group.prim_index(index)] = values[column.data_row_index(index)]
                    del values
                    stage.release_group(group)
            if not np.all(np.isfinite(transforms)):
                raise RuntimeError("Motion views require transforms for all seven lineup robots")

            matrix_dtype = ovstage.numpy_to_dldatatype(transforms.dtype, lanes=16)
            for selector in motion_selectors:
                render_product_path = f"/Render/{selector}"
                # Refresh previous-frame transforms after the other views' independent warmups.
                for _ in range(2):
                    products = renderer.step(
                        render_products={render_product_path}, delta_time=args.step_dt, ordinal=ordinal
                    )
                    del products

                for motion_step in range(10):
                    # Alternate small offsets to keep robots in view while providing motion every frame.
                    direction = 1.0 if motion_step % 2 == 0 else -1.0
                    transforms[:, 3, :3] += direction * velocities * args.step_dt
                    ordinal += 1
                    tensor = ovstage.make_dltensor(transforms, dtype=matrix_dtype, shape=[len(robot_paths)], ndim=1)
                    stage.write_attribute(query, attribute, ordinal=ordinal, tensors=tensor, is_array=False).wait()
                    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
                    products = renderer.step(
                        render_products={render_product_path}, delta_time=args.step_dt, ordinal=ordinal
                    )
                    if motion_step < 9:
                        del products

                if not products[render_product_path].frames:
                    raise RuntimeError(f"{render_product_path} did not produce a moving frame")
                frame = products[render_product_path].frames[0]
                pixels = _map_hdr_debug_view(frame, render_product_path)
                display = _to_uint8(pixels)
                changed_pixels = np.count_nonzero(np.any(display != images[selector], axis=-1))
                print(f"Moving {selector}: {changed_pixels} pixels differ from static capture", flush=True)
                images[selector] = display
                del frame, products
        paths.destroy_path_list(path_list)
    # [/snippet:doc-render-gbuffer-debug-views]

    grid_columns = max(args.grid_columns, 1)
    if not args.no_rr:
        _log_to_rerun(images, args.rrd, grid_columns)
    if args.png:
        _save_contact_sheet(images, args.png, grid_columns)

    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


if __name__ == "__main__":
    main()
