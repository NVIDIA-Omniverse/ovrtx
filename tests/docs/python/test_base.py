# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Tests using ovrtx-test-base.usda."""

from pathlib import Path

import numpy as np
import ovrtx
import ovstage
import pytest
from PIL import Image

TEST_BASE_PATH = str((Path(__file__).parent / "../data/ovrtx-test-base.usda").resolve())
LOGO_ANIMATED_PATH = str((Path(__file__).parent / "../data/ovrtx-test-base-logo-animated.usda").resolve())
LDR_COLOR_PATH = "/Render/Camera/LdrColor"
SLICED_RENDERING_USDA = f"""#usda 1.0
(
    subLayers = [@{Path(TEST_BASE_PATH).as_posix()}@]
)

over "Render" {{
    over RenderProduct "Camera" {{
        float4 dataWindowNDC = (0.0, 0.0, 1.0, 1.0)
    }}
}}
"""
RTPT_GLASS_USDA = f"""#usda 1.0
(
    subLayers = [@{Path(TEST_BASE_PATH).as_posix()}@]
)

over "Render" {{
    over "Camera" {{
        uint omni:rtx:rtpt:maxBounces = 2
    }}
}}

over "World" {{
    over "logo" {{
        over "logo" {{
            over "logo" {{
                rel material:binding = </World/Looks/srf_glass>
            }}
        }}
    }}
}}
"""


def _open(stage, path):
    ovstage.population.open_usd(stage, path, ordinal=1)
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()


def test_base(renderer, stage, output_dir):
    """Render LdrColor from /World/Camera using the test base scene."""
    _open(stage, TEST_BASE_PATH)

    for _ in range(5):
        renderer.step(render_products={"/Render/Camera"}, delta_time=1.0 / 60, ordinal=1)

    products = renderer.step(render_products={"/Render/Camera"}, delta_time=1.0 / 60, ordinal=1)
    for product in products.values():
        for frame in product.frames:
            var = frame.render_vars[LDR_COLOR_PATH].map(device=ovrtx.Device.CPU)
            pixels = np.from_dlpack(var)
            assert pixels.dtype == np.uint8
            assert pixels.shape[2] == 4
            Image.fromarray(pixels).save(output_dir / "base.Camera.LdrColor.0001.png")


def test_sliced_rendering(renderer, stage, output_dir):
    """Render four data-window crops and stitch them into one image."""
    ovstage.population.open_usd_from_string(stage, SLICED_RENDERING_USDA, ordinal=1)
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()

    # [snippet:doc-sliced-rendering]
    warmup_frames = 10

    def capture(ordinal):
        for _ in range(warmup_frames):
            renderer.step(render_products={"/Render/Camera"}, delta_time=1.0 / 60, ordinal=ordinal)

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

    full_frame = capture(ordinal=1)
    assert full_frame.shape == (512, 512, 4)
    assert full_frame.dtype == np.uint8

    slices = (
        # LdrColor rows follow dataWindowNDC's bottom-up Y order.
        ("TL", (0.0, 0.5, 0.5, 1.0), (256, 0)),
        ("TR", (0.5, 0.5, 1.0, 1.0), (256, 256)),
        ("BL", (0.0, 0.0, 0.5, 0.5), (0, 0)),
        ("BR", (0.5, 0.0, 1.0, 0.5), (0, 256)),
    )
    stitched = np.empty((512, 512, 4), dtype=np.uint8)

    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/Render/Camera"])
        try:
            with stage.query_from_path_list(path_list) as query:
                attribute = paths.intern_token("dataWindowNDC")
                crop_dtype = ovstage.numpy_to_dldatatype(np.dtype(np.float32), lanes=4)

                for ordinal, (label, crop_ndc, (dst_y, dst_x)) in enumerate(slices, start=2):
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

                    pixels = capture(ordinal)
                    assert pixels.shape == (256, 256, 4)
                    assert pixels.dtype == np.uint8
                    reference_tile = full_frame[dst_y : dst_y + 256, dst_x : dst_x + 256, :3]
                    tile_error = np.abs(
                        pixels[:, :, :3].astype(np.int16) - reference_tile.astype(np.int16)
                    ).mean()
                    assert tile_error < 8.0, f"{label} tile differs from its full-frame region: MAE={tile_error}"
                    stitched[dst_y : dst_y + 256, dst_x : dst_x + 256] = pixels
        finally:
            paths.destroy_path_list(path_list)

    Image.fromarray(full_frame).save(output_dir / "base.Camera.LdrColor.full.png")
    Image.fromarray(stitched).save(output_dir / "base.Camera.LdrColor.sliced.png")
    # [/snippet:doc-sliced-rendering]


def test_bind_material(renderer, stage, output_dir):
    """Bind the glass material to the logo and render."""
    _open(stage, TEST_BASE_PATH)

    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/World/logo/logo/logo"])
        with stage.query_from_path_list(path_list) as query:
            # [snippet:doc-bind-material]
            material_binding = paths.intern_token("material:binding")
            material_path = np.array([paths.intern_path("/World/Looks/srf_glass")], dtype=np.uint64)
            stage.write_attribute(
                query,
                material_binding,
                ordinal=2,
                tensors=material_path,
                is_array=True,
                semantic=ovstage.AttributeSemantic.RELATIONSHIP_PATH_ID,
            ).wait()
            stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
            # [/snippet:doc-bind-material]
        paths.destroy_path_list(path_list)

    # [snippet:doc-warmup]
    WARMUP_FRAMES = 40
    for _ in range(WARMUP_FRAMES):
        renderer.step(render_products={"/Render/Camera"}, delta_time=1.0 / 60, ordinal=2)
    # [/snippet:doc-warmup]

    products = renderer.step(render_products={"/Render/Camera"}, delta_time=1.0 / 60, ordinal=2)
    for product in products.values():
        for frame in product.frames:
            var = frame.render_vars[LDR_COLOR_PATH].map(device=ovrtx.Device.CPU)
            pixels = np.from_dlpack(var)
            assert pixels.dtype == np.uint8
            assert pixels.shape[2] == 4
            Image.fromarray(pixels).save(output_dir / "bind_material.Camera.LdrColor.0001.png")


def test_settings_rtpt_maxBounces(renderer, stage, output_dir):
    """Test omni:rtx:rtpt:maxBounces render setting at different values."""
    _open(stage, TEST_BASE_PATH)

    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/Render/Camera"])
        with stage.query_from_path_list(path_list) as query:
            attribute = paths.intern_token("omni:rtx:rtpt:maxBounces")
            for ordinal, max_bounces in enumerate([2, 3, 23], start=2):
                # [snippet:doc-set-render-setting]
                stage.write_attribute(
                    query,
                    attribute,
                    ordinal=ordinal,
                    tensors=np.array([max_bounces], dtype=np.uint32),
                    is_array=False,
                ).wait()
                stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
                # [/snippet:doc-set-render-setting]

                renderer.reset()
                for _ in range(40):
                    renderer.step(render_products={"/Render/Camera"}, delta_time=1.0 / 60, ordinal=ordinal)

                products = renderer.step(render_products={"/Render/Camera"}, delta_time=1.0 / 60, ordinal=ordinal)
                for product in products.values():
                    for frame in product.frames:
                        var = frame.render_vars[LDR_COLOR_PATH].map(device=ovrtx.Device.CPU)
                        pixels = np.from_dlpack(var)
                        assert pixels.dtype == np.uint8
                        assert pixels.shape[2] == 4
                        Image.fromarray(pixels).save(
                            output_dir
                            / f"settings_rtpt_maxBounces.Camera.LdrColor.maxBounces-{max_bounces}.0001.png"
                        )
        paths.destroy_path_list(path_list)


def test_settings_view_lighting_camera_light(renderer, stage, output_dir):
    """Test View Lighting Mode (camera light) settings, including the spot light type."""
    _open(stage, TEST_BASE_PATH)

    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/Render/Camera"])
        with stage.query_from_path_list(path_list) as query:
            # [snippet:doc-set-view-lighting]
            # Enable View Lighting Mode (camera light) and configure it as a spot light.
            # All settings share one ordinal so they publish together for the next render.
            stage.write_attribute(
                query,
                paths.intern_token("omni:rtx:scene:useViewLightingMode"),
                ordinal=2,
                tensors=np.array([True], dtype=np.bool_),
                is_array=False,
            ).wait()
            stage.write_attribute(
                query,
                paths.intern_token("omni:rtx:viewLighting:lightType"),
                ordinal=2,
                tensors=np.array([paths.intern_token("spot")], dtype=np.uint64),
                is_array=False,
                semantic=ovstage.AttributeSemantic.TOKEN_ID,
            ).wait()
            stage.write_attribute(
                query,
                paths.intern_token("omni:rtx:viewLighting:intensity"),
                ordinal=2,
                tensors=np.array([5000.0], dtype=np.float32),
                is_array=False,
            ).wait()
            stage.write_attribute(
                query,
                paths.intern_token("omni:rtx:viewLighting:coneAngle"),
                ordinal=2,
                tensors=np.array([30.0], dtype=np.float32),
                is_array=False,
            ).wait()
            stage.write_attribute(
                query,
                paths.intern_token("omni:rtx:viewLighting:coneSoftness"),
                ordinal=2,
                tensors=np.array([0.5], dtype=np.float32),
                is_array=False,
            ).wait()
            stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
            # [/snippet:doc-set-view-lighting]
        paths.destroy_path_list(path_list)

    # Reset and warm up so the settings take effect
    renderer.reset()
    for _ in range(40):
        renderer.step(render_products={"/Render/Camera"}, delta_time=1.0 / 60, ordinal=2)

    products = renderer.step(render_products={"/Render/Camera"}, delta_time=1.0 / 60, ordinal=2)
    assert "/Render/Camera" in products
    for product in products.values():
        assert len(product.frames) > 0
        for frame in product.frames:
            var = frame.render_vars[LDR_COLOR_PATH].map(device=ovrtx.Device.CPU)
            pixels = np.from_dlpack(var)
            assert pixels.dtype == np.uint8
            assert pixels.shape[2] == 4
            Image.fromarray(pixels).save(output_dir / "settings_view_lighting.Camera.LdrColor.spot.0001.png")


def test_update_from_usd_time_async(renderer, stage):
    """Asynchronously evaluate a time-sampled attribute at two distinct times."""
    _open(stage, LOGO_ANIMATED_PATH)
    renderer.reset()

    def _translate_x_at(time_seconds: float, ordinal: int) -> float:
        # [snippet:doc-update-from-usd-time-async]
        ovstage.population.update_from_usd_time_async(stage, ordinal=ordinal, time_code=time_seconds).wait()
        stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
        # [/snippet:doc-update-from-usd-time-async]

        renderer.step(render_products={"/Render/Camera"}, delta_time=1.0, ordinal=ordinal)
        with ovstage.PathDictionary(stage) as paths:
            path_list = paths.create_path_list_from_strings(["/World/logo"])
            with stage.query_from_path_list(path_list) as query:
                attribute = paths.intern_token("omni:xform")
                with stage.read_attributes(query, [attribute], ovstage.OrdinalRange.latest(ordinal)) as read:
                    group = read.fetch_next()
                    matrix = np.from_dlpack(group.dlpack(0)).copy().reshape(4, 4)
                    stage.release_group(group)
            paths.destroy_path_list(path_list)
        return float(matrix[3, 0])

    x_at_start = _translate_x_at(0.0, 2)
    x_at_end = _translate_x_at(1.0, 3)
    assert abs(x_at_end - x_at_start) > 1.0


@pytest.mark.allow_deprecated_ovrtx_api
def test_operation_status_while_loading(renderer):
    """Poll ``Operation.query_status()`` on a deprecated population operation."""
    renderer.reset_stage()

    # [snippet:doc-operation-status]
    op = renderer.add_usd_reference_async(TEST_BASE_PATH, "/LoadedBase")
    saw_counter = False
    while True:
        status = op.query_status()
        assert status.state in (ovrtx.EventStatus.PENDING, ovrtx.EventStatus.COMPLETED)
        assert isinstance(status.counters, list)
        for counter in status.counters:
            assert isinstance(counter, ovrtx.OperationCounter)
            saw_counter = True
        if status.state != ovrtx.EventStatus.PENDING:
            break
    op.wait()
    # [/snippet:doc-operation-status]

    if not saw_counter:
        print("note: USD reference load completed before any counter was observed")


def test_settings_rtpt_extraSpecularAndTransmissiveBounces(renderer, stage, output_dir):
    """Test omni:rtx:rtpt:extraSpecularAndTransmissiveBounces with glass material."""
    ovstage.population.open_usd_from_string(stage, RTPT_GLASS_USDA, ordinal=1)
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()

    images = {}
    with ovstage.PathDictionary(stage) as paths:
        render_paths = paths.create_path_list_from_strings(["/Render/Camera"])
        with stage.query_from_path_list(render_paths) as render_query:
            attribute = paths.intern_token("omni:rtx:rtpt:extraSpecularAndTransmissiveBounces")
            for ordinal, bounces in enumerate([0, 2, 23], start=2):
                stage.write_attribute(
                    render_query,
                    attribute,
                    ordinal=ordinal,
                    tensors=np.array([bounces], dtype=np.uint32),
                    is_array=False,
                ).wait()
                stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

                renderer.reset()
                for _ in range(40):
                    renderer.step(render_products={"/Render/Camera"}, delta_time=1.0 / 60, ordinal=ordinal)

                products = renderer.step(render_products={"/Render/Camera"}, delta_time=1.0 / 60, ordinal=ordinal)
                for product in products.values():
                    for frame in product.frames:
                        var = frame.render_vars[LDR_COLOR_PATH].map(device=ovrtx.Device.CPU)
                        pixels = np.from_dlpack(var)
                        assert pixels.dtype == np.uint8
                        assert pixels.shape[2] == 4
                        images[bounces] = pixels.copy()
                        Image.fromarray(pixels).save(
                            output_dir
                            / "settings_rtpt_extraSpecularAndTransmissiveBounces.Camera.LdrColor."
                            f"extraSpecularAndTransmissiveBounces-{bounces}.0001.png"
                        )
        paths.destroy_path_list(render_paths)

    difference = images[0].astype(np.float32) - images[2].astype(np.float32)
    rmse = np.sqrt(np.mean(difference * difference))
    # The glass scene measures about 17 RMSE; no-effect render noise stays below 1.
    assert rmse > 5.0, f"extra specular bounces had no visible effect: RMSE={rmse}"
