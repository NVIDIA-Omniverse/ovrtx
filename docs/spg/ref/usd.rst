.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-ref-usd:

What You Can Author in USD
==========================

Everything SPG reads from a scene. Attributes not listed here are not read by SPG.

.. _spg-nodes-and-ports:

Ports
-----

A node is one unit of GPU work with named ports. Ports are declared in the USD shader
definition and come in three kinds.

.. list-table::
   :header-rows: 1
   :widths: 26 26 48

   * - Kind
     - Declared as
     - Carries
   * - Resource-input
     - ``opaque inputs:X``
     - An AOV or a buffer another node produced. ``opaque`` because the type is settled at runtime.
   * - Value-input
     - a typed attribute, such as ``float inputs:strength``
     - A number, vector, matrix or token authored in USD.
   * - Resource-output
     - ``opaque outputs:Y``
     - What this node writes.

The port name is the contract. It is what the scene connects to, and what the launch script
keys on. Nothing is matched by position at this level; position only matters inside a launch
script, where the GPU code's parameters or declarations are matched in order.

The Shader Prim
---------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Attribute
     - Meaning
   * - ``uniform token info:implementationSource``
     - ``"sourceAsset"`` for a node you wrote, ``"id"`` for a built-in.
   * - ``uniform asset info:spg:sourceAsset``
     - The GPU source. The extension selects the language. May be a path, a file inside a package, or a URI; refer to :ref:`Where Assets May Live <spg-asset-locations>`.
   * - ``uniform token info:spg:sourceAsset:subIdentifier``
     - The entry point to invoke. Must match the GPU source and the Lua function name. Optional:
       without it the prim's own name is used, so a prim named ``GrayscaleKernel`` looks for an
       entry point called ``GrayscaleKernel``.
   * - ``uniform token info:id``
     - The built-in node, as ``spg:<node-id>``. Refer to :doc:`builtin_catalogue`.
   * - ``opaque inputs:<name>``
     - A resource-input: an AOV, a buffer, or a sensor composite.
   * - ``opaque outputs:<name>``
     - A resource-output the node writes.
   * - a typed attribute, such as ``float inputs:strength``
     - A value-input. The types are below.

The launch script is not authored. It is found by appending ``.lua`` to
``info:spg:sourceAsset``, so the pairing is by file name and cannot be redirected.

Shader prims must not be nested under a ``Material`` prim, and a shader under an instance
prototype is ignored.

``params:X`` is accepted in place of ``inputs:X`` and maps to it. It is the older spelling, kept so
existing scenes load; author ``inputs:``. Where a scene has both, ``inputs:`` wins, and ``inputs:X``
is the only name that can be written at runtime either way. Refer to :doc:`../do/runtime_changes`.

.. _spg-value-input-types:

Value-Input Types
-----------------

A value-input is any attribute under ``inputs:`` that is not ``opaque``. Its USD type decides what
the launch script is handed and what the GPU code has to declare.

.. list-table::
   :header-rows: 1
   :widths: 30 26 44

   * - USD type
     - Arrives as
     - Notes
   * - ``bool``
     - ``bool``
     -
   * - ``int``, ``uint``, ``int64``, ``uint64``
     - the matching integer
     - The 64-bit forms bind on CUDA and not on Slang. Refer to :doc:`lua_slang`.
   * - ``half``, ``float``, ``double``
     - the matching float
     -
   * - ``int2``, ``int3``, ``int4``
     - ``int2``, ``int3``, ``int4``
     -
   * - ``half2/3/4``, ``float2/3/4``, ``double2/3/4``
     - the matching vector
     -
   * - ``matrix2d``, ``matrix3d``, ``matrix4d``
     - ``float2x2``, ``float3x3``, ``float4x4``, or the ``double`` forms
     - USD has no float matrix type, so a shader's ``float4x4`` is authored as ``matrix4d``.
   * - ``quatf``, ``quatd``
     - ``quatf``, ``quatd``
     - Four components. **The text order is not the memory order**: USDA writes ``(w, x, y, z)``
       and the GPU receives ``(x, y, z, w)``, because that is USD's own layout. The identity
       quaternion is authored ``(1, 0, 0, 0)`` and arrives as ``(0, 0, 0, 1)``.
   * - ``token``
     - a null-terminated ``char`` array
     - Bound with ``cuda.array(inputs["x"])`` or ``slang.array(inputs["x"])``.
   * - ``asset``
     - the file's raw bytes, read as the dtype you name
     - SPG resolves the path and uploads the contents. It may be a path, a file inside a package, or a URI; refer to :ref:`Where Assets May Live <spg-asset-locations>` and :doc:`../do/upload_data`.
   * - an array, such as ``float[]``
     - a buffer
     - Read on Slang as a ``StructuredBuffer<T>``.

Types that share a base type behave alike, so ``color3f``, ``point3f``, ``normal3f`` and
``texCoord3f`` all arrive as a three-component float, exactly as ``float3`` does. A type whose base
type is none of the above is not read, and the log says so by name.

.. _spg-asset-locations:

Where Assets May Live
---------------------

Two things a shader prim can name are files: ``info:spg:sourceAsset``, the GPU source, and any
``asset`` value-input, which is data to upload. Both are resolved the same way, and either may
come from any of three places.

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Written as
     - Reads from
   * - ``@Kernel.cu@``
     - A path, resolved relative to the file that names it.
   * - ``@pkg.usdz[Kernel.cu]@``
     - A file inside a USD package, alongside the scene that references it.
   * - ``@file:///path/Kernel.cu@``
     - A URI. ``file://`` resolves, and so does any other scheme the Omniverse client is
       configured to reach, ``omniverse://`` and ``http(s)://`` among them.

**The launch script follows its source.** It is found by appending ``.lua`` to whatever
``info:spg:sourceAsset`` says, so a kernel loaded from a server takes its script from that same
server. Inside a package the suffix goes within the brackets, so ``pkg.usdz[Kernel.cu]`` pairs
with ``pkg.usdz[Kernel.cu.lua]``.

**A data file is read as raw bytes wherever it came from.** Nothing parses a format, so the
location changes nothing about how the launch script reads it. Refer to :doc:`../do/upload_data`.

The RenderVar Prim
------------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Attribute
     - Meaning
   * - ``uniform string sourceName``
     - The AOV name. Required, both to publish a new AOV and to name an existing one.
   * - ``opaque omni:rtx:aov``
     - Exposes a renderer AOV as connectable, for a node to read.
   * - ``opaque omni:rtx:aov.connect``
     - Connects a node output to this RenderVar, publishing it.
   * - ``token[] channels``
     - For a sensor composite, which channels it carries. Refer to :doc:`../do/composites`.

The RenderProduct Prim
----------------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Attribute
     - Meaning
   * - ``rel camera``
     - The camera, or the sensor, this product renders from.
   * - ``rel orderedVars``
     - Which RenderVars the product produces. Every RenderVar a graph consumes or publishes belongs here; intermediates do not.
   * - ``uniform int2 resolution``
     - The product's resolution.

Connections
-----------

The pattern a graph is wired with, in order:

.. code-block:: text

    RenderVar.omni:rtx:aov  ->  Shader.inputs:X
    Shader.outputs:Y        ->  Shader.inputs:Z        (chaining, stays internal)
    Shader.outputs:Y        ->  RenderVar.omni:rtx:aov.connect   (publishing)

A shader-to-shader connection groups both prims into one graph. A node output can be bound to
one RenderVar at a time.
