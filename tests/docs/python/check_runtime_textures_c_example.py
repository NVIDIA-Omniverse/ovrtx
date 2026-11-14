# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow==12.1.1"]
# ///
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""Validate fresh red/green outputs from both packaged C loader models."""
import argparse
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageStat, ImageChops


def run_examples(binary_root, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    reference = None
    for model, name in (("static", "runtime-textures"), ("shared", "runtime-textures-dynamic")):
        directory = binary_root / model
        if sys.platform == "win32":
            directory /= "Release"
            name += ".exe"
        binary = (directory / name).resolve()
        if not binary.is_file():
            raise FileNotFoundError(f"Missing packaged runtime-textures binary: {binary}")
        if sys.platform != "win32":
            binary.chmod(0o755)
        states = [binary.parent / f"runtime-textures{suffix}.png" for suffix in ("_before", "")]
        for path in states:
            path.unlink(missing_ok=True)
        label = f"{model}-cuda"
        with (output_dir / f"{label}.log").open("w") as log:
            subprocess.run([str(binary)], cwd=binary.parent,
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=600)
        images = []
        for channel, path in enumerate(states):
            with Image.open(path) as image:
                assert image.format == "PNG" and image.size == (512, 512), path
                image = image.convert("RGB")
                mean = ImageStat.Stat(image.crop((64, 64, 448, 448))).mean
                assert all(mean[channel] > mean[c] + 60 for c in range(3) if c != channel), mean
                image.save(output_dir / f"{label}-{'red' if channel == 0 else 'green'}.png")
                images.append(image)
        if reference is not None:
            # Independent startup noise is allowed, but both loader models must show the same result.
            for expected, actual in zip(reference, images):
                assert max(ImageStat.Stat(ImageChops.difference(expected, actual)).mean) < 3
        reference = images
        print(f"Validated {label}: fresh 512x512 red and green frames")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary_root", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    run_examples(args.binary_root.resolve(), args.output_dir.resolve())
