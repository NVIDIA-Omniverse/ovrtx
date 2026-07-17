.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Loading USD
===========

.. note::

   Python examples populate an attached ovstage. The ``Renderer.open_usd*``,
   reference, remove, reset, and USD-time wrappers are deprecated compatibility
   APIs. Refer to ``skills/update-0_3-0_4-python/SKILL.md``. The C tabs retain the
   corresponding standalone APIs.

Before rendering, load USD content into the application-owned ovstage. The
population layer supports three composition patterns:

- Open a file path, URL, or inline USDA string as the root layer.
- Compose a new inline root layer that sublayers an existing scene and authors
  additional prims such as cameras, RenderProducts, RenderVars, or labels.
- Add removable referenced content under a path prefix after a root stage is
  already open.

Opening a Root Layer
--------------------

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../examples/python/minimal/main.py
         :language: python
         :start-after: # [snippet:add-usd]
         :end-before: # [/snippet:add-usd]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../examples/c/minimal/main.cpp
         :language: cpp
         :start-after: // [snippet:load-usd-and-wait]
         :end-before: // [/snippet:load-usd-and-wait]
         :dedent:

Python population assigns an ordinal; advance the ovstage write floor before
rendering that ordinal. C compatibility open calls are asynchronous and must be
waited before using the loaded stage.

Inline Composition
------------------

Use an inline root layer when an existing scene does not contain the render
configuration, sensors, or semantic metadata the application needs. The inline
root can sublayer the original scene and author additional prims without
modifying the source asset.

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/usd/data/inline_sublayers_camera_renderproduct.usda
         :language: usda
         :start-after: # [snippet:doc-usda-inline-sublayers-camera-renderproduct]
         :end-before: # [/snippet:doc-usda-inline-sublayers-camera-renderproduct]

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_sensor_configuration.py
         :language: python
         :start-after: # [snippet:doc-add-render-config-layer]
         :end-before: # [/snippet:doc-add-render-config-layer]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_sensor_configuration.cpp
         :language: cpp
         :start-after: // [snippet:doc-add-render-config-layer-c]
         :end-before: // [/snippet:doc-add-render-config-layer-c]
         :dedent:

References
----------

Use reference APIs when a root stage is already open and you want to add content
under a new path prefix, then later remove it by handle.

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_stage_mutation.py
         :language: python
         :start-after: # [snippet:doc-add-remove-usd-reference]
         :end-before: # [/snippet:doc-add-remove-usd-reference]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_stage_mutation.cpp
         :language: cpp
         :start-after: // [snippet:doc-add-remove-usd-reference-c]
         :end-before: // [/snippet:doc-add-remove-usd-reference-c]
         :dedent:

Inline referenced content must have a ``defaultPrim`` because the reference is
composed below the requested path prefix.

Time-Sampled USD
----------------

For animated USD scenes, re-evaluate time-sampled attributes through
``ovstage.population.update_from_usd_time`` (Python) or
``ovstage_population_apply_usd_time`` (attached-mode C) and publish the
changes at a new ordinal.

USD authors time samples in **timecodes** (frame-like units), but the runtime time APIs take
**seconds**. Convert using the stage's ``timeCodesPerSecond`` metadata:
``seconds = timecode / timeCodesPerSecond``. For example, with ``timeCodesPerSecond = 24``,
a sample at timecode ``48`` is at ``2.0`` seconds. Despite its name, the ``usd_time``
parameter is in seconds, not timecodes.

This is distinct from the *simulation time* advanced by ``step(delta_time)`` — the two
clocks are independent (refer to the stepping-and-rendering skill). ``step()`` does not move USD
animation; ``update_from_usd_time()`` does not advance the simulation/sensor clock.

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_base.py
         :language: python
         :start-after: # [snippet:doc-update-from-usd-time-async]
         :end-before: # [/snippet:doc-update-from-usd-time-async]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_base.cpp
         :language: cpp
         :start-after: // [snippet:doc-update-from-usd-time-async-c]
         :end-before: // [/snippet:doc-update-from-usd-time-async-c]
         :dedent:

Resetting the Stage
-------------------

``reset_stage`` clears all USD content from the runtime stage. Python exposes
``reset_stage`` and ``reset_stage_async``; C uses :c:func:`ovrtx_reset_stage`.
Opening a new root layer replaces the previous root.

Authored Attribute Population
-----------------------------

By default, the runtime populates supported schema attributes. To read or write
generic custom authored attributes, an inline root layer can set
``customLayerData.populateAllAuthoredAttributes = true``. Use this only when
needed: large assets can contain many authored properties that the application
will never use.
