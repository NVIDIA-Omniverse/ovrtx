.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-lua-script:

The Lua Launch Script
=====================

Everything a launch script may contain. For what a node is made of, refer to
:doc:`../overview`.

SPG finds the script by appending ``.lua`` to the ``info:spg:sourceAsset`` path, so
``GrayscaleKernel.cu`` is paired with ``GrayscaleKernel.cu.lua``. The pairing is by file name and
cannot be redirected.

What follows is identical whichever language the GPU source is written in. For the parts that
differ, refer to :doc:`lua_cuda` and :doc:`lua_slang`.

A Complete Script
-----------------

A complete script. It validates the input it was handed, takes the shape from it, describes the
output, and returns the launch configuration.

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      .. literalinclude:: ../../../examples/python/spg-grayscale/GrayscaleKernel.cu.lua
         :language: lua
         :start-after: -- [snippet:grayscale-launch-template]
         :end-before: -- [/snippet:grayscale-launch-template]
         :emphasize-lines: 3, 12, 14
         :caption: ``GrayscaleKernel.cu.lua``, from the runnable :doc:`grayscale example <../../examples/python_spg_grayscale>`

   .. tab-item:: Slang
      :sync: slang

      .. literalinclude:: ../../../examples/python/spg-grayscale/GrayscaleKernel.slang.lua
         :language: lua
         :start-after: -- [snippet:grayscale-slang-launch-template]
         :end-before: -- [/snippet:grayscale-slang-launch-template]
         :emphasize-lines: 7, 11, 13
         :caption: ``GrayscaleKernel.slang.lua``, from the runnable :doc:`grayscale example <../../examples/python_spg_grayscale>`

Highlighted: the function, whose name has to match the entry point; the line that describes the
output; and the return that carries the launch configuration. Those three are the contract.

What the Script Is Handed
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 46 54

   * - It has
     - It does not have
   * - Descriptors for every bound resource: shape, dtype and rank
     - The contents of those resources. No pixel, point or buffer value is readable here.
   * - The value-inputs authored in USD
     - Anything a previous frame computed, unless it was written to a stateful output
   * - The current frame number
     - Any result of this frame's GPU work, which has not run yet

The practical consequence catches people out: a launch script cannot branch on data. A lidar's
``Counts`` channel, for example, says how many returns a sweep produced, but the script sees
only its descriptor. The count is passed to the GPU and the bound is applied there.

Function Signature
------------------

The script defines one global function. Its name must match both the entry point in the GPU
source and ``info:spg:sourceAsset:subIdentifier`` in the USD shader definition. It receives
two tables:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Parameter
     - Contents
   * - ``inputs``
     - Unified map of all shader inputs. Contains both **resource-inputs** (from ``opaque`` USD attributes) and **value-inputs** (from typed USD attributes such as ``float``, ``int``, ``bool``). Keyed by the attribute name with the ``inputs:`` scope stripped, so USD ``inputs:LdrColor`` becomes ``inputs["LdrColor"]`` and USD ``float inputs:strength`` becomes ``inputs["strength"]``.
   * - ``outputs``
     - Map you populate with output descriptors. Keyed the same way, so USD ``outputs:LdrGrayscale`` becomes ``outputs["LdrGrayscale"]``.

The function returns the launch configuration produced by ``cuda.kernel(...)`` or by one of the
``slang`` launch calls.

An older three-argument form, ``f(inputs, outputs, params)``, is still accepted, with ``params``
holding the value-inputs alone. It pairs with the ``params:X`` USD spelling described in
:doc:`usd`. Both are kept so existing nodes load; write the two-argument form, where ``inputs``
already carries the value-inputs.

Resource-Inputs and Value-Inputs
--------------------------------

Both kinds of port arrive in the same ``inputs`` table, and they are told apart by their
fields. Which port is which is settled in USD, as described in
:ref:`Nodes and Ports <spg-nodes-and-ports>`.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Kind
     - Fields
   * - Resource-input
     - ``.shape`` (Lua table), ``.dtype``, ``.rank``
   * - Value-input
     - ``.value``, the raw Lua value

Test ``inputs["X"].value ~= nil`` to distinguish them. A value-input is a wrapper rather than
a number, so it cannot be used in arithmetic directly. Refer to :doc:`../do/values`.

.. _spg-shapes-and-types:

Shapes and Types
----------------

A resource is described by three things, and every function that creates or inspects one is
written in terms of them.

.. list-table::
   :header-rows: 1
   :widths: 16 84

   * - Term
     - What it is
   * - ``shape``
     - A Lua table of the resource's dimensions, one entry per dimension.
   * - ``rank``
     - How many dimensions it has, which is how many entries ``shape`` holds.
   * - ``dtype``
     - What one element is. A dtype is a value rather than a name: ``cuda.uchar4`` and
       ``slang.float`` are dtypes, taken from the ``cuda`` and ``slang`` tables and handed to
       the functions that create resources.

**A dtype says three things about an element**: what kind of number it holds, how wide that
number is, and how many of them make one element. ``cuda.uchar4`` is four unsigned 8-bit
numbers, so one RGBA pixel; ``cuda.float`` is a single 32-bit float. That is why an image and
a plain run of numbers are described in the same vocabulary.

**A dtype compares, and it is callable.** Comparing is how a script checks what it was handed,
``inputs["Image"].dtype == cuda.uchar4``. Calling one wraps a value for the GPU,
``cuda.int(42)``. Neither is something a plain type name could do, and both are used
throughout the launch scripts in the examples.

**Shapes are height-first**: ``shape[1]`` is height and ``shape[2]`` is width. Functions that
take explicit dimensions, such as ``cuda.image(width, height, dtype)``, take them in the
opposite order, which is the single most common source of an image that comes out transposed.

A resource is also either texture-backed or buffer-backed, and that choice is fixed when it
is created. Which one an output should be is stated when it is described, and the binder used
for it has to agree.

Describing Outputs
------------------

Every output declared in the USD shader definition must be assigned a descriptor in
``outputs`` before the script returns. A descriptor states what the output has to be, its
shape and dtype, and is not the memory itself. An output left undescribed is never backed,
so the node has nothing to write into.

Which function describes it depends on how the output is backed. Refer to
:doc:`../do/textures_buffers`.

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      ``cuda.image`` takes width and height, in that order:

      .. code-block:: lua

          outputs["LdrGrayscale"] = cuda.image(width, height, cuda.uchar4)

      A shape is height-first while width and height are not, so the two orders are reversed.

   .. tab-item:: Slang
      :sync: slang

      ``slang.image`` takes width and height, or a shape table, which is how a texture of one or
      three dimensions is asked for:

      .. code-block:: lua

          outputs["LdrGrayscale"] = slang.image(inputs["LdrColor"].shape, inputs["LdrColor"].dtype)

The available descriptor functions, and their exact signatures, are listed in :doc:`lua_cuda`
and :doc:`lua_slang`.

Global Variables
----------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Variable
     - Description
   * - ``rtx.frameId``
     - The current rendered frame, counted by the renderer. The same in either language. One host
       ``step`` can render several frames, so this advances faster than the calls that drive it.

Logging Functions
-----------------

A launch script can write to the renderer log, visible in the console and in the renderer's log
file.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Function
     - Description
   * - ``info(msg)``
     - Log a message at INFO level.
   * - ``warning(msg)``
     - Log a message at WARNING level.
   * - ``print(...)``
     - Log arguments at VERBOSE level.
   * - ``assert(cond, msg)``
     - Assert a condition; logs an error on failure.

**Only warnings are visible by default.** At the renderer's default log level ``info`` and ``print``
are not printed, so a script that reports through them looks silent whether it ran or not. Raise
the log level, or use ``warning`` while you are debugging.

**The script runs once per rendered frame**, not once per host ``step``. A single step can render
several frames while the image converges, so anything logged unconditionally arrives many times
over. ``rtx.frameId`` counts those rendered frames.

Sandbox
-------

Launch scripts run in a restricted Lua 5.4 interpreter. Only the ``base``, ``math``,
``string`` and ``table`` libraries are available. File, OS, module and coroutine access are
removed, and each script is bounded in both memory and instruction count. Keep the script to
validation, output descriptions and building the launch table; the work belongs in the GPU
source.

Before a script runs, its source is scanned for forbidden constructs. The scan is a plain
substring match over the whole file, **including comments and identifiers**, so a comment
mentioning one of them is enough to have the script rejected. A rejected script produces no
GPU work, which surfaces as an output AOV that never gets written.

Editor Support
--------------

ovrtx ships a ``.luarc/`` folder, under ``docs/spg/.luarc/``, with type stubs for the Lua
Language Server declaring the globals SPG injects at runtime (``cuda``, ``slang``, ``rtx``,
``info``, ``warning``). Any editor with a Lua Language Server integration can use them for
completions, hover hints and diagnostics when authoring launch scripts.

To enable it for your own project:

1. Configure your editor with a Lua Language Server.
2. At the **root of your workspace**, the folder you open in the editor, create a
   ``.luarc.json`` file with the following contents:

.. code-block:: json

    {
      "Lua.runtime.version": "Lua 5.4",
      "Lua.workspace.library": [
        "<path-to-spg-luarc>"
      ],
      "Lua.workspace.checkThirdParty": false,
      "Lua.diagnostics.globals": ["cuda", "slang", "rtx", "info", "warning"],
      "Lua.diagnostics.disable": ["lowercase-global"]
    }

Fill in the placeholder as follows:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Placeholder
     - What to use
   * - ``<path-to-spg-luarc>``
     - Absolute path to the SPG ``.luarc`` folder shipped with ovrtx, the ``docs/spg/.luarc`` directory.

``Lua.runtime.version`` is ``"Lua 5.4"`` because that is the version of the SPG Lua runtime.

Once the file is saved, the language server resolves ``cuda.kernel(...)`` and
``slang.dispatch(...)``, recognizes the SPG globals, and stops flagging them as undefined. If
completions do not appear, restart the Lua Language Server so it picks up the new
configuration.
