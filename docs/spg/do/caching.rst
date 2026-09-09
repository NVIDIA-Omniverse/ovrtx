.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-do-caching:

Cache Work Across Frames
========================

**Goal.** Compute something once instead of every frame.

**Before you start.** :doc:`../ref/lua_contract`.

The Shape
---------

The launch script runs every frame. Wrap anything that does not change per frame in ``static``:

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      .. filtered-literalinclude:: ../../../examples/python/spg-blur/BlurKernel.cu.lua
         :language: lua
         :start-after: -- [snippet:blur-weights]
         :end-before: -- [/snippet:blur-weights]
         :exclude-pattern: ^\s*--\s*\[/?snippet:
         :caption: ``BlurKernel.cu.lua``, from the runnable :doc:`blur example <../../examples/python_spg_blur>`

      .. code-block:: lua

          -- at the call site, in place of gaussianWeights(radius)
          cuda.static(gaussianWeights, radius)

   .. tab-item:: Slang
      :sync: slang

      .. filtered-literalinclude:: ../../../examples/python/spg-blur/BlurKernel.slang.lua
         :language: lua
         :start-after: -- [snippet:blur-slang-weights]
         :end-before: -- [/snippet:blur-slang-weights]
         :exclude-pattern: ^\s*--\s*\[/?snippet:
         :caption: ``BlurKernel.slang.lua``, from the runnable :doc:`blur example <../../examples/python_spg_blur>`

      .. code-block:: lua

          -- at the call site, in place of gaussianWeights(radius)
          slang.static(gaussianWeights, radius)

How It Works
------------

``static`` **calls the function once and caches the result**, keyed on the arguments. When an
argument changes, the function runs again. Anything else reuses what was computed before.

**This is about the launch script, not the GPU.** It stops the table being rebuilt on every frame,
which is Lua work under an instruction budget, and it is the cheapest of the three ways to avoid
redoing work across frames: :doc:`state` keeps a resource the node itself wrote, and
:doc:`previous_frame` keeps an AOV any node can read.

.. _spg-static-upload:

**It does not stop the upload.** SPG keeps an uploaded buffer resident across frames only for a
tensor whose strides it reads as implicit row-major, and every array a launch script hands over
carries explicit ones, so the bytes are copied to the GPU again each frame. The renderer log says
so, once per frame per array::

    allocateOrReuseStaticTensorResource: tensor '...' is not dense/row-major (size=68, dense=68); not caching

For a filter kernel of a few dozen values that costs nothing measurable. Size a design around the
Lua saving rather than around the transfer.

Verify It Worked
----------------

Call ``warning`` inside the cached function and count the lines over a run. Across a hundred frames
with an unchanging argument the count must be one. One line per frame means the cache key changes
every frame, and the usual cause is passing a :doc:`value-input <values>` as the wrapper it arrives
as, rather than as its ``.value``.

Use ``warning`` rather than ``info``: at the renderer's default log level ``info`` is not printed,
so an uncounted cache looks exactly like a working one. Refer to :doc:`../ref/lua_contract`.

The :doc:`blur example <../../examples/python_spg_blur>` does this and reports the count. It
renders at two radii over some fifty frames and prints ``weight tables built: 2``.

When It Goes Wrong
------------------

- It runs every frame: an argument is changing, often because a value-input is being passed as
  the wrapper rather than as ``.value``.
- The script is stopped part way through: it exceeded the sandbox's instruction budget. That
  budget is fixed and renewed each frame, so heavy work belongs in the GPU code rather than in
  Lua.

Related
-------

:doc:`upload_data`, :doc:`state`, :doc:`../ref/lua_contract`,
:doc:`../../examples/python_spg_blur`
