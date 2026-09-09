# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Tests for camera_sensors.rst Python code examples."""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import ovrtx
import ovstage

SCENE_PATH = str((Path(__file__).parent / "../../../tests/data/simple_camera.usda").resolve())
LDR_COLOR_PATH = "/Render/Camera/LdrColor"
HDR_COLOR_PATH = "/Render/Camera/HdrColor"

USDA = f"""#usda 1.0
(
    subLayers = [
        @{SCENE_PATH}@
    ]
)

def "Render" {{
    def RenderProduct "Camera" {{
        int2 resolution = (1920, 1080)
        rel camera = </Camera0>
        rel orderedVars = [<LdrColor>, <HdrColor>]

        def RenderVar "LdrColor" {{
            string sourceName = "LdrColor"
        }}

        def RenderVar "HdrColor" {{
            string sourceName = "HdrColor"
        }}
    }}
}}
"""


def test_step_and_map_camera_outputs(renderer, stage, output_dir):
    """Test stepping and mapping both LdrColor and HdrColor outputs (camera_sensors.rst)."""
    ordinal = 1
    ovstage.population.open_usd_from_string(stage, USDA, ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    # Warm up
    for _ in range(5):
        renderer.step(render_products={"/Render/Camera"}, delta_time=1.0 / 60, ordinal=ordinal)

    # [snippet:doc-step-and-map-camera-outputs]
    products = renderer.step(
        render_products={"/Render/Camera"},
        delta_time=1.0 / 60,
        ordinal=ordinal,
    )

    for product_name, product in products.items():
        for frame in product.frames:
            # LdrColor: uint8 sRGB image
            var = frame.render_vars[LDR_COLOR_PATH].map(device=ovrtx.Device.CPU)
            ldr_pixels = np.from_dlpack(var)  # shape: (H, W, 4), dtype: uint8
            assert ldr_pixels.shape == (1080, 1920, 4)
            assert ldr_pixels.dtype == np.uint8
            Image.fromarray(ldr_pixels).save(output_dir / "test_camera_sensors.LdrColor.png")

            # HdrColor: float16 linear image
            var = frame.render_vars[HDR_COLOR_PATH].map(device=ovrtx.Device.CPU)
            hdr_pixels = np.from_dlpack(var)  # shape: (H, W, 4), dtype: float16
            assert hdr_pixels.shape == (1080, 1920, 4)
            assert hdr_pixels.dtype == np.float16
    # [/snippet:doc-step-and-map-camera-outputs]


def test_step_async_returns_operation(renderer, stage):
    """``step_async`` returns an ``Operation[PendingFetch[RenderProductSetOutputs]]``.

    Replaces the 0.2.0 ``RendererResult`` return type — see CHANGELOG 0.3.0.
    """
    ordinal = 1
    ovstage.population.open_usd_from_string(stage, USDA, ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    # [snippet:doc-step-async]
    # step_async() returns an Operation. wait() resolves to a PendingFetch,
    # whose fetch() produces the RenderProductSetOutputs that step() would
    # have returned synchronously.
    op = renderer.step_async(
        render_products={"/Render/Camera"},
        delta_time=1.0 / 60,
        ordinal=ordinal,
    )
    pending = op.wait()
    products = pending.fetch()
    # [/snippet:doc-step-async]

    assert isinstance(op, ovrtx.Operation)
    assert isinstance(pending, ovrtx.PendingFetch)
    assert isinstance(products, ovrtx.RenderProductSetOutputs)


def test_map_camera_output_cuda(renderer, stage):
    """Map a render output as CUDA memory."""
    ordinal = 1
    ovstage.population.open_usd_from_string(stage, USDA, ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    products = renderer.step(render_products={"/Render/Camera"}, delta_time=1.0 / 60, ordinal=ordinal)

    # [snippet:doc-map-render-output-cuda]
    mapping = products["/Render/Camera"].frames[0].render_vars["/Render/Camera/LdrColor"].map(
        device=ovrtx.Device.CUDA
    )
    try:
        assert mapping.wait_event is not None
        mapping.wait()
        assert mapping.__dlpack_device__()[0] == 2  # DLPack kDLCUDA
    finally:
        mapping.unmap()
    # [/snippet:doc-map-render-output-cuda]


def test_map_camera_output_cuda_array(renderer, stage):
    """Map a render output as a CUDA array (the zero-copy image path)."""
    ordinal = 1
    ovstage.population.open_usd_from_string(stage, USDA, ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    products = renderer.step(render_products={"/Render/Camera"}, delta_time=1.0 / 60, ordinal=ordinal)

    # [snippet:doc-map-render-output-cuda-array]
    # Device.CUDA_ARRAY hands back the render target's CUDA array instead of copying
    # it into linear memory. The tensor therefore carries an opaque cudaArray_t handle
    # that no DLPack consumer can read. ovrtx exposes it as a plain int and leaves the
    # reading to you: wrap it with Warp 1.15+ (wp.Texture2D(cuda_array=...) then
    # copy_to() or wp.texture_sample()), with CuPy, or with your own CUDA wrapper.
    mapping = products["/Render/Camera"].frames[0].render_vars[LDR_COLOR_PATH].map(
        device=ovrtx.Device.CUDA_ARRAY
    )
    try:
        mapping.wait()  # Or mapping.wait_on(stream) to order a stream without blocking.
        tensor = mapping["LdrColor"]
        cuda_array = tensor.cuda_array  # cudaArray_t / CUarray -- an image handle, not a pointer.
        height, width, channels = tensor.shape

        # .device reports the resolved DLDevice, not the Device you asked for.
        assert mapping.device.device_type.value == ovrtx.DLDeviceType.kDLCUDA
        assert cuda_array != 0
        assert (height, width, channels) == (1080, 1920, 4)
        # The array belongs to one CUDA device, which is not necessarily device 0.
        # Make that device current before issuing copies against the handle.
        assert tensor.device.device_id >= 0
    finally:
        mapping.unmap()
    # [/snippet:doc-map-render-output-cuda-array]


def test_renderer_result_no_longer_exported():
    """The 0.2.0 ``RendererResult`` export was removed; importing it must fail."""
    with pytest.raises(ImportError):
        from ovrtx import RendererResult  # noqa: F401


def test_reset_re_bases_simulation_clock(renderer, stage):
    """``reset(time=T)`` re-bases the step window; frame capture is still at ``T + dt``.
    """
    ordinal = 1
    ovstage.population.open_usd_from_string(stage, USDA, ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    reset_time = 5.0
    delta_time = 1.0 / 60
    renderer.reset(time=reset_time)

    # [snippet:doc-reset-simulation-clock]
    products = renderer.step(
        render_products={"/Render/Camera"},
        delta_time=delta_time,
        ordinal=ordinal,
    )
    assert products.simulation_start_time == pytest.approx(reset_time)
    assert products.simulation_end_time == pytest.approx(reset_time + delta_time)
    # a render product associated with a camera sensor with no tick rate, will have both 
    # ``FrameOutput.start_time`` and ``FrameOutput.end_time`` equal to the step window
    # end simulation time.
    frame = products["/Render/Camera"].frames[-1]
    assert frame.start_time == pytest.approx(reset_time + delta_time)
    assert frame.end_time == pytest.approx(reset_time + delta_time)
    # [/snippet:doc-reset-simulation-clock]
