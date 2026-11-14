.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Python: SPG Pipeline
====================

Two SPG shaders chained into a pipeline: ``LdrColor`` → grayscale → invert → ``LdrInverted``.
Shaders are chained by connecting one shader's output directly to the next shader's input, so the
intermediate grayscale result stays internal to the chain and only the final image is published
as an AOV. SPG runs the shaders in topological order of the connection graph.

.. pull-quote::

   *“Chain two SPG shaders so the renderer's color output is converted to grayscale and then inverted in a single RenderProduct, reading back only the final result.”*

.. image:: ../../img/example-spg-pipeline.png
   :alt: SPG two-shader pipeline example output
   :align: center

Prerequisites
-------------

- Python 3.10-3.13
- `uv <https://docs.astral.sh/uv/>`_
- An NVIDIA RTX-capable GPU and a supported driver

Running
-------

.. code-block:: bash

   uv run main.py                                    # CUDA
   uv run main.py --scene pipeline_scene_slang.usda  # Slang

The first step compiles both kernels. A successful run writes
``_output/input.png`` and ``_output/inverted_grayscale.png``, the input turned grey by the first
node and inverted by the second. See :doc:`../spg/do/chaining` for the chaining and intermediate-AOV
patterns.
