.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

Python: Spectral Rendering
==========================

Render the rect-light scene with ``white``, ``blackbody3200``, ``daylight``, ``sodium``, or ``mercury`` illumination and ``rgb`` or ``spectral`` transport.
The diamond rests on a pavilion facet with its crown facing 65 degrees
camera-left. Rendering uses 32 maximum bounces, denoising, and glossy, diffuse,
and emissive firefly thresholds of 10,000.
The scene, camera, and 6400-lumen light power remain fixed. Run each transport
in a separate process because the material backend is initialized at startup.

.. figure:: ../img/spectral-banner.avif
   :alt: Spectral PathTracing under white, sodium, and mercury illumination

   *Spectral PathTracing under white (left), sodium (center), and mercury (right).*

Build and run from the example directory:

.. code-block:: bash

   # Enter the spectral rendering example directory.
   cd examples/python/spectral-rendering
   # Render low-pressure sodium with RGB transport and save a PNG.
   uv run main.py --illuminant sodium --transport rgb --png _output/sodium-rgb.png
   # Render low-pressure sodium with spectral PathTracing and save a PNG.
   uv run main.py --illuminant sodium --transport spectral --png _output/sodium-spectral.png
   # Render mercury light with RGB transport and save a PNG.
   uv run main.py --illuminant mercury --transport rgb --png _output/mercury-rgb.png
   # Render mercury light with spectral PathTracing and save a PNG. Also save a Rerun recording.
   uv run main.py --illuminant mercury --transport spectral --png _output/mercury-spectral.png --rrd _output/mercury.rrd

Transport defaults to RGB; pass ``--transport spectral`` to enable spectral PathTracing.

Use ``--spp`` to change the default 4096 samples per pixel, and ``--size`` to
change the default 512-pixel square output. ``--png PATH`` saves a headless image;
``--rrd PATH`` saves a Rerun recording. With neither option, Rerun opens a viewer.
``--hdr PATH.npy`` also saves linear :ref:`HdrColor <camera-output-tables>` for
numerical comparisons. Renderer diagnostics go to ``_output/spectral.log``;
use ``--log PATH`` for a separate log per render.

The following snippet sets the startup configuration.

.. literalinclude:: ../../examples/python/spectral-rendering/main.py
   :language: python
   :start-after: # [snippet:doc-spectral-config-python]
   :end-before: # [/snippet:doc-spectral-config-python]
   :dedent:

The following snippet selects the shared scene variants and renders one converged PathTracing frame.

.. literalinclude:: ../../examples/python/spectral-rendering/main.py
   :language: python
   :start-after: # [snippet:doc-spectral-select-python]
   :end-before: # [/snippet:doc-spectral-select-python]
   :dedent:

See :doc:`../sensors/cameras/render_modes/spectral_rendering` for the
comparison images, settings, and limitations.

Camera Responsivity Example
---------------------------

Compare Canon EOS 5D and Sony α7 IV sensitivity curves from rawtoaces with the
default CIE 1931 observer. The following commands render all six combinations of
camera response and illuminant:

.. code-block:: bash

   # Repeat the comparison under D65 daylight and sodium illumination.
   for light in daylight sodium; do
     # Compare the CIE 1931 observer, Canon EOS 5D, and Sony α7 IV.
     for camera in cie1931 canon5d sony_a7iv; do
       # Render this illuminant and camera response with spectral PathTracing; save the named outputs.
       uv run main.py --transport spectral --illuminant "$light" --camera "$camera" --png "_output/${light}-${camera}.png" --hdr "_output/${light}-${camera}.npy"
     done # Finish this camera comparison.
   done # Finish both illuminants.

The camera choice defaults to ``cie1931``. Custom responsivities require spectral
transport.

White-Point Adaptation
----------------------

Select the camera white point independently of the light. These commands render
eight images with CIE 1931 responsivity, 4096 samples, 32 bounces, denoising,
and firefly thresholds of 10,000. The camera responsivity API is applied when
a white point is supplied; its default channel curves retain the CIE observer.

.. code-block:: bash

   # Compare tungsten-like blackbody illumination with D65 daylight.
   for light in blackbody3200 daylight; do
     # Select the camera white point explicitly; no scene estimation is performed.
     for white in 3200 5000 5600 6504; do
       # Save a spectral image using CIE 1931 responsivity and sensor-channel white balance.
       uv run main.py --transport spectral --illuminant "$light" --white-point "$white" --png "_output/${light}-wb${white}.png"
     done # Finish the four white points.
   done # Finish both illuminants.

.. figure:: ../img/spectral-white-balance.avif
   :alt: Blackbody 3200 K and D65 illumination at four selected camera white points

   *Top: blackbody 3200 K. Bottom: D65. Columns select 3200, 5000, 5600, and 6504 K camera white points.*
