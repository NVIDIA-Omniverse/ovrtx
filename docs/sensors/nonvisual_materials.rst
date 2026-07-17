.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Non-Visual Materials
====================

Non-visual material labels let lidar, radar, and acoustic sensors map USD
materials to sensor-return behavior. The visual material can remain ordinary;
sensor semantics come from custom attributes on the bound ``Material`` prim.

Author Labels
-------------

.. tab-set::

   .. tab-item:: Python Example Scene

      .. literalinclude:: ../../examples/python/radar/radar_example.usda
         :language: usda
         :start-after: # [snippet:configure-nonvisual-materials]
         :end-before: # [/snippet:configure-nonvisual-materials]

   .. tab-item:: C Example Scene

      .. literalinclude:: ../../examples/c/radar/radar_example.usda
         :language: usda
         :start-after: # [snippet:configure-nonvisual-materials]
         :end-before: # [/snippet:configure-nonvisual-materials]

The default runtime prefix is ``omni:simready:nonvisual``. The alternate
supported prefix is ``inputs:nonvisual``, selected by
``/rtx/materialDb/nonVisualMaterialSemantics/prefix``. Public examples may
author both prefixes so scenes work with either runtime setting.

Labels belong on the ``Material`` prim that geometry binds through
``material:binding``. Use :doc:`../scene/material_binding` when the geometry
still needs to be bound to the material.

Base Materials
--------------

Use exact base-material strings. Common values include:

.. list-table::
   :header-rows: 1

   * - Category
     - Values
   * - Default
     - ``none``
   * - Metals
     - ``aluminum``, ``steel``, ``oxidized_steel``, ``iron``,
       ``oxidized_iron``, ``silver``, ``brass``, ``bronze``,
       ``oxidized_Bronze_Patina``, ``tin``
   * - Polymers
     - ``plastic``, ``fiberglass``, ``carbon_fiber``, ``vinyl``,
       ``plexiglass``, ``pvc``, ``nylon``, ``polyester``
   * - Glass
     - ``clear_glass``, ``frosted_glass``, ``one_way_mirror``, ``mirror``,
       ``ceramic_glass``
   * - Other
     - ``asphalt``, ``concrete``, ``leaf_grass``, ``dead_leaf_grass``,
       ``rubber``, ``wood``, ``bark``, ``cardboard``, ``paper``, ``fabric``,
       ``skin``, ``fur_hair``, ``leather``, ``marble``, ``brick``, ``stone``,
       ``gravel``, ``dirt``, ``mud``, ``water``, ``salt_water``, ``snow``,
       ``ice``, ``calibration_lambertian``

``none`` and ``calibration_lambertian`` map to default-material behavior. Other
base materials default to composite-material behavior.

Coatings and Attributes
-----------------------

.. list-table::
   :header-rows: 1

   * - Kind
     - Values
   * - Coating
     - ``none``, ``paint``, ``clearcoat``, ``paint_clearcoat``
   * - Attribute flags
     - ``none``, ``emissive``, ``retroreflective``, ``single_sided``,
       ``visually_transparent``

Attributes are encoded as a bit field, so multiple attributes can be combined
when the USD representation supports a list.

Troubleshooting
---------------

- If every object behaves like the same material, check that the runtime prefix
  matches the authored prefix.
- Preserve coating and attribute flags unless base-material-only behavior is
  intentional.
- ``MaterialId`` lidar channels can be used to debug which material id was
  assigned to a hit.
- Semantic labels for segmentation are separate from non-visual material labels.
  Refer to :doc:`../scene/semantic_labels` for semantic class labels.
