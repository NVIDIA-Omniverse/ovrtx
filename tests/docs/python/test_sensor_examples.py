# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Smoke tests for the public Python sensor examples."""

from __future__ import annotations

from collections.abc import Callable
import math
import re
import sys
from pathlib import Path

PUBLIC_ROOT = Path(__file__).resolve().parents[3]
PYTHON_EXAMPLES = PUBLIC_ROOT / "examples" / "python"

if str(PYTHON_EXAMPLES) not in sys.path:
    sys.path.insert(0, str(PYTHON_EXAMPLES))

from lidar.main import main as run_lidar_example  # noqa: E402
from radar.main import main as run_radar_example  # noqa: E402


def run_python_example(
    example_name: str,
    example_main: Callable[[list[str]], None],
    capsys,
    output_dir: Path,
    extra_args: list[str] | None = None,
) -> str:
    """Run a public Python sensor example headless in the docs test process."""
    log_file_path = output_dir / f"python-doc-tests-{example_name}-example.log"
    example_main(["--no-rr", "--log", str(log_file_path), *(extra_args or [])])

    captured = capsys.readouterr()
    return captured.out + captured.err


def test_python_lidar_example_reports_valid_pointcloud(capsys, output_dir):
    """Run the lidar example and sanity-check the printed PointCloud summary."""
    # [snippet:python-lidar-example-reports-valid-pointcloud]
    output = run_python_example(
        "lidar",
        run_lidar_example,
        capsys,
        output_dir,
    )

    match = re.search(
        r"valid points=(\d+), mean intensity=([-+0-9.eE]+), "
        r"max time offset=(\d+) ns",
        output,
    )
    assert match, output

    valid_points = int(match.group(1))
    mean_intensity = float(match.group(2))
    max_time_offset_ns = int(match.group(3))

    assert valid_points > 1000
    assert math.isfinite(mean_intensity)
    assert mean_intensity >= 0.0
    assert max_time_offset_ns > 0
    # [/snippet:python-lidar-example-reports-valid-pointcloud]


def test_python_radar_example_reports_moving_detections(capsys, output_dir):
    """Run the radar example and sanity-check per-step radial velocity output."""
    # [snippet:python-radar-example-reports-moving-detections]
    output = run_python_example(
        "radar",
        run_radar_example,
        capsys,
        output_dir,
    )

    step_matches = re.findall(
        r"step (\d+): valid points=(\d+), "
        r"radial velocity min/max=\[([-+0-9.eE]+), ([-+0-9.eE]+)\] m/s",
        output,
    )
    assert len(step_matches) == 10, output

    max_abs_radial_velocity = 0.0
    for step, valid_points, min_velocity, max_velocity in step_matches:
        assert 1 <= int(step) <= 10
        assert int(valid_points) > 0

        min_velocity = float(min_velocity)
        max_velocity = float(max_velocity)
        assert math.isfinite(min_velocity)
        assert math.isfinite(max_velocity)
        max_abs_radial_velocity = max(
            max_abs_radial_velocity,
            abs(min_velocity),
            abs(max_velocity),
        )

    assert max_abs_radial_velocity > 0.1
    # [/snippet:python-radar-example-reports-moving-detections]


def test_python_lidar_example_runs_the_panels_scene(capsys, output_dir):
    """The alternative lidar scene, selected with --scene, delivers a point cloud through the same code."""
    output = run_python_example(
        "lidar-panels",
        run_lidar_example,
        capsys,
        output_dir,
        ["--scene", str(PYTHON_EXAMPLES / "lidar" / "lidar_example_panels.usda")],
    )
    match = re.search(r"valid points=(\d+), mean intensity=([-+0-9.eE]+), ", output)
    assert match, output
    # Five panels around the sensor return far more points than the single cube of the default scene.
    assert int(match.group(1)) > 100000
    assert math.isfinite(float(match.group(2)))


def test_python_radar_example_runs_the_field_scene(capsys, output_dir):
    """The alternative radar scene, selected with --scene, reports the panel field and the closing cube."""
    output = run_python_example(
        "radar-field",
        run_radar_example,
        capsys,
        output_dir,
        ["--scene", str(PYTHON_EXAMPLES / "radar" / "radar_example_field.usda")],
    )
    step_matches = re.findall(
        r"step (\d+): valid points=(\d+), "
        r"radial velocity min/max=\[([-+0-9.eE]+), ([-+0-9.eE]+)\] m/s",
        output,
    )
    assert len(step_matches) == 10, output
    for _step, valid_points, min_velocity, _max_velocity in step_matches:
        # The field holds 33 steel panels; each step reports most of them plus the cube.
        assert int(valid_points) >= 20
        # The cube closes at 10 m/s along the radar's line of sight.
        assert -11.0 < float(min_velocity) < -8.0
