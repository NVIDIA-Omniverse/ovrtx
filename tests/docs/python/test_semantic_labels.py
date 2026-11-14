# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Tests for semantic label authoring and semantic segmentation outputs."""

from pathlib import Path

import numpy as np
import ovrtx
import ovstage
import pytest

TEST_BASE_PATH = str((Path(__file__).parent / "../data/ovrtx-test-base.usda").resolve())
SEMANTIC_LABELS_PATH = str(
    (Path(__file__).parent / "../data/ovrtx-test-base-semantic-labels.usda").resolve()
)
RESOLUTION = (1280, 720)
RENDER_PRODUCT_PATH = "/Render/SemanticCamera"


# [snippet:doc-semantic-class-overrides-python]
SEMANTIC_CLASS_USDA = f"""#usda 1.0
(
    subLayers = [
        @{SEMANTIC_LABELS_PATH}@,
        @{TEST_BASE_PATH}@
    ]
)

def "Render"
{{
    def RenderProduct "SemanticCamera"
    {{
        int2 resolution = {RESOLUTION}
        rel camera = </World/Camera>
        rel orderedVars = [<SemanticSegmentation>, <SemanticIdMap>]

        def RenderVar "SemanticSegmentation"
        {{
            string sourceName = "SemanticSegmentation"
        }}

        def RenderVar "SemanticIdMap"
        {{
            string sourceName = "SemanticIdMap"
        }}
    }}
}}
"""
# [/snippet:doc-semantic-class-overrides-python]


# [snippet:doc-interpret-semantic-segmentation-python]
def _map_render_var(frame, name: str) -> np.ndarray | dict[str, np.ndarray]:
    with frame.render_vars[f"/Render/SemanticCamera/{name}"].map(device=ovrtx.Device.CPU) as mapped:
        if name != "SemanticIdMap":
            return np.from_dlpack(mapped).copy()
        return {key: np.from_dlpack(mapped[key]).copy() for key in mapped}


def _decode_semantic_id_map(fields: dict[str, np.ndarray]) -> dict[tuple[int, ...], str]:
    ids, offsets, data = fields["id"], fields["label_offsets"], fields["label_data"]
    if (ids.dtype != np.uint32 or ids.shape != (len(ids), 4)
            or offsets.dtype != np.uint64 or offsets.shape != (len(ids) + 1,)
            or data.dtype != np.uint8 or data.ndim != 1 or offsets[0] != 0
            or offsets[-1] != len(data) or np.any(offsets[1:] < offsets[:-1])):
        raise ValueError("Invalid semantic identifier fields or label spans")
    return {tuple(int(word) for word in identifier): data[int(start):int(end)].tobytes().decode("utf-8").rstrip()
            for identifier, start, end in zip(ids, offsets[:-1], offsets[1:])}


def test_semantic_class_labels_are_rendered(renderer, stage):
    """Set semantic class labels and verify their rendered semantic IDs."""
    ordinal = 1
    ovstage.population.open_usd_from_string(stage, SEMANTIC_CLASS_USDA, ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    for _ in range(5):
        renderer.step(render_products={RENDER_PRODUCT_PATH}, delta_time=1.0 / 60.0, ordinal=ordinal)

    products = renderer.step(render_products={RENDER_PRODUCT_PATH}, delta_time=1.0 / 60.0, ordinal=ordinal)
    frame = products[RENDER_PRODUCT_PATH].frames[0]

    semantic_id_map = _decode_semantic_id_map(_map_render_var(frame, "SemanticIdMap"))
    ids_by_label = {label: semantic_id for semantic_id, label in semantic_id_map.items()}

    logo_id = ids_by_label["class: logo;"]
    ground_id = ids_by_label["class: ground;"]

    semantic_segmentation = np.squeeze(_map_render_var(frame, "SemanticSegmentation"))
    # Scalar class pixels occupy the first word; preserve all four words when joining the map.
    semantic_ids_in_image = {(int(value), 0, 0, 0) for value in np.unique(semantic_segmentation)}

    assert logo_id in semantic_ids_in_image
    assert ground_id in semantic_ids_in_image
    assert np.count_nonzero(semantic_segmentation == logo_id[0]) > 0
    assert np.count_nonzero(semantic_segmentation == ground_id[0]) > 0
    # [/snippet:doc-interpret-semantic-segmentation-python]


def test_named_semantic_id_map_fields():
    """Read strided IDs, UTF-8 spans and empty maps without interpreting private bytes."""
    ids = np.array([[99, 7, 0, 0, 0, 99], [99, 9, 0, 0, 0, 99]], dtype=np.uint32)[:, 1:5]
    labels = "class: logo; class: café; ".encode("utf-8")
    fields = {"id": ids, "label_offsets": np.array([0, 13, len(labels)], dtype=np.uint64),
              "label_data": np.frombuffer(labels, dtype=np.uint8)}
    assert _decode_semantic_id_map(fields) == {(7, 0, 0, 0): "class: logo;", (9, 0, 0, 0): "class: café;"}
    with pytest.raises(ValueError, match="spans"):
        _decode_semantic_id_map({**fields, "label_offsets": np.array([0, 13, 1000], dtype=np.uint64)})
    non_scalar = ids.copy()
    non_scalar[1] = [7, 2, 3, 4]
    assert _decode_semantic_id_map({**fields, "id": non_scalar}) == {
        (7, 0, 0, 0): "class: logo;", (7, 2, 3, 4): "class: café;"}
    assert _decode_semantic_id_map({"id": np.empty((0, 4), dtype=np.uint32),
                                   "label_offsets": np.array([0], dtype=np.uint64),
                                   "label_data": np.empty(0, dtype=np.uint8)}) == {}
