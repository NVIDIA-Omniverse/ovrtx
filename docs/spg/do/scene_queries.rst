.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-do-scene-queries:

Read the Scene
==============

**Goal.** Read a camera's transform and lens values, the attributes of a prim of your own, or one
attribute across many prims, inside a launch script, and hand the result to the GPU code.

**Before you start.** A working node, from :doc:`../first_node`, and :doc:`values` for how a
number reaches the GPU.

The Shape
---------

A launch script reaches the scene through the ``rtx`` table. The product the node's prim sits
under is ``rtx.product``. A prim comes as a *prim table*: it holds the prim's path and reads the scene each
time you ask it for a value. Refer to :ref:`spg-rtx-prim-tables`.

.. code-block:: lua

    local camera = rtx.product.cameras[1]       -- the camera this product is bound to
    local world = camera.world_matrix           -- 16 numbers, row-major
    local focalLength = camera["focalLength"]   -- any attribute of the prim, by name

How It Works
------------

**Start from the product.** ``rtx.product`` is the RenderProduct the node's prim sits under. Its
``cameras`` and ``render_vars`` are lists of prim tables, in authored order, and its attributes
read by name, such as ``resolution``. It is ``nil`` when the node's prim is not under a product
being rendered. Refer to :ref:`spg-rtx-product`.

.. filtered-literalinclude:: ../../../examples/python/spg-scene-query/MarkerOverlayKernel.cu.lua
   :language: lua
   :start-after: -- [snippet:scene-query-camera]
   :end-before: -- [/snippet:scene-query-camera]
   :exclude-pattern: ^\s*--\s*\[/?snippet:
   :dedent:
   :caption: ``MarkerOverlayKernel.cu.lua``, from the runnable :doc:`scene query example <../../examples/python_spg_scene_query>`

**Read a prim through its table.** A prim table answers ``path``, its two transforms as
``local_matrix`` and ``world_matrix``, and any attribute by its USD name, ``prim.focalLength`` or
``prim["focalLength"]``. What it lacks reads ``nil``, so check before you index a result. What
each attribute type reads as is listed in :ref:`spg-rtx-values`.

**Reach any prim by path.** ``rtx.stage.prim(path)`` gives the same kind of table for any prim on
the stage, and ``rtx.stage.prim(base, relative)`` finds one relative to another, as in
``rtx.stage.prim(rtx.product, "Shader")``. When no prim is there it returns ``nil`` and logs why.
Here the path comes from a value-input, so the scene decides which prim the node reads:

.. filtered-literalinclude:: ../../../examples/python/spg-scene-query/MarkerOverlayKernel.cu.lua
   :language: lua
   :start-after: -- [snippet:scene-query-prim]
   :end-before: -- [/snippet:scene-query-prim]
   :exclude-pattern: ^\s*--\s*\[/?snippet:
   :dedent:
   :caption: ``MarkerOverlayKernel.cu.lua``, from the runnable :doc:`scene query example <../../examples/python_spg_scene_query>`

**Read many prims at once.** ``rtx.stage.query_attributes(paths, names)`` reads the named
attributes of every path in one call and returns a table keyed by path. ``LOCAL_MATRIX`` and
``WORLD_MATRIX`` name the two transforms. A prim that is not on the stage is left out of the
result, so a script can branch on it:

.. filtered-literalinclude:: ../../../examples/python/spg-scene-query/MarkerOverlayKernel.cu.lua
   :language: lua
   :start-after: -- [snippet:scene-query-batch]
   :end-before: -- [/snippet:scene-query-batch]
   :exclude-pattern: ^\s*--\s*\[/?snippet:
   :dedent:
   :caption: ``MarkerOverlayKernel.cu.lua``, from the runnable :doc:`scene query example <../../examples/python_spg_scene_query>`

**Publish the prims you read.** Loading a scene puts its prims on the stage, but the custom
attributes of a prim of your own, such as the settings prim here, arrive only when the load names
that prim. In Python the load takes a description with a selector:

.. literalinclude:: ../../../examples/python/spg-scene-query/main.py
   :language: python
   :start-after: # [snippet:scene-query-populate]
   :end-before: # [/snippet:scene-query-populate]
   :dedent:
   :caption: ``main.py``, from the runnable :doc:`scene query example <../../examples/python_spg_scene_query>`

Refer to :ref:`spg-rtx-availability`.

**Hand it to the GPU.** A matrix is sixteen numbers and a position list is three per prim, so
both go through ``array``, as any Lua table does; refer to :doc:`upload_data`. The kernel reads
the world matrix as USD stores it: the first three rows are the prim's axes in world space and
the fourth its position.

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      .. filtered-literalinclude:: ../../../examples/python/spg-scene-query/MarkerOverlayKernel.cu.lua
         :language: lua
         :start-after: -- [snippet:scene-query-launch]
         :end-before: -- [/snippet:scene-query-launch]
         :exclude-pattern: ^\s*--\s*\[/?snippet:
         :caption: ``MarkerOverlayKernel.cu.lua``, from the runnable :doc:`scene query example <../../examples/python_spg_scene_query>`

   .. tab-item:: Slang
      :sync: slang

      .. filtered-literalinclude:: ../../../examples/python/spg-scene-query/MarkerOverlayKernel.slang.lua
         :language: lua
         :start-after: -- [snippet:scene-query-slang-launch]
         :end-before: -- [/snippet:scene-query-slang-launch]
         :exclude-pattern: ^\s*--\s*\[/?snippet:
         :caption: ``MarkerOverlayKernel.slang.lua``, from the runnable :doc:`scene query example <../../examples/python_spg_scene_query>`

**Keep the table, not the values.** A prim table kept across frames reads the current frame, but a
value read from it keeps what it held when it was read. To follow a prim over frames, keep its
table in a script-level local and read the values each frame.

Verify It Worked
----------------

Change what the script reads, and the output must follow. In the :doc:`scene query example
<../../examples/python_spg_scene_query>`, moving the camera's rig or a marker moves the crosshair
drawn on that marker in ``_output/overlay.png``.

When It Goes Wrong
------------------

**The script stopped with** ``attempt to index a nil value``. A read came back ``nil``: the prim
path is wrong, or the attribute is misspelt or was not published. Compare one name with ``nil``
to tell which. For a custom attribute, check that the load named its prim.

``rtx.product`` **is** ``nil``. The node's Shader prim is authored outside the product. The node
still runs; reach the product by path with ``rtx.stage.prim``, or author the node under the
product.

**Text came back as a number.** The attribute is a ``string`` published through a selector.
Author it as a ``token``.

**A transform is** ``nil``. The prim is not placed in the scene, as RenderProducts and RenderVars
are not. Refer to :ref:`spg-rtx-transforms`.

**The node's graph stopped on an assignment.** Prim tables are read-only views of the scene. Keep
the value in a local variable instead.

**A lookup returned** ``nil``. The log says why: a wrong argument, a relative path that cannot be
resolved, or no prim at that path.

Refer to :ref:`Nothing Appears <spg-symptom-nothing>` for the general checks.

Related
-------

:doc:`../ref/lua_rtx`, :doc:`values`, :doc:`upload_data`, :doc:`products`
