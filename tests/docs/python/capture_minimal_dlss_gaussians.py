# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Capture independent Minimal Gaussian sequences for the DLSS regression test."""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

import ovrtx
import ovstage


def capture(mode: int, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    scene_path = Path(__file__).parents[1] / "data" / "minimal_dlss_gaussians.usda"
    renderer = ovrtx.Renderer(
        ovrtx.RendererConfig(
            log_file_path=str(output.with_suffix(".log")),
            enable_geometry_streaming=True,
        )
    )
    stage = ovstage.Stage("ovrtx.docs.minimal-dlss-gaussians")
    renderer.attach_ovstage(stage)
    try:
        scene = f"""#usda 1.0
        (subLayers = [@{scene_path.resolve().as_posix()}@])
        over "Render" {{
            over "Camera" {{
                int omni:rtx:minimal:dlss:mode = {mode}
            }}
        }}
        """
        ovstage.population.open_usd_from_string(stage, scene, ordinal=1)
        stage.advance_write_floor(1, ovstage.Scope.ALL).wait()
        samples = []
        # Let temporal reconstruction settle, then measure a sequence rather than
        # the random noise in one chosen frame. Each mode starts in a fresh process.
        sample_count = 128 if mode == 0 else 32
        for frame_index in range(32 + sample_count):
            products = renderer.step(render_products={"/Render/Camera"}, delta_time=1.0 / 60.0, ordinal=1)
            for frame in products["/Render/Camera"].frames:
                with frame.render_vars["/Render/Camera/LdrColor"].map(device=ovrtx.Device.CPU) as mapped:
                    pixels = np.from_dlpack(mapped).copy()
                if frame_index >= 32:
                    samples.append(pixels[..., :3])
                del frame
            del products
        if len(samples) != sample_count:
            raise RuntimeError(f"Expected {sample_count} Gaussian frames, got {len(samples)}")
        frames = np.stack(samples)
        np.savez_compressed(output, frames=frames)
        Image.fromarray(frames[-1]).save(output.with_suffix(".png"))
        Image.fromarray(frames.mean(axis=0).astype(np.uint8)).save(output.with_name(f"{output.stem}-mean.png"))
    finally:
        renderer.detach_ovstage()
        stage.destroy()
        renderer.destroy()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", type=int, choices=(0, 1, 2))
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    capture(args.mode, args.output)
