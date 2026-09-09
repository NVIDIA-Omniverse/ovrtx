.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-do-builtin:

Use a Built-In Node
===================

**Goal.** Get a common operation without writing any GPU code.

**Before you start.** :doc:`aovs`.

The Shape
---------

A built-in node is named rather than sourced. There is no GPU file and no launch script:

.. code-block:: usda

    def Shader "AddNode"
    {
        uniform token info:implementationSource = "id"
        uniform token info:id = "spg:rtx.spg.stdlib/Add"

        opaque inputs:A.connect = <../LdrColor.omni:rtx:aov>
        opaque inputs:B.connect = <../LdrColor.omni:rtx:aov>
        opaque outputs:Result
    }

How It Works
------------

The scene adds ``LdrColor`` to itself with the built-in Add node, doubling brightness with
saturating arithmetic, then halves the resolution with the built-in Scale node. Highlighted:
the two lines that name each one. Everything else is the ordinary wiring of any graph.

.. literalinclude:: ../../../examples/python/spg-builtin-nodes/stdlib_scene.usda
   :language: usda
   :start-after: # [snippet:render-graph]
   :end-before: # [/snippet:render-graph]
   :emphasize-lines: 23-24, 33-34
   :caption: ``stdlib_scene.usda``, from the runnable :doc:`built-in nodes example <../../examples/python_spg_builtin_nodes>`

- ``info:implementationSource = "id"`` tells SPG this shader is identified by an
  SPG node ID, not a source asset. ``info:id`` names the built-in node
  (``"spg:rtx.spg.stdlib/Add"``, ``"spg:rtx.spg.stdlib/Scale"``). The ``spg:`` prefix scopes
  SPG node IDs away from MaterialX and UsdPreview shader IDs.
- No GPU source file, launch script, or external shader definition is needed. The entire
  graph is defined inline in the scene file.
- Shader-to-shader chaining works the same way as for nodes you write yourself:
  ``ScaleNode.inputs:Input`` connects directly to ``AddNode.outputs:Result``.
- :doc:`Value-inputs <values>` (``scaleX``, ``scaleY``) also behave the same way. Scene files can override
  defaults per shader instance.
- ``orderedVars`` lists only the input (``LdrColor``) and final output
  (``Downscaled``). The intermediate brightened result from AddNode is internal
  to the chain.

**A built-in is the whole node, not a starting point.** You get it by name and you get its
behaviour as it is: no GPU source to edit, no launch script to adjust, and no way to change what it
does beyond the value-inputs it declares. The moment you need something it does not do, you are
writing a node, and the two cannot be mixed within one shader. What the built-ins are is
:doc:`../ref/builtin_catalogue`.

Verify It Worked
----------------

Compare both the dimensions and the values against the input. Add and Scale together double
brightness with saturating arithmetic and halve each dimension, so the output is exactly half the
input's width and height, and a pixel at value ``v`` comes back at ``min(2v, 255)``. A value that
did not double means Add never ran; a size that did not halve means Scale never ran. Both
operations are exact in integers, so the
:doc:`built-in nodes example <../../examples/python_spg_builtin_nodes>` rebuilds them on the host
and compares with no tolerance, printing
``largest difference from the host-computed result: 0``.

When It Goes Wrong
------------------

- The node is not found: check the ``info:id`` against :doc:`../ref/builtin_catalogue`.
  A misspelling is the usual cause. An ID outside that table may belong to another renderer
  component; it is not a supported authoring surface.
- The node rejects its input: these operate on 2D textures only, and not on integer formats.

Related
-------

:doc:`../ref/builtin_catalogue`, :doc:`aovs`
