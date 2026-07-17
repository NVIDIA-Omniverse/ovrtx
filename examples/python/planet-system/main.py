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
Animated planetary system demo using ovrtx Python bindings.

Demonstrates:
- Loading a USD scene and injecting additional geometry via add_usd_reference_from_string
- Using bind_attribute/map_attribute for zero-copy transform updates
- GPU-accelerated animation using Warp kernels
- Hierarchical animation (orbit parent rotation + planet self-spin)

Usage:
    python main.py                    # CPU mode, streams to rerun.io
    python main.py --gpu              # CUDA mode
    python main.py --num-planets 500  # Scale test (1-1000)
    python main.py --png              # Save frames to _output/
    python main.py --no-rr            # Disable rerun.io streaming
    python main.py --log              # Enable carb log file
"""

import argparse
import math
from pathlib import Path

import numpy as np
import warp as wp

from ovrtx import Device, PrimMode, Renderer, RendererConfig

# Script directory for output
SCRIPT_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = SCRIPT_DIR / "_output"

# USD scene path (relative to rendering tree root)
RENDERING_ROOT = SCRIPT_DIR.parents[2].resolve()  # [0]examples -> [1]source -> [2]rendering
USD_SCENE = "simple_scene.usda"


def generate_orbit_layer_usda(num_planets: int, orbit_radius: float, planet_scale: float) -> str:
    """Generate USDA layer with Orbit Xform containing N planet cubes.

    This layer is added under /World/Cube, so planets automatically inherit
    the cube's transform. Only need to animate localMatrix for rotation.

    Hierarchy (added under /World/Cube):
        /Orbit  <-- Rotate this via localMatrix for orbital motion
            /Planet_0  <-- Individual cubes that spin locally
            /Planet_1
            ...
    """
    from math import cos, pi, sin

    orbit_str = r"""#usda 1.0
(
    defaultPrim = "Orbit"
)

def Xform "Orbit" {
    matrix4d xformOp:transform = ( (1,0,0,0), (0,1,0,0), (0,0,1,0), (0,0,0,1) )
    uniform token[] xformOpOrder = ["xformOp:transform"]
"""

    planet_lines = []
    half_size = planet_scale / 2.0
    for i in range(num_planets):
        # Initial position in ring (XZ plane, Y=0 relative to Orbit)
        angle = (2.0 * pi * i) / num_planets
        x = orbit_radius * cos(angle)
        z = orbit_radius * sin(angle)
        planet_lines.append(
            rf"""
    def Cube "Planet_{i}" {{
        float3[] extent = [({-half_size}, {-half_size}, {-half_size}), ({half_size}, {half_size}, {half_size})]
        double size = {planet_scale}
        matrix4d xformOp:transform = ( (1,0,0,0), (0,1,0,0), (0,0,1,0), ({x:.2f},0,{z:.2f},1) )
        uniform token[] xformOpOrder = ["xformOp:transform"]
    }}"""
        )

    return orbit_str + "".join(planet_lines) + "\n}"


# Warp kernel for planetary system animation
@wp.func
def make_y_rotation_transform(angle: wp.float64, tx: wp.float64, ty: wp.float64, tz: wp.float64) -> wp.mat44d:
    """Build 4x4 transform: Y-axis rotation + translation."""
    c = wp.cos(angle)
    s = wp.sin(angle)
    _0 = wp.float64(0.0)
    _1 = wp.float64(1.0)
    return wp.mat44d(c, _0, s, _0, _0, _1, _0, _0, -s, _0, c, _0, tx, ty, tz, _1)


@wp.kernel
def compute_system_transforms(
    transforms: wp.array(dtype=wp.mat44d),
    time: wp.float64,
    orbit_speed: wp.float64,
    spin_speed: wp.float64,
    orbit_radius: wp.float64,
    tau: wp.float64,
    num_planets: int,
):
    """Compute transforms for entire planetary system in one kernel.

    Index layout:
    - transforms[0]: Orbit parent Xform (rotates whole system)
    - transforms[1:]: Individual planet transforms (position + local spin)
    """
    tid = wp.tid()
    _0 = wp.float64(0.0)

    if tid == 0:
        # Index 0: Orbit parent transform (Y-axis rotation only)
        orbit_angle = time * orbit_speed
        transforms[0] = make_y_rotation_transform(orbit_angle, _0, _0, _0)
    else:
        # Fixed position in ring (local to Orbit parent)
        phase = (tau * wp.float64(tid - 1)) / wp.float64(num_planets)
        x = orbit_radius * wp.cos(phase)
        z = orbit_radius * wp.sin(phase)

        # Self-rotation around local Y-axis
        spin_angle = time * spin_speed
        transforms[tid] = make_y_rotation_transform(spin_angle, x, _0, z)


def run_animation(device: Device, num_planets: int, save_png: bool, enable_log: bool, rr) -> None:
    """Run the planetary system animation.

    Args:
        device: Device.CPU or Device.CUDA
        num_planets: Number of planets to animate (1-1000)
        save_png: Save rendered frames as PNGs
        enable_log: Enable carb log file
        rr: rerun module (already initialized) or None to skip streaming
    """
    # Computed constants
    num_transforms = num_planets + 1  # orbit (index 0) + planets
    orbit_radius = 100.0  # Well beyond cube half-extent (25) + margin
    # Logarithmic scale: 36 planets → 10.0, 1000 planets → ~5.2
    planet_scale = 10.0 * math.log2(37) / math.log2(num_planets + 1)

    # Timing: simulation at 100 Hz, renderer at 60 fps
    SIM_HZ = 100
    SIM_DELTA_TIME = 1.0 / SIM_HZ  # 0.01s per simulation step
    SIM_DURATION = 4.0  # 4 seconds for one full orbit cycle
    NUM_SIM_STEPS = int(SIM_DURATION * SIM_HZ)

    # Animation speeds for perfect loop: speed = N × 2π / duration
    # - Orbit: 1 full rotation (N=1) → 2π/4 = π/2 rad/s
    # - Spin: 6 full rotations (N=6) → 12π/4 = 3π rad/s
    ORBIT_SPEED = math.tau / SIM_DURATION  # 1 orbit cycle
    SPIN_SPEED = 6 * math.tau / SIM_DURATION  # 6 spin cycles (lines up at end)

    # Prepare output directory
    if save_png:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        from PIL import Image

    # Build renderer config
    log_path = str(OUTPUT_DIR / "anim_planet_system.log") if enable_log else None
    config = RendererConfig(log_file_path=log_path)
    renderer = Renderer(config)

    print(f"Device: {device.name}")
    print(f"USD scene: {USD_SCENE}")
    print(f"Simulation: {NUM_SIM_STEPS} steps @ {SIM_HZ} Hz ({SIM_DURATION}s)")
    print(f"Animation: {num_planets} planets, orbit={orbit_radius}, scale={planet_scale:.1f}")

    # 1. Load base scene (cube is our "sun")
    renderer.open_usd(str(USD_SCENE))

    # 2. Inject orbit layer under /World/Cube (inherits cube's transform automatically)
    orbit_usda = generate_orbit_layer_usda(num_planets, orbit_radius, planet_scale)
    renderer.add_usd_reference_from_string(orbit_usda, "/World/Cube/Orbit")

    # 3. Create SINGLE binding for all prims (1 orbit + N planets)
    all_prim_paths = ["/World/Cube/Orbit"] + [f"/World/Cube/Orbit/Planet_{i}" for i in range(num_planets)]
    system_binding = renderer.bind_attribute(
        prim_paths=all_prim_paths,
        attribute_name="omni:xform",
        dtype="float64",
        shape=(4, 4),
        prim_mode=PrimMode.MUST_EXIST,
    )

    # 4. Animation loop - simulation at 100 Hz, renderer produces at 60 fps
    # Binding is persistent, but mapping is per-frame (writes flush to Fabric on unmap)
    cuda_stream = None
    rendered_frame_count = 0
    for sim_step in range(NUM_SIM_STEPS):
        sim_time = sim_step * SIM_DELTA_TIME  # Current frame's time

        # Map, compute transforms, unmap (writes back to renderer scene)
        with system_binding.map(device=device, device_id=0) as attr_mapping:
            wp_transforms = wp.from_dlpack(attr_mapping.tensor, dtype=wp.mat44d)
            if cuda_stream is None and device == Device.CUDA:
                cuda_stream = wp.Stream(device=wp_transforms.device)

            wp.launch(
                kernel=compute_system_transforms,
                dim=num_transforms,
                inputs=[
                    wp_transforms,
                    wp.float64(sim_time),
                    wp.float64(ORBIT_SPEED),
                    wp.float64(SPIN_SPEED),
                    wp.float64(orbit_radius),
                    wp.float64(math.tau),
                    num_planets,
                ],
                device=wp_transforms.device,
            )
            attr_mapping.unmap(stream=cuda_stream.cuda_stream if cuda_stream else None)

        # Step renderer - uses transforms computed above for current sim_time
        products = renderer.step(
            render_products={"/Render/OmniverseKit/HydraTextures/ViewportTexture0"}, delta_time=SIM_DELTA_TIME
        )

        # Process rendered frames (requires --png or --rr to produce visible output)
        for product_name, product in products.items():
            for frame in product.frames:
                rendered_frame_count += 1
                if "LdrColor" not in frame.render_vars:
                    continue

                var = frame.render_vars["LdrColor"].map(device=device)
                np_array = wp.from_dlpack(var).numpy()

                # Save/stream frame
                if save_png:
                    Image.fromarray(np_array).save(OUTPUT_DIR / f"planetary_system_{rendered_frame_count:03d}.png")
                    print(f"  Saved frame {rendered_frame_count} (sim step {sim_step}, t={sim_time:.3f}s)")
                if rr:
                    rr.set_time("sim_time", duration=sim_time)
                    rr.log("render/LdrColor", rr.Image(np_array))

    print(f"Simulation: {NUM_SIM_STEPS} steps @ {SIM_HZ} Hz -> {rendered_frame_count} rendered frames @ 60 fps")

    # 5. Cleanup - unbind
    system_binding.unbind()

    # 6. Save final state via debug dump
    products = renderer.step(render_products={"ovrtx_debug_dump_stage"}, delta_time=0.0)
    frame = products["ovrtx_debug_dump_stage"].frames[0]
    var = frame.render_vars["debug"].map(device=Device.CPU)
    dump = np.from_dlpack(var).tobytes().decode("utf-8")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / f"planetary_system_final.usda").write_text(dump, encoding="utf-8")

    print(f"Animated {num_planets} planets on {device.name}: {NUM_SIM_STEPS} sim steps @ {SIM_HZ} Hz")
    if save_png:
        print(f"  Frames saved to: {OUTPUT_DIR}")


def main():
    parser = argparse.ArgumentParser(
        description="Animated planetary system demo using ovrtx Python bindings.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # CPU mode, streams to rerun.io
  python main.py --gpu              # CUDA mode
  python main.py --num-planets 500  # Scale test (1-1000)
  python main.py --png              # Save frames to _output/
  python main.py --no-rr            # Disable rerun.io streaming
  python main.py --log              # Enable carb log file

To create a video from frames:
  ffmpeg -framerate 60 -i _output/planetary_system_%03d.png -c:v libx264 -pix_fmt yuv420p planet.mp4
""",
    )
    parser.add_argument("--gpu", action="store_true", help="Use CUDA device (default: CPU)")
    parser.add_argument("--num-planets", type=int, default=36, help="Number of planets (1-1000, default: 36)")
    parser.add_argument("--png", action="store_true", help="Save rendered frames as PNGs to _output/")
    parser.add_argument("--no-rr", action="store_true", help="Disable rerun.io streaming (enabled by default)")
    parser.add_argument("--log", action="store_true", help="Enable carb log file in _output/")
    args = parser.parse_args()

    # Sanitize num_planets
    num_planets = max(1, min(1000, args.num_planets))

    # Initialize rerun (enabled by default, disable with --no-rr)
    rr = None
    if not args.no_rr:
        try:
            import rerun as rr

            rr.init("ovrtx_example_anim_planet_system", spawn=True)
        except ImportError:
            print("Warning: rerun not installed, skipping rerun.io streaming.")
            print("  Install with: pip install rerun-sdk")

    wp.init()
    run_animation(
        device=Device.CUDA if args.gpu else Device.CPU,
        num_planets=num_planets,
        save_png=args.png,
        enable_log=args.log,
        rr=rr,
    )


if __name__ == "__main__":
    main()

