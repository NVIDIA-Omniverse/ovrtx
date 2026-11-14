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

      It becomes a kernel parameter, declared in the signature:

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

**A scene can override the default.** The scene states the value on the shader instance; a
value stated there overrides the definition's default.

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

**On CUDA a numeric vector can pass by value or by pointer.** A dtype constructor such as
``cuda.float3`` passes every component by value to a matching ``float3`` kernel parameter.
``cuda.array`` passes a pointer to the components instead; use it for matrices or when the
kernel expects a pointer. A quaternion can use a matching four-component dtype constructor
or ``cuda.array``. On Slang the value goes into the parameter block and the shader declares
it as a field of its struct.

**Slang integer fields require matching element widths.** A narrower integer value is rejected
with an error naming the value and both widths, for scalar and vector fields as well as arrays
and matrices. Use ``slang.int`` or ``slang.uint`` for a 32-bit integer field.

**A token and an asset arrive as arrays.** A ``token`` arrives as a null-terminated ``char`` array;
CUDA can pass it directly with ``array``. To pack token bytes into a Slang ``uint4`` field, construct
the four 32-bit words explicitly, as below; a byte array does not match that field's element width.
An ``asset`` arrives as the file's raw bytes and is read as whichever dtype you name. The bytes must make
whole elements of that dtype: an asset with bytes left over after its last whole element, or too short
for one element, stops the node's graph.

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      .. code-block:: lua

          cuda.array(inputs["mode"])              -- token -> const char*
          cuda.array(inputs["lut"], cuda.uint)    -- asset -> const unsigned int*

   .. tab-item:: Slang
      :sync: slang

      .. code-block:: lua

          local token = inputs["mode"].value
          assert(#token < 16) -- reserve a byte for the null terminator
          local words = { 0, 0, 0, 0 }
          for i = 1, #token do
              local word = (i - 1) // 4 + 1
              words[word] = words[word] | (string.byte(token, i) << (((i - 1) % 4) * 8))
          end
          -- Inside the parameter block, matching a uint4 field:
          slang.uint4(words[1], words[2], words[3], words[4])
          slang.StructuredBuffer(slang.array(inputs["lut"], slang.uint))  -- asset -> StructuredBuffer<uint>

A USD array attribute, ``float[]`` say, is a buffer already and reaches a Slang shader as a
read-only ``StructuredBuffer<float>``. Refer to :doc:`upload_data`.

A USD array attribute handed to ``cuda.array`` or ``slang.array``:

- Without a dtype, it reaches the GPU as authored: a ``float3[]`` arrives as ``float3`` elements.
- With a dtype of another number of components per element, its components are regrouped: a
  ``float[]`` passed as ``float2`` arrives as pairs. The components must make whole elements of the
  dtype, or the node's graph stops.
- A ``uchar[]`` array given a dtype is read the way an asset is: its bytes are taken as elements of
  that dtype.
- Any other array given a dtype of another element type has each value converted, then grouped as
  above: a ``double[]`` passed as ``float2`` arrives as pairs of floats. The conversion runs in the
  launch script on every frame and counts every value against the script's instruction and memory
  :ref:`limits <spg-lua-sandbox>`, so a large array stops the node's graph.

A value converted to an integer element type:

- An integer that an unsigned type does not hold wraps: the element keeps the integer modulo 2 to
  the power of the type's bits, so ``-1`` from an ``int[]`` arrives as 4294967295 in a ``uint``. A
  ``uint64`` keeps all 64 bits of any integer. SPG logs the first integer that wraps at info level,
  once per node and input.
- An integer that a signed type does not hold stops the node's graph.
- Any other value is truncated toward zero, and the node's graph stops when the result does not fit
  the type, such as ``-1.0`` from a ``double[]`` converted to ``uint``, or when the value is not a
  finite number.

Author the array in the element type the GPU code reads.

**An array may hold no elements.** An array authored as ``[]``, written empty while the stage runs,
or connected to an attribute that holds none reaches the node with no elements: ``.value`` is an
empty list and ``sourceShape[1]`` is 0.

- ``cuda.array`` hands the kernel a null pointer, and a Slang buffer binds a placeholder the shader
  must not read, so pass the count to the GPU code and read no element past it.
- A parameter-block array field, or a place the launch script states, takes no elements and stays
  zero. A scalar, vector or matrix field cannot take an empty array, and the node's graph stops.
- In a shader that does not describe itself, such as a ``.spv`` binary, SPG sizes a parameter block
  from the offsets the launch script states and the sizes of the values placed there. A block whose
  size comes out as zero, such as one that holds only an empty array at offset 0, stops the node's
  graph with an error naming the first value placed there that cannot be laid out, else the empty
  array.
- ``cuda.array({}, dtype)`` and ``slang.array({}, dtype)`` make an array of no elements as well, and
  so does a ``uchar[]`` of no bytes given a dtype.

**Passing an array on is free in Lua.** An array, token or asset input handed to ``array`` without a
dtype, with a dtype of its own element type, or, for a ``uchar[]`` array or an asset, with any dtype,
reaches the GPU without its elements passing through the launch script. Reading ``.value`` builds a
Lua table of all its elements, every frame; reading it alone does not change what the kernel
receives.

Changes the script makes to that table before it hands the input to ``array`` reach the kernel,
which still receives as many elements as the input has, taken in order from the table:

- An element the table lacks arrives as 0, and elements past the input's length are not passed on.
- A fraction in an integer array arrives truncated toward zero, and ``true`` and ``false`` arrive
  as 1 and 0.
- A string, even one that holds a number, or a table where a number belongs stops the node's graph.
- An integer written into an unsigned element that does not hold it wraps, so ``300`` in a
  ``uchar`` array arrives as 44. A fraction whose truncated value does not fit, such as ``300.5`` in
  a ``uchar`` array, stops the graph, and so does an integer that a signed element type does not
  hold.
- A ``uint64`` value is the Lua integer with the same 64 bits, as Lua's own ``string.unpack`` gives
  it. The largest Lua integer is 9223372036854775807, so a value above it reads as a negative number
  and converts to another element type as one. Any Lua integer written into a ``uint64`` keeps its
  bits, so ``0xFFFFFFFFFFFFFFFF`` and ``-1`` both set every bit.

Verify It Worked
----------------

Change the value in the scene and re-run. If the output does not change, the value never
reached the GPU. In the :doc:`pipeline example <../../examples/python_spg_pipeline>`, ``strength`` at ``0.0`` passes the image through
unchanged and ``1.0`` fully inverts it, so the two ends of the range are unmistakable.

When It Goes Wrong
------------------

- Wrong value, or garbage: the argument order does not match. Refer to
  :ref:`Wrong Pixels Rather Than No Pixels <spg-symptom-wrong-pixels>`.
- On CUDA, check that the dtype constructor matches the kernel parameter's element type and
  component count, or use ``cuda.array`` when the parameter is a pointer.
- On Slang, a wrong field count is an error and a wrong order only a warning. Refer to
  :doc:`descriptor_sets`.

Related
-------

:doc:`../ref/lua_contract`, :doc:`../ref/lua_cuda`, :doc:`../ref/lua_slang`
