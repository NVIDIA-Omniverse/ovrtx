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
                values = np.from_dlpack(group.dlpack(0)).copy()
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
                values = np.from_dlpack(group.dlpack(0)).copy()
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
                values = np.from_dlpack(group.dlpack(0)).copy().reshape(1, 4, 4)
                stage.release_group(group)
            assert values.shape == (1, 4, 4)
        paths.destroy_path_list(path_list)
    # [/snippet:doc-shape-mat4-array]

    np.testing.assert_allclose(values[0, 3, 0:3], [10.0, 20.0, 30.0])
