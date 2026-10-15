.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-ref-rtx:

The ``rtx`` Lua Table
=====================

What a launch script can read about the frame it runs in and the scene it runs over. The same
in either language. For how a launch script is found and when it runs, refer to
:doc:`lua_contract`; for the task-by-task guide, refer to :doc:`../do/scene_queries`.

Throughout this page, *on the stage* means published for the renderer at the time the script
runs. Refer to :ref:`spg-rtx-availability`.

The Frame
---------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Description
   * - ``rtx.frameId``
     - The current rendered frame, counted by the renderer.

.. _spg-rtx-product:

The Product
-----------

``rtx.product`` is the RenderProduct the node's prim sits under, or ``nil`` when the prim is not
under a product being rendered. It is a :ref:`prim table <spg-rtx-prim-tables>` of the product
prim, so its attributes read by name: ``rtx.product.resolution`` is the authored resolution,
width first. A prim table of a RenderProduct being rendered, however it was obtained, also
answers these fields:

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Field
     - Contents
   * - ``tiling.count_x``, ``tiling.count_y``
     - How many tiles the image is divided into, across and down. A product bound to several
       cameras renders one camera per tile; an untiled product reports one tile each way.
   * - ``tiling.count``
     - How many tiles hold an image.
   * - ``tiling.width``, ``tiling.height``
     - The size of one tile, in pixels; for an untiled product, the size of the image.
   * - ``cameras``
     - The cameras the product is bound to, as prim tables, in the order of its ``camera``
       relationship. Empty when the relationship is unset.
   * - ``render_vars``
     - The RenderVars the product publishes, as prim tables, in the order of its ``orderedVars``
       relationship. Empty when the relationship is unset.

**A node outside its product.** A node runs wherever its Shader prim is authored, as long as a
RenderVar of a product being rendered connects to it. A node authored outside the product reads
``nil`` for ``rtx.product``. It reaches the product by path: ``rtx.stage.prim("/Render/Product")``
gives the same table.

.. _spg-rtx-prim-tables:

Prim Tables
-----------

A prim table is how a launch script holds a prim. It carries the prim's path and reads the scene
each time it is asked for a value. ``rtx.product``, the entries of its ``cameras`` and
``render_vars``, and ``rtx.stage.prim`` all give this kind of table.

- **Current.** A table kept from an earlier frame reads the current frame. A value read from it
  does not change, so keep the table, not the values.
- **Read-only.** Assigning to it fails the node; keep a computed value in a local variable.
- **Identified by its path.** Two tables of the same prim compare equal with ``==``.

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Access
     - Result
   * - ``prim.path``
     - The prim's path, as a string.
   * - ``prim.local_matrix``, ``prim.world_matrix``
     - The prim's local and world transform, or ``nil`` when the prim has none. Refer to
       :ref:`spg-rtx-transforms`.
   * - ``prim.name``, ``prim["name"]``
     - The attribute of that USD name, as listed in :ref:`spg-rtx-values`, or ``nil`` when the
       prim does not carry it.
   * - ``tostring(prim)``
     - The prim's path and the names of its attributes. The log shortens long messages, so for a
       large prim only the first names show.

A table of a prim that is not on the stage reads ``nil`` for everything but ``path``.

``rtx.stage.prim``
------------------

.. code-block:: lua

    local prim = rtx.stage.prim(path)
    local prim = rtx.stage.prim(base, relative)

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Argument
     - Meaning
   * - ``path``
     - An absolute prim path, a string starting with ``/``.
   * - ``base``
     - The prim the relative path starts from: an absolute prim path, or anything with a
       ``path`` field, such as a prim table or ``rtx.product``.
   * - ``relative``
     - A path relative to ``base``, resolved as in USD: ``.`` is ``base`` itself, ``..`` its
       parent, and any other component a child. ``rtx.stage.prim(camera, "../Target")`` is a
       sibling of ``camera``.

Returns the prim as a :ref:`prim table <spg-rtx-prim-tables>`. When no prim is found it returns
``nil`` and logs why, once per node and problem. The node keeps running, so check the result for
``nil``.

``rtx.stage.query_attributes``
------------------------------

.. code-block:: lua

    local result = rtx.stage.query_attributes(paths, names)

Reads the named attributes of many prims in one call. ``paths`` is one absolute prim path or a
list of them; ``names`` is one attribute name or a list. Leaving ``names`` out reads every
attribute, large arrays included, so name the ones you need.

Returns a table keyed by prim path, with one entry per prim on the stage; a prim that is not on
the stage is left out. Each entry holds the named attributes, as listed in :ref:`spg-rtx-values`.
Reading a name the query did not ask for, or one the prim does not carry, fails the node with a
message naming it.

``LOCAL_MATRIX`` and ``WORLD_MATRIX`` name the two transforms:

.. code-block:: lua

    local camera = rtx.stage.query_attributes(path, { WORLD_MATRIX, "focalLength" })[path]
    local matrix = camera[WORLD_MATRIX]

.. _spg-rtx-values:

Values
------

Every read, through a prim table or ``query_attributes``, gives the same value for an attribute.

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Authored as
     - Reads as
   * - ``bool``
     - A boolean.
   * - ``int``, ``uint``, ``int64``, ``uint64``, ``uchar``
     - A Lua integer.
   * - ``half``, ``float``, ``double``, ``timecode``
     - A Lua float.
   * - A vector: ``float3``, ``double3``, ``int2``, ``point3f``, ``color3f`` and the like
     - A table of numbers in component order, starting at 1.
   * - ``matrix2d``, ``matrix3d``, ``matrix4d``
     - A table of 4, 9 or 16 numbers, row by row.
   * - ``quatf``, ``quatd``, ``quath``
     - A table of four numbers, the imaginary part first: (x, y, z, w). USDA writes a quaternion
       (w, x, y, z), so the authored ``(1, 2, 3, 4)`` reads as ``{2, 3, 4, 1}``.
   * - A numeric array such as ``float[]`` or ``float3[]``
     - A table of numbers, one per element, with a vector's components in order. A ``bool[]``
       reads as 0 and 1.
   * - ``token``
     - A string.
   * - ``token[]``
     - A table of strings.
   * - ``string``
     - A string for an attribute the renderer uses, such as a RenderVar's ``sourceName``. A
       custom ``string`` reads as a number: author custom text as a ``token``.
   * - ``asset``, ``asset[]``
     - The path as a string, or a table of them: the resolved path, or the authored one when it
       carries a URI scheme or does not resolve. Never the file's content.
   * - A path, a path array, a relationship
     - The path as a string, or a table of them in authored order.
   * - A connected attribute
     - The value of the connection's source, as in USD. Connections are followed on SPG Shader
       prims; on other prims the attribute reads its own value.

Reading any other value fails the node with a message naming the prim and the attribute.

.. _spg-rtx-transforms:

Transforms
----------

A transform places a prim in the scene: the local transform relative to its parent, the world
transform in the world. Prims placed in the scene have both. RenderProducts and RenderVars are not
placed in the scene and read ``nil`` for both.

Each transform is a 4x4 matrix as 16 numbers, row by row, as USD stores it. The first three rows
are the prim's axes and the fourth row its position, so the translation is at 13, 14 and 15.

.. _spg-rtx-availability:

What Is on the Stage
--------------------

Loading a scene puts its prims on the stage with what the renderer needs of them. A prim of your
own, such as a ``Scope`` holding settings, is on the stage too, but its custom attributes are
not. They are published only when the load names the prim that carries it: in Python, a
description with a selector passed to ``ovstage.population.open_usd_with_desc``. Refer to
:doc:`../do/scene_queries` for the call.
