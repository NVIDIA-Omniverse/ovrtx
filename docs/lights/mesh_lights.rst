.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Mesh Lights
===========

Overview
--------

A mesh light is renderable geometry with a bound emissive material. Mesh lights
can represent sources whose shape would be difficult to approximate with an
intrinsic light, such as neon signs, coiled bulbs, and emissive displays.

An emissive material makes the geometry visibly glow. Mesh-light sampling is a
separate RenderProduct setting that lets ovrtx explicitly sample that geometry
as a direct-light source. Without sampling, the geometry remains emissive but
direct illumination from it converges much more slowly and can remain noisy at
practical sample counts.

.. |mesh-light-caption| replace:: The fluorescent bulb and TV screen remain
   emissive in both panels. The screen is a textured mesh light whose emission
   color comes from an image. At this real-time frame budget, enabling mesh-light
   sampling improves illumination of the room. Screen image:
   `Chelsea the cat <https://scikit-image.org/docs/stable/api/skimage.data.html#skimage.data.chelsea>`__,
   photographed by Stefan van der Walt and dedicated to the public domain under
   `CC0 1.0 Universal <https://creativecommons.org/publicdomain/zero/1.0/>`__.

.. figure:: ../img/light-mesh-sampling.avif
   :alt: An emissive fluorescent bulb and textured TV screen with RTPT mesh-light sampling disabled and enabled
   :align: center

   |mesh-light-caption|

Authoring a Mesh Light
----------------------

.. note::

   Do not apply ``UsdLuxMeshLightAPI`` to enable an ovrtx mesh light. Current
   RTX mesh-light discovery is driven by emissive material-bound geometry and
   ignores the API's ``light:materialSyncMode`` and ``light:shaderId`` values.

Author renderable geometry, bind an emissive material, and configure that
material's emission inputs. The following declarations describe the
``OmniEmissive`` material used by the example:

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 48, 52
   :class: compact-table

   "``rel material:binding``", "Binds the emissive material to the geometry."
   "``uniform asset info:mdl:sourceAsset = @OmniEmissive.mdl@``", "Selects the built-in ``OmniEmissive`` MDL material."
   "``color3f inputs:emissive_color = (1, 1, 1)``", "Sets the emitted color for ``OmniEmissive``."
   "``float inputs:emission_intensity = 200``", "Sets emission strength for ``OmniEmissive``. This is a material input, not a UsdLux intensity value."

Emission parameter names, defaults, and units belong to the selected material.
Other emissive MDL or USD Preview Surface materials use their own inputs.

The following examples create a simple emissive mesh and bind its material:

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/usd/data/mesh_lights.usda
         :language: usda
         :start-after: # [snippet:doc-mesh-light]
         :end-before: # [/snippet:doc-mesh-light]
         :dedent: 4

   .. tab-item:: USD Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-mesh-light-python]
         :end-before: # [/snippet:doc-mesh-light-python]
         :dedent:

Enabling Mesh-Light Sampling
----------------------------

Mesh-light sampling is disabled by default. Enable the setting that belongs to
the active render mode on each RenderProduct that should sample emissive
geometry:

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 48, 52
   :class: compact-table

   "``bool omni:rtx:pt:ris:meshLights = false``", "Enables mesh-light sampling in Path Tracing mode."
   "``bool omni:rtx:rtpt:ris:meshLights = false``", "Enables mesh-light sampling in Real-Time Path-Tracing mode."

Minimal mode does not support mesh-light sampling. Authoring both settings is
safe when a RenderProduct may switch between Path Tracing and Real-Time
Path-Tracing; only the setting for the active mode is consumed.

The following examples enable mesh-light sampling for both supported modes:

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/usd/data/mesh_lights.usda
         :language: usda
         :start-after: # [snippet:doc-enable-mesh-light-sampling]
         :end-before: # [/snippet:doc-enable-mesh-light-sampling]

   .. tab-item:: USD Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-enable-mesh-light-sampling-python]
         :end-before: # [/snippet:doc-enable-mesh-light-sampling-python]
         :dedent:

Limitations
-----------

The physical-lighting schemas do not support mesh lights.
``PhysicalLightIlluminantAPI`` and ``PhotometricAreaLightAPI`` cannot be
applied to mesh geometry, so mesh lights cannot use their illuminant spectra,
lumens, or lux-at-distance controls. Mesh-light color and brightness come from
the bound material's emission values instead. A material may provide its own
physically meaningful emission controls, but those controls are
material-specific and are not part of the physical-lighting schemas.

ovrtx supports at most 16,777,216 (2^24) mesh-light geometries in a scene. Additional
eligible geometries are not added to the mesh-light sampling buffer. Large
numbers of emissive meshes or triangles also increase sampling and scene-update
costs.

Further Reading
---------------

Refer to :doc:`../materials/material_binding` for material binding and to
:doc:`../sensors/cameras/render_modes` for render-mode configuration.
