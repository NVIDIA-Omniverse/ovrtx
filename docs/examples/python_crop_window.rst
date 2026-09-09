.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION is strictly prohibited.

Python: Crop Window
===================

Renders the center 512×512 region of a 1024×1024 RenderProduct by authoring
``dataWindowNDC = (0.25, 0.25, 0.75, 0.75)``. The example verifies the mapped
``LdrColor`` dimensions before displaying the crop or saving it as a PNG.

.. pull-quote::

   *“Create an example that renders a centered dataWindowNDC crop from a full-resolution RenderProduct, verifies the cropped output dimensions, and saves or displays the result.”*

.. image:: ../../img/example-crop-window.png
   :alt: Center crop rendered with dataWindowNDC
   :align: center

Prerequisites
-------------

- Python 3.10-3.13
- `uv <https://docs.astral.sh/uv/>`_
- An NVIDIA RTX-capable GPU and a supported driver

Running
-------

.. code-block:: bash

   cd examples/python/crop-window
   uv run main.py

Pass ``--png`` to save ``_output/render.png`` instead of displaying the image.
