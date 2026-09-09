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
     - A UsdShade Shader prim representing a processing node. In SPG, a shader is either a custom node (wrapping a CUDA kernel and Lua launch script through ``info:spg:sourceAsset``) or a built-in node (identified through ``info:id``). Inputs can be resource-inputs connected to AOVs (``opaque``) or value-inputs carrying typed values (``int``, ``float``, ``bool``).
   * - **Lua Launch Script**
     - The ``.lua`` file named after the GPU source and sitting beside it, ``GrayscaleKernel.cu.lua`` for a CUDA node and ``GrayscaleKernel.slang.lua`` for a Slang one. Called per frame to validate inputs, describe the outputs, and return a launch configuration.
   * - **subIdentifier**
     - The ``info:spg:sourceAsset:subIdentifier`` attribute on a Shader. Names the entry point in the GPU source, an ``extern "C"`` function on CUDA or a ``[shader(...)]`` entry point on Slang, and the Lua function to invoke. Optional: without it the Shader prim's own name is used for both.
   * - **shape**
     - A resource's dimensions, as a Lua table with one entry per dimension. Height-first for images: ``shape[1]`` is height, ``shape[2]`` is width. Refer to :ref:`spg-shapes-and-types`.
   * - **rank**
     - How many dimensions a resource has, which is how many entries its ``shape`` holds.
   * - **dtype**
     - What one element of a resource is: the kind of number, its width in bits, and how many of them make an element. A dtype is a value taken from the ``cuda`` or ``slang`` table, such as ``cuda.uchar4`` or ``slang.float``, not a type name. It can be compared against another dtype and called to wrap a value for the GPU. Refer to :ref:`spg-shapes-and-types`.
