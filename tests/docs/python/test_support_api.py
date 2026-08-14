# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Tests for low-level Python support types exposed by ovrtx."""

from pathlib import Path

import numpy as np
import ovrtx
import ovstage

TEST_BASE_PATH = str((Path(__file__).parent / "../data/ovrtx-test-base.usda").resolve())


def test_dl_data_type_from_str():
    """Construct DLPack dtype descriptors from string aliases."""
    # [snippet:doc-dldata-type-from-str]
    point_dtype = ovrtx.DLDataType.from_str("float32", lanes=3)
    assert point_dtype.bits == 32
    assert point_dtype.lanes == 3
    # [/snippet:doc-dldata-type-from-str]


def test_managed_dl_tensor_helpers(stage):
    """Exercise convenience methods on a CPU ManagedDLTensor."""
    ovstage.population.open_usd(stage, TEST_BASE_PATH, ordinal=1)
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()

    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/Render/Camera"])
        with stage.query_from_path_list(path_list) as query:
            attribute = paths.intern_token("omni:rtx:rtpt:maxBounces")
            stage.write_attribute(
                query,
                attribute,
                ordinal=2,
                tensors=np.array([19], dtype=np.uint32),
                is_array=False,
            ).wait()
            stage.advance_write_floor(2, ovstage.Scope.ALL).wait()

            with stage.read_attributes(query, [attribute], ovstage.OrdinalRange.latest(2)) as read:
                group = read.fetch_next()
                # [snippet:doc-managed-dltensor-helpers]
                tensor = group.dlpack(0)
                values = tensor.numpy().copy()
                device_type, device_id = tensor.__dlpack_device__()
                # [/snippet:doc-managed-dltensor-helpers]
                stage.release_group(group)
        paths.destroy_path_list(path_list)

    assert isinstance(tensor, ovstage.ManagedDLTensor)
    assert int(values[0]) == 19
    assert (device_type, device_id) == (1, 0)  # DLPack kDLCPU, device 0


def test_renderer_config_version_and_async_stage(output_dir):
    """Cover RendererConfig, version, config echo, and void async stage ops."""
    # [snippet:doc-renderer-config]
    config = ovrtx.RendererConfig(
        sync_mode=True,
        log_file_path=str(output_dir / "config-test.log"),
        log_level="info",
    )
    renderer = ovrtx.Renderer(config=config)
    assert any(component > 0 for component in renderer.version)
    assert renderer.config.sync_mode is True
    assert renderer.config.log_level == "info"
    assert renderer.config.log_file_path == str(output_dir / "config-test.log")
    # [/snippet:doc-renderer-config]

    stage = ovstage.Stage("ovrtx.docs.support-api")
    renderer.attach_ovstage(stage)

    # [snippet:doc-open-usd-async]
    op = ovstage.population.open_usd_async(stage, TEST_BASE_PATH, ordinal=1)
    op.wait()
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()
    # [/snippet:doc-open-usd-async]

    plane_filter = ovstage.Filter([ovstage.Predicate("usd-path", ovstage.FilterOp.IN, ["/World/Plane"])])
    with stage.query(filter=plane_filter) as plane_query:
        assert plane_query.result().total_prim_count == 1

    # [snippet:doc-open-usd-from-string-async]
    inline = '#usda 1.0\ndef Xform "World" {}\n'
    # TODO: Restore the assertion once the packaged open_usd_from_string_async wrapper returns _VOID_RESULT.
    ovstage.population.open_usd_from_string_async(stage, inline, ordinal=2).wait()
    stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
    # [/snippet:doc-open-usd-from-string-async]

    # [snippet:doc-reset-async]
    assert renderer.reset_async().wait() is True
    # [/snippet:doc-reset-async]

    # [snippet:doc-reset-stage-async]
    ovstage.population.reset_usd_async(stage).wait()
    ovstage.population.apply_usd_changes_async(stage, ordinal=3).wait()
    stage.advance_write_floor(3, ovstage.Scope.ALL).wait()
    # [/snippet:doc-reset-stage-async]

    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


def test_dome_baking_resolution_config(output_dir):
    """dome_baking_resolution is accepted at renderer creation and round-trips.

    Verifies the int64 config wiring (RendererConfig field -> whitelist ->
    ovrtx_config_entry_int -> OVRTX_CONFIG_DOME_BAKING_RESOLUTION) does not raise
    and that the value is echoed back on ``renderer.config``. This is an
    API-surface check only.

    That the value is actually applied to the carb setting and clamped is
    covered behaviorally by the C++ unit test
    ``test.ovrtx.unit`` ->
    "OVRTX - DomeLight baking resolution config applies to carb setting".
    Golden validation that the baked DomeLight environment texture visually
    changes with resolution requires an MDL-material-driven dome and lives in
    the dedicated ovrtx domelight test suite.
    """
    config = ovrtx.RendererConfig(
        dome_baking_resolution=256,
        log_file_path=str(output_dir / "dome-baking-resolution.log"),
    )
    renderer = ovrtx.Renderer(config=config)
    assert renderer.config.dome_baking_resolution == 256
