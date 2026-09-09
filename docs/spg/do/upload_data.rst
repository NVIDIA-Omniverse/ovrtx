.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-do-upload:

Upload Your Own Data
====================

**Goal.** Get a lookup table, a filter kernel or any authored array onto the GPU, either built in
Lua or read from a file.

**Before you start.** :doc:`textures_buffers`.

The Shape
---------

Build the data in Lua and hand it to ``array`` with a dtype:

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      .. code-block:: lua

          local keys = cuda.array({ 0xA5, 0x5A, 0x12, 0x34 }, cuda.uint)

   .. tab-item:: Slang
      :sync: slang

      .. code-block:: lua

          local keys = slang.array({ 0xA5, 0x5A, 0x12, 0x34 }, slang.uint)

Then bind ``keys`` in the launch configuration like any other buffer.

How It Works
------------

``array`` **takes the data from wherever you have it.** Given a Lua table and a dtype it creates a
device buffer holding that data. Given a resource descriptor it binds a buffer that already exists,
which is what :doc:`composites` does with a sensor's channels. Given an ``asset`` input and a dtype
it creates a device buffer from that file's bytes, which is the next section. Both forms are on ``cuda`` and on ``slang``.

``ones`` **and** ``zeros`` **take a shape and a dtype** and create a filled buffer with no Lua data to
build.

**Build the table once.** Wrap the call in ``static``, or it is rebuilt on every frame,
because the launch script runs on every frame, and a launch script has an instruction budget. The
upload itself is redone each frame either way. Refer to :doc:`caching`.

From a File
~~~~~~~~~~~

Data too large to write out in Lua comes from a file instead. Declare an ``asset``
:doc:`value-input <values>` on the shader definition and point it at the file:

.. code-block:: usda

    # A raw binary lookup table: 256 little-endian uint32 entries.
    uniform asset inputs:lut = @LutInvert.bin@

The launch script reads it with the same ``array`` call, giving the dtype the file's bytes should be
read as. SPG resolves the path and uploads the contents:

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      .. code-block:: lua

          cuda.array(inputs["lut"], cuda.uint)   -- -> const unsigned int* lut

   .. tab-item:: Slang
      :sync: slang

      .. code-block:: lua

          slang.StructuredBuffer(slang.array(inputs["lut"], slang.uint))
          -- -> StructuredBuffer<uint> g_Lut

On CUDA the call is complete on its own. On Slang a binder still has to wrap it, because Slang
binds by declared type.

Which Slang binder you reach for is three independent choices, not a list to memorise.
``StructuredBuffer`` is read-only, storage-backed, addressed by element, and each of those three
has an alternative. Storage or typed decides whether the shader interprets the bytes itself or the
hardware converts on access, and that one is fixed when the buffer is created. Read-only or
read/write is the ``RW`` prefix. By element or by byte offset is the only one that costs nothing to
change, because both are the same descriptor and differ only in how the shader addresses it. The
exact names are in :doc:`../ref/lua_slang`.

The file is read as raw bytes. Nothing parses a format or converts between types, so the dtype has
to match how the file was written, and the shader indexes the result like any other buffer.

**The file need not be a local one.** An ``asset`` value-input is resolved exactly as the GPU
source is, so a lookup table may sit beside the scene, inside a ``.usdz`` package, or behind a
URI the Omniverse client can reach. Refer to :ref:`Where Assets May Live <spg-asset-locations>`.

Verify It Worked
----------------

Upload data whose effect is exact and reversible, then reproduce it on the host. A per-channel
XOR key is the usual choice: ``out[..., c]`` must equal ``in[..., c] ^ K[c]`` for every pixel and
every channel. Approximate data, a blur kernel say, hides an off-by-one in the upload because the
result still looks right.

When It Goes Wrong
------------------

- The values are wrong but structured: the dtype does not match what the GPU code reads, or, for a
  file, does not match how the file was written.
- The data is right on the first frame only, or is rebuilt every frame: refer to :doc:`caching`.
- The script is stopped part way through: building the table exceeded the launch script's
  instruction budget. Wrap it in ``static`` so it runs once, or move the work into the GPU code.

Related
-------

:doc:`textures_buffers`, :doc:`values`, :doc:`caching`, :doc:`../ref/lua_cuda`,
:doc:`../ref/lua_slang`, :doc:`../../examples/python_spg_blur`
