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
import os
import sys
from pathlib import Path

import numpy as np
import ovrtx
import ovstage

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
def build_render_layer_usda(scene_path: Path, resolution: tuple[int, int]) -> str:
    """Compose the robot scene and author a RenderProduct with each requested camera AOV."""
    width, height = resolution
    source_scene = _usd_asset_path(scene_path)

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
        token omni:rtx:rendermode = "RealTimePathTracing"
        rel orderedVars = [
            <LdrColor>,
            <HdrColor>,
            <NormalSD>,
            <DepthSD>,
            <DistanceToCameraSD>,
            <DistanceToImagePlaneSD>,
            <DiffuseAlbedoSD>,
            <Camera3dPositionSD>,
            <SemanticSegmentation>,
            <SemanticIdMap>
        ]

        def RenderVar "LdrColor" {{
            string sourceName = "LdrColor"
        }}

        def RenderVar "HdrColor" {{
            string sourceName = "HdrColor"
        }}

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

        def RenderVar "SemanticSegmentation" {{
            string sourceName = "SemanticSegmentation"
        }}

        def RenderVar "SemanticIdMap" {{
            string sourceName = "SemanticIdMap"
        }}
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


def build_aov_blueprint(rrb, grid_columns: int):
    return rrb.Blueprint(
        rrb.Grid(
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/LdrColor/display", name="LdrColor"),
            rrb.Spatial2DView(origin="/", contents="+/render/aovs/HdrColor/display", name="HdrColor"),
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
            grid_columns=grid_columns,
            name="Camera AOVs",
        ),
        rrb.TimePanel(timeline="sim_time"),
        collapse_panels=True,
    )


def _map_render_var(frame, name: str) -> np.ndarray:
    mapped = frame.render_vars[name].map(device=ovrtx.Device.CPU)
    view = np.from_dlpack(mapped)
    pixels = view.copy()
    del view, mapped
    return pixels


def _log_raw_tensor(rr, name: str, pixels: np.ndarray) -> None:
    if hasattr(rr, "Tensor"):
        rr.log(f"render/aovs/{name}/raw", rr.Tensor(np.ascontiguousarray(pixels)))


def _print_logged(name: str, pixels: np.ndarray) -> None:
    print(f"  Logged {name}: shape={pixels.shape}, dtype={pixels.dtype}", file=sys.stderr)


def _print_missing(name: str) -> None:
    print(f"  Missing AOV: {name}", file=sys.stderr)


def _decode_id_map(tensor: np.ndarray) -> dict[bytes, str]:
    """Decode an RT2 IdentifierMap render var into raw ID bytes mapped to labels."""
    # SemanticIdMap is a byte buffer, not an image. It contains:
    #
    #   IdentifierMap entries:
    #     uint32 id[4]         16-byte identifier, with semantic IDs in id[0]
    #     uint32 labelLength   byte length of the UTF-8 label
    #     uint32 labelOffset   byte offset of the label inside this same buffer
    #   packed label bytes
    #   uint32 numEntries      stored in the final 4 bytes
    #
    # Keep IDs as their raw 16 bytes so they can be compared directly with the
    # zero-extended SemanticSegmentation pixel IDs below.
    data = np.ascontiguousarray(tensor).view(np.uint8).reshape(-1)
    if data.size < 4:
        return {}

    entry_data_type = np.dtype(
        [("id", "<u4", (4)), ("label_length", "<u4"), ("label_offset", "<u4")]
    )

    num_entries = int.from_bytes(data[-4:].tobytes(), byteorder="little")
    entry_data_length = num_entries * entry_data_type.itemsize
    if entry_data_length > data.size - 4:
        raise ValueError(
            f"ID map declares {num_entries} entries, but the tensor has only {data.size} bytes"
        )

    entries = data[:entry_data_length].view(entry_data_type).reshape(num_entries)
    mapping: dict[bytes, str] = {}
    for entry in entries:
        id_bytes = entry["id"].tobytes()
        label_offset = int(entry["label_offset"])
        label_length = int(entry["label_length"])
        label_end = label_offset + label_length
        if label_end > data.size:
            id_text = f"0x{int.from_bytes(id_bytes, byteorder='little'):032x}"
            raise ValueError(f"ID map label for {id_text} extends past the tensor")

        label = data[label_offset:label_end].tobytes().decode("utf-8", errors="replace")
        mapping[id_bytes] = label.rstrip("\x00").rstrip()

    return mapping


def _map_id_map(frame, name: str) -> dict[bytes, str]:
    mapped = frame.render_vars[name].map(device=ovrtx.Device.CPU)
    view = np.from_dlpack(mapped)
    tensor = view.copy()
    del view, mapped
    return _decode_id_map(tensor)


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
    # are stored in 16-byte IdentifierMap slots, so allocate a compact uint16
    # class ID for each map entry and log the reverse lookup through
    # AnnotationContext.
    #
    # Python dicts preserve insertion order. That order is the order authored by
    # the IdentifierMap buffer, so class ID 0 corresponds to the first map entry,
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

    if "SemanticIdMap" in frame.render_vars:
        semantic_id_map = _map_id_map(frame, "SemanticIdMap")
        _print_logged_id_map("SemanticIdMap", semantic_id_map)
        logged += 1
    else:
        _print_missing("SemanticIdMap")

    if "LdrColor" in frame.render_vars:
        ldr_color = _map_render_var(frame, "LdrColor")
        _log_raw_tensor(rr, "LdrColor", ldr_color)
        rr.log("render/aovs/LdrColor/display", rr.Image(np.ascontiguousarray(ldr_color)))
        _print_logged("LdrColor", ldr_color)
        logged += 1
    else:
        _print_missing("LdrColor")

    if "HdrColor" in frame.render_vars:
        hdr_color = _map_render_var(frame, "HdrColor")
        _log_raw_tensor(rr, "HdrColor", hdr_color)
        rr.log("render/aovs/HdrColor/display", rr.Image(_visualize_hdr(hdr_color)))
        _print_logged("HdrColor", hdr_color)
        logged += 1
    else:
        _print_missing("HdrColor")

    if "NormalSD" in frame.render_vars:
        normal_sd = _map_render_var(frame, "NormalSD")
        _log_raw_tensor(rr, "NormalSD", normal_sd)
        rr.log("render/aovs/NormalSD/display", rr.Image(_visualize_normal(normal_sd)))
        _print_logged("NormalSD", normal_sd)
        logged += 1
    else:
        _print_missing("NormalSD")

    if "DepthSD" in frame.render_vars:
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

    if "DistanceToCameraSD" in frame.render_vars:
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

    if "DistanceToImagePlaneSD" in frame.render_vars:
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

    if "DiffuseAlbedoSD" in frame.render_vars:
        diffuse_albedo = _map_render_var(frame, "DiffuseAlbedoSD")
        _log_raw_tensor(rr, "DiffuseAlbedoSD", diffuse_albedo)
        rr.log("render/aovs/DiffuseAlbedoSD/display", rr.Image(np.ascontiguousarray(diffuse_albedo)))
        _print_logged("DiffuseAlbedoSD", diffuse_albedo)
        logged += 1
    else:
        _print_missing("DiffuseAlbedoSD")

    if "Camera3dPositionSD" in frame.render_vars:
        camera_position = _map_render_var(frame, "Camera3dPositionSD")
        _log_raw_tensor(rr, "Camera3dPositionSD", camera_position)
        rr.log("render/aovs/Camera3dPositionSD/display", rr.Image(_visualize_vector3(camera_position)))
        _print_logged("Camera3dPositionSD", camera_position)
        logged += 1
    else:
        _print_missing("Camera3dPositionSD")

    if "SemanticSegmentation" in frame.render_vars:
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
    from PIL import Image

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
        "NormalSD": normal_to_uint8,
        "DepthSD": turbo_colormap,
        "DistanceToCameraSD": turbo_colormap,
        "DistanceToImagePlaneSD": turbo_colormap,
        "DiffuseAlbedoSD": rgba_or_rgb_uint8,
        "Camera3dPositionSD": normalize_vector3,
        "SemanticSegmentation": hashed_id_colors,
    }

    exported = 0
    for name, converter in converters.items():
        if name not in frame.render_vars:
            continue

        pixels = _map_render_var(frame, name)
        save_png(name, converter(pixels))
        exported += 1

    return exported


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
        default=5,
        help="Frames to render before logging the final AOVs (default: 5)",
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scene_path = _resolve_scene_path(args.usd)
    if not scene_path.exists():
        raise SystemExit(f"USD file not found: {scene_path}")
    scene_asset_path = _scene_asset_path(args.usd)

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
        build_render_layer_usda(scene_asset_path, tuple(args.resolution)),
        ordinal=ordinal,
    )
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()
    print("USD loaded.", file=sys.stderr)
    # [/snippet:open-sublayered-usd]

    render_product_path = "/Render/Camera"
    step_dt = args.step_dt
    sim_step = 0
    sim_time = 0.0

    for frame_index in range(max(args.warmup_frames, 0)):
        print(f"Warming up frame {frame_index + 1}/{args.warmup_frames}...", file=sys.stderr)
        renderer.step(render_products={render_product_path}, delta_time=step_dt, ordinal=ordinal)
        sim_step += 1
        sim_time = sim_step * step_dt

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
            if args.no_spawn:
                exported = export_aov_pngs(frame, EXAMPLE_DIR / "_output")
                print(f"  Wrote {exported} AOV PNGs to {EXAMPLE_DIR / '_output'}", file=sys.stderr)

    print(f"Logged {logged} AOVs to Rerun.", file=sys.stderr)
    del frame, product, products
    renderer.detach_ovstage()
    stage.destroy()
    renderer.destroy()


if __name__ == "__main__":
    main()
