.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Path Tracing
============

Path Tracing mode uses progressive sampling to converge towards
ground-truth-quality images. In ovrtx, a render step accumulates towards the
``omni:rtx:pt:samplesPerPixel`` limit before returning output, so application
code usually captures Path Tracing output with a single step rather than the
multi-frame warm-up loop used for Real-Time Path-Tracing convergence. Path Tracing is best suited
for offline or reference-quality workflows where convergence time is acceptable.

.. code-block:: usda

   token omni:rtx:rendermode = "PathTracing"

Warm-Up
-------

PathTracing mode does not need the same warm-up loop for path-tracing convergence
that Real-Time Path-Tracing uses. Texture availability can still matter if an
application requires high-resolution mips in the first captured frame.

Settings
--------

Path Tracing
~~~~~~~~~~~~

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 70 15 15

   * - USD Attribute
     - Type
     - Default
   * - ``omni:rtx:pt:samplesPerPixel``

       Maximum number of samples to accumulate per pixel. When this count is reached, rendering stops until a scene or setting change is detected. Set to 0 to remove this limit.
     - ``uint``
     - ``512``
   * - ``omni:rtx:pt:samplesPerIteration``

       Number of samples per pixel, per iteration. Multiple iterations can be run per launch to reduce kernel launch overhead.
     - ``int``
     - ``1``
   * - ``omni:rtx:pt:adaptiveSampling:enabled``

       When enabled, noise values are computed for each pixel, and upon reaching the threshold level the pixel is no longer sampled.
     - ``bool``
     - ``true``
   * - ``omni:rtx:pt:limits:maxBounces``

       Maximum number of ray bounces for any ray type. Higher values give more accurate results, but worse performance.
     - ``uint``
     - ``4``
   * - ``omni:rtx:pt:limits:maxGlossyBounces``

       Maximum number of ray bounces for specular and transmission.
     - ``uint``
     - ``6``
   * - ``omni:rtx:pt:maxVolumeBounces``

       Maximum number of ray bounces for SSS.
     - ``uint``
     - ``15``
   * - ``omni:rtx:pt:limits:maxFogBounces``

       Maximum number of bounces for volume scattering within a fog/sky volume.
     - ``uint``
     - ``2``
   * - ``omni:rtx:pt:fractionalCutoutOpacity``

       If disabled, material opacity is considered binary: values greater than or equal to 0.5 are considered opaque, while values less than 0.5 are considered transparent.
     - ``bool``
     - ``true``

Denoising
~~~~~~~~~

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 70 15 15

   * - USD Attribute
     - Type
     - Default
   * - ``omni:rtx:pt:denoising:enabled``
     - ``bool``
     - ``true``
   * - ``omni:rtx:pt:denoising:optix:temporal``
     - ``bool``
     - ``false``
   * - ``omni:rtx:pt:denoising:blendFactor``

       Blend factor indicating how much to blend the denoised image with the original. 0 shows only the denoised image, 1.0 shows no denoising.
     - ``float``
     - ``0.0``
   * - ``omni:rtx:pt:denoising:optix:denoiseAOVs``

       If enabled, the OptiX Denoiser also denoises additional render variables alongside the color output.
     - ``bool``
     - ``true``

Sampling and Caching
~~~~~~~~~~~~~~~~~~~~

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 70 15 15

   * - USD Attribute
     - Type
     - Default
   * - ``omni:rtx:pt:radianceCache:enabled``

       Enables caching path-tracing results for improved performance at the cost of some accuracy.
     - ``bool``
     - ``true``
   * - ``omni:rtx:pt:lightCache:enabled``

       Enables the many-light sampling algorithm, which can improve performance in scenes with many lights.
     - ``bool``
     - ``true``
   * - ``omni:rtx:pt:ris:meshLights``

       Enables direct illumination sampling of geometry with emissive materials.
     - ``bool``
     - ``false``
   * - ``omni:rtx:pathtracing:rayguide:cached:enabled``

       Enables caching lighting results for improving surface ray sampling directions.
     - ``bool``
     - ``false``

Firefly Filter
~~~~~~~~~~~~~~

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 70 15 15

   * - USD Attribute
     - Type
     - Default
   * - ``omni:rtx:pt:fireflyFilter:enabled``
     - ``bool``
     - ``true``
   * - ``omni:rtx:pt:fireflyFilter:maxUnexposedIntensityPerSample``

       Clamps the maximum ray intensity for glossy bounces. Can help prevent fireflies, but can result in energy loss. Automatically scaled with exposure.
     - ``float``
     - ``3200.0``
   * - ``omni:rtx:pt:fireflyFilter:maxUnexposedIntensityPerSampleDiffuse``

       Clamps the maximum ray intensity for diffuse bounces. Can help prevent fireflies, but can result in energy loss. Automatically scaled with exposure.
     - ``float``
     - ``3200.0``
   * - ``omni:rtx:pt:fireflyFilter:maxPerEmissiveUnexposedIntensity``

       Clamps the maximum ray intensity for emissive contribution after primary bounce. Can help prevent fireflies, but can result in energy loss. Automatically scaled with exposure.
     - ``float``
     - ``3200.0``

Spectral Rendering
~~~~~~~~~~~~~~~~~~

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 70 15 15

   * - USD Attribute
     - Type
     - Default
   * - ``omni:rtx:pathtracing:spectral:enabled``
     - ``bool``
     - ``false``
   * - ``omni:rtx:pathtracing:spectral:wavelengthMin``

       Minimum simulated wavelength in nanometers.
     - ``float``
     - ``10.0``
   * - ``omni:rtx:pathtracing:spectral:wavelengthMax``

       Maximum simulated wavelength in nanometers.
     - ``float``
     - ``10000.0``
   * - ``omni:rtx:renderingColorSpace``

       Color space input is converted from and to spectral.
     - ``string``
     - ``"lin_rec709_scene"``
   * - ``omni:rtx:pathtracing:spectral:responseCurve``

       Response curve to convert spectral to CIE XYZ.
     - ``uint``
     - ``0``

Non-Uniform Volumes
~~~~~~~~~~~~~~~~~~~

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 70 15 15

   * - USD Attribute
     - Type
     - Default
   * - ``omni:rtx:pt:ptvol:enabled``
     - ``bool``
     - ``false``
   * - ``omni:rtx:pt:volumes:transmittanceMethod``

       Choose between ``biasedRayMarching`` or ``ratioTracking``. Biased ray marching is the ideal option in all cases.
     - ``token``
     - ``"biasedRayMarching"``
   * - ``omni:rtx:pt:volumes:tracking:maxScatteringSteps``

       Maximum delta tracking steps between bounces. Increase for highly scattering volumes like clouds.
     - ``int``
     - ``1024``
   * - ``omni:rtx:pt:volumes:tracking:maxShadowSteps``

       Maximum ratio tracking delta steps for shadow rays. Increase for highly scattering volumes like clouds.
     - ``int``
     - ``32``
   * - ``omni:rtx:pt:limits:maxVolumeBounces``

       Maximum number of bounces in non-uniform volumes.
     - ``uint``
     - ``2``

Multi-GPU
~~~~~~~~~

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 70 15 15

   * - USD Attribute
     - Type
     - Default
   * - ``omni:rtx:pt:multigpu:enabled``
     - ``bool``
     - ``true``
   * - ``omni:rtx:pt:mgpu:autoLoadBalancing:enabled``

       Automatically balance path-tracing work across GPUs in a multi-GPU configuration.
     - ``bool``
     - ``true``
   * - ``omni:rtx:pt:mgpu:compressRadiance``

       Enables lossy compression of per-pixel output radiance values.
     - ``bool``
     - ``false``
   * - ``omni:rtx:pt:mgpu:compressAlbedo``

       Enables lossy compression of per-pixel output albedo values (needed by OptiX denoiser).
     - ``bool``
     - ``true``
   * - ``omni:rtx:pt:mgpu:compressNormals``

       Enables lossy compression of per-pixel output normal values (needed by OptiX denoiser).
     - ``bool``
     - ``true``
   * - ``omni:rtx:multiThreading:enabled``

       Enabling multi-threading improves UI responsiveness.
     - ``bool``
     - ``true``

Global Volumetric Effects
~~~~~~~~~~~~~~~~~~~~~~~~~

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 70 15 15

   * - USD Attribute
     - Type
     - Default
   * - ``omni:rtx:pt:ptvol:raySky``

       Enables an additional medium of Rayleigh-scattering particles to simulate a physically based sky.
     - ``bool``
     - ``false``
   * - ``omni:rtx:pt:ptvol:raySkyScale``

       Scales the size of the Rayleigh sky.
     - ``float``
     - ``1.0``
   * - ``omni:rtx:pt:ptvol:raySkyDomelight``

       If a domelight is rendered for the sky color, the Rayleigh atmosphere is applied to the foreground while the background sky color is left unaffected.
     - ``bool``
     - ``false``

Anti-Aliasing
~~~~~~~~~~~~~

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 70 15 15

   * - USD Attribute
     - Type
     - Default
   * - ``omni:rtx:pt:pixelFilter:filter``

       Sampling pattern used for anti-aliasing. Select from ``box``, ``triangle``, ``gaussian``, and ``uniform``.
     - ``token``
     - ``"triangle"``
   * - ``omni:rtx:pt:pixelFilter:radius``

       Sampling footprint radius, in pixels, when generating samples with the selected anti-aliasing pattern.
     - ``float``
     - ``1.0``
