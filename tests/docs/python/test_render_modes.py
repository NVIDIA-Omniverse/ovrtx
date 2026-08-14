# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Tests for camera render modes."""

from pathlib import Path

import numpy as np
import ovrtx
import ovstage
import pytest
from PIL import Image

OUTPUT_DIR = Path(__file__).parent / "_output"

USDA = """#usda 1.0
(
    subLayers = [
        @https://omniverse-content-production.s3.us-west-2.amazonaws.com/Samples/Robot-OVRTX/robot-ovrtx.usda@
    ]
)

# [snippet:doc-path-tracing-render-product]
def Scope "Render" {
    def RenderProduct "Camera" {
        int2 resolution = (640, 480)
        rel camera = </World/Camera>
        rel orderedVars = [<LdrColor>]

        # Select path-tracing render mode
        token omni:rtx:rendermode = "PathTracing"
        # [omit]
        # You generally don't want to turn off the denoiser,
        # or set samples this low, but it's an easy way to
        # see the difference
        bool omni:rtx:pt:denoising:enabled = false
        uint omni:rtx:pt:samplesPerPixel = 2
        # [/omit]

        def RenderVar "LdrColor" {
            string sourceName = "LdrColor"
        }
    }
}
# [/snippet:doc-path-tracing-render-product]
"""


def test_path_tracing_mode():
    """Test that PathTracing render mode produces valid output."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    config = ovrtx.RendererConfig(
        log_level="info",
        log_file_path=str(OUTPUT_DIR / "test_render_modes.log"),
    )
    renderer = ovrtx.Renderer(config)
    stage = ovstage.Stage("ovrtx.docs.render-modes")
    renderer.attach_ovstage(stage)
    ordinal = 1
    ovstage.population.open_usd_from_string(stage, USDA, ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    products = renderer.step(
        render_products={"/Render/Camera"},
        delta_time=1.0 / 60,
        ordinal=ordinal,
    )

    for product_name, product in products.items():
        for frame in product.frames:
            var = frame.render_vars["LdrColor"].map(device=ovrtx.Device.CPU)
            view = np.from_dlpack(var)
            ldr_color = view.copy()
            del view
            var.unmap()
            del var

            assert ldr_color.shape == (480, 640, 4) and ldr_color.dtype == np.uint8
            assert not np.all(ldr_color == 0), "LdrColor is all zeros"

            # Save output for visual inspection
            Image.fromarray(ldr_color).save(OUTPUT_DIR / "test_path_tracing_mode.LdrColor.png")

    del products

    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()
