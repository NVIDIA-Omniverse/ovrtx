.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-do-chaining:

Chain Nodes
===========

**Goal.** Feed one node's output straight into the next, without publishing the intermediate.

**Before you start.** A working node, from :doc:`../first_node`.

The Shape
---------

Two nodes in a row, with the image passing between them never published:

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
      "LdrColor" -> "a"
      "a" -> "b"
      "b" -> "Out"
   }

Connect the downstream node's input to the upstream node's output. No RenderVar sits between
them:

.. code-block:: usda

    def Shader "InvertKernel" (
        references = @InvertKernel.usda@
    )
    {
        opaque inputs:Image.connect = <../GrayscaleKernel.outputs:LdrGrayscale>
    }

How It Works
------------

The pipeline scene does exactly that. Highlighted: the edge itself, and the ``orderedVars``
list, which names only the input and the final result. The grayscale image is produced and
consumed without ever appearing there.

.. literalinclude:: ../../../examples/python/spg-pipeline/pipeline_scene.usda
   :language: usda
   :start-after: # [snippet:render-graph]
   :end-before: # [/snippet:render-graph]
   :emphasize-lines: 7, 33
   :caption: ``pipeline_scene.usda``, from the runnable :doc:`pipeline example <../../examples/python_spg_pipeline>`

.. _spg-execution-order:

**Order comes from the connections**, not from ``orderedVars``. SPG runs nodes in topological
order over the edges the connections create. ``orderedVars`` says which AOVs a product
produces; it does not sequence anything.

**An intermediate stays inside the graph.** An output consumed by another node needs no
RenderVar, is not published, and cannot be read back from the host. Publishing it is a
deliberate act: give it a RenderVar and list it. Refer to :doc:`aovs`.

**Languages can be mixed.** Nothing requires the two nodes in a chain to be written in the
same language.

Verify It Worked
----------------

Read back the final AOV and check that both transformations survived. In the
:doc:`pipeline example <../../examples/python_spg_pipeline>` that means ``R == G == B`` from the
first node, and each channel equal to ``255 - g`` where ``g`` is the grey value the first node
produced. Grey but not inverted means the second node did not run. Inverted but still coloured
means the first did not. The example recomputes the unpublished intermediate on the host and
prints the largest difference it found.

When It Goes Wrong
------------------

- The second node never runs: its output is not consumed and publishes no RenderVar. Refer to
  :ref:`Nothing Appears <spg-symptom-nothing>`.
- The intermediate cannot be read back: that is by design. Publish it if you need it.

Related
-------

:doc:`aovs`, :doc:`split_join`, :doc:`../../examples/python_spg_pipeline`
