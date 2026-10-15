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

"""Keep four sensors active while each produces outputs on its own schedule."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import ovrtx
import ovstage


def project_points(points: np.ndarray, camera_to_world: np.ndarray, focal_length: float,
                   horizontal_aperture: float, near_clip: float = 0.01, far_clip: float = 10000,
                   width: int = 320, height: int = 240):
    """Project world-space metre coordinates through a USD perspective camera.

    camera_to_world uses USD row vectors, with its translation already in metres.
    Horizontal aperture determines the field of view; pixels are square.
    """
    homogeneous = np.column_stack((points, np.ones(len(points))))
    camera_points = homogeneous @ np.linalg.inv(camera_to_world)
    # USD cameras look down -Z, with +Y pointing up.
    depth = -camera_points[:, 2]
    valid = np.isfinite(camera_points).all(axis=1) & (depth >= near_clip) & (depth <= far_clip)
    camera_points, depth = camera_points[valid], depth[valid]
    focal_pixels = width * focal_length / horizontal_aperture
    pixels = np.column_stack((
        width / 2 + focal_pixels * camera_points[:, 0] / depth,
        height / 2 - focal_pixels * camera_points[:, 1] / depth,
    ))
    inside = (pixels[:, 0] >= 0) & (pixels[:, 0] < width) & (pixels[:, 1] >= 0) & (pixels[:, 1] < height)
    return pixels[inside], depth[inside]


def filmstrip_camera(stage, ordinal):
    """Read the fixed rolling-shutter camera after rendering computes its pose."""
    values = []
    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/World/Camera20"])
        try:
            with stage.query_from_path_list(path_list) as query:
                for name in ("omni:fabric:worldMatrix", "focalLength", "horizontalAperture", "clippingRange"):
                    with stage.read_attributes(query, [paths.intern_token(name)],
                                               ovstage.OrdinalRange.latest(ordinal)) as read:
                        read.wait()
                        group = read.fetch_next()
                        if group is None:
                            raise RuntimeError(f"Missing camera attribute: {name}")
                        try:
                            values.append(np.from_dlpack(group.dlpack(0)).copy())
                        finally:
                            stage.release_group(group)
        finally:
            paths.destroy_path_list(path_list)
    matrix = values[0].reshape(4, 4)
    # multi_rate.usda uses centimetres; PointCloud WORLD coordinates use metres.
    matrix[3, :3] *= 0.01
    near_clip, far_clip = values[3].ravel() * 0.01
    return matrix, float(values[1].item()), float(values[2].item()), float(near_clip), float(far_clip)


def save_filmstrip(path: Path, images: dict, clouds: dict, camera: tuple,
                   steps: int, partial_outputs: bool) -> None:
    """Plot actual camera and lidar deliveries during the first eight steps."""
    columns = min(steps, 8)
    figure = Image.new("RGB", (240 + 336 * max(columns, 4), 1360), "white")
    draw = ImageDraw.Draw(figure)
    title_font = ImageFont.load_default(size=56)
    label_font = ImageFont.load_default(size=44)
    draw.text((24, 20), "Camera and lidar output delivery", fill="#172b4d", font=title_font)
    draw.text(
        (24, 76),
        f"Simulation: 40 Hz (25 ms per step)   |   partialOutputs = {str(partial_outputs).lower()}",
        fill="#394b61", font=label_font,
    )
    for step in range(1, columns + 1):
        x = 240 + (step - 1) * 336
        draw.text((x + 160, 150), f"{step / 40:.3f} s", fill="#172b4d", font=label_font, anchor="mm")
    for row, (sensor, label) in enumerate((("Camera10", "Global\nshutter"), ("Camera20", "Rolling\nshutter"),
                                         ("Lidar40", "Lidar"), ("Lidar20", "Lidar"))):
        y = 180 + row * 280
        draw.text((24, y + 56), ("10 Hz", "20 Hz", "40 Hz", "20 Hz")[row], fill="#172b4d", font=title_font)
        draw.text((24, y + 136), label, fill="#394b61", font=label_font)
        for step in range(1, columns + 1):
            x = 240 + (step - 1) * 336
            key = (f"/Render/{sensor}", step)
            pixels = images.get(key)
            points = clouds.get(key)
            if row < 2 and pixels is not None:
                figure.paste(Image.fromarray(pixels[..., :3]), (x, y))
            elif row >= 2 and points is not None:
                view = Image.new("RGB", (320, 240), "#101c2a")
                point_draw = ImageDraw.Draw(view)
                projected, depth = project_points(points, *camera)
                # Paint farther returns first. Each cell uses only this delivery,
                # without accumulating points or reusing an earlier scan.
                for index in np.argsort(depth)[::-1]:
                    px, py = projected[index]
                    point_draw.ellipse((px - 1, py - 1, px + 1, py + 1), fill="#5eead4")
                point_draw.rectangle((0, 182, 320, 240), fill="#101c2a")
                point_draw.text((6, 183), f"{len(points):,} returns\n{len(projected):,} in view",
                                fill="white", font=ImageFont.load_default(size=26), spacing=0)
                figure.paste(view, (x, y))
            else:
                draw.rectangle((x, y, x + 319, y + 239), fill="#f0f3f6", outline="#d7dfe8", width=2)
    draw.text(
        (240, 1300), "Blank: no image or nonempty cloud. Lidar: camera viewpoint. Times: step end.",
        fill="#394b61", font=label_font,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.save(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--partial-outputs", action="store_true", help="Also deliver incomplete scans and exposures")
    parser.add_argument("--steps", type=int, default=40, help="Number of 1/40-second steps (default: 40)")
    parser.add_argument("--no-rr", action="store_true", help="Do not open Rerun")
    parser.add_argument("--rrd", type=Path, help="Save a Rerun recording instead of opening a viewer")
    parser.add_argument("--png", type=Path, help="Save the last delivered images side by side (10 Hz, then 20 Hz)")
    parser.add_argument("--filmstrip", type=Path, help="Save camera and lidar delivery timelines for the first eight steps")
    parser.add_argument("--report", type=Path, help="Save per-output timing and point counts as JSON")
    args = parser.parse_args()
    if args.steps < 1:
        parser.error("--steps must be positive")
    if args.rrd and args.no_rr:
        parser.error("--rrd cannot be combined with --no-rr")

    rr = None
    if not args.no_rr:
        import rerun as rr
        import rerun.blueprint as rrb

        rr.init("ovrtx_multi_rate_sensors", spawn=args.rrd is None)
        if args.rrd:
            args.rrd.parent.mkdir(parents=True, exist_ok=True)
            rr.save(str(args.rrd))
        rr.send_blueprint(
            rrb.Blueprint(
                rrb.Grid(
                    rrb.Spatial2DView(origin="/Render/Camera10", name="Global shutter, 10 Hz"),
                    rrb.Spatial2DView(origin="/Render/Camera20", name="Rolling shutter, 20 Hz"),
                    rrb.Spatial3DView(origin="/Render/Lidar40", name="Lidar, 40 Hz"),
                    rrb.Spatial3DView(origin="/Render/Lidar20", name="Lidar, 20 Hz"),
                    grid_columns=2,
                )
            )
        )

    renderer = ovrtx.Renderer(ovrtx.RendererConfig(motion_bvh=ovrtx.MotionBvh.ENABLE))
    stage = ovstage.Stage("ovrtx.example.multi-rate-sensors")
    renderer.attach_ovstage(stage)
    events = []
    images = {}
    filmstrip_images = {}
    filmstrip_clouds = {}
    try:
        ordinal = 1
        ovstage.population.open_usd(stage, str(Path(__file__).with_name("multi_rate.usda")), ordinal=ordinal)
        stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

        # [snippet:doc-multi-rate-partial-outputs]
        # Set the delivery policy on all four sensors before the first step.
        # False returns completed captures only; True also allows intermediate outputs.
        ordinal += 1
        with ovstage.PathDictionary(stage) as paths:
            path_list = paths.create_path_list_from_strings(
                [
                    "/World/Lidar40",
                    "/World/Lidar20",
                    "/World/Camera10",
                    "/World/Camera20",
                ]
            )
            with stage.query_from_path_list(path_list) as query:
                stage.write_attribute(
                    query,
                    "omni:sensor:Core:partialOutputs",
                    ordinal=ordinal,
                    tensors=np.full(4, args.partial_outputs, dtype=np.bool_),
                    is_array=False,
                ).wait()
            paths.destroy_path_list(path_list)
        stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
        # [/snippet:doc-multi-rate-partial-outputs]

        for step_index in range(args.steps):
            # [snippet:doc-multi-rate-step]
            # Update scene animation to the next 25 ms simulation time.
            ordinal += 1
            simulation_time = (step_index + 1) / 40
            ovstage.population.update_from_usd_time(stage, ordinal, simulation_time)
            # Make the scene updates available to the renderer.
            stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
            # Advance every sensor by 25 ms, including those with no output this step.
            # Capture rates and partialOutputs determine when outputs are returned.
            # Keep all four sensors requested to avoid teardown and reinitialization.
            products = renderer.step(
                render_products={
                    "/Render/Lidar40",
                    "/Render/Lidar20",
                    "/Render/Camera10",
                    "/Render/Camera20",
                },
                delta_time=1 / 40,
                ordinal=ordinal,
            )
            # [/snippet:doc-multi-rate-step]
            if rr is not None:
                rr.set_time("simulation", duration=products.simulation_end_time)

            delivered = []
            # [snippet:doc-multi-rate-read-outputs]
            # Iterate what was returned. A product can be absent or have no frames.
            for product_path, product in products.items():
                for frame in product.frames:
                    for render_var in frame.render_vars.values():
                        with render_var.map(device=ovrtx.Device.CPU) as mapped:
                            if render_var.source_name == "PointCloud":
                                count = int(np.from_dlpack(mapped["Counts"])[0])
                                if count == 0:
                                    # No points this step; keep the lidar active.
                                    continue
                                points = np.from_dlpack(mapped["Coordinates"])[:, :count].T
                                if rr is not None:
                                    rr.log(product_path, rr.Points3D(points, radii=0.02))
                                del points
                            else:
                                pixels = np.from_dlpack(mapped)
                                if rr is not None:
                                    rr.log(product_path, rr.Image(pixels))
                            # [/snippet:doc-multi-rate-read-outputs]

                            event = {
                                "product": product_path,
                                "step": step_index + 1,
                                "simulation_end_time": products.simulation_end_time,
                                "capture_start_time": frame.start_time,
                                "capture_end_time": frame.end_time,
                            }
                            for name in ("timestampNs", "frameId", "frameStartTimeStampNs", "frameEndTimeStampNs"):
                                if name in mapped.params:
                                    event[name] = int(np.from_dlpack(mapped.params[name]).item())
                            if render_var.source_name == "PointCloud":
                                if args.filmstrip and step_index < 8:
                                    filmstrip_clouds[(product_path, step_index + 1)] = (
                                        np.from_dlpack(mapped["Coordinates"])[:, :count].T.copy()
                                    )
                                event["point_count"] = count
                                offsets = np.from_dlpack(mapped["TimeOffsetNs"])[:count]
                                event["min_point_offset_ns"] = int(offsets.min())
                                event["max_point_offset_ns"] = int(offsets.max())
                                del offsets
                            else:
                                images[product_path] = pixels.copy()
                                if args.filmstrip and step_index < 8:
                                    filmstrip_images[(product_path, step_index + 1)] = images[product_path]
                                del pixels
                            events.append(event)
                            delivered.append(product_path.rsplit("/", 1)[-1])
                        del mapped
            print(
                f"step={step_index + 1:02d} t={products.simulation_end_time:.3f}s: "
                f"{', '.join(sorted(delivered)) or 'no outputs'}",
                flush=True,
            )
            del products

        if args.png:
            if not all(path in images for path in ("/Render/Camera10", "/Render/Camera20")):
                raise RuntimeError("No image from both cameras; run more simulation steps")
            args.png.parent.mkdir(parents=True, exist_ok=True)
            comparison = np.concatenate((images["/Render/Camera10"], images["/Render/Camera20"]), axis=1)
            Image.fromarray(comparison[..., :3]).save(args.png)
        camera_projection = None
        if args.filmstrip:
            camera_projection = filmstrip_camera(stage, ordinal)
            save_filmstrip(args.filmstrip, filmstrip_images, filmstrip_clouds,
                           camera_projection, args.steps, args.partial_outputs)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(
                json.dumps(
                    {
                        "ovrtx_version": renderer.version,
                        "partial_outputs": args.partial_outputs,
                        "step_size": 1 / 40,
                        "steps": args.steps,
                        "events": events,
                        "filmstrip_camera": None if camera_projection is None else {
                            "camera_to_world_metres": camera_projection[0].tolist(),
                            "focal_length": camera_projection[1],
                            "horizontal_aperture": camera_projection[2],
                            "clipping_range_metres": list(camera_projection[3:]),
                        },
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        for path in ("/Render/Lidar40", "/Render/Lidar20", "/Render/Camera10", "/Render/Camera20"):
            print(f"{path}: {sum(event['product'] == path for event in events)} delivered outputs")
    finally:
        renderer.detach_ovstage()
        stage.destroy()
        renderer.destroy()


if __name__ == "__main__":
    main()
