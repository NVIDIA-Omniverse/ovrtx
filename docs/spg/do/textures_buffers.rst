.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-do-buffers:

Choose a Resource's Backing
===========================

**Goal.** Decide whether a resource is texture-backed or buffer-backed, and bind it with a binder
that agrees.

**Before you start.** :doc:`../ref/lua_contract`.

The Shape
---------

Describe what the output has to be. ``image`` asks for a texture, ``empty`` asks for a buffer.

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      .. code-block:: lua

          outputs["Picture"] = cuda.image(width, height, cuda.uchar4)
          outputs["Values"]  = cuda.empty({ count }, cuda.float)

   .. tab-item:: Slang
      :sync: slang

      .. code-block:: lua

          outputs["Picture"] = slang.image(width, height, slang.uchar4)
          outputs["Values"]  = slang.empty({ count }, slang.float)

How It Works
------------

Five things hold whichever language the node is written in.

**Backing is fixed at creation.** A resource is either texture-backed or buffer-backed, and that
choice cannot be revisited. Describe it as what it needs to be, and bind it with a binder that
agrees.

**Shapes are height-first.** ``shape[1]`` is height and ``shape[2]`` is width, while the ``image``
functions take width first. That reversal is the most common cause of a wrongly proportioned
result.

**A texture has one, two or three dimensions.** Anything else is buffer-backed.

.. _spg-formatless-dtypes:

**Not every dtype can back a texture.** A texture element needs a hardware format, and the
three-component types narrower than 32 bits have none: ``half3``, ``short3``, ``ushort3``,
``char3`` and ``uchar3``. Asking for one is refused where it is asked for. Use the four-component
form and leave the fourth channel unread, or make the resource buffer-backed, where any dtype
goes.

.. _spg-uchar4-unorm:

**Normalisation is where the two languages differ.** A ``uchar4`` texture's hardware format is
``RGBA8_UNORM``, alone among the 8-bit element types, so the hardware maps its bytes to
and from the range 0.0 to 1.0 on every access. A Slang shader writes ``float4`` values in that
range and the hardware rounds them to bytes; a CUDA kernel writes the bytes itself through
``surf2Dwrite`` and nothing rounds. The same intended colour can therefore land one least
significant bit apart in the two languages. Where a test has to match byte for byte, pick colours
that are exact in 8 bits.

The names, and what the GPU code receives, depend on the language.

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      **Allocate** with ``cuda.image(width, height, dtype)`` for a texture and
      ``cuda.empty(shape, dtype)`` for a buffer. To create one from data you wrote in Lua, use
      ``cuda.array(luaTable, dtype)``; refer to :doc:`upload_data`.

      **Bind** with ``cuda.TextureObject(r)`` to read a texture, ``cuda.SurfaceObject(r)`` to
      write one, and ``cuda.array(r)`` for a buffer. The full set is in :doc:`../ref/lua_cuda`.

      **A buffer arrives as a pointer.** Nothing constrains how the kernel reads it: element
      size, stride and interpretation are yours. A texture instead arrives as a
      ``cudaTextureObject_t`` or ``cudaSurfaceObject_t``, and the hardware handles addressing and
      format conversion.

      The grayscale node works on textures throughout. Highlighted: the allocation, then the two
      binders.

      .. literalinclude:: ../../../examples/python/spg-grayscale/GrayscaleKernel.cu.lua
         :language: lua
         :start-after: -- [snippet:grayscale-launch-template]
         :end-before: -- [/snippet:grayscale-launch-template]
         :emphasize-lines: 12, 19-20
         :caption: ``GrayscaleKernel.cu.lua``, from the runnable :doc:`grayscale example <../../examples/python_spg_grayscale>`

      A node routinely mixes the two. Here a texture output is allocated and two buffer inputs are
      bound alongside it, in one list. ``coordinates`` and ``counts`` are buffer-backed resources
      this node was given; where they came from is :doc:`composites`.

      .. literalinclude:: ../../../examples/python/spg-composite-aov/RangeHistogramKernel.cu.lua
         :language: lua
         :start-after: -- [snippet:histogram-binding]
         :end-before: -- [/snippet:histogram-binding]
         :dedent: 4
         :emphasize-lines: 11-13
         :caption: ``RangeHistogramKernel.cu.lua``, from the runnable :doc:`composite AOV example <../../examples/python_spg_composite_aov>`

   .. tab-item:: Slang
      :sync: slang

      **Allocate** with ``slang.image(width, height, dtype)`` for a texture and
      ``slang.empty(shape, dtype)`` for a buffer. To create one from data you wrote in Lua, use
      ``slang.array(luaTable, dtype)``; refer to :doc:`upload_data`.

      **Bind** with ``slang.Texture2D(r)`` to read a texture, ``slang.RWTexture2D(r)`` to write
      one, and ``slang.StructuredBuffer(r)`` for a buffer. Slang names its binders after the types
      they bind and checks what it is given, so the binder has to match how the shader declares
      the parameter. The full set is in :doc:`../ref/lua_slang`.

      ``slang.StructuredBuffer`` **is one point in a small space**, not a name to memorise. It is
      read-only, storage-backed and addressed by element, and each of those three has an
      alternative. Storage or typed decides whether the shader interprets the bytes itself or the
      hardware converts on access, and that one is fixed when the buffer is created. Read-only or
      read/write is the ``RW`` prefix, and follows from whether the resource is an input or an
      output. By element or by byte offset costs nothing to change, because both are the same
      descriptor and only the shader's addressing differs.

      **Typed and storage buffers are different resources.** The binder that declares an output is
      what describes it, so ``slang.RWBuffer`` is what asks for a typed buffer, taking its element
      format from the output's dtype. Every node that reads that buffer must then read it with
      ``slang.Buffer``. A buffer created any other way must be read with
      ``slang.StructuredBuffer`` or ``slang.ByteAddressBuffer``. Reading one as the kind it was not
      created as is rejected by name, in both directions, with the fix in the message.

      Two allocations are refused where they are asked for: an element type that names no format,
      and an element count past the device's typed-buffer limit.

      The grayscale node works on textures throughout. Highlighted: the allocation, then the two
      binders.

      .. literalinclude:: ../../../examples/python/spg-grayscale/GrayscaleKernel.slang.lua
         :language: lua
         :start-after: -- [snippet:grayscale-slang-launch-template]
         :end-before: -- [/snippet:grayscale-slang-launch-template]
         :emphasize-lines: 11, 16-17
         :caption: ``GrayscaleKernel.slang.lua``, from the runnable :doc:`grayscale example <../../examples/python_spg_grayscale>`

      A node routinely mixes the two. Here a texture output is allocated and two buffer inputs are
      bound alongside it, in one list. ``coordinates`` and ``counts`` are buffer-backed resources
      this node was given; where they came from is :doc:`composites`.

      .. literalinclude:: ../../../examples/python/spg-composite-aov/RangeHistogramKernel.slang.lua
         :language: lua
         :start-after: -- [snippet:histogram-slang-binding]
         :end-before: -- [/snippet:histogram-slang-binding]
         :dedent: 4
         :emphasize-lines: 11-13
         :caption: ``RangeHistogramKernel.slang.lua``, from the runnable :doc:`composite AOV example <../../examples/python_spg_composite_aov>`

Verify It Worked
----------------

Write a known pattern into the resource and read it back on the host. A round trip that survives
exactly proves both the backing and the binder. A result that looks plausible but shifted usually
means the stride or the shape order is wrong, not the binding.

When It Goes Wrong
------------------

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      - The values are shifted or interleaved wrongly: the kernel's element size or stride does
        not match how the buffer was allocated. Nothing checks this for you.
      - Wrong pixels rather than none: refer to
        :ref:`Wrong Pixels Rather Than No Pixels <spg-symptom-wrong-pixels>`.

   .. tab-item:: Slang
      :sync: slang

      - A binder rejects the resource: the message names the port and what it expected. That is a
        Lua-side check, so it fires before anything reaches the GPU.
      - A buffer is rejected as the wrong kind: it was created typed and read as storage, or the
        reverse. The message says which, and the fix is to match the creating binder.
      - Wrong pixels rather than none: refer to
        :ref:`Wrong Pixels Rather Than No Pixels <spg-symptom-wrong-pixels>`.

Related
-------

:doc:`upload_data`, :doc:`composites`, :doc:`launch_geometry`, :doc:`../ref/lua_cuda`, :doc:`../ref/lua_slang`
