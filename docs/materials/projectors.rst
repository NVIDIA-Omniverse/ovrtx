.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _Projectors:

UV Projectors
=============

Overview
--------

UV projectors provide a method for applying UV texture coordinates to primitives in ovrtx. You can use UV projectors to apply textures to geometry that lacks proper UV texture coordinates, or override existing UV coordinates to achieve specific texture placements on objects.

UV projectors are particularly valuable when working with imported assets that have poor or missing UV mapping, allowing you to quickly apply professional texture coordinates without returning to your 3D modeling software. In this guide, you will learn how to create projectors, configure their attributes, and select the appropriate projection type for your geometry.

.. note:: UV projectors differ from projector lights. Projector lights project textures onto the scene from rectangular lights (similar to slide projectors), while UV projectors apply texture coordinates directly to geometry.

.. figure:: ../img/projectors-lineup.avif
   :alt: Four 3D objects showing different UV projection types: cubic, planar, spherical normalized, and triplanar
   :align: center
   :width: 100%

   *UV projectors applied to a variety of objects. From top to bottom: cubic, planar, spherical normalized, and triplanar projections.*

Creating a UV Projector
-----------------------

Apply ``OmniProjectorAPI`` to a transformable prim to make that prim a UV
projector. This example applies the API to a dedicated ``CubicProjection``
Xform, explicitly selects the ``cubic`` projection type, and scales the
generated UV coordinates:

.. literalinclude:: ../../examples/python/projectors/projectors.usda
   :language: usda
   :start-after: # [snippet:doc-uv-projector-api]
   :end-before: # [/snippet:doc-uv-projector-api]
   :dedent: 12

The transform of ``/World/proj_cubic/cube/CubicProjection`` defines the
projector frame. Author the projector attributes described below on this prim.

Binding the UV Projector to a Prim
----------------------------------

To use the generated coordinates on geometry, apply ``OmniCoordSysAPI`` with
the desired texture-space instance and bind it to the projector. This example
applies ``OmniCoordSysAPI:st`` to the Cube and targets the separate
``CubicProjection`` prim through ``coordSys:st:binding``:

.. literalinclude:: ../../examples/python/projectors/projectors.usda
   :language: usda
   :start-after: # [snippet:doc-uv-projector-binding]
   :end-before: # [/snippet:doc-uv-projector-binding]
   :dedent: 12

``st`` selects texture space 0. Use ``st1``, ``st2``, or ``st3`` for the other
texture spaces. You can bind the same projector to multiple prims, apply
``OmniCoordSysAPI`` to a parent prim to bind its descendants, or apply both APIs
to the same prim when a separate projector prim is unnecessary.

.. _projector_attributes:

OmniProjectorAPI Attributes
---------------------------

``OmniProjectorAPI`` defines the following attributes:

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1

   * - Attribute
     - Meaning
   * - ``omni:projector:type``
     - Selects the projection type using a coordinate system based around the
       origin of the primitive to which you apply this API. Refer to
       :ref:`Projector Types <projector_types>`.
   * - ``omni:projector:space``
     - Selects the space in which the system calculates the projection.
       *Object* applies the projection in the local space of the primitive;
       *World* applies it in world space; *Texture* takes UV coordinates from
       the texture space selected by ``omni:projector:inputSpace`` (up to four
       spaces; this mode is not yet functional). *Object meters* and *World
       meters* account for scene units, so the texture repeats instead of
       stretching when a primitive is scaled up.
   * - ``omni:projector:inputSpace``
     - Selects the texture space to read when ``omni:projector:space`` is set
       to *Texture* (up to four spaces).
   * - ``omni:projector:translate``
     - Translates the projection frame in the selected UV projector space.
   * - ``omni:projector:rotate``
     - Rotates the projection frame in the selected UV projector space.
   * - ``omni:projector:scale``
     - Scales the projection frame in the selected UV projector space.
   * - ``omni:projector:uv:translate``
     - Translates the computed projected UVs.
   * - ``omni:projector:uv:rotate``
     - Rotates the computed projected UVs.
   * - ``omni:projector:uv:scale``
     - Scales the computed projected UVs.

.. _projector_types:

Projector Types
---------------

You can apply the following types of UV projection to a primitive. The up direction is the Z axis in object space.

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1

   * - Type
     - Effect
   * - ``cubic``
     - Projects UVs from six planes, similar to how a cube would surround the
       primitive.
   * - ``cylindrical``
     - Projects UVs as if the primitive were wrapped by a capped cylinder.
   * - ``cylindricalNormalized``
     - A variant of the Cylindrical projection where the U coordinate is scaled
       to always fit within the standard [0,1] range, regardless of the
       object's size.
   * - ``infiniteCylindrical``
     - A Cylindrical UV mapping method that treats the cylinder as having
       infinite height.
   * - ``infiniteCylindricalNormalized``
     - A combination of the Cylindrical Normalized and Infinite Cylindrical
       projections.
   * - ``planar``
     - Projects UVs onto the primitive from a single plane.
   * - ``spherical``
     - Projects UVs as if the primitive were wrapped by a sphere.
   * - ``sphericalNormalized``
     - A variant of the Spherical projection where the calculated UV
       coordinates are always normalized to the [0,1] × [0,1] range,
       regardless of the object's size.
   * - ``triPlanar``
     - A UV mapping technique that blends UVs projected from three orthogonal
       planes (XY, XZ, YZ), minimizing visible seams and distortion.

UV projectors let you quickly add or override texture coordinates without modifying your source geometry. For information about applying materials to textured geometry, refer to :doc:`material_binding`.
