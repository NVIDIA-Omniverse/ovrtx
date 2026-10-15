# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from pathlib import Path
from pxr import Usd


def test_public_scene_arrays_are_consistent():
    scene = Path(__file__).parents[3] / "examples/python/gaussian-splats/gaussian_splats.usda"
    stage = Usd.Stage.Open(str(scene))
    splats = stage.GetPrimAtPath("/World/Splats")
    for name in ("positions", "orientations", "scales", "opacities", "radiance:sphericalHarmonicsCoefficients"):
        assert len(splats.GetAttribute(name).Get()) == 73
    assert splats.GetAttribute("radiance:sphericalHarmonicsDegree").Get() == 0
