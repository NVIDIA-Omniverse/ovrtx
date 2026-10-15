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
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``uint omni:rtx:pt:samplesPerPixel = 512``
     - Maximum number of samples to accumulate per pixel. When this count is reached, rendering stops until a scene or setting change is detected. Set to 0 to remove this limit.
   * - ``int omni:rtx:pt:samplesPerIteration = 1``
     - Number of samples per pixel, per iteration. Multiple iterations can be run per launch to reduce kernel launch overhead.
   * - ``bool omni:rtx:pt:adaptiveSampling:enabled = false``
     - When enabled, noise values are computed for each pixel, and upon reaching the threshold level the pixel is no longer sampled.
   * - ``uint omni:rtx:pt:limits:maxBounces = 4``
     - Maximum number of ray bounces for any ray type. Higher values give more accurate results, but worse performance.
   * - ``uint omni:rtx:pt:limits:extraSpecularAndTransmissiveBounces = 2``
     - Maximum number of ray bounces for specular and transmission.
   * - ``uint omni:rtx:pt:maxVolumeBounces = 15``
     - Maximum number of ray bounces for SSS.
   * - ``uint omni:rtx:pt:limits:maxFogBounces = 2``
     - Maximum number of bounces for volume scattering within a fog/sky volume.
   * - ``bool omni:rtx:pt:fractionalCutoutOpacity = true``
     - If disabled, material opacity is considered binary: values greater than or equal to 0.5 are considered opaque, while values less than 0.5 are considered transparent.

Denoising
~~~~~~~~~

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``bool omni:rtx:pt:denoising:enabled = true``
     - Runs the selected denoiser on the image.
   * - ``bool omni:rtx:pt:denoising:optix:temporal = false``
     - Uses motion information to reduce frame-to-frame flickering artifacts in the denoiser.
   * - ``float omni:rtx:pt:denoising:blendFactor = 0.0``
     - Blend factor indicating how much to blend the denoised image with the original. 0 shows only the denoised image, 1.0 shows no denoising.
   * - ``bool omni:rtx:pt:denoising:optix:denoiseAOVs = true``
     - If enabled, the OptiX Denoiser also denoises additional render variables alongside the color output.

Sampling and Caching
~~~~~~~~~~~~~~~~~~~~

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``bool omni:rtx:pt:radianceCache:enabled = true``
     - Enables caching path-tracing results for improved performance at the cost of some accuracy.
   * - ``bool omni:rtx:pt:lightCache:enabled = true``
     - Enables the many-light sampling algorithm, which can improve performance in scenes with many lights.
   * - ``bool omni:rtx:pt:ris:meshLights = false``
     - Enables direct illumination sampling of geometry with emissive materials.
   * - ``bool omni:rtx:pathtracing:rayguide:cached:enabled = false``
     - Enables caching lighting results for improving surface ray sampling directions.

Firefly Filter
~~~~~~~~~~~~~~

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``bool omni:rtx:pt:fireflyFilter:enabled = true``
     - Enables the firefly filter.
   * - ``float omni:rtx:pt:fireflyFilter:maxUnexposedIntensityPerSample = 3200.0``
     - Clamps the maximum ray intensity for glossy bounces. Can help prevent fireflies, but can result in energy loss. Automatically scaled with exposure.
   * - ``float omni:rtx:pt:fireflyFilter:maxUnexposedIntensityPerSampleDiffuse = 3200.0``
     - Clamps the maximum ray intensity for diffuse bounces. Can help prevent fireflies, but can result in energy loss. Automatically scaled with exposure.
   * - ``float omni:rtx:pt:fireflyFilter:maxPerEmissiveUnexposedIntensity = 3200.0``
     - Clamps the maximum ray intensity for emissive contribution after primary bounce. Can help prevent fireflies, but can result in energy loss. Automatically scaled with exposure.

Spectral Rendering
~~~~~~~~~~~~~~~~~~

See :doc:`spectral_rendering` for startup configuration, physical illuminants,
and RGB-versus-spectral comparisons.

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``bool omni:rtx:pathtracing:spectral:enabled = false``
     - Enables spectral rendering.
   * - ``float omni:rtx:pathtracing:spectral:wavelengthMin = 10.0``
     - Minimum simulated wavelength in nanometers.
   * - ``float omni:rtx:pathtracing:spectral:wavelengthMax = 10000.0``
     - Maximum simulated wavelength in nanometers.
   * - ``string omni:rtx:renderingColorSpace = "lin_rec709_scene"``
     - Color space input is converted from and to spectral.
   * - ``uint omni:rtx:pathtracing:spectral:responseCurve = 0``
     - Response curve to convert spectral to CIE XYZ.

Non-Uniform Volumes
~~~~~~~~~~~~~~~~~~~

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``bool omni:rtx:pt:ptvol:enabled = false``
     - Enables path-traced non-uniform volumes.
   * - ``token omni:rtx:pt:volumes:transmittanceMethod = "biasedRayMarching"``
     - Choose between ``biasedRayMarching`` or ``ratioTracking``. Biased ray marching is the ideal option in all cases.
   * - ``int omni:rtx:pt:volumes:tracking:maxScatteringSteps = 1024``
     - Maximum delta tracking steps between bounces. Increase for highly scattering volumes like clouds.
   * - ``int omni:rtx:pt:volumes:tracking:maxShadowSteps = 32``
     - Maximum ratio tracking delta steps for shadow rays. Increase for highly scattering volumes like clouds.
   * - ``uint omni:rtx:pt:limits:maxVolumeBounces = 2``
     - Maximum number of bounces in non-uniform volumes.

Multi-GPU
~~~~~~~~~

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``bool omni:rtx:pt:multigpu:enabled = true``
     - Enables rendering across multiple GPUs when available.
   * - ``bool omni:rtx:pt:mgpu:autoLoadBalancing:enabled = true``
     - Automatically balance path-tracing work across GPUs in a multi-GPU configuration.
   * - ``bool omni:rtx:pt:mgpu:compressRadiance = false``
     - Enables lossy compression of per-pixel output radiance values.
   * - ``bool omni:rtx:pt:mgpu:compressAlbedo = true``
     - Enables lossy compression of per-pixel output albedo values (needed by OptiX denoiser).
   * - ``bool omni:rtx:pt:mgpu:compressNormals = true``
     - Enables lossy compression of per-pixel output normal values (needed by OptiX denoiser).
   * - ``bool omni:rtx:multiThreading:enabled = true``
     - Enabling multi-threading improves UI responsiveness.

Global Volumetric Effects
~~~~~~~~~~~~~~~~~~~~~~~~~

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``bool omni:rtx:pt:ptvol:raySky = false``
     - Enables an additional medium of Rayleigh-scattering particles to simulate a physically based sky.
   * - ``float omni:rtx:pt:ptvol:raySkyScale = 1.0``
     - Scales the size of the Rayleigh sky.
   * - ``bool omni:rtx:pt:ptvol:raySkyDomelight = false``
     - If a domelight is rendered for the sky color, the Rayleigh atmosphere is applied to the foreground while the background sky color is left unaffected.

Anti-Aliasing
~~~~~~~~~~~~~

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``token omni:rtx:pt:pixelFilter:filter = "triangle"``
     - Sampling pattern used for anti-aliasing. Select from ``box``, ``triangle``, and ``gaussian``. ``uniform`` is deprecated and is rendered as ``box``.
   * - ``float omni:rtx:pt:pixelFilter:radius = 1.0``
     - Sampling footprint radius, in pixels, when generating samples with the selected anti-aliasing pattern.
