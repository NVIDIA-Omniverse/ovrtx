# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow==12.1.1"]
# ///
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Validate fresh RGB and spectral PNGs from the extracted C example artifact."""

import argparse
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


def run_example(binary, output_dir):
    """Fail on missing deployment inputs or missing/constant renders."""
    binary = binary.resolve()
    if not binary.is_file():
        raise FileNotFoundError(binary)
    for asset in (
        "spectral.usda",
        "data/ovrtx-light-test-rect.usda",
        "data/ground.usd",
        "data/lookdev_grid_10k.png",
        "data/balls/balls.usd",
        "data/colorchecker/colorchecker.usd",
        "data/colorchecker/colorchecker.png",
    ):
        if not (binary.parent / asset).is_file():
            raise FileNotFoundError(binary.parent / asset)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    images = {}
    for transport, spp in (("rgb", 512), ("spectral", 512), ("rgb", 2048), ("spectral", 2048)):
        output = output_dir / f"c-spectral-{transport}-{spp}.png"
        output.unlink(missing_ok=True)
        with output.with_suffix(".log").open("w") as log:
            subprocess.run(
                [str(binary), "sodium", transport, str(spp), str(output)],
                cwd=output_dir,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=900,
            )
        with Image.open(output) as image:
            image.load()
            if image.size != (512, 512) or image.format != "PNG":
                raise RuntimeError(f"Invalid PNG dimensions/format: {output}")
            image = image.convert("RGB")
            if max(ImageStat.Stat(image).stddev) <= 5:
                raise RuntimeError(f"Constant image: {output}")
            images[transport, spp] = image.resize((16, 16), Image.Resampling.BOX)
    # Compare low-frequency transport differences with both sample-count convergence changes.
    convergence = max(
        sum(ImageStat.Stat(ImageChops.difference(images[t, 512], images[t, 2048])).mean) / 3
        for t in ("rgb", "spectral")
    )
    effect = sum(ImageStat.Stat(ImageChops.difference(images["rgb", 2048], images["spectral", 2048])).mean) / 3
    if effect <= max(3 * convergence, 0.25):
        raise RuntimeError(f"Transport effect {effect} does not exceed convergence change {convergence}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    run_example(args.binary, args.output_dir)
