# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this material and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Validate the LPE RenderProduct authoring shown in the public docs."""

from pathlib import Path

from conftest import validate_usda
from pxr import Sdf, Usd
from test_usd_python_examples import (
    _author_example_lpe_render_vars,
    _author_lpe_render_vars,
)

DATA = Path(__file__).parent / "data" / "light_path_expressions.usda"
PUBLIC_ROOT = Path(__file__).parents[3]
EXAMPLE_LAYER = PUBLIC_ROOT / "examples/python/lpes/lpe-layer.usda"


def _snapshot(stage):
    product = stage.GetPrimAtPath("/Render/Camera")
    return {
        "apis": tuple(product.GetPrimStack()[0].GetInfo("apiSchemas").prependedItems),
        "camera": tuple(product.GetRelationship("camera").GetTargets()),
        "mode": product.GetAttribute("omni:rtx:rendermode").Get(),
        "radiance_cache": product.GetAttribute(
            "omni:rtx:pt:radianceCache:enabled"
        ).Get(),
        "ordered_vars": tuple(product.GetRelationship("orderedVars").GetTargets()),
        "vars": {
            path.name: (
                stage.GetPrimAtPath(path).GetAttribute("sourceName").Get(),
                stage.GetPrimAtPath(path).GetAttribute("sourceType").Get(),
            )
            for path in product.GetRelationship("orderedVars").GetTargets()
        },
    }


def test_lpe_render_vars_usda_matches_python():
    usda_stage = Usd.Stage.Open(validate_usda(DATA.read_text()))
    python_stage = Usd.Stage.CreateInMemory()
    _author_lpe_render_vars(python_stage)

    assert _snapshot(usda_stage) == _snapshot(python_stage)
    assert _snapshot(usda_stage)["camera"] == (Sdf.Path("/World/Camera"),)


def test_lpe_readme_snippet_matches_example_source():
    source = (PUBLIC_ROOT / "examples/python/lpes/main.py").read_text()
    start = source.index("# [snippet:doc-read-lpe-outputs]\n")
    start = source.index("\n", start) + 1
    end = source.index("# [/snippet:doc-read-lpe-outputs]", start)
    source_snippet = source[start:end].rstrip()

    readme = (PUBLIC_ROOT / "examples/python/lpes/README.md").read_text()
    start = readme.index("```python\n") + len("```python\n")
    end = readme.index("\n```", start)
    assert readme[start:end] == source_snippet


def test_lpe_example_uses_documented_expressions():
    stage = Usd.Stage.Open(validate_usda(EXAMPLE_LAYER.read_text()))
    python_stage = Usd.Stage.CreateInMemory()
    _author_example_lpe_render_vars(python_stage)
    assert _snapshot(stage) == _snapshot(python_stage)

    expected = {
        "DiffuseReflection": "E<RD>.*L",
        "GlossyReflection": "E<RG>.*L",
        "GlossyTransmission": "E<TG>.*L",
        "Caustics": "EDG.*L",
    }
    for name, expression in expected.items():
        render_var = stage.GetPrimAtPath(f"/Render/Camera/{name}")
        assert render_var.GetAttribute("sourceName").Get() == expression
        assert render_var.GetAttribute("sourceType").Get() == "lpe"
