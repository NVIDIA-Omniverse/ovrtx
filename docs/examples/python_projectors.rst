.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Python: Projectors
==================

Renders an authored scene that demonstrates cubic, planar, spherical normalized, and tri-planar UV projection across
several primitive types. The cubic Cube demonstrates applying ``OmniProjectorAPI`` to a separate projector prim and
targeting it from the geometry through ``coordSys:st:binding``.

.. pull-quote::

   *“Create a Python example that loads the projectors scene without modifying it, warms up the renderer, renders one frame, and saves the result as a PNG.”*

.. image:: ../img/projectors-lineup.avif
   :alt: Projectors example output
   :align: center

Prerequisites
-------------

- Python 3.10-3.13
- `uv <https://docs.astral.sh/uv/>`_
- An NVIDIA RTX-capable GPU and a supported driver

Running
-------

.. code-block:: bash

   cd examples/python/projectors
   uv run main.py

A successful run writes ``_output/projectors.png``.
