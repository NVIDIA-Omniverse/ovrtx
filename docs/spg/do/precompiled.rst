.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-do-precompiled:

Compile It Yourself
===================

**Goal.** Build the GPU code with your own toolchain, or split it across files, instead of handing
SPG one source file to compile.

**Before you start.** A working node in the language you are building.

The Shape
---------

``info:spg:sourceAsset`` decides which of these happens. The extension is what SPG reads.

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      ``.cu`` is compiled by SPG on load. ``.ptx``, ``.cubin`` and ``.fatbin`` are loaded already
      compiled.

   .. tab-item:: Slang
      :sync: slang

      ``.slang`` is compiled by SPG on load. ``.slang-module`` and ``.spv`` are loaded already
      compiled, and the two are not interchangeable.

How It Works
------------

What Stays the Same
~~~~~~~~~~~~~~~~~~~

- **The launch script is still required, and still found the same way**, by appending ``.lua`` to
  the source asset path. ``InvertKernel.ptx`` pairs with ``InvertKernel.ptx.lua``. SPG has no other
  way to learn the output shapes or the binding order.
- **The argument list still has to match what the code was compiled with.** An artifact
  carries no signature SPG can check a CUDA ``args`` list against, so a mismatch shows up as the
  kernel reading the wrong memory rather than as an error at load.

What the Artifact Is
~~~~~~~~~~~~~~~~~~~~

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      A ``.ptx``, ``.cubin`` or ``.fatbin`` is handed to the CUDA driver as it is, and NVRTC is
      not involved. ``.ptx`` is portable and JIT-compiled by the driver for the target
      architecture, ``.cubin`` targets one architecture and skips that JIT, and ``.fatbin``
      carries several architectures in one file.

      ``info:spg:sourceAsset:subIdentifier`` still names the entry point, now resolved as a symbol
      in the loaded module. The name has to appear in the binary exactly as written, so compile
      the entry point as ``extern "C"``; a mangled C++ symbol will not be found.

      **A CUDA node is one translation unit, compiled against a single include directory.** That
      directory is the CUDA installation SPG finds: ``CUDA_PATH`` or ``CUDA_HOME`` if either is set
      in the environment, otherwise the headers bundled with the renderer. The directory holding
      the ``.cu`` is never on the path, so ``#include "MyHelpers.cuh"`` beside the source does not
      resolve. To split a node across files, compile it with ``nvcc`` and ship the ``.ptx``,
      ``.cubin`` or ``.fatbin``.

   .. tab-item:: Slang
      :sync: slang

      The two forms are not interchangeable.

      ``.slang-module`` holds Slang IR, which is target-agnostic: it is lowered to whichever
      graphics backend is active when the shader is linked, so one artifact serves any of them. It
      carries its entry point and its binding layout, so the node binds as a source node does.

      ``.spv`` holds SPIR-V, already lowered for Vulkan, and carries no binding layout SPG can
      read:

      - **Everything reflection would have supplied has to be stated instead**, which makes
        :doc:`descriptor_sets` a prerequisite for this form rather than optional reading.
        :ref:`What reflection fills in <spg-do-reflection>` lists the items one by one.
      - **Compute only.** A ray-tracing pipeline is assembled from shader-database handles, which
        byte code has none of, so those stages take ``.slang`` source or a ``.slang-module``.
        Refer to :doc:`raygen`.
      - **The entry point comes from the binary**, not from ``subIdentifier``, because the
        compiler names it independently: ``slangc`` emits ``main`` whatever ``-entry`` says.

      **A shader can be split across files.** ``import MyHelpers;`` resolves to
      ``MyHelpers.slang`` beside the shader. A symbol is visible to the importing shader only if it
      is declared ``public``. Imports are resolved during a source compile, so an artifact that is
      already compiled carries what it needs and does not re-resolve them.

      The :doc:`blur example <../../examples/python_spg_blur>` keeps the tap loop its two passes
      share in a module beside the shader:

      .. filtered-literalinclude:: ../../../examples/python/spg-blur/BlurTaps.slang
         :language: hlsl
         :start-after: // [snippet:blur-module]
         :end-before: // [/snippet:blur-module]
         :exclude-pattern: ^\s*//\s*\[/?snippet:
         :caption: ``BlurTaps.slang``, from the runnable :doc:`blur example <../../examples/python_spg_blur>`

Where the Files May Live
~~~~~~~~~~~~~~~~~~~~~~~~

An artifact is named by ``info:spg:sourceAsset`` like any other source, so it may sit beside the
scene, inside a ``.usdz`` package, or behind a URI, and its launch script follows it. Refer to
:ref:`Where Assets May Live <spg-asset-locations>`.

Verify It Worked
----------------

Render the same scene twice, once from source and once from the artifact, and compare the two
outputs byte for byte. They must be identical. Compare the content rather than checking that the
run completed: a node that loads and binds nothing still renders a plausible image from zeros.

When It Goes Wrong
------------------

- The entry point is not found: for CUDA the symbol has to be unmangled, so compile it as
  ``extern "C"``.
- A ``.spv`` on a ray-generation stage is rejected. Refer to :doc:`raygen`.
- An import does not resolve, on Slang: the module does not sit beside the shader, or its file
  name does not match the imported name.
- An ``#include`` does not resolve, on CUDA: one include directory is searched, never the
  directory the ``.cu`` sits in. Check what ``CUDA_PATH`` or ``CUDA_HOME`` point at.

Related
-------

:doc:`descriptor_sets`, :doc:`../ref/lua_cuda`, :doc:`../ref/lua_slang`,
:doc:`../../examples/python_spg_blur`
