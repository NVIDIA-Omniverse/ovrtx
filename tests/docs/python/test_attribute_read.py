# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Tests for ovstage attribute reads used with an attached renderer.

Reads target schema-known attributes the runtime exposes to Fabric:
``omni:rtx:rtpt:maxBounces`` on the RenderProduct (a 32-bit integer; the
runtime may report it as either int32 or uint32) and ``points`` on
``/World/Plane`` (a float3 array authored in ``ovrtx-test-base-geometry.usda``).
"""

from pathlib import Path

import numpy as np
import ovrtx
import ovstage
import pytest

TEST_BASE_PATH = str((Path(__file__).parent / "../data/ovrtx-test-base.usda").resolve())


def _load_base(stage):
    ovstage.population.open_usd(stage, TEST_BASE_PATH, ordinal=1)
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()


def _load_base_legacy(renderer):
    renderer.open_usd(TEST_BASE_PATH)
    renderer.reset()


def test_read_scalar_attribute_cpu(stage):
    """Write a schema-known int32 scalar and read it back."""
    _load_base(stage)

    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/Render/Camera"])
        query = stage.query_from_path_list(path_list)
        attribute = paths.intern_token("omni:rtx:rtpt:maxBounces")
        stage.write_attribute(
            query, attribute, ordinal=2, tensors=np.array([17], dtype=np.uint32), is_array=False
        ).wait()
        stage.advance_write_floor(2, ovstage.Scope.ALL).wait()

        # [snippet:doc-read-attribute-scalar]
        read = stage.read_attributes(query, [attribute], ovstage.OrdinalRange.latest(2))
        read.wait()
        group = read.fetch_next()
        tensor = group.dlpack(0)
        values = np.from_dlpack(tensor).copy()
        stage.release_group(group)
        read.release().wait()
        # [/snippet:doc-read-attribute-scalar]

        query.release().wait()
        paths.destroy_path_list(path_list)

    assert isinstance(tensor, ovstage.ManagedDLTensor)
    # maxBounces is a 32-bit integer; the runtime may report it as int32 or
    # uint32 depending on the schema — compare the value, not the sign-ness.
    assert values.dtype.itemsize == 4 and values.dtype.kind in ("i", "u")
    assert values.shape == (1,)
    assert int(values[0]) == 17


@pytest.mark.filterwarnings("ignore:.* is deprecated in ovrtx 0\\.4\\..*:DeprecationWarning")
def test_read_scalar_attribute_into_dest(renderer):
    """Pass a pre-allocated tensor as ``dest``; verify data lands in it."""
    _load_base_legacy(renderer)

    renderer.write_attribute(
        prim_paths=["/Render/Camera"],
        attribute_name="omni:rtx:rtpt:maxBounces",
        tensor=np.array([11], dtype=np.int32),
    )

    # [snippet:doc-read-attribute-dest-tensor]
    # Pre-allocate the destination. The read writes directly into `dest`; the
    # returned tensor is a handle to the same memory — both aliases are valid.
    # The dtype must match how the runtime stores the attribute.
    dest = np.empty((1,), dtype=np.uint32)
    renderer.read_attribute(
        attribute_name="omni:rtx:rtpt:maxBounces",
        prim_paths=["/Render/Camera"],
        dest=dest,
    )
    # `dest` now holds the attribute value.
    # [/snippet:doc-read-attribute-dest-tensor]

    assert int(dest[0]) == 11


def test_read_array_attribute(stage):
    """Read ``points`` (``float3[]``) from the Plane mesh."""
    _load_base(stage)

    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/World/Plane"])
        query = stage.query_from_path_list(path_list)
        points = paths.intern_token("points")

        # [snippet:doc-read-array-attribute]
        with stage.read_attributes(query, [points], ovstage.OrdinalRange.latest(1)) as read:
            group = read.fetch_next()
            values = np.from_dlpack(group.dlpack(0)).copy()
            stage.release_group(group)
        # [/snippet:doc-read-array-attribute]

        query.release().wait()
        paths.destroy_path_list(path_list)

    # ovrtx-test-base-geometry.usda authors 4 float3 points on the Plane.
    assert values.dtype == np.float32
    assert values.size == 4 * 3


def test_read_attribute_async(stage):
    """Exercise the two-phase async lifecycle for an attribute read."""
    _load_base(stage)

    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/Render/Camera"])
        query = stage.query_from_path_list(path_list)
        attribute = paths.intern_token("omni:rtx:rtpt:maxBounces")
        stage.write_attribute(
            query, attribute, ordinal=2, tensors=np.array([5], dtype=np.uint32), is_array=False
        ).wait()
        stage.advance_write_floor(2, ovstage.Scope.ALL).wait()

        # [snippet:doc-read-attribute-async]
        read = stage.read_attributes(query, [attribute], ovstage.OrdinalRange.latest(2))
        read.wait()
        group = read.fetch_next()
        values = np.from_dlpack(group.dlpack(0)).copy()
        stage.release_group(group)
        read.release().wait()
        # [/snippet:doc-read-attribute-async]

        query.release().wait()
        paths.destroy_path_list(path_list)

    assert int(values[0]) == 5


@pytest.mark.filterwarnings("ignore:.* is deprecated in ovrtx 0\\.4\\..*:DeprecationWarning")
def test_read_attribute_cuda_dest(renderer):
    """Read directly into a GPU (CUDA) destination tensor via DLPack."""
    import warp as wp  # via warp-lang; provides DLPack-compatible CUDA arrays

    _load_base_legacy(renderer)

    renderer.write_attribute(
        prim_paths=["/Render/Camera"],
        attribute_name="omni:rtx:rtpt:maxBounces",
        tensor=np.array([9], dtype=np.int32),
    )

    # [snippet:doc-read-attribute-cuda-dest]
    # Allocate a CUDA destination through Warp (any DLPack-compatible CUDA
    # allocator works). The read writes directly into GPU memory; pass a CUDA
    # stream handle so the read is ordered on the caller's stream.
    dest = wp.empty(1, dtype=wp.uint32, device="cuda:0")
    stream = wp.Stream(device=dest.device)
    renderer.read_attribute(
        attribute_name="omni:rtx:rtpt:maxBounces",
        prim_paths=["/Render/Camera"],
        dest=dest,
        cuda_stream=stream.cuda_stream,
    )
    wp.synchronize_stream(stream)
    # [/snippet:doc-read-attribute-cuda-dest]

    # Copy back to host and verify the value.
    host = dest.numpy()
    assert int(host[0]) == 9
