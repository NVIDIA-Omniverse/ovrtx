# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""CPU checks for the acoustic example's basic-mode range axis; no renderer needed."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

SOURCE = Path(__file__).parents[3] / "examples/python/acoustic/main.py"
spec = importlib.util.spec_from_file_location("acoustic_example", SOURCE)
example = importlib.util.module_from_spec(spec)
spec.loader.exec_module(example)


@pytest.mark.parametrize("duration", [102.4e-6, 200e-6])
def test_basic_mode_range_bin_lower_bounds(duration):
    ranges = example.sample_ranges_m({"num_samples": 320, "sample_duration_s": duration})
    assert ranges.shape == (320,)
    # The first stored bin begins at one sample period, not time zero.
    assert ranges[0] == pytest.approx(duration * 343.21 / 2)
    assert ranges[-1] == pytest.approx(320 * duration * 343.21 / 2)
    np.testing.assert_allclose(np.diff(ranges), duration * 343.21 / 2)
    # An arrival inside each displayed bin must map back through the model's
    # floor(roundTripTime / sampleDuration) - 1 indexing rule to that same bin.
    inside_bin_time = 2 * ranges / 343.21 + 0.25 * duration
    actual_bins = np.floor(inside_bin_time / duration).astype(int) - 1
    np.testing.assert_array_equal(actual_bins, np.arange(320))


def test_empty_range_axis():
    result = example.sample_ranges_m({"num_samples": 0, "sample_duration_s": 102.4e-6})
    assert result.shape == (0,)
