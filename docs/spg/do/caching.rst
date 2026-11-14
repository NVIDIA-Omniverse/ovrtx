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

The launch function, the global function the launch script defines under the entry-point name, runs
every frame; the rest of the script runs once, when it is loaded. Wrap anything that does not change
per frame in ``static``:

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

``static`` **calls the function once and caches the result** for its arguments. When an argument
changes, the function runs again and its result replaces the cached one; calls with unchanged
arguments reuse what was computed before. Numbers, strings and booleans are compared by value. A
table is compared by which table it is, not by what it holds: changing a field of a table passed as
an argument does not run the function again, and a table built inside the launch function, such as
the one an array input's ``.value`` returns, is a new argument on every frame. The function can be written inline at the call site: it is
the same function on every launch.

An error raised by the function fails the launch.
The failed call stores no result; a later successful call is cached.

**One result per node and function.** ``static`` keeps, for each node and function, the result of
that node's most recent call. Nodes that run the same launch script file never reuse or replace each
other's results, also when they pass equal arguments, so each node computes its own result once. A node
built again, after an edit for instance, starts without results, and the results of a node that no
longer exists are released. What the script computes with ``static`` while it loads, outside the
launch function, belongs to the script, and no node reuses it.
A table ``static`` returns is the same table on every call of that
node that reuses it, so do not change it.

A cached result is also tied to the variables the function uses from outside itself, not to their
values. A variable declared at the top level of the script, outside the launch function, is the same
variable on every frame, so giving it a new value does not run the function again. A variable declared
inside the launch function is a new variable on every frame, so a function that uses one runs again on
every frame, even when its value does not change. Pass every value the function reads that can change
between frames, or that is declared inside the launch function, as an argument instead. Pass the
number, string or boolean itself, such as ``settings.radius``, not a table that holds it.

**This is about the launch script, not the GPU.** It stops the table being rebuilt on every frame,
which is Lua work under an instruction budget, and it is the cheapest of the three ways to avoid
redoing work across frames: :doc:`state` keeps a resource the node itself wrote, and
:doc:`previous_frame` keeps an AOV any node can read.

.. _spg-static-upload:

**The upload is separate.** An array whose bytes stay the same from frame to frame stays on the GPU
and is not copied again, whether or not it came from ``static``; an array whose bytes change is
copied again.

Verify It Worked
----------------

Call ``warning`` inside the cached function and count the lines over a run. Across a hundred frames
with an unchanging argument, the count must be one for each node that calls the function. One line per
frame means the cache key changes
every frame, and the usual cause is passing a :doc:`value-input <values>` as the wrapper it arrives
as, rather than as its ``.value``.

Use ``warning`` rather than ``info``: at the renderer's default log level ``info`` is not printed,
so an uncounted cache looks exactly like a working one. Refer to :doc:`../ref/lua_contract`.

When It Goes Wrong
------------------

- It runs every frame: an argument is changing, often because a value-input is being passed as
  the wrapper rather than as ``.value``.
- It runs every frame although its arguments do not change: the function uses a variable declared
  inside the launch function, or an argument is a table built on every frame. Pass the values
  themselves as arguments.
- The result does not follow a change: the function reads a value that is not one of its arguments,
  such as a variable declared at the top level of the script, or a field of a table argument whose
  contents change. Pass that value itself as an argument.
- The node's graph stops after its first run: the script reached a sandbox limit, such as one
  million instructions per call, and the log names the node. The limits are fixed and renewed each
  frame, so heavy work belongs in the GPU code rather than in Lua.

Related
-------

:doc:`upload_data`, :doc:`state`, :doc:`../ref/lua_contract`,
:doc:`../../examples/python_spg_blur`
