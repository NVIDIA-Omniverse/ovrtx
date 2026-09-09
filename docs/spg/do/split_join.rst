.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-do-split-join:

Split and Join
==============

**Goal.** Feed one node's output to several consumers, or several producers into one node.

**Before you start.** :doc:`chaining`.

The Shape
---------

Both are ordinary connections. A port may be the source of more than one edge, and a node may
declare more than one input.

**Fan out.** One node's output feeds a published AOV and a second node at the same time.

.. graphviz::
   :align: center

   digraph {
      rankdir=LR
      bgcolor="transparent"
      node [shape=box style="rounded,filled" fontname="Helvetica" fontsize=11 penwidth=0]
      edge [color="#9aa0a6" penwidth=1.2 arrowsize=0.7]
      "LdrColor" [fillcolor="#4c566a" fontcolor="white"]
      "Out1" [fillcolor="#4c566a" fontcolor="white"]
      "Out2" [fillcolor="#4c566a" fontcolor="white"]
      "a" [fillcolor="#76b900" fontcolor="#1b1b1b"]
      "b" [fillcolor="#76b900" fontcolor="#1b1b1b"]
      "LdrColor" -> "a"
      "a" -> "Out1"
      "a" -> "b"
      "b" -> "Out2"
   }

**Fan in.** One node takes two inputs, here an upstream node's output and an AOV directly.

.. graphviz::
   :align: center

   digraph {
      rankdir=LR
      bgcolor="transparent"
      node [shape=box style="rounded,filled" fontname="Helvetica" fontsize=11 penwidth=0]
      edge [color="#9aa0a6" penwidth=1.2 arrowsize=0.7]
      "LdrColor" [fillcolor="#4c566a" fontcolor="white"]
      "Out" [fillcolor="#4c566a" fontcolor="white"]
      "a" [fillcolor="#76b900" fontcolor="#1b1b1b"]
      "n" [fillcolor="#76b900" fontcolor="#1b1b1b"]
      "LdrColor" -> "a"
      "a" -> "n"
      "LdrColor" -> "n"
      "n" -> "Out"
   }

**Diamond.** A split that rejoins, so ``d`` runs only after both branches have.

.. graphviz::
   :align: center

   digraph {
      rankdir=LR
      bgcolor="transparent"
      node [shape=box style="rounded,filled" fontname="Helvetica" fontsize=11 penwidth=0]
      edge [color="#9aa0a6" penwidth=1.2 arrowsize=0.7]
      "LdrColor" [fillcolor="#4c566a" fontcolor="white"]
      "Out" [fillcolor="#4c566a" fontcolor="white"]
      "a" [fillcolor="#76b900" fontcolor="#1b1b1b"]
      "b" [fillcolor="#76b900" fontcolor="#1b1b1b"]
      "c" [fillcolor="#76b900" fontcolor="#1b1b1b"]
      "d" [fillcolor="#76b900" fontcolor="#1b1b1b"]
      "LdrColor" -> "a"
      "a" -> "b"
      "a" -> "c"
      "b" -> "d"
      "c" -> "d"
      "d" -> "Out"
   }

How It Works
------------

**A node's output may feed more than one consumer.** Connect the same ``outputs:`` port to each
one. The :doc:`blur example <../../examples/python_spg_blur>` does this with the first of its two
passes, which feeds the second pass and a RenderVar of its own:

.. literalinclude:: ../../../examples/python/spg-blur/blur_scene.usda
   :language: usda
   :start-after: # [snippet:render-graph]
   :end-before: # [/snippet:render-graph]
   :emphasize-lines: 21, 41
   :caption: ``blur_scene.usda``, from the runnable :doc:`blur example <../../examples/python_spg_blur>`

**A published RenderVar may also feed more than one node.** Both fan-outs are allowed, and the
choice is not about the graph but about who else may see the intermediate. A direct connection keeps
it inside the graph; a RenderVar exposes it to the host and to other products, and costs you a name
in ``orderedVars``. Refer to :doc:`aovs`.

**A node's inputs may come from different kinds of source.** In the fan-in shape, ``n`` takes one
input from an upstream node and one straight from an AOV. A node whose inputs are two other nodes'
outputs works the same way, including when one of those is itself a join.

The :doc:`built-in nodes example <../../examples/python_spg_builtin_nodes>` joins in the simplest
possible way: one AOV feeds both inputs of an Add node, which is how it doubles brightness.

.. literalinclude:: ../../../examples/python/spg-builtin-nodes/stdlib_scene.usda
   :language: usda
   :start-after: # [snippet:render-graph]
   :end-before: # [/snippet:render-graph]
   :emphasize-lines: 26-27
   :caption: ``stdlib_scene.usda``, from the runnable :doc:`built-in nodes example <../../examples/python_spg_builtin_nodes>`

**Order still comes from the edges.** Every branch of a split runs after its producer, and a join
runs after all of its producers. Refer to :ref:`Order comes from connections <spg-execution-order>`.

**Two graphs with no shared edge are independent.** ``LdrColor -> a -> OutA, LdrColor -> b -> OutB``
is two graphs in one product, not one graph.

Verify It Worked
----------------

Give the branches kernels with different, recognisable effects, then read every published AOV
back. Each must show its own branch's transform, and no two may be equal. Two identical outputs
mean one branch is unwired and both RenderVars are reading the same producer.

The blur example reads all three of its AOVs and checks that they fall in order: the sharpest edge
in the image drops once after the horizontal pass and again after the vertical one. The middle
value only exists because the first pass feeds a RenderVar as well as the second node. The check is
the ordering, not the three figures, which move with the render.

When It Goes Wrong
------------------

- A branch never runs: its output is consumed by nothing and it publishes no RenderVar. Refer to
  :ref:`Nothing Appears <spg-symptom-nothing>`.
- A join reads one input and not the other: the second connection is missing, or its port name does
  not match the shader definition.

Related
-------

:doc:`chaining`, :doc:`aovs`, :doc:`products`, :doc:`../../examples/python_spg_blur`
