.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _decals:

Decals
======

Overview
--------

Decals project materials onto mesh geometry without changing the geometry, like stickers. An ``OmniDecal`` prim defines a bounded volume (the clipbox), a projector, and the material to overlay. Bound mesh surfaces receive the decal where they intersect that volume.

Use decals for labels, dirt, wear, and markings that should remain independent of the receiver's geometry and UV layout. Overlapping decals are composited by priority; at most six contribute at one surface point.

.. note::

   Decals differ from :doc:`UV projectors <projectors>`. UV projectors provide texture coordinates to a primitive's material. A decal overlays a separate material on bound geometry.

.. figure:: ../img/example-decals.avif
   :align: center
   :width: 100%
   :alt: Red RTX lettering and silver NVIDIA logos projected onto a curved green logo

   *Silver NVIDIA logos overlap red RTX lettering on the curved receiver.
   Cutouts reveal lower-priority decals or the original green material.*

Creating a Decal
----------------

Define an ``OmniDecal`` prim, set its local-space ``extent``, and bind a material. ``OmniDecal`` and ``OmniCoordSysAPI`` do not have typed usd-core Python bindings, so Python authoring uses generic prim, attribute, metadata, and relationship APIs.

The following equivalent snippets create a planar decal and bind a placeholder material. Add an MDL shader network to that material for a visible result.

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/usd/data/decal.usda
         :language: usda
         :start-after: # [snippet:doc-create-decal]
         :end-before: # [/snippet:doc-create-decal]

   .. tab-item:: usd-core Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-create-decal-python]
         :end-before: # [/snippet:doc-create-decal-python]

The decal's transform and ``extent`` position and size the clipbox. The
``OmniDecal`` schema automatically applies ``OmniProjectorAPI``, whose
attributes control how the decal computes UV coordinates within that region.

Binding a Decal to a Prim
-------------------------

Apply a named ``OmniCoordSysAPI`` instance to receiving geometry and target the decal through the matching ``coordSys:<instance>:binding`` relationship. The instance name connects the applied schema to its relationship.

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/usd/data/decal_binding.usda
         :language: usda
         :start-after: # [snippet:doc-bind-decal]
         :end-before: # [/snippet:doc-bind-decal]

   .. tab-item:: usd-core Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-bind-decal-python]
         :end-before: # [/snippet:doc-bind-decal-python]

Use a unique instance name for each additional decal. A decal can target multiple receivers, and a binding authored on a parent applies to mesh descendants unless a descendant blocks or replaces it.

OmniDecal Attributes
--------------------

``OmniDecal`` defines the following attributes:

.. rst-class:: compact-table

.. csv-table::
   :header: "Declaration and default", "Behavior"
   :widths: 42, 58

   "``float3[] extent``", "Local-space minimum and maximum corners of the clipbox. This attribute has no schema default and must be authored."
   "``bool omni:decal:enabled = true``", "Enables or disables the decal."
   "``token omni:decal:faceMode = ""front""``", "Selects receiving faces; see :ref:`decal_face_modes`."
   "``int omni:decal:outputSpace = 0``", "Selects ``st``, ``st1``, ``st2``, or ``st3`` for values 0 through 3."
   "``int omni:decal:priority = 0``", "Orders overlapping decals. Higher values are composited over lower values; negative values are valid."

Projector Attributes
--------------------

``OmniDecal`` automatically applies ``OmniProjectorAPI``. Its attributes
control how UV coordinates are computed inside the clipbox. Refer to
:ref:`OmniProjectorAPI Attributes <projector_attributes>` and :ref:`Projector
Types <projector_types>`.

.. _decal_face_modes:

Face Modes
----------

``omni:decal:faceMode`` accepts the following values:

.. rst-class:: compact-table

.. csv-table::
   :header: "Value", "Effect"
   :widths: 25, 75

   "``front``", "Applies to front-facing surfaces. This is the default."
   "``back``", "Applies to back-facing surfaces."
   "``frontAndBack``", "Applies to both sides."

Front and back are classified by whether the rendering ray enters or exits the
receiver surface. Projector direction does not currently affect this
classification.

Ordering Overlapping Decals
----------------------------

Use ``omni:decal:priority`` to choose which decal appears on top where their
projected masks overlap. Higher values cover lower values. A cutout in the
top decal reveals the next lower decal, or the receiver's original material
if no lower decal applies. Assign distinct priorities when ordering matters;
do not rely on binding relationship order to break ties.

These Path Tracing renders use the same geometry, masks, and decal transforms.
Only the red decals' priority changes. Silver covers red at priority 10 versus
0; red covers silver when raised to 20. The masks' black areas remain cut out
in either order.

.. tab-set::

   .. tab-item:: Silver above red

      .. figure:: ../img/example-decals.avif
         :alt: Silver NVIDIA decals cover the upper red R and lower-right red X with silver priority 10 and red priority 0

         *Default: silver 10, red 0.*

   .. tab-item:: Red above silver

      .. figure:: ../img/example-decals-red-on-top.avif
         :alt: Upper red R and lower-right red X cover the silver NVIDIA decals after red priority is raised to 20

         *Reordered: red 20, silver 10. Placement and size are unchanged.*

Limitations
-----------

- A maximum of six decals can be active at any surface point. If more than six overlap, only the six with the highest priority values are rendered.
- Real-Time Path Tracing and Path Tracing support decals. The Minimal renderer does not.
- Cutout opacity is supported. Transmissive decal materials are not supported.
- In path-traced modes, decal cutouts contribute to shadow visibility.

For complete runnable workflows, see :doc:`../examples/python_decals` and :doc:`../examples/c_decals`. For material assignment, see :doc:`material_binding`.
