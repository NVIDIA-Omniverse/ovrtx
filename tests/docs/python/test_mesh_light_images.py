# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Runtime validation for the Mesh Lights documentation comparison."""

import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

GENERATOR = Path(__file__).with_name("generate_mesh_light_images.py")


def test_mesh_light_sampling_converges_receiver_illumination(tmp_path):
    output = tmp_path / "light-mesh-sampling.png"
    subprocess.run(
        [
            sys.executable,
            str(GENERATOR),
            "--output",
            str(output),
            "--warmup-frames",
            "16",
        ],
        check=True,
    )

    with Image.open(output) as image:
        assert image.size == (1024, 560)
        pixels = np.asarray(image)[48:, :, :3]

    sampling_off, sampling_on = np.split(pixels, 2, axis=1)

    # Sample the back wall above the TV, excluding both emissive sources.
    receiver = np.s_[140:240, 40:200, :]
    off_receiver = sampling_off[receiver]
    on_receiver = sampling_on[receiver]
    assert float(np.mean(on_receiver)) > 10.0 * float(np.mean(off_receiver))
    difference = on_receiver.astype(np.float32) - off_receiver.astype(np.float32)
    assert float(np.sqrt(np.mean(difference * difference))) > 50.0

    # The visible emitter itself stays saturated in both renders. This guards
    # against exposure changes masquerading as receiver illumination.
    emitter = np.s_[50:115, 235:275, :]
    off_white = float(np.mean(np.min(sampling_off[emitter], axis=2) > 245))
    on_white = float(np.mean(np.min(sampling_on[emitter], axis=2) > 245))
    assert off_white > 0.25
    assert on_white > 0.25
    assert abs(on_white - off_white) < 0.05
