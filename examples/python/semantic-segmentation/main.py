#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""
Render camera AOVs from the robot lineup scene and log them to Rerun.

Usage:
    uv run main.py
    uv run main.py --resolution 1280 720 --warmup-frames 10
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image, ImageDraw, ImageFont

EXAMPLE_DIR = Path(__file__).resolve().parent
DEFAULT_USD = Path("ovrtx-robot-lineup.usda")


def _usd_asset_path(path: Path) -> str:
    asset_path = path.expanduser().as_posix()
    if "@" in asset_path:
        raise ValueError(f"USD asset paths containing '@' are not supported: {asset_path}")
    return asset_path


def _resolve_scene_path(path: Path) -> Path:
    expanded = path.expanduser()
    if expanded.is_absolute():
        return expanded.resolve()
    return (EXAMPLE_DIR / expanded).resolve()


def _scene_asset_path(path: Path) -> Path:
    expanded = path.expanduser()
    if expanded.is_absolute():
        return expanded.resolve()

    resolved = _resolve_scene_path(expanded)
    return Path(os.path.relpath(resolved, Path.cwd()))


# [snippet:compose-sublayer-render-product]
def build_render_layer_usda(
    scene_path: Path, resolution: tuple[int, int], render_mode: str = "RealTimePathTracing"
) -> str:
    """Compose the robot scene and author a RenderProduct with each requested camera AOV."""
    width, height = resolution
    source_scene = _usd_asset_path(scene_path)

    # Minimal has no HDR color output. Request its clip-depth aliases alongside the shared annotations.
    hdr_request = "<HdrColor>," if render_mode != "MinimalRendering" else ""
    selection_request = "<SelectionState>," if render_mode != "MinimalRendering" else ""
    selection_definition = ('def RenderVar "SelectionState" {\n'
                            '            string sourceName = "SelectionState"\n        }'
                            if render_mode != "MinimalRendering" else "")
    minimal_depth_requests = "<Depth>, <XRDepth>," if render_mode == "MinimalRendering" else ""
    # Minimal ignores dome lighting; add ambient fill so every robot is visible in the preview.
    minimal_settings_and_vars = """color3f omni:rtx:rt:ambientLight:color = (1, 1, 1)
    float omni:rtx:rt:ambientLight:intensity = 0.2
    def RenderVar "Depth" {
        string sourceName = "Depth"
    }
    def RenderVar "XRDepth" {
        string sourceName = "XRDepth"
    }""" if render_mode == "MinimalRendering" else ""

    return f"""#usda 1.0
(
    subLayers = [
        @{source_scene}@
    ]
)

over "World"
{{
    over "GR1T2_fourier_hand_6dof" (
        prepend apiSchemas = ["SemanticsAPI:label", "SemanticsAPI:class"]
    )
    {{
        string semantic:class:params:semanticData = "robot"
        string semantic:class:params:semanticType = "class"
        string semantic:label:params:semanticData = "GR1T2_fourier_hand_6dof"
        string semantic:label:params:semanticType = "label"
    }}

    over "spot" (
        prepend apiSchemas = ["SemanticsAPI:label", "SemanticsAPI:class"]
    )
    {{
        string semantic:class:params:semanticData = "robot"
        string semantic:class:params:semanticType = "class"
        string semantic:label:params:semanticData = "spot"
        string semantic:label:params:semanticType = "label"
    }}

    over "forklift_c" (
        prepend apiSchemas = ["SemanticsAPI:label", "SemanticsAPI:class"]
    )
    {{
        string semantic:class:params:semanticData = "robot"
        string semantic:class:params:semanticType = "class"
        string semantic:label:params:semanticData = "forklift_c"
        string semantic:label:params:semanticType = "label"
    }}

    over "forklift_b" (
        prepend apiSchemas = ["SemanticsAPI:label", "SemanticsAPI:class"]
    )
    {{
        string semantic:class:params:semanticData = "robot"
        string semantic:class:params:semanticType = "class"
        string semantic:label:params:semanticData = "forklift_b"
        string semantic:label:params:semanticType = "label"
    }}

    over "carter_v1" (
        prepend apiSchemas = ["SemanticsAPI:label", "SemanticsAPI:class"]
    )
    {{
        string semantic:class:params:semanticData = "robot"
        string semantic:class:params:semanticType = "class"
        string semantic:label:params:semanticData = "carter_v1"
        string semantic:label:params:semanticType = "label"
    }}

    over "jetbot" (
        prepend apiSchemas = ["SemanticsAPI:label", "SemanticsAPI:class"]
    )
    {{
        string semantic:class:params:semanticData = "robot"
        string semantic:class:params:semanticType = "class"
        string semantic:label:params:semanticData = "jetbot"
        string semantic:label:params:semanticType = "label"
    }}

    over "kaya" (
        prepend apiSchemas = ["SemanticsAPI:label", "SemanticsAPI:class"]
    )
    {{
        string semantic:class:params:semanticData = "robot"
        string semantic:class:params:semanticType = "class"
        string semantic:label:params:semanticData = "kaya"
        string semantic:label:params:semanticType = "label"
    }}
}}

def "Render"
{{
    def RenderProduct "Camera"
    {{
        rel camera = </World/Camera>
        int2 resolution = ({width}, {height})
        token omni:rtx:rendermode = "{render_mode}"
        rel orderedVars = [
            <LdrColor>,
            {hdr_request}
            {selection_request}
            {minimal_depth_requests}
            <NormalSD>,
            <DepthSD>,
            <DistanceToCameraSD>,
            <DistanceToImagePlaneSD>,
            <DiffuseAlbedoSD>,
            <Camera3dPositionSD>,
            <TargetMotionSD>,
            <SemanticSegmentation>,
            <SemanticIdMap>,
            <SemanticInstanceSegmentation>,
            <StableIdSegmentation>,
            <NonStableInstanceSegmentation>,
            <BoundingBox2DTightSD>,
            <BoundingBox2DLooseSD>,
            <BoundingBox3DSD>,
            <SemanticBoundingBox2DTight>,
            <SemanticBoundingBox2DLoose>,
            <SemanticBoundingBox3D>,
            <OcclusionSD>,
            <TruncationSD>,
            <InstanceIdTokenMapSD>,
            <StableIdMap>,
            <InstanceMap>,
            <StableIdMapDeltas>,
            <SemanticIdMapDeltas>,
            <CameraParams>,
            <CrossCorrespondenceSD>,
            <StableIdSemanticIdMap>
        ]

        def RenderVar "LdrColor" {{
            string sourceName = "LdrColor"
        }}

        def RenderVar "HdrColor" {{
            string sourceName = "HdrColor"
        }}

        {selection_definition}

        def RenderVar "NormalSD" {{
            string sourceName = "NormalSD"
        }}

        def RenderVar "DepthSD" {{
            string sourceName = "DepthSD"
        }}

        def RenderVar "DistanceToCameraSD" {{
            string sourceName = "DistanceToCameraSD"
        }}

        def RenderVar "DistanceToImagePlaneSD" {{
            string sourceName = "DistanceToImagePlaneSD"
        }}

        def RenderVar "DiffuseAlbedoSD" {{
            string sourceName = "DiffuseAlbedoSD"
        }}

        def RenderVar "Camera3dPositionSD" {{
            string sourceName = "Camera3dPositionSD"
        }}

        def RenderVar "TargetMotionSD" {{
            string sourceName = "TargetMotionSD"
        }}

        def RenderVar "SemanticSegmentation" {{
            string sourceName = "SemanticSegmentation"
        }}

        def RenderVar "SemanticIdMap" {{
            string sourceName = "SemanticIdMap"
        }}

        def RenderVar "SemanticInstanceSegmentation" {{
            string sourceName = "SemanticInstanceSegmentation"
        }}

        def RenderVar "StableIdSegmentation" {{
            string sourceName = "StableIdSegmentation"
        }}

        def RenderVar "NonStableInstanceSegmentation" {{
            string sourceName = "NonStableInstanceSegmentation"
        }}

        def RenderVar "BoundingBox2DTightSD" {{
            string sourceName = "BoundingBox2DTightSD"
        }}

        def RenderVar "BoundingBox2DLooseSD" {{
            string sourceName = "BoundingBox2DLooseSD"
        }}

        def RenderVar "BoundingBox3DSD" {{
            string sourceName = "BoundingBox3DSD"
        }}

        def RenderVar "SemanticBoundingBox2DTight" {{
            string sourceName = "SemanticBoundingBox2DTight"
        }}

        def RenderVar "SemanticBoundingBox2DLoose" {{
            string sourceName = "SemanticBoundingBox2DLoose"
        }}

        def RenderVar "SemanticBoundingBox3D" {{
            string sourceName = "SemanticBoundingBox3D"
        }}

        def RenderVar "OcclusionSD" {{
            string sourceName = "OcclusionSD"
        }}

        def RenderVar "TruncationSD" {{
            string sourceName = "TruncationSD"
        }}

        def RenderVar "InstanceIdTokenMapSD" {{
            string sourceName = "InstanceIdTokenMapSD"
        }}

        def RenderVar "StableIdMap" {{
            string sourceName = "StableIdMap"
        }}

        def RenderVar "InstanceMap" {{
            string sourceName = "InstanceMap"
        }}

        def RenderVar "StableIdMapDeltas" {{
            string sourceName = "StableIdMapDeltas"
        }}

        def RenderVar "SemanticIdMapDeltas" {{
            string sourceName = "SemanticIdMapDeltas"
        }}

        def RenderVar "CameraParams" {{
            string sourceName = "CameraParams"
        }}

        def RenderVar "CrossCorrespondenceSD" {{
            string sourceName = "CrossCorrespondenceSD"
        }}

        def RenderVar "StableIdSemanticIdMap" {{
            string sourceName = "StableIdSemanticIdMap"
        }}
        {minimal_settings_and_vars}
    }}
}}
"""
# [/snippet:compose-sublayer-render-product]


def _to_uint8_image(values: np.ndarray) -> np.ndarray:
    return (np.clip(values, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def _visualize_scalar(values: np.ndarray) -> np.ndarray:
    scalar = np.nan_to_num(np.asarray(values, dtype=np.float32), copy=False)
    finite = scalar[np.isfinite(scalar)]
    if finite.size == 0:
        return np.zeros((*scalar.shape, 3), dtype=np.uint8)

    lo, hi = np.percentile(finite, [1.0, 99.0])
    if not hi > lo:
        hi = lo + 1.0

    normalized = (scalar - lo) / (hi - lo)
    gray = _to_uint8_image(normalized)
    return np.repeat(gray[..., None], 3, axis=-1)


def _visualize_labels(values: np.ndarray) -> np.ndarray:
    labels = np.squeeze(values)
    if labels.ndim == 3:
        labels = labels.astype(np.uint64, copy=False)
        label_ids = labels[..., 0]
        if labels.shape[-1] > 1:
            label_ids = label_ids ^ (labels[..., 1] << 13)
        if labels.shape[-1] > 2:
            label_ids = label_ids ^ (labels[..., 2] << 27)
        if labels.shape[-1] > 3:
            label_ids = label_ids ^ (labels[..., 3] << 41)
    elif np.issubdtype(labels.dtype, np.floating):
        label_ids = np.nan_to_num(labels, nan=0, posinf=0, neginf=0).astype(np.uint64)
    else:
        label_ids = labels.astype(np.uint64, copy=False)

    colors = np.empty((*label_ids.shape, 3), dtype=np.uint8)
    colors[..., 0] = ((label_ids * 37 + 17) & 0xFF).astype(np.uint8)
    colors[..., 1] = ((label_ids * 67 + 29) & 0xFF).astype(np.uint8)
    colors[..., 2] = ((label_ids * 97 + 53) & 0xFF).astype(np.uint8)
    colors[label_ids == 0] = 0
    return colors


def _select_lineup_robots(renderer, frame) -> None:
    """Select rendered geometry beneath three robots; parent Xforms do not select their children."""
    robot_groups = {"/World/GR1T2_fourier_hand_6dof": 1, "/World/forklift_c": 2, "/World/kaya": 3}
    selected_paths = []
    selected_groups = []
    # Reuse the captured path map, including instance-proxy paths, instead of guessing mesh names.
    for path in sorted(set(_map_id_map(frame, "StableIdMap").values())):
        for root, group in robot_groups.items():
            if path.startswith(root + "/"):
                selected_paths.append(path)
                selected_groups.append(group)
                break
    # Custom scenes may contain none of these robots; still capture their AOVs with empty selection.
    if selected_paths:
        renderer.set_selection_outline_group_strings(selected_paths, selected_groups)


# [snippet:doc-selection-state-preview]
def _visualize_selection_state(values: np.ndarray) -> np.ndarray:
    """Decode coverage samples before coloring: hue is group, brightness is visibility."""
    if values.dtype != np.uint16 or values.ndim != 3 or values.shape[-1] != 4:
        raise ValueError("SelectionState must have uint16 shape (H, W, 4)")
    groups = values & 0xFF
    visible = (values & 0x100) != 0
    # The robot capture uses groups 1/2/3: cyan, orange, and purple. Zero stays black.
    palette = np.array([[0, 0, 0], [0, 0.85, 1], [1, 0.55, 0.1], [0.8, 0.35, 1]], dtype=np.float32)
    colors = palette[(groups - 1) % 3 + 1]
    brightness = np.where(groups == 0, 0.0, np.where(visible, 1.0, 0.25))
    # Each channel is a coverage sample, not a color component; average decoded colors.
    return _to_uint8_image((colors * brightness[..., None]).mean(axis=2))
# [/snippet:doc-selection-state-preview]


def _visualize_vector3(values: np.ndarray) -> np.ndarray:
    vector = np.nan_to_num(np.asarray(values[..., :3], dtype=np.float32), copy=False)
    normalized = np.empty_like(vector, dtype=np.float32)

    for channel in range(3):
        values_channel = vector[..., channel]
        finite = values_channel[np.isfinite(values_channel)]
        if finite.size == 0:
            normalized[..., channel] = 0.0
            continue

        lo, hi = np.percentile(finite, [1.0, 99.0])
        if not hi > lo:
            hi = lo + 1.0
        normalized[..., channel] = (values_channel - lo) / (hi - lo)

    return _to_uint8_image(normalized)


def _visualize_hdr(values: np.ndarray) -> np.ndarray:
    rgb = np.nan_to_num(np.asarray(values[..., :3], dtype=np.float32), copy=False)
    tonemapped = rgb / (1.0 + np.maximum(rgb, 0.0))
    return _to_uint8_image(tonemapped ** (1.0 / 2.2))


def _visualize_normal(values: np.ndarray) -> np.ndarray:
    normals = np.asarray(values[..., :3], dtype=np.float32)
    return _to_uint8_image(normals * 0.5 + 0.5)


def _visualize_motion(values: np.ndarray) -> np.ndarray:
    """Show backward flow direction as hue and magnitude as brightness, with 20 pixels at full brightness."""
    motion = np.asarray(values, dtype=np.float32)
    valid = np.all(np.isfinite(motion), axis=-1) & (motion[..., 3] >= 0)
    flow = np.where(valid[..., None], motion[..., :2], 0.0)
    magnitude = np.linalg.norm(flow, axis=-1)

    # A fixed scale preserves displacement comparisons; invalid and stationary pixels stay black.
    hsv = np.zeros((*flow.shape[:2], 3), dtype=np.uint8)
    hsv[..., 0] = ((np.arctan2(flow[..., 1], flow[..., 0]) / (2.0 * np.pi) + 1.0) % 1.0 * 255).astype(np.uint8)
    hsv[..., 1] = 255
    hsv[..., 2] = (np.clip(magnitude / 20.0, 0.0, 1.0) * 255).astype(np.uint8)
    hsv[magnitude < 1.0e-3] = 0
    return np.asarray(Image.frombytes("HSV", (hsv.shape[1], hsv.shape[0]), hsv.tobytes()).convert("RGB"))


def build_aov_blueprint(rrb, grid_columns: int):
    return rrb.Blueprint(
        rrb.Grid(
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/LdrColor/display", name="LdrColor"),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/HdrColor/display", name="HdrColor"),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/SelectionState/display", name="SelectionState"),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/NormalSD/display", name="NormalSD"),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/DepthSD/display", name="DepthSD"),
            rrb.Spatial2DView(
                origin="/",
                contents="+/render/aovs/DistanceToCameraSD/display",
                name="DistanceToCameraSD",
            ),
            rrb.Spatial2DView(
                origin="/",
                contents="+/render/aovs/DistanceToImagePlaneSD/display",
                name="DistanceToImagePlaneSD",
            ),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/DiffuseAlbedoSD/display", name="DiffuseAlbedoSD"),
            rrb.Spatial2DView(
                origin="/",
                contents="+/render/aovs/Camera3dPositionSD/display",
                name="Camera3dPositionSD",
            ),
            rrb.Spatial2DView(
                origin="/",
                contents="+/render/aovs/SemanticSegmentation/class_ids",
                name="SemanticSegmentation",
            ),
            rrb.Spatial2DView(
                origin="/", contents="+/render/aovs/TargetMotionSD/display", name="TargetMotionSD",
            ),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/SemanticInstanceSegmentation/display", name="SemanticInstanceSegmentation"),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/StableIdSegmentation/display", name="StableIdSegmentation"),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/NonStableInstanceSegmentation/display", name="NonStableInstanceSegmentation"),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/BoundingBox2DTightSD/display", name="BoundingBox2DTightSD"),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/BoundingBox2DLooseSD/display", name="BoundingBox2DLooseSD"),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/BoundingBox3DSD/display", name="BoundingBox3DSD"),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/SemanticBoundingBox2DTight/display", name="SemanticBoundingBox2DTight"),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/SemanticBoundingBox2DLoose/display", name="SemanticBoundingBox2DLoose"),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/SemanticBoundingBox3D/display", name="SemanticBoundingBox3D"),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/OcclusionSD/display", name="OcclusionSD"),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/InstanceIdTokenMapSD/display", name="InstanceIdTokenMapSD"),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/StableIdMap/display", name="StableIdMap"),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/InstanceMap/display", name="InstanceMap"),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/StableIdMapDeltas/display", name="StableIdMapDeltas"),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/SemanticIdMapDeltas/display", name="SemanticIdMapDeltas"),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/CameraParams/display", name="CameraParams"),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/StableIdSemanticIdMap/display", name="StableIdSemanticIdMap"),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/SemanticIdMap/display", name="SemanticIdMap"),
            grid_columns=grid_columns,
            name="Camera AOVs",
        ),
        rrb.TimePanel(timeline="sim_time"),
        collapse_panels=True,
    )


def _map_render_var(frame, name: str) -> np.ndarray | dict:
    """Copy named fields and CPU parameters, or the existing single tensor while mapped."""
    with frame.render_vars[f"/Render/Camera/{name}"].map(device=ovrtx.Device.CPU) as mapped:
        if name in {"BoundingBox2DTightSD", "BoundingBox2DLooseSD", "BoundingBox3DSD",
                    "SemanticBoundingBox2DTight", "SemanticBoundingBox2DLoose", "SemanticBoundingBox3D"}:
            return {key: np.from_dlpack(mapped[key]).copy() for key in mapped}
        if name in {"SemanticIdMap", "StableIdMap", "SemanticIdMapDeltas", "StableIdMapDeltas"}:
            return {key: np.from_dlpack(mapped[key]).copy() for key in mapped}
        if name in {"OcclusionSD", "InstanceIdTokenMapSD", "InstanceMap", "StableIdSemanticIdMap"}:
            fields = {key: np.from_dlpack(mapped[key]).copy() for key in mapped}
            if mapped.params:
                fields["params"] = {key: np.from_dlpack(value).copy() for key, value in mapped.params.items()}
            return fields
        if name == "CameraParams":
            return {"params": {key: np.from_dlpack(value).copy() for key, value in mapped.params.items()}}
        return np.from_dlpack(mapped).copy()

def _log_raw_tensor(rr, name: str, pixels: np.ndarray) -> None:
    if hasattr(rr, "Tensor"):
        rr.log(f"render/aovs/{name}/raw", rr.Tensor(np.ascontiguousarray(pixels)))


def _print_logged(name: str, pixels: np.ndarray) -> None:
    print(f"  Logged {name}: shape={pixels.shape}, dtype={pixels.dtype}", file=sys.stderr)


def _print_missing(name: str) -> None:
    print(f"  Missing AOV: {name}", file=sys.stderr)


def _map_id_map(frame, name: str) -> dict[bytes, str]:
    """Read full-width IDs and UTF-8 label spans from named public tensors."""
    return _decode_id_map(_map_render_var(frame, name))


def _decode_id_map(values: dict) -> dict[bytes, str]:
    ids, offsets, data = values["id"], values["label_offsets"], values["label_data"]
    if (ids.dtype != np.uint32 or ids.shape != (len(ids), 4)
            or offsets.dtype != np.uint64 or offsets.shape != (len(ids) + 1,)
            or data.dtype != np.uint8 or data.ndim != 1 or offsets[0] != 0
            or offsets[-1] != data.size or np.any(offsets[1:] < offsets[:-1])):
        raise ValueError("Invalid identifier map shape or label spans")
    # This semantic-label lookup uses the full128-bit ID as its key. Stable path
    # maps may contain duplicate IDs; consumers of those maps should keep rows.
    return {identifier.tobytes(): data[int(start):int(end)].tobytes().decode("utf-8").rstrip()
            for identifier, start, end in zip(ids, offsets[:-1], offsets[1:]) if start != end}


def _print_logged_id_map(name: str, id_map: dict[bytes, str]) -> None:
    print(f"  Decoded {name}: {len(id_map)} labels", file=sys.stderr)


def _print_logged_class_ids(
    name: str,
    class_ids: np.ndarray,
    unmapped_unique_ids: int,
    total_unique_ids: int,
) -> None:
    class_count = np.unique(class_ids).size
    print(
        f"  Logged {name} class ids: shape={class_ids.shape}, dtype={class_ids.dtype}, "
        f"classes={class_count}, unmapped_unique_ids={unmapped_unique_ids}/{total_unique_ids}",
        file=sys.stderr,
    )


def _class_color(class_id: int) -> tuple[int, int, int]:
    return (
        (class_id * 37 + 17) & 0xFF,
        (class_id * 67 + 29) & 0xFF,
        (class_id * 97 + 53) & 0xFF,
    )


def _id_label(id_bytes: bytes, label: str | None) -> str:
    if label:
        return label
    return f"0x{int.from_bytes(id_bytes, byteorder='little'):032x}"


def _build_class_id_mapping(
    id_map: dict[bytes, str],
) -> tuple[dict[bytes, int], list[tuple[int, str, tuple[int, int, int]]]]:
    # Rerun SegmentationImage pixels must be uint16 ClassIds. The renderer IDs
    # are stored as four uint32 words per IdentifierMap row, so allocate a compact uint16
    # class ID for each map entry and log the reverse lookup through
    # AnnotationContext.
    #
    # Python dicts preserve insertion order. That order is the order authored by
    # the decoded IdentifierMap lookup, so class ID 0 corresponds to its first entry,
    # class ID 1 to the second, and so on.
    if len(id_map) > np.iinfo(np.uint16).max + 1:
        raise ValueError(f"Rerun SegmentationImage supports 65536 class ids, got {len(id_map)}")

    class_id_by_id = {}
    annotations = []
    for class_id, (id_bytes, label) in enumerate(id_map.items()):
        class_id_by_id[id_bytes] = class_id
        annotations.append((class_id, _id_label(id_bytes, label), _class_color(class_id)))

    return class_id_by_id, annotations


def _append_unmapped_annotation(annotations: list[tuple[int, str, tuple[int, int, int]]]) -> int:
    if len(annotations) <= np.iinfo(np.uint16).max:
        class_id = len(annotations)
        annotations.append((class_id, "Unmapped", (0, 0, 0)))
        return class_id

    return 0


def _segmentation_id_keys(segmentation: np.ndarray) -> np.ndarray:
    # Convert a segmentation image into one raw 16-byte key per pixel.
    #
    # SemanticSegmentation is a scalar uint32 image. SemanticIdMap stores those
    # values in IdentifierMap::id[0], with id[1:4] zeroed, so we zero-extend each
    # scalar pixel to a 16-byte key.
    ids = np.squeeze(segmentation)

    if ids.ndim != 2:
        raise ValueError(f"Expected a 2D scalar segmentation image, got shape {ids.shape}")

    if np.issubdtype(ids.dtype, np.floating):
        scalar_ids = np.nan_to_num(ids, nan=0, posinf=0, neginf=0).astype("<u8")
    else:
        scalar_ids = ids.astype("<u8", copy=False)

    packed_ids = np.zeros((*scalar_ids.shape, 2), dtype="<u8")
    packed_ids[..., 0] = scalar_ids
    return np.ascontiguousarray(packed_ids).view(np.dtype((np.void, 16))).reshape(scalar_ids.shape)


def _remap_segmentation_to_class_ids(
    segmentation: np.ndarray,
    id_map: dict[bytes, str],
) -> tuple[np.ndarray, list[tuple[int, str, tuple[int, int, int]]], int, int]:
    class_id_by_id, annotations = _build_class_id_mapping(id_map)

    # Work per unique ID instead of per pixel. A 1920x1080 segmentation image can
    # contain millions of pixels but usually only a small number of object IDs.
    # np.unique gives us a compact unique-ID table and an inverse array that
    # reconstructs the original image shape after each unique ID is mapped once.
    id_keys = _segmentation_id_keys(segmentation)
    unique_ids, inverse = np.unique(id_keys.reshape(-1), return_inverse=True)

    # Map each unique 16-byte render ID to the uint16 Rerun class ID assigned
    # from the decoded IdentifierMap. If a pixel ID is absent from the map, put
    # those pixels in a single explicit "Unmapped" class so the viewer exposes
    # the mismatch instead of silently folding them into class 0.
    class_ids_for_unique = np.zeros(unique_ids.shape, dtype=np.uint16)
    unmapped_class_id = None
    unmapped_unique_ids = 0
    for index, id_key in enumerate(unique_ids):
        class_id = class_id_by_id.get(id_key.tobytes())
        if class_id is None:
            if unmapped_class_id is None:
                unmapped_class_id = _append_unmapped_annotation(annotations)
            class_id = unmapped_class_id
            unmapped_unique_ids += 1
        class_ids_for_unique[index] = class_id

    class_ids = class_ids_for_unique[inverse].reshape(id_keys.shape)
    class_ids = np.ascontiguousarray(class_ids)
    return class_ids, annotations, unmapped_unique_ids, unique_ids.size


def _log_segmentation_image_with_context(
    rr,
    path: str,
    segmentation: np.ndarray,
    id_map: dict[bytes, str],
) -> tuple[np.ndarray, int, int]:
    class_ids, annotations, unmapped_unique_ids, total_unique_ids = _remap_segmentation_to_class_ids(
        segmentation,
        id_map,
    )

    # The SegmentationImage intentionally contains compact uint16 class IDs, not
    # the original uint32 semantic IDs. The original render-var tensor is still
    # logged separately under render/aovs/<name>/raw. Rerun uses this entity's
    # AnnotationContext to turn those compact IDs back into labels and colors.
    rr.log(path, rr.AnnotationContext(annotations), static=True)
    rr.log(f"{path}/class_ids", rr.SegmentationImage(class_ids))
    return class_ids, unmapped_unique_ids, total_unique_ids


# [snippet:log-aovs-to-rerun]
def log_aovs_to_rerun(rr, frame) -> int:
    logged = 0
    semantic_id_map = None

    if "/Render/Camera/SemanticIdMap" in frame.render_vars:
        semantic_id_map = _map_id_map(frame, "SemanticIdMap")
        _print_logged_id_map("SemanticIdMap", semantic_id_map)
        logged += 1
    else:
        _print_missing("SemanticIdMap")

    if "/Render/Camera/LdrColor" in frame.render_vars:
        ldr_color = _map_render_var(frame, "LdrColor")
        _log_raw_tensor(rr, "LdrColor", ldr_color)
        rr.log("render/aovs/LdrColor/display", rr.Image(np.ascontiguousarray(ldr_color)))
        _print_logged("LdrColor", ldr_color)
        logged += 1
    else:
        _print_missing("LdrColor")

    if "/Render/Camera/HdrColor" in frame.render_vars:
        hdr_color = _map_render_var(frame, "HdrColor")
        _log_raw_tensor(rr, "HdrColor", hdr_color)
        rr.log("render/aovs/HdrColor/display", rr.Image(_visualize_hdr(hdr_color)))
        _print_logged("HdrColor", hdr_color)
        logged += 1
    else:
        _print_missing("HdrColor")

    if "/Render/Camera/SelectionState" in frame.render_vars:
        selection = _map_render_var(frame, "SelectionState")
        _log_raw_tensor(rr, "SelectionState", selection)
        rr.log("render/aovs/SelectionState/display", rr.Image(_visualize_selection_state(selection)))
        _print_logged("SelectionState", selection)
        logged += 1

    if "/Render/Camera/NormalSD" in frame.render_vars:
        normal_sd = _map_render_var(frame, "NormalSD")
        _log_raw_tensor(rr, "NormalSD", normal_sd)
        rr.log("render/aovs/NormalSD/display", rr.Image(_visualize_normal(normal_sd)))
        _print_logged("NormalSD", normal_sd)
        logged += 1
    else:
        _print_missing("NormalSD")

    if "/Render/Camera/DepthSD" in frame.render_vars:
        depth_sd = _map_render_var(frame, "DepthSD")
        depth_scalar = np.ascontiguousarray(np.squeeze(depth_sd, axis=-1))
        _log_raw_tensor(rr, "DepthSD", depth_sd)
        if hasattr(rr, "DepthImage"):
            rr.log("render/aovs/DepthSD/depth", rr.DepthImage(depth_scalar))
        rr.log("render/aovs/DepthSD/display", rr.Image(_visualize_scalar(depth_scalar)))
        _print_logged("DepthSD", depth_sd)
        logged += 1
    else:
        _print_missing("DepthSD")

    if "/Render/Camera/DistanceToCameraSD" in frame.render_vars:
        distance_to_camera = _map_render_var(frame, "DistanceToCameraSD")
        distance_to_camera_scalar = np.ascontiguousarray(np.squeeze(distance_to_camera, axis=-1))
        _log_raw_tensor(rr, "DistanceToCameraSD", distance_to_camera)
        if hasattr(rr, "DepthImage"):
            rr.log("render/aovs/DistanceToCameraSD/depth", rr.DepthImage(distance_to_camera_scalar))
        rr.log("render/aovs/DistanceToCameraSD/display", rr.Image(_visualize_scalar(distance_to_camera_scalar)))
        _print_logged("DistanceToCameraSD", distance_to_camera)
        logged += 1
    else:
        _print_missing("DistanceToCameraSD")

    if "/Render/Camera/DistanceToImagePlaneSD" in frame.render_vars:
        distance_to_image_plane = _map_render_var(frame, "DistanceToImagePlaneSD")
        distance_to_image_plane_scalar = np.ascontiguousarray(np.squeeze(distance_to_image_plane, axis=-1))
        _log_raw_tensor(rr, "DistanceToImagePlaneSD", distance_to_image_plane)
        if hasattr(rr, "DepthImage"):
            rr.log("render/aovs/DistanceToImagePlaneSD/depth", rr.DepthImage(distance_to_image_plane_scalar))
        rr.log(
            "render/aovs/DistanceToImagePlaneSD/display",
            rr.Image(_visualize_scalar(distance_to_image_plane_scalar)),
        )
        _print_logged("DistanceToImagePlaneSD", distance_to_image_plane)
        logged += 1
    else:
        _print_missing("DistanceToImagePlaneSD")

    if "/Render/Camera/DiffuseAlbedoSD" in frame.render_vars:
        diffuse_albedo = _map_render_var(frame, "DiffuseAlbedoSD")
        _log_raw_tensor(rr, "DiffuseAlbedoSD", diffuse_albedo)
        rr.log("render/aovs/DiffuseAlbedoSD/display", rr.Image(np.ascontiguousarray(diffuse_albedo)))
        _print_logged("DiffuseAlbedoSD", diffuse_albedo)
        logged += 1
    else:
        _print_missing("DiffuseAlbedoSD")

    if "/Render/Camera/Camera3dPositionSD" in frame.render_vars:
        camera_position = _map_render_var(frame, "Camera3dPositionSD")
        _log_raw_tensor(rr, "Camera3dPositionSD", camera_position)
        rr.log("render/aovs/Camera3dPositionSD/display", rr.Image(_visualize_vector3(camera_position)))
        _print_logged("Camera3dPositionSD", camera_position)
        logged += 1
    else:
        _print_missing("Camera3dPositionSD")

    if "/Render/Camera/SemanticSegmentation" in frame.render_vars:
        semantic_segmentation = _map_render_var(frame, "SemanticSegmentation")
        _log_raw_tensor(rr, "SemanticSegmentation", semantic_segmentation)
        if semantic_id_map is not None:
            semantic_class_ids, unmapped_unique_ids, total_unique_ids = _log_segmentation_image_with_context(
                rr,
                "render/aovs/SemanticSegmentation",
                semantic_segmentation,
                semantic_id_map,
            )
            _print_logged_class_ids(
                "SemanticSegmentation",
                semantic_class_ids,
                unmapped_unique_ids,
                total_unique_ids,
            )
        rr.log("render/aovs/SemanticSegmentation/display", rr.Image(_visualize_labels(semantic_segmentation)))
        _print_logged("SemanticSegmentation", semantic_segmentation)
        logged += 1
    else:
        _print_missing("SemanticSegmentation")

    return logged
# [/snippet:log-aovs-to-rerun]


def export_aov_pngs(frame, output_dir: Path) -> int:
    """Write display PNGs for no-spawn runs without changing the Rerun logging path."""
    output_dir.mkdir(parents=True, exist_ok=True)

    def save_png(name: str, image: np.ndarray) -> None:
        image = np.ascontiguousarray(image)
        Image.fromarray(image).save(output_dir / f"{name}.png")

    def srgb_transfer(linear: np.ndarray) -> np.ndarray:
        linear = np.clip(linear, 0.0, 1.0)
        return np.where(
            linear <= 0.0031308,
            12.92 * linear,
            1.055 * np.power(linear, 1.0 / 2.4) - 0.055,
        )

    def rgba_or_rgb_uint8(values: np.ndarray) -> np.ndarray:
        values = np.asarray(values)
        if values.dtype == np.uint8:
            return values
        return _to_uint8_image(np.asarray(values, dtype=np.float32))

    def hdr_to_srgb(values: np.ndarray) -> np.ndarray:
        hdr = np.nan_to_num(np.asarray(values, dtype=np.float32), copy=False)
        rgb = srgb_transfer(hdr[..., :3])
        if hdr.shape[-1] >= 4:
            alpha = np.clip(hdr[..., 3:4], 0.0, 1.0)
            return _to_uint8_image(np.concatenate([rgb, alpha], axis=-1))
        return _to_uint8_image(rgb)

    def normalize_scalar(values: np.ndarray) -> np.ndarray:
        scalar = np.squeeze(np.asarray(values, dtype=np.float32))
        finite = scalar[np.isfinite(scalar)]
        if finite.size == 0:
            return np.zeros_like(scalar, dtype=np.float32)

        lo, hi = np.percentile(finite, [1.0, 99.0])
        if not hi > lo:
            return np.zeros_like(scalar, dtype=np.float32)

        return np.clip((np.nan_to_num(scalar, nan=lo, posinf=hi, neginf=lo) - lo) / (hi - lo), 0.0, 1.0)

    def turbo_colormap(values: np.ndarray) -> np.ndarray:
        x = normalize_scalar(values)
        coeffs = np.array(
            [
                [0.13572138, 4.61539260, -42.66032258, 132.13108234, -152.94239396, 59.28637943],
                [0.09140261, 2.19418839, 4.84296658, -14.18503333, 4.27729857, 2.82956604],
                [0.10667330, 12.64194608, -60.58204836, 110.36276771, -89.90310912, 27.34824973],
            ],
            dtype=np.float32,
        )
        powers = np.stack([x**i for i in range(coeffs.shape[1])], axis=-1)
        rgb = np.tensordot(powers, coeffs.T, axes=([-1], [0]))
        return _to_uint8_image(rgb)

    def normalize_vector3(values: np.ndarray) -> np.ndarray:
        vector = np.asarray(values[..., :3], dtype=np.float32)
        normalized = np.zeros_like(vector, dtype=np.float32)

        for channel in range(3):
            component = vector[..., channel]
            finite = component[np.isfinite(component)]
            if finite.size == 0:
                continue

            lo, hi = np.percentile(finite, [1.0, 99.0])
            if not hi > lo:
                continue

            normalized[..., channel] = np.clip(
                (np.nan_to_num(component, nan=lo, posinf=hi, neginf=lo) - lo) / (hi - lo),
                0.0,
                1.0,
            )

        return _to_uint8_image(normalized)

    def normal_to_uint8(values: np.ndarray) -> np.ndarray:
        normals = np.nan_to_num(np.asarray(values[..., :3], dtype=np.float32), copy=False)
        return _to_uint8_image(normals * 0.5 + 0.5)

    def hashed_id_colors(values: np.ndarray) -> np.ndarray:
        labels = np.squeeze(values)
        if labels.ndim != 2:
            raise ValueError(f"Expected a 2D semantic segmentation image, got shape {labels.shape}")

        if np.issubdtype(labels.dtype, np.floating):
            ids = np.nan_to_num(labels, nan=0, posinf=0, neginf=0).astype(np.uint64)
        else:
            ids = labels.astype(np.uint64, copy=False)

        hashed = ids.copy()
        hashed = (hashed ^ (hashed >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        hashed = (hashed ^ (hashed >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        hashed = hashed ^ (hashed >> np.uint64(31))

        colors = np.empty((*ids.shape, 3), dtype=np.uint8)
        colors[..., 0] = (hashed & np.uint64(0xFF)).astype(np.uint8)
        colors[..., 1] = ((hashed >> np.uint64(8)) & np.uint64(0xFF)).astype(np.uint8)
        colors[..., 2] = ((hashed >> np.uint64(16)) & np.uint64(0xFF)).astype(np.uint8)
        colors[ids == 0] = 0
        return colors

    converters = {
        "LdrColor": rgba_or_rgb_uint8,
        "HdrColor": hdr_to_srgb,
        "SelectionState": _visualize_selection_state,
        "NormalSD": normal_to_uint8,
        "Depth": turbo_colormap,
        "XRDepth": turbo_colormap,
        "DepthSD": turbo_colormap,
        "DistanceToCameraSD": turbo_colormap,
        "DistanceToImagePlaneSD": turbo_colormap,
        "DiffuseAlbedoSD": rgba_or_rgb_uint8,
        "Camera3dPositionSD": normalize_vector3,
        "SemanticSegmentation": hashed_id_colors,
    }

    exported = 0
    for name, converter in converters.items():
        if f"/Render/Camera/{name}" not in frame.render_vars:
            continue

        pixels = _map_render_var(frame, name)
        save_png(name, converter(pixels))
        exported += 1

    return exported


def capture_additional_aovs(rr, frame, initial_maps: dict, output_dir: Path) -> int:
    """Save additional SD tensors and capture diagnostics, including failures, without hiding empty outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {}
    tensors = {name: _map_render_var(frame, name) for name in ("LdrColor", "SemanticIdMap")}
    np.savez(output_dir / "SemanticIdMap.npz", **tensors["SemanticIdMap"])
    names = (
        "SemanticInstanceSegmentation", "StableIdSegmentation",
        "NonStableInstanceSegmentation", "BoundingBox2DTightSD", "BoundingBox2DLooseSD", "BoundingBox3DSD",
        "SemanticBoundingBox2DTight", "SemanticBoundingBox2DLoose", "SemanticBoundingBox3D", "OcclusionSD",
        "TruncationSD", "InstanceIdTokenMapSD", "StableIdMap", "InstanceMap", "StableIdMapDeltas",
        "SemanticIdMapDeltas", "CameraParams", "CrossCorrespondenceSD", "StableIdSemanticIdMap",
    )
    names += tuple(name for name in ("Depth", "XRDepth", "SelectionState") if f"/Render/Camera/{name}" in frame.render_vars)
    for name in names:
        try:
            values = _map_render_var(frame, name)
            tensors[name] = values
            if isinstance(values, dict):
                fields = {key: value for key, value in values.items() if key != "params"}
                fields.update({"param_" + key: value for key, value in values.get("params", {}).items()})
                np.savez(output_dir / f"{name}.npz", **fields)
                report[name] = {"fields": {key: {"shape": list(value.shape), "dtype": str(value.dtype)}
                                          for key, value in fields.items()},
                                "bytes": sum(value.nbytes for value in fields.values())}
                continue
            np.save(output_dir / f"{name}.npy", values)
            entry = {"shape": list(values.shape), "dtype": str(values.dtype), "bytes": values.nbytes}
            if values.size:
                entry.update(nonzero=int(np.count_nonzero(values)), finite=bool(np.all(np.isfinite(values))))
                _log_raw_tensor(rr, name, values)
                if values.ndim == 3:
                    entry["occupied_pixels"] = int(np.count_nonzero(np.any(values != 0, axis=-1)))
                    entry["unique_ids"] = int(np.unique(values.reshape(-1, values.shape[-1]), axis=0).shape[0])
                    display = (_visualize_selection_state(values) if name == "SelectionState" else
                               _visualize_scalar(np.squeeze(values)) if name in ("Depth", "XRDepth")
                               else _visualize_labels(values))
                    Image.fromarray(display).save(output_dir / f"{name}.png")
                    rr.log(f"render/aovs/{name}/display", rr.Image(display))
            report[name] = entry
            print(f"  Captured {name}: {entry}", file=sys.stderr)
        except (KeyError, RuntimeError, ValueError) as exc:
            report[name] = {"error": str(exc)}
            print(f"  Cannot capture {name}: {exc}", file=sys.stderr)

    visualize_sd_buffers(rr, tensors, initial_maps, output_dir)
    (output_dir / "capture.json").write_text(json.dumps(report, indent=2) + "\n")
    return sum(entry.get("bytes", 0) > 0 for entry in report.values())


def visualize_sd_buffers(rr, tensors: dict, initial_maps: dict, output_dir: Path) -> None:
    """Decode SD records and show their camera-space meaning without presenting metadata as raw pixels."""
    # Join semantic indices to stable IDs, paths and labels; map ordering alone is not an index contract.
    id_maps = {}
    decoded = {}
    for name in ("SemanticIdMap", "StableIdMap", "StableIdMapDeltas", "SemanticIdMapDeltas"):
        values = initial_maps.get(name, tensors[name]) if name.endswith("Deltas") else tensors[name]
        if values is None:
            continue
        id_maps[name] = _decode_id_map(values)
        # Preserve repeated IDs in the saved rows even when a display lookup selects one path.
        decoded[name] = [{"id": identifier.tolist(),
                          "label": values["label_data"][int(start):int(end)].tobytes().decode("utf-8")}
                         for identifier, start, end in zip(values["id"], values["label_offsets"][:-1],
                                                            values["label_offsets"][1:])]

    pairs = np.concatenate((tensors["StableIdSemanticIdMap"]["stable_id"],
                            tensors["StableIdSemanticIdMap"]["semantic_id"]), axis=1)
    decoded["StableIdSemanticIdMap"] = pairs.tolist()
    stable_paths = id_maps["StableIdMap"]
    semantic_labels = id_maps["SemanticIdMap"]
    robot_paths = [
        "/World/GR1T2_fourier_hand_6dof", "/World/spot", "/World/forklift_c", "/World/forklift_b",
        "/World/carter_v1", "/World/jetbot", "/World/kaya",
    ]
    palette = [(255, 110, 100), (255, 205, 70), (80, 210, 250), (205, 145, 255),
               (105, 225, 160), (245, 145, 210), (160, 210, 255)]
    robot_by_index = {}
    robot_by_stable = {}
    for index, pair in enumerate(pairs):
        path = stable_paths.get(pair[:4].tobytes(), "")
        for robot, root in enumerate(robot_paths):
            if path == root or path.startswith(root + "/"):
                robot_by_index[index] = robot
                robot_by_stable[pair[:4].tobytes()] = robot
                break

    # Instance records are named tensors; range and tile metadata are CPU parameters.
    tokens = tensors["InstanceIdTokenMapSD"]
    token_params = tokens["params"]
    count = len(tokens["instance_id"])
    min_instance = token_params["min_instance_id"].item()
    instance_map = tensors["InstanceMap"]["semantic_instance_index"]
    decoded["InstanceIdTokenMapSD"] = {
        "count": count, "min_instance": min_instance, "max_instance": token_params["max_instance_id"].item(),
        "tiles": token_params["render_tile_count"].item(),
        "records": [[int(value) for value in row] for row in zip(tokens["instance_id"], tokens["prim_token"],
                                                               tokens["prototype_index"], tokens["instance_index"])],
    }
    decoded["InstanceMap"] = instance_map.tolist()
    robot_by_instance = {
        min_instance + index: robot_by_index[int(semantic_index)]
        for index, semantic_index in enumerate(instance_map) if int(semantic_index) in robot_by_index
    }

    # Camera matrices use row vectors. Keep camera and box values in scene units; no extra metre scaling is needed.
    camera = tensors["CameraParams"]["params"]
    view, projection = camera["view_matrix"].astype(np.float64), camera["projection_matrix"].astype(np.float64)
    width, height = map(int, camera["render_product_resolution"])
    near, far = map(float, camera["near_far"])
    camera_model = camera["camera_model"].tobytes().decode("utf-8")
    if camera_model != "pinhole":
        raise ValueError("This example's box projection currently supports pinhole cameras only")
    decoded["CameraParams"] = {
        "view": view.tolist(), "projection": projection.tolist(),
        "meters_per_scene_unit": camera["meters_per_scene_unit"].item(),
        "resolution": [width, height], "near_far": [near, far], "model": camera_model,
        "focal_length_distance_fstop_fovx": [camera[key].item() for key in
                                              ("focal_length", "focal_distance", "f_stop", "fov_x_radians")],
        "fisheye_parameters": {key: value.item() if value.shape == (1,) else value.tolist()
                               for key, value in camera.items() if key.startswith(("ftheta_", "lens_"))},
    }
    base = Image.fromarray(tensors["LdrColor"]).convert("RGB")
    base = Image.blend(base, Image.new("RGB", base.size, (15, 20, 28)), 0.35)
    font = ImageFont.load_default(size=max(14, width // 85))
    small_font = ImageFont.load_default(size=max(12, width // 105))
    boxes = {}
    for name in ("BoundingBox2DTightSD", "BoundingBox2DLooseSD", "BoundingBox3DSD",
                 "SemanticBoundingBox2DTight", "SemanticBoundingBox2DLoose", "SemanticBoundingBox3D"):
        semantic = name.startswith("Semantic")
        three_d = "3D" in name
        values = tensors[name]
        count = int(values["valid_count"][0]) if semantic else len(values["extent"])
        if not 0 <= count <= len(values["extent"]):
            raise ValueError(f"Invalid record count for {name}")
        records = []
        for index in range(count):
            row = {"min": values["extent"][index, 0], "max": values["extent"][index, 1]}
            if semantic:
                row.update(stable=values["id"][index], semantic=values["semantic_id"][index])
            else:
                row.update(instance=values["instance_id"][index], tile=values["render_tile_id"][index])
            if three_d:
                row["transform"] = values["object_to_world"][index]
            records.append(row)
        decoded[name] = [{field: value.tolist() for field, value in row.items()} for row in records]
        selected = []
        for row in records:
            robot = (robot_by_stable.get(row["stable"].tobytes()) if semantic
                     else robot_by_instance.get(int(row["instance"])))
            if robot is None or np.any(row["max"] < row["min"]):
                continue
            # Semantic views show one aggregate box per top-level robot. Raw views retain individual robot parts.
            if semantic and stable_paths.get(row["stable"].tobytes()) != robot_paths[robot]:
                continue
            selected.append((robot, row))
        boxes[name] = selected

    # Reuse one edge projection for both raw/semantic boxes and the camera-parameter illustration.
    # [snippet:doc-lineup-project-box]
    def draw_projected_box(draw, row, color) -> int:
        """Transform eight local corners and clip each edge against the camera near plane before projection."""
        corners = np.array([[row["max"][axis] if index & (1 << axis) else row["min"][axis]
                             for axis in range(3)] + [1] for index in range(8)], dtype=np.float64)
        clip = corners @ row["transform"] @ view @ projection
        edges_drawn = 0
        for first in range(8):
            for axis in range(3):
                second = first ^ (1 << axis)
                if second < first:
                    continue
                a, b = clip[first].copy(), clip[second].copy()
                if not np.all(np.isfinite([a, b])) or max(a[3], b[3]) < near:
                    continue
                if a[3] < near:
                    a += (b - a) * (near - a[3]) / (b[3] - a[3])
                if b[3] < near:
                    b += (a - b) * (near - b[3]) / (a[3] - b[3])
                ndc = np.array([a[:2] / a[3], b[:2] / b[3]])
                pixels = (ndc * [0.5, -0.5] + 0.5) * [width, height]
                draw.line([tuple(point) for point in pixels], fill=color, width=max(1, width // 750))
                edges_drawn += 1
        return edges_drawn
    # [/snippet:doc-lineup-project-box]

    displays = {}
    visual_report = {}
    for name, selected in boxes.items():
        image = base.copy()
        draw = ImageDraw.Draw(image)
        drawn = 0
        for robot, row in selected:
            if "3D" in name:
                drawn += draw_projected_box(draw, row, palette[robot]) > 0
            else:
                bounds = (*map(int, row["min"]), *map(int, row["max"]))
                draw.rectangle(bounds, outline=palette[robot], width=max(1, width // 750))
                drawn += 1
            if name.startswith("Semantic") and "3D" not in name:
                x, y = map(int, row["min"])
                label = robot_paths[robot].split("/")[-1].replace("_fourier_hand_6dof", "")
                draw.text((x, max(75, y - 30)), label, font=small_font, fill=palette[robot], stroke_width=2,
                          stroke_fill=(0, 0, 0))
        draw.rectangle((0, 0, width, 65), fill=(15, 20, 28))
        draw.text((18, 12), f"{name} | {drawn} robot {'boxes' if name.startswith('Semantic') else 'part boxes'}",
                  font=font, fill="white")
        displays[name] = image
        visual_report[name] = {"selected_records": len(selected), "drawn_boxes": drawn}

    # Occlusion is a per-instance statistic, not a pixel image: color the corresponding loose boxes.
    occlusion = tensors["OcclusionSD"]
    decoded["OcclusionSD"] = [dict(instance=int(instance), tile=int(tile), ratio=float(ratio))
                               for instance, tile, ratio in zip(occlusion["instance_id"], occlusion["render_tile_id"],
                                                                occlusion["occlusion_ratio"])]
    ratios = {(row["instance"], row["tile"]): row["ratio"] for row in decoded["OcclusionSD"]}
    image = base.copy()
    draw = ImageDraw.Draw(image)
    drawn = 0
    for robot, row in boxes["BoundingBox2DLooseSD"]:
        ratio = ratios.get((int(row["instance"]), int(row["tile"])), -1)
        if not 0 <= ratio <= 1:
            continue
        color = (int(70 + 185 * ratio), int(220 - 150 * ratio), 75)
        draw.rectangle((*map(int, row["min"]), *map(int, row["max"])), outline=color, width=max(1, width // 750))
        drawn += 1
    draw.rectangle((0, 0, width, 65), fill=(15, 20, 28))
    draw.text((18, 12), "OcclusionSD | robot part boxes: green = visible, red = occluded; -1 omitted",
              font=font, fill="white")
    displays["OcclusionSD"] = image
    visual_report["OcclusionSD"] = {"drawn_boxes": drawn}

    # Metadata gets an annotated scene plus readable decoded rows. These are derived illustrations, not image AOVs.
    token_by_instance = {int(instance): {"instance": int(instance), "token": int(token)}
                         for instance, token in zip(tokens["instance_id"], tokens["prim_token"])}
    for name in ("SemanticIdMap", "StableIdMap", "InstanceIdTokenMapSD", "InstanceMap", "StableIdMapDeltas",
                 "SemanticIdMapDeltas", "StableIdSemanticIdMap", "CameraParams"):
        image = Image.new("RGB", (width, height), (15, 20, 28))
        draw = ImageDraw.Draw(image)
        scene = displays["SemanticBoundingBox3D" if name == "CameraParams" else "SemanticBoundingBox2DTight"].copy()
        scene.thumbnail((width * 2 // 3, height * 3 // 4))
        image.paste(scene, (0, height // 7))
        panel_x = width * 2 // 3 + 12
        draw.text((18, 20), name + " | decoded metadata", font=font, fill="white")
        lines = []
        if name == "CameraParams":
            params = decoded[name]
            focal, distance, fstop, fov = params["focal_length_distance_fstop_fovx"]
            lines = [camera_model, f"Resolution: {width} x {height}",
                     f"Metres / scene unit: {params['meters_per_scene_unit']:.3g}",
                     f"Clipping: {near:g} ... {far:g}", f"Focal length: {focal:g}",
                     f"Focus distance: {distance:g}", f"f-stop: {fstop:g}",
                     f"Horizontal FOV: {np.degrees(fov):.2f} deg",
                     "", "Row-vector projection:", "local @ box transform", "@ view @ projection", "divide XY by W",
                     "map NDC to image pixels", "", "View matrix:"]
            lines += [" ".join(f"{value: .3f}" for value in row) for row in view]
            lines += ["", "Projection matrix:"]
            lines += [" ".join(f"{value: .3f}" for value in row) for row in projection]
        else:
            for robot, root in enumerate(robot_paths):
                indices = [index for index, owner in robot_by_index.items() if owner == robot
                           and stable_paths.get(pairs[index, :4].tobytes()) == root]
                if not indices:
                    continue
                index = indices[0]
                key = pairs[index, :4].tobytes()
                label_key = pairs[index, 4:].tobytes()
                caption = root.split("/")[-1].replace("_fourier_hand_6dof", "")
                lines.append((caption, palette[robot]))
                if name in ("StableIdMap", "StableIdMapDeltas"):
                    source = id_maps.get(name, {})
                    lines += [f"ID: {key.hex()}", source.get(key, "No entry in this capture").replace("/World/", "")]
                elif name in ("SemanticIdMap", "SemanticIdMapDeltas"):
                    source = id_maps.get(name, {})
                    lines += [f"Semantic ID: {int(pairs[index, 4])}",
                              source.get(label_key, "No entry in this capture").replace("label: ", "")]
                elif name == "StableIdSemanticIdMap":
                    lines += [f"Semantic-instance index: {index}",
                              f"Stable {key.hex()[:16]}... -> label {int(pairs[index, 4])}"]
                else:
                    instances = [instance for instance, owner in robot_by_instance.items() if owner == robot
                                 and int(instance_map[instance - min_instance]) == index]
                    if name == "InstanceMap":
                        lines += [f"{len(instances)} runtime instances -> index {index}",
                                  f"Pixels encode index + 2 = {index + 2}"]
                    else:
                        token = token_by_instance.get(instances[0]) if instances else None
                        lines += [f"{len(instances)} matching runtime instances"]
                        lines += [f"ID {int(token['instance'])}: token {int(token['token']):#x}"
                                  if token is not None else "No direct token record"]
                lines.append("")
        y = 85
        for line in lines:
            text, color = line if isinstance(line, tuple) else (line, "white")
            # Keep labels inside the panel; full strings and complete identifiers remain in decoded.json.
            text = text if len(text) <= 43 else text[:40] + "..."
            draw.text((panel_x, y), text, font=small_font, fill=color)
            y += max(18, height // 36)
        footer = "Robot subset shown; all decoded records are saved in decoded.json."
        if name.endswith("Deltas"):
            current_count = len(tensors[name]["id"])
            footer = f"First frame: {len(decoded.get(name, []))} entries. Static capture: {current_count} new entries."
        elif name == "StableIdMap":
            unique_ids = np.unique(tensors["StableIdSegmentation"].reshape(-1, 4), axis=0)
            matched = sum(row.tobytes() in stable_paths for row in unique_ids)
            footer = (f"Partial geometry coverage: {matched}/{len(unique_ids)} visible IDs. "
                      "Semantic-instance IDs resolve.")
        draw.text((18, height - 75), footer, font=small_font, fill="white")
        displays[name] = image

    for name, image in displays.items():
        image.save(output_dir / f"{name}.png")
        rr.log(f"render/aovs/{name}/display", rr.Image(np.asarray(image)))
    (output_dir / "decoded.json").write_text(json.dumps(decoded, indent=2) + "\n")
    (output_dir / "visualization.json").write_text(json.dumps(visual_report, indent=2) + "\n")


# Registered PT output candidates; empty outputs stay in capture diagnostics, not the docs table.
PT_AOV_NAMES = [
    'LdrColor', 'HdrColor', 'PtDirectIllumation', 'PtGlobalIllumination',
    'PtReflections', 'PtRefractions', 'PtSubsurfaceScattering', 'PtSelfIllumination',
    'PtBackground', 'PtPreDenoisedResult', 'PtWorldNormal', 'PtWorldPos',
    'PtViewNormal', 'PtZDepth', 'PtVolumes', 'PtDiffuseFilter',
    'PtReflectionFilter', 'PtRefractionFilter', 'PtSubsurfaceFilter', 'PtLuminance',
    'PtIlluminance', 'PtMotion', 'PtLpe0', 'PtLpe1',
    'PtLpe2', 'PtLpe3', 'PtLpe4', 'PtLpe5',
    'PtLpe6', 'PtLpe7', 'PtLpe8', 'DeveloperDebugTexture',
    'DlssInput', 'BumpNormal', 'BumpNormalResearch', 'DiffuseAlbedo',
    'SpecularAlbedo', 'ReflectionsMotion2d', 'ReflectionsFirstBounceDiffuseAlbedo', 'ReflectionsFirstBounceNormal',
    'DepthLinearized', 'Motion2dXYZ', 'Motion2dDilated', 'Motion2dXYZDilated',
    'MotionWorld', 'EmissionAndForegroundMask', 'DiffuseLightingDirectAndIndirect', 'SpecularLightingDirectAndIndirect',
    'LightingComposited', 'Exposure', 'Roughness',
    'DisocclusionMask', 'ReprojectionQuality', 'ViewspacePosition', 'ReflectionsHitT',
    'SubsurfaceScattering', 'SubsurfaceTransmission', 'HighResDepth', 'HighResMotion2d',
    'HighResMotion2dXYZ', 'HighResDisocclusionMask', 'HighResReflectionsMotion2d', 'ReflectionsFirstBounceRayDirAndHitT',
    'XRDepth', 'GroundTruthDeveloperDebugTexture', 'GroundTruthDiffuseAlbedo', 'GroundTruthSpecularAlbedo',
    'GroundTruthDiffuseLighting', 'GroundTruthSpecularLighting', 'GroundTruthCustomComposited', 'GroundTruthEmissionAndForegroundMask',
    'GroundTruthDepthLinearized', 'GroundTruthDepthLinearizedAvgMinMax', 'GroundTruthNormals', 'GroundTruthSubsurfaceScattering',
    'GroundTruthSubsurfaceTransmission', 'GroundTruthDlssInput', 'GroundTruthDlssInputTonemapped', 'PtMultiMatte0',
    'PtMultiMatte1', 'PtMultiMatte2', 'PtMultiMatte3', 'PtMultiMatte4',
    'PtMultiMatte5', 'PtMultiMatte6', 'PtMultiMatte7',
]
PT_LPE_EXPRESSIONS = ["E.*L", "E<RD>.*L", "E<RG>.*L", "E<TD>.*L", "E<TG>.*L",
                      "E<RD>L", "E<RG>L", "E<RD>.+L", "E<RG>.+L"]
# [snippet:doc-pt-multimatte-channels]
# Each requested RenderVar selects four independent RGBA masks. -1 disables a component.
# RGB selectors follow camera position for the sliced preview; alpha is shown separately.
PT_MULTIMATTE_CHANNELS = [
    (8, False), (9, False), (10, False), (11, False),
    (1, False), (2, False), (5, False), (6, False),
    (4, False), (103, True), (104, True), (7, False),
    (3, False), (101, True), (102, True), (-1, False),
]
# [/snippet:doc-pt-multimatte-channels]
PT_MOTION_NAMES = {"PtMotion", "Motion2dXYZ", "Motion2dDilated", "Motion2dXYZDilated", "MotionWorld",
                   "HighResMotion2d", "HighResMotion2dXYZ", "HighResReflectionsMotion2d", "TargetMotionSD"}


# [snippet:doc-pt-lineup-render-product]
def build_pt_render_layer_usda(scene_path: Path, resolution: tuple[int, int], samples_per_pixel: int = 128) -> str:
    """Request PT outputs on the same labeled lineup without changing its source scene."""
    base = build_render_layer_usda(scene_path, resolution)
    # Tag existing objects and bound materials; mask IDs do not change their appearance.
    robot_names = ["GR1T2_fourier_hand_6dof", "spot", "forklift_c", "forklift_b",
                   "carter_v1", "jetbot", "kaya"]
    material_overrides = {
        "forklift_c": '''over "Looks" {
            over "M_Forklift_C01" {
                int multimatte_id = 101
            }
            over "M_Forklift_C01_Blue" {
                int multimatte_id = 102
            }
        }''',
        "forklift_b": '''over "Looks" {
            over "M_Forklift_B1_Body" {
                int multimatte_id = 103
            }
            over "M_Forklift_B1_Glass" {
                int multimatte_id = 104
            }
        }''',
    }
    for identifier, name in enumerate(robot_names, 1):
        base = re.sub(r'(over "' + name + r'"\s*\([^)]*\)\s*\{)',
                      lambda match: match[0] + f'\n        int primvars:multimatte_id = {identifier}\n'
                      + material_overrides.get(name, "") + "\n", base)
    # The source scene assigns IDs 8/9/10 to warehouse walls, shelves and pallets.
    # The source scene also tags warehouse floors with ID 11 for an independent alpha mask.
    # Request only the four configured Multi-Matte RenderVars; each carries its own selectors.
    names = list(dict.fromkeys(PT_AOV_NAMES + re.findall(r'string sourceName = "(\w+)"', base)))
    names = [name for name in names if not name.startswith("PtMultiMatte") or int(name[-1]) < 4]
    definitions = []
    for name in names:
        expression = PT_LPE_EXPRESSIONS[int(name[-1])] if name.startswith("PtLpe") else name
        source_type = 'token sourceType = "lpe"' if name.startswith("PtLpe") else ''
        matte_selectors = ""
        if name.startswith("PtMultiMatte"):
            index = int(name[-1])
            selectors = PT_MULTIMATTE_CHANNELS[index * 4:index * 4 + 4]
            for component, (identifier, is_material) in zip("rgba", selectors):
                matte_selectors += f"int omni:rtx:pt:multimatte:{component}Id = {identifier}\n"
                matte_selectors += f"bool omni:rtx:pt:multimatte:{component}IsMat = {str(is_material).lower()}\n"
        definitions.append(f'def RenderVar "{name}" {{\nstring sourceName = "{expression}"\n{source_type}\n{matte_selectors}}}')
    variables = "\n".join(definitions)
    ordered = ", ".join(f"<{name}>" for name in names)
    width, height = resolution
    # Allow two setup passes after scene edits; samplesPerPixel still caps the render at the requested SPP.
    return base.split('def "Render"', 1)[0] + f'''def "Render" {{
    def RenderProduct "Camera" {{
        rel camera = </World/Camera>
        int2 resolution = ({width}, {height})
        token omni:rtx:rendermode = "PathTracing"
        uint omni:rtx:pt:samplesPerPixel = {samples_per_pixel}
        int omni:rtx:pt:samplesPerIteration = {min(samples_per_pixel, 32)}
        int omni:rtx:quality = 100
        int omni:rtx:quality:minSpp = {samples_per_pixel + 2 * min(samples_per_pixel, 32)}
        bool omni:rtx:pt:adaptiveSampling:enabled = false
        bool omni:rtx:pt:radianceCache:enabled = false
        uint omni:rtx:rt:groundTruth:resolution:width = {width}
        uint omni:rtx:rt:groundTruth:resolution:height = {height}
        rel orderedVars = [{ordered}]
        {variables}
    }}
}}
'''
# [/snippet:doc-pt-lineup-render-product]


# [snippet:doc-pt-pixels-python]
import numpy as np

def decode_pt_pixels(values: np.ndarray) -> np.ndarray:
    """Read typed PT pixels, converting half floats to float32 and UNORM bytes to [0,1]."""
    if values.ndim != 3 or values.shape[-1] not in (1, 2, 4):
        raise ValueError("Expected a channel-last PT image")
    if values.dtype == np.uint8:
        return values.astype(np.float32) / 255.0
    if values.dtype not in (np.float16, np.float32):
        raise ValueError("Expected uint8, float16, or float32 PT pixels")
    return values.astype(np.float32)
# [/snippet:doc-pt-pixels-python]


def pt_display_image(name: str, values: np.ndarray, exposure: float = 1.0) -> np.ndarray:
    """Make PT previews by output meaning; display remapping never changes saved raw values."""
    pixels = decode_pt_pixels(values)
    if name == "Exposure":
        image = Image.new("RGB", (640, 360), "#101820")
        ImageDraw.Draw(image).text((40, 160), f"Exposure multiplier: {float(pixels[0, 0, 0]):.7g}", fill="white")
        return np.asarray(image)
    if name in PT_MOTION_NAMES:
        # XY are screen-space pixel displacement; MotionWorld remains in scene units.
        padded = np.zeros((*pixels.shape[:2], 4), dtype=np.float32)
        padded[..., :min(3, pixels.shape[-1])] = pixels[..., :min(3, pixels.shape[-1])]
        padded[..., 3] = 1
        if name == "MotionWorld":
            # World displacement is in scene units; normalize XY magnitude for this preview.
            magnitude = np.linalg.norm(padded[..., :2], axis=-1)
            scale = max(float(np.percentile(magnitude[magnitude > 0], 99)), 1e-6) if np.any(magnitude > 0) else 1
            padded[..., :2] *= 20 / scale
        return _visualize_motion(padded)
    if "Normal" in name or name == "ReflectionsFirstBounceRayDirAndHitT":
        return _to_uint8_image(np.clip(pixels[..., :3] * .5 + .5, 0, 1))
    if name in ("PtWorldPos", "ViewspacePosition", "Camera3dPositionSD"):
        rgb = pixels[..., :3]
        lo, hi = np.nanpercentile(rgb, [1, 99], axis=(0, 1))
        return _to_uint8_image(np.clip((rgb - lo) / np.maximum(hi - lo, 1e-6), 0, 1))
    if name == "Roughness":
        return _to_uint8_image(np.repeat(pixels[..., 2:3], 3, axis=-1))
    if pixels.shape[-1] == 1 or name == "PtZDepth":
        scalar = pixels[..., 0]
        valid = np.isfinite(scalar) & (np.abs(scalar) < 1e30)
        lo, hi = np.percentile(scalar[valid], [1, 99]) if np.any(valid) else (0, 1)
        gray = np.clip((np.where(valid, scalar, lo) - lo) / max(float(hi - lo), 1e-6), 0, 1)
        if name in ("DisocclusionMask", "HighResDisocclusionMask", "ReprojectionQuality"):
            gray = np.clip(scalar, 0, 1)
        return _to_uint8_image(np.repeat(gray[..., None], 3, axis=-1))
    if values.dtype == np.uint8 or "Filter" in name or name.startswith("PtMultiMatte"):
        return _to_uint8_image(pixels[..., :3])
    if name in {"PtLuminance", "PtIlluminance", "DiffuseLightingDirectAndIndirect",
                "SpecularLightingDirectAndIndirect", "LightingComposited"}:
        # Photometric and filter-free lighting have different ranges from beauty radiance.
        # Log compression retains both bright highlights and darker geometry in their previews.
        rgb = np.log1p(np.maximum(pixels[..., :3], 0))
        scale = max(float(np.percentile(rgb, 99)), 1e-6)
        return _to_uint8_image(np.clip(rgb / scale, 0, 1))
    # Radiance components use a common exposure from HdrColor and an sRGB display transfer.
    rgb = np.maximum(pixels[..., :3] * exposure, 0)
    rgb = np.where(rgb <= .0031308, 12.92 * rgb, 1.055 * np.power(rgb, 1 / 2.4) - .055)
    return _to_uint8_image(np.clip(rgb, 0, 1))


def capture_pt_lineup(args) -> None:
    """Save PT static outputs before robot motion, then replace only motion previews."""
    import rerun as rr
    output_dir = EXAMPLE_DIR / "_output" / "pt"
    output_dir.mkdir(parents=True, exist_ok=True)
    rr.init("ovrtx_path_tracing_aovs", spawn=not args.no_spawn)
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.path-tracing-aovs")
    renderer.attach_ovstage(stage)
    report = {}
    tensors = {}
    try:
        layer = build_pt_render_layer_usda(_scene_asset_path(args.usd), tuple(args.resolution), args.samples_per_pixel)
        ovstage.population.open_usd_from_string(stage, layer, ordinal=1)
        stage.advance_write_floor(1, ovstage.Scope.ALL).wait()
        names = list(dict.fromkeys(PT_AOV_NAMES + re.findall(r'string sourceName = "(\w+)"', build_render_layer_usda(_scene_asset_path(args.usd), tuple(args.resolution)))))
        initial_maps = {}
        # PT converges within one frame; RT warmup frames do not apply to this capture.
        products = renderer.step(render_products={"/Render/Camera"}, delta_time=args.step_dt, ordinal=1)
        frame = next(iter(products.values())).frames[0]
        for name in ("StableIdMapDeltas", "SemanticIdMapDeltas"):
            initial_maps[name] = _map_render_var(frame, name)
        # The first step creates renderer instances; selection flags require those instances to exist.
        _select_lineup_robots(renderer, frame)
        del frame, products
        products = renderer.step(render_products={"/Render/Camera"}, delta_time=args.step_dt, ordinal=1)
        frame = next(iter(products.values())).frames[0]
        if not frame.converged:
            raise RuntimeError("PT static frame did not reach the requested sample count")
        print(f"PT static capture: one frame at {args.samples_per_pixel} SPP, converged={frame.converged}, iterations={frame.progression}", file=sys.stderr, flush=True)
        for name in names:
            try:
                values = _map_render_var(frame, name)
                if isinstance(values, dict):
                    # The final PT report must retain diagnostics for the structured .npz outputs too.
                    fields = {key: value for key, value in values.items() if key != "params"}
                    fields.update({"param_" + key: value for key, value in values.get("params", {}).items()})
                    report[name] = {
                        "fields": {
                            key: {"shape": list(value.shape), "dtype": str(value.dtype)}
                            for key, value in fields.items()
                        },
                        "bytes": sum(value.nbytes for value in fields.values()),
                    }
                    continue  # Structured outputs are saved by capture_additional_aovs below.
                tensors[name] = values
                np.save(output_dir / f"{name}.npy", values)
                content = values[..., :min(values.shape[-1], 3)] if values.ndim == 3 else values
                report[name] = {"shape": list(values.shape), "dtype": str(values.dtype), "size": int(values.size),
                                "nonzero_content": int(np.count_nonzero(content)), "nonfinite": int(np.count_nonzero(~np.isfinite(values)))}
            except Exception as exc:
                report[name] = {"error": str(exc)}
        # Shared Synthetic Data decoding and overlays use the same records as the RT capture.
        capture_additional_aovs(rr, frame, initial_maps, output_dir)
        export_aov_pngs(frame, output_dir)
        display_exposure = 1 / max(float(np.percentile(tensors["HdrColor"][..., :3].astype(np.float32), 99)), 1e-6)
        for name in PT_AOV_NAMES:
            values = tensors.get(name)
            if values is None or values.ndim != 3 or not values.size:
                continue
            image = pt_display_image(name, values, display_exposure)
            Image.fromarray(image).save(output_dir / f"{name}.png")
            rr.log(f"render/aovs/{name}/display", rr.Image(image))
        # Use corresponding vertical slices to fit each output family into one table image.
        width, height = args.resolution
        families = [
            ("LightPathExpressions", [f"PtLpe{i}" for i in range(9)],
             [f"{i}: {expression}" for i, expression in enumerate(PT_LPE_EXPRESSIONS)]),
            ("MultiMatte", [f"PtMultiMatte{i}" for i in range(4)],
             [f"{i}: " + "/".join(f"{'M' if material else 'G'}{identifier}"
                                   for identifier, material in PT_MULTIMATTE_CHANNELS[i * 4:i * 4 + 4])
              for i in range(4)]),
        ]
        for filename, outputs, captions in families:
            # Empty buffers cannot produce an illustration; retain them only in capture diagnostics.
            if any(name not in tensors or not tensors[name].size for name in outputs):
                continue
            if filename == "MultiMatte" and any(not np.any(tensors[name][..., channel])
                                                for name in outputs for channel in range(3)):
                print("Multi-Matte has empty masks; skipping its combined preview", file=sys.stderr)
                continue
            # Alpha is independent coverage, not opacity for the RGB mask preview.
            alpha_height = height // 4 if filename == "MultiMatte" else 0
            preview = Image.new("RGB", (width, height + 24 + alpha_height), "#101820")
            labels = ImageDraw.Draw(preview)
            for index, (name, caption) in enumerate(zip(outputs, captions)):
                left, right = index * width // len(outputs), (index + 1) * width // len(outputs)
                with Image.open(output_dir / f"{name}.png") as image:
                    preview.paste(image.crop((left, 0, right, height)), (left, 24))
                labels.text((left + 3, 5), caption, fill="white")
                if alpha_height:
                    alpha = np.rint(np.clip(tensors[name][..., 3], 0, 1) * 255).astype(np.uint8)
                    alpha_image = Image.fromarray(alpha).resize((right - left, alpha_height))
                    preview.paste(alpha_image.convert("RGB"), (left, height + 24))
            preview.save(output_dir / f"{filename}.png")
        del frame, products

        robot_paths = ["/World/GR1T2_fourier_hand_6dof", "/World/spot", "/World/forklift_c", "/World/forklift_b",
                       "/World/carter_v1", "/World/jetbot", "/World/kaya"]
        velocities = np.array([(3,0,0),(-3,0,0),(2,0,1),(-2,0,1),(3,0,1),(-3,0,1),(2,0,1)], dtype=np.float64)
        ordinal = 1
        with ovstage.PathDictionary(stage) as paths:
            path_list = paths.create_path_list_from_strings(robot_paths)
            with stage.query_from_path_list(path_list) as query:
                attribute = paths.intern_token("omni:xform")
                transforms = np.full((len(robot_paths),4,4), np.nan, dtype=np.float64)
                with stage.read_attributes(query, [attribute], ovstage.OrdinalRange.latest(ordinal)) as read:
                    while (group := read.fetch_next()) is not None:
                        column = group.columns[0]
                        values = np.from_dlpack(column.dlpack(0)).reshape(-1,4,4)
                        for i in range(group.prim_count):
                            transforms[group.prim_index(i)] = values[column.data_row_index(i)]
                        del values
                        stage.release_group(group)
                if not np.isfinite(transforms).all():
                    raise RuntimeError("Missing robot transforms for PT motion capture")
                dtype = ovstage.numpy_to_dldatatype(transforms.dtype, lanes=16)
                # Render one moved frame after saving the static outputs.
                transforms[:,3,:3] += velocities * args.step_dt
                ordinal += 1
                tensor = ovstage.make_dltensor(transforms, dtype=dtype, shape=[len(robot_paths)], ndim=1)
                stage.write_attribute(query, attribute, ordinal=ordinal, tensors=tensor, is_array=False).wait()
                stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
                products = renderer.step(render_products={"/Render/Camera"}, delta_time=args.step_dt, ordinal=ordinal)
                frame = next(iter(products.values())).frames[0]
                print(f"PT motion capture: converged={frame.converged}, iterations={frame.progression}", file=sys.stderr, flush=True)
                if not frame.converged:
                    raise RuntimeError("PT motion frame did not reach the requested sample count")
                for name in PT_MOTION_NAMES | {"DisocclusionMask", "HighResDisocclusionMask", "ReprojectionQuality"}:
                    motion = _map_render_var(frame, name)
                    if not motion.size:
                        continue
                    np.save(output_dir / f"{name}.npy", motion)
                    Image.fromarray(pt_display_image(name, motion)).save(output_dir / f"{name}.png")
                    report[name]["motion_nonzero"] = int(np.count_nonzero(motion[..., :2]))
                del frame, products
            paths.destroy_path_list(path_list)
        (output_dir / "capture.json").write_text(json.dumps(report, indent=2) + "\n")
    finally:
        renderer.detach_ovstage()
        stage.destroy()
        renderer.destroy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render semantic segmentation and log it to Rerun.")
    parser.add_argument(
        "--usd",
        type=Path,
        default=DEFAULT_USD,
        help=f"Scene USD to sublayer (default: {DEFAULT_USD})",
    )
    parser.add_argument(
        "--resolution",
        type=int,
        nargs=2,
        metavar=("WIDTH", "HEIGHT"),
        default=(1920, 1080),
        help="Render resolution (default: 1920 1080)",
    )
    parser.add_argument(
        "--warmup-frames",
        type=int,
        default=50,
        help="Frames to render before logging the static AOVs (default: 50)",
    )
    parser.add_argument(
        "--step-dt",
        type=float,
        default=1.0 / 60.0,
        help="Simulation delta time in seconds for each renderer step (default: 1/60)",
    )
    parser.add_argument(
        "--grid-columns",
        type=int,
        default=4,
        help="Number of columns in the Rerun AOV grid blueprint (default: 4)",
    )
    parser.add_argument(
        "--no-spawn",
        action="store_true",
        help="Do not spawn a Rerun viewer; log to an already-running recording stream.",
    )
    parser.add_argument(
        "--render-mode", choices=["RealTimePathTracing", "PathTracing", "MinimalRendering"],
        default="RealTimePathTracing",
    )
    parser.add_argument("--samples-per-pixel", type=int, default=128, help="PT samples per frame (default: 128)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.render_mode == "PathTracing":
        capture_pt_lineup(args)
        return
    scene_path = _resolve_scene_path(args.usd)
    if not scene_path.exists():
        raise SystemExit(f"USD file not found: {scene_path}")
    scene_asset_path = _scene_asset_path(args.usd)
    output_dir = EXAMPLE_DIR / "_output"
    if args.render_mode == "MinimalRendering":
        output_dir /= "minimal"

    try:
        import rerun as rr
        import rerun.blueprint as rrb
    except ImportError as exc:
        raise SystemExit("rerun-sdk is required. Run this example with `uv run main.py`.") from exc

    blueprint = build_aov_blueprint(rrb, max(args.grid_columns, 1))
    rr.init("ovrtx_semantic_segmentation", spawn=not args.no_spawn, default_blueprint=blueprint)
    rr.send_blueprint(blueprint, make_active=True, make_default=True)

    # [snippet:create-renderer]
    print("Creating renderer. First launch can take time while shaders compile...", file=sys.stderr)
    renderer = ovrtx.Renderer()
    stage = ovstage.Stage("ovrtx.example.semantic-segmentation")
    renderer.attach_ovstage(stage)
    print("Renderer created.", file=sys.stderr)
    # [/snippet:create-renderer]

    # [snippet:open-sublayered-usd]
    print(f"Opening composed scene with sublayer: {scene_asset_path}", file=sys.stderr)
    ordinal = 1
    ovstage.population.open_usd_from_string(
        stage,
        build_render_layer_usda(scene_asset_path, tuple(args.resolution), args.render_mode),
        ordinal=ordinal,
    )
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    print("USD loaded.", file=sys.stderr)
    # [/snippet:open-sublayered-usd]

    render_product_path = "/Render/Camera"
    step_dt = args.step_dt
    sim_step = 0
    sim_time = 0.0

    initial_maps = {}
    for frame_index in range(max(args.warmup_frames, 0)):
        print(f"Warming up frame {frame_index + 1}/{args.warmup_frames}...", file=sys.stderr)
        warmup_products = renderer.step(render_products={render_product_path}, delta_time=step_dt, ordinal=ordinal)
        if frame_index == 0:
            # Delta maps report newly introduced IDs; save scene creation before warmup consumes the changes.
            for warmup_product in warmup_products.values():
                for warmup_frame in warmup_product.frames:
                    for name in ("StableIdMapDeltas", "SemanticIdMapDeltas"):
                        values = _map_render_var(warmup_frame, name)
                        initial_maps[name] = values
                        initial_dir = output_dir / "initial"
                        initial_dir.mkdir(parents=True, exist_ok=True)
                        np.savez(initial_dir / f"{name}.npz", **values)
                    if args.render_mode != "MinimalRendering":
                        _select_lineup_robots(renderer, warmup_frame)
            del warmup_frame, warmup_product
        del warmup_products
        sim_step += 1
        sim_time = sim_step * step_dt

    # Even with warmup disabled, capture the path map once before selecting geometry.
    if args.render_mode != "MinimalRendering" and args.warmup_frames <= 0:
        setup_products = renderer.step(render_products={render_product_path}, delta_time=step_dt, ordinal=ordinal)
        _select_lineup_robots(renderer, next(iter(setup_products.values())).frames[0])
        del setup_products

    # [snippet:step-all-aovs]
    print("Rendering camera AOVs...", file=sys.stderr)
    products = renderer.step(
        render_products={render_product_path},
        delta_time=step_dt,
        ordinal=ordinal,
    )
    # [/snippet:step-all-aovs]
    sim_step += 1
    sim_time = sim_step * step_dt

    logged = 0
    for product_name, product in products.items():
        print(f"Processing {product_name}...", file=sys.stderr)
        for frame in product.frames:
            rr.set_time("sim_time", duration=sim_time)
            rr.set_time("step", sequence=sim_step)
            logged += log_aovs_to_rerun(rr, frame)
            logged += capture_additional_aovs(rr, frame, initial_maps, output_dir)
            if args.no_spawn:
                exported = export_aov_pngs(frame, output_dir)
                print(f"  Wrote {exported} AOV PNGs to {output_dir}", file=sys.stderr)

    # Release the static capture before moving anything. Only TargetMotionSD is logged/exported below.
    del frame, product, products
    robot_paths = [
        "/World/GR1T2_fourier_hand_6dof", "/World/spot", "/World/forklift_c", "/World/forklift_b",
        "/World/carter_v1", "/World/jetbot", "/World/kaya",
    ]
    # Different directions distinguish the robots; upward offsets keep the small robots above the floor.
    velocities = np.array(
        [(3, 0, 0), (-3, 0, 0), (2, 0, 1), (-2, 0, 1), (3, 0, 1), (-3, 0, 1), (2, 0, 1)],
        dtype=np.float64,
    )
    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings(robot_paths)
        with stage.query_from_path_list(path_list) as query:
            attribute = paths.intern_token("omni:xform")
            transforms = np.full((len(robot_paths), 4, 4), np.nan, dtype=np.float64)
            # Preserve authored orientation and scale, including the centimetre-scaled forklift payload.
            with stage.read_attributes(query, [attribute], ovstage.OrdinalRange.latest(ordinal)) as read:
                while (group := read.fetch_next()) is not None:
                    column = group.columns[0]
                    values = np.from_dlpack(column.dlpack(0)).reshape(-1, 4, 4)
                    for i in range(group.prim_count):
                        transforms[group.prim_index(i)] = values[column.data_row_index(i)]
                    del values
                    stage.release_group(group)
            if not np.all(np.isfinite(transforms)):
                raise RuntimeError("The motion capture requires transforms for all seven lineup robots.")

            matrix_dtype = ovstage.numpy_to_dldatatype(transforms.dtype, lanes=16)
            for motion_step in range(10):
                # Alternate between the rest pose and a small offset so every robot stays in the camera frame.
                direction = 1.0 if motion_step % 2 == 0 else -1.0
                transforms[:, 3, :3] += direction * velocities * step_dt
                ordinal += 1
                matrix_tensor = ovstage.make_dltensor(transforms, dtype=matrix_dtype, shape=[len(robot_paths)], ndim=1)
                stage.write_attribute(query, attribute, ordinal=ordinal, tensors=matrix_tensor, is_array=False).wait()
                stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
                products = renderer.step(render_products={render_product_path}, delta_time=step_dt, ordinal=ordinal)
                sim_step += 1
                sim_time = sim_step * step_dt
                print(f"Moving robots: frame {motion_step + 1}/10...", file=sys.stderr)
        paths.destroy_path_list(path_list)

    for product in products.values():
        for frame in product.frames:
            motion = _map_render_var(frame, "TargetMotionSD")
            display = _visualize_motion(motion)
            rr.set_time("sim_time", duration=sim_time)
            rr.set_time("step", sequence=sim_step)
            _log_raw_tensor(rr, "TargetMotionSD", motion)
            rr.log("render/aovs/TargetMotionSD/display", rr.Image(display))
            _print_logged("TargetMotionSD", motion)
            logged += 1
            if args.no_spawn:
                display_path = output_dir / "TargetMotionSD.png"
                # Retain the raw vectors and flags beside the display image for quantitative inspection.
                np.save(display_path.with_suffix(".npy"), motion)
                Image.fromarray(display).save(display_path)
                print(f"  Wrote motion PNG to {display_path}", file=sys.stderr)

    print(f"Logged {logged} AOVs to Rerun.", file=sys.stderr)
    del frame, product, products
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


if __name__ == "__main__":
    main()
