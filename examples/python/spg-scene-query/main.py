# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Draw a crosshair on each scene marker, placed from what the launch script reads out of the scene.

Loads overlay_scene.usda, which renders three coloured spheres and runs the MarkerOverlay SPG
node over the LdrColor AOV. The node's launch script reads the camera's transform and lens
values and the markers' world positions through the scene query API; the kernel projects each
marker into the image and draws a crosshair on it. Writes the rendered image and the overlay to
_output/.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SCENE = SCRIPT_DIR / "overlay_scene.usda"
OUTPUT_DIR = SCRIPT_DIR / "_output"
RENDER_PRODUCT = "/Render/OverlayDemo"
LDR_COLOR_PATH = f"{RENDER_PRODUCT}/LdrColor"
OVERLAY_PATH = f"{RENDER_PRODUCT}/Overlay"
SETTINGS_PRIM = "/World/Overlay"
WARMUP_STEPS = 5
STEP_DT = 1.0 / 60.0


def read_render_var(frame, render_var_path: str) -> np.ndarray:
    """Map a render var to the CPU and return an owned copy."""
    mapped = frame.render_vars[render_var_path].map(device=ovrtx.Device.CPU)
    pixels = np.array(np.from_dlpack(mapped), copy=True)
    del mapped
    return pixels


def save_png(pixels: np.ndarray, path: Path) -> None:
    Image.fromarray(np.ascontiguousarray(pixels)).save(path)
    print(f"Saved {path}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="ovrtx SPG scene query example")
    parser.add_argument("--scene", type=Path, default=DEFAULT_SCENE, help="USDA scene to load")
    args = parser.parse_args()

    print("Creating renderer...", file=sys.stderr)
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.spg-scene-query")
    renderer.attach_ovstage(stage)

    # [snippet:scene-query-populate]
    # Loading a scene publishes what the renderer needs of its prims. /World/Overlay is a prim of
    # this scene's own, and its custom attributes arrive only because the load names it.
    print(f"Loading {args.scene}...", file=sys.stderr)
    ordinal = 1
    settings = ovstage.population.Selector(
        prim_predicate=ovstage.population.PrimPredicate.has_path(SETTINGS_PRIM),
        property_predicate=ovstage.population.PropertyPredicate.all(),
    )
    ovstage.population.open_usd_with_desc(
        stage,
        str(args.scene),
        ordinal=ordinal,
        time=ovstage.population.DEFAULT_TIME,
        descs=[ovstage.population.Desc(domains=ovstage.PopulationDomain.RENDERING, selectors=[settings])],
    )
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    # [/snippet:scene-query-populate]

    # Warm up so the kernel is compiled and the image has converged, then render.
    for _ in range(WARMUP_STEPS):
        renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal)
    products = renderer.step(render_products={RENDER_PRODUCT}, delta_time=STEP_DT, ordinal=ordinal)

    OUTPUT_DIR.mkdir(exist_ok=True)
    frame = products[RENDER_PRODUCT].frames[0]
    image = read_render_var(frame, LDR_COLOR_PATH)
    overlay = read_render_var(frame, OVERLAY_PATH)
    save_png(image, OUTPUT_DIR / "color.png")
    save_png(overlay, OUTPUT_DIR / "overlay.png")

    del frame, products
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


if __name__ == "__main__":
    main()
