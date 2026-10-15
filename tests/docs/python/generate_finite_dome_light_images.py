# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Generate finite dome comparisons for lights/dome_light.rst."""

import argparse
import gc
from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image, ImageDraw, ImageFont


DOCS_ROOT = Path(__file__).parents[1]
RENDER_PRODUCT = "/Render/OmniverseKit/HydraTextures/omni_kit_widget_viewport_ViewportTexture_0"
LDR_COLOR = "/Render/Vars/LdrColor"
PANEL_SIZE = 512
FIGURES = {
    "light-finite-dome-modes": (
        ("Infinite", "ovrtx-light-test-finite-dome-infinite.usda", ""),
        ("Ground", "ovrtx-light-test-finite-dome-ground.usda", ""),
        ("Sphere", "ovrtx-light-test-finite-dome-sphere.usda", ""),
        ("Box", "ovrtx-light-test-finite-dome-box.usda", ""),
        ("Sphere + Ground", "ovrtx-light-test-finite-dome-sphere-with-ground.usda", ""),
        ("Box + Ground", "ovrtx-light-test-finite-dome-box-with-ground.usda", ""),
    ),
    "light-finite-dome-radius": (
        ("50", "ovrtx-light-test-finite-dome-sphere-with-ground.usda", "        float omni:rtx:domeLight:radius = 50\n"),
        ("100", "ovrtx-light-test-finite-dome-sphere-with-ground.usda", "        float omni:rtx:domeLight:radius = 100\n"),
        ("200", "ovrtx-light-test-finite-dome-sphere-with-ground.usda", "        float omni:rtx:domeLight:radius = 200\n"),
    ),
    "light-finite-dome-size": (
        ("100 × 100 × 100", "ovrtx-light-test-finite-dome-box-with-ground.usda", "        float3 omni:rtx:domeLight:size = (100, 100, 100)\n"),
        ("200 × 200 × 200", "ovrtx-light-test-finite-dome-box-with-ground.usda", "        float3 omni:rtx:domeLight:size = (200, 200, 200)\n"),
        ("400 × 200 × 300", "ovrtx-light-test-finite-dome-box-with-ground.usda", "        float3 omni:rtx:domeLight:size = (400, 200, 300)\n"),
    ),
    "light-finite-dome-ground-texture-scale": (
        ("10", "ovrtx-light-test-finite-dome-box-with-ground.usda", "        float omni:rtx:domeLight:groundTextureScale = 10\n"),
        ("30", "ovrtx-light-test-finite-dome-box-with-ground.usda", "        float omni:rtx:domeLight:groundTextureScale = 30\n"),
        ("100", "ovrtx-light-test-finite-dome-box-with-ground.usda", "        float omni:rtx:domeLight:groundTextureScale = 100\n"),
    ),
}


def render_panel(figure_name, panel_index, panel):
    label, filename, attributes = panel
    scene = (DOCS_ROOT / "data" / filename).resolve()
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage(f"ovrtx.docs.{figure_name}.{panel_index}")
    renderer.attach_ovstage(stage)
    try:
        root = f"""#usda 1.0
(
    subLayers = [@{scene.as_posix()}@]
)

over "World" {{
    over DomeLight "DomeLight" {{
{attributes}    }}
}}

over "Render" {{
    over "OmniverseKit" {{
        over "HydraTextures" {{
            over "omni_kit_widget_viewport_ViewportTexture_0" {{
                uniform int2 resolution = ({PANEL_SIZE}, {PANEL_SIZE})
            }}
        }}
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
        assert image.size == (PANEL_SIZE, PANEL_SIZE)
        del mapped, frame, products, pixels
        gc.collect()
        return label, image
    finally:
        renderer.detach_ovstage()
        stage.destroy()
        renderer.destroy()


def make_contact_sheet(figure_name, panels, output_dir):
    images = [render_panel(figure_name, index, panel) for index, panel in enumerate(panels)]
    columns = 3
    rows = (len(images) + columns - 1) // columns
    label_height = 48
    sheet = Image.new("RGB", (PANEL_SIZE * columns, (PANEL_SIZE + label_height) * rows), "black")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(
        str(Path(__file__).parents[1] / "data/fonts/DejaVuSans-Bold.ttf"), 24
    )
    for index, (label, image) in enumerate(images):
        column = index % columns
        row = index // columns
        x = column * PANEL_SIZE
        y = row * (PANEL_SIZE + label_height)
        draw.text((x + 16, y + 8), label, fill="white", font=font)
        sheet.paste(image, (x, y + label_height))
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
