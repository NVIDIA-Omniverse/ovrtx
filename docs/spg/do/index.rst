.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-tasks:

How-To
======

One page per thing a node or a graph can do. These are not written to be read in order.
Each page states its goal, what it assumes you already have, the shape of the
solution, how to confirm it worked, and what to check when it does not.

Both languages appear on the same page. Where CUDA and Slang differ, each is shown in its own tab
rather than in a separate chapter. For the surface each task draws on, refer to :doc:`../ref/index`.

Write a Node
------------

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Task
     - Goal
   * - :doc:`values`
     - Give a node a number, vector or matrix authored in USD, and read it in the GPU code.
   * - :doc:`textures_buffers`
     - Decide whether a resource is texture-backed or buffer-backed, and bind it correctly.
   * - :doc:`upload_data`
     - Get a lookup table, a filter kernel or any authored array onto the GPU.
   * - :doc:`launch_geometry`
     - Decide how many GPU threads run, and over what.
   * - :doc:`precompiled`
     - Build the GPU code with your own toolchain, or split it across files.

Wire a Graph
------------

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Task
     - Goal
   * - :doc:`chaining`
     - Feed one node's output straight into the next, without publishing the intermediate.
   * - :doc:`split_join`
     - Feed one node's output to several consumers, or several producers into one node.
   * - :doc:`aovs`
     - Decide what a graph exposes to the rest of the pipeline, and get it back on the host.
   * - :doc:`products`
     - Read an AOV produced by a different RenderProduct, or drive several products at once.
   * - :doc:`generate`
     - Build an AOV out of authored values alone, with no AOV coming in.
   * - :doc:`builtin`
     - Get a common operation without writing any GPU code.

Across Frames
-------------

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Task
     - Goal
   * - :doc:`state`
     - Let a node read what it wrote last frame.
   * - :doc:`previous_frame`
     - Read an AOV as it was N frames ago.
   * - :doc:`caching`
     - Compute something once instead of every frame.
   * - :doc:`runtime_changes`
     - Retune or rewire a graph without reloading the scene.

Reach Beyond an AOV
-------------------

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Task
     - Goal
   * - :doc:`composites`
     - Consume a lidar or radar point cloud in a node.
   * - :doc:`raygen`
     - Have a node render the scene itself rather than transform an AOV.

Slang Specifics
---------------

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Task
     - Goal
   * - :doc:`descriptor_sets`
     - Place resources into specific descriptor spaces, and state a constant buffer's layout.

.. toctree::
   :hidden:

   values
   textures_buffers
   upload_data
   launch_geometry
   precompiled
   chaining
   split_join
   aovs
   products
   generate
   builtin
   state
   previous_frame
   caching
   runtime_changes
   composites
   raygen
   descriptor_sets
