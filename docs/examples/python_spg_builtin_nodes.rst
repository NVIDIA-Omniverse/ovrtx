.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Python: SPG Built-In Nodes
==========================

Not every SPG node needs a custom CUDA kernel. SPG ships built-in factory nodes that you author
with ``info:implementationSource = "id"`` and an ``info:id`` — no ``.cu`` or ``.cu.lua`` required.
This example chains two stdlib nodes: ``Add`` doubles the ``LdrColor`` AOV's brightness by adding
it to itself (saturating at 255), then ``Scale`` downscales that result to half resolution.

This example uses the deprecated renderer scene-loading API so it can remain
focused on SPG authoring. Use the 0.3-to-0.4 migration skill when moving scene
management to ovstage.

.. pull-quote::

   *“Chain two built-in SPG nodes (no custom CUDA) that brighten the color output and downscale it to half resolution, wired into a RenderProduct via info:id.”*

.. image:: ../../img/example-spg-builtin-nodes.png
   :alt: SPG built-in node example output
   :align: center

Prerequisites
-------------

- Python 3.10-3.13
- `uv <https://docs.astral.sh/uv/>`_
- An NVIDIA RTX-capable GPU and a supported driver

Running
-------

.. code-block:: bash

   uv run main.py

A successful run writes ``_output/input.png`` and ``_output/downscaled.png``. See
:ref:`spg-stdlib-nodes` for the full catalog of built-in nodes.
