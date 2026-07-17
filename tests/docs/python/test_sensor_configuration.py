# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Tests for sensor_configuration.rst Python code examples."""

from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image

SCENE_PATH = str((Path(__file__).parent / "../../../tests/data/simple_camera.usda").resolve())

MULTI_RENDER_PRODUCT_USDA = f"""#usda 1.0
(
    subLayers = [
        @{SCENE_PATH}@
    ]
)

def "Render" {{
    def RenderProduct "FrontCamera" {{
        int2 resolution = (1280, 720)
        rel camera = </Camera0>
        rel orderedVars = [<../Vars/LdrColor>]
    }}

    def RenderProduct "RearCamera" {{
        int2 resolution = (1280, 720)
        rel camera = </Camera1>
        rel orderedVars = [<../Vars/LdrColor>]
    }}

    def "Vars" {{
        def RenderVar "LdrColor" {{
            string sourceName = "LdrColor"
        }}
    }}
}}
"""

def test_step_multiple_render_products(renderer, stage, output_dir):
    """Test stepping with multiple RenderProduct paths (sensor_configuration.rst)."""
    ordinal = 1
    ovstage.population.open_usd_from_string(stage, MULTI_RENDER_PRODUCT_USDA, ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    # Warm up
    for _ in range(5):
        renderer.step(
            render_products={"/Render/FrontCamera", "/Render/RearCamera"},
            delta_time=1.0 / 60,
            ordinal=ordinal,
        )

    # [snippet:doc-step-multiple-render-products]
    products = renderer.step(
        render_products={"/Render/FrontCamera", "/Render/RearCamera"},
        delta_time=1.0 / 60,
        ordinal=ordinal,
    )
    # [/snippet:doc-step-multiple-render-products]

    assert len(products) == 2
    for product_name, product in products.items():
        assert len(product.frames) > 0
        for frame in product.frames:
            var = frame.render_vars["LdrColor"].map(device=ovrtx.Device.CPU)
            ldr = np.from_dlpack(var)
            cam_name = product_name.rsplit("/", 1)[-1]
            Image.fromarray(ldr).save(output_dir / f"test_sensor_config.{cam_name}.LdrColor.png")

def test_add_render_config_layer(renderer, stage, output_dir):
    """Test adding RenderProducts at runtime via open_usd_from_string (sensor_configuration.rst)."""
    scene_path = SCENE_PATH
    ordinal = 1

    # [snippet:doc-add-render-config-layer]
    ovstage.population.open_usd_from_string(stage, f'''
    #usda 1.0
    (
        subLayers = [
            @{scene_path}@
        ]
    )

    def "Render" {{
        def RenderProduct "Camera" {{
            int2 resolution = (1920, 1080)
            rel camera = </Camera0>
            rel orderedVars = [<LdrColor>, <HdrColor>]

            def RenderVar "LdrColor" {{
                string sourceName = "LdrColor"
            }}

            def RenderVar "HdrColor" {{
                string sourceName = "HdrColor"
            }}
        }}
    }}
    ''', ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    products = renderer.step(
        render_products={"/Render/Camera"},
        delta_time=1.0 / 60,
        ordinal=ordinal,
    )
    # [/snippet:doc-add-render-config-layer]

    assert products is not None
    assert "/Render/Camera" in products

    for product_name, product in products.items():
        for frame in product.frames:
            var = frame.render_vars["LdrColor"].map(device=ovrtx.Device.CPU)
            ldr = np.from_dlpack(var)
            Image.fromarray(ldr).save(output_dir / "test_sensor_config.AddRenderConfigLayer.LdrColor.png")
