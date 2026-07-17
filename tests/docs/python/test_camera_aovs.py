# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Tests that all documented camera AOVs render successfully."""

from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image

SCENE_PATH = str((Path(__file__).parent / "../../../tests/data/simple_camera.usda").resolve())

RESOLUTION = (640, 360)

AOV_NAMES = [
    "LdrColor", "HdrColor", "NormalSD", "DepthSD",
    "DistanceToCameraSD", "DistanceToImagePlaneSD",
    "DiffuseAlbedoSD", "Camera3dPositionSD",
]

_ordered_vars = ", ".join(f"<{n}>" for n in AOV_NAMES)
_render_var_defs = "\n".join(
    f'        def RenderVar "{n}" {{\n            string sourceName = "{n}"\n        }}'
    for n in AOV_NAMES
)

# [snippet:doc-camera-aov-usda]
USDA = f"""#usda 1.0
(
    subLayers = [
        @{SCENE_PATH}@
    ]
)

def "Render" {{
    def RenderProduct "Camera" {{
        int2 resolution = {RESOLUTION}
        rel camera = </Camera0>
        rel orderedVars = [{_ordered_vars}]

{_render_var_defs}
    }}
}}
"""
# [/snippet:doc-camera-aov-usda]


def test_all_camera_aovs(renderer, stage, output_dir):
    """Test that all documented camera AOVs render with correct shape and non-zero data."""
    ordinal = 1
    ovstage.population.open_usd_from_string(stage, USDA, ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    # Warm up
    for _ in range(5):
        renderer.step(render_products={"/Render/Camera"}, delta_time=1.0 / 60, ordinal=ordinal)

    # [snippet:doc-camera-aov-smoke-test]
    products = renderer.step(
        render_products={"/Render/Camera"},
        delta_time=1.0 / 60,
        ordinal=ordinal,
    )

    h, w = RESOLUTION[1], RESOLUTION[0]

    for product_name, product in products.items():
        for frame in product.frames:
            # LdrColor: RGBA uint8
            var = frame.render_vars["LdrColor"].map(device=ovrtx.Device.CPU)
            ldr_color = np.from_dlpack(var)
            assert ldr_color.shape == (h, w, 4) and ldr_color.dtype == np.uint8
            assert not np.all(ldr_color == 0), "LdrColor is all zeros"
            Image.fromarray(ldr_color).save(output_dir / "test_camera_aovs.LdrColor.png")

            # HdrColor: RGBA float16
            var = frame.render_vars["HdrColor"].map(device=ovrtx.Device.CPU)
            hdr_color = np.from_dlpack(var)
            assert hdr_color.shape == (h, w, 4) and hdr_color.dtype == np.float16
            assert not np.all(hdr_color == 0), "HdrColor is all zeros"

            # NormalSD: XYZA float32
            var = frame.render_vars["NormalSD"].map(device=ovrtx.Device.CPU)
            normals = np.from_dlpack(var)
            assert normals.shape == (h, w, 4) and normals.dtype == np.float32
            assert not np.all(normals == 0), "NormalSD is all zeros"

            # DepthSD: Z float32
            var = frame.render_vars["DepthSD"].map(device=ovrtx.Device.CPU)
            depth = np.from_dlpack(var)
            assert depth.shape == (h, w, 1) and depth.dtype == np.float32
            # Note: DepthSD may be all zeros in some configurations

            # DistanceToCameraSD: Z float32
            var = frame.render_vars["DistanceToCameraSD"].map(device=ovrtx.Device.CPU)
            dist_camera = np.from_dlpack(var)
            assert dist_camera.shape == (h, w, 1) and dist_camera.dtype == np.float32
            assert not np.all(dist_camera == 0), "DistanceToCameraSD is all zeros"

            # DistanceToImagePlaneSD: Z float32
            var = frame.render_vars["DistanceToImagePlaneSD"].map(device=ovrtx.Device.CPU)
            dist_plane = np.from_dlpack(var)
            assert dist_plane.shape == (h, w, 1) and dist_plane.dtype == np.float32
            assert not np.all(dist_plane == 0), "DistanceToImagePlaneSD is all zeros"

            # DiffuseAlbedoSD: RGBA uint8
            var = frame.render_vars["DiffuseAlbedoSD"].map(device=ovrtx.Device.CPU)
            albedo = np.from_dlpack(var)
            assert albedo.shape == (h, w, 4) and albedo.dtype == np.uint8
            assert not np.all(albedo == 0), "DiffuseAlbedoSD is all zeros"
            Image.fromarray(albedo).save(output_dir / "test_camera_aovs.DiffuseAlbedoSD.png")

            # Camera3dPositionSD: XYZA float32
            var = frame.render_vars["Camera3dPositionSD"].map(device=ovrtx.Device.CPU)
            cam_pos = np.from_dlpack(var)
            assert cam_pos.shape == (h, w, 4) and cam_pos.dtype == np.float32
            assert not np.all(cam_pos == 0), "Camera3dPositionSD is all zeros"
    # [/snippet:doc-camera-aov-smoke-test]
