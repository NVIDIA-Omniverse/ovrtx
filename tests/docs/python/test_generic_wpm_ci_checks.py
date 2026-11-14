# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""CPU-only validation of the Generic WPM example artifact checks."""

import csv
from pathlib import Path
import subprocess
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from check_generic_wpm_examples import expected_slots, run_examples, validate_csv, validate_npz


def _rows(recipe):
    rows = []
    for ordinal in range(1, 6) if recipe == "mixed" else (1,):
        shape, slots = expected_slots(recipe, ordinal)
        for slot in sorted(slots):
            row = dict(zip(("tile", "tx", "ray", "bounce", "rx_slot"), np.unravel_index(slot, shape)))
            row.update(
                ordinal=ordinal,
                slot=slot,
                round_trip_m=22,
                hit_world_x=11,
                hit_world_y=0,
                hit_world_z=0,
                range_m=11 if recipe == "depth" else "",
            )
            rows.append(row)
    return rows


def _write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


@pytest.mark.parametrize("recipe", ("depth", "gaussian_bloom", "mixed"))
def test_csv_valid_recipes(tmp_path, recipe):
    path = tmp_path / "output.csv"
    _write_csv(path, _rows(recipe))
    validate_csv(path, recipe)


@pytest.mark.parametrize("fault", ("missing", "duplicate", "coordinate", "nonfinite", "range_nan", "wrong_mask"))
def test_csv_rejects_bad_outputs(tmp_path, fault):
    path = tmp_path / "output.csv"
    recipe = "gaussian_bloom" if fault == "wrong_mask" else "depth"
    rows = _rows(recipe)
    if fault == "missing":
        rows.pop()
    elif fault == "duplicate":
        rows[-1] = rows[0].copy()
    elif fault == "coordinate":
        rows[0]["tx"] = 999
    elif fault == "nonfinite":
        rows[0]["round_trip_m"] = "inf"
    elif fault == "range_nan":
        rows[0]["range_m"] = "nan"
    else:
        rows[0]["slot"] = 0  # A clipped corner slot, not a valid receiver.
    _write_csv(path, rows)
    with pytest.raises(RuntimeError):
        validate_csv(path, recipe)


@pytest.mark.parametrize("fault", (None, "distance_inf", "position_nan", "dtype", "mask"))
def test_npz_validation(tmp_path, fault):
    path = tmp_path / "output.npz"
    data = {
        "Valid": np.ones(15, np.uint32),
        "RoundTripDistanceM": np.full(15, 22, np.float32),
        "HitPosWorld": np.zeros((15, 3), np.float32),
        **{
            f"param_{name}": np.array([value], np.uint32)
            for name, value in zip(("numTiles", "numTx", "raysPerTx", "maxBounces", "groupSize"), (1, 15, 1, 1, 1))
        },
        **{
            f"param_{name}": np.array([0], np.uint32)
            for name in ("activeTxPatternIndex", "activeRxPatternIndex", "activeMappingPageIndex")
        },
    }
    if fault == "distance_inf":
        data["RoundTripDistanceM"][0] = np.inf
    elif fault == "position_nan":
        data["HitPosWorld"][0, 0] = np.nan
    elif fault == "dtype":
        data["HitPosWorld"] = data["HitPosWorld"].astype(np.float64)
    elif fault == "mask":
        data["Valid"][0] = 0
    np.savez(path, **data)
    if fault is None:
        validate_npz(path, "depth")
    else:
        with pytest.raises(RuntimeError):
            validate_npz(path, "depth")


def test_missing_binary_is_not_skipped(tmp_path):
    with pytest.raises(FileNotFoundError, match="example is missing"):
        run_examples(tmp_path, tmp_path / "output", c_binary=tmp_path / "missing")


def test_stale_output_cannot_hide_missing_new_output(tmp_path, monkeypatch):
    binary = tmp_path / "generic-wpm"
    binary.touch()
    stale = tmp_path / "c-generic-wpm-depth.csv"
    _write_csv(stale, _rows("depth"))
    monkeypatch.setattr(
        "check_generic_wpm_examples.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )
    with pytest.raises(FileNotFoundError):
        run_examples(tmp_path, tmp_path, c_binary=binary)
    assert not stale.exists()


def test_junit_records_validated_recipes_and_their_logs(tmp_path, monkeypatch):
    binary = tmp_path / "generic-wpm"
    binary.touch()
    report = tmp_path / "results.xml"

    def run(command, **kwargs):
        recipe = command[2]
        _write_csv(Path(command[3]), _rows(recipe))
        summary = "requested=0/1/0 accepted=2/1/1" if recipe == "mixed" else recipe
        return SimpleNamespace(returncode=0, stdout=summary, stderr="")

    monkeypatch.setattr("check_generic_wpm_examples.subprocess.run", run)
    run_examples(tmp_path, tmp_path, c_binary=binary, junitxml=report)
    suite = ET.parse(report).getroot()
    assert suite.get("tests") == "3" and suite.get("failures") == suite.get("skipped") == "0"
    cases = list(suite)
    assert [case.get("name") for case in cases] == ["depth", "gaussian_bloom", "mixed"]
    assert all(case.get("classname") == "examples/c/generic-wpm" for case in cases)
    assert all(float(case.get("time")) >= 0 and case.findtext("system-out") for case in cases)


@pytest.mark.parametrize("fault", ("exit", "timeout", "invalid_output"))
def test_junit_preserves_failure_and_skips_unexecuted_recipes(tmp_path, monkeypatch, fault):
    binary = tmp_path / "generic-wpm"
    binary.touch()
    report = tmp_path / "results.xml"
    report.write_text('<testsuite><testcase name="stale-pass"/></testsuite>')
    calls = []

    def run(command, **kwargs):
        recipe = command[2]
        calls.append(recipe)
        rows = _rows(recipe)
        if recipe == "gaussian_bloom":
            if fault == "timeout":
                raise subprocess.TimeoutExpired(command, 600, output=b"partial output", stderr=b"timeout detail")
            if fault == "exit":
                return SimpleNamespace(returncode=1, stdout="\x1b[31mfailed", stderr=" & reason <here>")
            rows.pop()
        _write_csv(Path(command[3]), rows)
        return SimpleNamespace(returncode=0, stdout=recipe, stderr="")

    monkeypatch.setattr("check_generic_wpm_examples.subprocess.run", run)
    with pytest.raises((RuntimeError, subprocess.TimeoutExpired)):
        run_examples(tmp_path, tmp_path, c_binary=binary, junitxml=report)
    assert calls == ["depth", "gaussian_bloom"]
    suite = ET.parse(report).getroot()
    assert suite.get("tests") == "3" and suite.get("failures") == suite.get("skipped") == "1"
    depth, bloom, mixed = list(suite)
    assert depth.find("failure") is None and depth.find("skipped") is None
    assert bloom.find("failure") is not None and bloom.findtext("system-out")
    assert mixed.find("skipped") is not None and mixed.find("system-out") is None
    assert "stale-pass" not in report.read_text()
    if fault == "timeout":
        assert bloom.findtext("system-out") == "partial outputtimeout detail"
    elif fault == "exit":
        assert bloom.findtext("system-out") == "[31mfailed & reason <here>"


@pytest.mark.parametrize("language", ("c", "python"))
def test_junit_reports_missing_program_as_failure(tmp_path, language):
    report = tmp_path / "results.xml"
    program = {"c_binary" if language == "c" else "python_example": tmp_path / "missing"}
    with pytest.raises(FileNotFoundError):
        run_examples(tmp_path, tmp_path, junitxml=report, **program)
    suite = ET.parse(report).getroot()
    assert suite.get("failures") == "1" and suite.get("skipped") == "2"
    assert all(case.get("classname") == f"examples/{language}/generic-wpm" for case in suite)
