.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _ovstage-integration:

ovstage Integration
===================

Starting with ovrtx 0.4, the renderer can attach to an externally owned
**ovstage** instance and render the scene that ovstage holds. This page explains
what ovstage is, how the two libraries divide responsibilities, and how the
attach and pull mechanics work.

What Is ovstage?
----------------

ovstage is a separate NVIDIA library that manages post-composition scene data:
the runtime stage, prim hierarchy, attribute storage, and the ordinal-keyed
change model that records which writes happened at which simulation step. It is
the authoritative owner of scene state when both libraries are used together.

ovrtx was originally self-contained, managing its own internal USD stage and
Fabric. With the optional ovstage integration (0.4+), ovrtx can operate in two
modes:

- **Standalone** — ovrtx owns its own runtime stage, loaded through
  ``open_usd`` / :c:func:`ovrtx_open_usd_from_file`. This compatibility mode is
  still available, but its scene population, query, and attribute APIs are
  deprecated in 0.4 as scene ownership transitions entirely to ovstage in a
  future release.
- **Attached** — ovrtx renders scene state from an external ovstage instance.
  The application creates and drives the ovstage instance; ovrtx reads from
  it.

Responsibility Split
--------------------

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - ovstage owns
     - ovrtx owns
   * - Post-composition scene data
     - Rendering and sensor simulation
   * - Path dictionary and interning
     - Consuming attached ovstage data
   * - Prim attributes, cloning, queries
     - Render products and outputs
   * - Ordinal-keyed writes and change detection
     - Camera, lidar, radar, acoustic sensors
   * - Ordinal write-floor gates
     - Pulling state through ``update_from_stage`` / :c:func:`ovrtx_update_from_stage`

The Attached Update Loop
------------------------

After mutating ovstage, advance its write floor and wait for that publication
to complete. The write-floor operation is ordered after the mutations it
publishes. The ordinal passed to ovrtx is a committed-publication gate:
rendering may observe that publication or a later one.

In C, enqueue :c:func:`ovrtx_update_from_stage` followed by
:c:func:`ovrtx_step_with_stage`. The two operations are stream-ordered, so no
wait is needed between them. The high-level Python
:meth:`ovrtx.Renderer.step` method performs the update, waits for the step, and
fetches its results:

.. tab-set::

   .. tab-item:: C

      .. filtered-literalinclude:: ../../tests/docs/c/test_stage_mutation.cpp
         :language: cpp
         :start-after: // [snippet:doc-attached-update-loop-c]
         :end-before: // [/snippet:doc-attached-update-loop-c]
         :exclude-pattern: ^\s*ASSERT_
         :dedent:

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_stage_mutation.py
         :language: python
         :start-after: # [snippet:doc-attached-update-loop-python]
         :end-before: # [/snippet:doc-attached-update-loop-python]
         :dedent:

A per-attribute write-floor gate in ovstage makes repeated calls to
:c:func:`ovrtx_update_from_stage` at the same ordinal a fast no-op: if no
attribute has a new write at or after the current floor, the update returns
immediately without touching Fabric.

Ordinals and Write-Floor Gates
-------------------------------

ovstage uses **ordinals** (monotonically increasing ``uint64_t`` values) to
version writes. Every ``write_attribute``, ``clone``, and related mutation
carries an ordinal. ovstage 0.1 retains the latest committed snapshot only; an
ordinal passed to rendering is a publication gate, not a historical snapshot
selector.

A **write-floor gate** is a per-attribute lower bound that rejects writes at or
below the floor with ``OVSTAGE_ERROR_WRITE_FLOOR_VIOLATION``
(returned through ``wait_op``). Key properties:

- Admission is per-attribute, not a global watermark. A clone is blocked only
  by a floor on an attribute it would touch, not by unrelated seals.
- :c:func:`ovrtx_update_from_stage` uses the per-attribute write floor to skip
  attributes that have not changed since the last pull at the same ordinal,
  making incremental updates cheap.
- ovrtx does not set write floors; they are managed by ovstage. Scene writes
  should go through ovstage. The renderer attribute-write entry points remain
  available for compatibility but are deprecated in 0.4.

The ordinal model and write-floor API are owned by ovstage. Consult the ovstage
documentation for the full API reference.

Path Dictionary Notes
---------------------

Both libraries expose a ``path_dictionary_instance_t`` for converting between
prim-path strings and compact ``ovx_primpath_t`` tokens. Obtain the dictionary
through the public accessor supplied by its owner:

- **ovrtx:** ``ovrtx_get_path_dictionary(renderer, &dict)`` — flat utility
  symbol; dictionary lifetime is tied to the renderer.
- **ovstage:** ``ovstage_get_path_dictionary(instance)`` — owner-provided
  dictionary; do not free it or assume dictionaries are shared across
  instances.

Path-list handles returned by ovstage result structs are **borrows** valid only
for the lifetime of the producing operation. Call
``path_dictionary_add_path_list_reference`` before releasing the producer when
the list must remain usable, then pair it with
``path_dictionary_release_path_list_reference``.

Detaching From ovstage
-----------------------

Call :c:func:`ovrtx_detach_ovstage` to return the renderer to standalone mode.
Detach resets the renderer's stage, dropping all prims and attributes sourced
from the attached ovstage. After detach, the
renderer can use the deprecated standalone scene APIs for compatibility.

Related Docs
------------

- :doc:`renderer_configuration` — Renderer creation and configuration.
- :doc:`application_flow` — Minimal lifecycle and step loop.
- :doc:`../scene/cloning` — Clone semantics differences between ovrtx and
  ovstage (``_usd`` suffix, ordinals, error handling).
- :doc:`../scene/attributes` — Reading and writing attributes in standalone and
  attached mode.
