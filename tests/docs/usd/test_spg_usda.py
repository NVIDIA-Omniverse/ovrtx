# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Validate the SPG (Sensor Processing Graph) example USDA files.

Parses every shader definition and scene under examples/python/spg-* and, for
each scene, composes the stage and asserts the RenderProduct graph is present and
that the shader's subIdentifier matches the kernel/Lua function name.
"""

from pathlib import Path

import pytest
from pxr import Usd

from conftest import validate_usda

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = REPO_ROOT / "examples" / "python"

# All shader-definition and scene USDA files that must parse.
USDA_FILES = [
    "spg-grayscale/GrayscaleKernel.usda",
    "spg-grayscale/grayscale_scene.usda",
    "spg-pipeline/GrayscaleKernel.usda",
    "spg-pipeline/InvertKernel.usda",
    "spg-pipeline/pipeline_scene.usda",
    "spg-builtin-nodes/stdlib_scene.usda",
]

# scene file, render product path, prims that must compose, expected (shader, subIdentifier).
SCENES = [
    (
        "spg-grayscale/grayscale_scene.usda",
        "/Render/GrayscaleDemo",
        ["/World/Camera", "/Render/GrayscaleDemo/LdrColor", "/Render/GrayscaleDemo/LdrGrayscale"],
        [("GrayscaleKernel", "grayscale")],
    ),
    (
        "spg-pipeline/pipeline_scene.usda",
        "/Render/PipelineDemo",
        ["/World/Camera", "/Render/PipelineDemo/LdrColor", "/Render/PipelineDemo/LdrInverted"],
        [("GrayscaleKernel", "grayscale"), ("InvertKernel", "invert")],
    ),
    (
        "spg-builtin-nodes/stdlib_scene.usda",
        "/Render/StdlibDemo",
        ["/World/Camera", "/Render/StdlibDemo/LdrColor", "/Render/StdlibDemo/Downscaled"],
        [],  # built-in factory nodes: no sourceAsset subIdentifier
    ),
]


# [snippet:test-spg-usda-parses]
@pytest.mark.parametrize("rel_path", USDA_FILES)
def test_spg_usda_parses(rel_path):
    """Every SPG shader/scene USDA file is syntactically valid."""
    usda_path = EXAMPLES / rel_path
    assert usda_path.exists(), f"missing {usda_path}"
    validate_usda(usda_path.read_text())
# [/snippet:test-spg-usda-parses]


# [snippet:test-spg-scene-composes]
@pytest.mark.parametrize("rel_path, product, prims, shaders", SCENES)
def test_spg_scene_composes(rel_path, product, prims, shaders):
    """Each SPG scene composes its RenderProduct graph and binds its shaders."""
    scene_path = EXAMPLES / rel_path
    stage = Usd.Stage.Open(str(scene_path))
    assert stage is not None

    assert stage.GetPrimAtPath(product).IsValid(), f"missing render product {product}"
    for prim_path in prims:
        assert stage.GetPrimAtPath(prim_path).IsValid(), f"missing prim {prim_path}"

    for shader_name, sub_identifier in shaders:
        shader = stage.GetPrimAtPath(f"{product}/{shader_name}")
        assert shader.IsValid(), f"missing shader {shader_name}"
        attr = shader.GetAttribute("info:spg:sourceAsset:subIdentifier")
        assert attr and attr.Get() == sub_identifier, (
            f"{shader_name} subIdentifier should be {sub_identifier!r}"
        )
# [/snippet:test-spg-scene-composes]
