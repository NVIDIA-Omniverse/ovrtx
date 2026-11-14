# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Render the public example and compare against the same scene without splats."""
from pathlib import Path
import subprocess
import sys
import numpy as np
from PIL import Image
import pytest


@pytest.mark.parametrize("steps", [None, 32], ids=["first-frame", "32-frames"])
@pytest.mark.parametrize("mode,shading,visible", [
    ("rtpt", 3, True), ("pt", 3, True), ("minimal", 3, True), ("minimal", 2, False),
])
def test_gaussian_example_changes_render(mode, shading, visible, steps, output_dir):
    example = Path(__file__).parents[3] / "examples/python/gaussian-splats"
    folder = output_dir / f"gaussian-splats-{mode}-{shading}-{steps or 1}"
    folder.mkdir(exist_ok=True)
    # Preserve each state and its log for debugging, including failed runs.
    for name in ("visible", "hidden"):
        (folder / f"{name}.png").unlink(missing_ok=True)
        (folder / f"{name}.log").unlink(missing_ok=True)
    configured = folder / "configured.usda"
    # Mode 2 leaves splats unshaded (black), so remove the dome that Minimal shows behind them.
    dome = "" if visible else 'over "World" {\n over "Dome" (active = false) {\n }\n }\n'
    configured.write_text('#usda 1.0\n(subLayers = [@' + (example / 'gaussian_splats.usda').as_posix() + '@])\n'
                          'over "Render" {\n over "Camera" {\n int omni:rtx:minimal:mode = ' + str(shading) + '\n }\n }\n'
                          + dome, encoding="utf-8")
    hidden = folder / "hidden.usda"
    hidden.write_text('#usda 1.0\n(subLayers = [@' + configured.as_posix() + '@])\n'
                      'over "World" {\n over "Splats" {\n token visibility = "invisible"\n }\n }\n',
                      encoding="utf-8")
    for scene, name in ((configured, "visible"), (hidden, "hidden")):
        log_path = folder / f"{name}.log"
        with log_path.open("w", encoding="utf-8") as log:
            result = subprocess.run([sys.executable, str(example / "main.py"), "--mode", mode,
                                     "--scene", str(scene), "--png", str(folder / f"{name}.png")]
                                    + (["--steps", str(steps)] if steps is not None else []),
                                    cwd=folder, stdout=log, stderr=subprocess.STDOUT, timeout=300)
        assert result.returncode == 0, f"Render failed; see {log_path}"
    with Image.open(folder / "visible.png") as image:
        a = np.asarray(image).astype(float)
    with Image.open(folder / "hidden.png") as image:
        b = np.asarray(image).astype(float)
    assert a.shape == b.shape == (512, 768, 4)
    # A background-only image must not pass a simple nonzero-output check.
    difference = np.mean(np.abs(a[..., :3] - b[..., :3]))
    if visible:
        assert difference > 8, f"Splats are missing (difference={difference}); see {folder}"
    else:
        assert difference < 1, f"Minimal mode 2 unexpectedly renders splats (difference={difference}); see {folder}"
