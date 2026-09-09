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
Crop window demo using ovrtx Python bindings.

Demonstrates:
- Setting a crop window on a RenderProduct using OpenUSD dataWindowNDC
- Verifying the rendered output matches the expected crop dimensions

The scene uses a 1024x1024 RenderProduct with dataWindowNDC set to
(0.25, 0.25, 0.75, 0.75), which crops to the center 512x512 pixels.

Usage:
    uv run main.py              # Display the cropped render
    uv run main.py --png        # Save to _output/render.png
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image

SCRIPT_DIR = Path(__file__).parent.resolve()
TEST_DATA_DIR = (SCRIPT_DIR / "../../../tests/docs/data").resolve()
TEST_BASE_NO_LIGHT = TEST_DATA_DIR / "ovrtx-test-base-no-light.usda"
TEST_BASE_LIGHT = TEST_DATA_DIR / "ovrtx-test-base-light.usda"

FULL_RESOLUTION = (1024, 1024)
CROP_NDC = (0.25, 0.25, 0.75, 0.75)  # center crop
EXPECTED_CROP = (512, 512)
LDR_COLOR_PATH = "/Render/Camera/LdrColor"


def generate_scene_usda(scene_path: Path, light_path: Path) -> str:
    """Generate a USDA that references the test base scene with a 1024x1024
    RenderProduct and a centered 512x512 crop window via dataWindowNDC."""
    return f"""#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 0.01
    subLayers = [
        @{light_path}@,
        @{scene_path}@
    ]
    upAxis = "Y"
)

def Scope "Render"
{{
    def RenderProduct "Camera" (
        prepend apiSchemas = ["OmniRtxDebugSettingsAPI_1"]
    )
    {{
        rel camera = </World/Camera>
        int2 resolution = ({FULL_RESOLUTION[0]}, {FULL_RESOLUTION[1]})
        float4 dataWindowNDC = ({CROP_NDC[0]}, {CROP_NDC[1]}, {CROP_NDC[2]}, {CROP_NDC[3]})
        rel orderedVars = <LdrColor>

        def RenderVar "LdrColor" {{
            string sourceName = "LdrColor"
        }}
    }}
}}
"""


def main():
    parser = argparse.ArgumentParser(description="Crop window demo using ovrtx")
    parser.add_argument("--png", action="store_true", help="Save render to _output/render.png instead of displaying")
    args = parser.parse_args()

    if not TEST_BASE_NO_LIGHT.exists():
        print(f"Error: test base scene not found at {TEST_BASE_NO_LIGHT}", file=sys.stderr)
        sys.exit(1)

    scene_usda = generate_scene_usda(TEST_BASE_NO_LIGHT, TEST_BASE_LIGHT)

    # [snippet:crop-window-setup]
    print("Creating renderer...", file=sys.stderr)
    ovrtx.register_schema_paths()
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.crop-window")
    renderer.attach_ovstage(stage)

    print("Loading scene...", file=sys.stderr)
    ordinal = 1
    ovstage.population.open_usd_from_string(stage, scene_usda, ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    # [/snippet:crop-window-setup]

    # [snippet:crop-window-step-and-verify]
    print("Stepping renderer...", file=sys.stderr)
    products = renderer.step(
        render_products={"/Render/Camera"},
        delta_time=1.0 / 60,
        ordinal=ordinal,
    )

    for _product_name, product in products.items():
        for frame in product.frames:
            var = frame.render_vars[LDR_COLOR_PATH].map(device=ovrtx.Device.CPU)
            view = np.from_dlpack(var)
            pixels = view.copy()
            del view
            var.unmap()
            del var

            height, width = pixels.shape[:2]

            print(f"Full resolution: {FULL_RESOLUTION[0]}x{FULL_RESOLUTION[1]}", file=sys.stderr)
            print(f"Crop window NDC: {CROP_NDC}", file=sys.stderr)
            print(f"Output size:     {width}x{height}", file=sys.stderr)

            img = Image.fromarray(pixels)
            if args.png:
                output_dir = SCRIPT_DIR / "_output"
                output_dir.mkdir(exist_ok=True)
                img.save(output_dir / "render.png")
                print(f"Saved to {output_dir / 'render.png'}", file=sys.stderr)
            else:
                img.show()

            print(f"Full resolution: {FULL_RESOLUTION[0]}x{FULL_RESOLUTION[1]}", file=sys.stderr)
            print(f"Crop window NDC: {CROP_NDC}", file=sys.stderr)
            print(f"Output size:     {width}x{height}", file=sys.stderr)

            assert width == EXPECTED_CROP[0] and height == EXPECTED_CROP[1], (
                f"Expected {EXPECTED_CROP[0]}x{EXPECTED_CROP[1]}, got {width}x{height}"
            )
            print(f"Verified: output is {width}x{height} as expected.", file=sys.stderr)
    # [/snippet:crop-window-step-and-verify]

    del frame, product, products
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


if __name__ == "__main__":
    main()
