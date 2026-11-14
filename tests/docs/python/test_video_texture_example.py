# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Validate the video-texture example's source-time-aware frame checks."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

EXAMPLE_MAIN = (
    Path(__file__).parents[3] / "examples/python/video-textures/main.py"
)
SPEC = importlib.util.spec_from_file_location("video_texture_example", EXAMPLE_MAIN)
video_texture_example = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(video_texture_example)


def _synthetic_frame(frame_index: int) -> np.ndarray:
    frame = np.full((360, 640, 3), (20, 30, 40), dtype=np.uint8)
    frame[10:40, 10:60] = 255
    center_x, center_y = video_texture_example.EXPECTED_BALL_CENTERS[frame_index]
    x = round(center_x)
    y = round(center_y)
    frame[y - 10 : y + 11, x - 10 : x + 11] = (220, 120, 20)
    return frame


def test_argument_parsing_rejects_times_less_than_one_frame_apart(monkeypatch, capsys):
    monkeypatch.setattr(
        video_texture_example.sys,
        "argv",
        ["main.py", "--times", "0", "0.01", "--no-rr"],
    )
    with pytest.raises(SystemExit):
        video_texture_example.parse_args()
    assert "at least 0.1 seconds apart" in capsys.readouterr().err


def test_argument_parsing_accepts_times_one_frame_apart(monkeypatch):
    monkeypatch.setattr(
        video_texture_example.sys,
        "argv",
        ["main.py", "--times", "0", "0.1", "--no-rr"],
    )
    assert video_texture_example.parse_args().times == [0.0, 0.1]


def test_validation_rejects_frames_in_the_wrong_time_order():
    with pytest.raises(RuntimeError, match="expected clip frame"):
        video_texture_example._validate_frames(
            [0.0, 1.0], [_synthetic_frame(10), _synthetic_frame(0)]
        )
