.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

Spectral Rendering
==================

.. image:: ../../../img/spectral-banner.avif
   :alt: Spectral PathTracing under white, sodium, and mercury illumination, from left to right
   :width: 100%

Spectral rendering samples light transport over a continuous spectrum to produce
an RGB image according to the response of the camera. This produces much more
accurate simulation of color, particularly in the presence of high-frequency
illuminant spectra.

In the current version, there is no way to specify spectral material response:
all material colors are uplifted from RGB to the spectral domain during rendering.

Enable Spectral PathTracing
---------------------------

Spectral rendering is **off by default**. Enable spectral support when creating
the **first renderer in a process**, then
explicitly author spectral tracing on its ``PathTracing`` RenderProduct, as
shown below. The startup option prepares the spectral material backend and
physical light spectra. It also sets the spectral-enabled default to true;
the examples author that choice explicitly on the RenderProduct.

The following example snippets configure the renderer before loading a scene.
``transport`` is the example's ``rgb`` or ``spectral`` command-line selection:

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../../../examples/python/spectral-rendering/main.py
         :language: python
         :start-after: # [snippet:doc-spectral-config-python]
         :end-before: # [/snippet:doc-spectral-config-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../../../examples/c/spectral-rendering/main.cpp
         :language: cpp
         :start-after: // [snippet:doc-spectral-config-c]
         :end-before: // [/snippet:doc-spectral-config-c]
         :dedent:

.. warning::

   The startup choice cannot change within a process, including after destroying
   every renderer. Omit the option on later instances to inherit the first choice.
   Run RGB and spectral comparisons in separate processes. Do not mix RGB and
   spectral RenderProducts in the same scene: physical light spectra are prepared
   for the scene as a whole.

Spectral tracing is supported in PathTracing. Real-Time Path-Tracing and Minimal do not
use it. A spectral RenderProduct attribute alone does not initialize spectral
support.

Authoring A Physical Illuminant
-------------------------------

Apply ``PhysicalLightIlluminantAPI`` to the light. The following snippets select
a 3000 K blackbody illuminant and enable visible-spectrum PathTracing for an existing
camera at ``/World/Camera``. Add resolution and output RenderVars as described in
:doc:`../../configuration`.

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../../../tests/docs/usd/data/spectral_rendering.usda
         :language: usda
         :start-after: # [snippet:doc-spectral-authoring]
         :end-before: # [/snippet:doc-spectral-authoring]

   .. tab-item:: Python (usd-core)

      .. literalinclude:: ../../../../tests/docs/usd/test_spectral_rendering.py
         :language: python
         :start-after: # [snippet:doc-spectral-authoring-python]
         :end-before: # [/snippet:doc-spectral-authoring-python]
         :dedent:

These attributes belong to the light:

.. csv-table::
   :header: "USD declaration", "Behavior"
   :widths: 45, 55
   :class: compact-table

   "``token physical:illuminant = ""white""``", "Selects the spectrum using one of the modes below."
   "``float2[] physical:customIlluminant``", "Wavelength in nanometers and spectral radiance pairs, ordered by increasing wavelength. Emission is zero outside the supplied range."

The illuminant modes have different spectral shapes:

.. csv-table::
   :header: "Mode", "Spectrum"
   :widths: 25, 75
   :class: compact-table

   "``white``", "Matches the white point of the rendering color space; it is not necessarily a flat spectrum."
   "``blackbody``", "Thermal emission at ``inputs:colorTemperature`` in Kelvin."
   "``illuminant D``", "CIE daylight spectrum at ``inputs:colorTemperature``; temperatures are clamped to 4000–25000 K. D65 uses 6504 K."
   "``custom``", "Uses the measured or authored samples in ``physical:customIlluminant``."

Blackbody and daylight modes use the temperature directly, without requiring
``inputs:enableColorTemperature``. Keep ``inputs:color`` white when comparing
unmodified spectra; a colored value also filters the emitted light.

A custom spectrum has an absolute scale unless you specify a photometric target.
For comparisons at equal luminous power, also apply ``PhotometricAreaLightAPI``
and set ``photometric:power``. This normalizes each spectrum to the requested
lumens. See :doc:`../../../lights/physical_lighting` for units and other light types.

Spectral Controls
-----------------

Author these custom attributes on the RenderProduct. They currently have no
applied settings schema; the values below are base renderer defaults rather
than USD schema fallbacks. The startup option changes the enabled default to
true.

.. csv-table::
   :header: "USD declaration", "Behavior"
   :widths: 58, 42
   :class: compact-table

   "``custom bool omni:rtx:pathtracing:spectral:enabled = false``", "Enables spectral tracing in PathTracing after startup support is enabled."
   "``custom float omni:rtx:pathtracing:spectral:wavelengthMin = 10``", "Lower wavelength limit in nanometers."
   "``custom float omni:rtx:pathtracing:spectral:wavelengthMax = 10000``", "Upper wavelength limit in nanometers."
   "``custom uint omni:rtx:pathtracing:spectral:responseCurve = 0``", "CIE observer: 0 selects 1931 2-degree; 1 selects 1964 10-degree."

The wavelength limits are clipped to the available response curve. The built-in
CIE response covers approximately 360–830 nm; the broad default limits do not
imply an infrared response. Keep the lower limit below the upper limit.
The examples use 360–830 nm and the default CIE 1931 observer.

The output is still a color image, not a spectral cube. Read
:ref:`HdrColor <camera-output-tables>` for numerical comparisons before tone
mapping, or :ref:`LdrColor <camera-output-tables>` for display.

RGB And Spectral Comparisons
----------------------------

The examples reuse the rect-light scene with its color chart and material
spheres, with a closer camera view to make the color patches easier to compare.
A dispersive diamond sits in front of the spheres. Its material uses an index
of refraction of 2.4187 and an Abbe number of 55.3.
Every image uses the same camera, fixed exposure at ISO 400, 6400-lumen rect light,
4096 samples per pixel, and a maximum of 32 path bounces. Denoising and firefly
filtering are enabled, with glossy, diffuse, and emissive firefly thresholds all
set to 10,000. Adaptive sampling and radiance caching are disabled. Only the
illuminant and transport selection change.

.. figure:: ../../../img/spectral-white.avif
   :alt: White illumination rendered with RGB on the left and spectral PathTracing on the right

   *White illumination uses the rendering color space white point (D65 in this case).
   RGB and spectral rendering are very similar with a smooth illuminant, apart
   from the dispersive diamond refractions.*

Low-pressure sodium concentrates most of its light in a narrow yellow band.
The mercury-vapor spectrum has strong violet, blue, green, and yellow peaks.
These spiky spectra make the differences between RGB and spectral transport
easier to see.

.. figure:: ../../../img/spectral-discharge.avif
   :alt: Low-pressure sodium and mercury-vapor illumination, each rendered with RGB and spectral PathTracing

   *Low-pressure sodium above, mercury vapor below. RGB is on the left;
   spectral PathTracing is on the right. Compare the chart patches and colored reflections.*

Camera Responsivity Comparison
------------------------------

``PhysicalCameraResponsivityAPI`` replaces the default CIE 1931 observer with
three camera-channel sensitivity curves in spectral PathTracing. Ordinary RGB transport
does not use these curves. Apply the API to a Camera and supply these attributes:

.. csv-table::
   :header: "USD declaration", "Behavior"
   :widths: 50, 50
   :class: compact-table

   "``float2[] physical:responsivity:r``", "Red-channel wavelength/response pairs; wavelength is in nanometers."
   "``float2[] physical:responsivity:g``", "Green-channel wavelength/response pairs."
   "``float2[] physical:responsivity:b``", "Blue-channel wavelength/response pairs."
   "``matrix3d physical:responsivity:cameraToXYZ``", "Converts camera channels to CIE XYZ. A zero matrix selects automatic calibration; nonzero matrices, including identity, are used unchanged."
   "``float physical:responsivity:colorTemperature = 6504``", "Selected whitepoint temperature in kelvin for sensor-channel white balance. Nonpositive or nonfinite values disable adaptation."

Provide a responsivity curve for each of the camera's red, green, and blue
sensor responses using ``physical:responsivity:r``, ``physical:responsivity:g``,
and ``physical:responsivity:b``. Each curve needs at least two
(wavelength in nanometers, response) pairs, ordered by increasing wavelength.
The renderer converts these three sensor responses into the output color space
to produce a color image.

When ``cameraToXYZ`` is zero (its schema default), RTX fits a matrix
from the supplied curves and 190 reference reflectances under 6504 K CIE daylight.
The fit preserves the daylight whitepoint and is cached until the curves change.
It does not depend on scene lights or ``colorTemperature``. The schema's default
CIE XYZ curves reproduce identity within numerical precision. Responses with
insufficient independent channels cannot be fitted and retain identity.

White balance is separate from calibration. RTX integrates the selected illuminant
against the camera responsivities, then applies diagonal gains in sensor-channel
space before camera-to-XYZ and rendering-color-space conversion. The selected
white maps to equal output RGB values while preserving its CIE Y luminance.
This does not estimate scene illumination. Positive temperatures clamp to
1667–25000 K: blackbody below 4000 K, daylight above 5000 K, and a smooth blend
of unit-luminance spectra between. The default 6504 K selects daylight near D65.
Invalid temperatures, singular transforms, or nonpositive white responses bypass
white balance. XYZ output uses equal XYZ components as its neutral target.

The camera example uses the original Canon EOS 5D and Sony α7 IV (ILCE-7M4)
profiles from the `rawtoaces camera database
<https://github.com/AcademySoftwareFoundation/rawtoaces-data/tree/e9b8503cf8a0641f40e5345d9757bde60c15f423/data/camera>`_.
Both have 81 samples from 380–780 nm at 5 nm spacing. The baseline camera has no
responsivity API and uses the renderer's default CIE 1931 observer.

.. figure:: ../../../img/spectral-camera-responsivity.avif
   :alt: D65 daylight and sodium rendered with CIE 1931, Canon EOS 5D, and Sony alpha 7 IV spectral responses

   *D65 daylight above, sodium below. Columns show CIE 1931, Canon EOS 5D, and
   Sony α7 IV. All six images use spectral PathTracing, 4096 samples per pixel, the same
   camera geometry and exposure, and 6400 lumens of light. Camera response and
   its fixed display calibration are the only camera differences.*

Run the comparison from the :doc:`../../../examples/python_spectral_rendering`
or :doc:`../../../examples/c_spectral_rendering` example.

Further Reading
---------------

- :doc:`../../../examples/python_spectral_rendering`
- :doc:`../../../examples/c_spectral_rendering`
- :doc:`../../../lights/physical_lighting`
- :doc:`path_tracing`
