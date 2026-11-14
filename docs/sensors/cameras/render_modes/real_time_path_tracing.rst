.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-cameras-render-modes-real-time-path-tracing:

Real-Time Path Tracing
======================

Real-Time Path Tracing (RTPT) is the default render mode. It renders global illumination, reflections and shadows, using cached lighting to reduce the work per frame.

Select ``RealTimePathTracing`` on the RenderProduct. See :doc:`../render_modes`
for equivalent USDA and Python authoring examples.

See :doc:`../outputs` for this mode's outputs, including ``SelectionState`` for
custom selection drawing with :doc:`SPG <../../../examples/c_selection_spg>`.

DLSS Frame Generation
---------------------

:doc:`DLSS Frame Generation <real_time_path_tracing/frame_generation>` inserts
interpolated color frames between simulated frames for smoother presentation.

Settings
--------

Sampling and Caching
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``bool omni:rtx:rtpt:cached:enabled = true``
     - Enables caching path-tracing results for improved performance at the cost of some accuracy.
   * - ``bool omni:rtx:rtpt:lightcache:cached:enabled = true``
     - Enables the many-light sampling algorithm, which can improve performance in scenes with many lights.
   * - ``bool omni:rtx:rtpt:ris:meshLights = false``
     - Enables direct illumination sampling of geometry with emissive materials. See :doc:`../../../lights/mesh_lights`.

Ray Bounces and Shading
~~~~~~~~~~~~~~~~~~~~~~~

``omni:rtx:rtpt:maxBounces``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Maximum number of ray bounces for any ray type. Higher values give more accurate global illumination, but worse performance.

| Type: ``uint`` | Default: ``3``

.. grid:: 3
   :class-container: setting-comparison

   .. grid-item-card:: maxBounces = 2
      :img-top: ../../../img/settings/rtpt/settings_rtpt_maxBounces.Camera.LdrColor.maxBounces-2.0001.avif
      :link: ../../../_images/settings_rtpt_maxBounces.Camera.LdrColor.maxBounces-2.0001.avif
      :link-type: url

   .. grid-item-card:: maxBounces = 3
      :img-top: ../../../img/settings/rtpt/settings_rtpt_maxBounces.Camera.LdrColor.maxBounces-3.0001.avif
      :link: ../../../_images/settings_rtpt_maxBounces.Camera.LdrColor.maxBounces-3.0001.avif
      :link-type: url

   .. grid-item-card:: maxBounces = 23
      :img-top: ../../../img/settings/rtpt/settings_rtpt_maxBounces.Camera.LdrColor.maxBounces-23.0001.avif
      :link: ../../../_images/settings_rtpt_maxBounces.Camera.LdrColor.maxBounces-23.0001.avif
      :link-type: url

``omni:rtx:rtpt:extraSpecularAndTransmissiveBounces``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Additional number of specular and transmission ray bounces beyond ``maxBounces``. Affects reflections and refractions through transparent materials like glass.

| Type: ``uint`` | Default: ``0``

..
   The comparisons below use ``maxBounces = 2``.

   .. grid:: 3
      :class-container: setting-comparison

      .. grid-item-card:: extraSpecularAndTransmissiveBounces = 0
         :img-top: ../../../img/settings/rtpt/settings_rtpt_extraSpecularAndTransmissiveBounces.Camera.LdrColor.extraSpecularAndTransmissiveBounces-0.0001.avif
         :link: ../../../_images/settings_rtpt_extraSpecularAndTransmissiveBounces.Camera.LdrColor.extraSpecularAndTransmissiveBounces-0.0001.avif
         :link-type: url

      .. grid-item-card:: extraSpecularAndTransmissiveBounces = 2
         :img-top: ../../../img/settings/rtpt/settings_rtpt_extraSpecularAndTransmissiveBounces.Camera.LdrColor.extraSpecularAndTransmissiveBounces-2.0001.avif
         :link: ../../../_images/settings_rtpt_extraSpecularAndTransmissiveBounces.Camera.LdrColor.extraSpecularAndTransmissiveBounces-2.0001.avif
         :link-type: url

      .. grid-item-card:: extraSpecularAndTransmissiveBounces = 23
         :img-top: ../../../img/settings/rtpt/settings_rtpt_extraSpecularAndTransmissiveBounces.Camera.LdrColor.extraSpecularAndTransmissiveBounces-23.0001.avif
         :link: ../../../_images/settings_rtpt_extraSpecularAndTransmissiveBounces.Camera.LdrColor.extraSpecularAndTransmissiveBounces-23.0001.avif
         :link-type: url

Other Ray Bounce and Shading Settings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``uint omni:rtx:rtpt:maxVolumeBounces = 3``
     - Maximum number of ray bounces for subsurface scattering (SSS).
   * - ``bool omni:rtx:pt:fractionalCutoutOpacity = true``
     - If enabled, fractional cutout opacity values are treated as a measure of surface 'presence', resulting in a translucency effect similar to alpha-blending.
   * - ``float omni:rtx:rtpt:maxRoughness = 0.3``
     - Roughness threshold above which a surface is considered rough and rendered with performance-favoring approximations.
   * - ``bool omni:rtx:rtpt:translucency:virtualMotion:enabled = true``
     - Enables motion vectors for translucent (refractive) objects, which can improve temporal rendering such as denoising but can reduce performance.

.. _rtpt-material-transmission-override:

Material Transmission Override
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Real-Time Path Tracing analyzes materials to identify surfaces that light can
pass through, using known parameter names and their values to refine the
classification. For example, RTPT can trace an extra ray past a glass surface to
collect depth, normals, and material data from the object behind it. This lets
screen-space subsurface scattering operate on that object instead of the glass.
The classification also affects opaque-only XR depth and translucent-pixel
compositing; it does not change the material's transmission shader.

Parameter matching works for built-in materials with recognized parameters, but
custom MDL and MaterialX materials may use parameters the renderer does not
recognize. In those cases, use ``omni:rtx:enableTransmission`` to override the
automatic translucency classification.

Author the custom boolean attribute on the bound **Material prim**, not on its
Shader child, geometry, or RenderProduct.

To clear the material's translucency flag, add this declaration inside the existing
Material prim:

.. code-block:: usda

   custom bool omni:rtx:enableTransmission = false

For specular translucency, the override applies only when the material is already
classified as translucent and no recognized transmission-driving parameter is found. Recognized parameters
take precedence, including ``enable_specular_transmission``, ``transmission_factor``,
registered specular-transmission parameters, and ``transmission_color_texture``
when ``transmission_color`` is zero. For those materials, change the shader's
transmission inputs instead.

Leave the attribute unauthored to use the material-derived classification. Setting
it to ``true`` retains existing translucency; it cannot make a non-translucent
material transmissive.

Setting the attribute to ``true`` also clears a diffuse-transmissive material's
diffuse-transmission flag when the material has no ``enable_diffuse_transmission``
parameter. Leave the attribute unauthored to preserve that automatic classification.

.. note::

   This changes material classification, not the shader's transmission behavior.
   It does not disable transmission in Path Tracing (PT). Setting it to ``false``
   also does not disable diffuse transmission or cutout opacity.

Firefly Filter
~~~~~~~~~~~~~~

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``bool omni:rtx:rtpt:fireflyFilter:enabled = true``
     - Enables the firefly filter.
   * - ``float omni:rtx:rtpt:fireflyFilter:maxUnexposedIntensityPerSample = 3200.0``
     - Clamps the maximum ray intensity for glossy bounces. Can help prevent fireflies, but can result in energy loss. Automatically scaled with exposure.
   * - ``float omni:rtx:rtpt:fireflyFilter:maxUnexposedIntensityPerSampleDiffuse = 3200.0``
     - Clamps the maximum ray intensity for diffuse bounces. Can help prevent fireflies, but can result in energy loss. Automatically scaled with exposure.
   * - ``float omni:rtx:rtpt:fireflyFilter:maxPerEmissiveUnexposedIntensity = 3200.0``
     - Clamps the maximum ray intensity for emissive contribution after primary bounce. Can help prevent fireflies, but can result in energy loss. Automatically scaled with exposure.

Gaussian Splatting
~~~~~~~~~~~~~~~~~~

See :doc:`../../../geometry/gaussian_splats` for ParticleField authoring and runnable examples.

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 46 54

   * - USD declaration
     - Description
   * - ``bool omni:rtx:rtpt:gaussian:accumulatedDepth:enabled = true``
     - When enabled, Gaussian hit depth is opacity-weighted across up to ``maxGaussiansToAccumulate`` hits, producing a more stable depth than the stochastic single-hit depth. Useful for reducing ghosting in DLSS-RR.
   * - ``bool omni:rtx:rtpt:gaussian:accumulatedAlbedo:enabled = true``
     - When enabled, Gaussian SH0 albedo is opacity-weighted across up to ``maxGaussiansToAccumulate`` hits and the result sets the accumulated diffuse albedo, which usually improves image quality.
   * - ``int omni:rtx:rtpt:gaussian:maxGaussiansToAccumulate = 48``
     - Total hit budget for Gaussian depth/albedo accumulation. Values up to 48 use a single pass over the closest N hits. Values above 48 enable a multi-batch traversal that continues until the budget is reached, the 95% opacity threshold is hit, or no more candidates are found. Set to -1 for unlimited accumulation (stops only on opacity threshold or no remaining intersections). Set to 0 to disable accumulation entirely (depth/albedo accumulation settings are ignored).
   * - ``bool omni:rtx:rtpt:gaussian:nonStochastic:enabled = false``
     - When enabled, RTPT deterministically composites Gaussians in supported ParticleFields for primary camera rays instead of using stochastic transparency. This requires inline Gaussian tracing. Pipeline fallback, secondary rays, spectral materials, and shadows remain stochastic. At most three overlapping ParticleFields are composited.

.. toctree::
   :hidden:
   :maxdepth: 1

   dlss_nr
   real_time_path_tracing/frame_generation

Related
-------

- :doc:`../render_modes`
- :doc:`dlss_nr`
- :doc:`../outputs`
