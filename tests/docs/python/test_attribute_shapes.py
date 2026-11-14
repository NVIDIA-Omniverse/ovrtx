# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Round-trip tests for ovstage DLPack tensor-layout conventions.

Multi-component attributes use DLTensor lanes. Their NumPy backing arrays and
DLPack consumers expose those components as trailing dimensions.
"""

from pathlib import Path

import numpy as np
import pytest

import ovrtx
import ovstage

TEST_BASE_PATH = str((Path(__file__).parent / "../data/ovrtx-test-base.usda").resolve())


def _load_base(stage):
    ovstage.population.open_usd(stage, TEST_BASE_PATH, ordinal=1)
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()


def test_scalar_int32_shape(stage):
    """Scalar uint32: ``shape=(N,)`` — one value per prim, one prim."""
    _load_base(stage)

    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/Render/Camera"])
        with stage.query_from_path_list(path_list) as query:
            attribute = paths.intern_token("omni:rtx:rtpt:maxBounces")

            # [snippet:doc-shape-scalar-int32]
            values_in = np.array([23], dtype=np.uint32)
            stage.write_attribute(query, attribute, ordinal=2, tensors=values_in, is_array=False).wait()
            stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
            with stage.read_attributes(query, [attribute], ovstage.OrdinalRange.latest(2)) as read:
                group = read.fetch_next()
                column = group.columns[0]
                values = np.from_dlpack(column.dlpack(0)).copy()
                stage.release_group(group)
            assert values.shape == (1,)
            # [/snippet:doc-shape-scalar-int32]

        paths.destroy_path_list(path_list)

    assert int(values[0]) == 23


def test_float3_array_shape(stage):
    """``float3[]`` array: ``shape=(M, 3)`` per prim — M elements, 3 components each."""
    _load_base(stage)

    # [snippet:doc-shape-float3-array]
    # point3f[] is a variable-length array of 3-component float vectors.
    # Store values in a 2-D ndarray, then expose M logical elements with three
    # lanes each to ovstage.
    points = np.array(
        [
            [-50.0, 0.0, -50.0],
            [50.0, 0.0, -50.0],
            [-50.0, 0.0, 50.0],
            [50.0, 0.0, 50.0],
        ],
        dtype=np.float32,
    )  # shape=(4, 3)
    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/World/Plane"])
        with stage.query_from_path_list(path_list) as query:
            attribute = paths.intern_token("points")
            point_dtype = ovstage.numpy_to_dldatatype(points.dtype, lanes=3)
            point_tensor = ovstage.make_dltensor(points, dtype=point_dtype, shape=[4], ndim=1)
            stage.write_attribute(query, attribute, ordinal=2, tensors=point_tensor, is_array=True).wait()
            stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
            with stage.read_attributes(query, [attribute], ovstage.OrdinalRange.latest(2)) as read:
                group = read.fetch_next()
                column = group.columns[0]
                values = np.from_dlpack(column.dlpack(0)).copy()
                stage.release_group(group)
            assert values.shape == (4, 3)
        paths.destroy_path_list(path_list)
    # [/snippet:doc-shape-float3-array]

    np.testing.assert_array_equal(values, points)


def test_mat4_array_shape(stage):
    """4x4 double matrix: ``shape=(N, 4, 4)`` — N prims, one 4x4 matrix each."""
    _load_base(stage)

    # [snippet:doc-shape-mat4-array]
    # Back a lane-16 per-prim transform with a 3-D ndarray of shape=(N, 4, 4).
    # Translate /World/Camera to (10, 20, 30) using USD row-vector convention
    # (translation lives in matrix[3][0..2]).
    xform = np.eye(4, dtype=np.float64)
    xform[3, 0:3] = [10.0, 20.0, 30.0]
    transforms = xform.reshape(1, 4, 4)  # shape=(1, 4, 4)
    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(["/World/Camera"])
        with stage.query_from_path_list(path_list) as query:
            attribute = paths.intern_token("omni:xform")
            matrix_dtype = ovstage.numpy_to_dldatatype(transforms.dtype, lanes=16)
            matrix_tensor = ovstage.make_dltensor(transforms, dtype=matrix_dtype, shape=[1], ndim=1)
            stage.write_attribute(
                query,
                attribute,
                ordinal=2,
                tensors=matrix_tensor,
                is_array=False,
                semantic=ovstage.AttributeSemantic.MATRIX,
            ).wait()
            stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
            with stage.read_attributes(query, [attribute], ovstage.OrdinalRange.latest(2)) as read:
                group = read.fetch_next()
                column = group.columns[0]
                values = np.from_dlpack(column.dlpack(0)).copy()
                stage.release_group(group)
            assert values.shape == (1, 4, 4)
        paths.destroy_path_list(path_list)
    # [/snippet:doc-shape-mat4-array]

    np.testing.assert_allclose(values[0, 3, 0:3], [10.0, 20.0, 30.0])


@pytest.mark.allow_deprecated_ovrtx_api
@pytest.mark.parametrize("persistent_binding", [False, True], ids=["direct", "binding"])
@pytest.mark.parametrize("matrix_size", [2, 3, 4], ids=["matrix2d", "matrix3d", "matrix4d"])
def test_numpy_matrix_column_and_array_shapes(renderer, persistent_binding, matrix_size):
    """Compatibility reads preserve NumPy matrix shape for fixed and array values."""
    renderer.open_usd(TEST_BASE_PATH)
    # [snippet:doc-matrix-compatibility-round-trip]
    matrices = np.arange(2 * matrix_size**2, dtype=np.float64).reshape(2, matrix_size, matrix_size)
    matrix_dtype = ovrtx.DLDataType.from_str("float64", lanes=matrix_size**2)
    # Keep automatic 4x4 inference covered alongside explicitly declared smaller matrices.
    direct_semantic = ovrtx.Semantic.NONE if matrix_size == 4 else ovrtx.Semantic.MATRIX
    prims = ["/World/Camera", "/World/Plane"]
    other_size = 3 if matrix_size == 2 else 2
    binding = None
    if persistent_binding:
        binding = renderer.bind_attribute(
            prims,
            "test:numpyMatrix4d",
            dtype=matrix_dtype if matrix_size != 4 else None,
            semantic=ovrtx.Semantic.MATRIX,
            prim_mode=ovrtx.PrimMode.CREATE_NEW,
        )
    try:
        if binding is not None:
            with pytest.raises(ValueError, match="components per matrix"):
                binding.write(np.zeros((len(prims), other_size, other_size), dtype=np.float64))
            with pytest.raises(ValueError, match="scalar type"):
                binding.write(matrices.astype(np.float32))
            binding.write(matrices)
        else:
            renderer.write_attribute(
                prims, "test:numpyMatrix4d", matrices, semantic=direct_semantic, prim_mode=ovrtx.PrimMode.CREATE_NEW
            )
        matrix_tensor = renderer.read_attribute("test:numpyMatrix4d", prims)
        values = np.from_dlpack(matrix_tensor).copy()
        assert values.shape == (2, matrix_size, matrix_size)
        np.testing.assert_array_equal(values, matrices)

        mapped_values = matrices + 0.5
        mapping = (
            binding.map()
            if binding is not None
            else renderer.map_attribute(prims, "test:numpyMatrix4d", dtype=matrix_dtype, semantic=ovrtx.Semantic.MATRIX)
        )
        with mapping:
            mapped = np.from_dlpack(mapping)
            assert mapped.shape == mapped_values.shape
            mapped[:] = mapped_values
        values = np.from_dlpack(renderer.read_attribute("test:numpyMatrix4d", prims)).copy()
        np.testing.assert_array_equal(values, mapped_values)
    finally:
        if binding is not None:
            binding.unbind()

    matrix_array = np.arange(3 * matrix_size**2, dtype=np.float64).reshape(3, matrix_size, matrix_size)
    renderer.write_array_attribute(
        [prims[0]],
        "test:numpyMatrixArray",
        [matrix_array],
        semantic=direct_semantic,
        prim_mode=ovrtx.PrimMode.CREATE_NEW,
    )
    array_tensors = renderer.read_array_attribute("test:numpyMatrixArray", [prims[0]])
    array_values = np.from_dlpack(array_tensors[prims[0]]).copy()
    assert array_values.shape == (3, matrix_size, matrix_size)
    np.testing.assert_array_equal(array_values, matrix_array)

    # Aggregate bytes alone cannot validate the size of each matrix in an array.
    wrong_size = np.zeros((matrix_size**2, other_size, other_size), dtype=np.float64)
    with pytest.raises(ValueError, match="All tensors must have the same element type"):
        renderer.write_array_attribute(
            prims,
            "test:mixedMatrixArrays",
            [matrix_array, wrong_size],
            semantic=ovrtx.Semantic.MATRIX,
            prim_mode=ovrtx.PrimMode.CREATE_NEW,
        )
    # [/snippet:doc-matrix-compatibility-round-trip]
