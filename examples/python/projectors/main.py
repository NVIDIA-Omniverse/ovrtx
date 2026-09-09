#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Render the projectors test scene and save it as a PNG."""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

import ovrtx
import ovstage

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECTORS_USD = SCRIPT_DIR / "projectors.usda"
RENDER_PRODUCT_PATH = "/Render/OmniverseKit/HydraTextures/omni_kit_widget_viewport_ViewportTexture_0"
LDR_COLOR_PATH = "/Render/Vars/LdrColor"
WARMUP_FRAMES = 40


def main():
    # [snippet:projectors-create-renderer]
    print("Creating renderer...", file=sys.stderr)
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.projectors")
    renderer.attach_ovstage(stage)
    # [/snippet:projectors-create-renderer]

    # [snippet:projectors-load-usd]
    print(f"Loading {PROJECTORS_USD}...", file=sys.stderr)
    ordinal = 1
    ovstage.population.open_usd(stage, PROJECTORS_USD, ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    # [/snippet:projectors-load-usd]

    # [snippet:projectors-warmup]
    print(f"Warming up ({WARMUP_FRAMES} frames)...", file=sys.stderr)
    for _ in range(WARMUP_FRAMES):
        renderer.step(render_products={RENDER_PRODUCT_PATH}, delta_time=1.0 / 60, ordinal=ordinal)
    # [/snippet:projectors-warmup]

    # [snippet:projectors-render]
    print("Rendering final frame...", file=sys.stderr)
    products = renderer.step(render_products={RENDER_PRODUCT_PATH}, delta_time=1.0 / 60, ordinal=ordinal)
    # [/snippet:projectors-render]

    # [snippet:projectors-save-png]
    print("Saving render...", file=sys.stderr)
    output_path = SCRIPT_DIR / "_output/projectors.png"
    output_path.parent.mkdir(exist_ok=True)
    frame = product = None
    for product in products.values():
        for frame in product.frames:
            var = frame.render_vars[LDR_COLOR_PATH].map(device=ovrtx.Device.CPU)
            view = np.from_dlpack(var)
            pixels = view.copy()
            del view
            var.unmap()
            del var
            Image.fromarray(pixels).save(output_path)
    print(f"Saved to {output_path}", file=sys.stderr)
    # [/snippet:projectors-save-png]

    frame = product = None
    del products
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


if __name__ == "__main__":
    main()
