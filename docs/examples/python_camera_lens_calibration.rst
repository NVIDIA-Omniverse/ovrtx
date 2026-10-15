.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

Python: Camera Lens Calibration
===============================

This example renders the robot-lineup scene from separate OpenCV pinhole,
OpenCV fisheye, and omni-directional stereo RenderProducts. It logs all three
images to Rerun and can save individual PNGs plus a contact sheet.

.. figure:: ../img/camera-lens-calibration.avif
   :alt: OpenCV pinhole, OpenCV fisheye, and omni-directional stereo camera outputs
   :align: center

   *Three camera views of the same scene showing three different lens
   calibration schemata. Clockwise from top-left:
   OmniLensDistortionOpenCvPinholeAPI, OmniLensDistortionOpenCvFisheyeAPI,
   OmniLensDistortionOmniDirectionalStereoAPI*

.. code-block:: bash

   cd examples/python/camera-lens-calibration
   uv run main.py
   uv run main.py --rrd _output/camera-lens-calibration.rrd
   uv run main.py --no-rr --png _output/camera-lens-calibration.png

See :doc:`../sensors/cameras/lens_calibration` for the authoring model.
