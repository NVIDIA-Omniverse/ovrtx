# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Generate comparison images for lights/physical_lighting.rst."""

import argparse
import gc
from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image, ImageDraw, ImageFont


DOCS_ROOT = Path(__file__).parents[1]
BASE_SCENE = (DOCS_ROOT / "data/ovrtx-light-test-base.usda").resolve()
RENDER_PRODUCT = "/Render/OmniverseKit/HydraTextures/omni_kit_widget_viewport_ViewportTexture_0"
LDR_COLOR = "/Render/Vars/LdrColor"

BASE_ATTRIBUTES = """        float inputs:exposure = 0
        float inputs:intensity = 1
        color3f inputs:color = (1, 1, 1)
"""


def panel(label, attributes):
    return label, BASE_ATTRIBUTES + attributes


FIGURES = {
    "light-physical-illuminant": (
        panel("White", '        token physical:illuminant = "white"\n        float photometric:power = 6400\n'),
        panel(
            "Blackbody 3,000 K",
            '        token physical:illuminant = "blackbody"\n'
            "        float inputs:colorTemperature = 3000\n"
            "        float photometric:power = 6400\n",
        ),
        panel(
            "Illuminant D 6,504 K",
            '        token physical:illuminant = "illuminant D"\n'
            "        float inputs:colorTemperature = 6504\n"
            "        float photometric:power = 6400\n",
        ),
        panel(
            "CIE FL5",
            '        token physical:illuminant = "custom"\n'
            # CIE standard fluorescent illuminant FL5, sampled every 5 nm.
            "        float2[] physical:customIlluminant = [(380, 0.0012770819), (385, 0.001604889), (390, 0.00199416), (395, 0.0023561136), (400, 0.0034829506), (405, 0.012914235), (410, 0.004097589), (415, 0.004172711), (420, 0.004678081), (425, 0.0051766206), (430, 0.005675161), (435, 0.027836287), (440, 0.01096788), (445, 0.007047853), (450, 0.0074507827), (455, 0.007785419), (460, 0.00807908), (465, 0.008311276), (470, 0.00846835), (475, 0.008563961), (480, 0.008591278), (485, 0.008550302), (490, 0.008516156), (495, 0.0083317645), (500, 0.008120055), (505, 0.007928834), (510, 0.0077376137), (515, 0.0075805397), (520, 0.007484929), (525, 0.0074917586), (530, 0.0076215155), (535, 0.0078810295), (540, 0.008277129), (545, 0.018971836), (550, 0.012108375), (555, 0.009882019), (560, 0.010380559), (565, 0.010769829), (570, 0.010995197), (575, 0.01266155), (580, 0.013317164), (585, 0.010510315), (590, 0.009998117), (595, 0.00936982), (600, 0.008666401), (605, 0.007901518), (610, 0.007136634), (615, 0.0063854093), (620, 0.005661502), (625, 0.0049990583), (630, 0.004377591), (635, 0.0038449042), (640, 0.0033463642), (645, 0.002909288), (650, 0.002540505), (655, 0.0022195273), (660, 0.0019326961), (665, 0.0017004994), (670, 0.00149562), (675, 0.0013180578), (680, 0.0011678129), (685, 0.0010380559), (690, 0.0010107385), (695, 0.0008604937), (700, 0.0007717126), (705, 0.0007170781), (710, 0.0006556142), (715, 0.0005804918), (720, 0.0005326866), (725, 0.0004917107), (730, 0.0004643934), (735, 0.0004575641), (740, 0.0004439055), (745, 0.0004165882), (750, 0.0004234175), (755, 0.0004029296), (760, 0.0004234175), (765, 0.0004370762), (770, 0.0003756123), (775, 0.0003209778), (780, 0.0002731726)]\n"
            "        float photometric:power = 6400\n",
        ),
    ),
    "light-physical-power": (
        panel("1,600 lm", "        float photometric:power = 1600\n"),
        panel("6,400 lm", "        float photometric:power = 6400\n"),
        panel("16,000 lm", "        float photometric:power = 16000\n"),
    ),
    "light-physical-illuminance": (
        panel("250 lx at 2 m", "        float photometric:power = 0\n        float photometric:illuminance = 250\n        float photometric:illuminance:distance = 2\n"),
        panel("1,000 lx at 2 m", "        float photometric:power = 0\n        float photometric:illuminance = 1000\n        float photometric:illuminance:distance = 2\n"),
        panel("4,000 lx at 2 m", "        float photometric:power = 0\n        float photometric:illuminance = 4000\n        float photometric:illuminance:distance = 2\n"),
    ),
    "light-physical-illuminance-distance": (
        panel("1,000 lx at 1 m", "        float photometric:power = 0\n        float photometric:illuminance = 1000\n        float photometric:illuminance:distance = 1\n"),
        panel("1,000 lx at 2 m", "        float photometric:power = 0\n        float photometric:illuminance = 1000\n        float photometric:illuminance:distance = 2\n"),
        panel("1,000 lx at 4 m", "        float photometric:power = 0\n        float photometric:illuminance = 1000\n        float photometric:illuminance:distance = 4\n"),
    ),
}


def render_panel(figure_name, panel_index, panel_data):
    label, attributes = panel_data
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage(f"ovrtx.docs.{figure_name}.{panel_index}")
    renderer.attach_ovstage(stage)
    try:
        root = f"""#usda 1.0
(
    subLayers = [@{BASE_SCENE.as_posix()}@]
)

over "World" {{
    over RectLight "RectLight" (
        prepend apiSchemas = ["PhotometricAreaLightAPI"]
    ) {{
{attributes}    }}
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


def make_contact_sheet(figure_name, panels, output_dir):
    images = [render_panel(figure_name, index, panel_data) for index, panel_data in enumerate(panels)]
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
