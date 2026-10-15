# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Render the separate background and lighting domes for the Dome Light page."""

import argparse
from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    scene = (Path(__file__).parents[1] / "data/ovrtx-light-test-dome-multi.usda").resolve()
    product_path = "/Render/OmniverseKit/HydraTextures/omni_kit_widget_viewport_ViewportTexture_0"
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.docs.multiple-dome-lights")
    renderer.attach_ovstage(stage)
    try:
        layer = f'''#usda 1.0
(
    subLayers = [@{scene.as_posix()}@]
)
over "Render" {{
    over "OmniverseKit" {{
        over "HydraTextures" {{
            over "omni_kit_widget_viewport_ViewportTexture_0" {{
                uniform int2 resolution = (512, 512)
                token omni:rtx:lights:visibilityOverride = "perLight"
            }}
        }}
    }}
}}
'''
        ovstage.population.open_usd_from_string(stage, layer, ordinal=1)
        stage.advance_write_floor(1, ovstage.Scope.ALL).wait()
        for _ in range(64):
            products = renderer.step(
                render_products={product_path}, delta_time=1.0 / 60.0, ordinal=1
            )
        frame = products[product_path].frames[-1]
        mapped = frame.render_vars["/Render/Vars/LdrColor"].map(device=ovrtx.Device.CPU)
        pixels = np.from_dlpack(mapped).copy()
        mapped.unmap()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(pixels[..., :3]).save(args.output)
        del mapped, frame, products
    finally:
        renderer.detach_ovstage()
        stage.destroy()
        renderer.destroy()


if __name__ == "__main__":
    main()
