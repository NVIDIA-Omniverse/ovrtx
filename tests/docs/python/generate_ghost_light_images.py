# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Generate comparison images for lights/ghost_lights.rst."""

import argparse
import gc
from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image, ImageDraw, ImageFont


DOCS_ROOT = Path(__file__).parents[1]
BASE_SCENE = (DOCS_ROOT / "data/ovrtx-light-test-rect.usda").resolve()
RENDER_PRODUCT = "/Render/OmniverseKit/HydraTextures/omni_kit_widget_viewport_ViewportTexture_0"
LDR_COLOR = "/Render/Vars/LdrColor"
PANEL_SIZE = 512

FIGURES = {
    "light-ghost-primary-visibility": (
        ("False", "        bool visibleInPrimaryRay = false\n        float ghostFactor = -1\n"),
        ("True", "        bool visibleInPrimaryRay = true\n        float ghostFactor = -1\n"),
    ),
    "light-ghost-factor": (
        ("0", "        bool visibleInPrimaryRay = true\n        float ghostFactor = 0\n"),
        ("0.5", "        bool visibleInPrimaryRay = true\n        float ghostFactor = 0.5\n"),
        ("1", "        bool visibleInPrimaryRay = true\n        float ghostFactor = 1\n"),
    ),
}


def render_panel(figure_name, panel_index, panel):
    label, attributes = panel
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage(f"ovrtx.docs.{figure_name}.{panel_index}")
    renderer.attach_ovstage(stage)
    try:
        root = f"""#usda 1.0
(
    subLayers = [@{BASE_SCENE.as_posix()}@]
)

over "World" {{
    over RectLight "RectLight" {{
{attributes}    }}

    over "balls" {{
        over "Looks" {{
            over "mat_greyball" {{
                over "Shader" {{
                    float inputs:specular_reflection_roughness = 0.3
                }}
            }}
        }}
    }}
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
        for _ in range(64):
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
    if figure_name == "light-ghost-factor":
        images = [(label, image.crop((280, 220, 512, 480))) for label, image in images]
    label_height = 48
    panel_width, panel_height = images[0][1].size
    sheet = Image.new("RGB", (panel_width * len(images), panel_height + label_height), "black")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(
        str(Path(__file__).parents[1] / "data/fonts/DejaVuSans-Bold.ttf"), 24
    )
    for index, (label, image) in enumerate(images):
        x = index * panel_width
        draw.text((x + 16, 8), label, fill="white", font=font)
        sheet.paste(image, (x, label_height))
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
