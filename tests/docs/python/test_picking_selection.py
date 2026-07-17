# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Tests for viewport picking and selection outline drawing."""

from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image
import pytest

TEST_PICKING_PATH = str(
    (Path(__file__).parent / "../data/ovrtx-test-picking-selection.usda").resolve()
)

DEFAULT_SELECTION_STYLE = ovrtx.SelectionGroupStyle(
    outline_color=(1.0, 0.6, 0.0, 1.0),
    fill_color=(0.0, 0.0, 0.0, 0.0),
)
RENDER_WIDTH = 640
RENDER_HEIGHT = 320
CENTER_X = RENDER_WIDTH // 2
CENTER_Y = RENDER_HEIGHT // 2
MARQUEE_RIGHT = RENDER_WIDTH * 150 // 256
CENTER_LEFT_NDC = CENTER_X / RENDER_WIDTH
CENTER_TOP_NDC = CENTER_Y / RENDER_HEIGHT
CENTER_RIGHT_NDC = (CENTER_X + 1) / RENDER_WIDTH
CENTER_BOTTOM_NDC = (CENTER_Y + 1) / RENDER_HEIGHT
MARQUEE_RIGHT_NDC = MARQUEE_RIGHT / RENDER_WIDTH


@pytest.fixture()
def picking_renderer(output_dir):
    # [snippet:doc-create-selection-outline-renderer-python]
    log_file_path = str(output_dir / "picking_selection.ovrtx.log")

    config = ovrtx.RendererConfig(
        selection_outline_enabled=True,
        log_file_path=log_file_path,
    )
    renderer = ovrtx.Renderer(config=config)
    stage = ovstage.Stage("ovrtx.docs.picking")
    renderer.attach_ovstage(stage)
    # [/snippet:doc-create-selection-outline-renderer-python]
    yield renderer, stage
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


@pytest.fixture()
def styled_selection_renderer(output_dir):
    # [snippet:doc-create-styled-selection-renderer-python]
    log_file_path = str(output_dir / "picking_selection_styled.ovrtx.log")

    config = ovrtx.RendererConfig(
        selection_outline_enabled=True,
        selection_outline_width=8,
        selection_fill_mode=ovrtx.SelectionFillMode.GROUP_FILL_COLOR,
        log_file_path=log_file_path,
    )
    renderer = ovrtx.Renderer(config=config)
    stage = ovstage.Stage("ovrtx.docs.picking-styled")
    renderer.attach_ovstage(stage)
    # [/snippet:doc-create-styled-selection-renderer-python]
    yield renderer, stage
    renderer.set_selection_group_styles({
        1: DEFAULT_SELECTION_STYLE,
        2: DEFAULT_SELECTION_STYLE,
    })
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


def _load_scene(renderer, stage):
    ovstage.population.open_usd(stage, TEST_PICKING_PATH, ordinal=1)
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()
    renderer.reset()
    for _ in range(2):
        renderer.step(render_products={"/Render/Camera"}, delta_time=1.0 / 60.0, ordinal=1)
    return 1


def _pick_hits(renderer, ordinal, left_ndc, top_ndc, right_ndc, bottom_ndc):
    # [snippet:doc-enqueue-pick-query-python]
    renderer.enqueue_pick_query(
        render_product_path="/Render/Camera",
        left_ndc=left_ndc,
        top_ndc=top_ndc,
        right_ndc=right_ndc,
        bottom_ndc=bottom_ndc,
    )
    products = renderer.step(
        render_products={"/Render/Camera"},
        delta_time=1.0 / 60.0,
        ordinal=ordinal,
    )
    # [/snippet:doc-enqueue-pick-query-python]

    product = products["/Render/Camera"]
    frame = product.frames[0]
    pick_var = frame.render_vars[ovrtx.OVRTX_RENDER_VAR_PICK_HIT]

    # [snippet:doc-read-pick-hit-buffer-python]
    mapping = pick_var.map(device=ovrtx.Device.CPU)
    magic = int(np.from_dlpack(mapping.params["magic"]).reshape(-1)[0])
    version = int(np.from_dlpack(mapping.params["version"]).reshape(-1)[0])
    hit_count = int(np.from_dlpack(mapping.params["hitCount"]).reshape(-1)[0])
    prim_paths = np.from_dlpack(mapping["primPath"]).copy().reshape(-1)
    object_types = np.from_dlpack(mapping["objectType"]).copy().reshape(-1)
    geometry_instance_ids = np.from_dlpack(mapping["geometryInstanceId"]).copy().reshape(-1)
    world_positions = np.from_dlpack(mapping["worldPositionM"]).copy().reshape((-1, 3))
    world_normals = np.from_dlpack(mapping["worldNormal"]).copy().reshape((-1, 3))
    mapping.unmap()

    if magic != ovrtx.OVRTX_PICK_HIT_MAGIC or version != ovrtx.OVRTX_PICK_HIT_VERSION:
        raise RuntimeError("Unexpected pick-hit schema")

    hits = []
    for i in range(hit_count):
        prim_path = int(prim_paths[i])
        if prim_path == 0:
            raise RuntimeError("Pick hit has an empty prim path id")
        hits.append(
            {
                "prim_path": prim_path,
                "object_type": int(object_types[i]),
                "geometry_instance_id": int(geometry_instance_ids[i]),
                "world_position": tuple(float(x) for x in world_positions[i]),
                "world_normal": tuple(float(x) for x in world_normals[i]),
            }
        )
    # [/snippet:doc-read-pick-hit-buffer-python]

    return hits


def _resolve_picked_paths(renderer, hits):
    # [snippet:doc-resolve-picked-prim-paths-python]
    picked_paths = {
        renderer.resolve_prim_path_id(hit["prim_path"])
        for hit in hits
    }
    picked_paths.discard("")
    # [/snippet:doc-resolve-picked-prim-paths-python]

    return picked_paths


def _pick_paths(renderer, ordinal, left_ndc, top_ndc, right_ndc, bottom_ndc):
    return _resolve_picked_paths(renderer, _pick_hits(renderer, ordinal, left_ndc, top_ndc, right_ndc, bottom_ndc))


def _render_ldr(renderer, ordinal):
    products = renderer.step(
        render_products={"/Render/Camera"},
        delta_time=1.0 / 60.0,
        ordinal=ordinal,
    )
    frame = products["/Render/Camera"].frames[0]
    mapping = frame.render_vars["LdrColor"].map(device=ovrtx.Device.CPU)
    pixels = np.from_dlpack(mapping).copy()
    mapping.unmap()
    assert pixels.dtype == np.uint8
    assert pixels.shape == (RENDER_HEIGHT, RENDER_WIDTH, 4)
    return pixels


def _num_changed_pixels(a, b, threshold=8):
    diff = np.abs(a.astype(np.int16) - b.astype(np.int16))
    return int(np.count_nonzero(np.any(diff > threshold, axis=2)))


def _save_ldr_image(output_dir, name, pixels):
    Image.fromarray(pixels).save(output_dir / f"{name}.png")


def _save_delta_image(output_dir, name, a, b):
    diff = np.abs(a.astype(np.int16) - b.astype(np.int16))
    visible_diff = np.clip(diff * 8, 0, 255).astype(np.uint8)
    visible_diff[:, :, 3] = 255
    Image.fromarray(visible_diff).save(output_dir / f"{name}.png")


def test_pick_center_pixel(picking_renderer):
    renderer, stage = picking_renderer
    ordinal = _load_scene(renderer, stage)

    picked_paths = _pick_paths(
        renderer,
        ordinal,
        CENTER_LEFT_NDC,
        CENTER_TOP_NDC,
        CENTER_RIGHT_NDC,
        CENTER_BOTTOM_NDC,
    )
    assert picked_paths == {"/World/CenterCube"}


def test_marquee_picks_multiple_prims(picking_renderer):
    renderer, stage = picking_renderer
    ordinal = _load_scene(renderer, stage)

    picked_paths = _pick_paths(renderer, ordinal, 0.0, 0.0, MARQUEE_RIGHT_NDC, 1.0)
    assert "/World/LeftCube" in picked_paths
    assert "/World/CenterCube" in picked_paths
    assert "/World/RightCube" not in picked_paths


@pytest.mark.filterwarnings("ignore:.* is deprecated in ovrtx 0\\.4\\..*:DeprecationWarning")
def test_pickable_false_excludes_prim(output_dir):
    renderer = ovrtx.Renderer(
        ovrtx.RendererConfig(
            selection_outline_enabled=True,
            log_file_path=str(output_dir / "picking_selection_pickable.ovrtx.log"),
        )
    )
    renderer.open_usd(TEST_PICKING_PATH)
    renderer.reset()
    for _ in range(2):
        renderer.step(render_products={"/Render/Camera"}, delta_time=1.0 / 60.0)

    center_hits = _pick_hits(
        renderer,
        None,
        CENTER_LEFT_NDC,
        CENTER_TOP_NDC,
        CENTER_RIGHT_NDC,
        CENTER_BOTTOM_NDC,
    )
    picked_paths = _resolve_picked_paths(renderer, center_hits)
    assert picked_paths == {"/World/CenterCube"}

    # [snippet:doc-set-pickable-python]
    center_path_ids = [hit["prim_path"] for hit in center_hits]
    renderer.set_pickable(center_path_ids, False)
    # [/snippet:doc-set-pickable-python]

    picked_paths = _pick_paths(renderer, None, 0.0, 0.0, MARQUEE_RIGHT_NDC, 1.0)
    assert "/World/LeftCube" in picked_paths
    assert "/World/CenterCube" not in picked_paths
    renderer.destroy()


def test_selection_outline_group_renders(picking_renderer, output_dir):
    renderer, stage = picking_renderer
    _load_scene(renderer, stage)

    center_hits = _pick_hits(
        renderer,
        1,
        CENTER_LEFT_NDC,
        CENTER_TOP_NDC,
        CENTER_RIGHT_NDC,
        CENTER_BOTTOM_NDC,
    )

    baseline_pixels = _render_ldr(renderer, 1)
    _save_ldr_image(output_dir, "picking_selection.selection_outline.baseline", baseline_pixels)

    # [snippet:doc-set-selection-outline-group-python]
    center_path_ids = [hit["prim_path"] for hit in center_hits]
    renderer.set_selection_outline_group(center_path_ids, 1)
    # [/snippet:doc-set-selection-outline-group-python]

    selected_pixels = _render_ldr(renderer, 1)
    _save_ldr_image(output_dir, "picking_selection.selection_outline.selected", selected_pixels)
    _save_delta_image(
        output_dir,
        "picking_selection.selection_outline.delta_selected_vs_baseline",
        selected_pixels,
        baseline_pixels,
    )
    assert _num_changed_pixels(selected_pixels, baseline_pixels) > 0

    # [snippet:doc-clear-selection-outline-group-python]
    renderer.set_selection_outline_group(center_path_ids, 0)
    # [/snippet:doc-clear-selection-outline-group-python]

    cleared_pixels = _render_ldr(renderer, 1)
    _save_ldr_image(output_dir, "picking_selection.selection_outline.cleared", cleared_pixels)
    _save_delta_image(
        output_dir,
        "picking_selection.selection_outline.delta_selected_vs_cleared",
        selected_pixels,
        cleared_pixels,
    )
    assert _num_changed_pixels(selected_pixels, cleared_pixels) > 0


def test_selection_style_groups_control_outline_and_fill(styled_selection_renderer, output_dir):
    renderer, stage = styled_selection_renderer
    _load_scene(renderer, stage)

    baseline_pixels = _render_ldr(renderer, 1)

    # [snippet:doc-set-selection-group-styles-python]
    renderer.set_selection_group_styles({
        1: ovrtx.SelectionGroupStyle(
            outline_color=(1.0, 0.0, 0.0, 1.0),
            fill_color=(0.0, 1.0, 0.0, 1.0),
        ),
        2: ovrtx.SelectionGroupStyle(
            outline_color=(0.0, 0.0, 1.0, 1.0),
            fill_color=(1.0, 0.0, 1.0, 1.0),
        ),
    })
    # [/snippet:doc-set-selection-group-styles-python]

    # [snippet:doc-assign-selection-style-groups-python]
    renderer.set_selection_outline_group_strings(["/World/CenterCube", "/World/LeftCube"], [1, 2])
    # [/snippet:doc-assign-selection-style-groups-python]

    styled_pixels = _render_ldr(renderer, 1)
    _save_ldr_image(output_dir, "picking_selection.selection_style.group_assignment", styled_pixels)
    _save_delta_image(
        output_dir,
        "picking_selection.selection_style.delta_group_assignment_vs_baseline",
        styled_pixels,
        baseline_pixels,
    )
    assert _num_changed_pixels(styled_pixels, baseline_pixels) > 0

    renderer.set_selection_group_styles({
        1: ovrtx.SelectionGroupStyle(
            outline_color=(1.0, 0.0, 0.0, 1.0),
            fill_color=(0.0, 0.0, 1.0, 1.0),
        ),
        2: ovrtx.SelectionGroupStyle(
            outline_color=(0.0, 0.0, 1.0, 1.0),
            fill_color=(0.0, 1.0, 0.0, 1.0),
        ),
    })
    fill_recolored_pixels = _render_ldr(renderer, 1)
    _save_delta_image(
        output_dir,
        "picking_selection.selection_style.delta_fill_recolor",
        fill_recolored_pixels,
        styled_pixels,
    )
    assert _num_changed_pixels(fill_recolored_pixels, styled_pixels) > 0

    renderer.set_selection_outline_group_strings(["/World/CenterCube", "/World/LeftCube"], [2, 1])
    swapped_pixels = _render_ldr(renderer, 1)
    _save_delta_image(
        output_dir,
        "picking_selection.selection_style.delta_swapped_groups",
        swapped_pixels,
        fill_recolored_pixels,
    )
    assert _num_changed_pixels(swapped_pixels, fill_recolored_pixels) > 0
