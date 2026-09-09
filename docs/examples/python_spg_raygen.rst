.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Python: SPG Ray Generation
==========================

An SPG node that traces the scene itself instead of post-processing an AOV. One primary ray per
pixel through the render product's camera, a shadow ray toward the light, and the exact
geometric normal of every surface recovered from two extra probe rays. The whole image is
produced by the node; nothing in it is a renderer AOV.

.. image:: ../../img/example-spg-raygen.png
   :alt: A ray-traced Cornell box rendered by a single SPG ray-generation node
   :align: center

Surface colour is the recovered normal, encoded and modulated by the lighting, so each face's
hue states its orientation: the floor's +Y reads green-dominant, the left wall's +X
red-dominant, the back wall's +Z blue-dominant. The two blocks are rotated about Y, so their
faces are not axis aligned and each still resolves to its own correct normal.

A shader under a RenderProduct receives the scene acceleration structure and its camera's
transform with no authored input and no connection, which is what lets it author rays in
ordinary camera space. No vertex data is exposed, so the normal is derived from the trace
itself: three points on a flat triangle define its plane.

Prerequisites
-------------

- Python 3.10-3.13
- `uv <https://docs.astral.sh/uv/>`_
- An NVIDIA RTX-capable GPU and a supported driver
- The renderer running on Vulkan, which is the default

Running
-------

.. code-block:: bash

   uv run main.py                                          # inline RayQuery
   uv run main.py --scene cornell_box_pipeline_scene.usda  # ray-tracing pipeline

The same room, traced two ways. Both runs print the same checks, and the two images agree on
99.85% of pixels. Refer to :doc:`../spg/do/raygen` for what the two forms differ in.

``main.py`` checks the render with no golden image: that no ray escaped the room, that each
wall's dominant colour channel matches its normal, that a real population of off-axis normals
is present, and that both shadowed and lit pixels exist. See :doc:`../spg/do/raygen` for
the ray-generation dispatch and the implicit scene binding.
