# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow==12.1.1"]
# ///
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""Render with both packaged C loaders and verify the splats against a hidden baseline."""

import argparse
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


def run_examples(binary_root: Path, scene: Path, output_dir: Path) -> None:
    scene = scene.resolve()
    output_dir = output_dir.resolve()
    if not scene.is_file():
        raise FileNotFoundError(f"Gaussian example scene is missing: {scene}")
    output_dir.mkdir(parents=True, exist_ok=True)
    hidden_scene = output_dir / "c-gaussian-splats-hidden.usda"
    hidden_scene.write_text(
        '#usda 1.0\n(subLayers = [@' + scene.as_posix() + '@])\n'
        'over "World" {\n over "Splats" {\n token visibility = "invisible"\n }\n }\n',
        encoding="utf-8",
    )
    for model, name in (("static", "gaussian-splats"), ("shared", "gaussian-splats-dynamic")):
        binary_dir = binary_root / model
        if sys.platform == "win32":
            binary_dir /= "Release"
            name += ".exe"
        binary = (binary_dir / name).resolve()
        if not binary.is_file():
            raise FileNotFoundError(f"Packaged C Gaussian example is missing: {binary}")
        if sys.platform != "win32":
            binary.chmod(0o755)
        images = []
        for state, source in (("visible", scene), ("hidden", hidden_scene)):
            output = output_dir / f"c-gaussian-splats-{model}-{state}.png"
            output.unlink(missing_ok=True)
            log_path = output.with_suffix(".log")
            with log_path.open("w", encoding="utf-8") as log:
                subprocess.run(
                    [str(binary), str(source), str(output)], cwd=output_dir,
                    stdout=log, stderr=subprocess.STDOUT, timeout=600, check=True,
                )
            with Image.open(output) as image:
                if image.format != "PNG" or image.size != (768, 512):
                    raise RuntimeError(f"Expected a 768x512 PNG, got {image.format} {image.size}: {output}")
                images.append(image.convert("RGB"))
        difference = sum(ImageStat.Stat(ImageChops.difference(*images)).mean) / 3
        if difference <= 8:
            raise RuntimeError(f"Gaussian splats are missing: difference={difference}; see {output_dir}")
        print(f"Validated {name}: visible/hidden difference={difference:.3f}; outputs: {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary_root", type=Path)
    parser.add_argument("scene", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    run_examples(args.binary_root, args.scene, args.output_dir)
