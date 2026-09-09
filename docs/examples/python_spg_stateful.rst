.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Python: SPG Stateful Node
=========================

An SPG node that reads back its own previous output, so a moving object drags a fading comet
tail behind it. The whole node is one line, ``history[n] = current[n] + decay * history[n-1]``:
fade what you published last time, add what you were handed this time.

An output marked stateful keeps its resource across frames instead of being handed a fresh
one, and is zero-initialised on first use, so the node needs no special case for the first
frame. That resource is never published, so it needs no RenderVar.

.. image:: ../../img/example-spg-stateful.png
   :alt: SPG stateful node example output, a ball dragging a comet tail
   :align: center

The run writes two images from the same render step, ``_output/live.png`` and
``_output/trail.png``, through the same node and the same tone map. Everything that differs
between them came from the previous frame.

Prerequisites
-------------

- Python 3.10-3.13
- `uv <https://docs.astral.sh/uv/>`_
- An NVIDIA RTX-capable GPU and a supported driver

Running
-------

.. code-block:: bash

   uv run main.py                                # CUDA
   uv run main.py --scene trail_scene_slang.usda # Slang

The node ships in both languages, so the two backends can be compared side by side. See :doc:`../spg/do/state` for what stateful means and how an output is marked.
