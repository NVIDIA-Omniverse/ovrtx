.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

Python: Runtime textures
========================

NVIDIA Carter drives in a circle through a warehouse. Its forward-facing camera
feeds a stationary monitor: Warp converts the previous frame to greyscale, then
ovstage publishes the pixels as an ``OmniRuntimeTexture``. An existing
``UsdUVTexture`` shader samples that texture through ``dynamic://carterMonitor``
and feeds a ``UsdPreviewSurface`` material on the monitor screen.

.. figure:: ../img/carter-monitor.avif
   :alt: Carter in the warehouse beside a monitor displaying its greyscale camera feed
   :align: center

   *The external view shows Carter and the monitor. The monitor displays the
   previous robot-camera frame after the Warp luminance conversion.*

The scene is a copy of the robot-lineup scene, trimmed to Carter and the
warehouse, with two added viewing cameras and the monitor. Motion is kinematic:
the example writes Carter's pose along a circle, and its child camera follows.
The first frame displays black because no previous frame exists yet.

Running
-------

Run a complete circle and record the animation, or save a final overview:

.. code-block:: bash

   cd examples/python/runtime-textures
   uv run main.py --rrd _output/carter-monitor.rrd
   uv run main.py --png _output/carter-monitor.png

Use matching ovrtx and ovstage packages containing ``OmniRuntimeTexture``, an
RTX-capable GPU, and internet access for the warehouse and Carter payloads.
The renderer and Warp both use CUDA device 0. The example uses the Hydra path.

Without ``--png`` or ``--rrd``, the example opens Rerun and streams the overview,
current robot camera, and a close-up of the monitor. ``--rrd`` saves those views
as an animated recording. ``--png`` saves the final overview and sibling
``_first.png``, ``_robot.png``, and ``_monitor.png`` files.

The defaults render 180 frames at 30 simulation frames per second, completing a
circle in six seconds. ``--frames``, ``--fps``, and ``--period`` control those
values independently. ``--check`` additionally compares the GPU conversion with
an independent CPU reference and the rendered monitor with the previous frame.
These validation readbacks are separate from the GPU texture-feedback path.

Converting the camera image
---------------------------

The kernel reads :ref:`LdrColor <camera-output-tables>`. It decodes sRGB, computes
linear-light luminance with Rec. 709 weights, and encodes greyscale back to sRGB.
The runtime texture declares ``texture:colorSpace = "sRGB"``. The kernel preserves
the camera image's row order:

.. literalinclude:: ../../examples/python/runtime-textures/main.py
   :language: python
   :start-after: # [snippet:doc-runtime-texture-luminance]
   :end-before: # [/snippet:doc-runtime-texture-luminance]
   :dedent:

Publishing the previous frame
------------------------------

Before rendering frame N, the loop maps frame N-1 on the GPU and runs Warp.
The result and mapping stay alive until the kernel completes. The packed
CUDA bytes are then written to the texture:

.. literalinclude:: ../../examples/python/runtime-textures/main.py
   :language: python
   :start-after: # [snippet:doc-runtime-texture-camera-feedback]
   :end-before: # [/snippet:doc-runtime-texture-camera-feedback]
   :dedent:

The mapping uses linear CUDA memory. Mapping and texture publication can copy
GPU data; this path avoids host texel readback but is not zero-copy sampling.
The explicit waits make ownership and ordering visible in this small example.
See :doc:`../core/cuda_vulkan_scheduling` for the Linux scheduling considerations.

Moving Carter and rendering
----------------------------

The monitor starts with black pixels published at ordinal 1. The first loop
iteration, at ordinal 2, updates only Carter's pose because there is no previous
camera frame to display. Subsequent iterations update Carter's pose and the
monitor pixels together at the same ordinal, then seal it before rendering.
Carter faces the circle's tangent:

.. literalinclude:: ../../examples/python/runtime-textures/main.py
   :language: python
   :start-after: # [snippet:doc-runtime-texture-carter-motion]
   :end-before: # [/snippet:doc-runtime-texture-carter-motion]
   :dedent:

For texture authoring, supported formats, lifetime rules, and attachment behavior,
see :doc:`../materials/runtime_textures`.
