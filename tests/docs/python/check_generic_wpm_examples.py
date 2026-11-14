# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Run Generic WPM examples and validate newly written CSV or NPZ outputs."""

import argparse
import csv
import math
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path


def expected_slots(recipe, ordinal=1):
    if recipe == "depth":
        shape = (1, 15, 1, 1, 1)
    elif recipe == "gaussian_bloom":
        shape = (1, 15, 9, 1, 9)
    else:
        shape = ((1, 1, 1, 1, 2), (1, 2, 3, 1, 1), (1, 1, 9, 1, 2), (1, 1, 9, 1, 2), (1, 1, 1, 1, 2))[ordinal - 1]
    slots = set(range(math.prod(shape)))
    if recipe == "gaussian_bloom":
        slots = {
            (tx * 9 + ray) * 9 + slot
            for tx in range(15)
            for ray in range(9)
            for slot in range(9)
            if 0 <= tx // 5 + slot // 3 - 1 < 3 and 0 <= tx % 5 + slot % 3 - 1 < 5
        }
    return shape, slots


def validate_csv(path, recipe):
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    ordinals = range(1, 6) if recipe == "mixed" else (1,)
    if {int(row["ordinal"]) for row in rows} != set(ordinals):
        raise RuntimeError(f"Missing or unexpected capture ordinals in {path}")
    for ordinal in ordinals:
        shape, expected = expected_slots(recipe, ordinal)
        capture = [row for row in rows if int(row["ordinal"]) == ordinal]
        if len(capture) != len(expected) or {int(row["slot"]) for row in capture} != expected:
            raise RuntimeError(f"Missing, repeated or unexpected valid slots at ordinal {ordinal}: {path}")
        for row in capture:
            coordinates = tuple(int(row[name]) for name in ("tile", "tx", "ray", "bounce", "rx_slot"))
            slot = 0
            for coordinate, size in zip(coordinates, shape):
                if not 0 <= coordinate < size:
                    raise RuntimeError(f"Invalid dense slot coordinate: {row}")
                slot = slot * size + coordinate
            distance = float(row["round_trip_m"])
            position = [float(row[name]) for name in ("hit_world_x", "hit_world_y", "hit_world_z")]
            if slot != int(row["slot"]) or not all(math.isfinite(x) for x in (distance, *position)) or distance <= 0:
                raise RuntimeError(f"Invalid contribution payload: {row}")
            if recipe == "depth":
                depth = float(row["range_m"])
                if not math.isfinite(depth) or abs(depth - distance / 2) > 1e-5:
                    raise RuntimeError(f"Incorrect depth range: {row}")
                if slot == 7 and abs(distance / 2 - 11) > 1e-3:
                    raise RuntimeError(f"Expected 11 m centre range: {row}")
            elif row["range_m"]:
                raise RuntimeError("Range must be blank for the bloom and mixed CSV recipes")


def validate_npz(path, recipe):
    import numpy as np

    shape, expected = expected_slots(recipe, 5 if recipe == "mixed" else 1)
    with np.load(path, allow_pickle=False) as data:
        observed = tuple(
            int(data[f"param_{name}"].item()) for name in ("numTiles", "numTx", "raysPerTx", "maxBounces", "groupSize")
        )
        valid = data["Valid"]
        if observed != shape or valid.shape != (math.prod(shape),) or valid.dtype != np.uint32:
            raise RuntimeError(f"Unexpected contribution shape/type: {path}")
        if set(np.flatnonzero(valid)) != expected:
            raise RuntimeError(f"Incorrect valid-slot mask: {path}")
        if any(
            int(data[f"param_{name}"].item()) != 0
            for name in ("activeTxPatternIndex", "activeRxPatternIndex", "activeMappingPageIndex")
        ):
            raise RuntimeError(f"Expected the initial/recovered selector triplet: {path}")
        distances = data["RoundTripDistanceM"]
        positions = data["HitPosWorld"]
        if (
            distances.shape != valid.shape
            or positions.shape != (valid.size, 3)
            or distances.dtype != np.float32
            or positions.dtype != np.float32
        ):
            raise RuntimeError(f"Invalid channel dimensions: {path}")
        if (
            not np.isfinite(positions[valid != 0]).all()
            or not np.isfinite(distances[valid != 0]).all()
            or not np.all(distances[valid != 0] > 0)
        ):
            raise RuntimeError(f"Invalid contribution payload: {path}")
        if recipe == "depth" and abs(float(distances[7]) / 2 - 11) > 1e-3:
            raise RuntimeError(f"Expected 11 m centre range: {path}")


def _run_recipe(public_root, output_dir, program, language, recipe, *, c_binary):
    output = output_dir / f"{language}-generic-wpm-{recipe}.{'csv' if c_binary else 'npz'}"
    png = output.with_suffix(".png")
    log = output.with_suffix(".console.log")
    output.unlink(missing_ok=True)
    png.unlink(missing_ok=True)
    log.unlink(missing_ok=True)
    if not program.is_file():
        raise FileNotFoundError(f"Generic WPM example is missing: {program}")
    if c_binary:
        command = [str(program), str(public_root), recipe, str(output)]
    else:
        command = [sys.executable, str(program), "--recipe", recipe, "--no-rr", "--output", str(output)]
        if recipe == "depth":
            command += ["--png", str(png)]
    if recipe == "mixed":
        command += ["--live-edits"]
    try:
        result = subprocess.run(command, cwd=output_dir, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired as exc:
        log.write_text("".join(part.decode(errors="replace") if isinstance(part, bytes) else part or ""
                               for part in (exc.stdout, exc.stderr)), encoding="utf-8")
        raise
    log.write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"Generic WPM {recipe} failed ({result.returncode}); see {log}")
    if c_binary:
        validate_csv(output, recipe)
    else:
        validate_npz(output, recipe)
        if recipe == "depth":
            from PIL import Image, ImageStat

            with Image.open(png) as image:
                if image.format != "PNG" or image.size != (750, 350) or max(ImageStat.Stat(image).stddev) <= 5:
                    raise RuntimeError(f"Expected a labelled 750x350 range grid: {png}")
    if recipe == "mixed":
        summary = re.sub(r"\s+", "", result.stdout)
        rejected = "requested=0/1/0accepted=2/1/1" if c_binary else "requested=(0,1,0),accepted=(2,1,1),slots=18"
        if rejected not in summary:
            raise RuntimeError(f"Missing rejected-edit retention summary; see {log}")
    print(f"Validated {language} Generic WPM {recipe}: {output}")


def run_examples(public_root, output_dir, *, c_binary=None, python_example=None, junitxml=None):
    public_root, output_dir = public_root.resolve(), output_dir.resolve()
    program = (c_binary or python_example).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    language = "c" if c_binary else "python"
    suite = ET.Element("testsuite", name=f"generic-wpm-{language}")
    for recipe in ("depth", "gaussian_bloom", "mixed"):
        case = ET.SubElement(suite, "testcase", classname=f"examples/{language}/generic-wpm", name=recipe, time="0")
        ET.SubElement(case, "skipped", message="Not run because an earlier recipe failed")
    if junitxml is not None:
        junitxml.parent.mkdir(parents=True, exist_ok=True)
        junitxml.unlink(missing_ok=True)
    try:
        for case in suite:
            case.remove(case.find("skipped"))
            recipe = case.get("name")
            started = time.monotonic()
            try:
                _run_recipe(public_root, output_dir, program, language, recipe, c_binary=c_binary)
            except Exception as exc:
                ET.SubElement(case, "failure", type=type(exc).__name__, message=str(exc)).text = str(exc)
                raise
            finally:
                case.set("time", str(time.monotonic() - started))
                log = output_dir / f"{language}-generic-wpm-{recipe}.console.log"
                if log.is_file():
                    ET.SubElement(case, "system-out").text = log.read_text(encoding="utf-8")
    finally:
        if junitxml is not None:
            suite.set("tests", str(len(suite)))
            suite.set("failures", str(len(suite.findall("testcase/failure"))))
            suite.set("skipped", str(len(suite.findall("testcase/skipped"))))
            suite.set("time", str(sum(float(case.get("time")) for case in suite)))
            # Console output may contain ANSI control bytes, which XML 1.0 forbids.
            for element in suite.iter():
                if element.text:
                    element.text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", element.text)
                for key, value in element.attrib.items():
                    element.set(key, re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value))
            ET.ElementTree(suite).write(junitxml, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("public_root", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--junitxml", type=Path, help="Write per-recipe results for CI publication")
    program = parser.add_mutually_exclusive_group(required=True)
    program.add_argument("--c-binary", type=Path)
    program.add_argument("--python-example", type=Path)
    args = parser.parse_args()
    run_examples(args.public_root, args.output_dir, c_binary=args.c_binary, python_example=args.python_example,
                 junitxml=args.junitxml)
