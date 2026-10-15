# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Exercise mixed camera/lidar timing through the runnable public example."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image


@pytest.fixture(scope="module")
def multi_rate_runs(output_dir):
    example = Path(__file__).parents[3] / "examples/python/multi-rate-sensors/main.py"
    results = {}
    for partial in (False, True):
        name = "partial" if partial else "full"
        report = output_dir / f"multi-rate-{name}.json"
        image = output_dir / f"multi-rate-{name}.png"
        filmstrip = output_dir / f"multi-rate-{name}-timeline.png"
        log = output_dir / f"multi-rate-{name}.log"
        report.unlink(missing_ok=True)
        image.unlink(missing_ok=True)
        filmstrip.unlink(missing_ok=True)
        command = [
            sys.executable, str(example), "--no-rr", "--report", str(report),
            "--png", str(image), "--filmstrip", str(filmstrip),
        ]
        if partial:
            command.append("--partial-outputs")
        with log.open("w", encoding="utf-8") as stream:
            completed = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=600, check=False)
        assert completed.returncode == 0, log.read_text(encoding="utf-8", errors="replace")
        results[partial] = json.loads(report.read_text(encoding="utf-8"))
        # Check the actual runtime extraction, including this scene's cm-to-m
        # conversion. Merely getting some projected dots does not prove units.
        calibration = results[partial]["filmstrip_camera"]
        camera_matrix = np.asarray(calibration["camera_to_world_metres"])
        np.testing.assert_allclose(camera_matrix[3], [0, 3.5, 10, 1])
        angle = np.deg2rad(-20)
        np.testing.assert_allclose(camera_matrix[:3, :3],
                                   [[1, 0, 0], [0, np.cos(angle), np.sin(angle)],
                                    [0, -np.sin(angle), np.cos(angle)]], atol=1e-7)
        assert calibration["focal_length"] == pytest.approx(50)
        assert calibration["horizontal_aperture"] == pytest.approx(20.955)
        np.testing.assert_allclose(calibration["clipping_range_metres"], [0.01, 10000])
        with Image.open(image) as rendered:
            assert rendered.size == (640, 240)
            assert rendered.mode == "RGB", "The comparison image must not retain the camera AOV's alpha channel"
            for view in np.split(np.asarray(rendered), 2, axis=1):
                assert np.any(view)
                assert np.any(view != view[0, 0]), "Camera output is uniform"
        with Image.open(filmstrip) as timeline:
            assert timeline.size == (2928, 1360)
            assert timeline.mode == "RGB"
            pixels = np.asarray(timeline)
            # Each lidar cell must agree with actual deliveries, including empty
            # steps. A delivered scan can have no returns in the camera's view.
            for row, name in ((2, "Lidar40"), (3, "Lidar20")):
                delivered = {event["step"] for event in results[partial]["events"]
                             if event["product"] == f"/Render/{name}"}
                for step in range(1, 9):
                    x, y = 240 + (step - 1) * 336, 180 + row * 280
                    cell = pixels[y + 4:y + 214, x + 4:x + 316]
                    if step not in delivered:
                        assert np.all(cell == (240, 243, 246)), (name, step)
                    else:
                        assert np.any(np.all(cell == (16, 28, 42), axis=-1)), (name, step)
                # This scene must actually project visible returns, not merely
                # create empty panels that match the delivery schedule.
                row_pixels = pixels[180 + row * 280:398 + row * 280, 240:]
                assert np.any(np.all(row_pixels == (94, 234, 212), axis=-1)), name
    return results


@pytest.fixture
def multi_rate_example():
    example = Path(__file__).parents[3] / "examples/python/multi-rate-sensors/main.py"
    spec = importlib.util.spec_from_file_location("multi_rate_example", example)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_world_point_projection_uses_camera_pose_and_clips_invalid_points(multi_rate_example):
    # Camera rotated 90 degrees around Y and translated in world metres.
    # Independent known rays in its local frame should land at these pixels.
    camera = np.array([[0, 0, -1, 0], [0, 1, 0, 0], [1, 0, 0, 0], [3, 4, 5, 1]], dtype=float)
    points = np.array([[1, 4, 5], [1, 4, 4], [1, 4.5, 5],
                       [4, 4, 5], [3, 4, 5], [1, 4, 2], [1, 7, 5],
                       [np.nan, 4, 5], [np.inf, 4, 5], [-17, 4, 5], [2.95, 4, 5]])
    with np.errstate(invalid="ignore"):
        pixels, depth = multi_rate_example.project_points(points, camera, 1, 2, .1, 10)
    np.testing.assert_allclose(pixels, [[160, 120], [240, 120], [160, 80]])
    np.testing.assert_allclose(depth, [2, 2, 2])
    empty_pixels, empty_depth = multi_rate_example.project_points(np.empty((0, 3)), camera, 1, 2)
    assert empty_pixels.shape == (0, 2)
    assert empty_depth.size == 0


def test_lidar_timeline_draws_each_delivery_without_reusing_or_accumulating_points(multi_rate_example, tmp_path):
    clouds = {("/Render/Lidar40", 1): np.array([[0., 0., -2.]]),
              ("/Render/Lidar40", 2): np.array([[.5, 0., -2.]])}
    path = tmp_path / "deliveries.png"
    multi_rate_example.save_filmstrip(path, {}, clouds, (np.eye(4), 1, 2), 3, True)
    with Image.open(path) as image:
        pixels = np.asarray(image)
        # Known pixel locations from the independent centred perspective rays.
        # Step two must contain its new point and must not retain step one's.
        np.testing.assert_array_equal(pixels[740 + 120, 240 + 160], [94, 234, 212])
        np.testing.assert_array_equal(pixels[740 + 120, 576 + 200], [94, 234, 212])
        np.testing.assert_array_equal(pixels[740 + 120, 576 + 160], [16, 28, 42])
        np.testing.assert_array_equal(pixels[740 + 120, 912 + 160], [240, 243, 246])


def test_completed_outputs_follow_sensor_rates(multi_rate_runs):
    report = multi_rate_runs[False]
    assert report["partial_outputs"] is False
    assert report["steps"] == 40
    assert report["step_size"] == pytest.approx(1 / 40)
    for name, hz in (("Lidar40", 40), ("Lidar20", 20), ("Camera10", 10), ("Camera20", 20)):
        events = [event for event in report["events"] if event["product"] == f"/Render/{name}"]
        assert len(events) == hz, f"{name}: {events}"
        delivery_steps = [event["step"] for event in events]
        # Assert the first output as well as the interval: no skipped warmup steps.
        np.testing.assert_array_equal(delivery_steps, np.arange(40 // hz, 41, 40 // hz))
        capture_times = [event["capture_start_time"] for event in events]
        np.testing.assert_allclose(np.diff(capture_times), 1 / hz, atol=1e-6)
        for event in events:
            expected_time = event["step"] / 40
            assert event["simulation_end_time"] == pytest.approx(expected_time)
            assert event["capture_start_time"] <= event["capture_end_time"] <= expected_time + 1e-6
            if name == "Camera10":
                assert event["capture_start_time"] == event["capture_end_time"]
            elif name == "Camera20":
                assert event["capture_end_time"] - event["capture_start_time"] == pytest.approx(1 / 20)


def test_completed_lidar_scans_keep_history_across_empty_steps(multi_rate_runs):
    for name, hz in (("Lidar40", 40), ("Lidar20", 20)):
        events = [event for event in multi_rate_runs[False]["events"] if event["product"] == f"/Render/{name}"]
        # This lidar's frameId counts render calls, including intermediate scan steps.
        np.testing.assert_array_equal(np.diff([event["frameId"] for event in events]), 40 // hz)
        for index, event in enumerate(events):
            assert event["point_count"] > 0
            assert event["capture_end_time"] - event["capture_start_time"] == pytest.approx(1 / hz)
            assert event["min_point_offset_ns"] >= 0
            # For the 20 Hz lidar, a payload containing only the last 25 ms slice fails this check.
            assert event["max_point_offset_ns"] - event["min_point_offset_ns"] > 0.75e9 / hz
            if index:
                assert event["capture_start_time"] == pytest.approx(events[index - 1]["capture_end_time"])


def test_accumulated_lidar_timestamp_anchors_scan_start(multi_rate_runs):
    report = multi_rate_runs[False]
    if tuple(report["ovrtx_version"]) < (0, 6, 0):
        pytest.skip("OMPE-106853 fixes accumulated lidar timestampNs in ovrtx 0.6; the pinned 0.5 lacks the fix")
    for name, hz in (("Lidar40", 40), ("Lidar20", 20)):
        events = [event for event in report["events"] if event["product"] == f"/Render/{name}"]
        for index, event in enumerate(events):
            assert event["timestampNs"] / 1e9 == pytest.approx(event["capture_start_time"])
            if index:
                assert event["timestampNs"] - events[index - 1]["timestampNs"] == round(1e9 / hz)


def test_partial_delivery_preserves_capture_cadence(multi_rate_runs):
    full, partial = multi_rate_runs[False], multi_rate_runs[True]
    assert partial["partial_outputs"] is True
    for name in ("Lidar20", "Camera20"):
        complete_events = [event for event in full["events"] if event["product"] == f"/Render/{name}"]
        partial_events = [event for event in partial["events"] if event["product"] == f"/Render/{name}"]
        assert len(partial_events) > len(complete_events)
        assert {event["step"] for event in partial_events} == set(range(1, 41))

    # Captures that already fit in one step retain their completed-output cadence.
    for name, interval in (("Lidar40", 1), ("Camera10", 4)):
        events = [event for event in partial["events"] if event["product"] == f"/Render/{name}"]
        assert [event["step"] for event in events] == list(range(interval, 41, interval))

    rolling = [event for event in partial["events"] if event["product"] == "/Render/Camera20"]
    # The public color RenderVar has no completion flag. For this fixed two-split
    # exposure, compare the reported capture spans with the authored exposure.
    spans = np.array([event["capture_end_time"] - event["capture_start_time"] for event in rolling])
    np.testing.assert_allclose(spans, [1 / 40 if event["step"] % 2 else 1 / 20 for event in rolling])
    instantaneous = [event for event in partial["events"] if event["product"] == "/Render/Camera10"]
    assert len(instantaneous) == 10
    assert all(event["capture_start_time"] == event["capture_end_time"] for event in instantaneous)
