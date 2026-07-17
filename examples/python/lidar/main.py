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


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SCENE = SCRIPT_DIR / "lidar_example.usda"
OUTPUT_DIR = SCRIPT_DIR / "_output"
RENDER_PRODUCT = "/World/Render/Products/LidarProduct"
WARMUP_STEPS = 3
STEP_DT_SECONDS = 0.1


# [snippet:intensity-colors]
def intensity_colors(intensity: np.ndarray) -> np.ndarray:
    """Map lidar intensity to grayscale RGB point colors."""
    if len(intensity) == 0:
        return np.empty((0, 3), dtype=np.uint8)

    min_value = float(np.min(intensity))
    max_value = float(np.max(intensity))
    scale = max(max_value - min_value, 1.0e-6)
    normalized = np.clip((intensity - min_value) / scale, 0.0, 1.0)
    value = (normalized * 255).astype(np.uint8)
    return np.repeat(value[:, None], 3, axis=1)


# [/snippet:intensity-colors]


# [snippet:log-lidar-points]
def log_lidar_points(rr, points: np.ndarray, intensity: np.ndarray) -> None:
    """Log one lidar frame to rerun with intensity as point color."""
    if len(points) == 0:
        return

    rr.log(
        "world/lidar_points",
        rr.Points3D(
            positions=points,
            colors=intensity_colors(intensity),
            radii=0.05,
        ),
    )
    rr.log(
        "world/lidar",
        rr.Arrows3D(
            origins=[[0.0, 0.0, 1.0]],
            vectors=[[3.0, 0.0, 0.0]],
            colors=[[255, 255, 0]],
            radii=0.04,
            labels=["Lidar +X"],
        ),
    )


# [/snippet:log-lidar-points]


# [snippet:read-lidar-pointcloud]
def read_lidar_pointcloud(frame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Map the PointCloud composite tensor to CPU and return valid point channels."""
    with frame.render_vars["PointCloud"].map(device=ovrtx.Device.CPU) as pointcloud:
        coordinates = np.from_dlpack(pointcloud["Coordinates"])
        counts = np.from_dlpack(pointcloud["Counts"])
        intensity = np.from_dlpack(pointcloud["Intensity"])
        time_offset_ns = np.from_dlpack(pointcloud["TimeOffsetNs"])

        # Counts contains the number of valid entries in the per-point tensors.
        valid_count = int(counts[0])
        points = np.asarray(coordinates[:, :valid_count].T)
        return (
            points.copy(),
            np.asarray(intensity[:valid_count]).copy(),
            np.asarray(time_offset_ns[:valid_count]).copy(),
        )


# [/snippet:read-lidar-pointcloud]


def main(argv: list[str] | None = None) -> None:
    # [snippet:parse-lidar-cli-args]
    parser = argparse.ArgumentParser(
        description="Lidar PointCloud ovrtx example with rerun visualization"
    )
    parser.add_argument(
        "--scene", type=Path, default=DEFAULT_SCENE, help="USDA scene to load"
    )
    parser.add_argument(
        "--no-rr", action="store_true", help="Disable rerun visualization"
    )
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
        const=OUTPUT_DIR / "lidar_example.log",
        default=None,
        metavar="PATH",
        help="Write a carb log file (default: _output/lidar_example.log)",
    )
    args = parser.parse_args(argv)
    # [/snippet:parse-lidar-cli-args]

    # [snippet:initialize-rerun]
    # Rerun is optional: the same example can run headless with --no-rr.
    rr = None
    if not args.no_rr:
        import rerun as rr

        rr.init("ovrtx_lidar", spawn=args.rrd is None)
        if args.rrd is not None:
            rr.save(str(args.rrd))
        rr.log("/", rr.ViewCoordinates.RIGHT_HAND_Z_UP, static=True)
    # [/snippet:initialize-rerun]

    # [snippet:create-renderer]
    # Enable motion BVH: required by the lidar sensor pipeline.
    log_file_path = None
    if args.log is not None:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        log_file_path = str(args.log)
    renderer = ovrtx.Renderer(
        ovrtx.RendererConfig(
            log_file_path=log_file_path,
            log_level="info",
            motion_bvh=ovrtx.MotionBvh.ENABLE,
        )
    )
    stage = ovstage.Stage("ovrtx.example.lidar")
    renderer.attach_ovstage(stage)
    # [/snippet:create-renderer]

    # [snippet:load-lidar-scene]
    # The USDA scene defines the lidar, material bindings, and render product.
    print(f"Loading lidar scene from {args.scene}...")
    ordinal = 1
    ovstage.population.open_usd(stage, str(args.scene), ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    # [/snippet:load-lidar-scene]

    # [snippet:warm-up-lidar]
    # Warm up the sensor before reading the point cloud frame.
    for _ in range(WARMUP_STEPS):
        renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT_SECONDS, ordinal=ordinal)
    # [/snippet:warm-up-lidar]

    # [snippet:step-and-visualize-lidar]
    # Render one lidar frame, summarize scalar channels, and color points by intensity.
    products = renderer.step(
        render_products={RENDER_PRODUCT}, delta_time=STEP_DT_SECONDS, ordinal=ordinal
    )
    frame = products[RENDER_PRODUCT].frames[0]
    points, intensity, time_offset_ns = read_lidar_pointcloud(frame)

    if len(points) == 0:
        print("valid points=0")
        del frame, products
        renderer.detach_ovstage()
        stage.destroy()
        renderer.destroy()
        return

    print(
        f"valid points={len(points)}, "
        f"mean intensity={float(np.mean(intensity))}, "
        f"max time offset={int(np.max(time_offset_ns))} ns"
    )
    if rr is not None:
        log_lidar_points(rr, points, intensity)
    # [/snippet:step-and-visualize-lidar]

    del frame, products
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


if __name__ == "__main__":
    main()
