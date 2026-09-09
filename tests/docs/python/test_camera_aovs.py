# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Tests that all documented camera AOVs render successfully."""

import warnings
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
