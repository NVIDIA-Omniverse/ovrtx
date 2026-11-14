# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow==12.1.1"]
# ///
"""Build the contact sheet from the camera-calibration example's input photographs.

Run: uv run --script build_calibration_contact_sheet.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PUBLIC = Path(__file__).resolve().parents[4]
INPUTS = PUBLIC / "examples/python/camera-calibration/input_images"
OUTPUT = Path(__file__).with_name("calibration-inputs.avif")

photos = sorted(INPUTS.glob("*.png"), key=lambda p: int(p.stem.rsplit("_", 1)[1]))
width, height, label_height, gap = 480, 384, 36, 8
columns = 4
rows = (len(photos) + columns - 1) // columns
sheet = Image.new("RGB", (columns * (width + gap) - gap, rows * (height + label_height + gap) - gap), "white")
draw = ImageDraw.Draw(sheet)
font = ImageFont.load_default(size=20)
for i, path in enumerate(photos):
    x, y = (i % columns) * (width + gap), (i // columns) * (height + label_height + gap)
    with Image.open(path) as photo:
        tile = photo.convert("RGB")
        tile.thumbnail((width, height), Image.Resampling.LANCZOS)
        sheet.paste(tile, (x + (width - tile.width) // 2, y + (height - tile.height) // 2))
    draw.text((x + 10, y + height + 6), path.stem.rsplit("_", 1)[1], font=font, fill="#222222")
sheet.save(OUTPUT, quality=80, subsampling="4:4:4", speed=6)
print(OUTPUT)
