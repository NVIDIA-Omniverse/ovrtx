.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-do-values:

Types and Values
================

**Goal.** Give a node a number, vector or matrix authored in USD, and read it in the GPU code.

**Before you start.** A working node, from :doc:`../first_node`.

The Shape
---------

Declare a typed attribute on the shader definition. Anything not ``opaque`` is a value-input:

.. code-block:: usda

    float inputs:strength = 1.0

How It Works
------------

A value-input is declared once, alongside the ``opaque`` ports:

.. literalinclude:: ../../../examples/python/spg-pipeline/InvertKernel.usda
   :language: usda
   :start-after: # [snippet:invert-shader-definition]
   :end-before: # [/snippet:invert-shader-definition]
   :emphasize-lines: 11
   :caption: ``InvertKernel.usda``, from the runnable :doc:`pipeline example <../../examples/python_spg_pipeline>`

From there it reaches the GPU by a different route in each language.

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      It becomes an ordinary kernel parameter, declared in the signature like any other:

      .. literalinclude:: ../../../examples/python/spg-pipeline/InvertKernel.cu
         :language: c
         :start-after: // [snippet:invert-kernel]
         :end-before: // [/snippet:invert-kernel]
         :emphasize-lines: 6
         :caption: ``InvertKernel.cu``, from the runnable :doc:`pipeline example <../../examples/python_spg_pipeline>`

      The launch script places it in ``args`` at the position the signature expects:

      .. literalinclude:: ../../../examples/python/spg-pipeline/InvertKernel.cu.lua
         :language: lua
         :start-after: -- [snippet:invert-launch]
         :end-before: -- [/snippet:invert-launch]
         :emphasize-lines: 15
         :caption: ``InvertKernel.cu.lua``, from the runnable :doc:`pipeline example <../../examples/python_spg_pipeline>`

   .. tab-item:: Slang
      :sync: slang

      Values do not arrive individually. They are packed into one constant buffer, which the
      shader declares as a struct and reads through a ``ParameterBlock``:

      .. literalinclude:: ../../../examples/python/spg-pipeline/InvertKernel.slang
         :language: hlsl
         :start-after: // [snippet:invert-slang-kernel]
         :end-before: // [/snippet:invert-slang-kernel]
         :emphasize-lines: 11, 33
         :caption: ``InvertKernel.slang``, from the runnable :doc:`pipeline example <../../examples/python_spg_pipeline>`

      The launch script fills that block, in the order the struct declares the fields:

      .. literalinclude:: ../../../examples/python/spg-pipeline/InvertKernel.slang.lua
         :language: lua
         :start-after: -- [snippet:invert-slang-launch]
         :end-before: -- [/snippet:invert-slang-launch]
         :emphasize-lines: 13-15
         :caption: ``InvertKernel.slang.lua``, from the runnable :doc:`pipeline example <../../examples/python_spg_pipeline>`

.. _spg-value-wrapper:

**A value-input is a wrapper, not a number.** ``inputs["strength"]`` cannot be used in
arithmetic; that raises an error. Pass it through a dtype constructor to hand it to the GPU,
or read ``.value`` to compute with it in Lua.

**A scene can override the default.** The value on the shader definition is a default; a
shader instance in a scene may state its own.

.. literalinclude:: ../../../examples/python/spg-pipeline/pipeline_scene.usda
   :language: usda
   :start-after: # [snippet:render-graph]
   :end-before: # [/snippet:render-graph]
   :emphasize-lines: 34
   :caption: ``pipeline_scene.usda``, from the runnable :doc:`pipeline example <../../examples/python_spg_pipeline>`

**Every type you can author** is listed in :ref:`Value-Input Types <spg-value-input-types>`,
together with what each one becomes on the GPU.

**Two of them will catch you out.** A ``quatf`` or ``quatd`` is written ``(w, x, y, z)`` in USDA
and arrives as ``(x, y, z, w)``, so the identity quaternion authored ``(1, 0, 0, 0)`` reaches the
GPU as ``(0, 0, 0, 1)``. And 64-bit integers bind on CUDA but not on Slang, where the Vulkan
``shaderInt64`` feature is off.

**On CUDA a vector does not pass by value.** A ``float3``, a matrix or a quaternion is bound with
``cuda.array``, and the kernel parameter is a pointer to its components. Passed with a dtype
constructor instead, it reaches the kernel with only its first component intact. On Slang the
value goes into the parameter block and the shader declares it as an ordinary field.

**A token and an asset are arrays, not scalars**, so both are bound with ``array`` rather than with
a dtype constructor. A ``token`` arrives as a null-terminated ``char`` array and needs no dtype; an
``asset`` arrives as the file's raw bytes and is read as whichever dtype you name.

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      .. code-block:: lua

          cuda.array(inputs["mode"])              -- token -> const char*
          cuda.array(inputs["lut"], cuda.uint)    -- asset -> const unsigned int*

   .. tab-item:: Slang
      :sync: slang

      .. code-block:: lua

          slang.array(inputs["mode"])                             -- token, inside the parameter block
          slang.StructuredBuffer(slang.array(inputs["lut"], slang.uint))  -- asset -> StructuredBuffer<uint>

A USD array attribute, ``float[]`` say, is a buffer already and reaches a Slang shader as a
read-only ``StructuredBuffer<float>``. Refer to :doc:`upload_data`.

Verify It Worked
----------------

Change the value in the scene and re-run. If the output does not change, the value never
reached the GPU. In the :doc:`pipeline example <../../examples/python_spg_pipeline>`, ``strength`` at ``0.0`` passes the image through
unchanged and ``1.0`` fully inverts it, so the two ends of the range are unmistakable.

When It Goes Wrong
------------------

- Wrong value, or garbage: the argument order does not match. Refer to
  :ref:`Wrong Pixels Rather Than No Pixels <spg-symptom-wrong-pixels>`.
- On CUDA, the first component of a vector is right and the rest is noise: it was passed with a
  dtype constructor rather than with ``cuda.array``.
- On Slang, a wrong field count is an error and a wrong order only a warning. Refer to
  :doc:`descriptor_sets`.

Related
-------

:doc:`../ref/lua_contract`, :doc:`../ref/lua_cuda`, :doc:`../ref/lua_slang`
