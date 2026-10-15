.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

Python: Debug Views
===================

This example renders RT2 G-buffer and heat map debug views from the robot-lineup scene.
It captures each view before logging all images together to Rerun under their
debug-view selector names. Static views are captured first, then the robots move
for ten frames to capture ``targetMotion`` and ``targetMotionArrows``.

.. figure:: ../img/example-debug-views.avif
   :alt: Grid of RT2 depth, position, coordinate, normal, identifier, motion, and wireframe debug views
   :align: center

   *The RT2 G-buffer debug views rendered from one scene. Each tile is named after
   the selector authored on its RenderProduct.*

The example creates one RenderProduct per selector. Every RenderProduct requests
only :ref:`LdrColor and HdrColor <camera-output-tables>`.

The rendering loop below captures the :ref:`HdrColor <camera-output-tables>` output for each RenderProduct.
It converts the display-encoded debug views to 8-bit without tonemapping.

.. literalinclude:: ../../examples/python/debug-views/main.py
   :language: python
   :start-after: # [snippet:doc-render-gbuffer-debug-views]
   :end-before: # [/snippet:doc-render-gbuffer-debug-views]
   :dedent:

Run the example interactively, save a Rerun recording, or create PNG output:

.. code-block:: bash

   cd examples/python/debug-views
   uv run main.py
   uv run main.py --rrd _output/debug-views.rrd
   uv run main.py --no-rr --png _output/debug-views.png

See :doc:`../sensors/cameras/outputs` for the supported selectors and
output-routing behavior.
