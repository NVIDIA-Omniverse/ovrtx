.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-do-descriptor-sets:

Bind Resources and Descriptor Spaces
====================================

*Slang only.*

**Goal.** Place resources into specific descriptor sets, and state a constant buffer's layout
yourself rather than leaving it to reflection.

Reflection here means the binding layout SPG reads back out of a compiled Slang shader: which
space and slot each resource sits in, and where each value sits in the constant buffer.

**Before you start.** :doc:`values`, and a Slang node that runs.

The Shape
---------

Every resource needs two things settled: which descriptor set it belongs to, the **space**, and
which **slot** it occupies within that set. A flat ``bind = { ... }`` states neither and relies
on reflection for both. Grouping states them from the script:

.. code-block:: lua

    return slang.dispatch({
        slang.bind({
            slang.ParameterBlock(
                slang.float(inputs["strength"])   -- -> slot 0, the constant buffer
            ),
            slang.Texture2D(inputs["Image"]),     -- -> slot 1
            slang.RWTexture2D(outputs["Result"]), -- -> slot 2
        }, 1),

        slang.bind({
            slang.StructuredBuffer(weights),      -- -> space 2, slot 0
        }, 2),

        numthreads = { 8, 8, 1 },
        grid       = { math.ceil(width / 8), math.ceil(height / 8), 1 },
    })

**Each entry's slot is its position in the group, counting from zero.**

How It Works
------------

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Form
     - What it states
   * - ``bind = { ... }``
     - Neither space nor slot. Both come from reflection, matched shader-global per descriptor kind.
   * - ``slang.bind({...})``, no space
     - Slots, but not the space. The space comes from reflection; if the shader uses more than one, the load fails naming the spaces it found.
   * - ``slang.bind({...}, N)``
     - Both. Space ``N``, slots by position. Respected unconditionally.

Two or more groups must each state a space. There is no positional default and no ordering
assumption, so groups may be listed in any order. Grouping also scopes the matching: within a
group, resources are matched against the reflected resources of that space alone.

Lua rejects two ``ParameterBlock`` s in one group, a duplicate space across groups, and a space
that is negative or not an integer.

The With-Reflection Case
~~~~~~~~~~~~~~~~~~~~~~~~

Every Slang example takes the first form. The shader states the space and the slot for each
resource, and the launch script states neither: its ``bind`` list is purely positional and is
matched against what reflection found.

.. literalinclude:: ../../../examples/python/spg-pipeline/InvertKernel.slang
   :language: hlsl
   :start-after: // [snippet:invert-slang-kernel]
   :end-before: // [/snippet:invert-slang-kernel]
   :emphasize-lines: 9-12, 14-16
   :caption: ``InvertKernel.slang``, from the runnable :doc:`pipeline example <../../examples/python_spg_pipeline>`

.. literalinclude:: ../../../examples/python/spg-pipeline/InvertKernel.slang.lua
   :language: lua
   :start-after: -- [snippet:invert-slang-launch]
   :end-before: -- [/snippet:invert-slang-launch]
   :emphasize-lines: 12-18
   :caption: ``InvertKernel.slang.lua``, from the runnable :doc:`pipeline example <../../examples/python_spg_pipeline>`

The highlighted blocks are one contract seen from both ends. The ``Params`` struct fixes the
field order the ``ParameterBlock`` call has to follow, and the ``vk::binding`` declarations fix
the order of everything after it.

.. _spg-do-layout:

Stating the Layout
------------------

Each dtype constructor takes an optional second argument saying where its value sits in the
block. A bare number is a byte offset; the long form also states how a matrix is stored:

.. code-block:: lua

    slang.ParameterBlock(
        slang.uint(inputs["key"], 0),
        slang.float4x4(inputs["xform"], { offset = 16, order = slang.column_major, stride = 16 })
    )

``order`` takes ``slang.row_major`` or ``slang.column_major``. A bare number on a matrix is
rejected, because a matrix needs its storage order as well as its offset.

Offsets are **derived** when every value in the block is a single four-byte number. They become
**required** as soon as any vector or matrix appears, since alignment then decides the packing.

.. _spg-do-reflection:

What Reflection Fills In
------------------------

``.slang`` source and a pre-compiled ``.slang-module`` both carry reflection. A ``.spv``, which is
SPIR-V byte code, does not. Refer to :doc:`precompiled`. The rule between them is
one line: **the launch script is the source of truth, and reflection is the check on it.** What
the script states, reflection verifies; what it leaves out, reflection supplies; where the two
disagree, SPG reports it and binds what the shader declares.

.. list-table::
   :header-rows: 1
   :widths: 26 37 37

   * -
     - With reflection
     - Without reflection (``.spv``)
   * - Descriptor space
     - From the shader, or stated
     - **Must be stated**, with ``slang.bind(resources, N)``
   * - Binding slot
     - From the shader, or by position in a group
     - **By position in a group**, counting from zero
   * - Parameter-block offsets
     - From the shader, or stated
     - **Must be stated**, unless every value is a single four-byte number
   * - Matrix order and stride
     - From the shader, or stated
     - **Must be stated**
   * - Thread group size
     - The shader's ``[numthreads]``, which overrides a stated one
     - **Must be stated** with ``numthreads``, or ``grid`` stated in its place. With neither, the
       node reports what is missing and does not run.
   * - Entry point
     - ``subIdentifier``, or the prim name
     - Read from the binary
   * - ``grid``
     - Derived from the output's shape and the thread group size
     - The same, once a thread group size exists

A flat ``bind = { ... }`` therefore cannot work without reflection: nothing states a space, so
the node reports that the shader exposes no descriptor space and does not run.

Verify It Worked
----------------

Bind a value with an exact, reversible effect and check it byte for byte. An XOR key is the
usual choice: every output byte must equal the input byte XOR the key, with no exceptions. This
matters because a node whose parameter block never bound reads zeros, and XOR with zero is the
identity, so a broken binding renders an untouched copy rather than an error.

When It Goes Wrong
------------------

- "Shader exposes no descriptor space": a flat ``bind`` with a ``.spv``. Group with
  ``slang.bind``.
- A value lands in the wrong field: the order does not match the struct. A wrong count is an
  error, a wrong order only a warning.

Related
-------

:doc:`precompiled`, :doc:`values`, :doc:`../ref/lua_slang`
