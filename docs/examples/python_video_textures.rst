.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Python: Video Textures
======================

This example maps a generated H.265/HEVC video onto geometry, selects four
source times, renders every result, and logs the frames to one Rerun recording.
The video contains a timestamp overlay and moving ball, so both the person
viewing the recording and the CI checks can detect a stale frame. The dark-blue
background and orange ball provide high visual contrast.

.. figure:: ../img/video-textures.avif
   :align: center
   :width: 100%
   :alt: Four rendered H.265 video-texture frames with distinct timestamps and ball positions

   *The same H.265 texture rendered at 0, 1, 2, and 3 seconds.*

.. pull-quote::

   *“Create a video-texture example with a visible timestamp and moving object,
   render several source times, and make the results playable in Rerun.”*

See :doc:`../materials/video_textures` for media requirements, playback
controls, color-space behavior, network sources, and limitations.

Walkthrough
-----------

1. Assign the Video to an OmniPBR Material
##########################################

The sample creates an OmniPBR shader, assigns the H.265 file to its
``inputs:diffuse_texture`` asset input, and connects the shader to the
material. It applies ``OmniPlaybackAPI:inputs:diffuse_texture`` so the same
shader can select a source range and define its behavior outside that range:

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../examples/python/video-textures/video_textures.usda
         :language: usda
         :start-after: # [snippet:doc-video-texture-material]
         :end-before: # [/snippet:doc-video-texture-material]
         :dedent: 8

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-video-texture-material-python]
         :end-before: # [/snippet:doc-video-texture-material-python]
         :dedent:

The ``colorSpace`` metadata tells ovrtx to sample the decoded color as sRGB.
The sample selects the complete 0.0–3.9 second range and uses ``hold`` before
and after it, which makes frame selection clear at the clip boundaries.

2. Bind the Material to Geometry
################################

The sample creates a screen-shaped mesh with UV coordinates, applies
``MaterialBindingAPI``, and binds the video material to it. The UV coordinates
map the complete decoded frame across the screen:

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../examples/python/video-textures/video_textures.usda
         :language: usda
         :start-after: # [snippet:doc-video-texture-binding]
         :end-before: # [/snippet:doc-video-texture-binding]
         :dedent: 4

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-video-texture-binding-python]
         :end-before: # [/snippet:doc-video-texture-binding-python]
         :dedent:

3. Select and Render Video Timestamps
#####################################

The sample USDA deliberately omits differing start and end timecodes. Video
selection therefore uses the simulation clock. The example resets that clock
to zero once, then passes the difference between consecutive requested times
as ``delta_time`` to :py:meth:`~ovrtx.Renderer.step_async()`. Each RenderProduct
enables blocking video decoding, so its render waits for the selected frame.
The example bounds each wait with a timeout, so a frame that never decodes
fails with an error instead of hanging. The application then maps and logs the
image on the Rerun recording's
``video_time`` timeline:

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../examples/python/video-textures/main.py
         :language: python
         :start-after: # [snippet:doc-render-video-texture-source-times]
         :end-before: # [/snippet:doc-render-video-texture-source-times]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_video_textures.cpp
         :language: c
         :start-after: // [snippet:doc-render-video-texture-source-times-c]
         :end-before: // [/snippet:doc-render-video-texture-source-times-c]
         :dedent:

After rendering, the application validates every frame's dimensions and data
type, checks for the dark background and white timestamp, and compares the
orange ball's center with the expected position in the requested 10-FPS source
frame. ``--times`` requires consecutive values to be at least 0.1 seconds
apart, so every render advances by at least one source frame. Reversed, offset,
or placeholder frames fail.

Running
-------

From ``examples/python/video-textures``:

.. code-block:: bash

   uv run main.py
   uv run main.py --rrd _output/video-textures.rrd --png _output/video-textures.png
   uv run main.py --no-rr --png _output/video-textures.png

The first run may take up to 5 minutes while shaders compile and cache. Open
the ``.rrd`` file in Rerun to scrub the ``video_time`` timeline. Use ``--times``
to choose one to four increasing positions in the clip's 0.0-3.9 second
range, with at least 0.1 seconds between consecutive values.

Regenerating the H.265 Asset
----------------------------

The committed clip is generated by ``generate_video.sh`` with GStreamer's
``videotestsrc``, timestamp overlay, ``x265enc``, ``h265parse``, and ``mp4mux``.
It is a four-second, 640×360, 10 FPS, seekable MP4 containing H.265 Main Profile
video. GStreamer is not needed to run the example.
