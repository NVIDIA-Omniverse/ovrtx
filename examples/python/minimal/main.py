# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import argparse
import sys
from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image

USD_URL = "https://omniverse-content-production.s3.us-west-2.amazonaws.com/Samples/Robot-OVRTX/robot-ovrtx.usda"


def main():
    parser = argparse.ArgumentParser(description="Minimal ovrtx Python example")
    parser.add_argument("--png", action="store_true", help="Save render to _output/render.png instead of displaying")
    args = parser.parse_args()

    # [snippet:create-renderer]
    # Create the Renderer and attach the stage that owns scene data.
    print("Creating renderer. The first run of the application will take some time as shaders are compiled and cached...", file=sys.stderr)
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.minimal")
    renderer.attach_ovstage(stage)
    print("Renderer created.", file=sys.stderr)
    # [/snippet:create-renderer]

    # [snippet:add-usd]
    print(f"Opening {USD_URL}...", file=sys.stderr)
    ordinal = 1
    ovstage.population.open_usd(stage, USD_URL, ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    print("USD loaded.", file=sys.stderr)
    # [/snippet:add-usd]

    # [snippet:step]
    # Step the renderer to simulate the Camera at 60Hz
    print("Stepping renderer...", file=sys.stderr)
    products = renderer.step(
        render_products={"/Render/Camera"},
        delta_time=1.0 / 60,
        ordinal=ordinal,
    )
    print("Stepped renderer.", file=sys.stderr)
    # [/snippet:step]

    # [snippet:read-render-output]
    # Get the Camera output for the step as a numpy array and display it
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
                output_dir = Path("_output")
                output_dir.mkdir(exist_ok=True)
                img.save(output_dir / "render.png")
                print(f"Saved to {output_dir / 'render.png'}", file=sys.stderr)
            else:
                img.show()
    print("Fetched results.", file=sys.stderr)
    # [/snippet:read-render-output]

    del frame, product, products
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


if __name__ == "__main__":
    main()
