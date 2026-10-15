.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

C: Spectral Rendering
=====================

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
   cd examples/c/spectral-rendering
   # Configure a Release build and resolve the SDK dependencies.
   cmake -B build -DCMAKE_BUILD_TYPE=Release
   # Build the executable and stage its scene assets.
   cmake --build build --config Release
   # Render low-pressure sodium with RGB transport and save a PNG.
   ./build/spectral-rendering sodium rgb 4096 sodium-rgb.png
   # Render low-pressure sodium with spectral PathTracing and save a PNG.
   ./build/spectral-rendering sodium spectral 4096 sodium-spectral.png
   # Render mercury light with RGB transport and save a PNG.
   ./build/spectral-rendering mercury rgb 4096 mercury-rgb.png
   # Render mercury light with spectral PathTracing and save a PNG.
   ./build/spectral-rendering mercury spectral 4096 mercury-spectral.png

On Windows, use ``build\Release\spectral-rendering.exe``. The arguments are
illuminant, transport, sample count, and output PNG. Output resolution is
512 × 512. CMake stages the shared USD layer and its local assets beside the
executable. The example uses the C API from C++ and the shared ovrtx/ovstage loaders.

The following snippet sets the startup configuration.

.. literalinclude:: ../../examples/c/spectral-rendering/main.cpp
   :language: cpp
   :start-after: // [snippet:doc-spectral-config-c]
   :end-before: // [/snippet:doc-spectral-config-c]
   :dedent:

The following snippet selects the shared scene variants and renders one converged PathTracing frame.

.. literalinclude:: ../../examples/c/spectral-rendering/main.cpp
   :language: cpp
   :start-after: // [snippet:doc-spectral-select-c]
   :end-before: // [/snippet:doc-spectral-select-c]
   :dedent:

The following snippet copies the rendered color output to a PNG.

.. literalinclude:: ../../examples/c/spectral-rendering/main.cpp
   :language: cpp
   :start-after: // [snippet:doc-spectral-save-c]
   :end-before: // [/snippet:doc-spectral-save-c]
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
       ./build/spectral-rendering "$light" spectral 4096 "${light}-${camera}.png" "$camera"
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
       ./build/spectral-rendering "$light" spectral 4096 "${light}-wb${white}.png" cie1931 "$white"
     done # Finish the four white points.
   done # Finish both illuminants.

.. figure:: ../img/spectral-white-balance.avif
   :alt: Blackbody 3200 K and D65 illumination at four selected camera white points

   *Top: blackbody 3200 K. Bottom: D65. Columns select 3200, 5000, 5600, and 6504 K camera white points.*
