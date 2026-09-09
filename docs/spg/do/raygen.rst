.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-do-raygen:

Trace the Scene
===============

*Slang only.*

**Goal.** Have a node render the scene itself rather than transform an AOV.

**Before you start.** A Slang node that runs, and :doc:`values`.

A ray-generation node **traces the scene itself**, so its output is an image it rendered rather
than one it read and transformed.

It is a Slang node in every other respect: the same three files, the same launch script
contract, the same binders.

The Shape
---------

The entry point is marked ``[shader("raygeneration")]``, and the launch script returns one of two
calls in place of ``slang.dispatch``. Either way the ray grid is the output's shape, one
invocation per output element, so there is no ``numthreads``.

Which of the two you return decides **where the shading happens**, and nothing else:

.. list-table::
   :header-rows: 1
   :widths: 26 37 37

   * -
     - ``slang.rayQuery``
     - ``slang.traceRays``
   * - Traversal
     - Inline, inside the ray-generation shader
     - A ray-tracing pipeline with a shader binding table
   * - Shading
     - In the ray-generation shader
     - In separate entry points the table dispatches to
   * - Extra entry points
     - None
     - One ``miss`` and one hit group, in the same source file
   * - Extra launch fields
     - None
     - ``miss``, ``hit``, ``payloadSize``, ``attributeSize``

.. tab-set::

   .. tab-item:: Inline
      :sync: inline

      .. literalinclude:: ../../../examples/python/spg-raygen/RaygenCornellBox.slang.lua
         :language: lua
         :start-after: -- [snippet:raygen-launch]
         :end-before: -- [/snippet:raygen-launch]
         :emphasize-lines: 5, 17
         :caption: ``RaygenCornellBox.slang.lua``, from the runnable :doc:`ray generation example <../../examples/python_spg_raygen>`

      ``slang.rayQuery`` in place of ``slang.dispatch``, and the scene bound by name. That is the
      whole difference from a compute node.

   .. tab-item:: Pipeline
      :sync: pipeline

      .. literalinclude:: ../../../examples/python/spg-raygen/RaygenCornellBoxPipeline.slang.lua
         :language: lua
         :start-after: -- [snippet:pipeline-launch]
         :end-before: -- [/snippet:pipeline-launch]
         :emphasize-lines: 5-9
         :caption: ``RaygenCornellBoxPipeline.slang.lua``, from the runnable :doc:`ray generation example <../../examples/python_spg_raygen>`

      The entry points are named here, not discovered. ``payloadSize`` and ``attributeSize`` are
      byte sizes: the payload is the struct a hit or miss writes back, and the attributes are the
      built-in triangle barycentrics.

The acceleration structure is declared like any other resource, in both:

.. literalinclude:: ../../../examples/python/spg-raygen/RaygenCornellBox.slang
   :language: hlsl
   :start-after: // [snippet:raygen-bindings]
   :end-before: // [/snippet:raygen-bindings]
   :caption: ``RaygenCornellBox.slang``, from the runnable :doc:`ray generation example <../../examples/python_spg_raygen>`

How It Works
------------

What the Node Receives
~~~~~~~~~~~~~~~~~~~~~~

A shader living under a RenderProduct is given two things with **no authored input and no
connection in the scene**:

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - What
     - How it arrives
   * - The scene acceleration structure
     - A resource, bound with ``slang.binding("scene", inputs["scene"])``.
   * - That product's camera, and its unit factors
     - The :doc:`value-inputs <values>` ``sceneTransform``, ``sceneRenderScaleFactor`` and ``sceneMetersPerRenderUnit``.

``sceneTransform`` is the camera-to-trace-space transform. Rays are therefore authored in
ordinary scene-unit camera space, the camera at the origin looking down -Z, and placed by that
matrix, so the shader never needs to know where the camera is in the world.

The transform folds in the render scale, so ray ``TMax`` values are scaled by
``sceneRenderScaleFactor`` and returned distances divided by it.

Shading Through the Table
~~~~~~~~~~~~~~~~~~~~~~~~~

``slang.traceRays`` *only.* With an inline ``RayQuery`` the ray-generation shader reads the
traversal result directly. With a pipeline it never sees the traversal, so everything it needs
travels back in a payload struct that the hit and miss shaders write:

.. literalinclude:: ../../../examples/python/spg-raygen/RaygenCornellBoxPipeline.slang
   :language: hlsl
   :start-after: // [snippet:pipeline-entrypoints]
   :end-before: // [/snippet:pipeline-entrypoints]
   :caption: ``RaygenCornellBoxPipeline.slang``, from the runnable :doc:`ray generation example <../../examples/python_spg_raygen>`

**Exactly one hit group is supported.** ``hit`` is an array, but more than one entry is rejected
by name: the dispatch uses a zero-stride hit-group table, so every scene hit invokes group 0 and a
second group would never run. ``miss`` may hold several, and the index you pass to ``TraceRay``
selects among them.

**A hit group may also name an any-hit shader.** ``{ closesthit = "...", anyhit = "..." }``.
``closesthit`` is required; ``anyhit`` is optional and, when present, is compiled into the same
group. It is where a hit is inspected and possibly ignored, alpha-tested geometry being the usual
reason, rather than shaded.

``payloadSize`` **and** ``attributeSize`` **are byte counts you work out yourself.** Nothing derives
them from the struct. The payload above is one ``float`` and three ``uint``, so 16; the built-in
triangle attributes are two floats, so 8. Each is a whole number from 0 to 65535, and anything
else is rejected by name.

**The two produce the same picture.** The example ships the same Cornell box both ways, and both
pass the same checks. Choose the pipeline when a hit needs to do work the ray-generation shader
cannot express inline, not because it renders differently.

No Geometry Is Exposed
~~~~~~~~~~~~~~~~~~~~~~

A hit yields the distance and the surface's identity, its instance and primitive index, and
nothing else. There are no vertex buffers, no index buffers and no material data. This is a
deliberate boundary, not an oversight.

Anything else a shader needs has to be derived from tracing. The :doc:`ray generation example <../../examples/python_spg_raygen>` does this for
surface normals: a triangle is flat, so three points on it define its plane exactly. The
primary ray gives one point and the surface's identity; two probe rays fired parallel to it,
offset sideways, give two more, and the cross product of the two edge vectors is the exact
geometric normal. It costs two extra rays per shaded hit, is re-derived every frame so it
works on moving and tessellated geometry, and degrades only on triangles smaller than the
probe offset.

Refer to :doc:`../../examples/python_spg_raygen`, which renders a Cornell box this way,
including hard ray-traced shadows from a second trace toward the light.

Verify It Worked
----------------

Render the same scene both ways and check that the assertions hold for each. In the example the
two agree on 99.85% of pixels: 101 of 65536 differ, deterministically, so a rerun of either form
reproduces its own image exactly. Expect close agreement rather than an identical image.

Check the render against what the shader encodes rather than against a reference image. The
:doc:`ray generation example <../../examples/python_spg_raygen>` asserts four things: that no ray
escaped the box, that each wall's dominant colour channel matches its normal, that off-axis
normals are present in quantity, and that both shadowed and lit pixels exist. Those four fail
separately if the trace, the shading or the light is wrong, and none of them needs a golden
image.

**A pre-compiled SPIR-V binary cannot be used.** A ray-tracing pipeline is assembled from shader-database
handles, which byte code has none of, so a ray-generation node takes ``.slang`` source or a
``.slang-module``. Refer to :doc:`precompiled`. Everything else that constrains a Slang node
applies here too, including the Vulkan requirement.

When It Goes Wrong
------------------

- Nothing is traced: the scene binding is missing, or the node is not under a RenderProduct
  with a camera.
- Everything is black: rays are being authored in the wrong space. Place them with
  ``sceneTransform`` rather than assuming world coordinates.

Related
-------

:doc:`values`, :doc:`descriptor_sets`, :doc:`../ref/lua_slang`, :doc:`../../examples/python_spg_raygen`
