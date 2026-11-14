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

"""Render a timestamped H.265 video texture at several source times."""

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image, ImageDraw, ImageFont

EXAMPLE_DIR = Path(__file__).resolve().parent
MAX_SAMPLES = 4
DEFAULT_TIMES = (0.0, 1.0, 2.0, 3.0)
CLIP_FRAME_RATE = 10.0
MIN_SAMPLE_INTERVAL = 1.0 / CLIP_FRAME_RATE
# Blocking video streaming makes each step wait for the decoder. Bound those
# waits so a decode failure raises instead of hanging.
VIDEO_TIMEOUT_SECONDS = 300
VIDEO_TIMEOUT_NS = VIDEO_TIMEOUT_SECONDS * 1_000_000_000
# Ball centers measured from the 40 frames produced by generate_video.sh.
EXPECTED_BALL_CENTERS = (
    (320.0, 180.0),
    (329.5, 187.1),
    (338.9, 194.2),
    (348.3, 201.3),
    (357.5, 208.4),
    (366.9, 215.3),
    (376.2, 222.1),
    (385.5, 228.9),
    (394.6, 235.6),
    (403.7, 242.3),
    (412.7, 248.8),
    (421.6, 255.1),
    (430.5, 261.4),
    (439.1, 267.4),
    (447.7, 273.3),
    (456.2, 278.9),
    (464.6, 284.3),
    (472.7, 289.6),
    (480.7, 294.7),
    (488.6, 299.5),
    (496.4, 304.2),
    (503.8, 308.6),
    (511.4, 312.6),
    (518.3, 316.5),
    (525.4, 320.1),
    (532.1, 323.4),
    (538.8, 326.4),
    (545.1, 329.1),
    (551.1, 331.5),
    (557.1, 333.6),
    (562.6, 335.5),
    (568.2, 337.2),
    (573.4, 338.3),
    (578.2, 339.2),
    (582.9, 339.6),
    (587.3, 340.0),
    (591.5, 339.9),
    (595.3, 339.6),
    (599.0, 338.9),
    (602.3, 337.8),
)
BALL_CENTER_TOLERANCE = 8.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--times",
        type=float,
        nargs="+",
        default=DEFAULT_TIMES,
        help="Video times in seconds to render (default: 0 1 2 3)",
    )
    parser.add_argument(
        "--rrd", type=Path, help="Write a Rerun recording instead of opening a viewer"
    )
    parser.add_argument(
        "--png", type=Path, help="Write a contact sheet and individual rendered PNGs"
    )
    parser.add_argument("--no-rr", action="store_true", help="Do not log images to Rerun")
    parser.add_argument("--no-spawn", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.no_rr and args.rrd:
        parser.error("--rrd cannot be combined with --no-rr")
    if len(args.times) > MAX_SAMPLES:
        parser.error(f"--times accepts at most {MAX_SAMPLES} values")
    if any(time < 0.0 or time > 3.9 for time in args.times):
        parser.error("--times values must be within the clip's 0.0-3.9 second range")
    if any(second < first for first, second in zip(args.times, args.times[1:])):
        parser.error("--times values must be in nondecreasing order")
    if any(
        second - first < MIN_SAMPLE_INTERVAL - 1e-9
        for first, second in zip(args.times, args.times[1:])
    ):
        parser.error(
            f"--times values must be at least {MIN_SAMPLE_INTERVAL:.1f} seconds apart "
            "(one frame in the 10-FPS clip)"
        )
    return args


def _map_ldr_color(products, render_product: str) -> np.ndarray:
    frames = products[render_product].frames
    if not frames:
        raise RuntimeError(f"{render_product} produced no frame")
    render_var = frames[-1].render_vars[f"{render_product}/LdrColor"]
    mapped = render_var.map(device=ovrtx.Device.CPU)
    view = np.from_dlpack(mapped)
    pixels = np.ascontiguousarray(view[..., :3])
    del view
    mapped.unmap()
    del mapped, render_var, frames
    return pixels


def _validate_frames(times: list[float], frames: list[np.ndarray]) -> None:
    if len(frames) != len(times):
        raise RuntimeError(f"Expected {len(times)} video frames, received {len(frames)}")

    expected_shape = (360, 640, 3)
    for time, frame in zip(times, frames):
        if frame.shape != expected_shape or frame.dtype != np.uint8:
            raise RuntimeError(
                f"Frame at {time:.1f}s has {frame.shape=} and {frame.dtype=}; "
                f"expected {expected_shape} uint8"
            )
        spatial_std = frame.astype(np.float32).std(axis=(0, 1))
        if float(spatial_std.max()) < 5.0:
            raise RuntimeError(f"Frame at {time:.1f}s has no spatial detail")

        dark = np.all(frame < 64, axis=-1)
        white = np.all(frame > 180, axis=-1)
        orange = (
            (frame[..., 0] > 150)
            & (frame[..., 1] > 70)
            & (frame[..., 1] < 200)
            & (frame[..., 2] < 80)
        )
        if np.count_nonzero(dark) < 10_000:
            raise RuntimeError(f"Frame at {time:.1f}s is missing the dark background")
        if np.count_nonzero(white) < 1_000:
            raise RuntimeError(f"Frame at {time:.1f}s is missing the timestamp text")
        orange_y, orange_x = np.nonzero(orange)
        if orange_x.size < 250:
            raise RuntimeError(f"Frame at {time:.1f}s is missing the orange ball")

        frame_index = min(
            range(len(EXPECTED_BALL_CENTERS)),
            key=lambda index: abs(index / CLIP_FRAME_RATE - time),
        )
        expected_x, expected_y = EXPECTED_BALL_CENTERS[frame_index]
        actual_x = float(orange_x.mean())
        actual_y = float(orange_y.mean())
        print(
            f"{time:.3f}s selected clip frame {frame_index} "
            f"with ball center ({actual_x:.1f}, {actual_y:.1f})",
            file=sys.stderr,
        )
        if (
            abs(actual_x - expected_x) > BALL_CENTER_TOLERANCE
            or abs(actual_y - expected_y) > BALL_CENTER_TOLERANCE
        ):
            raise RuntimeError(
                f"Frame at {time:.3f}s has ball center "
                f"({actual_x:.1f}, {actual_y:.1f}); expected clip frame "
                f"{frame_index} near ({expected_x:.1f}, {expected_y:.1f})"
            )


def _save_pngs(path: Path, times: list[float], frames: list[np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image_height, image_width = frames[0].shape[:2]
    title_height = 48
    columns = 2
    rows = math.ceil(len(frames) / columns)
    sheet = Image.new(
        "RGB",
        (columns * image_width, rows * (image_height + title_height)),
        "#152331",
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=28)
    for index, (time, pixels) in enumerate(zip(times, frames)):
        row, column = divmod(index, 2)
        x = column * image_width
        y = row * (image_height + title_height)
        draw.text(
            (x + image_width // 2, y + title_height // 2),
            f"Video source time: {time:.1f} s",
            font=font,
            fill="white",
            anchor="mm",
        )
        image = Image.fromarray(pixels)
        sheet.paste(image, (x, y + title_height))
        image.save(path.with_name(f"{path.stem}-{time:.1f}s{path.suffix}"))
    sheet.save(path)


def _render_source_times(renderer, ordinal, times, rr):
    rendered_frames = []
    # [snippet:doc-render-video-texture-source-times]
    # This stage has no animation range, so video selection uses simulation time.
    if not renderer.reset_async(time=0.0).wait(timeout_ns=VIDEO_TIMEOUT_NS):
        raise TimeoutError(f"reset did not complete within {VIDEO_TIMEOUT_SECONDS} s")
    current_time = 0.0
    for index, video_time in enumerate(times):
        # Advance from the preceding requested timestamp to this one.
        render_product = f"/Render/Camera_{index}"
        pending = renderer.step_async(
            render_products={render_product},
            delta_time=video_time - current_time,
            ordinal=ordinal,
        ).wait(timeout_ns=VIDEO_TIMEOUT_NS)
        products = pending.fetch(timeout_ns=VIDEO_TIMEOUT_NS) if pending else None
        if products is None:
            raise TimeoutError(
                f"{render_product} did not render video time {video_time:.1f} s "
                f"within {VIDEO_TIMEOUT_SECONDS} s"
            )
        current_time = video_time

        # Put the mapped LdrColor image at its source time on the Rerun timeline.
        image = _map_ldr_color(products, render_product)
        rendered_frames.append(image)
        if rr:
            rr.set_time("video_time", duration=video_time)
            rr.log("render/video_texture", rr.Image(image))
        del products
    # [/snippet:doc-render-video-texture-source-times]
    return rendered_frames


def main() -> None:
    args = parse_args()
    times = list(args.times)

    rr = None
    if not args.no_rr:
        try:
            import rerun as rr
        except ImportError as exc:
            raise SystemExit(
                "rerun-sdk is required. Run this example with `uv run main.py`."
            ) from exc

        rr.init("ovrtx_video_textures", spawn=args.rrd is None and not args.no_spawn)
        if args.rrd:
            args.rrd.parent.mkdir(parents=True, exist_ok=True)
            rr.save(str(args.rrd))

    print(
        "Creating renderer. First launch can take time while shaders compile...",
        file=sys.stderr,
    )
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.video-textures")
    renderer.attach_ovstage(stage)

    try:
        ordinal = 1
        ovstage.population.open_usd(
            stage, str(EXAMPLE_DIR / "video_textures.usda"), ordinal=ordinal
        )
        stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

        rendered_frames = _render_source_times(renderer, ordinal, times, rr)

        if args.png:
            _save_pngs(args.png, times, rendered_frames)
        _validate_frames(times, rendered_frames)
        print(
            f"Rendered and validated {len(rendered_frames)} video frames.",
            file=sys.stderr,
        )
    finally:
        if rr:
            rr.disconnect()
        renderer.detach_ovstage()
        stage.destroy()
        renderer.destroy()


if __name__ == "__main__":
    main()
