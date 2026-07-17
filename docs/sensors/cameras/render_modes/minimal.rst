.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Minimal
=======

Minimal mode uses lightweight rasterization with minimal GPU cost. Use this when you need maximum throughput and do not require path-traced lighting -- for example, segmentation masks, bounding-box visualization, or high-FPS reinforcement learning loops.

.. code-block:: usda

   token omni:rtx:rendermode = "Minimal"

Lighting Behavior
-----------------

Minimal mode only respects the first ``DistantLight`` found in the scene, and shadows from that light are hard shadows. This restriction keeps Minimal mode fast and stable for speed-of-light rendering workloads.

Other light types, such as ``DomeLight``, are not used for Minimal mode lighting. If the scene has no ``DistantLight``, Minimal mode falls back to a single camera light.

For improved visibility without adding scene lights, use ambient lighting through the ``omni:rtx:rt:ambientLight:color`` and ``omni:rtx:rt:ambientLight:intensity`` attributes listed below, or disable shadows with ``omni:rtx:minimal:castShadows``.

Settings
--------

.. rst-class:: compact-table

.. list-table::
   :header-rows: 1
   :widths: 70 15 15

   * - USD Attribute
     - Type
     - Default
   * - ``omni:rtx:minimal:mode``

       Selects the shading mode.

       | 0: No Rendering -- no path tracing is performed and LdrColor is black; use when only data outputs such as depth and albedo are required.
       | 1: Constant Diffuse -- uses a single constant color for all surfaces.
       | 2: Texture Diffuse -- uses diffuse texture colors.
       | 3: Diffuse/Glossy/Emission -- full material evaluation with diffuse, glossy, and emission.
     - ``int``
     -
   * - ``omni:rtx:minimal:constantColor``

       The color to use in Constant Diffuse shading mode.
     - ``float3``
     -
   * - ``omni:rtx:minimal:castShadows``

       Global toggle to cast hard shadows from the first ``DistantLight`` in Minimal render mode.
     - ``bool``
     -
   * - ``omni:rtx:rt:ambientLight:color``

       Color of the global ambient environment lighting.
     - ``float3``
     -
   * - ``omni:rtx:rt:ambientLight:intensity``

       Brightness of the global ambient environment lighting. A value of 0 disables ambient lighting.
     - ``float``
     -
