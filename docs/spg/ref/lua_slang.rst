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
IR, and ``.spv``, SPIR-V and compute only. Extensions are matched case-insensitively.

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

The same functions describe the node's **memory**: storage only the node reads and writes,
kept across frames for as long as the node lives. A memory is stated on ``self.memory`` under
its name instead of on ``outputs``, and passed to the kernel with the same wrappers as an
output, as in the snippet below. Refer to
:doc:`../do/state`.

``slang.image`` and ``slang.empty`` also take an optional trailing ``slang.stateful``, which marks
an output persistent so SPG hands the same resource back next frame instead of a fresh one:
state the scene reads as well.

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
     - A buffer-backed output, created as a typed buffer, ``RWBuffer<T>``. Only a buffer created this way can be read with ``slang.Buffer``.

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
       ``slang.compute`` table rather than in ``bind``. Compute stages only: the ray-tracing
       calls read the flat ``bind`` list and reject a group. Refer to
       :doc:`../do/descriptor_sets`.
   * - ``slang.array(luaTable, dtype)``
     - Upload a Lua table of numbers to a GPU buffer. Wrap it in a buffer binder to bind it. An empty table binds a placeholder the shader must not read.
   * - ``slang.zeros(shape, dtype)``, ``slang.ones(shape, dtype)``, ``slang.full(shape, value, dtype)``
     - A GPU buffer of that shape filled with zeros, ones, or a stated value. Wrap it in a buffer binder to bind it, as the result of ``slang.array`` is.
   * - ``slang.array(value, dtype, { offset, strides })``
     - An array inside a parameter block, ``offset`` bytes into it, with ``strides`` giving the
       bytes from one index to the next at each level, padding included. A shader without
       reflection needs both; where the shader reports them, it uses its own and warns when stated
       ones differ. An empty array writes nothing; its bytes stay zero. Refer to
       :ref:`Stating the Layout <spg-do-layout>`.
   * - ``slang.array(resource)``
     - Reference a buffer-backed resource that already exists, such as a composite channel.
   * - ``slang.array(assetInput, dtype)``
     - Upload the raw bytes of an ``asset`` value-input, read as ``dtype``.
   * - ``slang.array(tokenInput)``
     - A ``token`` value-input as a null-terminated ``char`` array. No dtype: a token is always
       ``char``.

What a Launch Script Returns
----------------------------

A launch script returns one of the calls below, and the call it returns decides the shader stage.

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Function
     - Description
   * - ``slang.compute(table)``
     - A compute launch. The fields are below.
   * - ``slang.dispatch(table)``
     - Deprecated: the same call as ``slang.compute``, under a second name. It takes the same
       fields and returns the same launch, and logs a warning once per node. Call
       ``slang.compute`` instead.
   * - ``slang.rayQuery(table)``
     - A ray-generation launch that traces inline, with no shader binding table and so no miss or
       hit entry points. Takes ``bind`` only: there is no ``numthreads``, and the ray grid is the
       output AOV's shape, one invocation per element. Refer to :doc:`../do/raygen`.
   * - ``slang.traceRays(table)``
     - A ray-generation launch that drives a full ray-tracing pipeline with a shader binding
       table, so shading happens in separate entry points. Takes the extra fields below.

``slang.compute`` fields
~~~~~~~~~~~~~~~~~~~~~~~~

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
       ``numthreads``, there is nothing to derive from and the node's graph stops.

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
       entry-point names. **Exactly one hit group is supported**; more is rejected.
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
     - Call ``fn(...)`` once and cache the result. Later calls with the same arguments reuse it; a
       changed argument runs ``fn`` again, and its result replaces the cached one. An error from
       ``fn`` propagates and fails the launch; the failed call stores no result. A function
       written inline in the launch function is the same function on every launch. Refer to
       :doc:`../do/caching`.

Matrix Storage Order
--------------------

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Constant
     - Description
   * - ``slang.row_major``, ``slang.column_major``
     - Deprecated: the ``order`` of a matrix layout stated as ``{ offset, order, stride }``, which
       logs a warning. State ``strides`` instead. Refer to
       :ref:`Stating the Layout <spg-do-layout>`.

dtype Constants
---------------

Every constant is also callable as a constructor, so ``slang.float(inputs["strength"])`` wraps a
value for a parameter block and ``slang.float3(x, y, z)`` builds one from components. A
constructor holds one value of its type: given an input that holds more elements, it fails the
launch, and the array goes in with ``slang.array`` instead.

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
     - In a parameter block each component is packed as a four-byte shader ``bool``.
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
forms ``slang.double2x2``, ``slang.double3x3``, ``slang.double4x4``. A matrix in the parameter block
of a shader without reflection needs its offset and strides; refer to
:ref:`Stating the Layout <spg-do-layout>`.

Quaternions are ``slang.quatf``, ``slang.quatd`` and ``slang.quath``, four components of the
matching float width.

The three-component types narrower than 32 bits cannot back a texture. Refer to
:ref:`not every dtype can back a texture <spg-formatless-dtypes>`.

**What this table adds.** Everything ``cuda`` carries is here. This table adds ``char``,
``short`` and ``ushort``, the ``bool``, ``char``, ``short`` and ``ushort`` vectors, ``uchar2`` and
``uchar3``, every matrix type and every quaternion type.
