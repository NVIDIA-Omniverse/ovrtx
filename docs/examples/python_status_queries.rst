.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Python: Status Queries Example
==============================

This example is based on the minimal Python example and adds operation status
queries for USD loading and rendering.

It demonstrates:

1. Loading a USD layer from a remote S3 scene URL with ``open_usd_async()``
2. Polling ``Operation.query_status()`` while waiting
3. Running one shader-cache warm-up step with shader compilation progress
4. Stepping the renderer with ``step_async()``
5. Fetching and mapping the rendered output

This compatibility example intentionally retains deprecated renderer population
operations because ovstage population does not expose equivalent progress
counters. New applications should otherwise use the attached ovstage workflow.

Renderer logs are written to ``_output/status-queries-ovrtx.log``.

.. pull-quote::

   *“Create a Python rendering example that demonstrates progress reporting for long-running ovrtx operations, including asynchronous scene loading, status polling while waiting, shader warmup feedback, final frame rendering, and save-or-display output.”*

.. image:: ../../img/example-minimal.jpg
   :alt: Status queries example output
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

   uv run main.py

To save the render instead of displaying it:

.. code-block:: bash

   uv run main.py --png
