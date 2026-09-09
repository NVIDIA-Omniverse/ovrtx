.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-do-previous-frame:

Read a Previous Frame
=====================

**Goal.** Read an AOV as it was N frames ago.

**Before you start.** :doc:`aovs`.

The Shape
---------

Suffix the RenderVar's ``sourceName`` with ``:-N``. Everything else is an ordinary RenderVar.
Highlighted: the same AOV named twice, once live and once a frame back.

.. literalinclude:: ../../../examples/python/spg-previous-frame/motion_scene.usda
   :language: usda
   :start-after: # [snippet:render-graph]
   :end-before: # [/snippet:render-graph]
   :emphasize-lines: 11, 19
   :caption: ``motion_scene.usda``, from the runnable :doc:`previous-frame example <../../examples/python_spg_previous_frame>`

How It Works
------------

**N counts frames back**, so ``:-1`` is last frame. It runs from 1 to 8. Each retained frame is a
separately allocated, full-size GPU resource, which is what bounds the depth.

**The source may come from the renderer or from a node.** When it is a node's output, SPG orders
the producer ahead of the consumer.

**Nothing on the node says anything about time.** It declares ordinary ``opaque`` ports, and which
of them is a past frame follows from the RenderVar the scene connects it to. The same node runs
unchanged on two live AOVs.

**An unrecognised suffix is not an error.** ``:-0``, ``:-`` on its own, a non-numeric suffix, and
any N above 8 all leave the name unchanged, so the RenderVar reads the live AOV under that literal
name.

**The last separator is the one that counts**, so ``a:-b:-2`` reads the source named ``a:-b``, two
frames back.

**This is not the same as a stateful output.** A stateful output is a node's own resource, handed
back to it next frame. ``:-N`` reads an AOV, through a RenderVar connected like any other. Refer to :doc:`state`.

Verify It Worked
----------------

Compare a moving scene against a still one, with the same graph. A node that subtracts the previous
frame from the current one lights up while something moves and goes dark when nothing does; a node
whose suffix was ignored is reading the live AOV twice and stays dark in both cases. A still scene
on its own cannot tell the two apart.

The :doc:`previous-frame example <../../examples/python_spg_previous_frame>` runs exactly that
pair, and the moving count comes out more than an order of magnitude above the still one.

Do not expect the still count to be zero, or either count to repeat between runs. A path-traced
render keeps refining, so consecutive frames of a static scene differ a little and the exact
numbers move. The ratio is what carries the result.

When It Goes Wrong
------------------

- The result matches the current frame: nothing in the scene changed between the two frames, or the
  suffix was not recognised and the RenderVar is reading the live AOV.
- Nothing appears at all: check the base name, which is everything before the last ``:-``.

Related
-------

:doc:`state`, :doc:`aovs`, :doc:`products`, :doc:`../../examples/python_spg_previous_frame`
