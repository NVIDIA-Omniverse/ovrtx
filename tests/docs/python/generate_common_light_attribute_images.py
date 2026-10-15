# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Generate the comparison images for lights/common_attributes.rst."""

import argparse
from pathlib import Path

from generate_light_shaping_images import RECT_SCENE, make_contact_sheet


SMALL_RECT = """
        float3[] extent = [(-5, -5, 0), (5, 5, 0)]
        float inputs:height = 10
        float inputs:width = 10
"""


def panel(label, attributes):
    return label, RECT_SCENE, "RectLight", "RectLight", SMALL_RECT + attributes


FIGURES = {
    "light-common-intensity": (
        panel("250,000", "        float inputs:intensity = 250000\n"),
        panel("1,000,000", "        float inputs:intensity = 1000000\n"),
        panel("4,000,000", "        float inputs:intensity = 4000000\n"),
    ),
    "light-common-exposure": (
        panel("-2", "        float inputs:exposure = -2\n        float inputs:intensity = 1000000\n"),
        panel("0", "        float inputs:exposure = 0\n        float inputs:intensity = 1000000\n"),
        panel("+2", "        float inputs:exposure = 2\n        float inputs:intensity = 1000000\n"),
    ),
    "light-common-color": (
        panel("White", "        color3f inputs:color = (1, 1, 1)\n        float inputs:intensity = 1000000\n"),
        panel("Blue", "        color3f inputs:color = (0.1, 0.2, 1)\n        float inputs:intensity = 1000000\n"),
        panel("Red", "        color3f inputs:color = (1, 0.1, 0.1)\n        float inputs:intensity = 1000000\n"),
    ),
    "light-common-enable-color-temperature": (
        panel("False", "        float inputs:colorTemperature = 3000\n        bool inputs:enableColorTemperature = false\n        float inputs:intensity = 1000000\n"),
        panel("True", "        float inputs:colorTemperature = 3000\n        bool inputs:enableColorTemperature = true\n        float inputs:intensity = 1000000\n"),
    ),
    "light-common-color-temperature": (
        panel("2,000 K", "        float inputs:colorTemperature = 2000\n        bool inputs:enableColorTemperature = true\n        float inputs:intensity = 1000000\n"),
        panel("6,500 K", "        float inputs:colorTemperature = 6500\n        bool inputs:enableColorTemperature = true\n        float inputs:intensity = 1000000\n"),
        panel("10,000 K", "        float inputs:colorTemperature = 10000\n        bool inputs:enableColorTemperature = true\n        float inputs:intensity = 1000000\n"),
    ),
    "light-common-normalize": (
        panel("False", "        float inputs:intensity = 1000000\n        bool inputs:normalize = false\n"),
        panel("True", "        float inputs:intensity = 1000000\n        bool inputs:normalize = true\n"),
    ),
    "light-common-diffuse": (
        panel("0", "        float inputs:diffuse = 0\n        float inputs:intensity = 1000000\n"),
        panel("0.5", "        float inputs:diffuse = 0.5\n        float inputs:intensity = 1000000\n"),
        panel("1", "        float inputs:diffuse = 1\n        float inputs:intensity = 1000000\n"),
    ),
    "light-common-specular": (
        panel("0", "        float inputs:intensity = 1000000\n        float inputs:specular = 0\n"),
        panel("0.5", "        float inputs:intensity = 1000000\n        float inputs:specular = 0.5\n"),
        panel("1", "        float inputs:intensity = 1000000\n        float inputs:specular = 1\n"),
    ),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--figure", choices=tuple(FIGURES))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    selected = {args.figure: FIGURES[args.figure]} if args.figure else FIGURES
    for figure_name, panels in selected.items():
        crop = (600, 500, 1000, 900) if figure_name in {
            "light-common-diffuse",
            "light-common-specular",
        } else None
        make_contact_sheet(figure_name, panels, args.output_dir, crop=crop)


if __name__ == "__main__":
    main()
