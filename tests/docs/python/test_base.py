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
            var = frame.render_vars["LdrColor"].map(device=ovrtx.Device.CPU)
            pixels = np.from_dlpack(var)
            assert pixels.dtype == np.uint8
            assert pixels.shape[2] == 4
            Image.fromarray(pixels).save(output_dir / "base.Camera.LdrColor.0001.png")


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
            var = frame.render_vars["LdrColor"].map(device=ovrtx.Device.CPU)
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
                        var = frame.render_vars["LdrColor"].map(device=ovrtx.Device.CPU)
                        pixels = np.from_dlpack(var)
                        assert pixels.dtype == np.uint8
                        assert pixels.shape[2] == 4
                        Image.fromarray(pixels).save(
                            output_dir
                            / f"settings_rtpt_maxBounces.Camera.LdrColor.maxBounces-{max_bounces}.0001.png"
                        )
        paths.destroy_path_list(path_list)


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


@pytest.mark.filterwarnings("ignore:.* is deprecated in ovrtx 0\\.4\\..*:DeprecationWarning")
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


def test_settings_rtpt_maxSpecularAndTransmissionBounces(renderer, stage, output_dir):
    """Test omni:rtx:rtpt:maxSpecularAndTransmissionBounces with glass material."""
    _open(stage, TEST_BASE_PATH)

    with ovstage.PathDictionary(stage) as paths:
        logo_paths = paths.create_path_list_from_strings(["/World/logo/logo/logo"])
        render_paths = paths.create_path_list_from_strings(["/Render/Camera"])
        with stage.query_from_path_list(logo_paths) as logo_query:
            material_binding = paths.intern_token("material:binding")
            material_path = np.array([paths.intern_path("/World/Looks/srf_glass")], dtype=np.uint64)
            stage.write_attribute(
                logo_query,
                material_binding,
                ordinal=2,
                tensors=material_path,
                is_array=True,
                semantic=ovstage.AttributeSemantic.RELATIONSHIP_PATH_ID,
            ).wait()
        stage.advance_write_floor(2, ovstage.Scope.ALL).wait()

        with stage.query_from_path_list(render_paths) as render_query:
            attribute = paths.intern_token("omni:rtx:rtpt:maxSpecularAndTransmissionBounces")
            for ordinal, bounces in enumerate([2, 3, 23], start=3):
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
                        var = frame.render_vars["LdrColor"].map(device=ovrtx.Device.CPU)
                        pixels = np.from_dlpack(var)
                        assert pixels.dtype == np.uint8
                        assert pixels.shape[2] == 4
                        Image.fromarray(pixels).save(
                            output_dir
                            / "settings_rtpt_maxSpecularAndTransmissionBounces.Camera.LdrColor."
                            f"maxSpecularAndTransmissionBounces-{bounces}.0001.png"
                        )
        paths.destroy_path_list(render_paths)
        paths.destroy_path_list(logo_paths)
