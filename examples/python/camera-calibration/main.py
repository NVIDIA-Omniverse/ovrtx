#!/usr/bin/env python3
"""Camera intrinsic calibration: checkerboard photos -> OpenCV intrinsics -> USD camera.

Given a folder of checkerboard photos, this script:

  1. detects the checkerboard corners in every photo (OpenCV),
  2. solves the camera intrinsics -- focal length, principal point and lens
     distortion coefficients (pinhole or fisheye), and
  3. writes a USD Camera prim carrying those values.

The output applies the dedicated OpenCV lens-distortion API schema
(``OmniLensDistortionOpenCvPinholeAPI`` or
``OmniLensDistortionOpenCvFisheyeAPI``) and carries the
``omni:lensdistortion:opencv*`` attributes (``fx``/``fy``/``cx``/``cy``,
``k1..k6``, ``p1``/``p2``, ``s1..s4``) straight from the OpenCV K/D. RTX projects
through these. The prim also sets the standard ``UsdGeom.Camera`` attributes so
it stays viewable in any USD tool.

Both pinhole and fisheye cameras are supported; ``--fisheye`` selects the fisheye
model. The lens-distortion schema attributes hold the calibrated lens and are
what RTX renders from.

Requires opencv-python, numpy and usd-core.

The example photos are the checkerboard shots in ``input_images/`` next to this
script (the default for ``--images``), so the example runs with just::

    uv run main.py --fisheye \
        --output-usd ./_out/calibrated_camera.usda
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
from pathlib import Path

import cv2
import numpy as np

_IMAGE_GLOBS = ("*.png", "*.jpg", "*.jpeg", "*.JPG", "*.JPEG", "*.PNG")

# Example photos live in input_images/ next to this script.
_DEFAULT_IMAGES_DIR = str(Path(__file__).resolve().parent / "input_images")

# Dedicated OpenCV lens-distortion API schemas.
# Applying one makes the RTX renderer apply the
# OpenCV distortion at the projection stage; its
# attributes map 1:1 to OpenCV K/D.
_PINHOLE_SCHEMA = "OmniLensDistortionOpenCvPinholeAPI"
_FISHEYE_SCHEMA = "OmniLensDistortionOpenCvFisheyeAPI"
_CAMERA_PRIM_NAME = "CalibratedCamera"


# ---------------------------------------------------------------------------
# OpenCV calibration
# ---------------------------------------------------------------------------


def _list_images(images_dir: str) -> list:
    paths: list = []
    for pat in _IMAGE_GLOBS:
        paths += glob.glob(os.path.join(images_dir, pat))
    return sorted(set(paths))


def _fisheye_calibrate(objpoints: list, imgpoints: list, img_size: tuple):
    """Run ``cv2.fisheye.calibrate`` and return ``(rms, K, D)``.

    The fisheye solver is sensitive to the initial focal-length guess -- some
    seeds converge to sub-pixel error while others diverge. So try a few guesses
    (fractions of the image size) and keep the lowest-error result.
    """

    # These flags moved to the top level in newer OpenCV; look them up in both.
    def flag(name):
        return getattr(cv2.fisheye, name, None) or getattr(cv2, name)

    flags = flag("CALIB_USE_INTRINSIC_GUESS") | flag("CALIB_RECOMPUTE_EXTRINSIC") | flag("CALIB_FIX_SKEW")
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    w, h = img_size
    base = float(max(w, h))

    best = None  # (rms, K, D)
    for factor in (0.3, 0.4, 0.5, 0.6, 0.8, 1.0):
        K = np.array([[base * factor, 0.0, w / 2.0], [0.0, base * factor, h / 2.0], [0.0, 0.0, 1.0]])
        D = np.zeros((4, 1))
        try:
            rms, K, D, _, _ = cv2.fisheye.calibrate(objpoints, imgpoints, img_size, K, D, flags=flags, criteria=crit)
        except cv2.error:
            continue
        if np.isfinite(rms) and (best is None or rms < best[0]):
            best = (float(rms), K, D)

    if best is None:
        raise SystemExit("fisheye calibration failed to converge for any focal seed")
    return best


def calibrate(images_dir: str, pattern: tuple, is_fisheye: bool, rational: bool) -> dict:
    """Detect corners in every photo and solve the camera intrinsics.

    ``pattern`` is the number of INNER corners as (cols, rows) -- an NxM-square
    board has (N-1, M-1) inner corners.

    Returns a dict with the resolution, fx/fy, cx/cy, distortion coefficients,
    reprojection RMS, a model name, and the used/failed file lists.
    """
    image_paths = _list_images(images_dir)
    if not image_paths:
        raise SystemExit(f"no images found in {images_dir}")

    # 3D corner grid of the board (a single flat plane at z=0).
    objp = np.zeros((pattern[0] * pattern[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0 : pattern[0], 0 : pattern[1]].T.reshape(-1, 2)

    corner_flags = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE | cv2.CALIB_CB_FAST_CHECK
    subpix = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    objpoints, imgpoints, used, failed = [], [], [], []
    size = None  # (width, height)
    for path in image_paths:
        name = os.path.basename(path)
        img = cv2.imread(path)
        if img is None:
            failed.append(name)
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        image_size = (gray.shape[1], gray.shape[0])
        if size is None:
            size = image_size
        elif image_size != size:
            raise SystemExit(
                f"image size mismatch: {name} is {image_size[0]}x{image_size[1]}, " f"expected {size[0]}x{size[1]}"
            )

        # [snippet:doc-calibration-detect-corners]
        # pattern is (columns, rows) of inner corners, not checkerboard squares.
        found, corners = cv2.findChessboardCorners(gray, pattern, corner_flags)
        if not found:
            failed.append(name)
            print(f"  [skip] no {pattern[0]}x{pattern[1]} board: {name}")
            continue
        # Refine pixel positions using a 5-pixel search radius in each direction.
        # (-1, -1) disables the excluded central region; subpix sets the stopping criteria.
        corners = cv2.cornerSubPix(gray, corners, (5, 5), (-1, -1), subpix)
        # OpenCV expects one float32 array per image: N x 1 x 2 image coordinates.
        imgpoints.append(corners.reshape(-1, 1, 2).astype(np.float32))
        # Pair these with N x 1 x 3 board coordinates in the same corner order.
        objpoints.append(objp.reshape(-1, 1, 3).astype(np.float32))
        used.append(name)
        print(f"  [ok]   corners found: {name}")
        # [/snippet:doc-calibration-detect-corners]

    if len(objpoints) < 3:
        raise SystemExit(
            f"need >=3 images with a detected board, got {len(objpoints)}. "
            "Check --pattern (inner-corner count, cols x rows) and --fisheye."
        )

    print(f"\nCalibrating from {len(objpoints)} images at {size[0]}x{size[1]} ...")
    # [snippet:doc-calibration-solve]
    if is_fisheye:
        # Try several initial focal lengths and keep the fit with the lowest RMS.
        rms, K, D = _fisheye_calibrate(objpoints, imgpoints, size)
        model = "fisheye (k1..k4)"
    else:
        # Enable three extra radial coefficients for the eight-coefficient model.
        flags = cv2.CALIB_RATIONAL_MODEL if rational else 0
        # Stop after 100 iterations or when the parameter change meets the 1e-6 tolerance.
        crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-6)
        # None lets OpenCV initialize K and D; discard the per-photo rotation/translation vectors.
        # Returns reprojection RMS in pixels, camera matrix K and distortion coefficients D.
        rms, K, D, _, _ = cv2.calibrateCamera(objpoints, imgpoints, size, None, None, flags=flags, criteria=crit)
        model = "pinhole rational (k1..k6)" if rational else "pinhole (k1,k2,p1,p2,k3)"
    # [/snippet:doc-calibration-solve]

    K = np.asarray(K, dtype=np.float64)
    D = np.asarray(D, dtype=np.float64).flatten()
    return {
        "is_fisheye": is_fisheye,
        "width": int(size[0]),
        "height": int(size[1]),
        "fx": float(K[0, 0]),
        "fy": float(K[1, 1]),
        "cx": float(K[0, 2]),
        "cy": float(K[1, 2]),
        "D": D,
        "rms": float(rms),
        "model": model,
        "used": used,
        "failed": failed,
    }


# ---------------------------------------------------------------------------
# USD camera authoring
# ---------------------------------------------------------------------------


def write_usd_camera(cal: dict, output_usd: str) -> None:
    """Write a USD ``Camera`` prim from the calibration result.

    Applies the dedicated OpenCV lens-distortion API schema
    (``OmniLensDistortionOpenCvPinholeAPI`` or ``...Fisheye...``) and authors the
    ``omni:lensdistortion:opencv*`` attributes straight from the OpenCV K/D --
    which is what RTX projects through. It also sets the standard
    ``UsdGeom.Camera`` attributes so the prim stays viewable in any USD tool.
    """
    from pxr import Gf, Sdf, Usd, UsdGeom

    w, h = float(cal["width"]), float(cal["height"])
    fx, fy, cx, cy = cal["fx"], cal["fy"], cal["cx"], cal["cy"]
    d = cal["D"]

    def coef(i):
        return float(d[i]) if i < len(d) else 0.0

    Path(output_usd).parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(output_usd)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)

    cam = UsdGeom.Camera.Define(stage, f"/{_CAMERA_PRIM_NAME}")
    prim = cam.GetPrim()
    # References to this asset can omit a prim path and resolve to this Camera.
    stage.SetDefaultPrim(prim)

    # Apply the OpenCV lens-distortion schema, and collect its fx/fy/cx/cy +
    # distortion coefficients. The pinhole D layout is
    # [k1, k2, p1, p2, k3, (k4, k5, k6, s1, s2, s3, s4)]; fisheye is [k1..k4].
    if cal["is_fisheye"]:
        schema, ns = _FISHEYE_SCHEMA, "omni:lensdistortion:opencvFisheye"
        lens = {"k1": coef(0), "k2": coef(1), "k3": coef(2), "k4": coef(3)}
    else:
        schema, ns = _PINHOLE_SCHEMA, "omni:lensdistortion:opencvPinhole"
        lens = {
            "k1": coef(0),
            "k2": coef(1),
            "k3": coef(4),
            "k4": coef(5),
            "k5": coef(6),
            "k6": coef(7),
            "p1": coef(2),
            "p2": coef(3),
            "s1": coef(8),
            "s2": coef(9),
            "s3": coef(10),
            "s4": coef(11),
        }
    lens.update({"fx": fx, "fy": fy, "cx": cx, "cy": cy})

    # [snippet:doc-calibration-write-camera]
    # Record an applied API schema as a USD list edit on this layer.
    schemas = Sdf.TokenListOp()
    # schema is the selected OpenCV pinhole or fisheye API schema name.
    schemas.prependedItems = [schema]
    prim.SetMetadata("apiSchemas", schemas)
    # lens maps attribute names to solved values; ns is the selected model's namespace.
    # custom=False marks these as schema attributes, not application-defined metadata.
    for name, value in lens.items():
        prim.CreateAttribute(f"{ns}:{name}", Sdf.ValueTypeNames.Float, custom=False).Set(float(value))
    # Preserve the calibration resolution as a USD int2 (width, height).
    prim.CreateAttribute(f"{ns}:imageSize", Sdf.ValueTypeNames.Int2, custom=False).Set(
        Gf.Vec2i(int(cal["width"]), int(cal["height"]))
    )
    # [/snippet:doc-calibration-write-camera]

    # Standard UsdGeom.Camera attrs, so the prim shows in plain USD viewers.
    if not cal["is_fisheye"]:
        # focalLength=fx with horizontalAperture=width reproduces the exact FOV.
        cam.CreateFocalLengthAttr(fx)
        cam.CreateHorizontalApertureAttr(w)
        cam.CreateVerticalApertureAttr(fx * h / fy)
        cam.CreateHorizontalApertureOffsetAttr(cx - w / 2.0)
        cam.CreateVerticalApertureOffsetAttr(cy - h / 2.0)
    else:
        # Nominal fisheye body placeholders (the schema holds the real lens).
        cam.CreateFocalLengthAttr(1.5)
        cam.CreateHorizontalApertureAttr(20.955)
        cam.CreateVerticalApertureAttr(15.2908)
    cam.CreateClippingRangeAttr((0.01, 1000000.0))

    # Stamp calibration provenance (custom attrs).
    prim.CreateAttribute("calibration:model", Sdf.ValueTypeNames.String, custom=True).Set(cal["model"])
    prim.CreateAttribute("calibration:reprojectionRmsPixels", Sdf.ValueTypeNames.Float, custom=True).Set(cal["rms"])

    stage.GetRootLayer().Save()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def print_report(cal: dict) -> None:
    print("\n" + "=" * 60)
    print("Camera intrinsic calibration")
    print("=" * 60)
    print(f"Model:              {cal['model']}")
    print(f"Resolution:         {cal['width']} x {cal['height']}")
    print(f"Focal length (px):  fx={cal['fx']:.3f}  fy={cal['fy']:.3f}")
    print(f"Principal point:    cx={cal['cx']:.3f}  cy={cal['cy']:.3f}")
    print(f"Distortion coeffs:  {np.array2string(np.asarray(cal['D']), precision=6)}")
    print(f"Reprojection RMS:   {cal['rms']:.4f} px")
    print(f"Images used:        {len(cal['used'])}  (failed: {len(cal['failed'])})")
    print("=" * 60)


def _parse_pattern(text: str) -> tuple:
    try:
        cols, rows = (int(x) for x in text.lower().replace("x", ",").split(","))
        return cols, rows
    except Exception:
        raise argparse.ArgumentTypeError(f"--pattern must be COLSxROWS inner corners, e.g. 20x14 (got {text!r})")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Calibrate a camera from checkerboard photos and write a USD camera prim.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--images",
        default=_DEFAULT_IMAGES_DIR,
        help="Folder of checkerboard photos (defaults to input_images/).",
    )
    p.add_argument(
        "--pattern",
        type=_parse_pattern,
        default="20x14",
        help="Inner-corner count COLSxROWS (for an NxM squares board: (N-1)x(M-1)).",
    )
    p.add_argument("--fisheye", action="store_true", help="Use the fisheye distortion model.")
    p.add_argument(
        "--rational",
        action="store_true",
        help="Pinhole only: solve the 8-coeff rational model (k1..k6) instead of 5-coeff.",
    )
    p.add_argument(
        "--output-usd",
        default="./_out/calibrated_camera.usda",
        help="Output USD camera path (.usda or .usd).",
    )
    args = p.parse_args(argv)
    if args.fisheye and args.rational:
        p.error("--rational is only valid for pinhole calibration and cannot be used with --fisheye")

    cal = calibrate(args.images, args.pattern, args.fisheye, args.rational)
    print_report(cal)
    write_usd_camera(cal, args.output_usd)
    print(f"\nUSD camera written: {args.output_usd}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
