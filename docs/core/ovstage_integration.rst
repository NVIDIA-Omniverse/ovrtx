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

ovrtx was originally self-contained, managing its own internal runtime stage.
With the optional ovstage integration (0.4+), ovrtx can operate in two modes:

- **Standalone** — ovrtx owns its own runtime stage, loaded through
  ``open_usd`` / :c:func:`ovrtx_open_usd_from_file`. This compatibility mode is
  still available, but its scene population, query, and attribute APIs are
  deprecated in 0.4 as scene ownership transitions entirely to ovstage in a
  future release.
- **Attached** — ovrtx renders scene state from an external ovstage instance.
  The application creates and drives the ovstage instance; ovrtx reads from it.

Attachment Ownership
--------------------

An ovstage instance may be attached to only one ovrtx renderer at a time. A
second attachment fails immediately; Python raises ``RuntimeError`` and the C
API returns ``OVRTX_API_ERROR``. Detach the stage before attaching it to another
renderer.

This restriction prevents multiple renderers from concurrently consuming stage
and history state that the current integration expects to have a single owner.

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
immediately without applying scene-data changes.

The update applies committed population changes while retaining shared
attribute storage. Python performs this update automatically before stepping.

Two Clocks: USD Time and the Simulation Clock
---------------------------------------------

An attached application drives two independent clocks, and ovrtx infers neither
of them from the other:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Clock
     - Driven by
   * - **USD time**, the position on the stage's timeline
     - ``ovstage_population_apply_usd_time``, which resamples time-sampled
       attributes into the attached scene data
   * - **Simulation clock**, the accumulated sensor/simulation time
     - the ``delta_time`` argument of :c:func:`ovrtx_step_with_stage`;
       :c:func:`ovrtx_reset` sets it to the time it is given

Under ovrtx, **animation time is the simulation clock**. Everything that
animates from animation time -- MDL ``state::animation_time()``, video texture
frame selection, animated NuRec volumes and ParticleFields -- advances with the
``ovrtx_step`` delta, not with the applied USD time. Applying a USD time never
changes animation time.

An application that wants animation playback must therefore advance both clocks
together. Derive them from a single time source: pass the absolute time to
``ovstage_population_apply_usd_time`` and the delta since the previous frame to
:c:func:`ovrtx_step_with_stage`. Advancing one without the other desynchronizes
materials from geometry: time-sampled geometry would move while materials stay
still, or the reverse.

Because ovrtx never reads the timeline position back out of the attached scene
data, the renderer's own notion of USD time stays at zero while attached. That is
by design -- ``ovstage_population_apply_usd_time`` resamples time-sampled
attributes into the scene data, so the renderer consumes already-evaluated values
and has no reason to re-evaluate them at a timeline position. Three consequences:

* Time-sampled render settings must be reached through population. Values that
  would only resolve by sampling USD at the current timeline position are not
  evaluated.
* Timestamp fallbacks that substitute USD time when simulation time is
  unavailable (some sensor and camera-ISP paths) read zero. Pass a real
  ``delta_time`` so simulation time is authoritative.
* Animation time never follows the timeline, as described above.

.. _ovstage-ordinal-admission:

Ordinals and Write-Floor Gates
-------------------------------

ovstage uses **ordinals** (application-supplied ``int64_t`` values) to
version writes. Every ``write_attribute``, ``clone``, and related mutation
carries an ordinal. ovstage retains the latest committed snapshot only; an
ordinal passed to rendering is a publication gate, not a historical snapshot
selector.

A **write-floor gate** is a per-attribute lower bound that rejects writes at or
below the floor with ``OVSTAGE_ERROR_WRITE_FLOOR_VIOLATION``
(reported by enqueue or operation completion, depending on the operation).
Key properties:

- For data-plane writes, map commits, clones, and deletes, clearing the floor is
  necessary but does not guarantee admission. The
  ``STRICTLY_INCREASING`` policy also rejects ordinals older than or equal to
  retained committed changes on affected cells (prim path and canonical
  attribute) and prim lifecycle. Disjoint cells may share an ordinal.
- ``NONDECREASING`` permits equality with retained changes while rejecting older
  ordinals. Both history policies check applicable prim-lifecycle history and
  the ``usd-path`` lifecycle floor. ``FLOOR_ONLY`` skips retained-history
  admission and that additional lifecycle check. All policies still enforce
  the operation's write floors and preserve type and create-only checks.
- Cloning commits copied cells at the clone ordinal. Under the strict policy,
  a subsequent customization of a copied cell needs a newer ordinal, even before
  sealing. Reusing the same unsealed ordinal requires an admission policy that
  allows equality.
- :c:func:`ovrtx_update_from_stage` uses the per-attribute write floor to skip
  attributes that have not changed since the last pull at the same ordinal,
  making incremental updates cheap.
- ovrtx does not set write floors; they are managed by ovstage. Scene writes
  should go through ovstage. The renderer attribute-write entry points remain
  available for compatibility but are deprecated in 0.4.

Enqueue success does not guarantee that a mutation will pass admission during
execution. Wait for successful mutation completion, then advance the write floor
and wait for that publication before updating or rendering through ovrtx.

Select the policy through ovstage's process configuration before creating
instances; it remains fixed until all initialization and instance references
have been released. With ``FLOOR_ONLY``, an older-ordinal mutation that executes
later can replace newer state. Ordinal ranges do not provide historical payload
snapshots. Consult the documentation shipped with the installed ovstage version
for its supported configuration settings.

The ordinal model, admission policy, and write-floor API are owned by ovstage.
See its `write contract
<https://github.com/NVIDIA-Omniverse/ovstage/blob/main/docs/scene/writing_attributes.rst>`_
and `asynchronous submit/observe model
<https://github.com/NVIDIA-Omniverse/ovstage/blob/main/docs/concepts/async_model.rst>`_
for the authoritative contracts.

For population update sequencing, see the `ovstage population documentation
<https://github.com/NVIDIA-Omniverse/ovstage/blob/main/docs/scene/population.rst>`_.

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

Both dictionaries construct absolute paths with
``path_dictionary_create_paths_from_tokens``. See the shared contract for
``path_dictionary_vtable_t::create_paths_from_tokens`` in
``<ovx/path_dictionary/path_dictionary_vtable.h>`` for component and root semantics.

``ovrtx_get_path_dictionary`` continues to return the renderer's own dictionary
when an OVStage instance is attached.

Path-list handles returned by ovstage result structs are **borrows** valid only
for the lifetime of the producing operation. Call
``path_dictionary_add_path_list_reference`` before releasing the producer when
the list must remain usable, then pair it with
``path_dictionary_release_path_list_reference``.

Detaching From ovstage
-----------------------

After a successful attach, ovrtx retains its own ovstage handle. The application
may destroy the handle it passed to :c:func:`ovrtx_attach_ovstage`; this
invalidates the application's handle but leaves the attached renderer and shared
stage state alive.

Call :c:func:`ovrtx_detach_ovstage` to return the renderer to standalone mode.
Detach resets the renderer's stage, dropping all prims and attributes sourced
from the attached ovstage, then releases ovrtx's retained handle. Destroying the
renderer performs the same attached-stage cleanup. After detach, the renderer
can attach the same or a different ovstage, or use the deprecated standalone
scene APIs for compatibility.

Attaching and Detaching Around In-Flight Operations
---------------------------------------------------

Both :c:func:`ovrtx_attach_ovstage` and :c:func:`ovrtx_detach_ovstage` rebuild
the renderer's internal state on the calling thread, so wait for previously
enqueued operations with :c:func:`ovrtx_wait_op` before calling either one. A
step whose result :c:func:`ovrtx_fetch_results` has returned has completed,
together with the operations enqueued before it, so no separate wait is needed
for them.
Neither call waits on your behalf, and rebuilding that state underneath a
running operation can crash or hang the renderer. Note that an
:c:func:`ovrtx_wait_op` timeout does not cancel the operation it was waiting
on: the operation keeps running, so a timed-out wait does not make it safe to
attach or detach.

When detach fails, teardown may be partial. Do not use the renderer again except
to destroy it. The application may release its own ovstage handle before or
after destroying the renderer because ovrtx retains any shared stage state still
needed for safe renderer destruction.

Related Docs
------------

- :doc:`renderer_configuration` — Renderer creation and configuration.
- :doc:`application_flow` — Minimal lifecycle and step loop.
- :doc:`../scene/cloning` — Clone semantics differences between ovrtx and
  ovstage (``_usd`` suffix, ordinals, error handling).
- :doc:`../scene/attributes` — Reading and writing attributes in standalone and
  attached mode.
