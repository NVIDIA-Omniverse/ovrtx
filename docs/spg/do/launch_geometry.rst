.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-do-launch-geometry:

Control the Launch Geometry
===========================

**Goal.** Configure how the node's GPU work is launched: how many threads run in a group, and how
many groups run.

**Before you start.** A node that runs, from :doc:`../first_node`.

The Shape
---------

The launch model is the one you already use. Only the names change.

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      Threads in a group is ``block``. Number of groups is ``grid``. Both are keys on the table
      ``cuda.kernel`` returns, and ``grid`` counts groups, not threads.

      A 1024 x 1024 output, one thread per pixel:

      .. code-block:: lua

          return cuda.kernel({
              args  = { --[[ the kernel's parameters ]] },
              block = { 16, 16 },      -- 256 threads per block
              grid  = { 64, 64 },      -- 64 x 64 blocks covers 1024 x 1024
          })

   .. tab-item:: Slang
      :sync: slang

      Threads in a group is ``numthreads``, declared in the shader. Number of groups is ``grid``, a
      key on the table ``slang.dispatch`` returns, and it counts groups, not threads.

      A 1024 x 1024 output, one thread per pixel:

      .. code-block:: hlsl

          // in the shader
          [numthreads(16, 16, 1)]      // 256 threads per group
          void myNode(uint3 tid : SV_DispatchThreadID)

      .. code-block:: lua

          -- in the launch script
          return slang.dispatch({
              bind = { --[[ the bound resources ]] },
              grid = { 64, 64, 1 },    -- 64 x 64 x 1 groups
          })

How It Works
------------

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      **Both keys are optional.** Left out, SPG derives them from the first output's shape. That
      gives one thread per element, which is the mapping an image-shaped kernel wants.

      **What it derives.** The block is 16 x 16 x 1, or 256 x 1 x 1 when the resource it derived
      from has rank 1 or 0. The grid is that resource's shape divided by the block and rounded up,
      reading ``shape[0]`` as height, ``shape[1]`` as width and ``shape[2]`` as depth.

      **State them when the iteration domain is not the output.** A kernel whose threads walk a
      buffer, or that runs one thread per column rather than one per pixel, has to say so. Sizing
      the grid yourself means dividing that domain by the block and rounding **up**, or the last
      partial group is never launched and the far edge is never reached.

      **A short table is fine.** ``cuda.kernel`` takes fewer than three components and fills the
      rest with 1, so ``block = { 16, 16 }`` is a 2D block and ``block = { 256 }`` is a 1D one.

      ``sharedMemSize`` **is dynamic shared memory in bytes**, the third argument of an ordinary
      CUDA launch.

      The :doc:`blur example <../../examples/python_spg_blur>` runs both cases side by side. Its
      horizontal pass takes one thread per output pixel and states nothing:

      .. filtered-literalinclude:: ../../../examples/python/spg-blur/BlurKernel.cu.lua
         :language: lua
         :start-after: -- [snippet:blur-horizontal-launch]
         :end-before: -- [/snippet:blur-horizontal-launch]
         :exclude-pattern: ^\s*--\s*\[/?snippet:
         :caption: ``BlurKernel.cu.lua``, from the runnable :doc:`blur example <../../examples/python_spg_blur>`

      Its vertical pass gives each thread a whole column to walk, so the domain is the width alone
      and the derived geometry would be wrong:

      .. filtered-literalinclude:: ../../../examples/python/spg-blur/BlurKernel.cu.lua
         :language: lua
         :start-after: -- [snippet:blur-vertical-launch]
         :end-before: -- [/snippet:blur-vertical-launch]
         :exclude-pattern: ^\s*--\s*\[/?snippet:
         :emphasize-lines: 22-23
         :caption: ``BlurKernel.cu.lua``, from the runnable :doc:`blur example <../../examples/python_spg_blur>`

      A pre-compiled ``.ptx``, ``.cubin`` or ``.fatbin`` changes nothing here, because launch
      geometry lives in the launch script and is never read from the artifact.

   .. tab-item:: Slang
      :sync: slang

      **The shader owns the group size.** ``[numthreads(x, y, z)]`` is where it is declared, and
      SPG reads it back by reflection. A shader that declares one needs nothing in the launch
      script, and SPG divides the output's shape by it to size the grid.

      ``InvertKernel.slang``, in the runnable
      :doc:`pipeline example <../../examples/python_spg_pipeline>`, declares
      ``[numthreads(32, 32, 1)]``, and its launch script says nothing about the group size.

      ``numthreads`` **tells SPG the group size the shader was compiled with**, so it can divide
      the output's shape into groups. It is for a shader that cannot describe itself, which means
      a ``.spv`` binary: SPIR-V byte code carries no reflection. Refer to :doc:`precompiled`.

      .. code-block:: lua

          -- in the launch script, for a .spv
          numthreads = { 16, 16, 1 },

      **Give the size the binary was built with.** Nothing compares the two, so a value that
      differs from the byte code produces a grid that under- or over-covers the output.

      **Where the shader declares one as well, the shader's is used**, since reflection has read
      the real size. The disagreement is logged at INFO level, which the renderer does not print
      at its default log level.

      **Both keys need exactly three components.** ``slang.dispatch`` rejects a ``numthreads`` or a
      ``grid`` that is not a 3-element table, and reports it rather than guessing. Write the
      trailing ``1`` for a 2D or 1D launch.

      **The grid is optional.** Without it SPG divides the output's shape by the group size,
      which gives one invocation per output element. State it only when that is not the mapping you
      want, such as one thread per column of an image rather than one per pixel.

      The :doc:`blur example <../../examples/python_spg_blur>` does both. Its horizontal pass
      states no grid, taking one invocation per pixel; its vertical pass gives each invocation a
      whole column, so the domain is the width alone:

      .. filtered-literalinclude:: ../../../examples/python/spg-blur/BlurKernel.slang.lua
         :language: lua
         :start-after: -- [snippet:blur-slang-vertical-launch]
         :end-before: -- [/snippet:blur-slang-vertical-launch]
         :exclude-pattern: ^\s*--\s*\[/?snippet:
         :emphasize-lines: 24
         :caption: ``BlurKernel.slang.lua``, from the runnable :doc:`blur example <../../examples/python_spg_blur>`

      .. _spg-slang-no-group-size:

      **With a group size from neither place, the node does not run.** A ``.spv`` whose launch
      script states neither ``numthreads`` nor ``grid`` leaves nothing to derive a grid from. SPG
      reports which of the two to supply and skips the node, so it publishes nothing rather than
      covering part of the output.

      **A ray-generation node states neither.** Its grid is the output AOV's shape, one ray per
      element, and there is no thread group to size. Refer to :doc:`raygen`.

Verify It Worked
----------------

Have the GPU code write each element's own linear index, then read the output back and check that
element ``i`` holds ``i``. Every mismatch is an element the launch never reached. Under-coverage
produces a plausible image with a band or a corner missing rather than an error, so it survives a
casual look at the picture.

A node that can be made the identity gives the same proof without a special kernel. The
:doc:`blur example <../../examples/python_spg_blur>` sets its radius to zero, which makes both
passes copy their input, and prints ``pixels differing from the input: 0``. One unreached column
would show up in that count.

When It Goes Wrong
------------------

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      - A band or corner of the output is unwritten: the grid is too small. Round up when dividing
        the iteration domain by the block.
      - Nothing is written at all: the bounds test in the kernel rejects every thread. Check the
        order of the width and height it was passed, in
        :ref:`Shapes and Types <spg-shapes-and-types>`.

   .. tab-item:: Slang
      :sync: slang

      - A band or corner of the output is unwritten: an explicit ``grid`` is too small, or the
        shader's ``[numthreads]`` is not what the grid was sized against.
      - The node does not load: ``numthreads`` or ``grid`` is not a 3-element table. The message
        names which.
      - The node publishes nothing and the log names ``numthreads``: a ``.spv`` with no group size
        from either place. Refer to
        :ref:`with a group size from neither place <spg-slang-no-group-size>`.
      - The log reports that the script and the shader disagree: the shader's size was used. Bring
        the script's into line or drop it.
      - Nothing is written at all: the bounds test in the shader rejects every invocation. Check
        the order of the width and height it was passed, in
        :ref:`Shapes and Types <spg-shapes-and-types>`.

Related
-------

:doc:`textures_buffers`, :doc:`descriptor_sets`, :doc:`precompiled`, :doc:`../ref/lua_cuda`,
:doc:`../ref/lua_slang`, :doc:`../../examples/python_spg_blur`
