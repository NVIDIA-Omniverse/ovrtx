.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Light Linking
=============

Overview
--------

Light linking controls which geometry receives illumination from a particular
light. Shadow linking independently controls which geometry casts shadows from
that light. Use these controls for selective lighting, removing an unwanted
shadow, or isolating a light to part of a scene.

Each light provides two named ``UsdCollectionAPI`` collections through
``UsdLuxLightAPI``:

.. csv-table::
   :header: "Collection", "Membership effect"
   :widths: 30, 70
   :class: compact-table

   "``lightLink``", "Members receive the light's contribution. Non-members do not."
   "``shadowLink``", "Members cast shadows from the light. Non-members do not."

By default, both collections include the pseudo-root. Every geometry prim is
therefore a member: the light illuminates the whole scene and all geometry can
cast shadows from it.

Light-Link Receivers
--------------------

Use the ``lightLink`` collection to choose which geometry receives light. The
following RTPT comparison uses the default collection, excludes the balls, and
then includes only the balls:

.. figure:: ../img/light-linking-receivers.avif
   :alt: Light-link comparison showing all geometry illuminated, balls excluded, and only balls illuminated
   :align: center

   *Light-link membership controls which geometry receives the light's contribution.*

Shadow-Link Casters
-------------------

Use the ``shadowLink`` collection to choose which geometry can block the light.
It does not control whether that geometry is illuminated. The following RTPT
comparison changes which objects cast shadows while leaving their light-link
membership unchanged:

.. figure:: ../img/light-linking-shadows.avif
   :alt: Shadow-link comparison showing all geometry casting shadows, balls excluded, and only balls casting shadows
   :align: center

   *Shadow-link membership controls which geometry casts shadows from the light.*

Collection Attributes
---------------------

Author these collection properties on the light prim:

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 48, 52
   :class: compact-table

   "``uniform bool collection:lightLink:includeRoot = true``", "Includes the pseudo-root, so all geometry receives light unless excluded. Set to false to build an explicit receiver list."
   "``uniform token collection:lightLink:expansionRule = ""expandPrims""``", "Controls whether included paths also include descendants."
   "``rel collection:lightLink:includes``", "Adds receiver paths to the collection."
   "``rel collection:lightLink:excludes``", "Removes receiver paths from the collection. Exclusions override inclusions."
   "``uniform bool collection:shadowLink:includeRoot = true``", "Includes the pseudo-root, so all geometry casts shadows unless excluded. Set to false to build an explicit caster list."
   "``uniform token collection:shadowLink:expansionRule = ""expandPrims""``", "Controls whether included paths also include descendants."
   "``rel collection:shadowLink:includes``", "Adds shadow-caster paths to the collection."
   "``rel collection:shadowLink:excludes``", "Removes shadow-caster paths from the collection. Exclusions override inclusions."

The expansion rule accepts these OpenUSD tokens:

.. csv-table::
   :header: "Token", "Behavior"
   :widths: 30, 70
   :class: compact-table

   "``explicitOnly``", "Includes only the explicitly targeted prims."
   "``expandPrims``", "Includes each targeted prim and its descendant prims. This is the default."
   "``expandPrimsAndProperties``", "Also includes properties. Property membership does not add renderable geometry to an ovrtx link."

Authoring Links
---------------

The following examples illuminate only ``Subjects`` and ``Ground``, while
excluding ``NoShadow`` from shadow casting. Built-in light types already
provide both named collections through ``UsdLuxLightAPI``.

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/usd/data/light_linking.usda
         :language: usda
         :start-after: # [snippet:doc-light-linking]
         :end-before: # [/snippet:doc-light-linking]
         :dedent: 4

   .. tab-item:: USD Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-light-linking-python]
         :end-before: # [/snippet:doc-light-linking-python]
         :dedent:

Further Reading
---------------

Refer to the `UsdLux light-linking documentation <https://openusd.org/25.05/api/class_usd_lux_light_a_p_i.html>`_
and the `UsdCollectionAPI reference <https://openusd.org/25.05/api/class_usd_collection_a_p_i.html>`_
for the complete OpenUSD collection model.
