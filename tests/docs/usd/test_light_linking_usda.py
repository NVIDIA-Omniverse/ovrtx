# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Validate the USDA snippet used by the Light Linking documentation page."""

from pathlib import Path

from pxr import Sdf, Usd, UsdLux

from conftest import validate_usda


DATA_DIR = Path(__file__).parent / "data"


def test_light_linking_usda():
    scene_path = DATA_DIR / "light_linking.usda"
    layer = validate_usda(scene_path.read_text())
    stage = Usd.Stage.Open(str(scene_path))
    assert stage
    assert layer.GetPrimAtPath("/World/KeyLight")

    light = UsdLux.SphereLight(stage.GetPrimAtPath("/World/KeyLight"))
    light_link = light.LightAPI().GetLightLinkCollectionAPI()
    shadow_link = light.LightAPI().GetShadowLinkCollectionAPI()

    assert light_link.GetIncludeRootAttr().Get() is False
    assert light_link.GetExpansionRuleAttr().Get() == Usd.Tokens.expandPrims
    assert light_link.GetIncludesRel().GetTargets() == [
        Sdf.Path("/World/Subjects"),
        Sdf.Path("/World/Ground"),
    ]
    light_query = light_link.ComputeMembershipQuery()
    assert light_query.IsPathIncluded(Sdf.Path("/World/Subjects/Linked"))
    assert light_query.IsPathIncluded(Sdf.Path("/World/Subjects/NoShadow"))
    assert light_query.IsPathIncluded(Sdf.Path("/World/Ground"))
    assert not light_query.IsPathIncluded(Sdf.Path("/World/Unlinked"))

    assert shadow_link.GetIncludeRootAttr().Get() is True
    assert shadow_link.GetExcludesRel().GetTargets() == [
        Sdf.Path("/World/Subjects/NoShadow")
    ]
    shadow_query = shadow_link.ComputeMembershipQuery()
    assert shadow_query.IsPathIncluded(Sdf.Path("/World/Subjects/Linked"))
    assert not shadow_query.IsPathIncluded(Sdf.Path("/World/Subjects/NoShadow"))
