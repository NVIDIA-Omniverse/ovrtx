.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-do-generate:

Write a Node With No Input
==========================

**Goal.** Build an AOV out of authored values alone, with no AOV coming in.

**Before you start.** :doc:`values`, and a node that runs.

The Shape
---------

Declare typed attributes and an output, and no ``opaque inputs:`` port at all:

.. literalinclude:: ../../../examples/python/spg-generate/CheckerKernel.usda
   :language: usda
   :start-after: # [snippet:checker-shader-definition]
   :end-before: # [/snippet:checker-shader-definition]
   :emphasize-lines: 12-16, 18
   :caption: ``CheckerKernel.usda``, from the runnable :doc:`generating-node example <../../examples/python_spg_generate>`

The shader definition is the same either language, apart from what
``info:spg:sourceAsset`` points at.

How It Works
------------

**A resource-input is optional; a node needs no AOV to run.** Nothing else changes: the launch
script is still required, the entry point is still named the same way, and the output is
published like any other.

**Nothing hands you a shape, so state one.** A node with a resource-input can take its width and
height from that input's descriptor. This one has no input descriptor to read, so the size comes
from somewhere you control, which usually means typed attributes:

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      .. literalinclude:: ../../../examples/python/spg-generate/CheckerKernel.cu.lua
         :language: lua
         :start-after: -- [snippet:checker-launch]
         :end-before: -- [/snippet:checker-launch]
         :emphasize-lines: 7-8, 12
         :caption: ``CheckerKernel.cu.lua``, from the runnable :doc:`generating-node example <../../examples/python_spg_generate>`

   .. tab-item:: Slang
      :sync: slang

      .. literalinclude:: ../../../examples/python/spg-generate/CheckerKernel.slang.lua
         :language: lua
         :start-after: -- [snippet:checker-slang-launch]
         :end-before: -- [/snippet:checker-slang-launch]
         :emphasize-lines: 7-8, 12
         :caption: ``CheckerKernel.slang.lua``, from the runnable :doc:`generating-node example <../../examples/python_spg_generate>`

Verify It Worked
----------------

Build something you can recompute exactly on the host, then compare pixel for pixel. The
:doc:`checkerboard example <../../examples/python_spg_generate>` draws its pattern from an
authored square size and two authored colours, rebuilds the same pattern in NumPy, and prints
``pixels differing from the host-computed pattern: 0``. Anything above zero means a value did not
arrive or the launch did not cover the output.

When It Goes Wrong
------------------

- Nothing appears: nothing asked for the output, so the node never ran. Give it a RenderVar and
  list it in ``orderedVars``. Refer to :ref:`Nothing Appears <spg-symptom-nothing>`.

Related
-------

:doc:`values`, :doc:`aovs`, :doc:`raygen`, :doc:`../../examples/python_spg_generate`
