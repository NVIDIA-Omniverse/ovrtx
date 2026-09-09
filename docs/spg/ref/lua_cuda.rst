.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-ref-cuda:

The ``cuda`` Lua Table
======================

Every function and constant a ``.cu.lua`` launch script can use. For what a launch script is
and when it runs, refer to :doc:`lua_contract`.

Accepted source assets: ``.cu``, compiled with NVRTC on load, and the pre-compiled ``.ptx``,
``.cubin`` and ``.fatbin``. Extensions are matched case-insensitively. That is the complete
list.

The CUDA headers are reachable from a ``.cu`` source through ``#include``, for example
``#include <cuda_fp16.h>``. They come from one directory, the CUDA installation SPG finds:
``CUDA_PATH`` or ``CUDA_HOME`` if either is set in the environment, otherwise the headers bundled
with the renderer. It is the **only** include directory the compile is given, so a header sitting
beside the ``.cu`` does not resolve. Refer to :doc:`../do/precompiled`.

Describing Outputs
------------------

Output descriptors state what an output has to be; SPG owns the memory.

.. list-table::
   :header-rows: 1
   :widths: 44 56

   * - Function
     - Description
   * - ``cuda.image(width, height, dtype)``
     - A texture-backed output. Preferred for image data. Note the argument order against height-first shapes.
   * - ``cuda.empty(shape, dtype)``
     - A buffer-backed output of arbitrary shape, up to 8 dimensions. Use for non-image data.
   * - ``cuda.zeros(shape, dtype)``, ``cuda.ones(shape, dtype)``, ``cuda.full(shape, value, dtype)``
     - A buffer filled with zeros, ones, or a stated value.

``cuda.image`` and ``cuda.empty`` take an optional trailing ``cuda.stateful``, which marks the
output persistent so SPG hands the same resource back next frame instead of a fresh one:

.. filtered-literalinclude:: ../../../examples/python/spg-stateful/TrailKernel.cu.lua
   :language: lua
   :start-after: -- [snippet:trail-alloc]
   :end-before: -- [/snippet:trail-alloc]
   :exclude-pattern: ^\s*--\s*\[/?snippet:
   :caption: ``TrailKernel.cu.lua``, from the runnable :doc:`stateful node example <../../examples/python_spg_stateful>`

The Wrappers
------------

Each wrapper turns a descriptor or a value into the CUDA type the kernel parameter expects.

.. list-table::
   :header-rows: 1
   :widths: 32 26 42

   * - Function
     - Wraps to
     - Description
   * - ``cuda.TextureObject(resource)``
     - ``cudaTextureObject_t``
     - Read-only, hardware-cached texture access to an input or output resource.
   * - ``cuda.SurfaceObject(resource)``
     - ``cudaSurfaceObject_t``
     - Read-write surface access to an output resource.
   * - ``cuda.array(resource)``
     - ``cudaRawPointer_t``
     - Raw device pointer to an input or output resource.
   * - ``cuda.array(luaTable, dtype)``
     - ``cudaRawPointer_t``
     - Upload a Lua table of numbers to a GPU device array.
   * - ``cuda.array(tokenOrAssetInput)``
     - ``cudaRawPointer_t``
     - Upload a ``token`` value-input as a null-terminated ``const char*``, or an ``asset``
       value-input as the file's raw bytes. An ``asset`` takes a dtype as its second argument;
       a ``token`` does not, because it is always ``char``.
   * - ``cuda.int(value)``, ``cuda.float(value)``, ``cuda.bool(value)``, ``cuda.double(value)``, ``cuda.uint(value)``
     - the matching C scalar
     - Scalar kernel argument.

Every dtype constant can be called as a scalar constructor, for example ``cuda.half(1.0)``.
Vector types accept multiple scalar arguments or a single value-input entry, for example
``cuda.float3(x, y, z)`` or ``cuda.int2(inputs["size"])``.

Kernel Launch
-------------

.. code-block:: lua

    return cuda.kernel({
        args  = { --[[ ordered kernel arguments ]] },
        block = { bx, by },
        grid  = { gx, gy },
        sharedMemSize = 0,
    })

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Description
   * - ``args``
     - Ordered kernel arguments, matched against the C signature by position. Required.
   * - ``block``
     - Threads per block, as ``{ x }``, ``{ x, y }`` or ``{ x, y, z }``; components left out are
       1. Optional.
   * - ``grid``
     - Blocks per launch, in the same form. Optional.
   * - ``sharedMemSize``
     - Dynamic shared memory in bytes, the third argument of ``<<<grid, block, shared>>>``.
       Optional; 0 when omitted.

``block`` and ``grid`` map directly to the CUDA launch configuration (``<<<grid, block>>>``).
Left out, they are derived from the first output's shape: a block of 16 x 16 x 1, or 256 x 1 x 1
for a rank-1 or rank-0 resource, and a grid covering that shape. Value-inputs on the shader prim supply them instead when the script
states neither. Set them explicitly whenever the iteration domain is not the output image, such as
a kernel whose threads walk a buffer. Refer to :doc:`../do/launch_geometry`.

dtype Constants
---------------

All dtype constants live in the ``cuda`` table and can also be called as constructors for
kernel arguments, for example ``cuda.int(42)``.

.. list-table::
   :header-rows: 1
   :widths: 34 33 33

   * - Constant
     - C Type
     - Size
   * - ``cuda.bool``
     - bool
     - 1 byte
   * - ``cuda.uchar``
     - uint8
     - 1 byte
   * - ``cuda.uchar4``
     - uchar4
     - 4 bytes
   * - ``cuda.half``, ``cuda.half2``, ``cuda.half3``, ``cuda.half4``
     - __half, half2, half3, half4
     - 2 to 8 bytes
   * - ``cuda.float``, ``cuda.float2``, ``cuda.float3``, ``cuda.float4``
     - float, float2, float3, float4
     - 4 to 16 bytes
   * - ``cuda.int``, ``cuda.int2``, ``cuda.int3``, ``cuda.int4``
     - int32_t, int2, int3, int4
     - 4 to 16 bytes
   * - ``cuda.uint``, ``cuda.uint2``, ``cuda.uint3``, ``cuda.uint4``
     - uint32_t, uint2, uint3, uint4
     - 4 to 16 bytes
   * - ``cuda.double``, ``cuda.double2``, ``cuda.double3``, ``cuda.double4``
     - double, double2, double3, double4
     - 8 to 32 bytes
   * - ``cuda.int64``, ``cuda.uint64``
     - int64_t, uint64_t
     - 8 bytes

Cached Computation
------------------

.. list-table::
   :header-rows: 1
   :widths: 44 56

   * - Function
     - Description
   * - ``cuda.static(fn, ...)``
     - Call ``fn(...)`` once and cache the result, keyed on the arguments. Later calls with the
       same arguments reuse it; a changed argument runs ``fn`` again. Refer to
       :doc:`../do/caching`.
