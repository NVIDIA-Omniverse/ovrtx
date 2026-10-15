# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Generate the comparison images for lights/shaping_and_ies.rst."""

import argparse
import gc
from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image, ImageDraw, ImageFont


DOCS_ROOT = Path(__file__).parents[1]
RECT_SCENE = DOCS_ROOT / "data/ovrtx-light-test-rect.usda"
DISK_SCENE = DOCS_ROOT / "data/ovrtx-light-test-disk.usda"
SPHERE_SCENE = DOCS_ROOT / "data/ovrtx-light-test-sphere.usda"
IES_FILE = (DOCS_ROOT / "data/ies/bega-50898.4K3.ies").resolve()
RENDER_PRODUCT = "/Render/OmniverseKit/HydraTextures/omni_kit_widget_viewport_ViewportTexture_0"
LDR_COLOR = "/Render/Vars/LdrColor"

RECT_GEOMETRY = """
        float3[] extent = [(-5, -5, 0), (5, 5, 0)]
        float inputs:height = 10
        float inputs:intensity = 1000000
        float inputs:width = 10
"""
DISK_GEOMETRY = """
        float3[] extent = [(-5, -5, 0), (5, 5, 0)]
        float inputs:intensity = 1000000
        float inputs:radius = 5
"""
SPHERE_GEOMETRY = """
        float3[] extent = [(-1, -1, -1), (1, 1, 1)]
        float inputs:intensity = 10000000
        float inputs:radius = 1
        double3 xformOp:rotateXYZ = (-90, 0, 0)
        double3 xformOp:translate = (0, 140, -45)
"""
IES_ATTRIBUTES = f"""
        asset inputs:shaping:ies:file = @{IES_FILE.as_posix()}@
"""


def rect_panel(label, shaping):
    return label, RECT_SCENE, "RectLight", "RectLight", RECT_GEOMETRY + shaping


def disk_panel(label, shaping):
    return label, DISK_SCENE, "DiskLight", "DiskLight", DISK_GEOMETRY + shaping


def sphere_panel(label, shaping):
    return label, SPHERE_SCENE, "SphereLight", "SphereLight", SPHERE_GEOMETRY + shaping


FIGURES = {
    "light-shaping-cone-angle": (
        rect_panel("90°", "        float inputs:shaping:cone:angle = 90\n"),
        rect_panel("60°", "        float inputs:shaping:cone:angle = 60\n"),
        rect_panel("30°", "        float inputs:shaping:cone:angle = 30\n"),
    ),
    "light-shaping-cone-softness": (
        rect_panel("0", "        float inputs:shaping:cone:angle = 35\n        float inputs:shaping:cone:softness = 0\n"),
        rect_panel("0.5", "        float inputs:shaping:cone:angle = 35\n        float inputs:shaping:cone:softness = 0.5\n"),
        rect_panel("1", "        float inputs:shaping:cone:angle = 35\n        float inputs:shaping:cone:softness = 1\n"),
    ),
    "light-shaping-focus": (
        rect_panel("0", "        float inputs:shaping:cone:angle = 180\n        float inputs:shaping:focus = 0\n"),
        rect_panel("2", "        float inputs:shaping:cone:angle = 180\n        float inputs:shaping:focus = 2\n"),
        rect_panel("8", "        float inputs:shaping:cone:angle = 180\n        float inputs:shaping:focus = 8\n"),
    ),
    "light-shaping-focus-tint": (
        rect_panel("Black", "        float inputs:shaping:focus = 4\n        color3f inputs:shaping:focusTint = (0, 0, 0)\n"),
        rect_panel("Blue", "        float inputs:shaping:focus = 4\n        color3f inputs:shaping:focusTint = (0.1, 0.2, 1)\n"),
        rect_panel("Red", "        float inputs:shaping:focus = 4\n        color3f inputs:shaping:focusTint = (1, 0.1, 0.1)\n"),
    ),
    "light-shaping-forward-axis": (
        sphere_panel("-Z", "        float inputs:shaping:cone:angle = 35\n        token omni:rtx:shaping:forwardAxis = \"-Z\"\n"),
        sphere_panel("+X", "        float inputs:shaping:cone:angle = 35\n        token omni:rtx:shaping:forwardAxis = \"+X\"\n"),
        sphere_panel("-X", "        float inputs:shaping:cone:angle = 35\n        token omni:rtx:shaping:forwardAxis = \"-X\"\n"),
    ),
    "light-shaping-ies-file": (
        disk_panel("No profile", ""),
        disk_panel(
            "BEGA 50898.4K3",
            IES_ATTRIBUTES + "        float inputs:shaping:ies:angleScale = 1\n        bool inputs:shaping:ies:normalize = true\n",
        ),
    ),
    "light-shaping-ies-angle-scale": (
        disk_panel("0.5", IES_ATTRIBUTES + "        float inputs:shaping:ies:angleScale = 0.5\n        bool inputs:shaping:ies:normalize = true\n"),
        disk_panel("1", IES_ATTRIBUTES + "        float inputs:shaping:ies:angleScale = 1\n        bool inputs:shaping:ies:normalize = true\n"),
        disk_panel("1.5", IES_ATTRIBUTES + "        float inputs:shaping:ies:angleScale = 1.5\n        bool inputs:shaping:ies:normalize = true\n"),
    ),
    "light-shaping-ies-normalize": (
        disk_panel("False", IES_ATTRIBUTES + "        float inputs:shaping:ies:angleScale = 1\n        bool inputs:shaping:ies:normalize = false\n"),
        disk_panel("True", IES_ATTRIBUTES + "        float inputs:shaping:ies:angleScale = 1\n        bool inputs:shaping:ies:normalize = true\n"),
    ),
}


def render_panel(figure_name, panel_index, panel):
    label, base_scene, prim_type, prim_name, attributes = panel
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage(f"ovrtx.docs.{figure_name}.{panel_index}")
    renderer.attach_ovstage(stage)
    try:
        root = f"""#usda 1.0
(
    subLayers = [@{base_scene.resolve().as_posix()}@]
)

over "World" {{
    over {prim_type} "{prim_name}" (
        prepend apiSchemas = ["ShapingAPI"]
    )
    {{
{attributes}
    }}
}}
"""
        ovstage.population.open_usd_from_string(stage, root, ordinal=1)
        stage.advance_write_floor(1, ovstage.Scope.ALL).wait()

        products = None
        for _ in range(32):
            products = renderer.step(
                render_products={RENDER_PRODUCT},
                delta_time=1.0 / 60,
                ordinal=1,
            )

        frame = products[RENDER_PRODUCT].frames[-1]
        mapped = frame.render_vars[LDR_COLOR].map(device=ovrtx.Device.CPU)
        view = np.from_dlpack(mapped)
        pixels = view.copy()
        del view
        mapped.unmap()
        image = Image.fromarray(pixels[..., :3])
        del mapped, frame, products, pixels
        gc.collect()
        return label, image
    finally:
        renderer.detach_ovstage()
        stage.destroy()
        renderer.destroy()


def make_contact_sheet(figure_name, panels, output_dir, crop=None):
    images = [render_panel(figure_name, index, panel) for index, panel in enumerate(panels)]
    if crop is not None:
        images = [(label, image.crop(crop)) for label, image in images]
    label_height = 72
    panel_width, panel_height = images[0][1].size
    sheet = Image.new("RGB", (panel_width * len(images), panel_height + label_height), "black")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(
        str(Path(__file__).parents[1] / "data/fonts/DejaVuSans-Bold.ttf"), 36
    )
    for index, (label, image) in enumerate(images):
        x = index * panel_width
        sheet.paste(image, (x, label_height))
        draw.text((x + 24, 15), label, fill="white", font=font)
    sheet.save(output_dir / f"{figure_name}.png")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--figure", choices=tuple(FIGURES))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    selected = {args.figure: FIGURES[args.figure]} if args.figure else FIGURES
    for figure_name, panels in selected.items():
        make_contact_sheet(figure_name, panels, args.output_dir)


if __name__ == "__main__":
    main()
