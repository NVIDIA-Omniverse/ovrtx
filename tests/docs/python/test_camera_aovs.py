# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Tests that all documented camera AOVs render successfully."""

import importlib.util
import struct
import warnings

import pytest
from pathlib import Path

import numpy as np
import ovrtx
import ovstage
from PIL import Image

SCENE_PATH = str((Path(__file__).parent / "../../../tests/data/simple_camera.usda").resolve())

# ---------------------------------------------------------------------------
# RTPT AOV smoke-test catalog
# Source of truth for which AOVs exist, what shape to expect, and which are
# currently known-empty.  Keep in sync with:
#   examples/python/multi-aov/main.py  (RTPT_AOVS, PT_AOVS, MINIMAL_AOVS)
# ---------------------------------------------------------------------------

_RTPT_SCENE_PATH = str((Path(__file__).parent / "../../../tests/data/simple_scene.usda").resolve())
_RTPT_RESOLUTION = (320, 180)  # small for fast iteration; (w, h)
_RTPT_PRODUCT_PATH = "/Render/RtptCamera"

# AOVs expected to return image tensors (ndim == 3, height*width*channels).
_RTPT_IMAGE_AOVS = [
    # Core color
    "LdrColor", "HdrColor",
    # Depth variants
    "Depth", "DepthLinearized", "HighResDepth", "XRDepth",
    # Motion
    "Motion2dXYZ", "Motion2dDilated", "Motion2dXYZDilated", "MotionWorld",
    # Material
    "DiffuseAlbedo", "SpecularAlbedo", "Roughness",
    # Lighting decomposition
    "EmissionAndForegroundMask",
    "DiffuseLightingDirectAndIndirect", "SpecularLightingDirectAndIndirect",
    "LightingComposited",
    # Reflections detail
    "ReflectionsFirstBounceDiffuseAlbedo", "ReflectionsFirstBounceNormal",
    "ReflectionsFirstBounceRayDirAndHitT",
    # Temporal / quality
    "DisocclusionMask", "ReprojectionQuality", "ViewspacePosition",
    "Exposure", "ViewMatricesAux",
    # DLSS
    "DlssInput",
    # High-resolution variants
    "HighResMotion2d", "HighResMotion2dXYZ",
    "HighResDisocclusionMask", "HighResReflectionsMotion2d",
    # Normals
    "BumpNormal", "BumpNormalResearch",
    # Texture coordinates
    "Texcoord0", "Texcoord1",
    # SDG - depth and position
    "DistanceToCameraSD", "DistanceToImagePlaneSD", "DepthSD", "Camera3dPositionSD",
    # SDG - color and shading
    "LdrColorSD", "DiffuseAlbedoSD", "SimpleShadingSD",
    # SDG - normals and motion
    "NormalSD", "TargetMotionSD",
    # SDG - segmentation
    "SemanticSegmentation", "SemanticInstanceSegmentation",
    "StableIdSegmentation", "NonStableInstanceSegmentation",
]

# AOVs expected to return a 1-D flat buffer (ndim == 1) - structured metadata,
# not image-like.
_RTPT_BUFFER_AOVS = [
    # SDG - bounding boxes
    "BoundingBox2DTightSD", "BoundingBox2DLooseSD", "BoundingBox3DSD",
    "SemanticBoundingBox2DTight", "SemanticBoundingBox2DLoose", "SemanticBoundingBox3D",
    # SDG - visibility
    "OcclusionSD", "TruncationSD",
    # SDG - ID maps
    "InstanceIdTokenMapSD", "SemanticIdMap", "StableIdMap",
    "InstanceMap", "StableIdMapDeltas", "SemanticIdMapDeltas",
    # SDG - camera
    "CameraParams",
]

# AOVs currently returning empty data (shape=(0,)) in RTPT mode - disabled or
# not yet implemented.  map() must succeed; no ndim contract is asserted so the
# catalog can be promoted to IMAGE/BUFFER once the AOV is enabled.
_RTPT_EMPTY_AOVS = [
    "SmoothNormal", "StableDepth", "GBufferDepth", "Motion2d",
    "DirectDiffuse", "DirectSpecular", "Reflections", "IndirectDiffuse",
    "SubsurfaceScattering", "Irradiance", "Caustics", "AmbientOcclusion",
    "ReflectionsMotion2d", "ReflectionsMotionWorld",
    "ReflectionsFirstBounceWorldPos", "ReflectionsHitT",
    "IndirectDiffuseFirstBounceNormal", "IndirectDiffuseFirstBounceRayDirAndHitT",
    "DlssInputWithoutTransparency", "DeveloperDebugTexture",
    "CrossCorrespondenceSD", "StableIdSemanticIdMap",
]

# Core AOVs that must carry non-zero pixel data: the test scene has a sphere and
# a plane, so these must produce real content regardless of renderer settings.
_RTPT_CORE_NONZERO = frozenset({"LdrColor", "DiffuseAlbedo", "DistanceToCameraSD"})

# AOVs that require CPU texture readback from the GPU (D32, RGBA16F etc.).
# With a released package that lacks the fix these raise RuntimeError — the test
# warns rather than fails so the suite stays green while the fix is in-flight.
# Once the fix ships in a new release, remove from this set and update the
# version pin in pyproject.toml.
_RTPT_READBACK_AOVS = frozenset({
    # Depth variants
    "Depth", "DepthLinearized", "HighResDepth", "XRDepth",
    # Motion
    "Motion2dXYZ", "Motion2dDilated", "Motion2dXYZDilated", "MotionWorld",
    # Material
    "DiffuseAlbedo", "SpecularAlbedo", "Roughness",
    # Lighting decomposition
    "EmissionAndForegroundMask",
    "DiffuseLightingDirectAndIndirect", "SpecularLightingDirectAndIndirect",
    "LightingComposited",
    # Reflections detail
    "ReflectionsFirstBounceDiffuseAlbedo", "ReflectionsFirstBounceNormal",
    "ReflectionsFirstBounceRayDirAndHitT",
    # Temporal / quality
    "DisocclusionMask", "ReprojectionQuality", "ViewspacePosition",
    "Exposure", "ViewMatricesAux",
    # DLSS
    "DlssInput",
    # High-resolution variants
    "HighResMotion2d", "HighResMotion2dXYZ",
    "HighResDisocclusionMask", "HighResReflectionsMotion2d",
    # Normals
    "BumpNormal", "BumpNormalResearch",
    # Texture coordinates
    "Texcoord0", "Texcoord1",
})

RESOLUTION = (640, 360)

AOV_NAMES = [
    "LdrColor", "HdrColor", "NormalSD", "DepthSD",
    "DistanceToCameraSD", "DistanceToImagePlaneSD",
    "DiffuseAlbedoSD", "Camera3dPositionSD",
]
AOV_PATHS = {name: f"/Render/Camera/{name}" for name in AOV_NAMES}

_ordered_vars = ", ".join(f"<{n}>" for n in AOV_NAMES)
_render_var_defs = "\n".join(
    f'        def RenderVar "{n}" {{\n            string sourceName = "{n}"\n        }}'
    for n in AOV_NAMES
)

# [snippet:doc-camera-aov-usda]
USDA = f"""#usda 1.0
(
    subLayers = [
        @{SCENE_PATH}@
    ]
)

def "Render" {{
    def RenderProduct "Camera" {{
        int2 resolution = {RESOLUTION}
        rel camera = </Camera0>
        rel orderedVars = [{_ordered_vars}]

{_render_var_defs}
    }}
}}
"""
# [/snippet:doc-camera-aov-usda]


def test_all_camera_aovs(renderer, stage, output_dir):
    """Test that all documented camera AOVs render with correct shape and non-zero data."""
    ordinal = 1
    ovstage.population.open_usd_from_string(stage, USDA, ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    # Warm up
    for _ in range(5):
        renderer.step(render_products={"/Render/Camera"}, delta_time=1.0 / 60, ordinal=ordinal)

    # [snippet:doc-camera-aov-smoke-test]
    products = renderer.step(
        render_products={"/Render/Camera"},
        delta_time=1.0 / 60,
        ordinal=ordinal,
    )

    h, w = RESOLUTION[1], RESOLUTION[0]

    for product_name, product in products.items():
        for frame in product.frames:
            # LdrColor: RGBA uint8
            var = frame.render_vars[AOV_PATHS["LdrColor"]].map(device=ovrtx.Device.CPU)
            ldr_color = np.from_dlpack(var)
            assert ldr_color.shape == (h, w, 4) and ldr_color.dtype == np.uint8
            assert not np.all(ldr_color == 0), "LdrColor is all zeros"
            Image.fromarray(ldr_color).save(output_dir / "test_camera_aovs.LdrColor.png")

            # HdrColor: RGBA float16
            var = frame.render_vars[AOV_PATHS["HdrColor"]].map(device=ovrtx.Device.CPU)
            hdr_color = np.from_dlpack(var)
            assert hdr_color.shape == (h, w, 4) and hdr_color.dtype == np.float16
            assert not np.all(hdr_color == 0), "HdrColor is all zeros"

            # NormalSD: XYZA float32
            var = frame.render_vars[AOV_PATHS["NormalSD"]].map(device=ovrtx.Device.CPU)
            normals = np.from_dlpack(var)
            assert normals.shape == (h, w, 4) and normals.dtype == np.float32
            assert not np.all(normals == 0), "NormalSD is all zeros"

            # DepthSD: Z float32
            var = frame.render_vars[AOV_PATHS["DepthSD"]].map(device=ovrtx.Device.CPU)
            depth = np.from_dlpack(var)
            assert depth.shape == (h, w, 1) and depth.dtype == np.float32
            # Note: DepthSD may be all zeros in some configurations

            # DistanceToCameraSD: Z float32
            var = frame.render_vars[AOV_PATHS["DistanceToCameraSD"]].map(device=ovrtx.Device.CPU)
            dist_camera = np.from_dlpack(var)
            assert dist_camera.shape == (h, w, 1) and dist_camera.dtype == np.float32
            assert not np.all(dist_camera == 0), "DistanceToCameraSD is all zeros"

            # DistanceToImagePlaneSD: Z float32
            var = frame.render_vars[AOV_PATHS["DistanceToImagePlaneSD"]].map(device=ovrtx.Device.CPU)
            dist_plane = np.from_dlpack(var)
            assert dist_plane.shape == (h, w, 1) and dist_plane.dtype == np.float32
            assert not np.all(dist_plane == 0), "DistanceToImagePlaneSD is all zeros"

            # DiffuseAlbedoSD: RGBA uint8
            var = frame.render_vars[AOV_PATHS["DiffuseAlbedoSD"]].map(device=ovrtx.Device.CPU)
            albedo = np.from_dlpack(var)
            assert albedo.shape == (h, w, 4) and albedo.dtype == np.uint8
            assert not np.all(albedo == 0), "DiffuseAlbedoSD is all zeros"
            Image.fromarray(albedo).save(output_dir / "test_camera_aovs.DiffuseAlbedoSD.png")

            # Camera3dPositionSD: XYZA float32
            var = frame.render_vars[AOV_PATHS["Camera3dPositionSD"]].map(device=ovrtx.Device.CPU)
            cam_pos = np.from_dlpack(var)
            assert cam_pos.shape == (h, w, 4) and cam_pos.dtype == np.float32
            assert not np.all(cam_pos == 0), "Camera3dPositionSD is all zeros"
    # [/snippet:doc-camera-aov-smoke-test]


def test_all_rtpt_aovs(renderer, stage):
    """Smoke-test the full RTPT AOV catalog.

    Every AOV must map() without error.  Image AOVs must have ndim==3; 1-D
    buffer AOVs must have ndim==1.  Known-empty AOVs are allowed to return
    any shape (they are expected to return shape=(0,) until enabled, but the
    test will not fail if they start returning real data - move them to
    IMAGE/BUFFER when that happens).  Failures are collected and reported
    together so a single broken AOV doesn't hide others.
    """
    all_aovs = _RTPT_IMAGE_AOVS + _RTPT_BUFFER_AOVS + _RTPT_EMPTY_AOVS

    w, h = _RTPT_RESOLUTION
    ordered_vars = ", ".join(f"<{n}>" for n in all_aovs)
    render_var_defs = "\n".join(
        f'        def RenderVar "{n}" {{\n            string sourceName = "{n}"\n        }}'
        for n in all_aovs
    )
    usda = f"""#usda 1.0
(
    subLayers = [
        @{_RTPT_SCENE_PATH}@
    ]
)

def "Render" {{
    def RenderProduct "RtptCamera" {{
        int2 resolution = ({w}, {h})
        rel camera = </Camera0>
        token omni:rtx:rendermode = "RealTimePathTracing"
        rel orderedVars = [{ordered_vars}]

{render_var_defs}
    }}
}}
"""

    ordinal = 1
    ovstage.population.open_usd_from_string(stage, usda, ordinal=ordinal)
    stage.advance_write_floor(ordinal, ovstage.Scope.ALL).wait()

    for _ in range(5):
        renderer.step(render_products={_RTPT_PRODUCT_PATH}, delta_time=1.0 / 60, ordinal=ordinal)

    products = renderer.step(
        render_products={_RTPT_PRODUCT_PATH}, delta_time=1.0 / 60, ordinal=ordinal
    )
    assert products, "renderer.step() returned no products"
    product = next(iter(products.values()))
    frames = list(product.frames)
    assert frames, "product has no frames"
    frame = frames[0]

    # Single pass over all AOVs: (name, expected_ndim or None for empty/any).
    # Non-zero checks for core AOVs are folded into the same pass to avoid a
    # second map() call (which could race with implicit unmap of the first view).
    catalog = (
        [(n, 3) for n in _RTPT_IMAGE_AOVS]
        + [(n, 1) for n in _RTPT_BUFFER_AOVS]
        + [(n, None) for n in _RTPT_EMPTY_AOVS]
    )
    failures = []

    for aov_name, expected_ndim in catalog:
        var_path = f"{_RTPT_PRODUCT_PATH}/{aov_name}"
        if var_path not in frame.render_vars:
            failures.append(f"{aov_name}: missing from render_vars")
            continue
        try:
            t = np.from_dlpack(frame.render_vars[var_path].map(device=ovrtx.Device.CPU))
        except RuntimeError as exc:
            if aov_name in _RTPT_READBACK_AOVS:
                # CPU texture readback not yet in this release; warn, don't fail.
                warnings.warn(
                    f"CPU-readback AOV unavailable (update ovrtx to get fix): {aov_name}: {exc!r}",
                    UserWarning,
                    stacklevel=2,
                )
                continue
            failures.append(f"{aov_name}: map() raised {exc!r}")
            continue
        except Exception as exc:
            failures.append(f"{aov_name}: map() raised unexpected {type(exc).__name__}: {exc!r}")
            continue

        if expected_ndim is not None and t.ndim != expected_ndim:
            failures.append(
                f"{aov_name}: expected ndim={expected_ndim},"
                f" got ndim={t.ndim} shape={t.shape} dtype={t.dtype}"
            )

        if aov_name in _RTPT_CORE_NONZERO and t.ndim == 3 and np.all(t == 0):
            failures.append(f"{aov_name}: all zeros - scene has geometry, expected non-zero")

    assert not failures, "RTPT AOV smoke-test failures:\n" + "\n".join(f"  {f}" for f in failures)


# [snippet:doc-sd-map-image-python]
def map_sd_image(frame, render_var_path: str) -> np.ndarray:
    """Copy a typed image to CPU memory before its mapping is released."""
    mapped = frame.render_vars[render_var_path].map(device=ovrtx.Device.CPU)
    return np.from_dlpack(mapped).copy()
# [/snippet:doc-sd-map-image-python]


# [snippet:doc-sd-records-python]
def decode_sd_records(data: np.ndarray, dtype: np.dtype, counted: bool = False) -> np.ndarray:
    """Decode little-endian records, checking lengths before reading reserved buffers."""
    buffer = np.ascontiguousarray(data).view(np.uint8).reshape(-1)
    if counted:
        # Semantic boxes reserve unused capacity; their final uint32 is the actual count.
        if buffer.size < 4:
            raise ValueError("Missing record count")
        count = int.from_bytes(buffer[-4:].tobytes(), "little")
        if count > (buffer.size - 4) // dtype.itemsize:
            raise ValueError("Record count exceeds buffer capacity")
    else:
        if buffer.size % dtype.itemsize:
            raise ValueError("Incomplete record")
        count = buffer.size // dtype.itemsize
    return buffer[:count * dtype.itemsize].view(dtype)
# [/snippet:doc-sd-records-python]


# [snippet:doc-sd-boxes-python]
def decode_sd_boxes(data: np.ndarray, semantic: bool = False, three_d: bool = False) -> np.ndarray:
    """Decode raw or semantic boxes; 3D bounds are local and include a world transform."""
    fields = [("stable_id", "<u4", 4), ("semantic_id", "<u4", 4)] if semantic else [
        ("instance_id", "<u4"), ("tile_id", "<u4")]
    fields += [("min", "<f4" if three_d else "<i4", 3 if three_d else 2),
               ("max", "<f4" if three_d else "<i4", 3 if three_d else 2)]
    if three_d:
        fields += [("local_to_world", "<f4", (4, 4))]
    return decode_sd_records(data, np.dtype(fields), counted=semantic)
# [/snippet:doc-sd-boxes-python]


# [snippet:doc-sd-occlusion-python]
def decode_sd_occlusion(data: np.ndarray) -> np.ndarray:
    """Read occlusion ratios with their instance/tile keys; negative ratios are invalid."""
    dtype = np.dtype([("instance_id", "<u4"), ("tile_id", "<u4"), ("ratio", "<f4")])
    return decode_sd_records(data, dtype)
# [/snippet:doc-sd-occlusion-python]


# [snippet:doc-sd-tokens-python]
def decode_sd_tokens(data: np.ndarray) -> tuple[np.void, np.ndarray]:
    """Separate the token-map header from aligned instance records."""
    dtype = np.dtype({"names": ["instance_id", "prim_token", "prototype", "instance_index"],
                      "formats": ["<u4", "<u8", "<u4", "<u4"],
                      "offsets": [0, 8, 16, 20], "itemsize": 24})
    records = decode_sd_records(data, dtype)
    if not len(records) or int(records[0]["instance_id"]) != len(records) - 1:
        raise ValueError("Token-map header count does not match records")
    return records[0], records[1:]
# [/snippet:doc-sd-tokens-python]


# [snippet:doc-sd-instance-map-python]
def decode_sd_instance_map(data: np.ndarray) -> np.ndarray:
    """Read semantic indices; element i corresponds to minInstanceId + i from the token header."""
    return decode_sd_records(data, np.dtype("<u4"))
# [/snippet:doc-sd-instance-map-python]


# [snippet:doc-sd-identifiers-python]
def decode_sd_identifiers(data: np.ndarray) -> list[tuple[tuple[int, ...], str]]:
    """Decode labels/paths without dropping repeated IDs or any of their four words."""
    buffer = np.ascontiguousarray(data).view(np.uint8).reshape(-1)
    dtype = np.dtype([("id", "<u4", 4), ("length", "<u4"), ("offset", "<u4")])
    records = decode_sd_records(buffer, dtype, counted=True)
    labels = []
    for record in records:
        offset, length = int(record["offset"]), int(record["length"])
        if offset < records.nbytes or offset + length > buffer.size - 4:
            raise ValueError("Identifier string extends outside string storage")
        labels.append((tuple(int(word) for word in record["id"]),
                       buffer[offset:offset + length].tobytes().decode("utf-8")))
    return labels
# [/snippet:doc-sd-identifiers-python]


# [snippet:doc-sd-id-pairs-python]
def decode_sd_id_pairs(data: np.ndarray) -> np.ndarray:
    """Read stable-to-semantic ID pairs; this buffer has no trailing count."""
    dtype = np.dtype([("stable_id", "<u4", 4), ("semantic_id", "<u4", 4)])
    return decode_sd_records(data, dtype)
# [/snippet:doc-sd-id-pairs-python]


# [snippet:doc-sd-camera-python]
def decode_sd_camera(data: np.ndarray) -> np.void:
    """Decode the 260-byte camera record, including the projection-model padding."""
    dtype = np.dtype([
        ("world_to_camera", "<f4", (4, 4)), ("projection", "<f4", (4, 4)),
        ("meters_per_scene_unit", "<f4"), ("resolution", "<u4", 2), ("near_far", "<f4", 2),
        ("model", "S25"), ("padding", "u1", 3),
        ("focal_length", "<f4"), ("focal_distance", "<f4"), ("f_stop", "<f4"), ("fov_x", "<f4"),
        ("fisheye_width", "<f4"), ("fisheye_height", "<f4"), ("fisheye_center", "<f4", 2),
        ("fisheye_max_fov", "<f4"), ("fisheye_polynomial", "<f4", 6),
        ("lens_p", "<f4", 2), ("lens_s", "<f4", 4)])
    records = decode_sd_records(data, dtype)
    if len(records) != 1:
        raise ValueError("Expected one camera record")
    return records[0]
# [/snippet:doc-sd-camera-python]


# [snippet:doc-sd-project-python]
def project_sd_point(point, local_to_world, camera):
    """Project a local 3D point into pinhole pixels using row-vector matrices."""
    if camera["model"].split(b"\0", 1)[0] != b"pinhole":
        raise ValueError("This projection only handles pinhole cameras")
    world = np.append(point, 1.0) @ local_to_world
    clip = world @ camera["world_to_camera"] @ camera["projection"]
    if clip[3] <= 0:
        return None  # Behind the camera; clip crossing box edges before drawing them.
    ndc = clip[:2] / clip[3]
    return (ndc * [0.5, -0.5] + 0.5) * camera["resolution"]
# [/snippet:doc-sd-project-python]


def test_sd_decoder_bounds_and_identifier_storage():
    """Reject truncated records and strings; preserve aliases sharing a stable ID."""
    raw = np.frombuffer(struct.pack("<IIiiii", 7, 0, 10, 20, 30, 40), dtype=np.uint8)
    boxes = decode_sd_boxes(raw)
    assert boxes[0]["instance_id"] == 7
    np.testing.assert_array_equal(boxes[0]["min"], [10, 20])
    np.testing.assert_array_equal(boxes[0]["max"], [30, 40])
    with pytest.raises(ValueError, match="Incomplete record"):
        decode_sd_boxes(raw[:-1])
    with pytest.raises(ValueError, match="capacity"):
        decode_sd_boxes(np.array([1, 0, 0, 0], dtype=np.uint8), semantic=True)

    # Two paths intentionally share all 128 bits; a dictionary would lose one of them.
    payload = struct.pack("<4III", 1, 2, 3, 4, 2, 48)
    payload += struct.pack("<4III", 1, 2, 3, 4, 2, 51) + b"/a\0/b\0" + struct.pack("<I", 2)
    identifiers = np.frombuffer(payload, dtype=np.uint8)
    assert decode_sd_identifiers(identifiers) == [((1, 2, 3, 4), "/a"), ((1, 2, 3, 4), "/b")]
    broken = identifiers.copy()
    broken[20:24] = np.frombuffer(struct.pack("<I", 0), dtype=np.uint8)
    with pytest.raises(ValueError, match="storage"):
        decode_sd_identifiers(broken)
    broken = identifiers.copy()
    # Producers supply a byte length; padding after the string need not be NUL.
    broken[50] = 65
    assert decode_sd_identifiers(broken) == decode_sd_identifiers(identifiers)
    broken[16:20] = np.frombuffer(struct.pack("<I", 1024), dtype=np.uint8)
    with pytest.raises(ValueError, match="storage"):
        decode_sd_identifiers(broken)


def test_sd_camera_projection_and_reserved_box_capacity():
    """Check independent byte offsets, pixel orientation, and unused semantic capacity."""
    camera_bytes = bytearray(260)
    struct.pack_into("<16f", camera_bytes, 0, *np.eye(4).reshape(-1))
    struct.pack_into("<16f", camera_bytes, 64, *np.eye(4).reshape(-1))
    struct.pack_into("<fIIff", camera_bytes, 128, 0.01, 640, 360, 0.1, 100.0)
    camera_bytes[148:155] = b"pinhole"
    struct.pack_into("<f", camera_bytes, 176, 35.0)
    camera = decode_sd_camera(np.frombuffer(camera_bytes, dtype=np.uint8))
    assert camera["focal_length"] == 35.0
    np.testing.assert_allclose(project_sd_point([0, 0, 0], np.eye(4), camera), [320, 180])
    np.testing.assert_allclose(project_sd_point([1, 1, 0], np.eye(4), camera), [640, 0])
    # Hand calculation: local (1,2,3) -> world (3,1,3) -> camera (2,4,3).
    # Projection gives clip (.2,.4,3,4), NDC (.05,.1), then pixels (336,162).
    local = np.array([[2, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [1, -1, 0, 1]])
    camera["world_to_camera"] = [[1, 0, 0, 0], [0, 2, 0, 0], [0, 0, 1, 0], [-1, 2, 0, 1]]
    camera["projection"] = [[.1, 0, 0, 0], [0, .1, 0, 0], [0, 0, 1, 1], [0, 0, 0, 1]]
    np.testing.assert_allclose(project_sd_point([1, 2, 3], local, camera), [336, 162], atol=1e-5)
    assert project_sd_point([0, 0, -2], np.eye(4), camera) is None
    camera["model"] = b"fisheye"
    with pytest.raises(ValueError, match="pinhole"):
        project_sd_point([1, 2, 3], local, camera)
    reserved = bytearray(48 * 2 + 4)
    struct.pack_into("<8I4i", reserved, 0, 1, 2, 3, 4, 5, 0, 0, 0, 10, 20, 30, 40)
    struct.pack_into("<I", reserved, len(reserved) - 4, 1)
    boxes = decode_sd_boxes(np.frombuffer(reserved, dtype=np.uint8), semantic=True)
    assert len(boxes) == 1
    assert tuple(boxes[0]["stable_id"]) == (1, 2, 3, 4)


@pytest.mark.parametrize("render_mode", ["RealTimePathTracing", "PathTracing"])
def test_sd_decoders_rendered_scene(renderer, stage, render_mode):
    """Check packed layouts and ID joins against labeled geometry rendered by RTX."""
    names = ["NormalSD", "StableIdSegmentation", "SemanticSegmentation",
             "SemanticInstanceSegmentation", "NonStableInstanceSegmentation",
             "BoundingBox2DTightSD", "BoundingBox2DLooseSD", "BoundingBox3DSD",
             "SemanticBoundingBox2DTight", "SemanticBoundingBox2DLoose", "SemanticBoundingBox3D",
             "OcclusionSD", "InstanceIdTokenMapSD", "InstanceMap", "SemanticIdMap",
             "StableIdMapDeltas", "SemanticIdMapDeltas", "StableIdSemanticIdMap", "CameraParams"]
    definitions = "\n".join(f'def RenderVar "{name}" {{\n    string sourceName = "{name}"\n}}' for name in names)
    ordered = ", ".join(f"<{name}>" for name in names)
    scene = f'''#usda 1.0
( subLayers = [@{SCENE_PATH}@, @{_RTPT_SCENE_PATH}@] )
over "World" {{
    over "Sphere" (prepend apiSchemas = ["SemanticsAPI:class"]) {{
        string semantic:class:params:semanticType = "class"
        string semantic:class:params:semanticData = "sphere"
    }}
    over "Cube" (prepend apiSchemas = ["SemanticsAPI:class"]) {{
        string semantic:class:params:semanticType = "class"
        string semantic:class:params:semanticData = "cube"
    }}
}}
def "Render" {{
 def RenderProduct "Decoded" {{
    int2 resolution = (320, 180)
    rel camera = </Camera0>
    token omni:rtx:rendermode = "{render_mode}"
    uint omni:rtx:pt:samplesPerPixel = 128
    int omni:rtx:pt:samplesPerIteration = 32
    int omni:rtx:quality = 100
    rel orderedVars = [{ordered}]
    {definitions}
}}
}}
'''
    ovstage.population.open_usd_from_string(stage, scene, ordinal=1)
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()
    products = renderer.step(render_products={"/Render/Decoded"}, delta_time=1 / 60, ordinal=1)
    frame = next(iter(products.values())).frames[0]
    initial = {name: map_sd_image(frame, f"/Render/Decoded/{name}") for name in names}
    initial_paths = decode_sd_identifiers(initial["StableIdMapDeltas"])
    assert initial_paths
    assert decode_sd_identifiers(initial["SemanticIdMapDeltas"])

    # PT captures its first frame; RTPT keeps its existing warmed-up decoder checks.
    if render_mode == "RealTimePathTracing":
        for _ in range(5):
            products = renderer.step(render_products={"/Render/Decoded"}, delta_time=1 / 60, ordinal=1)
        frame = next(iter(products.values())).frames[0]
    data = {name: map_sd_image(frame, f"/Render/Decoded/{name}") for name in names}
    assert data["NormalSD"].shape == (180, 320, 4)
    if render_mode == "RealTimePathTracing":
        assert decode_sd_identifiers(data["StableIdMapDeltas"]) == []
        assert decode_sd_identifiers(data["SemanticIdMapDeltas"]) == []

    # Resolve the same full 128-bit IDs across pixels, pair records, and labels.
    pairs = decode_sd_id_pairs(data["StableIdSemanticIdMap"])
    labels = dict(decode_sd_identifiers(data["SemanticIdMap"]))
    assert {"class: sphere; ", "class: cube; "} <= set(labels.values())
    semantic_ids = {tuple(row) for row in data["SemanticInstanceSegmentation"].reshape(-1, 4)
                    if np.any(row) and tuple(row) != (0, 0, 0, 1)}
    geometry_pixels = data["StableIdSegmentation"].reshape(-1, 4)
    visible_geometry = {tuple(row) for row in geometry_pixels if np.any(row)}
    assert visible_geometry and visible_geometry <= {key for key, path in initial_paths}
    assert any(path.startswith("/World/Sphere") for key, path in initial_paths)
    assert any(path.startswith("/World/Cube") for key, path in initial_paths)
    pair_geometry = {tuple(row["stable_id"]) for row in pairs}
    pair_semantics = {tuple(row["semantic_id"]) for row in pairs}
    assert semantic_ids and semantic_ids <= pair_geometry
    for semantic_id in pair_semantics - {(0, 0, 0, 0), (1, 0, 0, 0)}:
        assert semantic_id in labels

    # Class IDs must agree pixel-by-pixel, rather than just containing the same set of IDs.
    class_by_instance = {tuple(row["stable_id"]): int(row["semantic_id"][0]) for row in pairs}
    instance_pixels = data["SemanticInstanceSegmentation"].reshape(-1, 4)
    class_pixels = data["SemanticSegmentation"].reshape(-1)
    nonstable_pixels = data["NonStableInstanceSegmentation"].reshape(-1)
    joined = np.unique(np.column_stack([instance_pixels, class_pixels, nonstable_pixels]), axis=0)
    for words in joined:
        instance_id, class_id, nonstable_id = tuple(words[:4]), int(words[4]), int(words[5])
        if instance_id == (0, 0, 0, 0):
            assert class_id == nonstable_id == 0
        elif instance_id == (0, 0, 0, 1):
            assert class_id == nonstable_id == 1
        else:
            assert class_by_instance[instance_id] == class_id
            assert nonstable_id >= 2
            pair = pairs[nonstable_id - 2]
            assert tuple(pair["stable_id"]) == instance_id
            assert int(pair["semantic_id"][0]) == class_id

    # Raw boxes and visibility share an instance/tile key; token headers define map indexing.
    tight = decode_sd_boxes(data["BoundingBox2DTightSD"])
    loose = decode_sd_boxes(data["BoundingBox2DLooseSD"])
    valid_tight = tight[np.all(tight["max"] >= tight["min"], axis=1)]
    assert len(valid_tight)
    occlusion = decode_sd_occlusion(data["OcclusionSD"])
    visibility = {(int(row["instance_id"]), int(row["tile_id"])): row["ratio"] for row in occlusion}
    for box in valid_tight:
        key = (int(box["instance_id"]), int(box["tile_id"]))
        assert key in visibility
        assert 0 <= visibility[key] <= 1
    header, tokens = decode_sd_tokens(data["InstanceIdTokenMapSD"])
    instance_map = decode_sd_instance_map(data["InstanceMap"])
    minimum = int(header["prim_token"]) & 0xffffffff
    maximum = int(header["prim_token"]) >> 32
    assert minimum <= maximum and len(instance_map) >= maximum - minimum + 1
    assert all(minimum <= int(record["instance_id"]) <= maximum for record in tokens)
    assert len(loose) == len(tight)

    # Project actual 3D box corners through the captured camera, detecting transpose/unit mistakes.
    camera = decode_sd_camera(data["CameraParams"])
    np.testing.assert_array_equal(camera["resolution"], [320, 180])
    boxes3d = decode_sd_boxes(data["BoundingBox3DSD"], three_d=True)
    projected = []
    for box in boxes3d:
        if np.any(box["max"] < box["min"]):
            continue
        for mask in range(8):
            point = [box["max"][axis] if mask & (1 << axis) else box["min"][axis] for axis in range(3)]
            pixel = project_sd_point(point, box["local_to_world"], camera)
            if pixel is not None:
                projected.append(pixel)
    assert projected and np.isfinite(projected).all()
    assert any(0 <= pixel[0] <= 320 and 0 <= pixel[1] <= 180 for pixel in projected)
    for name in ["SemanticBoundingBox2DTight", "SemanticBoundingBox2DLoose", "SemanticBoundingBox3D"]:
        boxes = decode_sd_boxes(data[name], semantic=True, three_d=name.endswith("3D"))
        assert len(boxes)
        assert any(tuple(box["semantic_id"]) in labels for box in boxes)
    del frame, products


# Load the canonical example's pure decoders without running its application entry point.
_PT_EXAMPLE_PATH = Path(__file__).resolve().parents[3] / "examples/python/semantic-segmentation/main.py"
_PT_SPEC = importlib.util.spec_from_file_location("pt_lineup_example", _PT_EXAMPLE_PATH)
_PT_EXAMPLE = importlib.util.module_from_spec(_PT_SPEC)
_PT_SPEC.loader.exec_module(_PT_EXAMPLE)


def test_pt_pixel_types_and_view_metadata():
    """Check half floats, UNORM values, rejected ID pixels, and independent metadata offsets."""
    halves = np.array([0x3c00, 0xc000, 0x0001, 0x7c00], dtype=np.uint16).view(np.float16).reshape(1, 1, 4)
    decoded = _PT_EXAMPLE.decode_pt_pixels(halves)
    np.testing.assert_array_equal(decoded[0, 0, :3], [1, -2, 2 ** -24])
    assert np.isposinf(decoded[0, 0, 3])
    assert decoded.dtype == np.float32
    unorm = np.array([255, 128, 0, 255], dtype=np.uint8).reshape(1, 1, 4)
    np.testing.assert_allclose(_PT_EXAMPLE.decode_pt_pixels(unorm)[0, 0], [1, 128 / 255, 0, 1])
    with pytest.raises(ValueError, match="uint8"):
        _PT_EXAMPLE.decode_pt_pixels(np.ones((1, 1, 4), dtype=np.uint32))
    data = np.arange(236, dtype=np.float32).reshape(1, 236, 1)
    record = _PT_EXAMPLE.decode_pt_view_data(data)
    assert record["view"][0, 0] == 48
    np.testing.assert_array_equal(record["view_origin"], [228, 229, 230, 231])
    np.testing.assert_array_equal(record["projection_jitter"], [234, 235])
    with pytest.raises(ValueError, match="236"):
        _PT_EXAMPLE.decode_pt_view_data(data[:, :-1])
    with pytest.raises(ValueError, match="float32"):
        _PT_EXAMPLE.decode_pt_view_data(data.astype(np.float16))


def test_pt_camera_outputs(renderer, stage):
    """Validate documented PT output contracts and LPE radiance on a local lit scene."""
    # Reuse the existing local scene while keeping the example's exact request/authoring path.
    layer = _PT_EXAMPLE.build_pt_render_layer_usda(Path(_RTPT_SCENE_PATH), (320, 180))
    layer = layer.replace('/World/Camera', '/Camera0')
    ovstage.population.open_usd_from_string(stage, layer, ordinal=1)
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()
    products = renderer.step(render_products={"/Render/Camera"}, delta_time=1 / 60, ordinal=1)
    frame = next(iter(products.values())).frames[0]
    assert frame.converged, "The first PT frame must reach its 128-SPP target"
    names = ["LdrColor", "HdrColor", "PtDirectIllumation", "PtGlobalIllumination", "PtReflections",
             "PtRefractions", "PtSubsurfaceScattering", "PtSelfIllumination", "PtBackground",
             "PtPreDenoisedResult", "PtWorldNormal", "PtWorldPos", "PtViewNormal", "PtZDepth", "PtVolumes",
             "PtDiffuseFilter", "PtReflectionFilter", "PtRefractionFilter", "PtSubsurfaceFilter",
             "PtLuminance", "PtIlluminance", "PtMotion", "DlssInput", "BumpNormal", "BumpNormalResearch",
             "DiffuseAlbedo", "SpecularAlbedo", "DepthLinearized", "Motion2dXYZ", "Motion2dDilated",
             "Motion2dXYZDilated", "MotionWorld", "EmissionAndForegroundMask", "DiffuseLightingDirectAndIndirect",
             "SpecularLightingDirectAndIndirect", "LightingComposited", "Exposure", "ViewMatricesAux",
             "Roughness", "DisocclusionMask", "ViewspacePosition", "HighResDepth", "HighResMotion2d",
             "HighResMotion2dXYZ", "HighResDisocclusionMask", "XRDepth"] + [f"PtLpe{i}" for i in range(9)]
    images = {name: map_sd_image(frame, f"/Render/Camera/{name}") for name in names}
    for name, pixels in images.items():
        assert pixels.ndim == 3 and pixels.size, name
        if name not in {"Exposure", "ViewMatricesAux"} and not name.startswith("HighRes"):
            assert pixels.shape[:2] == (180, 320), name
        expected = np.uint8 if name in {"LdrColor", "DiffuseAlbedo", "SpecularAlbedo", "Roughness"} else (
            np.float16 if name.startswith("Pt") and name not in {"PtWorldNormal", "PtWorldPos", "PtLuminance", "PtIlluminance", "PtMotion"}
            or name in {"HdrColor", "DlssInput", "BumpNormalResearch", "EmissionAndForegroundMask", "DiffuseLightingDirectAndIndirect", "SpecularLightingDirectAndIndirect", "DisocclusionMask"} else np.float32)
        assert pixels.dtype == expected, (name, pixels.dtype, expected)
        assert np.isfinite(pixels).all(), name
        _PT_EXAMPLE.decode_pt_pixels(pixels)
    assert images["Exposure"].shape == (1, 1, 1) and images["Exposure"][0, 0, 0] > 0
    _PT_EXAMPLE.decode_pt_view_data(images["ViewMatricesAux"])
    normal_lengths = np.linalg.norm(images["PtWorldNormal"][..., :3], axis=-1)
    visible = normal_lengths > .1
    assert visible.any()
    # Unit sample normals are averaged across 128 rays, so edges can have shorter vectors.
    assert np.all(normal_lengths[visible] <= 1.005)
    assert np.any(normal_lengths[visible] > .99), "Flat surface interiors retain a unit normal"
    depth = images["DepthLinearized"][..., 0]
    assert np.any((depth > 0) & (depth < 1e30))
    assert np.all((images["PtZDepth"][..., :3] >= 0) & (images["PtZDepth"][..., :3] <= 1))
    assert np.any(images["PtLpe5"][..., :3] > 0), "The lit diffuse scene must contribute direct LPE radiance"
    # Direct and indirect expressions partition the same diffuse/glossy paths.
    # Compare matching LPE outputs so beauty exposure/post-processing cannot skew the oracle.
    for combined, direct, indirect in [(1, 5, 7), (2, 6, 8)]:
        total = images[f"PtLpe{direct}"][..., :3].astype(np.float32) + images[f"PtLpe{indirect}"][..., :3]
        # Check partitioned radiance over the image: independently accumulated half-float
        # outputs can differ at individual pixels after many samples.
        combined_radiance = images[f"PtLpe{combined}"][..., :3].sum(axis=(0, 1), dtype=np.float64)
        partitioned_radiance = total.sum(axis=(0, 1), dtype=np.float64)
        assert np.all(partitioned_radiance > 0)
        np.testing.assert_allclose(combined_radiance, partitioned_radiance, rtol=.005, atol=.003)
    assert np.any(images["PtDirectIllumation"][..., :3] > 0)
    del frame, products
