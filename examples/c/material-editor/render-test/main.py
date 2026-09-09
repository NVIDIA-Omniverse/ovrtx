#!/usr/bin/env python3
"""Sanity check: load and render the material-editor ball scene via ovrtx Python API."""

import sys
from pathlib import Path

import numpy as np
import ovrtx
from PIL import Image

USDA_PATH = "../data/material-editor-ball.usda"
RENDER_PRODUCT = "/Render/Camera"
NUM_ITERATIONS = 50


def main():
    print("Creating renderer...", file=sys.stderr)
    renderer = ovrtx.Renderer()
    print("Renderer created.", file=sys.stderr)

    print(f"Loading {USDA_PATH}...", file=sys.stderr)
    renderer.open_usd(USDA_PATH)
    print("USD loaded.", file=sys.stderr)

    # Step once first to trigger hydra/material pipeline
    print("Stepping once to trigger material compilation...", file=sys.stderr)
    renderer.step(render_products={RENDER_PRODUCT}, delta_time=1.0 / 60)

    # Now try writing AFTER stepping (hypothesis: this will fail with size mismatch)
    print("Writing material binding and color after step...", file=sys.stderr)
    renderer.write_array_attribute(
        prim_paths=["/World/Sphere"],
        attribute_name="material:binding",
        tensors=[["/World/Looks/srf_green"]],
    )

    # Set diffuse color to blue — this should fail if the material pipeline
    # transformed the attribute from color3f (12 bytes) to something else (8 bytes)
    renderer.write_attribute(
        prim_paths=["/World/Looks/srf_green/Shader"],
        attribute_name="inputs:diffuse_color_constant",
        tensor=np.array([[0.1, 0.1, 0.6]], dtype=np.float32),
    )

    renderer.reset()
    print("Bound material and set color.", file=sys.stderr)

    # Step multiple times to converge
    for i in range(NUM_ITERATIONS):
        products = renderer.step(
            render_products={RENDER_PRODUCT},
            delta_time=1.0 / 60,
        )
        if (i + 1) % 10 == 0:
            print(f"  step {i + 1}/{NUM_ITERATIONS}", file=sys.stderr)

    # Map the final frame
    for _product_name, product in products.items():
        for frame in product.frames:
            with frame.render_vars["/Render/Camera/LdrColor"].map(device=ovrtx.Device.CPU) as var:
                pixels = var.tensor.numpy()
                img = Image.fromarray(pixels)
                output = Path("render_test.png")
                img.save(output)
                print(f"Saved to {output}", file=sys.stderr)


if __name__ == "__main__":
    main()
