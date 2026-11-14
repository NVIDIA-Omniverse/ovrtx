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

"""Render the compositing scene and save linear EXRs and LdrColor.png.

Run uv run render-aovs.py, or ./render-aovs.sh.
Defaults: 1280x720, 512 SPP, no denoising, _output/aov/.
Use --denoise aovs for denoised beauty and components.
Existing output files are overwritten. The source scene is never modified.
EXRs preserve floating-point RGBA values; preview PNGs are display-only.
"""

import argparse
import dataclasses
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import OpenEXR
from PIL import Image

import ovrtx
import ovstage

PRODUCT = "/Render/OmniverseKit/HydraTextures/omni_kit_widget_viewport_ViewportTexture_0"
AOVS = (
    "LdrColor",
    "HdrColor",
    "PtDirectIllumation",  # This spelling is the renderer's actual sourceName.
    "PtGlobalIllumination",
    "PtReflections",
    "PtRefractions",
    "PtSubsurfaceScattering",
    "PtSelfIllumination",
    "PtVolumes",
)
STAGE_METADATA_FIELDS = (
    "metersPerUnit",
    "upAxis",
    "timeCodesPerSecond",
    "startTimeCode",
    "endTimeCode",
    "framesPerSecond",
    "defaultPrim",
)


def read_stage_metadata(scene: Path) -> dict:
    """Read effective stage metadata through OVStage, without an extra USD Python dependency."""
    # Register RTX schemas before this first USD open freezes the schema registry.
    ovrtx.register_schema_paths()
    result = {}
    with ovstage.Stage("aov-compositing.source-metadata") as stage:
        ovstage.population.open_usd_with_desc(
            stage,
            str(scene),
            ordinal=1,
            time=ovstage.population.DEFAULT_TIME,
            descs=[ovstage.population.Desc(stage_metadata_paths=STAGE_METADATA_FIELDS)],
        )
        stage.advance_write_floor(1).wait()
        with ovstage.PathDictionary(stage) as paths:
            path_list = paths.create_path_list_from_strings(["/"])
            query = stage.query_from_path_list(path_list)
            try:
                for field in STAGE_METADATA_FIELDS:
                    read = stage.read_attributes(
                        query,
                        [paths.intern_token("usd-metadata:" + field)],
                        ovstage.OrdinalRange.latest(1),
                    )
                    values = []
                    try:
                        read.wait()
                        for group in read.groups():
                            try:
                                values.extend(group.columns[0].array(0).tolist())
                            finally:
                                stage.release_group(group)
                    finally:
                        read.release().wait()
                    if len(values) != 1:
                        raise RuntimeError(f"{scene}: expected one {field} value, got {values}")
                    value = values[0]
                    if field in ("upAxis", "defaultPrim"):
                        value = paths.token_to_string(ovstage.Token(value))
                    result[field] = value
            finally:
                stage.release_query(query).wait()
                paths.destroy_path_list(path_list)
    return result


def build_overlay(scene: Path, args: argparse.Namespace, stage_metadata: dict) -> str:
    """Override the existing product, retaining authored camera/material settings."""
    # Absolute sublayer identity preserves assets authored relative to the scene.
    if any(character in str(scene) for character in ("@", "\n", "\r")):
        raise ValueError("The scene path cannot contain @ or a newline")
    width, height = args.resolution
    spi = min(args.spp, 32)
    denoise = ""
    if args.denoise != "scene":
        denoise = (
            f"bool omni:rtx:pt:denoising:enabled = {str(args.denoise != 'none').lower()}\n"
            f"bool omni:rtx:pt:denoising:optix:denoiseAOVs = {str(args.denoise == 'aovs').lower()}\n"
        )
    ordered = ", ".join(f"</Render/Vars/{name}>" for name in AOVS)
    # USD stage metadata is NOT inherited from sublayers. Without this, a
    # meters-based scene becomes centimeters and its volumes become too thin.
    metadata_lines = "\n".join(f"    {name} = {json.dumps(value)}" for name, value in stage_metadata.items())
    return f"""#usda 1.0
(
    subLayers = [@{scene.as_posix()}@]
{metadata_lines}
)
over "Render"
{{
    over "OmniverseKit"
    {{
        over "HydraTextures"
        {{
            over "omni_kit_widget_viewport_ViewportTexture_0"
            {{
                uniform int2 resolution = ({width}, {height})
                token omni:rtx:rendermode = "PathTracing"
                token omni:rtx:post:tonemap:operator = "acesApproximation"
                float omni:rtx:post:tonemap:dither = 0
                token omni:rtx:post:tonemap:colorMode = "sRGBLinear"
                bool omni:rtx:post:tonemap:enableSrgbToGamma = true
                uint omni:rtx:pt:samplesPerPixel = {args.spp}
                int omni:rtx:pt:samplesPerIteration = {spi}
                int omni:rtx:quality = 100
                int omni:rtx:quality:minSpp = {args.spp}
                bool omni:rtx:pt:adaptiveSampling:enabled = false
                bool omni:rtx:pt:radianceCache:enabled = false
                bool omni:rtx:pt:dlss:enabled = false
                bool omni:rtx:pt:diAOV = true
                bool omni:rtx:pt:giAOV = true
                bool omni:rtx:pt:reflectionsAOV = true
                bool omni:rtx:pt:refractionsAOV = true
                bool omni:rtx:pt:subsurfaceScatteringAOV = true
                bool omni:rtx:pt:selfIllumAOV = true
                bool omni:rtx:pt:volumesAOV = true
                {denoise}
                rel orderedVars = [{ordered}]
            }}
        }}
    }}
}}
"""


def save_aov(output: Path, name: str, pixels: np.ndarray) -> dict:
    """Write lossless EXR data plus an explicitly display-only PNG preview."""
    if not pixels.size or not np.isfinite(pixels).all():
        raise RuntimeError(f"{name}: empty or non-finite renderer output")
    metadata = {
        "shape": list(pixels.shape),
        "dtype": str(pixels.dtype),
        "min": float(pixels.min()),
        "max": float(pixels.max()),
    }
    if pixels.ndim != 3 or pixels.shape[-1] != 4:
        raise RuntimeError(f"{name}: expected RGBA pixels, got {pixels.shape}")
    if name == "LdrColor":
        if pixels.dtype != np.uint8:
            raise RuntimeError(f"LdrColor: expected uint8, got {pixels.dtype}")
        Image.fromarray(pixels).save(output / f"{name}.png")
        metadata["image"] = f"{name}.png"
        return metadata
    if pixels.dtype not in (np.float16, np.float32):
        raise RuntimeError(f"{name}: expected floating-point output, got {pixels.dtype}")
    channels = {channel: np.ascontiguousarray(pixels[..., index]) for index, channel in enumerate("RGBA")}
    with OpenEXR.File({"compression": OpenEXR.ZIP_COMPRESSION, "type": OpenEXR.scanlineimage}, channels) as image:
        image.write(str(output / f"{name}.exr"))
    rgb = np.maximum(pixels[..., :3].astype(np.float32), 0)
    rgb = rgb / (1 + rgb)
    rgb = np.clip(rgb, 0, 1)
    rgb = np.where(rgb <= 0.0031308, 12.92 * rgb, 1.055 * rgb ** (1 / 2.4) - 0.055)
    Image.fromarray(np.rint(rgb * 255).astype(np.uint8)).save(output / f"{name}.preview.png")
    metadata.update(image=f"{name}.exr", preview=f"{name}.preview.png")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scene", type=Path, default=Path(__file__).resolve().with_name("aov-comp-scene.usda"))
    parser.add_argument("--spp", type=int, default=512, help="Path-tracing samples per pixel (default: 512)")
    parser.add_argument("--resolution", type=int, nargs=2, default=(1280, 720), metavar=("WIDTH", "HEIGHT"))
    parser.add_argument(
        "--denoise",
        choices=("scene", "none", "color", "aovs"),
        default="none",
        help="Denoising mode (default: none); aovs denoises beauty and every AOV",
    )
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "_output" / "aov")
    args = parser.parse_args()
    if args.spp < 1 or min(args.resolution) < 1:
        parser.error("SPP, width, and height must be positive")
    scene = args.scene.expanduser().resolve()
    if not scene.is_file():
        parser.error(f"Scene does not exist: {scene}")
    output = args.output_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    stage_metadata = read_stage_metadata(scene)
    overlay = build_overlay(scene, args, stage_metadata)
    (output / "render.usda").write_text(overlay, encoding="utf-8")
    if read_stage_metadata(output / "render.usda") != stage_metadata:
        raise RuntimeError("The render overlay changed the source stage's units, axis, or time metadata")
    # Remove the previous success record so a failed rerun cannot look complete.
    (output / "metadata.json").unlink(missing_ok=True)
    print(f"Rendering {scene}\nOutput: {output}\nSPP: {args.spp}; denoise: {args.denoise}", flush=True)
    # Avoid concurrent texture-feedback and VDB uploads during this offline capture.
    renderer = ovrtx.Renderer(
        ovrtx.RendererConfig(
            log_file_path=str(output / "renderer.log"),
            texture_streaming_mode="synchronous",
        )
    )
    started = time.monotonic()
    images = {}
    convergence = []
    try:
        with ovstage.Stage("aov-compositing.scene") as stage:
            renderer.attach_ovstage(stage)
            products = frame = mapped = None
            try:
                ovstage.population.open_usd_from_string(stage, overlay, ordinal=1)
                stage.advance_write_floor(1, ovstage.Scope.ALL).wait()
                # [snippet:doc-aov-compositing-render]
                # All components and the reference must come from the same converged frame.
                for attempt in range(8):
                    products = renderer.step(render_products={PRODUCT}, delta_time=1 / 60, ordinal=1)
                    if PRODUCT not in products or not products[PRODUCT].frames:
                        raise RuntimeError(f"Renderer returned no frame for {PRODUCT}")
                    frame = products[PRODUCT].frames[-1]
                    convergence.append(bool(frame.converged))
                    print(f"Render request {attempt + 1}: converged={frame.converged}", flush=True)
                    if frame.converged:
                        break
                    frame = products = None
                else:
                    raise RuntimeError("Path tracing did not converge after 8 render requests; see renderer.log")
                # Copy while mapped: the NumPy view otherwise borrows the renderer output.
                for name in AOVS:
                    with frame.render_vars[f"/Render/Vars/{name}"].map(device=ovrtx.Device.CPU) as mapped:
                        images[name] = np.from_dlpack(mapped).copy()
                # [/snippet:doc-aov-compositing-render]
                del mapped
            finally:
                # Drop borrowed frame/output handles before detaching and destroying the stage.
                mapped = None
                frame = products = None
                renderer.detach_ovstage()
        build_info = dataclasses.asdict(ovrtx.get_build_info())
    finally:
        renderer.destroy()
    render_seconds = time.monotonic() - started
    records = {}
    for name, pixels in images.items():
        if pixels.shape[:2] != (args.resolution[1], args.resolution[0]):
            raise RuntimeError(f"{name}: resolution mismatch: {pixels.shape}")
        records[name] = save_aov(output, name, pixels)
        print(f"Saved {name}", flush=True)
    metadata = {
        "scene": str(scene),
        "scene_sha256": hashlib.sha256(scene.read_bytes()).hexdigest(),
        "stage_metadata": stage_metadata,
        "render_product": PRODUCT,
        "resolution": list(args.resolution),
        "samples_per_pixel": args.spp,
        "denoise": args.denoise,
        "display_transform": "ACES Approximation followed by sRGB; no additional exposure in compositing",
        "converged": True,
        "convergence_by_request": convergence,
        "render_seconds": render_seconds,
        "ovrtx_build": build_info,
        "exr_values": "Unmodified renderer values, including alpha; no tone mapping or exposure conversion applied.",
        "preview_values": "Display only: Reinhard + sRGB.",
        "outputs": records,
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Complete: {len(AOVS)} AOV images in {output} ({render_seconds:.1f}s rendering)", flush=True)


if __name__ == "__main__":
    main()
