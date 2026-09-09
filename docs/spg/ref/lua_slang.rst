.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-ref-slang:

The ``slang`` Lua Table
=======================

Every function and constant a ``.slang.lua`` launch script can use. For what a launch script
is and when it runs, refer to :doc:`lua_contract`.

Accepted source assets: ``.slang``, compiled on load, ``.slang-module``, pre-compiled Slang
IR, and ``.spv``, SPIR-V and compute only. Extensions are matched case-insensitively. That is
the complete list.

Slang nodes require the renderer to be running on Vulkan, the ovrtx default on Linux and
Windows.

Describing Outputs
------------------

Output descriptors state what an output has to be; SPG owns the memory. The split matches
CUDA: ``image`` is texture-backed, ``empty`` is buffer-backed.

.. list-table::
   :header-rows: 1
   :widths: 44 56

   * - Function
     - Description
   * - ``slang.image(width, height, dtype)``
     - A texture-backed output. Note the argument order against height-first shapes.
   * - ``slang.image(shape, dtype)``
     - The same, with the shape as a table: ``{width}``, ``{height, width}`` or ``{height, width, depth}``. This is how a texture of one or three dimensions is asked for. A texture has one, two or three dimensions and no more.
   * - ``slang.empty(shape, dtype)``
     - A buffer-backed output of arbitrary shape.
   * - ``slang.zeros(shape, dtype)``, ``slang.ones(shape, dtype)``, ``slang.full(shape, value, dtype)``
     - A buffer filled with zeros, ones, or a stated value.

``slang.image`` and ``slang.empty`` take an optional trailing ``slang.stateful``, which marks
the output persistent so SPG hands the same resource back next frame instead of a fresh one:

.. filtered-literalinclude:: ../../../examples/python/spg-stateful/TrailKernel.slang.lua
   :language: lua
   :start-after: -- [snippet:trail-slang-alloc]
   :end-before: -- [/snippet:trail-slang-alloc]
   :exclude-pattern: ^\s*--\s*\[/?snippet:
   :caption: ``TrailKernel.slang.lua``, from the runnable :doc:`stateful node example <../../examples/python_spg_stateful>`

The Binders
-----------

Each binder is named after the Slang type it binds to, and behaves like it.

.. list-table::
   :header-rows: 1
   :widths: 44 56

   * - Function
     - Binds
   * - ``slang.ParameterBlock(...)``
     - The shader's constant buffer.
   * - ``slang.Texture1D(input)``, ``slang.Texture2D(input)``, ``slang.Texture3D(input)``
     - A resource-input as a read-only texture of that rank.
   * - ``slang.RWTexture1D(output)``, ``slang.RWTexture2D(output)``, ``slang.RWTexture3D(output)``
     - An output as a read/write texture of that rank.
   * - ``slang.StructuredBuffer(input)``, ``slang.ByteAddressBuffer(input)``
     - A read-only storage buffer, addressed by element or by byte offset. The two are the same descriptor and differ only in how the shader addresses it. Takes a resource-input or the result of ``slang.array(...)``.
   * - ``slang.RWStructuredBuffer(output)``, ``slang.RWByteAddressBuffer(output)``
     - A buffer-backed output as a read/write storage buffer, addressed by element or by byte offset.
   * - ``slang.Buffer(input)``
     - A read-only typed buffer, ``Buffer<T>``.
   * - ``slang.RWBuffer(output)``
     - A buffer-backed output as a typed buffer, ``RWBuffer<T>``. This is what creates one.

The binders check what they are given, in Lua, before anything reaches the GPU, and the
message names the port: the **rank** must match the type, the **direction** must match, the
**backing** must match, and for a buffer this node reads, the **kind** must match.

Shader-match failures cannot be caught this way, because the launch script does not see the
shader. Those surface from the node at load time.

Grouping and Data
-----------------

.. list-table::
   :header-rows: 1
   :widths: 44 56

   * - Function
     - Description
   * - ``slang.bind(resources)``, ``slang.bind(resources, space)``
     - Group bound resources into one descriptor set. Slots are positions in the group, counting
       from zero; ``space`` states the descriptor space. Passed in the array part of the
       ``slang.dispatch`` table rather than in ``bind``. Compute stages only: the ray-tracing
       calls read the flat ``bind`` list and reject a group. Refer to
       :doc:`../do/descriptor_sets`.
   * - ``slang.array(luaTable, dtype)``
     - Upload a Lua table of numbers to a GPU buffer. Wrap it in a buffer binder to bind it.
   * - ``slang.array(resource)``
     - Reference a buffer-backed resource that already exists, such as a composite channel.
   * - ``slang.array(assetInput, dtype)``
     - Upload the raw bytes of an ``asset`` value-input, read as ``dtype``.
   * - ``slang.array(tokenInput)``
     - A ``token`` value-input as a null-terminated ``char`` array. No dtype: a token is always
       ``char``.

What a Launch Script Returns
----------------------------

A launch script returns one of three calls, and which one it returns decides the shader stage.

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Function
     - Description
   * - ``slang.dispatch(table)``
     - A compute launch. The fields are below.
   * - ``slang.rayQuery(table)``
     - A ray-generation launch that traces inline, with no shader binding table and so no miss or
       hit entry points. Takes ``bind`` only: there is no ``numthreads``, and the ray grid is the
       output AOV's shape, one invocation per element. Refer to :doc:`../do/raygen`.
   * - ``slang.traceRays(table)``
     - A ray-generation launch that drives a full ray-tracing pipeline with a shader binding
       table, so shading happens in separate entry points. Takes the extra fields below.

``slang.dispatch`` fields
~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Description
   * - ``bind``
     - Ordered list of resource bindings. Required unless the resources are grouped with ``slang.bind`` in the array part instead.
   * - ``numthreads``
     - The group size the shader was compiled with, as ``{ x, y, z }``. SPG divides the output's
       shape by it to get the number of groups. For a shader that carries no reflection, meaning a
       ``.spv``; nothing compares it against the byte code. A shader that declares ``[numthreads]``
       supersedes it, logging the disagreement at INFO level. Refer to
       :doc:`../do/launch_geometry`.
   * - ``grid``
     - Number of thread groups as ``{ x, y, z }``. Optional; derived from the first output's shape
       and the thread-group size when omitted. With a thread-group size from neither the shader nor
       ``numthreads``, there is nothing to derive from and the node does not run.
   * - ``stage``
     - Shader stage. Optional; ``"compute"`` when omitted.

Set ``grid`` explicitly whenever the iteration domain is the data rather than the image. The
derived grid follows the output shape, which is wrong for a shader whose threads each walk a
buffer.

``slang.traceRays`` fields
~~~~~~~~~~~~~~~~~~~~~~~~~~

In addition to ``bind``. The named entry points live in the same source asset as the
ray-generation entry point.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Description
   * - ``miss``
     - Array of miss entry-point names, as strings.
   * - ``hit``
     - Array of hit groups, each a table defining ``closesthit`` and optionally ``anyhit``, both
       entry-point names. **Exactly one hit group is supported**; more is rejected, because the
       dispatch uses a zero-stride hit-group table and every scene hit invokes group 0.
   * - ``payloadSize``
     - Size of the ``TraceRay`` payload in bytes. A whole number from 0 to 65535.
   * - ``attributeSize``
     - Size of the hit attributes in bytes. A whole number from 0 to 65535.

Binding by Name
---------------

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Function
     - Description
   * - ``slang.binding(name, input)``
     - Bind a resource the renderer provides under a known name rather than one the scene
       connected. ``slang.binding("scene", inputs["scene"])`` is how a ray-generation node
       receives the scene acceleration structure.

Cached Computation
------------------

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Function
     - Description
   * - ``slang.static(fn, ...)``
     - Call ``fn(...)`` once and cache the result, keyed on the arguments. Later calls with the
       same arguments reuse it; a changed argument runs ``fn`` again. Refer to
       :doc:`../do/caching`.

Matrix Storage Order
--------------------

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Constant
     - Description
   * - ``slang.row_major``, ``slang.column_major``
     - How a matrix is stored in a parameter block, given as the ``order`` of a stated layout. A
       matrix needs its order as well as its offset. Refer to
       :ref:`Stating the Layout <spg-do-layout>`.

dtype Constants
---------------

Every constant is also callable as a constructor, so ``slang.float(inputs["strength"])`` wraps a
value for a parameter block and ``slang.float3(x, y, z)`` builds one from components.

.. list-table::
   :header-rows: 1
   :widths: 26 20 24 30

   * - Scalar
     - Element
     - Vector forms
     - Notes
   * - ``slang.bool``
     - 8-bit boolean
     - ``slang.bool2``, ``slang.bool3``, ``slang.bool4``
     -
   * - ``slang.char``, ``slang.uchar``
     - 8-bit signed, unsigned
     - ``slang.char2``, ``slang.char3``, ``slang.char4``, ``slang.uchar2``, ``slang.uchar3``,
       ``slang.uchar4``
     - ``uchar4`` is the one normalised texture format. Refer to
       :ref:`a uchar4 texture is normalised <spg-uchar4-unorm>`.
   * - ``slang.short``, ``slang.ushort``
     - 16-bit signed, unsigned
     - ``slang.short2``, ``slang.short3``, ``slang.short4``, ``slang.ushort2``,
       ``slang.ushort3``, ``slang.ushort4``
     -
   * - ``slang.int``, ``slang.uint``
     - 32-bit signed, unsigned
     - ``slang.int2``, ``slang.int3``, ``slang.int4``, ``slang.uint2``, ``slang.uint3``,
       ``slang.uint4``
     -
   * - ``slang.half``
     - 16-bit float
     - ``slang.half2``, ``slang.half3``, ``slang.half4``
     -
   * - ``slang.float``
     - 32-bit float
     - ``slang.float2``, ``slang.float3``, ``slang.float4``
     -
   * - ``slang.double``
     - 64-bit float
     - ``slang.double2``, ``slang.double3``, ``slang.double4``
     -
   * - ``slang.int64``, ``slang.uint64``
     - 64-bit signed, unsigned
     - none
     - Present, but a shader cannot use them: the Vulkan ``shaderInt64`` feature is not enabled.
       Write the node in CUDA when it needs 64-bit integers.

Square matrices are ``slang.float2x2``, ``slang.float3x3``, ``slang.float4x4`` and the ``double``
forms ``slang.double2x2``, ``slang.double3x3``, ``slang.double4x4``. A matrix in a parameter block
needs its storage order as well as its offset; refer to :ref:`Stating the Layout <spg-do-layout>`.

Quaternions are ``slang.quatf``, ``slang.quatd`` and ``slang.quath``, four components of the
matching float width.

The three-component types narrower than 32 bits cannot back a texture. Refer to
:ref:`not every dtype can back a texture <spg-formatless-dtypes>`.

**What this table adds.** Everything ``cuda`` carries is here. This table adds ``char``,
``short`` and ``ushort``, the ``bool``, ``char``, ``short`` and ``ushort`` vectors, ``uchar2`` and
``uchar3``, every matrix type and every quaternion type.
