# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Generate the mesh-light sampling comparison for lights/mesh_lights.rst."""

import argparse
import gc
from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image, ImageDraw, ImageFont

DOCS_ROOT = Path(__file__).parents[1]
BASE_SCENE = (DOCS_ROOT / "data/ovrtx-light-test-mesh.usda").resolve()
RENDER_PRODUCT = (
    "/Render/OmniverseKit/HydraTextures/omni_kit_widget_viewport_ViewportTexture_0"
)
LDR_COLOR = "/Render/Vars/LdrColor"
PANEL_SIZE = 512


def render_panel(
    label: str, enabled: bool, warmup_frames: int
) -> tuple[str, Image.Image]:
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage(f"ovrtx.docs.mesh-lights.{enabled}")
    renderer.attach_ovstage(stage)
    try:
        layer = f"""#usda 1.0
(
    subLayers = [@{BASE_SCENE.as_posix()}@]
)

over "Render" {{
    over "OmniverseKit" {{
        over "HydraTextures" {{
            over RenderProduct "omni_kit_widget_viewport_ViewportTexture_0" {{
                token omni:rtx:rendermode = "RealTimePathTracing"
                token omni:rtx:directLighting:sampledLighting:denoisingTechnique = "None"
                bool omni:rtx:indirectDiffuse:denoiser:enabled = false
                # Isolate mesh-light sampling from radiance-cache training.
                bool omni:rtx:rtpt:cached:enabled = false
                bool omni:rtx:rtpt:ris:meshLights = {str(enabled).lower()}
                uniform int2 resolution = ({PANEL_SIZE}, {PANEL_SIZE})
            }}
        }}
    }}
}}

over "World" {{
    over Camera "Camera" {{
        custom bool omni:rtx:autoExposure:enabled = false
    }}
}}
"""
        ovstage.population.open_usd_from_string(stage, layer, ordinal=1)
        stage.advance_write_floor(1, ovstage.Scope.ALL).wait()

        products = None
        for _ in range(warmup_frames):
            products = renderer.step(
                render_products={RENDER_PRODUCT},
                delta_time=1.0 / 60.0,
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--warmup-frames", type=int, default=64)
    args = parser.parse_args()
    if args.warmup_frames < 1:
        parser.error("--warmup-frames must be at least 1")

    panels = (
        render_panel("Sampling off", False, args.warmup_frames),
        render_panel("Sampling on", True, args.warmup_frames),
    )
    label_height = 48
    sheet = Image.new("RGB", (PANEL_SIZE * 2, PANEL_SIZE + label_height), "black")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(
        str(Path(__file__).parents[1] / "data/fonts/DejaVuSans-Bold.ttf"), 24
    )
    for index, (label, image) in enumerate(panels):
        x = index * PANEL_SIZE
        draw.text((x + 16, 8), label, fill="white", font=font)
        sheet.paste(image, (x, label_height))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output)


if __name__ == "__main__":
    main()
