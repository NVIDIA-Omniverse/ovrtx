# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Validate process startup contracts and spectral effects beyond convergence error."""

import os
import subprocess
import sys
from functools import cache
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

EXAMPLE = Path(__file__).parents[3] / "examples/python/spectral-rendering/main.py"


@pytest.fixture(scope="module")
def render_spectral(output_dir):
    """Cache subprocess captures; each transport initializes its own material backend."""
    output_dir = output_dir / "spectral" / os.environ.get("PYTEST_XDIST_WORKER", "main")
    output_dir.mkdir(parents=True, exist_ok=True)

    @cache
    def capture_transport(transport):
        """Amortize startup while keeping RGB and spectral material backends in separate processes."""
        subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--capture-comparisons", transport, str(output_dir)],
            check=True,
            timeout=900,
        )

    @cache
    def render(illuminant, transport, spp):
        """Return linear RGB block averages to compare transport without display processing."""
        capture_transport(transport)
        output = output_dir / f"{illuminant}-{transport}-{spp}.png"
        hdr = output.with_suffix(".npy")
        with Image.open(output) as image:
            assert image.size == (256, 256)
            # Measure spatial variation per channel: a solid red error image must fail.
            assert np.asarray(image)[..., :3].std(axis=(0, 1)).max() > 5
        values = np.load(hdr)[..., :3].astype(np.float64)
        assert np.isfinite(values).all()
        return values.reshape(16, 16, 16, 16, 3).mean(axis=(1, 3))

    return render


@pytest.mark.parametrize("illuminant", ["white", "sodium", "mercury"])
def test_spectral_example_outputs(illuminant, render_spectral):
    """Every authored illuminant must produce a nonconstant image in both transports."""
    for transport in ("rgb", "spectral"):
        render_spectral(illuminant, transport, 2048)


@pytest.mark.parametrize("illuminant", ["sodium", "mercury"])
def test_spectral_effect_exceeds_convergence_change(illuminant, render_spectral):
    """Transport differences must exceed the measured sample-count change in both estimators."""
    low = [render_spectral(illuminant, t, 512) for t in ("rgb", "spectral")]
    high = [render_spectral(illuminant, t, 2048) for t in ("rgb", "spectral")]
    convergence = max(np.abs(a - b).mean() for a, b in zip(low, high))
    effect = np.abs(high[0] - high[1]).mean()
    assert effect > max(3 * convergence, 1e-5), (illuminant, effect, convergence)


@pytest.mark.parametrize("transport", ["rgb", "spectral"])
def test_illuminant_response(transport, render_spectral):
    """Catch ignored spectra: sodium must suppress blue and differ from the white baseline."""
    white = render_spectral("white", transport, 2048)
    sodium = render_spectral("sodium", transport, 2048)
    white_mean = white.mean(axis=(0, 1))
    sodium_mean = sodium.mean(axis=(0, 1))
    assert sodium_mean[2] / sodium_mean[0] < 0.25 * white_mean[2] / white_mean[0]
    for illuminant in ("sodium", "mercury"):
        values = render_spectral(illuminant, transport, 2048)
        assert np.abs(values - white).mean() > 0.01 * np.abs(white).mean()


@pytest.mark.parametrize("enabled", [False, True, None])
def test_spectral_startup_configuration(enabled):
    """Exercise conversion, config readback, inheritance, and conflicting startup requests."""
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), str(-1 if enabled is None else int(enabled))],
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _capture_startup_frame(renderer, enabled):
    """Exercise restored material, scene, and shader resources after full system teardown."""
    import ovrtx
    import ovstage

    stage = ovstage.Stage("spectral-config-lifecycle")
    renderer.attach_ovstage(stage)
    try:
        source = EXAMPLE.with_name("spectral.usda").as_posix()
        transport = "" if enabled is None else ("spectral" if enabled else "rgb")
        layer = f"""#usda 1.0
(subLayers = [@{source}@])
over "World" {{
    over "RectLight" (variants = {{ string illuminant = "sodium" }}) {{}}
}}
over "Render" {{
    over "Camera" (variants = {{ string transport = "{transport}" }}) {{
        uint omni:rtx:pt:samplesPerPixel = 512
        int2 resolution = (64, 64)
    }}
}}
"""
        ovstage.population.open_usd_from_string(stage, layer, ordinal=1)
        stage.advance_write_floor(1, ovstage.Scope.ALL).wait()
        products = renderer.step(render_products={"/Render/Camera"}, delta_time=1 / 60, ordinal=1)
        frame = products["/Render/Camera"].frames[-1]
        mapped = frame.render_vars["/Render/Camera/HdrColor"].map(device=ovrtx.Device.CPU)
        pixels = np.from_dlpack(mapped).copy()[..., :3]
        mapped.unmap()
        del mapped, frame, products
        assert np.isfinite(pixels).all()
        assert pixels.std(axis=(0, 1)).max() > 0.001
        return pixels.mean(axis=(0, 1))
    finally:
        renderer.detach_ovstage()
        stage.destroy()


def _check_startup_configuration(enabled):
    """Run in a fresh process because the choice survives renderer destruction."""
    import ovrtx

    config = ovrtx.RendererConfig(enable_spectral_rendering=enabled, keep_system_alive=False)
    renderer = ovrtx.Renderer(config=config)
    try:
        assert renderer.config.enable_spectral_rendering is enabled
        before = _capture_startup_frame(renderer, bool(enabled))
        if enabled:
            # No variant selection authors no transport attribute; the startup default should apply.
            omitted = _capture_startup_frame(renderer, None)
            np.testing.assert_allclose(omitted, before, rtol=0.03, atol=0.001)
        inherited = ovrtx.Renderer(config=ovrtx.RendererConfig(keep_system_alive=False))
        inherited.destroy()
        matching = ovrtx.Renderer(config=config)
        matching.destroy()
        with pytest.raises(RuntimeError, match="enable_spectral_rendering must match"):
            ovrtx.Renderer(config=ovrtx.RendererConfig(enable_spectral_rendering=not enabled))
    finally:
        renderer.destroy()
    # Releasing graphics resources does not make the persistent material backend switchable.
    with pytest.raises(RuntimeError, match="enable_spectral_rendering must match"):
        ovrtx.Renderer(config=ovrtx.RendererConfig(enable_spectral_rendering=not enabled))
    inherited = ovrtx.Renderer(config=ovrtx.RendererConfig(keep_system_alive=False))
    try:
        after = _capture_startup_frame(inherited, bool(enabled))
        np.testing.assert_allclose(after, before, rtol=0.03, atol=0.001)
    finally:
        inherited.destroy()


def _capture_comparisons(transport, output_dir):
    """Run the canonical example for all sample-count comparisons with one startup choice."""
    import runpy

    example = runpy.run_path(str(EXAMPLE), run_name="spectral_example")
    output_dir = Path(output_dir)
    for illuminant in ("white", "sodium", "mercury"):
        for spp in ((2048,) if illuminant == "white" else (512, 2048)):
            output = output_dir / f"{illuminant}-{transport}-{spp}.png"
            hdr = output.with_suffix(".npy")
            output.unlink(missing_ok=True)
            hdr.unlink(missing_ok=True)
            sys.argv = [
                str(EXAMPLE), "--illuminant", illuminant, "--transport", transport,
                "--spp", str(spp), "--size", "256", "--png", str(output),
                "--hdr", str(hdr), "--log", str(output.with_suffix(".log")),
            ]
            print(f"Rendering {illuminant}, {transport}, {spp} samples", flush=True)
            example["main"]()


if __name__ == "__main__":
    if sys.argv[1] == "--capture-comparisons":
        _capture_comparisons(sys.argv[2], sys.argv[3])
    else:
        _check_startup_configuration(None if sys.argv[1] == "-1" else bool(int(sys.argv[1])))
