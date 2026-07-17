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


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SCENE = SCRIPT_DIR / "radar_example.usda"
OUTPUT_DIR = SCRIPT_DIR / "_output"
RENDER_PRODUCT = "/World/Render/Products/RadarProduct"
WARMUP_STEPS = 3
STEP_DT_SECONDS = 0.1


# [snippet:radial-velocity-colors]
def radial_velocity_colors(radial_velocity: np.ndarray) -> np.ndarray:
    """Map signed radial velocity to RGB: blue approaching, green near zero, red receding."""
    max_abs = max(float(np.max(np.abs(radial_velocity))), 1.0e-6)
    normalized = np.clip(radial_velocity / max_abs, -1.0, 1.0)

    colors = np.empty((len(radial_velocity), 3), dtype=np.uint8)
    colors[:, 0] = np.where(normalized > 0, normalized * 255, 0).astype(np.uint8)
    colors[:, 1] = ((1.0 - np.abs(normalized)) * 180).astype(np.uint8)
    colors[:, 2] = np.where(normalized < 0, -normalized * 255, 0).astype(np.uint8)
    return colors


# [/snippet:radial-velocity-colors]


# [snippet:log-radar-points]
def log_radar_points(rr, step: int, points: np.ndarray, radial_velocity: np.ndarray) -> None:
    """Log one radar frame to rerun with radial velocity as point color."""
    if len(points) == 0:
        return

    rr.set_time("step", sequence=step)
    rr.log(
        "world/radar_points",
        rr.Points3D(
            positions=points,
            colors=radial_velocity_colors(radial_velocity),
            radii=0.15,
        ),
    )
    rr.log(
        "world/radar",
        rr.Arrows3D(
            origins=[[0.0, 0.0, 1.0]],
            vectors=[[3.0, 0.0, 0.0]],
            colors=[[255, 255, 0]],
            radii=0.05,
            labels=["Radar +X"],
        ),
    )


# [/snippet:log-radar-points]


# [snippet:read-radar-pointcloud]
def read_radar_pointcloud(frame) -> tuple[np.ndarray, np.ndarray]:
    """Map the PointCloud composite tensor to CPU and return valid point channels."""
    with frame.render_vars["PointCloud"].map(device=ovrtx.Device.CPU) as pointcloud:
        coordinates = np.from_dlpack(pointcloud["Coordinates"])
        counts = np.from_dlpack(pointcloud["Counts"])
        radial_velocity = np.from_dlpack(pointcloud["RadialVelocityMs"])

        # Counts contains the number of valid detections in the composite tensors.
        valid_count = int(counts[0])
        points = np.asarray(coordinates[:, :valid_count].T)
        return (
            points.copy(),
            np.asarray(radial_velocity[:valid_count]).copy(),
        )


# [/snippet:read-radar-pointcloud]


def main(argv: list[str] | None = None) -> None:
    # [snippet:parse-radar-cli-args]
    parser = argparse.ArgumentParser(
        description="Radar PointCloud ovrtx example with rerun visualization"
    )
    parser.add_argument(
        "--scene", type=Path, default=DEFAULT_SCENE, help="USDA scene to load"
    )
    parser.add_argument(
        "--steps", type=int, default=10, help="Number of animated radar steps"
    )
    parser.add_argument("--no-rr", action="store_true", help="Disable rerun visualization")
    parser.add_argument(
        "--rrd",
        type=Path,
        default=None,
        help="Write a rerun .rrd recording instead of spawning",
    )
    parser.add_argument(
        "--log",
        nargs="?",
        type=Path,
        const=OUTPUT_DIR / "radar_example.log",
        default=None,
        metavar="PATH",
        help="Write a carb log file (default: _output/radar_example.log)",
    )
    args = parser.parse_args(argv)
    # [/snippet:parse-radar-cli-args]

    # [snippet:initialize-rerun]
    # Rerun is optional: the same example can run headless with --no-rr.
    rr = None
    if not args.no_rr:
        import rerun as rr

        rr.init("ovrtx_radar", spawn=args.rrd is None)
        if args.rrd is not None:
            rr.save(str(args.rrd))
        rr.log("/", rr.ViewCoordinates.RIGHT_HAND_Z_UP, static=True)
    # [/snippet:initialize-rerun]

    # [snippet:create-renderer]
    # Create the renderer. Radar defaults are provided by the ovrtx runtime.
    # Enable motion BVH: required for moving-object radial velocity in the radar pipeline.
    log_file_path = None
    if args.log is not None:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        log_file_path = str(args.log)
    renderer = ovrtx.Renderer(ovrtx.RendererConfig(
        log_file_path=log_file_path, 
        motion_bvh=ovrtx.MotionBvh.ENABLE))
    # [/snippet:create-renderer]

    # [snippet:load-radar-scene]
    # The USDA scene defines the radar, materials, render product, and animated cube.
    print(f"Loading radar scene from {args.scene}...")
    renderer.open_usd(str(args.scene))
    # [/snippet:load-radar-scene]

    # [snippet:warm-up-radar]
    # Warm up the sensor before reading the animated frames.
    renderer.update_from_usd_time(0.0)
    for _ in range(WARMUP_STEPS):
        renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT_SECONDS)
    # [/snippet:warm-up-radar]

    # [snippet:step-and-visualize-radar]
    # Step through the USD animation and color each detection by signed radial velocity.
    for step in range(1, args.steps + 1):
        renderer.update_from_usd_time(step * STEP_DT_SECONDS)
        products = renderer.step(
            render_products={RENDER_PRODUCT}, delta_time=STEP_DT_SECONDS
        )
        frame = products[RENDER_PRODUCT].frames[0]
        points, radial_velocity = read_radar_pointcloud(frame)

        if len(radial_velocity) == 0:
            print(f"step {step}: valid points=0")
            continue

        print(
            f"step {step}: valid points={len(points)}, "
            f"radial velocity min/max=[{radial_velocity.min()}, {radial_velocity.max()}] m/s"
        )
        if rr is not None:
            log_radar_points(rr, step, points, radial_velocity)
    # [/snippet:step-and-visualize-radar]


if __name__ == "__main__":
    main()
