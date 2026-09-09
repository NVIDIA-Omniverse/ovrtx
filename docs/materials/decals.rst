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

Decals project MDL materials onto mesh geometry without modifying the geometry itself, as if they were stickers. A decal defines a volumetric bounding region (a clipbox) and a projector. At render time, the decal overlays its material on the surface material of bound mesh geometry that intersects the clipbox.

Use decals to add labels, dirt, wear, or markings without requiring separate geometry or UV mapping changes. Multiple decals can overlap the same surface and are composited in priority order. Up to six decals can be active at any surface point.

.. note::

   Decals differ from :doc:`UV projectors <projectors>`. UV projectors generate or replace a primitive's UV texture coordinates. Decals project a separate MDL material onto a mesh at render time and overlay its existing material.

.. figure:: ../img/decals.avif
   :align: center
   :width: 100%
   :alt: Two bottles with multiple overlapping decorative decals layered on their surfaces

   *Several decals layered on the front of two objects.*

Creating a Decal
----------------

Define an ``OmniDecal`` prim to create a decal. Its ``extent`` attribute defines the local-space clipbox, and ``material:binding`` selects the MDL material to overlay. The material prim must contain an authored MDL shader network to produce a visible result.

This example creates a planar decal and binds a placeholder ``/World/Looks/DecalMaterial`` material. Replace the placeholder with an authored MDL shader network to produce a visible decal:

.. literalinclude:: ../../tests/docs/usd/data/decal.usda
   :language: usda
   :start-after: # [snippet:doc-create-decal]
   :end-before: # [/snippet:doc-create-decal]

The decal's transform and ``extent`` position and size the clipbox. The ``OmniDecal`` schema inherits ``OmniProjectorAPI``, so projector attributes control how the decal computes UV coordinates within that region.

Binding a Decal to a Prim
-------------------------

Apply the multiple-apply ``OmniCoordSysAPI`` to receiving geometry and bind that instance to the decal prim. This extended example adds a Cube, applies ``OmniCoordSysAPI:Decal``, and targets ``/World/Decal`` through the corresponding ``coordSys:Decal:binding`` relationship:

.. literalinclude:: ../../tests/docs/usd/data/decal_binding.usda
   :language: usda
   :start-after: # [snippet:doc-bind-decal]
   :end-before: # [/snippet:doc-bind-decal]

The ``Decal`` instance name identifies this binding. Use a unique ``OmniCoordSysAPI`` instance for each additional decal bound to the same prim. You can bind one decal to multiple prims, or apply the binding to a parent prim to affect mesh descendants.

OmniDecal Attributes
--------------------

``OmniDecal`` defines the following attributes:

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1

   * - Attribute
     - Meaning
   * - ``omni:decal:enabled``
     - Enables or disables the decal. A disabled decal has no effect, equivalent
       to setting the prim's visibility to ``invisible``.
   * - ``extent``
     - Defines the decal's local-space clipbox as minimum and maximum points. A
       surface point must be inside this box to receive the decal.
   * - ``omni:decal:faceMode``
     - Selects which side of a mesh receives the decal. Refer to
       :ref:`Face Modes <decal_face_modes>`.
   * - ``omni:decal:priority``
     - Sets composition order when decals overlap. Higher values render above
       lower values. Negative values are valid.
   * - ``omni:decal:outputSpace``
     - Selects the output UV set: 0 for ``st``, 1 for ``st1``, 2 for ``st2``,
       or 3 for ``st3``.

Inherited Projector Attributes
------------------------------

``OmniDecal`` inherits the attributes of ``OmniProjectorAPI``. These attributes control how UV coordinates are computed inside the clipbox. Refer to :ref:`OmniProjectorAPI Attributes <projector_attributes>` and :ref:`Projector Types <projector_types>`.

.. _decal_face_modes:

Face Modes
----------

``omni:decal:faceMode`` accepts the following values:

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1

   * - Value
     - Effect
   * - ``front``
     - Applies the decal only to the front side of the mesh. This is the
       default.
   * - ``back``
     - Applies the decal only to the back side of the mesh.
   * - ``frontAndBack``
     - Applies the decal to both sides of the mesh.

Mesh normals and the camera ray direction determine the front and back sides.

Limitations
-----------

- A maximum of six decals can be active at any surface point. If more than six overlap, only the six with the highest priority values are rendered.
- Real-Time Path-Tracing and Path Tracing support decals. Minimal rendering does not.
- Decals support cutout opacity only; transparency is not supported.
- Decals cannot cast shadows, including when an opaque decal overlays a transparent object.

For information about assigning an MDL material to a decal, refer to :doc:`material_binding`.
