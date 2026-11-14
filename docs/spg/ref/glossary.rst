.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Glossary
========

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Term
     - Definition
   * - **Shader**
     - A UsdShade Shader prim representing a processing node. In SPG, a shader is either a custom node (wrapping a CUDA kernel or Slang shader and its Lua launch script through ``info:spg:sourceAsset``) or a built-in node (identified through ``info:id``). Inputs can be resource-inputs connected to AOVs (``opaque``) or value-inputs carrying typed values (``int``, ``float``, ``bool``).
   * - **Lua Launch Script**
     - The ``.lua`` file named after the GPU source and sitting beside it, ``GrayscaleKernel.cu.lua`` for a CUDA node and ``GrayscaleKernel.slang.lua`` for a Slang one. Called per frame to validate inputs, describe the outputs, and return a launch configuration.
   * - **subIdentifier**
     - The ``info:spg:sourceAsset:subIdentifier`` attribute on a Shader. Names the entry point in the GPU source, an ``extern "C"`` function on CUDA or a ``[shader(...)]`` entry point on Slang, and the Lua function to invoke. Optional: without it the Shader prim's own name is used for both.
   * - **shape**
     - A resource's dimensions, as a Lua table with one entry per dimension. Height-first for images: ``shape[1]`` is height, ``shape[2]`` is width. Refer to :ref:`spg-shapes-and-types`.
   * - **rank**
     - How many dimensions a resource has, which is how many entries its ``shape`` holds.
   * - **dtype**
     - What one element of a resource is: the kind of number, its width in bits, and how many of them make an element. A dtype is a value taken from the ``cuda`` or ``slang`` table, such as ``cuda.uchar4`` or ``slang.float``. It can be compared against another dtype and called to wrap a value for the GPU. Refer to :ref:`spg-shapes-and-types`.
   * - **Prim table**
     - What a launch script gets for a prim of the scene: ``rtx.stage.prim(path)``, an entry of ``rtx.product.cameras`` or ``rtx.product.render_vars``, or ``rtx.product`` itself. It answers ``path``, ``local_matrix``, ``world_matrix`` and any attribute by name, reads them when asked, and cannot be assigned to. Refer to :doc:`lua_rtx`.
   * - **On the stage**
     - Published for the renderer at the time a launch script runs. Loading a scene puts its prims on the stage with what the renderer needs of them; custom attributes arrive only when the load names their prim. Refer to :ref:`spg-rtx-availability`.
   * - **AOV**
     - Arbitrary Output Variable: a named output of a RenderProduct, such as ``LdrColor``. A node reads AOVs and can publish its own. Refer to :doc:`../do/aovs`.
   * - **RenderVar**
     - The prim that names an AOV through ``sourceName``. Its ``omni:rtx:aov`` exposes the AOV to a node, and its ``omni:rtx:aov.connect`` publishes a node output under that name. Refer to :doc:`usd`.
   * - **Resource-input**, **resource-output**
     - A port declared ``opaque inputs:X`` or ``opaque outputs:Y``. It carries an AOV, a buffer another node produced, or a sensor composite; the launch script sees its descriptor. Refer to :ref:`spg-nodes-and-ports`.
   * - **Value-input**
     - An ``inputs:`` attribute that is not ``opaque``, such as ``float inputs:strength``. The launch script gets a wrapper whose ``.value`` is the raw Lua value. Refer to :ref:`spg-value-input-types`.
   * - **Composite**
     - What a lidar or radar publishes under one RenderVar: several named channels and params in place of one image. ``inputs["X"].isComposite`` tells the two apart. Refer to :doc:`../do/composites`.
   * - **Memory**
     - Storage only the node reads and writes, kept across frames for as long as the node lives. Stated on ``self.memory`` in the launch script. Refer to :doc:`../do/state`.
   * - **Stateful output**
     - An output SPG hands back as the same resource next frame, marked with a trailing ``cuda.stateful`` or ``slang.stateful``, or with ``self.stateful = true``. It stays a port that can be published and connected. Refer to :doc:`../do/state`.
