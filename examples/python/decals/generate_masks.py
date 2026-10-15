# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Regenerate cutout textures from the original logo artwork.

Run: uv run --no-project --with pillow generate_masks.py
This asset-authoring utility is not required to run main.py.
"""

from pathlib import Path

from PIL import Image

DATA = Path(__file__).resolve().parents[3] / "tests/docs/data"
ARTWORK = Path(__file__).resolve().parent / "artwork"
SIZE = 1024


def save_mask(mask, filename):
    """Fit the artwork into a square without changing its aspect ratio."""
    bounds = mask.getbbox()
    if bounds is None:
        raise ValueError(f"Empty mask: {filename}")
    mask = mask.crop(bounds)
    mask.thumbnail((922, 922), Image.Resampling.LANCZOS)
    # thumbnail() only shrinks; enlarge the small RTX reference consistently.
    scale = 922 / max(mask.size)
    mask = mask.resize(tuple(round(size * scale) for size in mask.size), Image.Resampling.LANCZOS)
    canvas = Image.new("L", (SIZE, SIZE), 0)
    canvas.paste(mask, ((SIZE - mask.width) // 2, (SIZE - mask.height) // 2))
    canvas.save(DATA / filename)


def main():
    # The NVIDIA source already has an exact alpha silhouette, independent of ink color.
    with Image.open(ARTWORK / "nvidia.png") as source:
        save_mask(source.getchannel("A"), "decal-nvidia-mask.png")
    # Remove the dark background of the supplied RTX reference, preserving edge coverage.
    with Image.open(ARTWORK / "rtx.png") as source:
        mask = source.convert("L").point(lambda value: round(max(0, min(1, (value - 64) / 136)) * 255))
        save_mask(mask, "decal-rtx-mask.png")


if __name__ == "__main__":
    main()
