# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Tests for the ovstage query API used with an attached renderer."""

from pathlib import Path

import ovrtx
import ovstage
import pytest

TEST_BASE_PATH = str((Path(__file__).parent / "../data/ovrtx-test-base.usda").resolve())
INLINE_SUBLAYERS_PATH = str(
    (Path(__file__).parent / "../usd/data/inline_sublayers_camera_renderproduct.usda").resolve()
)


def _load_base(stage):
    ovstage.population.open_usd(stage, TEST_BASE_PATH, ordinal=1)
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()


def test_query_all_prims_no_attrs(stage):
    """Query every prim on the stage without attribute descriptors."""
    _load_base(stage)

    # [snippet:doc-query-prims-basic]
    query = stage.query()
    query.wait()
    result = query.result()
    print(f"matched {result.total_prim_count} prims")
    query.release().wait()
    # [/snippet:doc-query-prims-basic]

    assert result.total_prim_count > 0


def test_query_by_prim_type(stage):
    """Filter prims by populated USD type."""
    _load_base(stage)

    # [snippet:doc-query-prims-by-type]
    mesh_filter = ovstage.Filter([ovstage.Predicate("usd-prim-type", ovstage.FilterOp.IN, ["Mesh"])])
    with stage.query(filter=mesh_filter) as meshes:
        mesh_count = meshes.result().total_prim_count
    # [/snippet:doc-query-prims-by-type]

    assert mesh_count > 0
    camera_filter = ovstage.Filter([ovstage.Predicate("usd-prim-type", ovstage.FilterOp.IN, ["Camera"])])
    with stage.query(filter=camera_filter) as cameras:
        assert cameras.result().total_prim_count == 1


def test_query_with_attribute_filter(stage):
    """Request selected attribute columns from matching prims."""
    _load_base(stage)

    # [snippet:doc-query-prims-with-attributes]
    with ovstage.PathDictionary(stage) as paths:
        points = paths.intern_token("points")
        material_binding = paths.intern_token("material:binding")
        mesh_filter = ovstage.Filter([ovstage.Predicate("usd-prim-type", ovstage.FilterOp.IN, ["Mesh"])])
        with stage.query(filter=mesh_filter, attrs=[points, material_binding]) as meshes:
            result = meshes.result()
    # [/snippet:doc-query-prims-with-attributes]

    assert result.total_prim_count > 0
    assert points in result.attributes
    assert material_binding in result.attributes


def test_query_prims_async(stage):
    """Exercise the asynchronous query operation and result fetch."""
    _load_base(stage)

    # [snippet:doc-query-prims-async]
    mesh_filter = ovstage.Filter([ovstage.Predicate("usd-prim-type", ovstage.FilterOp.IN, ["Mesh"])])
    meshes = stage.query(filter=mesh_filter)
    meshes.wait()
    result = meshes.result()
    meshes.release().wait()
    # [/snippet:doc-query-prims-async]

    assert result.total_prim_count > 0


@pytest.mark.filterwarnings("ignore:.* is deprecated in ovrtx 0\\.4\\..*:DeprecationWarning")
def test_query_require_any_exclude_all_attrs(renderer):
    """Exercise OR, NOT, and ALL-attributes query options together."""
    renderer.open_usd(TEST_BASE_PATH)
    renderer.reset()

    # [snippet:doc-query-require-any-exclude]
    # Match Mesh or Camera prims, then exclude Camera. The exclusion removes
    # a prim that would otherwise match the OR clause.
    prims = renderer.query_prims(
        require_any=[
            (ovrtx.FilterKind.PRIM_TYPE, "Mesh"),
            (ovrtx.FilterKind.PRIM_TYPE, "Camera"),
        ],
        exclude=[(ovrtx.FilterKind.PRIM_TYPE, "Camera")],
        attribute_filter_mode=ovrtx.AttributeFilterMode.ALL,
    )
    # [/snippet:doc-query-require-any-exclude]

    assert "/World/Plane" in prims
    assert "/World/Camera" not in prims
    assert prims["/World/Plane"]


@pytest.mark.filterwarnings("ignore:.* is deprecated in ovrtx 0\\.4\\..*:DeprecationWarning")
def test_query_specific_empty_attribute_list(renderer):
    """SPECIFIC with no requested names returns matched prims with no descriptors."""
    renderer.open_usd(TEST_BASE_PATH)
    renderer.reset()

    # [snippet:doc-query-specific-empty-attributes]
    result = renderer.query_prims(
        require_all=[(ovrtx.FilterKind.PRIM_TYPE, "Mesh")],
        attribute_filter_mode=ovrtx.AttributeFilterMode.SPECIFIC,
        attribute_names=[],
    )
    assert all(attrs == {} for attrs in result.values())
    # [/snippet:doc-query-specific-empty-attributes]

    assert "/World/Plane" in result


def test_query_inline_sublayer_composition(stage):
    """Query prims from both the inline root layer and its composed sublayer."""
    ovstage.population.open_usd(stage, INLINE_SUBLAYERS_PATH, ordinal=1)
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()

    # [snippet:doc-query-inline-sublayer-composition]
    expected_paths = ["/World/Plane", "/World/Camera", "/DocsCamera", "/Render/DocsCamera"]
    expected_filter = ovstage.Filter([ovstage.Predicate("usd-path", ovstage.FilterOp.IN, expected_paths)])
    with stage.query(filter=expected_filter) as query:
        assert query.result().total_prim_count == len(expected_paths)
    # [/snippet:doc-query-inline-sublayer-composition]
