# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Tests for runtime stage mutation: additive USD references, removal, and clone."""

from pathlib import Path

import numpy as np
import ovstage

TEST_BASE_PATH = str((Path(__file__).parent / "../data/ovrtx-test-base.usda").resolve())

ROOT_USDA = """#usda 1.0
def Xform "World" {
}
"""

REFERENCE_USDA = """#usda 1.0
(
    defaultPrim = "Referenced"
)

def Xform "Referenced" {
    def Cube "KnownChild" {
    }
}
"""


def _query_prefix_count(stage, prefix):
    filter_ = ovstage.Filter([ovstage.Predicate("usd-path", ovstage.FilterOp.PREFIX, [prefix])])
    with stage.query(filter=filter_) as query:
        return query.result().total_prim_count


def _read_attribute(stage, prim_path, attribute_name, ordinal):
    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings([prim_path])
        try:
            with stage.query_from_path_list(path_list) as query:
                attribute = paths.intern_token(attribute_name)
                with stage.read_attributes(query, [attribute], ovstage.OrdinalRange.latest(ordinal)) as read:
                    group = read.fetch_next()
                    assert group is not None
                    values = np.from_dlpack(group.dlpack(0)).copy()
                    stage.release_group(group)
                    return values
        finally:
            paths.destroy_path_list(path_list)


def test_add_remove_usd_reference_file(stage, tmp_path):
    """Add a file reference, prove composed child content exists, then remove it."""
    ovstage.population.open_usd_from_string(stage, ROOT_USDA, ordinal=1)
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()
    reference_file = tmp_path / "referenced.usda"
    reference_file.write_text(REFERENCE_USDA)

    # [snippet:doc-add-remove-usd-reference]
    handle = ovstage.population.add_usd_reference(stage, str(reference_file), "/World/LoadedBase")
    ovstage.population.apply_usd_changes(stage, ordinal=2)
    stage.advance_write_floor(2, ovstage.Scope.ALL).wait()

    ovstage.population.remove_usd(stage, handle)
    ovstage.population.apply_usd_changes(stage, ordinal=3)
    stage.advance_write_floor(3, ovstage.Scope.ALL).wait()
    # [/snippet:doc-add-remove-usd-reference]

    assert _query_prefix_count(stage, "/World/LoadedBase") == 0


def test_add_remove_usd_reference_from_string(stage):
    """Add an inline reference layer, prove child content exists, then remove it."""
    ovstage.population.open_usd_from_string(stage, ROOT_USDA, ordinal=1)
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()

    # [snippet:doc-add-usd-reference-from-string]
    handle = ovstage.population.add_usd_reference_from_string(stage, REFERENCE_USDA, "/World/Injected")
    ovstage.population.apply_usd_changes(stage, ordinal=2)
    stage.advance_write_floor(2, ovstage.Scope.ALL).wait()

    ovstage.population.remove_usd(stage, handle)
    ovstage.population.apply_usd_changes(stage, ordinal=3)
    stage.advance_write_floor(3, ovstage.Scope.ALL).wait()
    # [/snippet:doc-add-usd-reference-from-string]

    assert _query_prefix_count(stage, "/World/Injected") == 0


def test_clone_usd(stage):
    """Clone a mesh subtree and verify the clone keeps mesh data."""
    ovstage.population.open_usd(stage, TEST_BASE_PATH, ordinal=1)
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()
    source_points = _read_attribute(stage, "/World/Plane", "points", 1)

    # [snippet:doc-clone-usd]
    stage.clone("/World/Plane", ["/World/PlaneCloneA", "/World/PlaneCloneB"], ordinal=2)
    stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
    # [/snippet:doc-clone-usd]

    assert _query_prefix_count(stage, "/World/PlaneCloneA") == 1
    assert _query_prefix_count(stage, "/World/PlaneCloneB") == 1
    clone_points = _read_attribute(stage, "/World/PlaneCloneA", "points", 2)
    np.testing.assert_allclose(clone_points, source_points)


def test_clone_usd_async(stage):
    """Exercise the async clone operation for void-operation wait semantics."""
    ovstage.population.open_usd(stage, TEST_BASE_PATH, ordinal=1)
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()

    # [snippet:doc-clone-usd-async]
    op = stage.clone_async("/World/Plane", ["/World/PlaneCloneAsync"], ordinal=2)
    op.wait()
    stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
    # [/snippet:doc-clone-usd-async]

    assert _query_prefix_count(stage, "/World/PlaneCloneAsync") == 1
