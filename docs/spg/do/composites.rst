.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-do-composites:

Read a Sensor Composite
=======================

**Goal.** Consume a lidar or radar point cloud in a node.

**Before you start.** :doc:`textures_buffers`.

The Shape
---------

A composite arrives as a table of named channels under one RenderVar. Test for it, then take
the channels you need by name:

.. code-block:: lua

    local pc = inputs["PointCloud"]
    assert(pc.isComposite, "PointCloud must be connected to a composite AOV")

    local coordinates = pc.tensors["Coordinates"]
    local counts      = pc.tensors["Counts"]

How It Works
------------

Highlighted: the test that distinguishes a composite from an ordinary AOV, and the two channels
taken out of it. What the node then does with those channels is covered in
:doc:`textures_buffers`.

.. tab-set::

   .. tab-item:: CUDA
      :sync: cuda

      .. filtered-literalinclude:: ../../../examples/python/spg-composite-aov/RangeHistogramKernel.cu.lua
         :language: lua
         :start-after: -- [snippet:histogram-launch]
         :end-before: -- [/snippet:histogram-launch]
         :exclude-pattern: ^\s*--\s*\[/?snippet:
         :emphasize-lines: 14, 16-17

   .. tab-item:: Slang
      :sync: slang

      .. filtered-literalinclude:: ../../../examples/python/spg-composite-aov/RangeHistogramKernel.slang.lua
         :language: lua
         :start-after: -- [snippet:histogram-slang-launch]
         :end-before: -- [/snippet:histogram-slang-launch]
         :exclude-pattern: ^\s*--\s*\[/?snippet:
         :emphasize-lines: 16, 18-19

**The scene asks for the channels it needs.** The ``channels`` attribute on the RenderVar lists
them, and each listed channel the sensor supports appears. A name the sensor does not support, such
as a misspelling or a channel of another kind of sensor, is left out, and some sensors publish no
point cloud at all when none of the listed names is supported. A sensor can add channels of its own
as well, so a composite can carry channels the scene did not ask for: the point cloud of an
``OmniLidar`` or ``OmniRadar`` sensor always carries ``Counts`` and ``Flags``, and other sensor
models decide their own channels.

.. literalinclude:: ../../../examples/python/spg-composite-aov/lidar_scene.usda
   :language: usda
   :start-after: # [snippet:lidar-render-graph]
   :end-before: # [/snippet:lidar-render-graph]
   :emphasize-lines: 12-17
   :caption: ``lidar_scene.usda``, from the runnable :doc:`composite AOV example <../../examples/python_spg_composite_aov>`

**A sensor point cloud is always a composite.** A ``PointCloud`` RenderVar is one whether or not it
lists ``channels``.

**The connection decides whether a port is a composite**, so the same node can be pointed at a
different sensor without editing the shader.

**An input therefore arrives in one of two shapes, and the script has to handle the one it gets.**
A camera AOV is a single resource with a shape and a dtype. A sensor composite is a table of named
channels, and the individual channels are what carry shapes and dtypes. ``isComposite`` is the only
way to tell them apart, and a node written for one will not work on the other without that test.

.. _spg-composite-fields:

**What a composite carries.** ``inputs["X"]`` is a table rather than a resource:

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Field
     - Contents
   * - ``.isComposite``
     - ``true`` for a composite.
   * - ``.tensors[name]``
     - One channel, as a resource descriptor you bind as a buffer.
   * - ``.channelNames``
     - The channels this RenderVar actually carries, in order.
   * - ``.params[name]``
     - A scalar the sensor published alongside the channels, such as a lidar's ``maxPoints``.
       A value, not a resource, so it is read in the script and passed to the GPU like any other
       :doc:`value-input <values>`.
   * - ``.paramNames``
     - The parameters actually carried, in order.
   * - ``.status``
     - ``"empty"``, ``"partial"`` or ``"complete"``, as of the moment the launch script runs.
       Read the note below before branching on it.
   * - ``.name``, ``.doc``
     - The render output's own name and description, as the sensor published them.

.. _spg-composite-status:

``status`` **is not a test for "did the sensor produce data".** It reports what the render output
said at the moment the launch script ran, which is before the frame's GPU work. In the
:doc:`composite AOV example <../../examples/python_spg_composite_aov>` it reads ``"empty"`` on every
frame while the channels go on carrying a full sweep of some 26,000 returns.
A read of an earlier frame, ``:-N``, sees that frame as the
sensor filled it, status included: refer to :doc:`previous_frame`.

**Iterate the name lists rather than assuming.** ``channelNames`` and ``paramNames`` say what this
RenderVar carries, which can include channels the scene did not ask for and is not necessarily
everything the sensor can produce.

.. _spg-composite-counts:

**Bound the work by the count channel.** The point channels of an ``OmniLidar`` or ``OmniRadar``
point cloud are allocated for the worst case, and only the first ``Counts[0]`` entries hold a
return. The launch script sees descriptors rather
than data, so it cannot read that number: pass ``Counts`` to the GPU and apply the bound there.

**Mind the stride.** ``Coordinates`` is ``[3, Nmax]``, all the x values, then all the y, then
all the z. The step between runs is the allocated capacity, not the valid count.

Verify It Worked
----------------

Count what you consumed against what the sensor produced: the number of returns the node binned
has to equal ``Counts``, which varies from sweep to sweep. In the
:doc:`composite AOV example <../../examples/python_spg_composite_aov>`, the chart shows one bar per
box, at the range of the box's front face.

When It Goes Wrong
------------------

- Empty output with a valid scene: the sweep returned nothing. A lidar traced across the tick
  needs the motion BVH enabled or ``Counts`` comes back zero. ``Counts`` is what answers this;
  :ref:`status <spg-composite-status>` does not.
- The node's graph publishes nothing and the log names a channel: a channel or parameter was
  asked for under a name the composite does not carry. The message names the port, the name you
  used, the nearest match it found and everything available, and the graph stops.
- Plausible but wrong values: the stride was taken as the valid count rather than the capacity.
- The node's graph stops and the message names a channel after saying the node reads an earlier
  frame: the RenderVar is read with ``:-N``, and that channel is not a GPU buffer stored compactly,
  so SPG keeps no earlier frames of the composite.
- The node never runs, and the sensor logs that the ``PointCloud`` RenderVar requested no supported
  channels: list at least one channel the sensor supports.

Related
-------

:doc:`textures_buffers`, :doc:`products`, :doc:`../../examples/python_spg_composite_aov`
