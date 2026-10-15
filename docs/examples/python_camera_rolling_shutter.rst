.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

Python: Camera Rolling Shutter
==============================

This example renders an animated cube through global and top-to-bottom rolling
shutters. It logs both images to Rerun and can save a side-by-side PNG.

.. figure:: ../img/camera-rolling-shutter.avif
   :alt: A moving cube rendered with global and rolling-shutter timing
   :align: center

   *The global shutter on the left samples the cube at one instant. The rolling
   shutter on the right offsets that instant for each image row.*

.. code-block:: bash

   cd examples/python/camera-rolling-shutter
   uv run main.py
   uv run main.py --rrd _output/camera-rolling-shutter.rrd
   uv run main.py --no-rr --png _output/camera-rolling-shutter.png

See :doc:`../sensors/cameras/rolling_shutter` for timing and motion-BVH requirements.
