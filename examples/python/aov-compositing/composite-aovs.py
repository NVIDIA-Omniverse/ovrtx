#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Add seven linear RGB AOVs, apply ACES Approximation then sRGB, and compare.

Run uv run composite-aovs.py, or ./composite-aovs.sh.
No renderer or GPU is needed for this step. Inputs default to _output/aov/;
outputs are written to its composite/ directory. Inputs are never modified.
Alpha is neither added nor compared. No extra exposure or denoising is applied.
--check fails if ANY RGB channel differs from LdrColor.png by more than the
chosen 8-bit tolerance (default: one code value, or 1/255).
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import OpenEXR
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

# [snippet:doc-aov-compositing-inputs]
# Select radiance components explicitly: PtBackground and Pt*Filter are not additive inputs.
COMPONENTS = (
    "PtDirectIllumation",  # This spelling is the renderer's actual sourceName.
    "PtGlobalIllumination",
    "PtReflections",
    "PtRefractions",
    "PtSubsurfaceScattering",
    "PtSelfIllumination",
    "PtVolumes",
)
# [/snippet:doc-aov-compositing-inputs]


def read_rgb(path: Path) -> tuple[np.ndarray, list]:
    with OpenEXR.File(str(path), separate_channels=True) as image:
        if len(image.parts) != 1:
            raise ValueError(f"{path}: expected a single-part EXR")
        channels = image.channels()
        if not all(channel in channels for channel in "RGB"):
            raise ValueError(f"{path}: missing RGB channels")
        rgb = np.stack([channels[channel].pixels for channel in "RGB"], axis=-1).astype(np.float64)
        window = [np.asarray(value).tolist() for value in image.header()["dataWindow"]]
    if rgb.ndim != 3 or not rgb.size or not np.isfinite(rgb).all():
        raise ValueError(f"{path}: expected finite, non-empty RGB pixels")
    return rgb, window


# [snippet:doc-aov-compositing-display]
def srgb8(linear: np.ndarray) -> np.ndarray:
    # Encode only after summing and tone mapping; round once for the final 8-bit image.
    linear = np.clip(linear, 0.0, 1.0)
    encoded = np.where(linear <= 0.0031308, 12.92 * linear, 1.055 * linear ** (1.0 / 2.4) - 0.055)
    return np.rint(encoded * 255.0).astype(np.uint8)


def aces_approximation(linear: np.ndarray) -> np.ndarray:
    # Match this scene's ACES Approximation operator, with no second exposure multiplier.
    linear = np.maximum(linear, 0.0)
    return np.minimum(linear * (2.51 * linear + 0.03) / (linear * (2.43 * linear + 0.59) + 0.14), 1.0)


# [/snippet:doc-aov-compositing-display]


def save_png(path: Path, pixels: np.ndarray) -> None:
    info = PngImagePlugin.PngInfo()
    info.add(b"sRGB", b"\x00")
    Image.fromarray(pixels).save(path, pnginfo=info)


# [snippet:doc-aov-compositing-compare]
def compare(actual: np.ndarray, reference: np.ndarray, tolerance: float) -> dict:
    if actual.shape != reference.shape:
        raise ValueError(f"Image size mismatch: {actual.shape} vs {reference.shape}")
    # The threshold applies to every RGB channel, not just the average error.
    difference = actual.astype(np.float64) - reference.astype(np.float64)
    absolute = np.abs(difference)
    per_pixel = absolute.max(axis=-1)
    return {
        "exact_match": bool(np.all(absolute == 0)),
        "tolerance": tolerance,
        "within_tolerance": bool(np.all(absolute <= tolerance)),
        "mae": float(absolute.mean()),
        "rmse": float(np.sqrt(np.mean(difference**2))),
        "max_absolute_error": float(absolute.max()),
        "p99_absolute_error": float(np.percentile(absolute, 99)),
        "exact_pixels_percent": float(100 * np.mean(per_pixel == 0)),
        "pixels_within_tolerance_percent": float(100 * np.mean(per_pixel <= tolerance)),
    }


# [/snippet:doc-aov-compositing-compare]


def save_comparison(output: Path, name: str, pixels: np.ndarray, reference: np.ndarray, tolerance: int) -> dict:
    metrics = compare(pixels, reference, tolerance)
    absolute = np.abs(pixels.astype(np.int16) - reference.astype(np.int16))
    save_png(output / f"{name}.difference.png", absolute.astype(np.uint8))
    difference_x4 = np.minimum(absolute * 4, 255).astype(np.uint8)
    panels = [("LdrColor.png", reference), (name, pixels), ("Absolute RGB difference x4", difference_x4)]
    width = min(640, reference.shape[1])
    height = round(reference.shape[0] * width / reference.shape[1])
    sheet = Image.new("RGB", (width * 3, height + 56), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    for index, (label, data) in enumerate(panels):
        draw.text((index * width + 10, 10), label, fill="white")
        sheet.paste(Image.fromarray(data).resize((width, height), Image.Resampling.LANCZOS), (index * width, 30))
    draw.text(
        (10, height + 37),
        f"RGB 8-bit: MAE {metrics['mae']:.4f}, max {metrics['max_absolute_error']:.0f}; metrics use full resolution",
        fill="white",
    )
    save_png(output / f"{name}.comparison.png", np.asarray(sheet))
    return metrics


def save_catalog(output: Path, paths: list[Path], composite: np.ndarray) -> None:
    """Show each contribution with the same display transform as the final sum."""
    # Use the linear EXRs, not the render script's Reinhard previews. Do not normalize individual passes.
    panels = [(path.stem, srgb8(aces_approximation(read_rgb(path)[0]))) for path in paths]
    panels.append(("Final composite", composite))
    width = min(640, composite.shape[1])
    height = round(composite.shape[0] * width / composite.shape[1])
    gap, label_height = 16, 48
    rows = (len(panels) + 1) // 2
    sheet = Image.new("RGB", (2 * width + 3 * gap, rows * (height + label_height) + (rows + 1) * gap), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=28)
    for index, (label, pixels) in enumerate(panels):
        x = gap + (index % 2) * (width + gap)
        y = gap + (index // 2) * (height + label_height + gap)
        draw.text((x + 12, y + 8), label, font=font, fill="white")
        preview = Image.fromarray(pixels).resize((width, height), Image.Resampling.LANCZOS)
        sheet.paste(preview, (x, y + label_height))
    save_png(output / "aov-catalog.png", np.asarray(sheet))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--aov-dir", type=Path, default=Path(__file__).resolve().parent / "_output" / "aov")
    parser.add_argument("--output-dir", type=Path, help="Default: AOV_DIR/composite")
    parser.add_argument(
        "--tolerance", type=int, default=1, help="Maximum allowed RGB code-value error (default: 1/255)"
    )
    parser.add_argument("--png", type=Path, help="Optional additional path for the composite PNG")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.tolerance <= 255:
        parser.error("--tolerance must be between 0 and 255")
    aov_dir = args.aov_dir.expanduser().resolve()
    paths = [aov_dir / f"{name}.exr" for name in COMPONENTS]
    missing = [path.name for path in paths if not path.is_file()]
    if missing:
        parser.error(f"Missing required components in {aov_dir}: {', '.join(missing)}")
    output = (args.output_dir or aov_dir / "composite").expanduser().resolve()
    if output == aov_dir:
        parser.error("Use a separate output directory to keep the input AOVs untouched")
    reference_path = aov_dir / "LdrColor.png"
    with Image.open(reference_path) as image:
        reference = np.asarray(image.convert("RGB"))
    # [snippet:doc-aov-compositing-sum]
    # Read unmodified EXR RGB values. Preview PNGs have already been transformed.
    total = None
    inputs = []
    for path in paths:
        rgb, data_window = read_rgb(path)
        if total is None:
            total = np.zeros_like(rgb)
            expected_window = data_window
        if rgb.shape != total.shape or data_window != expected_window:
            raise ValueError(f"{path}: EXR dimensions/dataWindow differ from the other inputs")
        total += rgb
        inputs.append({"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    if total.shape != reference.shape:
        raise ValueError(f"EXR/PNG size mismatch: {total.shape} vs {reference.shape}")
    if not np.isfinite(total).all():
        raise ValueError("The AOV sum contains non-finite values")
    # [/snippet:doc-aov-compositing-sum]
    output.mkdir(parents=True, exist_ok=True)
    channels = {
        channel: np.ascontiguousarray(total[..., index], dtype=np.float32) for index, channel in enumerate("RGB")
    }
    header = {
        "compression": OpenEXR.ZIP_COMPRESSION,
        "type": OpenEXR.scanlineimage,
        "dataWindow": tuple(np.asarray(value, dtype=np.int32) for value in expected_window),
    }
    with OpenEXR.File(header, channels) as image:
        image.write(str(output / "sum.exr"))
    result = srgb8(aces_approximation(total))
    save_png(output / "sum.aces-srgb.png", result)
    save_catalog(output, paths, result)
    if args.png:
        png_path = args.png.expanduser().resolve()
        if png_path == reference_path or png_path in paths or png_path == aov_dir / "HdrColor.exr":
            parser.error("--png cannot overwrite an input image")
        png_path.parent.mkdir(parents=True, exist_ok=True)
        save_png(png_path, result)
    report = {
        "operation": "Add seven radiance AOV RGB values in linear space, then ACES Approximation, sRGB, and uint8 rounding",
        "alpha": "Ignored; RGB radiance addition and RGB comparison only",
        "aov_directory": str(aov_dir),
        "inputs": inputs,
        "reference": {"file": reference_path.name, "sha256": hashlib.sha256(reference_path.read_bytes()).hexdigest()},
        "resolution": [total.shape[1], total.shape[0]],
        "display_error_units": "8-bit RGB code values (0-255)",
        "sum_aces_srgb_vs_ldr": save_comparison(output, "sum.aces-srgb", result, reference, args.tolerance),
    }
    hdr_path = aov_dir / "HdrColor.exr"
    hdr = None
    if hdr_path.is_file():
        hdr, hdr_window = read_rgb(hdr_path)
        if hdr_window != expected_window:
            raise ValueError("HdrColor dataWindow differs from the PT inputs")
        report["hdr_reference_sha256"] = hashlib.sha256(hdr_path.read_bytes()).hexdigest()
        report["sum_linear_vs_hdr"] = compare(total, hdr, 0.0)
        report["sum_linear_vs_hdr"]["error_units"] = "Linear renderer RGB values"
    if hdr is not None:
        pixels = srgb8(aces_approximation(hdr))
        save_png(output / "hdr.aces-srgb.png", pixels)
        report["hdr_aces_srgb_vs_ldr"] = save_comparison(output, "hdr.aces-srgb", pixels, reference, args.tolerance)
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for key in ("sum_aces_srgb_vs_ldr", "hdr_aces_srgb_vs_ldr"):
        if key in report:
            stats = report[key]
            status = "MATCH within tolerance" if stats["within_tolerance"] else "MISMATCH"
            print(
                f"{key}: {status}; MAE={stats['mae']:.6f}, max={stats['max_absolute_error']:.0f}, exact={stats['exact_match']}"
            )
    print(f"Added {len(paths)} AOVs. Results: {output}")
    return int(args.check and not report["sum_aces_srgb_vs_ldr"]["within_tolerance"])


if __name__ == "__main__":
    raise SystemExit(main())
