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

"""
Tiled rendering demo using ovrtx Python bindings.

Demonstrates:
- Referencing the same USD scene multiple times with different transforms
- Using a single RenderProduct with multiple cameras to produce a tiled grid
- RTX lays out each camera's output as a tile in the final image

Usage:
    uv run main.py              # Display the tiled render
    uv run main.py --png        # Save to _output/tiled_render.png
"""

import argparse
import sys
import tempfile
from pathlib import Path

import colorsys

import numpy as np
import ovrtx
import ovstage
from PIL import Image

SCRIPT_DIR = Path(__file__).parent.resolve()
TEST_DATA_DIR = (SCRIPT_DIR / "../../../tests/docs/data").resolve()
TEST_BASE_NO_LIGHT = TEST_DATA_DIR / "ovrtx-test-base-no-light.usda"
TEST_BASE_LIGHT = TEST_DATA_DIR / "ovrtx-test-base-light.usda"

GRID_SIZE = 3       # 3x3 grid
SCENE_SPACING = 100  # Each scene instance covers ~100x100 units


def generate_tiled_scene_usda(scene_path: Path, light_path: Path) -> str:
    """Generate a USDA scene that references the no-light base scene in a 3x3
    grid, adds a single shared DomeLight, and creates a single RenderProduct
    targeting all 9 cameras."""

    # Build the 9 scene references, each offset in X and Z
    scene_prims = []
    camera_paths = []
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            name = f"Scene_{row}_{col}"
            tx = col * SCENE_SPACING
            tz = row * SCENE_SPACING
            scene_prims.append(f"""
    def Xform "{name}" (
        prepend references = @{scene_path}@
    )
    {{
        double3 xformOp:translate = ({tx}, 0, {tz})
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }}""")
            # The test base defaultPrim is "World", so Camera lives directly
            # under each Scene_R_C prim after the reference is composed.
            camera_paths.append(f"</World/{name}/Camera>")

    cameras_rel = ",\n            ".join(camera_paths)

    return f"""#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 0.01
    subLayers = [
        @{light_path}@
    ]
    upAxis = "Y"
)

def Xform "World"
{{{"".join(scene_prims)}
}}

def Scope "Render"
{{
    def RenderProduct "TiledCameras" (
        prepend apiSchemas = ["OmniRtxDebugSettingsAPI_1"]
    )
    {{
        rel camera = [
            {cameras_rel}
        ]
        int2 resolution = (1024, 1024)
        rel orderedVars = <LdrColor>

        def RenderVar "LdrColor" {{
            string sourceName = "LdrColor"
        }}
    }}
}}
"""


def main():
    parser = argparse.ArgumentParser(description="Tiled rendering demo using ovrtx")
    parser.add_argument("--png", action="store_true", help="Save render to _output/tiled_render.png instead of displaying")
    args = parser.parse_args()

    if not TEST_BASE_NO_LIGHT.exists():
        print(f"Error: test base scene not found at {TEST_BASE_NO_LIGHT}", file=sys.stderr)
        sys.exit(1)

    # Generate the tiled scene USDA and write to a temp file so the renderer
    # can load it (asset references in the USDA resolve relative to the
    # referenced file, so the test-base's textures/payloads still work).
    scene_usda = generate_tiled_scene_usda(TEST_BASE_NO_LIGHT, TEST_BASE_LIGHT)

    with tempfile.NamedTemporaryFile(suffix=".usda", mode="w", delete=False) as f:
        f.write(scene_usda)
        scene_path = f.name

    print("Creating renderer...", file=sys.stderr)
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.tiled-rendering")
    renderer.attach_ovstage(stage)

    print(f"Loading tiled scene ({GRID_SIZE}x{GRID_SIZE} grid)...", file=sys.stderr)
    ovstage.population.open_usd(stage, scene_path, ordinal=1)
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()

    # Give each instance's logo a unique color.
    # The material shader prim for the logo in each referenced scene is at:
    #   /World/Scene_R_C/Looks/srf_green_plastic/Shader
    num_instances = GRID_SIZE * GRID_SIZE
    shader_paths = []
    colors = []
    for idx, (row, col) in enumerate((r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)):
        hue = idx / num_instances
        rgb = colorsys.hsv_to_rgb(hue, 0.9, 0.5)
        shader_paths.append(f"/World/Scene_{row}_{col}/Looks/srf_green_plastic/Shader")
        colors.append(rgb)

    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(shader_paths)
        with stage.query_from_path_list(path_list) as query:
            color_values = np.asarray(colors, dtype=np.float32)
            color_dtype = ovstage.numpy_to_dldatatype(color_values.dtype, lanes=3)
            color_tensor = ovstage.make_dltensor(color_values, dtype=color_dtype, shape=[num_instances], ndim=1)
            stage.write_attribute(
                query,
                "inputs:diffuse_color_constant",
                ordinal=2,
                tensors=color_tensor,
                is_array=False,
                semantic=ovstage.AttributeSemantic.COLOR,
            ).wait()
            stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
        paths.destroy_path_list(path_list)

    # Warm up for 40 frames so texture streaming has finished loading highest quality mips and
    # path tracing converges to a good quality image.
    WARMUP_FRAMES = 40
    print(f"Warming up ({WARMUP_FRAMES} frames)...", file=sys.stderr)
    for _ in range(WARMUP_FRAMES):
        renderer.step(
            render_products={"/Render/TiledCameras"},
            delta_time=1.0 / 60,
            ordinal=2,
        )

    print("Rendering final frame...", file=sys.stderr)
    products = renderer.step(
        render_products={"/Render/TiledCameras"},
        delta_time=1.0 / 60,
        ordinal=2,
    )

    print("Fetching results...", file=sys.stderr)
    for _product_name, product in products.items():
        for frame in product.frames:
            var = frame.render_vars["LdrColor"].map(device=ovrtx.Device.CPU)
            view = np.from_dlpack(var)
            pixels = view.copy()
            del view
            var.unmap()
            del var
            img = Image.fromarray(pixels)
            if args.png:
                output_dir = SCRIPT_DIR / "_output"
                output_dir.mkdir(exist_ok=True)
                img.save(output_dir / "tiled_render.png")
                print(f"Saved to {output_dir / 'tiled_render.png'}", file=sys.stderr)
            else:
                img.show()

    print("Done.", file=sys.stderr)
    del frame, product, products
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


if __name__ == "__main__":
    main()
