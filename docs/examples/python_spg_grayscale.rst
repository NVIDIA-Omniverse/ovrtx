.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Python: SPG Grayscale
=====================

The "hello world" of Sensor Processing Graphs. A custom CUDA kernel converts the renderer's
``LdrColor`` AOV to grayscale entirely on the GPU and publishes the result as a new
``LdrGrayscale`` AOV. This is the minimal three-file SPG shader (``.cu`` kernel, ``.cu.lua``
launch script, ``.usda`` shader definition) wired into a ``RenderProduct``.

.. pull-quote::

   *“Create the smallest useful SPG example: a CUDA kernel that converts the LdrColor render output to grayscale, wired into a RenderProduct and read back from Python as a new AOV.”*

.. image:: ../../img/example-spg-grayscale.png
   :alt: SPG grayscale example output
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

The first step compiles the CUDA kernel with NVRTC and can block for up to a minute on a fresh
shader cache. A successful run writes ``_output/input.png`` and ``_output/grayscale.png``, which
is the same image with the colour taken out.

The run checks ``R == G == B`` in every pixel of the output, which the renderer's own
``LdrColor`` does not satisfy, and tests the input as well so that a node which never ran cannot
pass on a scene that was already grey. A failing check exits non-zero.

See the :doc:`../spg/overview` documentation for the full authoring reference.
