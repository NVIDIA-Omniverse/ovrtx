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

Give the node memory of its own. State it on ``self.memory`` with the allocator you would use
for an output, and pass it to the kernel with the wrapper you would use for an output:

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      .. code-block:: lua

          self.memory["History"] = cuda.image(width, height, cuda.float4)
          -- ...
          cuda.SurfaceObject(self.memory["History"])

   .. tab-item:: Slang
      :sync: slang

      .. code-block:: lua

          self.memory["History"] = slang.image(image.shape, slang.float4)
          -- ...
          slang.RWTexture2D(self.memory["History"])

SPG creates the memory, fills it with zeros, and hands the same resource back on every run for
as long as the node lives. The GPU code reads and writes it like an output.

How It Works
------------

Highlighted: the memory, and directly beneath it two outputs, which are handed out
fresh every frame.

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      .. literalinclude:: ../../../examples/python/spg-stateful/TrailKernel.cu.lua
         :language: lua
         :start-after: -- [snippet:trail-alloc]
         :end-before: -- [/snippet:trail-alloc]
         :emphasize-lines: 10, 12-13
         :caption: ``TrailKernel.cu.lua``, from the runnable :doc:`stateful node example <../../examples/python_spg_stateful>`

   .. tab-item:: Slang
      :sync: slang

      .. literalinclude:: ../../../examples/python/spg-stateful/TrailKernel.slang.lua
         :language: lua
         :start-after: -- [snippet:trail-slang-alloc]
         :end-before: -- [/snippet:trail-slang-alloc]
         :emphasize-lines: 7, 9-10
         :caption: ``TrailKernel.slang.lua``, from the runnable :doc:`stateful node example <../../examples/python_spg_stateful>`

``self`` **is the node itself.** It is a table SPG gives the launch function on every call, with
one field per thing the launch states about the node: ``self.memory``, the node's memory by name,
and ``self.stateful``, described below. ``image`` and ``empty`` describe a memory as they describe
an output, buffer or image alike, on either language's table.

**A memory is not a port.** No ``outputs:`` attribute declares it, nothing connects to it, no
RenderVar names it and it is never published.

.. _spg-stateful-zeroed:

**Memory is zero-initialised when SPG creates it.** The first frame reads zeros rather than
whatever was in GPU memory, so a node needs no special case for it.

**Memory may use whatever format the algorithm wants**, regardless of what the node publishes.
Here ``History`` is ``float4`` while the published images are ``uchar4``.

**Memory keeps its contents while its description stays the same.** A launch that states it
with another size, element type, or as a buffer instead of an image gets new memory, zeroed. A
launch that does not state it leaves it as it is, and a later launch that states it again gets
the kept contents.

**Memory is the node's, per render product and per GPU.** A graph that runs for two render
products keeps a memory for each, and two nodes that both name a memory ``acc`` each have
their own. It is released with the node's graph; a node rebuilt after an edit of the scene
starts with zeros again.

**Ordinary outputs carry no such guarantee.** Do not rely on a per-frame output retaining
anything, and write every pixel you intend to publish.

When the Scene Must See the State
---------------------------------

Memory is private. When the state itself is something the scene reads, a running average
that is also published, mark the **output** stateful instead: the output is then never handed
out fresh, and it is still a port, so a RenderVar can publish it and another node can connect
to it.

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      .. code-block:: lua

          outputs["Average"] = cuda.image(width, height, cuda.float4, cuda.stateful)

   .. tab-item:: Slang
      :sync: slang

      .. code-block:: lua

          outputs["Average"] = slang.image(image.shape, slang.float4, slang.stateful)

``stateful`` is a trailing argument to the allocator, ``image`` or ``empty`` alike. Setting
``self.stateful = true`` instead marks every output of the node stateful at once. A stateful
output is zero-initialised and kept exactly as memory is; the difference is only that it is a
port.

**There are four ways to carry something into the next frame, and they differ in who owns the
data.** Memory is the node's own resource, handed back to it and to nobody else. A stateful
output is the node's resource too, but it is a port the scene can publish and other nodes can
connect to. A previous-frame read is an AOV, so any node that connects to it sees the same
history, and it reaches back further than one frame; refer to :doc:`previous_frame`. A cached
computation never reaches the GPU at all and is about not rebuilding work in Lua; refer to
:doc:`caching`. Pick by asking who needs the data and whether the GPU ever has to see it.

Verify It Worked
----------------

Turn the memory into an ordinary output and compare. The feedback collapses to a single
frame's worth of data. In the :doc:`stateful node example <../../examples/python_spg_stateful>`
the tail behind the ball vanishes from ``trail.png``, which then shows the same ball as
``live.png`` over a darker backdrop.

When It Goes Wrong
------------------

- Nothing accumulates: the memory is stated as an output, or the node is writing a different
  resource than it reads, or the description changes from launch to launch.
- The first frame looks wrong: it is reading zeros, which is the defined behaviour.
- The node does not run and the log names ``self.memory['...']``: the entry is not a description.
  Every entry of ``self.memory`` is what ``image`` or ``empty`` returns, under a string key.

Related
-------

:doc:`previous_frame`, :doc:`caching`, :doc:`../../examples/python_spg_stateful`
