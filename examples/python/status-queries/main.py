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


# [snippet:format-operation-status]
def print_operation_status(label: str, status: ovrtx.OperationStatus) -> None:
    if status.progress < 0.0:
        progress = "indeterminate"
    else:
        progress = f"{status.progress:.0%}"

    counters = []
    for counter in status.counters:
        total = "unknown" if counter.total == 0 else str(counter.total)
        counters.append(f"{counter.name}={counter.current}/{total}")

    counter_text = f" ({', '.join(counters)})" if counters else ""
    print(f"{label}: state={status.state.name} progress={progress}{counter_text}", file=sys.stderr)
# [/snippet:format-operation-status]


# [snippet:wait-operation-with-status]
def wait_with_status(op: ovrtx.Operation, label: str):
    result = op.wait(timeout_ns=1_000_000_000)
    while result is None:
        print_operation_status(label, op.query_status())
        result = op.wait(timeout_ns=1_000_000_000)
    return result
# [/snippet:wait-operation-with-status]


def print_shader_compile_status(status: ovrtx.OperationStatus) -> None:
    if status.progress > 0.0:
        print(f"compiling shaders {int(status.progress * 100)}%...", file=sys.stderr)


def wait_for_shader_cache_step(op: ovrtx.Operation):
    result = op.wait(timeout_ns=1_000_000_000)
    while result is None:
        print_shader_compile_status(op.query_status())
        result = op.wait(timeout_ns=1_000_000_000)
    return result


def main():
    parser = argparse.ArgumentParser(description="ovrtx Python status query example")
    parser.add_argument("--png", action="store_true", help="Save render to _output/render.png instead of displaying")
    args = parser.parse_args()

    # [snippet:create-renderer]
    # Create the Renderer and attach the stage that owns scene data.
    output_dir = Path("_output")
    output_dir.mkdir(exist_ok=True)
    config = ovrtx.RendererConfig(log_file_path=str(output_dir / "status-queries-ovrtx.log"))
    print("Creating renderer...", file=sys.stderr)
    renderer = ovrtx.Renderer(config=config)
    stage = ovstage.Stage("ovrtx.example.status-queries")
    renderer.attach_ovstage(stage)
    print("Renderer created.", file=sys.stderr)
    # [/snippet:create-renderer]

    # [snippet:load-usd-with-status]
    # Population operations complete on the stage; poll with a wait timeout
    # (nanoseconds) for coarse progress reporting while the scene loads.
    print(f"Opening {USD_URL}...", file=sys.stderr)
    ordinal = 1
    load_op = ovstage.population.open_usd_async(stage, USD_URL, ordinal=ordinal)
    while load_op.wait(timeout=1_000_000_000) is None:
        print("open_usd: loading...", file=sys.stderr)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    print("USD loaded.", file=sys.stderr)
    # [/snippet:load-usd-with-status]

    # [snippet:compile-shader-cache-with-status]
    shader_cache_op = renderer.step_async(
        render_products={"/Render/Camera"},
        delta_time=1.0 / 60,
        ordinal=ordinal,
    )
    pending_shader_cache_products = wait_for_shader_cache_step(shader_cache_op)
    shader_cache_products = pending_shader_cache_products.fetch()
    del shader_cache_products, pending_shader_cache_products, shader_cache_op
    # [/snippet:compile-shader-cache-with-status]

    # [snippet:step-with-status]
    # Step the renderer to simulate the Camera at 60Hz.
    print("Stepping renderer...", file=sys.stderr)
    step_op = renderer.step_async(
        render_products={"/Render/Camera"},
        delta_time=1.0 / 60,
        ordinal=ordinal,
    )
    pending_products = wait_with_status(step_op, "step")
    products = pending_products.fetch()
    print("Stepped renderer.", file=sys.stderr)
    # [/snippet:step-with-status]

    # [snippet:read-render-output]
    # Get the Camera output for the step as a numpy array and display it
    print("Fetching results...", file=sys.stderr)
    for _product_name, product in products.items():
        for frame in product.frames:
            var = frame.render_vars["/Render/Camera/LdrColor"].map(device=ovrtx.Device.CPU)
            view = np.from_dlpack(var)
            pixels = view.copy()
            del view
            var.unmap()
            img = Image.fromarray(pixels)
            if args.png:
                img.save(output_dir / "render.png")
                print(f"Saved to {output_dir / 'render.png'}", file=sys.stderr)
            else:
                img.show()
    print("Fetched results.", file=sys.stderr)
    # [/snippet:read-render-output]

    del var, frame, product, products
    del pending_products, step_op
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


if __name__ == "__main__":
    main()
