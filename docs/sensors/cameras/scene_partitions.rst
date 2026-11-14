.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-cameras-scene-partitions:
.. _sensors-common-scene-partitions:

Scene Partitions
================

Scene partitions let cameras render separate environments from one stage,
while sharing unpartitioned geometry and lighting. Use them to simulate
independent robot environments without loading a separate stage for each one.
Partitioning is enabled by default in ovrtx. Named partition selection is
supported by Camera prims, including camera-based sensor models.
:ref:`Non-camera sensors <sensors-cameras-scene-partitions-non-camera-sensors>`
cannot select a named partition.

.. figure:: ../../img/sensors/common/camera-scene-partitions.avif
   :alt: Three matching camera views showing the left orange cube, right blue torus, and both objects
   :align: center
   :width: 100%

   *Three cameras at the same viewpoint render the orange cube, the blue
   torus, or both. All three views share the ground and studio lighting.*

Each :doc:`Camera prim <../cameras>` selects one partition. That selection
applies to every RenderProduct using the camera, including its tile in a
product that renders several cameras.

Creating scene partitions
-------------------------

Select a camera's partition with ``omni:scenePartition``. Assign geometry with
the ``primvars:omni:scenePartition`` token primvar. Primvars are inherited, so
you can assign an entire environment on its top-level Xform. A partition is
identified by its name: a camera and the geometry it should see carry the same
token.

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 46, 54
   :class: compact-table

   "``custom token omni:scenePartition``", "Author on a Camera to select the named partition that it renders."
   "``token primvars:omni:scenePartition``", "Author on geometry or an ancestor Xform to assign that content to a named partition."

Neither attribute has a schema-generated accessor. Author them using the
exact names and token types shown above.

With the default visibility settings:

- A camera sees geometry assigned to its selected partition.
- A camera does not see geometry assigned to another partition unless
  ``showAllPartitionsByDefault`` is enabled; see
  :ref:`Viewing all partitions <sensors-common-scene-partitions-render-settings>`.
- Unpartitioned geometry remains visible to every camera.
- A camera with a missing or empty selector sees only unpartitioned geometry.

:ref:`Viewing all partitions <sensors-common-scene-partitions-render-settings>`
changes these rules.

This excerpt from the example assigns the two objects to separate partitions
and selects them with the left and right cameras. The third camera has no
partition selector.

Both tabs author the same scene objects. Asset paths are relative to the
example directory; the Python snippet assumes an existing USD ``stage``.

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../examples/python/camera-scene-partitions/scene_partitions.usda
         :language: usda
         :start-after: # [snippet:doc-example-camera-scene-partitions]
         :end-before: # [/snippet:doc-example-camera-scene-partitions]
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-camera-scene-partitions-python]
         :end-before: # [/snippet:doc-camera-scene-partitions-python]
         :dedent:

.. _sensors-common-scene-partitions-render-settings:

Viewing all partitions
----------------------

A camera without a partition selector can render all partitions, for example
to provide an overview of several environments. Enable this with the following
scene-wide setting on the RenderSettings prim. The example uses
``/Render/OmniverseGlobalRenderSettings``; see :ref:`global render settings
<sensors-common-output-configuration-global-settings>` for how that prim is
selected.

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 55, 45
   :class: compact-table

   "``bool omni:rtx:scenePartitioning:showAllPartitionsByDefault = false``", "Allow cameras without a partition selector to render partitioned geometry as well as unpartitioned geometry."

``OmniRtxSettingsGlobalCommonAPI_1`` declares this setting. It also works as a
plain attribute without applying the schema, as in the example.

.. warning::

   This scene-wide setting also affects cameras with a partition selector:
   geometry from overlapping environments can appear in each other's camera
   views. Separate partition names do not preserve isolation when it is enabled.
   Leave it ``false`` when cameras must remain isolated. Cameras without a
   partition selector then see only unpartitioned geometry. Neural-reconstruction
   volumes are an exception: partition assignments do not isolate them with
   either value; see :ref:`Supported object types
   <sensors-common-scene-partitions-object-types>`.

Separating the environments' geometry in world space does not guarantee
isolation with this option enabled. The region a partition's camera can see
is sized using the largest partition extent along each axis, so geometry from
another environment can remain visible even when the environments do not overlap.
Large background meshes assigned to a partition can increase the separation
needed.

The example enables this setting so that the third camera sees both objects.

.. _sensors-cameras-scene-partitions-lighting:

Lighting
--------

Assign lights with ``primvars:omni:scenePartition`` on the light or an ancestor
Xform, just as for geometry. Partitioned lights illuminate their own
partition; unpartitioned lights provide shared lighting.

Dome lights use the following default policy:

- A partition with its own dome lights uses those domes.
- A partition without its own dome lights inherits the unpartitioned domes.
- An unpartitioned camera uses the unpartitioned domes.

The example's studio dome is unpartitioned, and neither object partition has
its own dome. Both therefore inherit the studio lighting without needing a
dome-light override. See :doc:`Dome Light <../../lights/dome_light>` for dome
properties.

.. _sensors-common-scene-partitions-object-types:

Supported object types
----------------------

Meshes, curves, points, OpenVDB volumes, and ParticleFields support
scene partitioning through ``primvars:omni:scenePartition``. Geometry instances
also carry their own partition assignment.

Partition bounds follow updated geometry bounds, including skinning and
displacement.

Neural-reconstruction volumes are not isolated by scene partitions. Assigning
a partition does not filter them from other cameras; their ordinary visibility
rules still apply. See :doc:`Limitations <../troubleshooting/limitations>`.

.. _sensors-cameras-scene-partitions-non-camera-sensors:

Non-camera sensors
------------------

``OmniLidar``, ``OmniRadar`` and ``OmniAcoustic`` prims do not use
``omni:scenePartition`` to select a partition. Authoring the attribute on one
of these prims does not isolate its measurements to the named environment.
Their rays use the rules for an unassigned partition:

.. list-table::
   :header-rows: 1
   :widths: 45 55
   :class: compact-table

   * - ``showAllPartitionsByDefault``
     - Geometry available to the sensor's rays
   * - ``false`` (default)
     - Unpartitioned geometry only. Partitioned geometry is excluded.
   * - ``true``
     - Unpartitioned geometry and all partitions at their world-space
       positions, without isolation between environments.

The setting is scene-wide and also affects cameras. Enabling it does not
provide independent lidar, radar or acoustic environments within one stage.

Related
-------

- :doc:`Python: Camera Scene Partitions <../../examples/python_camera_scene_partitions>` — the runnable example this page's excerpt comes from, three cameras from one viewpoint.
- :doc:`Output Configuration <../common/output_configuration>` — RenderProducts, RenderVars and where render settings are authored.
- :doc:`Sensor Configuration <../common/sensor_configuration>` — instantiating sensor prims and applying their schemas.
- :doc:`Loading USD <../../scene/loading_usd>` — loading the stage that carries the partitioned scene.
