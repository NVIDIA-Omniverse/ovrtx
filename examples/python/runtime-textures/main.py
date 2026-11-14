#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""Drive Carter in a circle and display its previous camera frame on a monitor."""

import argparse
from contextlib import ExitStack
import json
import math
from pathlib import Path
import sys

import numpy as np
import ovrtx
import ovstage
from PIL import Image
import warp as wp


# [snippet:doc-runtime-texture-luminance]
@wp.func
def srgb_to_linear(value: float):
    if value <= 0.04045:
        return value / 12.92
    return wp.pow((value + 0.055) / 1.055, 2.4)


@wp.kernel
def camera_luminance(source: wp.array3d(dtype=wp.uint8), texels: wp.array(dtype=wp.uint8)):
    y, x = wp.tid()
    r = srgb_to_linear(float(source[y, x, 0]) / 255.0)
    g = srgb_to_linear(float(source[y, x, 1]) / 255.0)
    b = srgb_to_linear(float(source[y, x, 2]) / 255.0)
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    encoded = 12.92 * luminance
    if luminance > 0.0031308:
        encoded = 1.055 * wp.pow(luminance, 1.0 / 2.4) - 0.055
    gray = wp.uint8(wp.clamp(encoded * 255.0 + 0.5, 0.0, 255.0))
    index = (y * source.shape[1] + x) * 4
    texels[index] = gray
    texels[index + 1] = gray
    texels[index + 2] = gray
    texels[index + 3] = wp.uint8(255)
# [/snippet:doc-runtime-texture-luminance]


def camera_image(products, name):
    output = products[f"/Render/{name}"].frames[-1].render_vars[f"/Render/{name}/LdrColor"]
    with output.map(device=ovrtx.Device.CPU) as mapped:
        return np.from_dlpack(mapped).copy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=int, default=180, help="Frames to render (default: one circle at 30 fps)")
    parser.add_argument("--fps", type=float, default=30.0, help="Simulation frames per second")
    parser.add_argument("--period", type=float, default=6.0, help="Seconds per circle")
    parser.add_argument("--png", type=Path, nargs="?", const=Path("_output/carter-monitor.png"),
                        help="Save the final overview plus camera, monitor and initial overview PNGs")
    parser.add_argument("--rrd", type=Path, help="Save the animated Rerun recording")
    parser.add_argument("--check", action="store_true", help="Also validate GPU texels and the monitor's sampled image")
    args = parser.parse_args()
    if args.frames < 2 or args.fps <= 0 or args.period <= 0:
        parser.error("Use at least two frames and positive fps/period")
    output_dir = args.png.parent if args.png else Path("_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    rr = None
    if args.rrd or not args.png:
        import rerun as rr
        rr.init("Carter camera monitor", spawn=args.rrd is None)
        if args.rrd:
            args.rrd.parent.mkdir(parents=True, exist_ok=True)
            rr.save(str(args.rrd))
        import rerun.blueprint as rrb
        rr.send_blueprint(rrb.Horizontal(
            rrb.Spatial2DView(origin="overview", name="Carter and monitor"),
            rrb.Vertical(rrb.Spatial2DView(origin="robot", name="Current robot camera"),
                         rrb.Spatial2DView(origin="monitor", name="Previous frame, greyscale")),
            column_shares=[2, 1],
        ))
    renderer = ovrtx.Renderer(ovrtx.RendererConfig(
        active_cuda_gpus="0", log_file_path=str(output_dir.resolve() / "carter-monitor.log")))
    stage = ovstage.Stage("ovrtx.example.carter-monitor")
    renderer.attach_ovstage(stage)
    products = None
    try:
        ovstage.set_log_callback(lambda severity, timestamp, message: print(f"{severity.name}: {message}", file=sys.stderr))
        try:
            ovstage.population.open_usd(stage, str(Path(__file__).with_name("carter_monitor.usda")), ordinal=1)
        finally:
            ovstage.set_log_callback(None)
        # A missing remote payload must fail, rather than showing an empty warehouse or robot.
        for prefix in ("/World/warehouse/", "/World/carter_v1/"):
            mesh_filter = ovstage.Filter([
                ovstage.Predicate("usd-path", ovstage.FilterOp.PREFIX, [prefix]),
                ovstage.Predicate("usd-prim-type", ovstage.FilterOp.IN, ["Mesh"]),
            ])
            with stage.query(filter=mesh_filter) as query:
                if not query.result().total_prim_count:
                    raise RuntimeError(f"No meshes loaded under {prefix}; check remote asset access")

        with ovstage.PathDictionary(stage) as paths, ExitStack() as resources:
            queries = []
            for prim in ("/Texture", "/World/carter_v1"):
                path_list = paths.create_path_list_from_strings([prim])
                resources.callback(paths.destroy_path_list, path_list)
                queries.append(resources.enter_context(stage.query_from_path_list(path_list)))
            texture_query, robot_query = queries
            width, height = 320, 240
            # Start black: there is no previous frame at frame zero.
            initial = np.zeros((height, width, 4), dtype=np.uint8)
            initial[:, :, 3] = 255
            texels = wp.array(initial.reshape(-1), dtype=wp.uint8, device="cuda:0")
            wp.synchronize_device("cuda:0")
            stage.write_attribute(texture_query, "texture:extent", ordinal=1, is_array=False,
                                  tensors=np.array([[width, height, 1]], dtype=np.int32)).wait()
            stage.write_attribute(texture_query, "texture:data", ordinal=1, is_array=True, tensors=texels).wait()
            stage.advance_write_floor(1, ovstage.Scope.ALL).wait()
            render_products = {"/Render/Robot", "/Render/Overview", "/Render/Monitor"}
            # Warm up materials while the monitor remains black. Discard these frames.
            print("Warming up the warehouse and Carter...", flush=True)
            for _ in range(40):
                products = renderer.step(render_products, 1.0 / args.fps, ordinal=1)
            products = None
            first_overview = None
            last_source = None
            max_kernel_error = 0
            monitor_correlations = []
            for frame in range(args.frames):
                ordinal = frame + 2
                # [snippet:doc-runtime-texture-camera-feedback]
                if products is not None:
                    # Consume frame N-1 before rendering N. Keep the result and mapping alive
                    # until Warp finishes reading; the texture update never goes through the CPU.
                    output = products["/Render/Robot"].frames[-1].render_vars["/Render/Robot/LdrColor"]
                    with output.map(device=ovrtx.Device.CUDA, sync_stream=0) as mapped:
                        mapped.wait()
                        source = wp.from_dlpack(mapped)
                        wp.launch(camera_luminance, dim=(height, width), inputs=[source, texels], device="cuda:0")
                        wp.synchronize_device("cuda:0")
                        del source
                    del mapped, output
                    stage.write_attribute(texture_query, "texture:data", ordinal=ordinal,
                                          is_array=True, tensors=texels).wait()
                # [/snippet:doc-runtime-texture-camera-feedback]
                if args.check and last_source is not None:
                    rgb = last_source[:, :, :3].astype(np.float64) / 255.0
                    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
                    luminance = linear @ np.array([0.2126, 0.7152, 0.0722])
                    encoded = np.where(luminance <= 0.0031308, luminance * 12.92,
                                       1.055 * luminance ** (1 / 2.4) - 0.055)
                    expected = np.clip(np.floor(encoded * 255 + 0.5), 0, 255).astype(np.uint8)
                    gpu = texels.numpy().reshape(height, width, 4)
                    error = int(np.abs(gpu[:, :, :3].astype(np.int16) - expected[:, :, None]).max())
                    max_kernel_error = max(max_kernel_error, error)
                    if error > 1 or not np.all(gpu[:, :, 3] == 255):
                        raise RuntimeError(f"Warp luminance differs from CPU reference: {error}")

                # [snippet:doc-runtime-texture-carter-motion]
                angle = math.tau * (frame / args.fps) / args.period
                heading = angle + math.pi / 2  # Carter's +X axis follows the circle's tangent.
                c, s = math.cos(heading), math.sin(heading)
                pose = np.array([[
                    [c, s, 0, 0], [-s, c, 0, 0], [0, 0, 1, 0],
                    [-5 + 1.4 * math.cos(angle), 4 + 1.4 * math.sin(angle), 0.25, 1],
                ]], dtype=np.float64)
                stage.write_attribute(robot_query, "omni:xform", ordinal=ordinal,
                                      is_array=False, tensors=pose).wait()
                # The child camera follows Carter. Seal texture and motion together.
                stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
                products = renderer.step(render_products, 1.0 / args.fps, ordinal=ordinal)
                # [/snippet:doc-runtime-texture-carter-motion]
                overview = camera_image(products, "Overview")
                robot = camera_image(products, "Robot")
                monitor = camera_image(products, "Monitor")
                if first_overview is None:
                    first_overview = overview.copy()
                if args.check:
                    for name, image in (("overview", overview), ("robot", robot), ("monitor", monitor)):
                        Image.fromarray(image).save(output_dir / f"check-{frame:03d}-{name}.png")
                    if frame == 0:
                        if monitor[4:-4, 4:-4, :3].max() > 3:
                            raise RuntimeError("The first frame's monitor must be black")
                    else:
                        observed = monitor[4:-4, 4:-4, :3].astype(np.float64)
                        expected_center = expected[4:-4, 4:-4].astype(np.float64)
                        # Display post-processing changes brightness, so compare spatial content.
                        correlation = float(np.corrcoef(observed.mean(axis=2).ravel(), expected_center.ravel())[0, 1])
                        monitor_correlations.append(correlation)
                        if not np.isfinite(correlation) or correlation < 0.9:
                            raise RuntimeError(f"Monitor does not sample the previous frame: correlation {correlation:.3f}")
                if rr:
                    rr.set_time("simulation", duration=frame / args.fps)
                    rr.log("overview", rr.Image(overview[:, :, :3]))
                    rr.log("robot", rr.Image(robot[:, :, :3]))
                    rr.log("monitor", rr.Image(monitor[:, :, :3]))
                last_source = robot
                if frame % 30 == 0:
                    print(f"Frame {frame + 1}/{args.frames}", flush=True)
            if args.check:
                (output_dir / "carter-monitor-checks.json").write_text(json.dumps({
                    "frames": args.frames, "kernel_max_error": max_kernel_error,
                    "monitor_correlations": monitor_correlations,
                }, indent=2) + "\n")
            if args.png:
                for suffix, pixels in (("", overview), ("_first", first_overview),
                                       ("_robot", robot), ("_monitor", monitor)):
                    Image.fromarray(pixels).save(args.png.with_name(args.png.stem + suffix + args.png.suffix))
                print(f"Saved {args.png}", flush=True)
    finally:
        products = None
        renderer.detach_ovstage()
        stage.destroy()
        renderer.destroy()


if __name__ == "__main__":
    main()
