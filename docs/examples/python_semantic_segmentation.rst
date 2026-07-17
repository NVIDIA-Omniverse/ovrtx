.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Python: Semantic Segmentation
=============================

Renders semantic segmentation from the bundled ``ovrtx-robot-lineup.usda`` scene through ``/World/Camera`` and streams labeled results to `rerun.io <https://rerun.io/>`_.

The example uses an inline USDA root layer with a relative ``subLayers`` arc to the source scene. The inline layer authors semantic-label overrides for each top-level robot payload, a ``RenderProduct`` targeting ``/World/Camera``, and one ``RenderVar`` for each requested AOV, so the original USD file is left untouched.

.. pull-quote::

   *“Create a Python example that composes an existing scene with semantic label overrides and camera annotation outputs, renders several camera AOVs including semantic segmentation and its ID map, decodes metadata into human-readable labels, logs a useful visual layout to a viewer, and supports headless image export.”*

.. image:: ../../img/example-semantic-segmentation.avif
   :alt: Semantic segmentation example output
   :align: center

Prerequisites
-------------

- Python 3.10-3.13
- `uv <https://docs.astral.sh/uv/>`_
- NVIDIA RTX-capable GPU
- Supported NVIDIA driver
- Internet access to download the remote payloads referenced by ``ovrtx-robot-lineup.usda``
- Unsandboxed runtime execution

Running
-------

.. code-block:: bash

   cd examples/python/semantic-segmentation
   uv run main.py

Options
^^^^^^^

.. list-table::
   :header-rows: 1

   * - Flag
     - Description
   * - ``--resolution WIDTH HEIGHT``
     - Set the render resolution
   * - ``--warmup-frames N``
     - Render warmup frames before logging
   * - ``--step-dt SECONDS``
     - Set the renderer step delta and Rerun simulation timestamp interval
   * - ``--grid-columns N``
     - Set the number of columns in the Rerun AOV grid blueprint
   * - ``--usd PATH``
     - Render a different USD file
   * - ``--no-spawn``
     - Do not spawn Rerun; write display PNGs for image AOVs to ``_output/``

The example decodes ``SemanticIdMap`` before logging ``SemanticSegmentation``. It remaps renderer semantic IDs into compact 16-bit Rerun class IDs, logs an ``AnnotationContext`` with the semantic labels, and displays the segmentation image in the Rerun blueprint grid.

The first step from a newly built application will block for 1-2 minutes while shaders are compiled and cached.
