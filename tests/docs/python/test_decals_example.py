# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Exercise the public example and compare decals against the unmarked receiver."""

import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def test_decals_example(tmp_path):
    public = Path(__file__).parents[3]
    example = public / "examples/python/decals/main.py"
    scene = public / "tests/docs/data/ovrtx-test-decals.usda"
    output = Path(__file__).parent / "_output"
    output.mkdir(exist_ok=True)
    png = output / "decals.enabled.png"
    with (output / "decals.enabled.log").open("w", encoding="utf-8") as log:
        subprocess.run([sys.executable, str(example), "--png", str(png)],
                       check=True, stdout=log, stderr=subprocess.STDOUT, timeout=300)
    pixels = np.asarray(Image.open(png).convert("RGB"), dtype=np.int16)
    assert pixels.shape == (768, 768, 3)
    red = (pixels[:, :, 0] > 100) & (pixels[:, :, 0] > 2 * pixels[:, :, 1])
    green = (pixels[:, :, 1] > 90) & (pixels[:, :, 1] > 1.2 * pixels[:, :, 0])
    assert red.sum() > 2500, "The red decals must be visible, not just the green receiver."
    assert green.sum() > 20000, "Cutouts must preserve visible green receiver material."

    # A second render removes all decals without changing geometry or lighting.
    baseline_scene = tmp_path / "no-decals.usda"
    baseline_scene.write_text(
        '#usda 1.0\n(\n subLayers = [@' + scene.as_posix() + '@]\n)\n'
        'over "World" {\n'
        + ''.join(f' over "{name}" {{\n bool omni:decal:enabled = false\n }}\n'
                  for name in ("RedRTXA", "RedRTXB", "RedRTXC", "SilverLogoA", "SilverLogoB", "SilverLogoC"))
        + '}\n', encoding="utf-8")
    baseline_png = output / "decals.disabled.png"
    # Invoke the unchanged public entry point with a different scene constant.
    command = (
        "import runpy,sys; from pathlib import Path; "
        "app=runpy.run_path(sys.argv[1]); app['main'].__globals__['SCENE_PATH']=Path(sys.argv[2]); "
        "sys.argv=[sys.argv[1], '--png', sys.argv[3]]; app['main']()"
    )
    with (output / "decals.disabled.log").open("w", encoding="utf-8") as log:
        subprocess.run([sys.executable, "-c", command, str(example), str(baseline_scene), str(baseline_png)],
                       check=True, stdout=log, stderr=subprocess.STDOUT, timeout=300)
    baseline = np.asarray(Image.open(baseline_png).convert("RGB"), dtype=np.int16)
    delta = np.abs(pixels - baseline).max(axis=2)
    assert np.count_nonzero(delta > 30) > 6000
    assert np.mean(delta[:90]) < 3, "The unbound ground should stay unchanged."
    # Each silver-logo region must change relative to the green baseline.
    for row, col in ((225, 324), (405, 580), (564, 304)):
        # Include both the NVIDIA eye and its wordmark.
        region = pixels[row-45:row+45, col-55:col+55]
        region_delta = delta[row-45:row+45, col-55:col+55]
        neutral = region.max(axis=2) - region.min(axis=2) < 18
        assert np.count_nonzero(neutral & (region_delta > 30)) > 100, "A silver logo is missing."
    # All three RTX instances must be visible in their separate surface regions.
    for row, col in ((185, 440), (422, 190), (505, 525)):
        assert np.count_nonzero(red[row-70:row+70, col-75:col+75]) > 600, "An RTX wordmark is missing."

    # Render the same transforms and masks with only red's priority raised.
    # This must expose red at pixels that silver previously covered.
    ordering_scene = scene.with_name("ovrtx-test-decals-red-on-top.usda")
    ordering_png = output / "decals.red-on-top.png"
    with (output / "decals.red-on-top.log").open("w", encoding="utf-8") as log:
        subprocess.run([sys.executable, "-c", command, str(example), str(ordering_scene), str(ordering_png)],
                       check=True, stdout=log, stderr=subprocess.STDOUT, timeout=300)
    reordered = np.asarray(Image.open(ordering_png).convert("RGB"), dtype=np.int16)
    reordered_red = (reordered[:, :, 0] > 100) & (reordered[:, :, 0] > 2 * reordered[:, :, 1])
    neutral = pixels.max(axis=2) - pixels.min(axis=2) < 25
    changed_to_red = neutral & ~red & reordered_red
    assert np.count_nonzero(changed_to_red[120:320, 200:550]) > 300, "Priority must reverse visible decal overlap."
    assert np.count_nonzero(changed_to_red[350:530, 480:660]) > 300, "The lower-right RTX must overlap the NVIDIA logo."
    # Most of the lower silver decal lies outside the RTX overlap and stays unchanged.
    assert np.abs(reordered[510:640, 250:400] - pixels[510:640, 250:400]).mean() < 3
