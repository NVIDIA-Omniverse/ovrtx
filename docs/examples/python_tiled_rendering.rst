.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Python: Tiled Rendering
=======================

Renders a 3×3 grid of scene instances through a single RenderProduct with multiple cameras. Demonstrates tiled multi-camera rendering, ovstage USD reference composition, ordinal-keyed transform and color writes, and attached-stage rendering.

Each grid cell references the same base scene but gets a unique logo color generated from evenly spaced HSV hues. A single 1024×1024 ``RenderProduct`` targets all nine cameras, and RTX tiles them into a grid in the output image.

.. pull-quote::

   *“Create a Python example that composes multiple referenced scene instances into a grid, assigns per-instance visual variation at runtime, renders all cameras through one tiled output, warms up for image quality, and saves or displays the final tiled image.”*

.. image:: ../../img/example-tiled-rendering.avif
   :alt: Tiled rendering example output
   :align: center

Prerequisites
-------------

- Python 3.10-3.13
- `uv <https://docs.astral.sh/uv/>`_

Running
-------

.. code-block:: bash

   cd examples/python/tiled-rendering
   uv run main.py

Options
^^^^^^^

.. list-table::
   :header-rows: 1

   * - Flag
     - Description
   * - ``--png``
     - Save rendered image to ``_output/tiled_render.png`` instead of displaying

The first time you run the example, the driver compiles and caches shaders. Subsequent runs are much faster.
