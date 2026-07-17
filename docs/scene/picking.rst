.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Picking and Selection
=====================

ovrtx can perform viewport picking against a RenderProduct and can draw
selection outlines for prims that the application marks as selected. Picking
answers the question "which prims are under this normalized RenderProduct region?"
Selection drawing answers a separate question: "which prims should the renderer
outline in future frames?"

The two features are designed to be composed by the application. A viewport UI
usually turns a click or drag rectangle into an NDC pick query, resolves the picked
path ids into prim paths, prints or stores those names, and then writes selection
outline group ids for the next rendered frame.

Concepts
--------

Picking is a one-step query. Queue the query before :c:func:`ovrtx_step()`;
the next step consumes it and returns a synthetic render var named
``OVRTX_RENDER_VAR_PICK_HIT``. The pick result is not a USD-authored RenderVar.
It appears only for a step that consumed a pick query.

Pick rectangles are always in normalized RenderProduct coordinates, not window
coordinates. Values use [0, 1] top-left-origin NDC: x increases left-to-right
and y increases top-to-bottom. Interactive applications that render into a
window, swapchain, or scaled framebuffer must convert the UI coordinates to
RenderProduct NDC before enqueueing the query.

In the current version, picking only works for RenderProducts running on
CUDA-visible GPU 0. On multi-GPU systems, author
``uint[] deviceIds = [0]`` on RenderProducts used for picking. ``deviceIds`` is
an allow-list of indices into ``CUDA_VISIBLE_DEVICES``; ovrtx can choose any
CUDA-visible GPU from the list, so ``[0]`` is required when picking must run on
CUDA-visible GPU 0.

Pick hit records contain ``ovx_primpath_t`` handles, not strings. Resolve those
handles through the renderer path dictionary before printing names, updating UI
selection state, or setting selection outline groups.

Selection outlines are persistent renderer state. Enable the outline pass when
creating the renderer, set a non-zero group id on the prims that should be
outlined, and set group ``0`` to clear the outline for a prim. Different
non-zero group ids are distinct outline groups. Global renderer-creation
settings control outline width and fill mode; runtime per-group settings control
outline and fill colors. Prims opt into a style by passing that group's id to
:py:meth:`~ovrtx.Renderer.set_selection_outline_group()` /
:c:func:`ovrtx_set_selection_outline_group()`.

Interactive Viewport Workflow
-----------------------------

For click selection, use the NDC rectangle that encloses the clicked RenderProduct
pixel. For marquee selection, convert the drag start and end points into
normalized RenderProduct coordinates, clamp to [0, 1], and use the normalized
rectangle as the query bounds.

After fetching the pick-hit output, validate the schema params before reading
the named tensors. Resolve ``primPath`` ids when printing or storing prim names.
If the viewport should also show selection outlines, clear the previous selection
by setting group ``0`` on its prims, then set group ``1`` or another non-zero
group on the new selection. Duplicate prim paths are allowed when setting
selection outline groups; the last occurrence wins.

The picking workflow is:

1. Queue an NDC pick rectangle with :c:func:`ovrtx_enqueue_pick_query()` before the next :c:func:`ovrtx_step()`.
2. Fetch the step results and find the synthetic render var named ``OVRTX_RENDER_VAR_PICK_HIT``.
3. Map that render var on the CPU with :c:func:`ovrtx_map_render_var_output()`.
4. Validate the ``magic`` and ``version`` params, read ``hitCount``, then consume the named tensors such as ``primPath`` and ``worldPositionM``.
5. Resolve each ``primPath`` value through the renderer path dictionary from :c:func:`ovrtx_get_path_dictionary()`.
6. Optionally set selection outline groups with :c:func:`ovrtx_set_selection_outline_group()` so selected prims are outlined in future rendered frames.

Pick Rectangles
---------------

Describe a pick region with :c:type:`ovrtx_pick_query_desc_t`.

The rectangle is expressed in normalized RenderProduct coordinates with
top-left-origin NDC semantics. It uses the same rectangle convention as the old
pixel API: ``right_ndc`` and ``bottom_ndc`` mark the edge just past the last
included pixel. For example, the old one-pixel rectangle ``[50, 50, 51, 51]`` on
a 100 x 100 RenderProduct becomes ``[0.50, 0.50, 0.51, 0.51]``. The full
RenderProduct is ``[0, 0, 1, 1]``.

Callers should clamp UI drag endpoints to [0, 1] before enqueueing a query. The
API rejects out-of-bounds rectangles, but old pixel-space values that already
fall inside [0, 1] are valid NDC and can be ambiguous during migration. Boundary values can be clamped to the valid range to account for
floating-point roundoff.

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_picking_selection.py
         :language: python
         :start-after: # [snippet:doc-enqueue-pick-query-python]
         :end-before: # [/snippet:doc-enqueue-pick-query-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_picking_selection.cpp
         :language: cpp
         :start-after: // [snippet:doc-enqueue-pick-query-c]
         :end-before: // [/snippet:doc-enqueue-pick-query-c]
         :dedent:

Use a one-pixel-equivalent NDC rectangle for click picking. For a RenderProduct
of size ``width`` by ``height``, the old pixel rectangle
``[px, py, px + 1, py + 1]`` is represented by
``left_ndc = px / width``, ``top_ndc = py / height``,
``right_ndc = (px + 1) / width``, and ``bottom_ndc = (py + 1) / height``. If
multiple pick queries are queued for the same RenderProduct before one
:c:func:`ovrtx_step()`, the last query wins.

Pick query flags:

* ``OVRTX_PICK_FLAG_GIZMO`` also requests gizmo picking.
* ``OVRTX_PICK_FLAG_INCLUDE_TRACKED_INFO`` requests tracked hit metadata such as
  object type, geometry instance id, world position, and world normal when
  available.

Pick Results
------------

Pick results are returned by the next step as the synthetic render var ``OVRTX_RENDER_VAR_PICK_HIT``. It is not authored in the USD RenderProduct; it appears only when a pick query is queued.

Map the output on the CPU and always validate the schema params before reading tensors:

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_picking_selection.py
         :language: python
         :start-after: # [snippet:doc-read-pick-hit-buffer-python]
         :end-before: # [/snippet:doc-read-pick-hit-buffer-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_picking_selection.cpp
         :language: cpp
         :start-after: // [snippet:doc-read-pick-hit-buffer-c]
         :end-before: // [/snippet:doc-read-pick-hit-buffer-c]
         :dedent:

The mapped render var exposes ``uint32`` params named ``magic``, ``version``, and ``hitCount`` plus named tensors such as ``primPath``, ``objectType``, ``geometryInstanceId``, ``worldPositionM``, and ``worldNormal``.

Resolving Picked Prim Names
---------------------------

Pick hit records store ``ovx_primpath_t`` handles, not strings. Python exposes
:py:meth:`~ovrtx.Renderer.resolve_prim_path_id()` for these ids. In C, get the
renderer path dictionary once and resolve path ids with
``path_dictionary_get_tokens_from_paths()`` and
``path_dictionary_get_strings_from_tokens()``:

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_picking_selection.py
         :language: python
         :start-after: # [snippet:doc-resolve-picked-prim-paths-python]
         :end-before: # [/snippet:doc-resolve-picked-prim-paths-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_picking_selection.cpp
         :language: cpp
         :start-after: // [snippet:doc-resolve-picked-prim-paths-c]
         :end-before: // [/snippet:doc-resolve-picked-prim-paths-c]
         :dedent:

The C helper used above expands each path id into tokens, then expands each
token into the path components:

.. literalinclude:: ../../tests/docs/c/helpers.h
   :language: cpp
   :start-after: // [snippet:doc-resolve-primpath-helper-c]
   :end-before: // [/snippet:doc-resolve-primpath-helper-c]
   :dedent:

Selection Outlines
------------------

Selection outlines are disabled by default. Enable them when creating the renderer:

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_picking_selection.py
         :language: python
         :start-after: # [snippet:doc-create-selection-outline-renderer-python]
         :end-before: # [/snippet:doc-create-selection-outline-renderer-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_picking_selection.cpp
         :language: cpp
         :start-after: // [snippet:doc-create-selection-outline-renderer-c]
         :end-before: // [/snippet:doc-create-selection-outline-renderer-c]
         :dedent:

Then mark selected prims with non-zero group ids:

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_picking_selection.py
         :language: python
         :start-after: # [snippet:doc-set-selection-outline-group-python]
         :end-before: # [/snippet:doc-set-selection-outline-group-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_picking_selection.cpp
         :language: cpp
         :start-after: // [snippet:doc-set-selection-outline-group-c]
         :end-before: // [/snippet:doc-set-selection-outline-group-c]
         :dedent:

Group ``0`` clears the outline for a prim. Different non-zero group ids map to distinct outline groups.

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_picking_selection.py
         :language: python
         :start-after: # [snippet:doc-clear-selection-outline-group-python]
         :end-before: # [/snippet:doc-clear-selection-outline-group-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_picking_selection.cpp
         :language: cpp
         :start-after: // [snippet:doc-clear-selection-outline-group-c]
         :end-before: // [/snippet:doc-clear-selection-outline-group-c]
         :dedent:

Selection Styling
-----------------

Selection style has a global part and a per-group part. Configure global outline
width and fill mode when creating the renderer:

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_picking_selection.py
         :language: python
         :start-after: # [snippet:doc-create-styled-selection-renderer-python]
         :end-before: # [/snippet:doc-create-styled-selection-renderer-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_picking_selection.cpp
         :language: cpp
         :start-after: // [snippet:doc-create-styled-selection-renderer-c]
         :end-before: // [/snippet:doc-create-styled-selection-renderer-c]
         :dedent:

Then set runtime colors for the selection groups your application uses:

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_picking_selection.py
         :language: python
         :start-after: # [snippet:doc-set-selection-group-styles-python]
         :end-before: # [/snippet:doc-set-selection-group-styles-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_picking_selection.cpp
         :language: cpp
         :start-after: // [snippet:doc-set-selection-group-styles-c]
         :end-before: // [/snippet:doc-set-selection-group-styles-c]
         :dedent:

Finally, assign those group ids to selected prims. This per-prim group value is
what connects a prim to its style:

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_picking_selection.py
         :language: python
         :start-after: # [snippet:doc-assign-selection-style-groups-python]
         :end-before: # [/snippet:doc-assign-selection-style-groups-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_picking_selection.cpp
         :language: cpp
         :start-after: // [snippet:doc-assign-selection-style-groups-c]
         :end-before: // [/snippet:doc-assign-selection-style-groups-c]
         :dedent:

Fill colors are visible only when the renderer's fill mode uses per-group fill
color, such as ``GROUP_FILL_COLOR`` /
``OVRTX_SELECTION_FILL_MODE_GROUP_FILL_COLOR``. Outline dashing and stippling
are not supported by the underlying outline pass.

Pickable Prims
--------------

Use :py:meth:`~ovrtx.Renderer.set_pickable()` / :c:func:`ovrtx_set_pickable()` to opt prims out of viewport picking where supported:

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_picking_selection.py
         :language: python
         :start-after: # [snippet:doc-set-pickable-python]
         :end-before: # [/snippet:doc-set-pickable-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_picking_selection.cpp
         :language: cpp
         :start-after: // [snippet:doc-set-pickable-c]
         :end-before: // [/snippet:doc-set-pickable-c]
         :dedent:

Reference
---------

Primary functions:

* :py:meth:`~ovrtx.Renderer.enqueue_pick_query()`
* :py:meth:`~ovrtx.Renderer.resolve_prim_path_id()`
* :py:meth:`~ovrtx.Renderer.set_selection_group_styles()`
* :py:meth:`~ovrtx.Renderer.set_selection_outline_group()`
* :py:meth:`~ovrtx.Renderer.set_pickable()`
* :py:class:`~ovrtx.RendererConfig`
* :c:func:`ovrtx_enqueue_pick_query()`
* :c:func:`ovrtx_map_render_var_output()`
* :c:func:`ovrtx_unmap_render_var_output()`
* :c:func:`ovrtx_get_path_dictionary()`
* :c:func:`ovrtx_config_entry_selection_outline_enabled()`
* :c:func:`ovrtx_config_entry_selection_outline_width()`
* :c:func:`ovrtx_config_entry_selection_fill_mode()`
* :c:func:`ovrtx_set_selection_group_styles()`
* :c:func:`ovrtx_set_selection_outline_group()`
* :c:func:`ovrtx_set_pickable()`

Primary types and constants:

* :c:type:`ovrtx_pick_query_desc_t`
* :c:type:`ovrtx_render_var_output_t`
* :c:type:`ovrtx_selection_group_style_t`
* ``OVRTX_RENDER_VAR_PICK_HIT``
* ``OVRTX_PICK_HIT_MAGIC``
* ``OVRTX_PICK_HIT_VERSION``
* ``OVRTX_PICK_FLAG_GIZMO``
* ``OVRTX_PICK_FLAG_INCLUDE_TRACKED_INFO``
