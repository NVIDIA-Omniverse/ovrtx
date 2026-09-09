.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-do-state:

Keep State Across Frames
========================

**Goal.** Let a node read what it wrote last frame.

**Before you start.** :doc:`aovs`.

The Shape
---------

Mark the output stateful when you describe it. It is then never handed out fresh:

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      .. code-block:: lua

          outputs["History"] = cuda.image(width, height, cuda.float4, cuda.stateful)

   .. tab-item:: Slang
      :sync: slang

      .. code-block:: lua

          outputs["History"] = slang.image(image.shape, slang.float4, slang.stateful)

How It Works
------------

Highlighted: the stateful allocation, and directly beneath it two ordinary outputs, which are
handed out fresh every frame. One marker is the entire difference.

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      .. literalinclude:: ../../../examples/python/spg-stateful/TrailKernel.cu.lua
         :language: lua
         :start-after: -- [snippet:trail-alloc]
         :end-before: -- [/snippet:trail-alloc]
         :emphasize-lines: 11, 13-14
         :caption: ``TrailKernel.cu.lua``, from the runnable :doc:`stateful node example <../../examples/python_spg_stateful>`

   .. tab-item:: Slang
      :sync: slang

      .. literalinclude:: ../../../examples/python/spg-stateful/TrailKernel.slang.lua
         :language: lua
         :start-after: -- [snippet:trail-slang-alloc]
         :end-before: -- [/snippet:trail-slang-alloc]
         :emphasize-lines: 8, 10-11
         :caption: ``TrailKernel.slang.lua``, from the runnable :doc:`stateful node example <../../examples/python_spg_stateful>`

``stateful`` **is a trailing argument** to the allocator that describes the output, ``image`` or
``empty`` alike, on either language's table.

.. _spg-stateful-zeroed:

**A stateful resource is zero-initialised on first use.** The first frame reads zeros rather
than whatever was in memory, so a node needs no special case for it.

**It need not be published.** A stateful output is usually scratch space for the node, so it
needs no RenderVar. It may use whatever format the algorithm wants, regardless of what the
node publishes.

The scene proves it by omission. The highlighted ``orderedVars`` lists the input and the two
published images. ``History``, which the whole effect depends on, is not there and needs no
RenderVar of its own.

.. literalinclude:: ../../../examples/python/spg-stateful/trail_scene.usda
   :language: usda
   :start-after: # [snippet:render-graph]
   :end-before: # [/snippet:render-graph]
   :emphasize-lines: 7
   :caption: ``trail_scene.usda``, from the runnable :doc:`stateful node example <../../examples/python_spg_stateful>`

**Ordinary outputs carry no such guarantee.** Do not rely on a per-frame output retaining
anything, and write every pixel you intend to publish.

**There are three ways to carry something into the next frame, and they differ in what owns the
data.** A stateful output is the node's own resource, handed back to it and to nobody else. A
previous-frame read is an AOV, so any node that connects to it sees the same history, and it reaches
back further than one frame; refer to :doc:`previous_frame`. A cached computation never reaches the
GPU at all and is about not rebuilding work in Lua; refer to :doc:`caching`. Pick by asking who
needs the data and whether the GPU ever has to see it.

Verify It Worked
----------------

Remove the stateful marker and compare. The feedback should collapse to a single frame's
worth of data. The :doc:`stateful node example <../../examples/python_spg_stateful>` measures
exactly this, and reports the lit area with and without the history: with feedback running it is
more than ten times larger. The counts themselves move from run to run, because the image is still
converging; the ratio is what carries the result.

When It Goes Wrong
------------------

- Nothing accumulates: the marker is missing, or the node is writing a different resource than
  it reads.
- The first frame looks wrong: it is reading zeros, which is the defined behaviour.

Related
-------

:doc:`previous_frame`, :doc:`caching`, :doc:`../../examples/python_spg_stateful`
