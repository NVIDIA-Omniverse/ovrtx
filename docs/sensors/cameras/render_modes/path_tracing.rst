.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-cameras-render-modes-path-tracing:

Path Tracing
============

Path Tracing mode uses progressive sampling to reduce image noise as samples
accumulate. Use it for offline or reference images when convergence time is
acceptable.

Select ``PathTracing`` on the RenderProduct. See :doc:`../render_modes`
for equivalent USDA and Python authoring examples.

.. _sensors-cameras-render-modes-path-tracing-convergence:

Warm-Up
-------

Path Tracing can accumulate multiple passes within a step. The number depends
on the initial-frame quality and minimum-accumulation settings; a step does
not unconditionally reach the sample limit. Texture availability can still
matter when the first captured frame needs high-resolution mips. See
:ref:`Warming up the renderer <sensors-common-output-configuration-warmup>`.

The output's ``progression`` and ``converged`` fields report accumulation
progress and whether a stopping criterion was reached. A zero
``omni:rtx:pt:samplesPerPixel`` removes the sample-count limit.
:py:meth:`~ovrtx.Renderer.reset` (:c:func:`ovrtx_reset()` in C) discards
accumulated rendering history. See :py:class:`~ovrtx.FrameOutput` and
:c:type:`ovrtx_render_product_frame_output_t` for the output fields.

See :doc:`../outputs` for this mode's outputs, including ``SelectionState`` for
custom selection drawing with :doc:`SPG <../../../examples/c_selection_spg>`.

.. _sensors-cameras-render-modes-path-tracing-settings:

Settings
--------

Author these settings on the RenderProduct, except for the global multi-GPU
setting noted below. See :doc:`Output Configuration <../../common/output_configuration>`
for authoring and runtime updates.

.. _sensors-cameras-render-modes-path-tracing-sampling:

Path Tracing
~~~~~~~~~~~~

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``uint omni:rtx:pt:samplesPerPixel = 512``
     - Maximum number of samples to accumulate per pixel. When this count is reached, rendering stops until a scene or setting change is detected. Set to 0 to remove this limit.
   * - ``int omni:rtx:pt:samplesPerIteration = 1``
     - Number of samples per pixel, per iteration. Multiple iterations can be run per launch to reduce iteration-batching overhead. Values above ``omni:rtx:pt:clampSpp`` are clamped to it.
   * - ``int omni:rtx:pt:clampSpp = 32``
     - Upper bound on ``samplesPerIteration``. Set to 0 to disable the clamp.
   * - ``bool omni:rtx:pt:adaptiveSampling:enabled = false``
     - When enabled, noise values are computed for each pixel, and upon reaching the threshold level the pixel is no longer sampled.
   * - ``float omni:rtx:pt:adaptiveSampling:targetError = 0.001``
     - Target error for adaptive sampling. Lower values require more sampling.
   * - ``uint omni:rtx:pt:limits:maxBounces = 4``
     - Maximum number of ray bounces for any ray type. Higher values give more accurate results, but worse performance.
   * - ``uint omni:rtx:pt:limits:extraSpecularAndTransmissiveBounces = 2``
     - Additional specular and transmission bounces beyond ``maxBounces``.
   * - ``uint omni:rtx:pt:maxVolumeBounces = 15``
     - Maximum number of bounces for subsurface scattering (SSS). Separate from ``omni:rtx:pt:limits:maxVolumeBounces``, which limits non-uniform volumes.
   * - ``uint omni:rtx:pt:limits:maxFogBounces = 2``
     - Maximum number of bounces for volume scattering within a fog/sky volume.
   * - ``bool omni:rtx:pt:fractionalCutoutOpacity = true``
     - If disabled, material opacity is considered binary: values greater than or equal to 0.5 are considered opaque, while values less than 0.5 are considered transparent.

Denoising
~~~~~~~~~

.. list-table::
   :class: compact-table
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

.. _sensors-cameras-render-modes-path-tracing-caching:

Sampling and Caching
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``bool omni:rtx:pt:radianceCache:enabled = true``
     - Enables caching path-tracing results for improved performance at the cost of some accuracy. Cached contributions are omitted from :doc:`light path expression <../light_path_expressions>` outputs.
   * - ``bool omni:rtx:pt:lightCache:enabled = true``
     - Enables the many-light sampling algorithm, which can improve performance in scenes with many lights.
   * - ``bool omni:rtx:pt:ris:meshLights = false``
     - Enables direct illumination sampling of geometry with emissive materials.

.. _sensors-cameras-render-modes-path-tracing-firefly-filter:

Firefly Filter
~~~~~~~~~~~~~~

.. list-table::
   :class: compact-table
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

.. list-table::
   :class: compact-table
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
   * - ``uint omni:rtx:pathtracing:spectral:responseCurve = 0``
     - Response curve to convert spectral to CIE XYZ.

Non-Uniform Volumes
~~~~~~~~~~~~~~~~~~~

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``bool omni:rtx:pt:ptvol:enabled = false``
     - Enables path-traced non-uniform volumes.
   * - ``token omni:rtx:pt:volumes:transmittanceMethod = "biasedRayMarching"``
     - Choose between ``biasedRayMarching`` or ``ratioTracking``.
   * - ``int omni:rtx:pt:volumes:tracking:maxScatteringSteps = 1024``
     - Maximum delta tracking steps between bounces. Increase for highly scattering volumes like clouds.
   * - ``int omni:rtx:pt:volumes:tracking:maxShadowSteps = 32``
     - Maximum ratio tracking delta steps for shadow rays. Increase for highly scattering volumes like clouds.
   * - ``uint omni:rtx:pt:limits:maxVolumeBounces = 2``
     - Maximum number of bounces in non-uniform volumes.

.. _sensors-cameras-render-modes-path-tracing-multi-gpu:

Multi-GPU
~~~~~~~~~

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``bool omni:rtx:pt:multigpu:enabled = true``
     - Enables rendering across multiple GPUs when available. Author this global setting on the stage's RenderSettings prim; see :ref:`sensors-common-output-configuration-global-settings`.
   * - ``bool omni:rtx:pt:mgpu:autoLoadBalancing:enabled = true``
     - Automatically balance path-tracing work across GPUs in a multi-GPU configuration.
   * - ``bool omni:rtx:pt:mgpu:compressRadiance = false``
     - Enables lossy compression of per-pixel output radiance values.
   * - ``bool omni:rtx:pt:mgpu:compressAlbedo = true``
     - Enables lossy compression of per-pixel output albedo values (needed by OptiX denoiser).
   * - ``bool omni:rtx:pt:mgpu:compressNormals = true``
     - Enables lossy compression of per-pixel output normal values (needed by OptiX denoiser).
   * - ``bool omni:rtx:multiThreading:enabled = true``
     - Prepares rendering commands concurrently across multiple GPUs. It has no effect with one GPU; disabling it serializes that work.

Global Volumetric Effects
~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :class: compact-table
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

.. _sensors-cameras-render-modes-path-tracing-anti-aliasing:

Anti-Aliasing
~~~~~~~~~~~~~

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``token omni:rtx:pt:pixelFilter:filter = "triangle"``
     - Sampling pattern used for anti-aliasing. Select from ``box``, ``triangle``, and ``gaussian``. ``uniform`` is deprecated and is rendered as ``box``.
   * - ``float omni:rtx:pt:pixelFilter:radius = 1.0``
     - Sampling footprint radius, in pixels, when generating samples with the selected anti-aliasing pattern.

.. _camera-aov-compositing:

Compositing and Back to Beauty
------------------------------

Path Tracing can separate the final image, or *beauty*, into seven lighting
contributions. You can adjust those contributions independently and add them
back together. Work with their linear RGB values before applying tone mapping
or a display transform.

.. figure:: ../../../img/aov-compositing.avif
   :width: 100%
   :alt: Path Tracing scene containing diffuse, reflective, transmissive, emissive, and volume objects, reconstructed from seven lighting outputs
   :align: center
   :target: ../../../examples/python_aov_compositing.html

   *The seven lighting outputs reconstruct this scene, including its volume
   and visible background. The example compares the result with the rendered beauty.*

The following expression lists the complete additive set. Each name refers to
the RGB channels of its :ref:`RenderVar <camera-output-tables>`:

.. math::

   \begin{aligned}
   \mathrm{Beauty}_{\mathrm{linear}} \approx{}&
       \mathrm{PtDirectIllumation}
       + \mathrm{PtGlobalIllumination} \\
       &+ \mathrm{PtReflections}
       + \mathrm{PtRefractions} \\
       &+ \mathrm{PtSubsurfaceScattering}
       + \mathrm{PtSelfIllumination}
       + \mathrm{PtVolumes}.
   \end{aligned}

Request these seven RenderVars through ``orderedVars`` on the same
``PathTracing`` RenderProduct. Capture them from the same completed frame.
Use an explicit list: adding every output whose name starts with ``Pt``
would also add filters, geometry data, and duplicate contributions.
Convert float16 values to float32 before summing. Do not sum alpha; coverage
and foreground masks require their own compositing operation.

The passes separate paths by the initial scattering contribution. Subsequent
lighting along a reflected or transmitted path remains in that pass.
The table below explains which contributions are included.

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 28 72

   * - :ref:`Output <camera-output-tables>`
     - Contribution
   * - ``PtDirectIllumation``
     - Direct diffuse reflection. Direct glossy highlights belong to ``PtReflections``.
   * - ``PtGlobalIllumination``
     - Indirect diffuse reflection. Reflected or transmitted views of other surfaces remain in the corresponding reflection or transmission pass.
   * - ``PtReflections``
     - Direct and indirect glossy/specular reflection. It already includes direct specular highlights; there is no additional highlight term in this sum.
   * - ``PtRefractions``
     - Direct and indirect glossy/specular transmission, such as glass.
   * - ``PtSubsurfaceScattering``
     - Direct and indirect diffuse transmission, including subsurface scattering. It is separate from glossy/specular transmission.
   * - ``PtSelfIllumination``
     - Emission, light hits, and environment misses seen directly by the camera. Emission seen through reflection or transmission remains in those passes.
   * - ``PtVolumes``
     - Direct and indirect paths whose initial scattering contribution is in a volume.

:ref:`PtBackground <camera-output-tables>` is useful for separate
background and matte operations. Do not add it to this sum: the directly
visible background is already in :ref:`PtSelfIllumination <camera-output-tables>`.
Normals, depth, motion, IDs, masks, and diagnostic buffers are also excluded.

.. _camera-aov-filters:

Lighting and Material Filters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The seven passes contain material-weighted radiance. Add them as they are.
Do not multiply them again by :ref:`PtDiffuseFilter, PtReflectionFilter,
PtRefractionFilter, or PtSubsurfaceFilter <camera-output-tables>`.
Those outputs describe material color filters; they are neither extra
lighting terms nor a required multiplication step for this reconstruction.

The RenderVar setting ``sourceType = "raw"`` selects a named renderer
output. Here, *raw* does not mean lighting with its material filter divided
out. This distinction matters when adapting a compositor built for another
renderer.

Matching the Beauty
~~~~~~~~~~~~~~~~~~~

Use :ref:`HdrColor <camera-output-tables>` as the linear comparison target
when its denoising and processing match the exported passes. Use
:ref:`PtPreDenoisedResult <camera-output-tables>` when checking the
accumulated result before denoising. Finite sampling and independently stored
float16 outputs can produce small differences; test a numerical tolerance
instead of requiring identical bytes.

Keep exposure, denoising, tone mapping, color correction, and display encoding
consistent with the reference:

* For a comparison without denoising, disable denoising for both the beauty
  and its component passes.
* For denoised reconstruction, enable
  ``omni:rtx:pt:denoising:enabled`` and
  ``omni:rtx:pt:denoising:optix:denoiseAOVs`` on the RenderProduct.
  Denoising only the beauty does not produce matching component passes.
* Add the linear values first, then apply the same exposure and display
  pipeline as the reference. Do not apply an exposure adjustment twice, and
  do not add tone-mapped or sRGB-encoded pass previews.
  The supplied PT example's lighting outputs already include camera exposure;
  it applies no additional exposure multiplier to the sum.
* To compare with :ref:`LdrColor <camera-output-tables>`, also reproduce
  its tone-map operator, display transfer, clipping, and output quantization.
  Applying the sRGB transfer alone is insufficient when tone mapping is enabled.

The :doc:`Python AOV compositing example <../../../examples/python_aov_compositing>`
provides a fixed scene, capture scripts, the seven-pass sum, and a numerical
comparison. Its ACES Approximation and sRGB conversion matches that scene's
configuration; it is not a replacement for every possible renderer color pipeline.

.. toctree::
   :hidden:
   :maxdepth: 1

   spectral_rendering

Related
-------

- :doc:`spectral_rendering`
- :doc:`../light_path_expressions`
- :doc:`../outputs`
