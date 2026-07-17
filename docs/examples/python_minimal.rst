.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Python: Minimal Example
=======================

This is the minimal Python example from the ovrtx README. It demonstrates the basic workflow:

1. Create a Renderer
2. Load a USD layer from a remote S3 scene URL
3. Step the renderer to produce a frame
4. Map the rendered output and display it

.. pull-quote::

   *“Create the smallest useful Python example that loads an existing USD scene, renders one camera frame, maps the color output to CPU memory, and either displays it or saves it as an image through a command-line flag.”*

.. image:: ../../img/example-minimal.jpg
   :alt: Minimal example output
   :align: center

Prerequisites
-------------

- Python 3.10-3.13
- `uv <https://docs.astral.sh/uv/>`_
- NVIDIA RTX-capable GPU
- Supported NVIDIA driver
- Internet access to download the remote S3 scene asset
- Unsandboxed runtime execution

Running
-------

.. code-block:: bash

   uv run main.py --png

A successful run writes ``_output/render.png``. The first step from a newly built application will block for 1-2 minutes while shaders are compiled and cached.
