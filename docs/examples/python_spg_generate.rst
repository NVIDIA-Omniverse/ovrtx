.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Python: SPG Generating Node
===========================

An SPG node with no input AOV at all. Every value it needs is a typed USD attribute, and it
draws a checkerboard into its own output, which the scene publishes as ``Checker``.

The run checks itself: it rebuilds the same checkerboard on the host from the attributes the
scene authored and compares the two pixel for pixel.

Running
-------

.. code-block:: bash

   uv run main.py

The first step compiles the kernel with NVRTC and can take up to a minute on a cold shader
cache. A successful run writes ``_output/checker.png`` and prints
``pixels differing from the host-computed pattern: 0``. A difference above zero exits non-zero.

The Node
--------

.. literalinclude:: ../../examples/python/spg-generate/CheckerKernel.cu.lua
   :language: lua
   :start-after: -- [snippet:checker-launch]
   :end-before: -- [/snippet:checker-launch]

Refer to :doc:`../spg/do/generate` for what a node without an input can and cannot assume.
