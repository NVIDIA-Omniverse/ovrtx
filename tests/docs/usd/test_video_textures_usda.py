# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Validate the video-texture authoring and extracted example snippet."""

from pathlib import Path

from conftest import validate_usda
from pxr import Sdf, Usd
from test_usd_python_examples import (
    _author_video_texture_blocking_product,
    _author_video_texture_material,
)

PUBLIC_ROOT = Path(__file__).parents[3]
EXAMPLE_DIR = PUBLIC_ROOT / "examples/python/video-textures"
EXAMPLE_LAYER = EXAMPLE_DIR / "video_textures.usda"


def _snapshot(stage, shader_path):
    shader = stage.GetPrimAtPath(shader_path)
    prefix = "inputs:omni:playback:inputs:diffuse_texture"
    return {
        "apis": tuple(shader.GetAppliedSchemas()),
        "texture": shader.GetAttribute("inputs:diffuse_texture").Get(),
        "color_space": shader.GetAttribute("inputs:diffuse_texture").GetMetadata(
            "colorSpace"
        ),
        "diffuse_color": shader.GetAttribute(
            "inputs:diffuse_color_constant"
        ).Get(),
        "roughness": shader.GetAttribute(
            "inputs:reflection_roughness_constant"
        ).Get(),
        "rate": shader.GetAttribute(f"{prefix}:rate").Get(),
        "source_start": shader.GetAttribute(f"{prefix}:sourceStart").Get(),
        "source_end": shader.GetAttribute(f"{prefix}:sourceEnd").Get(),
        "playback_start": shader.GetAttribute(f"{prefix}:playbackStart").Get(),
        "before": shader.GetAttribute(f"{prefix}:before").Get(),
        "after": shader.GetAttribute(f"{prefix}:after").Get(),
    }


def test_video_texture_usda_matches_python():
    usda_stage = Usd.Stage.Open(validate_usda(EXAMPLE_LAYER.read_text()))
    python_stage = Usd.Stage.CreateInMemory()
    _author_video_texture_material(python_stage)

    usda_snapshot = _snapshot(usda_stage, "/World/Looks/VideoMaterial_0/Shader")
    python_snapshot = _snapshot(python_stage, "/World/Looks/VideoMaterial/Shader")
    assert usda_snapshot == python_snapshot
    assert usda_snapshot["texture"] == Sdf.AssetPath(
        "./video_texture_h265.mp4"
    )

    for index in range(4):
        shader = usda_stage.GetPrimAtPath(
            f"/World/Looks/VideoMaterial_{index}/Shader"
        )
        assert shader.IsValid()
        render_product = usda_stage.GetPrimAtPath(f"/Render/Camera_{index}")
        blocking = render_product.GetAttribute("omni:rtx:videostreamer:blocking")
        assert blocking.GetTypeName() == Sdf.ValueTypeNames.Bool
        assert blocking.Get() is True

    python_product = _author_video_texture_blocking_product(python_stage)
    python_blocking = python_product.GetPrim().GetAttribute(
        "omni:rtx:videostreamer:blocking"
    )
    usda_blocking = usda_stage.GetPrimAtPath("/Render/Camera_0").GetAttribute(
        "omni:rtx:videostreamer:blocking"
    )
    assert python_blocking.GetTypeName() == usda_blocking.GetTypeName()
    assert python_blocking.Get() == usda_blocking.Get()


def _marked_snippet(path, name):
    source = path.read_text()
    start = source.index(f"# [snippet:{name}]\n")
    start = source.index("\n", start) + 1
    end = source.index(f"# [/snippet:{name}]", start)
    return source[start:end].rstrip()


def _readme_block_after(heading, language):
    readme = (EXAMPLE_DIR / "README.md").read_text()
    start = readme.index(f"```{language}\n", readme.index(heading))
    start += len(f"```{language}\n")
    end = readme.index("\n```", start)
    return readme[start:end]


def test_video_texture_readme_snippets_match_example_source():
    usda = EXAMPLE_DIR / "video_textures.usda"
    main = EXAMPLE_DIR / "main.py"

    assert _readme_block_after(
        "### 1. Assign the video", "usda"
    ) == _marked_snippet(usda, "doc-video-texture-material")
    assert _readme_block_after(
        "### 2. Bind the material", "usda"
    ) == _marked_snippet(usda, "doc-video-texture-binding")

    heading = "### 3. Select and render video timestamps"
    assert _readme_block_after(heading, "python") == _marked_snippet(
        main, "doc-render-video-texture-source-times"
    )


def test_h265_clip_is_committed():
    clip = EXAMPLE_DIR / "video_texture_h265.mp4"
    assert clip.is_file()
    assert clip.stat().st_size > 100_000
