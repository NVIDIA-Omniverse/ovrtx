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
outline in future frames?" For custom drawing, the ``SelectionState`` AOV exposes
selection groups and visibility for an application or SPG shader to style.

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
settings control the default outline width and fill mode; runtime per-group
settings control outline color, fill color, and outline width. Prims opt into a
style by passing that group's id to
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

1. Queue an NDC pick rectangle with :c:func:`ovrtx_enqueue_pick_query()` before
   the next :c:func:`ovrtx_step()`. Include
   ``OVRTX_PICK_FLAG_INCLUDE_TRACKED_INFO`` when a click query needs surface
   position, surface normal, object type, or geometry instance id.
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

Use ``OVRTX_PICK_FLAG_INCLUDE_TRACKED_INFO`` when a one-pixel-equivalent click
needs tracked metadata. The flag requests object type, geometry instance id,
world position in metres, and world normal for the first hit. Without the flag,
those tensors are still present but contain zeros. Multi-pixel picks do not
provide tracked metadata and leave those tensors zero-filled even when the flag
is set.

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

The mapped render var exposes ``uint32`` params named ``magic``, ``version``, and
``hitCount`` plus the following named tensors:

.. list-table:: Pick-hit tensors
   :header-rows: 1

   * - Tensor
     - Population
   * - ``primPath``
     - One renderer path-dictionary id per hit. This tensor is populated
       independently of the query flags.
   * - ``objectType``
     - Tracked object type for the first hit of a one-pixel-equivalent pick when
       ``OVRTX_PICK_FLAG_INCLUDE_TRACKED_INFO`` is set; zero otherwise.
   * - ``geometryInstanceId``
     - Opaque geometry instance id for that tracked hit; zero otherwise.
   * - ``worldPositionM``
     - Tracked world-space position in metres for that hit; ``(0, 0, 0)``
       otherwise. A populated hit can legitimately be at the world origin.
   * - ``worldNormal``
     - Tracked world-space normal for that hit; ``(0, 0, 0)`` otherwise.

.. warning::

   The tracked tensors are always present. Their presence does not mean that
   tracked information was requested or populated. Pass
   ``OVRTX_PICK_FLAG_INCLUDE_TRACKED_INFO`` for a one-pixel-equivalent click
   before consuming these values.

Resolving Picked Prim Names
---------------------------

The ``primPath`` tensor stores raw uint64 path IDs. In Python, wrap each value
in ``ovrtx.PrimPath(raw_id)`` before passing it to
:py:meth:`~ovrtx.Renderer.resolve_prim_path_id()`. In C or C++, construct an
``ovx_primpath_t`` from each numeric ID. Get the renderer path dictionary once
and resolve those handles with
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

Selection outlines are enabled by default. Set ``selection_outline_enabled=False`` in Python or use
``ovrtx_config_entry_selection_outline_enabled(false)`` in C to disable the global pass. Create the renderer:

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

Selection style has a global part and a per-group part. Configure the default
outline width and fill mode when creating the renderer:

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

Then set runtime colors (and optionally outline width) for the selection groups
your application uses. Omitting ``outline_width`` leaves that group's width
unchanged, so it keeps the renderer-creation default:

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
are not supported by the built-in outline pass. Use the ``SelectionState`` AOV
and a custom shader for those effects.

SelectionState AOV
------------------

``SelectionState`` exposes selected-surface coverage and visibility for custom
outlines, fills, and hidden-surface patterns. It is available in Path Tracing
and Real-Time Path Tracing. See :doc:`../examples/c_selection_spg` for a runnable
C example that uses an SPG shader to composite these effects over ``LdrColor``.

Requesting the Output
~~~~~~~~~~~~~~~~~~~~~~~~

Add a RenderVar with ``sourceName = "SelectionState"`` to the RenderProduct's
``orderedVars`` relationship. Assign prims to groups 1–255 with
:py:meth:`~ovrtx.Renderer.set_selection_outline_group()` or
:c:func:`ovrtx_set_selection_outline_group()`; group ``0`` removes a prim from
the selection. The example shows the USD graph wiring and group assignment.
Picking is optional: applications can assign groups directly without a pick query.

Requesting ``SelectionState`` suppresses the built-in selection overlay for
that RenderProduct. The AOV is produced even when the renderer's
``selection_outline_enabled`` option is false. Built-in outline width, color,
and fill settings do not style this output; the consuming shader controls those
choices. With no selected prims, the renderer clears a valid output image to
zero and skips selection ray tracing. Selection updates still run when RTPT
reuses its beauty image in eco mode.

Sample Format
~~~~~~~~~~~~~

The output is an ``RGBA16_UINT`` image at the RenderProduct's final output
resolution: eight bytes per pixel, exposed as ``uint16`` with shape
``(H, W, 4)``. Its four channels hold coverage samples, not color components.
Each sample has the following layout:

.. list-table::
   :header-rows: 1
   :class: compact-table

   * - Bits
     - Meaning
   * - 0–7
     - Selection group, 1–255. Zero means no selected geometry.
   * - 8
     - Visibility: 1 for visible, 0 for occluded selected geometry.
   * - 9–15
     - Reserved; always zero.

A background sample is ``0x000``. Group 1 is ``0x001`` when hidden and
``0x101`` when visible. Decode each sample before combining coverage; averaging
packed integer values would mix group and visibility bits. The image contains
no depth, instance ids, outline colors, or fill colors. Objects in the same
group form one mask and cannot be distinguished by this output alone.

Visibility and Coverage
~~~~~~~~~~~~~~~~~~~~~~~

For each traced sample, the renderer finds the nearest selected surface through
unselected geometry, then compares its identity with the full-scene hit along
the same unjittered camera ray. Only that nearest selected surface is represented;
a selected object behind another selected object has no separate layer.

Visibility is binary surface visibility, not accumulated transmission through
translucent materials or volumes. The traces use selection's backface-culling
and positive-opacity policy and respect camera visibility and camera/section
clipping. They run at output resolution independently of the beauty G-buffer
and DLSS rendering resolution.

Coverage is adaptive. Uniform regions replicate the pixel-center result into
all four channels. Changes in selected-instance identity or visibility between
neighboring centers trigger four subpixel samples. Their offsets from the pixel
center, in channel order, are ``(-0.125, -0.375)``, ``(0.375, -0.125)``,
``(-0.375, 0.125)``, and ``(0.125, 0.375)``. Thin geometry or occluders missed
by the center sampling pattern can therefore be missed entirely.

When a shader expands this mask into an outline, visibility belongs to the
selected sample. The AOV has no depth with which to reclassify an expanded
stroke against geometry beneath it. The SPG example carries the source sample's
visibility into that stroke.

XR foveation unwarp is unsupported. When unwarp is authored, the renderer clears
``SelectionState`` and logs a warning while beauty rendering continues. Disable
unwarp to read the selection output in warped coordinates.

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
* ``OVRTX_PICK_FLAG_INCLUDE_TRACKED_INFO``
