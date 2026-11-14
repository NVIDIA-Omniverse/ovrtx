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

Suffix the RenderVar's ``sourceName`` with ``:-N``.
Highlighted: the same AOV named twice, once live and once a frame back.

.. literalinclude:: ../../../examples/python/spg-previous-frame/motion_scene.usda
   :language: usda
   :start-after: # [snippet:render-graph]
   :end-before: # [/snippet:render-graph]
   :emphasize-lines: 11, 19
   :caption: ``motion_scene.usda``, from the runnable :doc:`previous-frame example <../../examples/python_spg_previous_frame>`

How It Works
------------

**N counts frames back**, so ``:-1`` is last frame and ``:-0`` the current one. It runs up to the
``/rtx/spg/state/maxPreviousFrameOffset`` setting, 8 by default. Each retained frame is a separately
allocated, full-size GPU resource, which is what bounds the depth. An AOV keeps as many frames as the
deepest read of it so far, for as long as any node reads it from an earlier frame, and releases them
when the last such read goes. A frame in which the AOV was not
produced, such as the first frames or a frame the render product was not rendered, reads as zeros;
an older frame is never returned in its place.

**A read further back than that setting allows stops the node's graph**, with an error naming
the node.

**A change of the AOV's shape starts its history over.** The frames from before the change read as
zeros, in the new shape.

**The source may come from the renderer or from a node.** When it is a node's output, SPG orders
the producer ahead of the consumer.

**A sensor composite keeps whole frames.** A ``:-N`` read of a sensor composite, such as a lidar
or radar ``PointCloud``, gives that frame as the sensor filled it: its channels with their contents
and lengths, its params and its status, which the launch script sees as well. Each kept frame holds
a copy of every channel.

- A frame the history does not hold reads as an empty frame: status ``"empty"``, and the channels
  and params of the newest frame the history holds, at its lengths, all zero.
- Until the history holds a first frame, the node does not run.
- When the channels or params change by name, element type or memory kind, the history starts
  over. A change of length, or only of the order of the channels, keeps it.
- SPG keeps earlier frames only of a composite whose channels are all GPU buffers of an element
  type SPG binds, stored compactly, with no ``/`` in their names. A ``:-N`` read of another
  composite stops the node's graph with an error naming the channel and why.

**The RenderVar picks the frame.** The node declares ``opaque`` ports, and which
of them is a past frame follows from the RenderVar the scene connects it to. The same node runs
unchanged on two live AOVs.

**A suffix that is not a number is part of the name.** ``:-`` on its own and a suffix such as
``:-x`` leave the name unchanged, so the RenderVar reads the live AOV under that literal name.

**The last separator is the one that counts**, so ``a:-b:-2`` reads the source named ``a:-b``, two
frames back.

**This is not the same as a node's memory.** Memory is the node's own resource, handed back to it
next frame and to nobody else. ``:-N`` reads an AOV through a RenderVar. Refer to :doc:`state`.

Verify It Worked
----------------

Compare a moving scene against a still one, with the same graph. A node that subtracts the previous
frame from the current one lights up while something moves and goes dark when nothing does; a node
whose suffix was ignored is reading the live AOV twice and stays dark in both cases. A still scene
on its own cannot tell the two apart.

The :doc:`previous-frame example <../../examples/python_spg_previous_frame>` runs exactly that
pair: ``motion-moving.png`` shows the ball and the hole it left, and ``motion-still.png`` stays
close to black.

Do not expect the still image to be completely black. A path-traced render keeps refining, so
consecutive frames of a static scene differ a little. The contrast between the two is what carries
the result.

When It Goes Wrong
------------------

- The result matches the current frame: nothing in the scene changed between the two frames, or the
  suffix was not recognised and the RenderVar is reading the live AOV.
- Nothing appears at all: check the base name, which is everything before the last ``:-``.
- The node's graph stops and the message names a channel of a sensor composite: the RenderVar read
  with ``:-N`` is a composite with a channel that is not a GPU buffer of an element type SPG binds,
  stored compactly, with no ``/`` in its name, and SPG keeps no earlier frames of it; the message says
  why.
- The node never runs on a sensor composite read with ``:-N``: the composite has not been rendered
  since the read began, so its history holds no frame yet.
- The node's graph stops and the message says how far back reads may reach: N is larger than
  ``/rtx/spg/state/maxPreviousFrameOffset`` allows, 8 by default.

Related
-------

:doc:`state`, :doc:`aovs`, :doc:`products`, :doc:`../../examples/python_spg_previous_frame`
