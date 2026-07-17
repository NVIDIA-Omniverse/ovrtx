# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Tests for persistent attribute bindings, mapping, and CUDA write paths."""

from pathlib import Path

import numpy as np
import ovrtx
import ovstage
import pytest
import warp as wp

TEST_BASE_PATH = str((Path(__file__).parent / "../data/ovrtx-test-base.usda").resolve())


@wp.kernel
def _set_xform_translation_x(transforms: wp.array(dtype=wp.mat44d), x: wp.float64):
    transforms[wp.tid()] = wp.mat44d(
        wp.float64(1.0),
        wp.float64(0.0),
        wp.float64(0.0),
        wp.float64(0.0),
        wp.float64(0.0),
        wp.float64(1.0),
        wp.float64(0.0),
        wp.float64(0.0),
        wp.float64(0.0),
        wp.float64(0.0),
        wp.float64(1.0),
        wp.float64(0.0),
        x,
        wp.float64(0.0),
        wp.float64(0.0),
        wp.float64(1.0),
    )


def _load_base(stage):
    ovstage.population.open_usd(stage, TEST_BASE_PATH, ordinal=1)
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()


def _load_base_legacy(renderer):
    renderer.open_usd(TEST_BASE_PATH)
    renderer.reset()


def _read_xform(stage, paths, query, ordinal):
    attribute = paths.intern_token("omni:xform")
    with stage.read_attributes(query, [attribute], ovstage.OrdinalRange.latest(ordinal)) as read:
        group = read.fetch_next()
        values = np.from_dlpack(group.dlpack(0)).copy().reshape(1, 4, 4)
        stage.release_group(group)
    return values


def _read_xform_legacy(renderer, prim="/World/Plane"):
    tensor = renderer.read_attribute("omni:xform", [prim])
    return np.from_dlpack(tensor).reshape(1, 4, 4)


def _make_xform(x):
    matrix = np.eye(4, dtype=np.float64).reshape(1, 4, 4)
    matrix[0, 3, 0] = x
    return matrix


def test_bind_attribute_write_unbind(stage):
    """Create a scalar binding, write through it, and read back the result."""
    _load_base(stage)
    matrix = _make_xform(12.0)

    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/World/Plane"])

        # [snippet:doc-bind-attribute-write]
        query = stage.query_from_path_list(path_list)
        attribute = paths.intern_token("omni:xform")
        matrix_dtype = ovstage.numpy_to_dldatatype(matrix.dtype, lanes=16)
        matrix_tensor = ovstage.make_dltensor(matrix, dtype=matrix_dtype, shape=[1], ndim=1)
        stage.write_attribute(query, attribute, ordinal=2, tensors=matrix_tensor, is_array=False).wait()
        stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
        # [/snippet:doc-bind-attribute-write]

        np.testing.assert_allclose(_read_xform(stage, paths, query, 2), matrix)
        query.release().wait()
        paths.destroy_path_list(path_list)


def test_bind_attribute_async_and_write_async(stage):
    """Create and write a binding asynchronously."""
    _load_base(stage)
    matrix = _make_xform(13.0)

    with ovstage.PathDictionary(stage) as paths:
        # [snippet:doc-bind-attribute-async]
        plane_filter = ovstage.Filter([ovstage.Predicate("usd-path", ovstage.FilterOp.IN, ["/World/Plane"])])
        query = stage.query(filter=plane_filter)
        query.wait()
        # [/snippet:doc-bind-attribute-async]

        # [snippet:doc-binding-write-async]
        attribute = paths.intern_token("omni:xform")
        matrix_dtype = ovstage.numpy_to_dldatatype(matrix.dtype, lanes=16)
        matrix_tensor = ovstage.make_dltensor(matrix, dtype=matrix_dtype, shape=[1], ndim=1)
        write_op = stage.write_attribute(query, attribute, ordinal=2, tensors=matrix_tensor, is_array=False)
        write_op.wait()
        stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
        # [/snippet:doc-binding-write-async]

        np.testing.assert_allclose(_read_xform(stage, paths, query, 2), matrix)
        query.release().wait()


def test_bind_array_attribute(stage):
    """Bind a variable-length array attribute, write through it, and read it back."""
    _load_base(stage)
    points = np.array(
        [
            [-1.0, 0.0, -1.0],
            [1.0, 0.0, -1.0],
            [-1.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )

    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/World/Plane"])
        query = stage.query_from_path_list(path_list)

        # [snippet:doc-bind-array-attribute]
        attribute = paths.intern_token("points")
        point_dtype = ovstage.numpy_to_dldatatype(points.dtype, lanes=3)
        point_tensor = ovstage.make_dltensor(points, dtype=point_dtype, shape=[4], ndim=1)
        stage.write_attribute(query, attribute, ordinal=2, tensors=point_tensor, is_array=True).wait()
        stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
        # [/snippet:doc-bind-array-attribute]

        with stage.read_attributes(query, [attribute], ovstage.OrdinalRange.latest(2)) as read:
            group = read.fetch_next()
            values = np.from_dlpack(group.dlpack(0)).copy()
            stage.release_group(group)
        np.testing.assert_allclose(values, points)
        query.release().wait()
        paths.destroy_path_list(path_list)


def test_map_attribute_cpu(stage):
    """Map an attribute by name on CPU and verify the mutation."""
    _load_base(stage)

    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/World/Plane"])
        query = stage.query_from_path_list(path_list)
        attribute = paths.intern_token("omni:xform")

        # [snippet:doc-map-attribute-cpu]
        with stage.map_attribute(query, attribute, ordinal=2) as mapping:
            mapping.wait()
            group = mapping.fetch_next()
            matrices = np.from_dlpack(group.dlpack(0)).reshape(1, 4, 4)
            matrices[0, 3, 0] = 10.0
        stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
        # [/snippet:doc-map-attribute-cpu]

        assert _read_xform(stage, paths, query, 2)[0, 3, 0] == 10.0
        query.release().wait()
        paths.destroy_path_list(path_list)


def test_map_bound_attribute_cpu(stage):
    """Map through an AttributeBinding rather than by name."""
    _load_base(stage)

    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/World/Plane"])

        # [snippet:doc-map-bound-attribute]
        query = stage.query_from_path_list(path_list)
        attribute = paths.intern_token("omni:xform")
        with stage.map_attribute(query, attribute, ordinal=2) as mapping:
            mapping.wait()
            group = mapping.fetch_next()
            matrices = np.from_dlpack(group.dlpack(0)).reshape(1, 4, 4)
            matrices[0, 3, 0] = 8.0
        stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
        # [/snippet:doc-map-bound-attribute]

        assert _read_xform(stage, paths, query, 2)[0, 3, 0] == 8.0
        query.release().wait()
        paths.destroy_path_list(path_list)


def test_unmap_attribute_async(stage):
    """Unmap explicitly through the async API."""
    _load_base(stage)

    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/World/Plane"])
        query = stage.query_from_path_list(path_list)
        attribute = paths.intern_token("omni:xform")

        # [snippet:doc-unmap-attribute-async]
        mapping = stage.map_attribute(query, attribute, ordinal=2)
        mapping.wait()
        group = mapping.fetch_next()
        matrices = np.from_dlpack(group.dlpack(0)).reshape(1, 4, 4)
        matrices[0, 3, 0] = 9.0
        op = mapping.unmap()
        op.wait()
        stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
        # [/snippet:doc-unmap-attribute-async]

        assert _read_xform(stage, paths, query, 2)[0, 3, 0] == 9.0
        query.release().wait()
        paths.destroy_path_list(path_list)


@pytest.mark.filterwarnings("ignore:.* is deprecated in ovrtx 0\\.4\\..*:DeprecationWarning")
def test_map_attribute_cuda(renderer):
    """Map an attribute on CUDA, edit it with Warp, and read back on CPU."""
    _load_base_legacy(renderer)

    # [snippet:doc-map-attribute-cuda]
    mapping = renderer.map_attribute(
        ["/World/Plane"],
        "omni:xform",
        dtype="float64",
        shape=(4, 4),
        device=ovrtx.Device.CUDA,
    )
    tensor = wp.from_dlpack(mapping.tensor, dtype=wp.mat44d)
    stream = wp.Stream(device=tensor.device)
    wp.launch(_set_xform_translation_x, dim=1, inputs=[tensor, wp.float64(6.0)], stream=stream)
    mapping.unmap(stream=stream.cuda_stream)
    # [/snippet:doc-map-attribute-cuda]

    assert _read_xform_legacy(renderer)[0, 3, 0] == 6.0


@pytest.mark.filterwarnings("ignore:.* is deprecated in ovrtx 0\\.4\\..*:DeprecationWarning")
def test_write_attribute_async_data_access_cuda(renderer):
    """Write a CUDA tensor with asynchronous data access and stream sync."""
    _load_base_legacy(renderer)
    cuda_tensor = wp.empty(1, dtype=wp.mat44d, device="cuda:0")
    stream = wp.Stream(device=cuda_tensor.device)
    wp.launch(_set_xform_translation_x, dim=1, inputs=[cuda_tensor, wp.float64(7.0)], stream=stream)

    # [snippet:doc-write-attribute-async-data-access]
    op = renderer.write_attribute_async(
        ["/World/Plane"],
        "omni:xform",
        cuda_tensor,
        data_access=ovrtx.DataAccess.ASYNC,
        cuda_stream=stream.cuda_stream,
    )
    assert op.wait() is True
    # [/snippet:doc-write-attribute-async-data-access]

    assert _read_xform_legacy(renderer)[0, 3, 0] == 7.0


def test_write_token_array_attribute(stage):
    """Write string data as a token array rather than a path relationship."""
    _load_base(stage)

    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/World/Plane"])
        query = stage.query_from_path_list(path_list)

        # [snippet:doc-write-token-array]
        attribute = paths.intern_token("omni:docTokens")
        token_ids = np.array([paths.intern_token("sensor"), paths.intern_token("validated")], dtype=np.uint64)
        stage.write_attribute(
            query,
            attribute,
            ordinal=2,
            tensors=token_ids,
            is_array=True,
            semantic=ovstage.AttributeSemantic.TOKEN_ID,
        ).wait()
        stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
        # [/snippet:doc-write-token-array]

        with stage.read_attributes(query, [attribute], ovstage.OrdinalRange.latest(2)) as read:
            group = read.fetch_next()
            assert group.is_array
            assert group.tensor(0).dtype.lanes == 1
            assert group.attribute == attribute
            stage.release_group(group)
        query.release().wait()
        paths.destroy_path_list(path_list)
