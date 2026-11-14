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

    return slang.compute({
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
     - Both. Space ``N``, slots by position. Where the shader reports a place, the stated one must be it.

Two or more groups must each state a space, and may be listed in any order.
Grouping also scopes the matching: within a
group, resources are matched against the reflected resources of that space alone.

Lua rejects two ``ParameterBlock`` s in one group, a duplicate space across groups, and a space
that is negative or not an integer.

**Loose uniform values sit where the compiler puts them.** A shader can declare its values as
``uniform`` globals instead of a ``ParameterBlock`` struct. The compiler gathers them into one
buffer and gives it a binding and a descriptor space of its own, around the resources the shader
places, such as binding 1 of space 0 beside a resource at ``[[vk::binding(0, 0)]]``. Reflection
does not report that place, so SPG reads it from the compiled shader and binds the values there. A
launch script that states it, as the ``ParameterBlock``'s position in a group, must state the same
place. When SPG cannot read the place from the compiled shader, the launch script has to state it,
and without it the node's graph stops with a message saying so.

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
the order of everything after it. A value that states its offset goes to the field that starts
there instead, and the values after it continue from that field.

.. _spg-do-layout:

Stating the Layout
------------------

Each dtype constructor and ``slang.array`` take an optional table saying where the value sits
in the block: ``offset``, the byte it starts at, and ``strides``, one number per level of the
value, outermost first, each the bytes from one index of that level to the next. The levels
are the value's array dimensions and, for a matrix, its rows and then its columns. The lanes of
a vector sit one after another and take no stride. A stride of ``0`` leaves that level's stride
to the shader. A bare number in place of the table is the offset of a single number:

.. code-block:: lua

    slang.ParameterBlock(
        slang.uint(inputs["key"], 0),
        slang.float4x4(inputs["xform"], { offset = 16, strides = { 4, 16 } }),
        slang.array(inputs["weights"], slang.float, { offset = 80, strides = { 16 } })
    )

The strides of some common fields, as a padded layout lays them out, such as slangc's SPIR-V
build of a constant buffer:

.. list-table::
   :header-rows: 1
   :widths: 40 20 40

   * - Field
     - ``strides``
     - Reads as
   * - ``float weights[4]``
     - ``{ 16 }``
     - each number 16 bytes after the one before
   * - ``float2x2 m``, column-major
     - ``{ 4, 16 }``
     - the next row 4 bytes on, the next column 16
   * - ``float2x2 m``, row-major
     - ``{ 16, 4 }``
     - the next row 16 bytes on, the next column 4
   * - ``float2x2 mats[2]``, column-major
     - ``{ 32, 4, 16 }``
     - the next matrix 32 bytes on, then as one matrix

**An array of structs** goes in field by field. Each field of the structs is a value of its own,
an array starting at the offset of that field in the first struct. A value that states an offset
goes to the field, or the field of the structs, that starts there, and the values after it take
the fields after that one. With reflection the offset is enough, and the shader gives the strides;
without it, the stride of each struct is stated too. For ``struct Item { float a; int b; }
items[3]`` followed by ``float gain``, where each ``Item`` takes 16 bytes:

.. code-block:: lua

    -- With reflection
    slang.array(inputs["a"], slang.float, { offset = 0 }),
    slang.array(inputs["b"], slang.int,   { offset = 4 }),
    slang.float(inputs["gain"])

    -- Without reflection
    slang.array(inputs["a"], slang.float, { offset = 0, strides = { 16 } }),
    slang.array(inputs["b"], slang.int,   { offset = 4, strides = { 16 } }),
    slang.float(inputs["gain"], 48)

A value that goes to an array of structs without stating an offset stops the node's graph with
an error that names the field.

A dtype constructor holds one value: given an input with more elements, it stops the node's
graph with an error that names the input. An array goes in with ``slang.array``.

A matrix layout stated as ``{ offset, order, stride }`` is deprecated and logs a warning; it will
be removed in a later release. ``order = slang.column_major, stride = 16`` on a ``float4x4`` is
``strides = { 4, 16 }``, and ``order = slang.row_major, stride = 16`` is ``strides = { 16, 4 }``.
An ``order`` alone or a ``stride`` alone leaves the rest of the layout to the shader, so it works
only with reflection; without it, the node's graph stops with an error that names what is
missing.

Without reflection, offsets are **derived** when every value in the block is a single four-byte
number. They become **required** as soon as any vector or matrix appears, since alignment then
decides the packing.

A value fills the block from its offset with all of its elements: an array given at an offset is
packed whole, each element where its strides place it, and for a shader without reflection SPG
sizes the block to hold every element. A value with more elements than the field the shader declares for it holds stops
the node's graph, with an error that names the node, the value, its element count and the field.
A field holds the elements the shader declares, whatever padding its layout puts between or after
them: each element of an array, and each row or column of a matrix, goes where the layout starts
it.

.. _spg-do-reflection:

What Reflection Fills In
------------------------

``.slang`` source and a pre-compiled ``.slang-module`` both carry reflection. A ``.spv``, which is
SPIR-V byte code, does not. Refer to :doc:`precompiled`.
**Reflection checks the launch script:** what
the script states, reflection verifies; what it leaves out, reflection supplies; what reflection
does not report, the script supplies. Where the two disagree about where a value sits, its
parameter-block offset or the strides of an array or matrix, SPG packs the value where the shader
declares it and logs a warning once per node and value that names the value, what the script states and
what the shader declares. Where they disagree about a descriptor space, a binding slot or a
texture's dimension, the node's graph stops with an error that names the resource and both sides.
A value that neither the shader nor the script places, such as one more value than the shader's
fields, stops the node's graph with an error that names the value.

SPG reads the fields of a ``ConstantBuffer<T>`` from the compiled shader, so they are filled in and
checked as the fields of a ``ParameterBlock<T>`` are.

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
     - From the shader; a stated one that differs logs a warning
     - **Must be stated**, unless every value is a single four-byte number
   * - Strides of an array or matrix
     - From the shader; stated ones that differ log a warning
     - **Must be stated**, with ``{ offset, strides }``
   * - Thread group size
     - The shader's ``[numthreads]``, which overrides a stated one
     - **Must be stated** with ``numthreads``, or ``grid`` stated in its place. With neither, the
       node reports what is missing and its graph stops.
   * - Entry point
     - ``subIdentifier``, or the prim name
     - Read from the binary
   * - ``grid``
     - Derived from the output's shape and the thread group size
     - The same, once a thread group size exists

A flat ``bind = { ... }`` therefore cannot work without reflection: nothing states a space, so
the node reports that the shader exposes no descriptor space and its graph stops.

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
- "... but the shader places that buffer at binding ..." or "... but the shader declares ...
  there": a group lists its entries in another order than the shader's bindings. Order the group
  as the shader's ``vk::binding`` declarations.
- A warning "... in the launch script but the shader declares it ...": a stated offset or strides
  differ from the shader's, and the shader's were used. Correct the launch script, or leave the
  layout to reflection.
- A value lands in the wrong field: the order does not match the struct. A wrong count is an
  error, a wrong order only a warning.

Related
-------

:doc:`precompiled`, :doc:`values`, :doc:`../ref/lua_slang`
