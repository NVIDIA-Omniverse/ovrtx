.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _video-textures:

Video Textures
==============

Video textures let an MDL material use a video asset wherever it accepts a
texture asset. Your application selects video frames through ovrtx's active
animation time and the material's ``OmniPlaybackAPI`` properties.

For default playback, assign a video file to an asset input such as
``inputs:diffuse_texture``. Apply ``OmniPlaybackAPI`` when the clip needs an
explicit source range, start time, playback rate, or out-of-range behavior.

.. figure:: ../img/video-textures.avif
   :align: center
   :width: 100%
   :alt: Four renders of a timestamped H.265 video texture at zero, one, two, and three seconds

   *One H.265 video texture rendered at four source-time positions. The
   timestamp and moving ball make frame selection visible.*

Follow the :doc:`Python video-textures walkthrough
<../examples/python_video_textures>` to assign an H.265 video to an OmniPBR
material, bind it to a mesh, select source timestamps, render them with ovrtx,
and inspect the results in Rerun.

Requirements
------------

- Author the video on an asset-valued input of a ``Material``, ``NodeGraph``,
  or ``Shader`` prim used by an RTX material.
- Use a container and codec that the NVIDIA hardware decoder on the target
  system supports. There is no CPU-decoder fallback.
- Use a seekable source for arbitrary timestamp selection and looping. Live
  sources normally support forward playback only.
- Author one video track per asset. Audio and additional tracks are ignored.

Authoring a Video Texture
-------------------------

``OmniPlaybackAPI`` is a multiple-apply API schema. Its instance name must
match the complete asset input name, including the ``inputs:`` namespace. For
``inputs:diffuse_texture``, apply
``OmniPlaybackAPI:inputs:diffuse_texture`` to the prim that owns the input.

The following tested snippets create equivalent OmniPBR materials. This
example plays the entire four-second H.265 clip and holds its boundary frames:

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

Bind the material to renderable geometry with ``MaterialBindingAPI`` as you
would for a still texture. See :doc:`material_binding`.

Playback Controls
-----------------

The schema authors the following properties below
``inputs:omni:playback:<textureInput>``:

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 24 16 60

   * - Property
     - Default
     - Effect
   * - ``rate``
     - ``1.0``
     - Multiplies playback speed. Reverse playback is not supported; use a
       nonnegative value.
   * - ``sourceStart``
     - ``0.0``
     - Selects the first source time in seconds.
   * - ``sourceEnd``
     - ``-1.0``
     - Selects the final source time in seconds. ``-1.0`` uses the available
       duration reported by the video.
   * - ``playbackStart``
     - ``0``
     - Authored as a USD timecode and converted to seconds using
       ``timeCodesPerSecond``. In ovrtx, it selects the animation time at which
       ``sourceStart`` begins.
   * - ``before``
     - ``loop``
     - Chooses what ovrtx returns while the animation time is earlier than
       ``playbackStart``. The mapped source time would otherwise be earlier
       than ``sourceStart``.
   * - ``after``
     - ``loop``
     - Chooses what ovrtx returns after the mapped source time passes
       ``sourceEnd``. When ``sourceEnd`` is ``-1.0``, ovrtx uses the available
       end of the video.

At ``playbackStart``, ovrtx selects ``sourceStart``. The ``before`` behavior
therefore applies only before ``playbackStart``. The ``after`` behavior applies
only after the mapped source time passes ``sourceEnd``; ``sourceEnd`` itself is
still inside the selected range.

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 18 41 41

   * - Mode
     - When ``before`` applies
     - When ``after`` applies
   * - ``loop``
     - Wraps backward through the selected source range. For example, a time
       immediately before ``playbackStart`` selects a frame near
       ``sourceEnd``.
     - Wraps to ``sourceStart`` and repeats the selected source range.
   * - ``hold``
     - Returns the frame at ``sourceStart``.
     - Returns the frame at ``sourceEnd``.
   * - ``black``
     - Returns zero in every channel.
     - Returns zero in every channel.

``loop`` requires a seekable source and a usable source range. Otherwise,
ovrtx changes ``loop`` to ``hold`` and logs a warning. Explicit ``sourceStart``
and ``sourceEnd`` values do not enable looping when the decoder reports no
usable seekable range. Use ``hold`` or ``black`` for that source, or use a
source whose decoder exposes a seekable range.

Blocking Frame Selection
------------------------

Video decoding is asynchronous by default. Interactive applications normally
want that behavior so decoding cannot stall rendering. Deterministic capture
and validation can instead author the following boolean property on
the RenderProduct before its first render:

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../examples/python/video-textures/video_textures.usda
         :language: usda
         :start-after: # [snippet:doc-video-texture-blocking]
         :end-before: # [/snippet:doc-video-texture-blocking]
         :dedent: 8

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-video-texture-blocking-python]
         :end-before: # [/snippet:doc-video-texture-blocking-python]
         :dedent:

When enabled, this property makes rendering wait for the selected decoded
frame. Its default is ``false``. Blocking can stall for media I/O, decoder
initialization, and seeking; reserve it for offline rendering, tests, or other
workflows that prefer determinism over latency.

Selecting Video Time in ovrtx
-----------------------------

``playbackStart`` is a stage timecode, while ``sourceStart`` and ``sourceEnd``
are seconds in the video. The stage's ``timeCodesPerSecond`` metadata converts
``playbackStart`` to seconds. ovrtx then maps its active animation time to a
video source time:

.. math::

   t_{video} = t_{sourceStart} + rate \left(t_{animation} -
   \frac{playbackStart}{timeCodesPerSecond}\right)

The source of ``t_animation`` depends on the stage's authored time range:

- When the stage's start and end timecodes are equal, video selection uses the
  simulation clock at the end of the render step. Establish an initial time
  with :py:meth:`~ovrtx.Renderer.reset()`, then advance to each requested time
  with the ``delta_time`` passed to :py:meth:`~ovrtx.Renderer.step()`. With
  ``playbackStart=0``, ``sourceStart=0``, and ``rate=1``, resetting to zero and
  stepping with ``delta_time=2`` selects source second 2.
- When the stage's start and end timecodes differ, video selection uses the
  most recently synchronized USD time instead. Set that time in seconds with
  ``ovstage.population.update_from_usd_time`` in Python or
  ``ovstage_population_apply_usd_time`` in attached-mode C, publish its
  ordinal, and render that ordinal. ``reset()`` and ``step(delta_time=...)``
  still control the simulation and sensor clock, but do not select the video
  time in this case. See :doc:`../scene/loading_usd`.

The :doc:`Python video-textures walkthrough
<../examples/python_video_textures>` uses a stage without an animation range,
resets the simulation clock to zero, and steps through several requested
source timestamps in nondecreasing order.

Supported Media
---------------

A file extension identifies the container, not its encoded video format. A
supported container must contain a track that the target GPU can decode. The
following combinations are validated authoring targets:

.. csv-table:: Validated video-texture media
   :header: "Container", "Video codec", "Notes"
   :widths: 20, 18, 62

   "MP4 (``.mp4``)", "H.264/AVC", "Validated with H.264 High Profile, 8-bit YUV 4:2:0 video. Audio tracks are ignored."
   "Matroska (``.mkv``)", "H.264/AVC", "Validated with H.264 Main Profile, 8-bit YUV 4:2:0 video."
   "MP4 (``.mp4``)", "H.265/HEVC", "Validated on supported GPUs; profiles, bit depths, chroma formats, and maximum resolutions depend on GPU architecture."
   "WebM (``.webm``)", "VP9", "Validated with Profile 0, 8-bit YUV 4:2:0 video."
   "MP4 (``.mp4``)", "AV1", "Validated with AV1 Main Profile, 8-bit YUV 4:2:0 video on supported GPUs; exact frame selection can be unreliable because frames may be dropped."

Additional Decoder and Container Support
########################################

The bundled Linux x86-64 decoder also advertises VP8, MPEG-1, MPEG-2,
MPEG-4, and DivX 4/5. These codecs are not all covered by cross-platform
video-texture tests. Validate the exact container, codec profile, chroma
format, bit depth, resolution, and frame rate on every target system.

The renderer bundles demuxers for these container families:

- ISO Base Media File Format and QuickTime, commonly ``.mp4``, ``.m4v``,
  and ``.mov``
- Matroska and WebM, commonly ``.mkv`` and ``.webm``
- Audio Video Interleave, commonly ``.avi``
- Flash Video, commonly ``.flv``

The file extension does not determine compatibility. An MP4 file still fails
if its video track uses an unsupported codec or profile. Compatible raw
elementary streams can also work when the bundled typefinder and parser
recognize them, but they are not validated authoring targets.

Platform and Stream Requirements
################################

Video textures use NVIDIA hardware decoding on Windows x86-64 and Linux
x86-64 or AArch64. Windows requires NVIDIA display driver 570.65 or newer.
Consult the `NVDEC decoder capabilities
<https://docs.nvidia.com/video-technologies/video-codec-sdk/13.0/nvdec-video-decoder-api-prog-guide/index.html#video-decoder-capabilities>`_
before selecting a deployment format. ovrtx converts decoded frames to 8-bit
RGBA textures regardless of source bit depth.

Network Video Sources
---------------------

Local files, direct HTTP or HTTPS media URLs, RTSP streams, and
``omniverse://`` assets can be video-texture sources. The URL must resolve from
the system running ovrtx.

.. warning::

   Do not author user names, passwords, bearer tokens, or reusable secrets in
   a video URL. The URL is stored in the USD layer and can appear in logs.

HTTP and HTTPS URLs must point directly to a supported media file and include
a recognized video extension such as ``.mp4`` or ``.webm`` in the path. Query
parameters may follow the extension. HLS and MPEG-DASH playlists and custom
HTTP request headers are not supported. Seeking depends on the server, source
element, and container exposing byte and time ranges.

An ``rtsp://`` URL does not need a filename extension. Live RTSP sources are
normally non-seekable, though recorded or time-shifted servers can expose a
seekable range. On non-seekable streams, frames are consumed in presentation
timestamp order and requested looping changes to holding.

For ``omniverse://`` URLs, ovrtx uses the application's existing client
session, downloads the complete asset before decoding, and caches it by the
complete URL. Large videos therefore increase startup time and local storage
use. Add a versioned query when a stage must resolve a specific revision.

Color Space
-----------

Use USD ``colorSpace`` metadata on the video asset input when its encoding is
known:

- ``sRGB`` treats decoded RGB values as sRGB color.
- ``raw`` treats values as linear data, appropriate for masks, roughness,
  normals, and other non-color inputs.
- With no authored value, ovrtx uses a signaled linear transfer as linear and
  treats other or missing transfer signals as sRGB.

The authored value takes precedence over the video's signal for GPU texture
sampling; it does not convert the video itself. Decoded textures are currently
8-bit RGBA. PQ and HLG transfer functions cannot be represented correctly as
linear or sRGB and can produce incorrect brightness. Videos that signal
BT.2020 primaries and matrix coefficients are not currently supported and can
fail before producing a frame. For predictable results, keep container color
metadata consistent with the encoded stream.

Performance and Resource Usage
------------------------------

ovrtx can share a loaded video texture when material inputs use the same
resolved URL and identical playback and color-space configuration. A different
URL or configuration creates a separate decoder and texture resource. Each
unique video consumes hardware-decoder capacity and GPU memory, potentially on
every active rendering GPU. Validate the intended stream count, resolution,
frame rate, and codec on each deployment target.

Limitations and Troubleshooting
-------------------------------

- Reverse playback is not supported.
- Use a nonnegative ``sourceStart`` and a ``sourceEnd`` greater than it for an
  explicit finite range.
- A shared video texture can represent only one timestamp per render update.
  If views request different animation times without a global override, ovrtx
  keeps the previous decoded texture for that update.
- If the texture stays on its placeholder, verify that the GPU supports the
  stream and inspect the log for decoder negotiation errors.
- If looping becomes holding, verify that the decoder reports both a seekable
  source and a usable seekable range. Explicit source bounds cannot replace a
  decoder-reported range.
- If the image is too light or dark, compare authored ``colorSpace`` metadata
  with the video's transfer-function signal.
- If playback begins at the wrong time, first check whether the stage's start
  and end timecodes differ. For such a stage, inspect the synchronized USD
  time. Otherwise, inspect the simulation time set by
  :py:meth:`~ovrtx.Renderer.reset()` and accumulated by
  :py:meth:`~ovrtx.Renderer.step()`. Also check ``timeCodesPerSecond`` and
  ``playbackStart``.
