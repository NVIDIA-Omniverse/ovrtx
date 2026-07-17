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
def _map_render_var(frame, name: str) -> np.ndarray:
    mapped = frame.render_vars[name].map(device=ovrtx.Device.CPU)
    view = np.from_dlpack(mapped)
    result = view.copy()
    del view, mapped
    return result


def _decode_semantic_id_map(tensor: np.ndarray) -> dict[int, str]:
    data = np.ascontiguousarray(tensor).view(np.uint8).reshape(-1)
    if data.size < 4:
        return {}

    entry_dtype = np.dtype(
        [("id", "<u4", (4)), ("label_length", "<u4"), ("label_offset", "<u4")]
    )
    num_entries = int.from_bytes(data[-4:].tobytes(), byteorder="little")
    entries_size = num_entries * entry_dtype.itemsize
    assert entries_size <= data.size - 4

    entries = data[:entries_size].view(entry_dtype).reshape(num_entries)
    labels_by_id = {}
    for entry in entries:
        semantic_id = int(entry["id"][0])
        label_offset = int(entry["label_offset"])
        label_length = int(entry["label_length"])
        label_end = label_offset + label_length
        assert label_end <= data.size

        label = data[label_offset:label_end].tobytes().decode("utf-8")
        labels_by_id[semantic_id] = label.rstrip("\x00").rstrip()

    return labels_by_id


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
    semantic_ids_in_image = set(int(value) for value in np.unique(semantic_segmentation))

    assert logo_id in semantic_ids_in_image
    assert ground_id in semantic_ids_in_image
    assert np.count_nonzero(semantic_segmentation == logo_id) > 0
    assert np.count_nonzero(semantic_segmentation == ground_id) > 0
    # [/snippet:doc-interpret-semantic-segmentation-python]
