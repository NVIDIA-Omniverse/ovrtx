#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Generate an RTX projector-light direction texture from OpenCV calibration."""

import argparse
from pathlib import Path

import cv2
import Imath
import numpy as np
import OpenEXR

# [snippet:doc-projector-opencv-calibration]
IMAGE_SIZE = (3840, 2160)
CAMERA_MATRIX = np.array(
    [
        [2400.0, 0.0, 1900.0],
        [0.0, 2421.0, 1200.0],
        [0.0, 0.0, 1.0],
    ],
    dtype=np.float64,
)
# OpenCV order: k1, k2, p1, p2, k3, k4, k5, k6,
# s1, s2, s3, s4, tau_x, tau_y.
DISTORTION = np.array(
    [
        -0.32734,
        0.07468,
        -0.00046,
        0.00106,
        0.0,
        0.0,
        0.0,
        0.0,
        -0.0008216463,
        0.0,
        -0.01727441,
        0.0,
        -0.03459962,
        0.001508283,
    ],
    dtype=np.float64,
)
# [/snippet:doc-projector-opencv-calibration]


def create_octahedral_directions(texture_size: int) -> np.ndarray:
    """Return the direction represented by every texel in the square lookup."""

    # [snippet:doc-projector-octahedral-directions]
    texel_centers = (np.arange(texture_size, dtype=np.float64) + 0.5) / texture_size
    oct_x, oct_y = np.meshgrid(
        texel_centers * 2.0 - 1.0,
        texel_centers * 2.0 - 1.0,
    )
    direction_z = 1.0 - np.abs(oct_x) - np.abs(oct_y)

    folded_x = (1.0 - np.abs(oct_y)) * np.where(oct_x >= 0.0, 1.0, -1.0)
    folded_y = (1.0 - np.abs(oct_x)) * np.where(oct_y >= 0.0, 1.0, -1.0)
    direction_x = np.where(direction_z <= 0.0, folded_x, oct_x)
    direction_y = np.where(direction_z <= 0.0, folded_y, oct_y)

    directions = np.stack((direction_x, direction_y, direction_z), axis=-1)
    directions /= np.linalg.norm(directions, axis=-1, keepdims=True)
    # [/snippet:doc-projector-octahedral-directions]
    return directions


def project_directions_to_uv(
    directions: np.ndarray,
    image_size: tuple[int, int],
    camera_matrix: np.ndarray,
    distortion: np.ndarray,
) -> np.ndarray:
    """Project octahedral directions into the calibrated image's UV space."""

    # [snippet:doc-projector-opencv-project]
    flat_directions = directions.reshape(-1, 3)
    uv = np.full((flat_directions.shape[0], 2), -1.0, dtype=np.float32)

    # The renderer flips local -Z before indexing the lookup, so valid decoded
    # directions face +Z in the coordinate system passed to OpenCV.
    front_facing = flat_directions[:, 2] > 1.0e-8
    image_points, _ = cv2.projectPoints(
        flat_directions[front_facing],
        np.zeros(3),
        np.zeros(3),
        camera_matrix,
        distortion,
    )
    projected_uv = image_points[:, 0, :] / np.asarray(image_size)

    # Projector lights emit only for UVs strictly inside (0, 1). Mark every
    # direction that projects outside the calibrated image with -1.
    inside_image = np.all((projected_uv > 0.0) & (projected_uv < 1.0), axis=1)
    front_indices = np.flatnonzero(front_facing)
    uv[front_indices[inside_image]] = projected_uv[inside_image]
    uv = uv.reshape(directions.shape[:2] + (2,))
    # [/snippet:doc-projector-opencv-project]
    return uv


def write_direction_texture(path: Path, uv: np.ndarray) -> None:
    """Write float32 projected UV coordinates to an RG OpenEXR image."""

    # [snippet:doc-projector-write-direction-texture]
    height, width, channels = uv.shape
    if width != height or channels != 2:
        raise ValueError("direction textures must be square float RG images")

    path.parent.mkdir(parents=True, exist_ok=True)
    float_channel = Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT))
    header = OpenEXR.Header(width, height)
    header["channels"] = {"R": float_channel, "G": float_channel}
    header["compression"] = Imath.Compression(Imath.Compression.ZIP_COMPRESSION)

    output = OpenEXR.OutputFile(str(path), header)
    output.writePixels(
        {
            "R": np.ascontiguousarray(uv[:, :, 0], dtype=np.float32).tobytes(),
            "G": np.ascontiguousarray(uv[:, :, 1], dtype=np.float32).tobytes(),
        }
    )
    output.close()
    # [/snippet:doc-projector-write-direction-texture]


def generate_direction_texture(path: Path, texture_size: int = 1024) -> np.ndarray:
    directions = create_octahedral_directions(texture_size)
    uv = project_directions_to_uv(
        directions,
        IMAGE_SIZE,
        CAMERA_MATRIX,
        DISTORTION,
    )
    write_direction_texture(path, uv)
    return uv


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate an RG OpenEXR direction texture from an OpenCV calibration"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--texture-size", type=int, default=1024)
    args = parser.parse_args()
    if args.texture_size < 2:
        parser.error("--texture-size must be at least 2")

    generate_direction_texture(args.output, args.texture_size)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
