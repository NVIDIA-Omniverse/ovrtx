# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Check the documented Generic WPM configurations against GPU contributions."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import ovrtx
import ovstage

PUBLIC_ROOT = Path(__file__).parents[3]
EXAMPLE = PUBLIC_ROOT / "examples/python/generic-wpm"
CONFIGS = PUBLIC_ROOT / "tests/docs/usd/data"
POSITION_ATOL = 1e-3


@pytest.fixture(scope="module")
def example():
    spec = importlib.util.spec_from_file_location("generic_wpm_example", EXAMPLE / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def renderer(output_dir):
    renderer = ovrtx.Renderer(
        ovrtx.RendererConfig(
            motion_bvh=ovrtx.MotionBvh.ENABLE,
            log_file_path=str(output_dir / "generic-wpm-doc-tests-ovrtx.log"),
        )
    )
    try:
        yield renderer
    finally:
        renderer.destroy()


def _load(stage, recipe, overrides=""):
    config = CONFIGS / f"generic_wpm_{recipe}.usda"
    scene = EXAMPLE / "scene.usda"
    ovstage.population.open_usd_from_string(
        stage,
        f"""#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
    timeCodesPerSecond = 10
    subLayers = [@{config.as_posix()}@, @{scene.as_posix()}@]
)
{overrides}
""",
        ordinal=1,
    )
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()


def _write(stage, ordinal, **attributes):
    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/World/Sensor"])
        try:
            with stage.query_from_path_list(path_list) as query:
                for name, value in attributes.items():
                    is_array = isinstance(value, np.ndarray)
                    semantic = ovstage.AttributeSemantic.NONE
                    if isinstance(value, str):
                        value = np.array([paths.intern_token(value).raw_id], dtype=np.uint64)
                        semantic = ovstage.AttributeSemantic.TOKEN_ID
                    elif not is_array:
                        value = np.array([value], dtype=np.uint32)
                    stage.write_attribute(
                        query,
                        paths.intern_token("omni:sensor:GenericWpm:" + name),
                        ordinal=ordinal,
                        tensors=value,
                        is_array=is_array,
                        semantic=semantic,
                    ).wait()
        finally:
            paths.destroy_path_list(path_list)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()


def _dimensions(tensors, params, *, tx, rx, rays=1, group=1, selectors=(0, 0, 0)):
    expected = {
        "numTx": tx,
        "numRx": rx,
        "raysPerTx": rays,
        "groupSize": group,
        "numTiles": 1,
        "maxBounces": 1,
        "maxContributions": tx * rays * group,
        **dict(zip(("activeTxPatternIndex", "activeRxPatternIndex", "activeMappingPageIndex"), selectors)),
    }
    for name, value in expected.items():
        assert params[name].dtype == np.uint32
        assert params[name].size == 1
        assert int(params[name].reshape(-1)[0]) == value, name
    count = tx * rays * group
    assert tensors["Valid"].shape == (count,)
    assert tensors["Valid"].dtype == np.uint32
    for name in ("HitPosSensorM", "HitPosWorld", "RxRelativePosM"):
        assert tensors[name].shape == (count, 3)
        assert tensors[name].dtype == np.float32
    for name in ("Power", "RoundTripDistanceM"):
        assert tensors[name].shape == (count,)
        assert tensors[name].dtype == np.float32


@pytest.mark.parametrize("recipe", ("depth", "planar", "cylindrical"))
def test_generic_wpm_grid_geometry(renderer, stage, example, recipe):
    _load(stage, recipe)
    tensors, params = example.capture(renderer)
    _dimensions(tensors, params, tx=15, rx=15)
    assert tensors["Valid"].all()
    rows = np.repeat(np.linspace(-10, 10, 3), 5)
    cols = np.tile(np.linspace(-20, 20, 5), 3)
    if recipe == "planar":
        expected = np.column_stack((np.full(15, 11), cols / 10, rows / 10))
        ranges = np.full(15, 11)
    else:
        azimuth = np.radians(cols)
        height = rows / 10 if recipe == "cylindrical" else 11 * np.tan(np.radians(rows)) / np.cos(azimuth)
        expected = np.column_stack((np.full(15, 11), 11 * np.tan(azimuth), height))
        origins = np.zeros_like(expected)
        if recipe == "cylindrical":
            origins[:, 2] = rows / 10
        ranges = np.linalg.norm(expected - origins, axis=1)
    np.testing.assert_allclose(tensors["HitPosSensorM"], expected, atol=POSITION_ATOL)
    np.testing.assert_allclose(tensors["HitPosWorld"], expected, atol=POSITION_ATOL)
    np.testing.assert_allclose(tensors["RoundTripDistanceM"] / 2, ranges, atol=POSITION_ATOL)
    for role in ("tx", "rx"):
        np.testing.assert_array_equal(params[f"gridShape:{role}:0"].reshape(-1), [0, 15, 3, 5, 0, 0])


def test_generic_wpm_lidar_seam_and_firing_times(renderer, stage, example):
    _load(stage, "lidar")
    tensors, params = example.capture(renderer)
    _dimensions(tensors, params, tx=64, rx=64)
    assert tensors["Valid"].all()
    hits = tensors["HitPosSensorM"]
    azimuth = np.arctan2(hits[:, 1], hits[:, 0])
    expected = np.radians(np.repeat(np.linspace(-180, 180, 16, endpoint=False), 4))
    np.testing.assert_allclose(np.cos(azimuth), np.cos(expected), atol=1e-4)
    np.testing.assert_allclose(np.sin(azimuth), np.sin(expected), atol=1e-4)
    np.testing.assert_array_equal(params["gridShape:tx:0"].reshape(-1), [0, 64, 4, 16, 1, 1])
    assert tensors["DeltaTimeNs"].dtype == np.uint64
    expected_times = np.arange(64, dtype=np.uint64) * 1000000 // 63
    np.testing.assert_array_equal(tensors["DeltaTimeNs"], expected_times)


def test_generic_wpm_gaussian_seed_and_zero_spread(renderer, stage, example):
    _load(stage, "gaussian")
    original, params = example.capture(renderer)
    _dimensions(original, params, tx=15, rx=15, rays=9)
    assert original["Valid"].all()
    _write(stage, 2, **{"gaussianPatterns:ray:seeds": np.array([8], dtype=np.uint32)})
    reseeded, _ = example.capture(renderer, ordinal=2, steps=3)
    assert reseeded["Valid"].all()
    assert not np.allclose(original["HitPosSensorM"], reseeded["HitPosSensorM"], atol=POSITION_ATOL)
    _write(stage, 3, **{"gaussianPatterns:ray:seeds": np.array([7], dtype=np.uint32)})
    repeated, _ = example.capture(renderer, ordinal=3, steps=3)
    np.testing.assert_allclose(repeated["HitPosSensorM"], original["HitPosSensorM"], atol=POSITION_ATOL)
    _write(
        stage,
        4,
        **{
            "gaussianPatterns:ray:stdDevsHorizontal": np.array([], dtype=np.float32),
            "gaussianPatterns:ray:stdDevsVertical": np.array([], dtype=np.float32),
        },
    )
    zero, params = example.capture(renderer, ordinal=4, steps=3)
    _dimensions(zero, params, tx=15, rx=15, rays=9)
    assert zero["Valid"].all()
    hits = zero["HitPosSensorM"].reshape(15, 9, 3)
    np.testing.assert_allclose(hits, np.repeat(hits[:, :1], 9, axis=1), atol=POSITION_ATOL)


def test_generic_wpm_bloom_retains_clipped_slots(renderer, stage, example):
    _load(stage, "gaussian_bloom")
    tensors, params = example.capture(renderer)
    _dimensions(tensors, params, tx=15, rx=15, rays=9, group=9)
    expected = np.zeros((15, 9, 9), dtype=bool)
    for tx in range(15):
        row, col = divmod(tx, 5)
        for slot, (dy, dx) in enumerate((dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)):
            expected[tx, :, slot] = 0 <= row + dy < 3 and 0 <= col + dx < 5
    np.testing.assert_array_equal(tensors["Valid"].reshape(15, 9, 9) != 0, expected)
    _write(stage, 2, **{"tx:mappingBloomFactors": np.array([], dtype=np.uint32)})
    zero, params = example.capture(renderer, ordinal=2, steps=3)
    _dimensions(zero, params, tx=15, rx=15, rays=9)
    assert zero["Valid"].all()
    np.testing.assert_allclose(
        tensors["HitPosSensorM"].reshape(15, 9, 9, 3)[:, :, 4],
        zero["HitPosSensorM"].reshape(15, 9, 3),
        atol=POSITION_ATOL,
    )


@pytest.mark.parametrize("recipe,receiver_ids", (("multistatic", (0, 1, 2)), ("multistatic_map", (2, 0))))
def test_generic_wpm_multistatic_paths(renderer, stage, example, recipe, receiver_ids):
    _load(stage, recipe)
    tensors, params = example.capture(renderer)
    slots = len(receiver_ids)
    _dimensions(tensors, params, tx=2, rx=3, rays=9, group=slots)
    # At this RF wavelength steel has a narrow specular return, not a diffuse lobe.
    expected_valid = np.zeros((2, 9, slots), dtype=bool)
    for tx, receiver_id in enumerate((0, 2)):
        expected_valid[tx, 4, receiver_ids.index(receiver_id)] = True
    np.testing.assert_array_equal(tensors["Valid"].reshape(2, 9, slots) != 0, expected_valid)
    hits = tensors["HitPosSensorM"].reshape(2, 9, slots, 3)
    relative = tensors["RxRelativePosM"].reshape(2, 9, slots, 3)
    distances = tensors["RoundTripDistanceM"].reshape(2, 9, slots)
    tx_positions = np.array([[0, -0.5, 0], [0, 0.5, 0]])
    rx_positions = np.array([[0, -0.4, 0], [0, 0, 0], [0, 0.4, 0]])[list(receiver_ids)]
    azimuth = np.radians(np.tile([-5, 0, 5], 3))
    elevation = np.radians(np.repeat([-5, 0, 5], 3))
    local_hits = np.column_stack((np.full(9, 11), 11 * np.tan(azimuth), 11 * np.tan(elevation) / np.cos(azimuth)))
    expected_hits = local_hits[None, :, None, :] + tx_positions[:, None, None, :]
    expected_hits = np.repeat(expected_hits, slots, axis=2)
    np.testing.assert_allclose(hits[expected_valid], expected_hits[expected_valid], atol=POSITION_ATOL)
    expected_relative = expected_hits - rx_positions
    np.testing.assert_allclose(relative[expected_valid], expected_relative[expected_valid], atol=POSITION_ATOL)
    outgoing = np.linalg.norm(expected_hits - tx_positions[:, None, None, :], axis=-1)
    returning = np.linalg.norm(expected_relative, axis=-1)
    np.testing.assert_allclose(distances[expected_valid], (outgoing + returning)[expected_valid], atol=5e-5, rtol=0)
    power = tensors["Power"].reshape(expected_valid.shape)[expected_valid]
    assert np.isfinite(power).all() and (power > 0).all()


def test_generic_wpm_acoustic_material_response(renderer, stage, example):
    _load(stage, "acoustic")
    mechanical, params = example.capture(renderer)
    _dimensions(mechanical, params, tx=1, rx=1)
    _write(stage, 2, waveType="electroMagnetic")
    electromagnetic, _ = example.capture(renderer, ordinal=2, steps=3)
    for tensors in (mechanical, electromagnetic):
        assert tensors["Valid"].tolist() == [1]
        np.testing.assert_allclose(tensors["HitPosSensorM"], [[11, 0, 0]], atol=POSITION_ATOL)
        assert np.isfinite(tensors["Power"]).all() and (tensors["Power"] > 0).all()
    # Normal-incidence steel/air impedance contrast, with diffuse albedo 0.4.
    steel_impedance = np.sqrt(8050 / 6.25e-12)
    air_impedance = 1.2041 * 343.21
    expected_power = ((steel_impedance - air_impedance) / (steel_impedance + air_impedance)) ** 2 * 0.6 / np.pi
    np.testing.assert_allclose(mechanical["Power"], [expected_power], atol=2e-4, rtol=0)
    assert not np.allclose(mechanical["Power"], electromagnetic["Power"], atol=1e-3)


def test_generic_wpm_mixed_selection_and_rejected_edit(renderer, stage, example):
    _load(stage, "mixed")
    states = (
        ((0, 0, 0), 1, 3, 1, (1, -1)),
        ((1, 1, 1), 2, 2, 3, (0.5,)),
        ((2, 1, 1), 1, 2, 9, (-0.5, 0.5)),
    )
    initial = None
    for ordinal, (selectors, tx, rx, rays, rx_y) in enumerate(states, start=2):
        example.select_patterns(stage, ordinal, *selectors)
        current = example.capture(renderer, ordinal=ordinal, steps=10 if initial is None else 3)
        tensors, params = current
        _dimensions(tensors, params, tx=tx, rx=rx, rays=rays, group=len(rx_y), selectors=selectors)
        assert tensors["Valid"].all()
        hits = tensors["HitPosSensorM"].reshape(tx, rays, len(rx_y), 3)
        receivers = np.array([[0, y, 0] for y in rx_y])
        np.testing.assert_allclose(hits[..., 0], 11, atol=POSITION_ATOL)
        np.testing.assert_allclose(
            tensors["RxRelativePosM"].reshape(hits.shape),
            hits - receivers,
            atol=POSITION_ATOL,
        )
        if initial is None:
            initial = current
    # The active two-element Rx pattern cannot supply receiver 2 on page 0.
    example.select_patterns(stage, 5, 0, 1, 0)
    rejected = example.capture(renderer, ordinal=5, steps=3)
    example.select_patterns(stage, 6, 0, 0, 0)
    recovered = example.capture(renderer, ordinal=6, steps=3)
    for expected, actual in ((current, rejected), (initial, recovered)):
        for name in ("Valid", "HitPosSensorM", "RxRelativePosM", "RoundTripDistanceM"):
            np.testing.assert_array_equal(actual[0][name], expected[0][name])
        for name in (
            "numTx",
            "numRx",
            "raysPerTx",
            "groupSize",
            "activeTxPatternIndex",
            "activeRxPatternIndex",
            "activeMappingPageIndex",
        ):
            np.testing.assert_array_equal(actual[1][name], expected[1][name])


def test_generic_wpm_initial_empty_and_recovery(renderer, stage, example):
    _load(
        stage,
        "mixed",
        """over "World" {
    over "Sensor" {
        uint omni:sensor:GenericWpm:activeRxPatternIndex = 1
    }
}
""",
    )
    tensors, params = example.capture(renderer)
    assert tensors["Valid"].size == 0
    assert all(values.shape[0] == 0 for values in tensors.values())
    assert int(params["maxContributions"].item()) == 0
    assert "activeTxPatternIndex" not in params
    example.select_patterns(stage, 2, 0, 0, 0)
    tensors, params = example.capture(renderer, ordinal=2, steps=3)
    _dimensions(tensors, params, tx=1, rx=3, group=2)
    assert tensors["Valid"].tolist() == [1, 1]


@pytest.mark.parametrize(
    "channel,expected",
    (("Power", {"Power", "Valid"}), ("HitVerticesM", {"HitVerticesM", "GeometryAreaM2", "Valid"})),
)
def test_generic_wpm_selected_channels(renderer, stage, example, channel, expected):
    _load(
        stage,
        "depth",
        f"""over "Render" {{
    over "GenericWpm" {{
        over "Contributions" {{
            token[] channels = ["{channel}"]
        }}
    }}
}}
""",
    )
    tensors, params = example.capture(renderer)
    assert set(tensors) == expected
    assert tensors["Valid"].tolist() == [1] * 15
    assert params["maxContributions"].item() == 15
    for name, values in tensors.items():
        assert values.shape == ((15, 3, 3) if name == "HitVerticesM" else (15,))
        assert values.dtype == (np.uint32 if name == "Valid" else np.float32)
        assert np.isfinite(values).all()
    if channel == "HitVerticesM":
        assert (tensors["GeometryAreaM2"] > 0).all()
    else:
        assert (tensors["Power"] > 0).all()


@pytest.mark.parametrize("recipe", ("depth", "mixed"))
def test_generic_wpm_example_headless(output_dir, recipe):
    output = output_dir / f"generic-wpm-{recipe}.npz"
    png = output_dir / "generic-wpm-depth.png"
    output.unlink(missing_ok=True)
    if recipe == "depth":
        png.unlink(missing_ok=True)
    completed = subprocess.run(
        [
            sys.executable,
            str(EXAMPLE / "main.py"),
            "--recipe",
            recipe,
            "--no-rr",
            "--output",
            str(output),
        ]
        + (["--png", str(png)] if recipe == "depth" else ["--live-edits"]),
        check=True,
        capture_output=True,
        text=True,
    )
    with np.load(output) as data:
        assert data["Valid"].shape == ((15,) if recipe == "depth" else (2,)) and data["Valid"].all()
        assert int(data["param_numTx"].item()) == (15 if recipe == "depth" else 1)
        assert data["param_activeTxPatternIndex"].item() == 0
    if recipe == "depth":
        with Image.open(png) as image:
            assert image.size == (750, 350)
            assert len(np.unique(np.asarray(image).reshape(-1, 3), axis=0)) > 10
    else:
        assert "requested=(0, 1, 0), accepted=(2, 1, 1), slots=18" in completed.stdout
        assert "requested=(0, 0, 0), accepted=(0, 0, 0), slots=2" in completed.stdout
