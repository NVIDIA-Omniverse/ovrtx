# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Render four image slices in succession and stitch them into one image.

The scene uses a 1024x1024 RenderProduct. The example renders its top-left,
top-right, bottom-left, and bottom-right 512x512 crops by updating OpenUSD's
``dataWindowNDC`` attribute, then assembles them into the full image.

Usage:
    uv run main.py              # Display the stitched render
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
SLICE_RESOLUTION = (512, 512)
WARMUP_FRAMES = 10
LDR_COLOR_PATH = "/Render/Camera/LdrColor"
SLICES = (
    # LdrColor rows follow dataWindowNDC's bottom-up Y order.
    ("TL", (0.0, 0.5, 0.5, 1.0), (512, 0)),
    ("TR", (0.5, 0.5, 1.0, 1.0), (512, 512)),
    ("BL", (0.0, 0.0, 0.5, 0.5), (0, 0)),
    ("BR", (0.5, 0.0, 1.0, 0.5), (0, 512)),
)


def generate_scene_usda(scene_path: Path, light_path: Path) -> str:
    """Generate the full-resolution scene whose data window will be sliced."""
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
        float4 dataWindowNDC = (0.0, 0.0, 1.0, 1.0)
        rel orderedVars = <LdrColor>

        def RenderVar "LdrColor" {{
            string sourceName = "LdrColor"
        }}
    }}
}}
"""


def render_slice(renderer: ovrtx.Renderer, ordinal: int) -> np.ndarray:
    """Render and copy one cropped LdrColor output into independent storage."""
    products = renderer.step(
        render_products={"/Render/Camera"},
        delta_time=1.0 / 60,
        ordinal=ordinal,
    )
    frame = products["/Render/Camera"].frames[-1]
    var = frame.render_vars[LDR_COLOR_PATH].map(device=ovrtx.Device.CPU)
    view = np.from_dlpack(var)
    pixels = view.copy()
    del view
    var.unmap()
    del var, frame, products
    return pixels


def main():
    parser = argparse.ArgumentParser(description="Sliced rendering demo using ovrtx")
    parser.add_argument(
        "--png", action="store_true", help="Save stitched render to _output/render.png instead of displaying"
    )
    args = parser.parse_args()

    if not TEST_BASE_NO_LIGHT.exists():
        print(f"Error: test base scene not found at {TEST_BASE_NO_LIGHT}", file=sys.stderr)
        sys.exit(1)

    scene_usda = generate_scene_usda(TEST_BASE_NO_LIGHT, TEST_BASE_LIGHT)

    # [snippet:sliced-rendering-setup]
    print("Creating renderer...", file=sys.stderr)
    ovrtx.register_schema_paths()
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.sliced-rendering")
    renderer.attach_ovstage(stage)

    print("Loading scene...", file=sys.stderr)
    ordinal = 1
    ovstage.population.open_usd_from_string(stage, scene_usda, ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    # [/snippet:sliced-rendering-setup]

    # [snippet:sliced-rendering-render-and-stitch]
    stitched = np.empty((FULL_RESOLUTION[1], FULL_RESOLUTION[0], 4), dtype=np.uint8)
    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/Render/Camera"])
        try:
            with stage.query_from_path_list(path_list) as query:
                attribute = paths.intern_token("dataWindowNDC")
                crop_dtype = ovstage.numpy_to_dldatatype(np.dtype(np.float32), lanes=4)

                for label, crop_ndc, (dst_y, dst_x) in SLICES:
                    ordinal += 1
                    crop_values = np.asarray([crop_ndc], dtype=np.float32)
                    crop_tensor = ovstage.make_dltensor(
                        crop_values,
                        dtype=crop_dtype,
                        shape=[1],
                        ndim=1,
                    )
                    stage.write_attribute(
                        query,
                        attribute,
                        ordinal=ordinal,
                        tensors=crop_tensor,
                        is_array=False,
                    ).wait()
                    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

                    print(f"Warming up {label} slice ({WARMUP_FRAMES} frames)...", file=sys.stderr)
                    for _ in range(WARMUP_FRAMES):
                        renderer.step(
                            render_products={"/Render/Camera"},
                            delta_time=1.0 / 60,
                            ordinal=ordinal,
                        )

                    print(f"Rendering {label} slice at {crop_ndc}...", file=sys.stderr)
                    pixels = render_slice(renderer, ordinal)
                    expected_shape = (SLICE_RESOLUTION[1], SLICE_RESOLUTION[0], 4)
                    assert pixels.shape == expected_shape, (
                        f"Expected {label} slice shape {expected_shape}, got {pixels.shape}"
                    )
                    stitched[
                        dst_y : dst_y + SLICE_RESOLUTION[1],
                        dst_x : dst_x + SLICE_RESOLUTION[0],
                    ] = pixels
        finally:
            paths.destroy_path_list(path_list)
    # [/snippet:sliced-rendering-render-and-stitch]

    image = Image.fromarray(stitched)
    if args.png:
        output_dir = SCRIPT_DIR / "_output"
        output_dir.mkdir(exist_ok=True)
        image.save(output_dir / "render.png")
        print(f"Saved stitched image to {output_dir / 'render.png'}", file=sys.stderr)
    else:
        image.show()

    print(f"Verified stitched output is {image.width}x{image.height}.", file=sys.stderr)

    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


if __name__ == "__main__":
    main()
