# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow==12.1.1"]
# ///
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Run the packaged C Minimal DLSS example and validate its freshly written PNG."""

import argparse
import subprocess
from pathlib import Path

from PIL import Image, ImageStat


def run_example(binary: Path, scene: Path, output_dir: Path) -> None:
    binary = binary.resolve()
    scene = scene.resolve()
    output_dir = output_dir.resolve()
    if not binary.is_file():
        raise FileNotFoundError(f"Packaged C Minimal DLSS example is missing: {binary}")
    if not scene.is_file():
        raise FileNotFoundError(f"Minimal DLSS scene is missing: {scene}")

    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "c-minimal-dlss.png"
    output.unlink(missing_ok=True)
    command = [str(binary), str(scene), str(output)]
    log_path = output_dir / "c-minimal-dlss.log"
    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"Running command: {command}\n")
        log.flush()
        subprocess.run(command, cwd=output_dir, stdout=log, stderr=subprocess.STDOUT, timeout=600, check=True)

    with Image.open(output) as image:
        if image.format != "PNG" or image.size != (1280, 720):
            raise RuntimeError(f"Expected a 1280x720 PNG, got {image.format} {image.size}: {output}")
        image.load()
        # Measure variation within each channel: a solid colored image is also a failure.
        if max(ImageStat.Stat(image.convert("RGB")).stddev) <= 5:
            raise RuntimeError(f"Expected visible geometry and texture detail in {output}")
    print(f"Validated C Minimal DLSS output: {output}; renderer log: {log_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("scene", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    run_example(args.binary, args.scene, args.output_dir)
