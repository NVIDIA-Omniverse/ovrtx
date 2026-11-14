.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-lidar-wpm-howto-tile-lidars:
.. _sensors-tiled-lidar-wpm:

Tile Lidars
===========

Tiling combines several Lidar generic wpm model sensors into one RenderProduct
and one aggregate point cloud. It reduces overhead when the sensors can share
a profile and firing schedule. The first sensor in ``rel camera`` supplies
the profile; each sensor retains its own transform and motion.

The Lidar generic core model requires one RenderProduct per sensor. For camera tiling,
see :ref:`Output Configuration <sensors-common-output-configuration-rel-camera>`.

Before you start. Start with a working wpm lidar using :doc:`firing_pattern` and
:doc:`../attributes`. The :doc:`first-sensor example <../../../first_sensor>`
uses a core lidar but demonstrates the shared scene components; see
:doc:`../../../common/output_configuration` for product wiring.
For separate point clouds, use :ref:`one product per sensor
<sensors-common-output-configuration-independent-products>` instead of tiling.

.. _sensors-nonvisual-lidar-wpm-howto-tile-lidars-shape:

RenderProduct configuration
---------------------------

List the sensor prims in one RenderProduct's ``camera`` relationship and
request ``PointCloud``. Each prim uses ``OmniSensorGenericLidarWpmAPI`` and
its own transform. Each requested point cloud contains every tile in
relationship order.

In compact output, tile *t* occupies
``[TilePointOffsets[t], TilePointOffsets[t + 1])`` in each point channel.
Dense output uses :ref:`stride params
<sensors-nonvisual-lidar-wpm-outputs-dense>` instead. See :doc:`../outputs`
for both layouts and the per-tile pose parameters.

The following fragment authors two tiles and one product. Tile zero carries
the firing pattern and a subsampling factor of 2, which the next sections
explain; tile one applies the same API schema and authors nothing but its
placement, eight meters to the side of tile zero and one meter higher. The
stage is authored in meters (``metersPerUnit = 1``); its scene geometry and
materials are defined elsewhere.

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../../tests/docs/usd/data/nonvisual/lidar_wpm_howto_tile_lidars_1.usda
         :language: usda
         :start-after: # [snippet:doc-nonvisual-lidar-wpm-howto-tile-lidars-1]
         :end-before: # [/snippet:doc-nonvisual-lidar-wpm-howto-tile-lidars-1]

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../../tests/docs/usd/test_nonvisual_authoring.py
         :language: python
         :start-after: # [snippet:doc-nonvisual-lidar-wpm-howto-tile-lidars-1-python]
         :end-before: # [/snippet:doc-nonvisual-lidar-wpm-howto-tile-lidars-1-python]
         :dedent:

.. _sensors-nonvisual-lidar-wpm-howto-tile-lidars-tile-zero:
.. _sensors-lidar-wpm-tile-homogeneity:

Shared profile
--------------

The first sensor in ``rel camera``, tile zero, supplies the scan schedule,
firing patterns, return processing, subsampling and output settings for every
tile. Other tiles' model attributes are ignored, so they can omit those
attributes, including firing-pattern arrays. Apply runtime parameter edits to
tile zero; see :doc:`runtime_updates`. The aggregate uses one profile and
schedule, with points grouped by tile.

Each tile contributes its own transform and motion. Output params report its
start and end poses; both transforms must be finite. Motion effects require
:ref:`motion BVH <sensors-common-output-configuration-motion-bvh>`, selected
at renderer creation. See :ref:`output motion behavior
<sensors-nonvisual-lidar-wpm-outputs-motion>` for the enabled and disabled cases.

.. _sensors-nonvisual-lidar-wpm-howto-tile-lidars-thin:

Subsampling
-----------

Several tiles cost several sensors' worth of tracing. The attribute
``uint omni:sensor:LidarWpm:tiledSubSampling`` reduces the number of emitter
rows traced by every tile without shortening the scan. Its semantics, the selection rule included, are described on
:ref:`Tiling and subsampling
<sensors-nonvisual-lidar-wpm-attributes-tiled-subsampling>`; this section is
the how-to.

1. Author ``omni:sensor:LidarWpm:tiledSubSampling = n`` on tile zero, with *n*
   above 1; leave it at ``0``, the default, or at ``1`` when every tile should
   trace at full fidelity.
2. Choose a factor that leaves every firing pattern, or the whole rotary scan,
   at least one emitter row; a factor that would not is refused (:ref:`Tiling
   and subsampling <sensors-nonvisual-lidar-wpm-attributes-tiled-subsampling>`).

In the fragment above, the pattern has two emitter rows and the factor is 2,
so each tile fires one row per scan instead of two.

.. _sensors-nonvisual-lidar-wpm-howto-tile-lidars-order:
.. _sensors-lidar-wpm-tile-order:

Keep tile order stable
----------------------

The model knows the tiles only by their position in ``rel camera``. That
position decides which range of the point cloud a tile fills, which entry of
``TilePointCounts`` is its own and which row of the per-tile pose params
describes it. Adding or removing a tile changes the aggregate's dimensions,
so it restarts the aggregate and discards a scan in progress. Keep the order
fixed while a scan is in progress, and change it only between scans.

.. _sensors-nonvisual-lidar-wpm-howto-tile-lidars-verify:

Verification
------------

Check the following in the step's ``PointCloud`` output. The tensors and params named here are defined on the :doc:`Outputs
page <../outputs>`; mapping an output and reading its params is on
:ref:`Sensor Outputs <sensors-common-sensor-outputs-params>`.

1. The ``tileCount`` param equals the number of sensors in ``rel camera``. A
   single sensor is an aggregate of one tile, so an untiled product reports
   ``1``.
2. In compact output, the default, ``TilePointCounts`` holds one entry per
   tile, in ``rel camera`` order, and the entries sum to ``Counts[0]``. In the
   fragment above, a scan in which each tile sees one surface gives
   ``TilePointCounts`` of ``[1, 1]``, ``TilePointOffsets`` of ``[0, 1, 2]``
   and a ``Counts[0]`` of ``2``.
3. The ``receiversPerTile`` param is the number of emitter rows the schedule
   keeps for one sensor after subsampling, the same for every tile: ``1`` in
   the fragment, two rows thinned by a factor of 2.
4. The ``tileFrameStartPosM`` param holds one position per tile, in meters, in
   ``rel camera`` order. On a static scene it reports each tile's authored
   position, ``(0, -4, 1)`` and ``(0, 4, 2)`` for the fragment, whose stage is
   authored in meters; when the tiles move, it reports each tile's pose at the
   start of the captured frame and ``tileFrameEndPosM`` its pose at the end.
5. The points in a tile's range come from where that tile stands: each tile
   reports its own surroundings, at its own range and height.

.. _sensors-nonvisual-lidar-wpm-howto-tile-lidars-symptoms:

Potential issues
----------------

- **Subsampling or another setting has no effect.** Check that the attribute
  is authored on the first sensor in ``rel camera`` (tile zero). Only that
  sensor's model attributes apply to the tiled product. To enable subsampling,
  set ``omni:sensor:LidarWpm:tiledSubSampling`` above ``1`` on tile zero;
  see :ref:`tile configuration
  <sensors-nonvisual-lidar-wpm-howto-tile-lidars-tile-zero>`.
- **The output stops after a tile was added.** The new tile's transform is not
  finite; the reason is logged as an error. Give the prim a finite transform,
  at both ends of the captured frame if it moves.
- **Two tiles return identical ranges.** They were left at the same transform.
  Each tile is its own prim and needs its own placement. Refer to
  :ref:`Incorrect coordinates or units <sensors-troubleshooting-symptoms-wrong-place>`.
- **Fewer points than expected on every tile.** A subsampling factor above
  ``1`` is set on tile zero and reduces the emitter rows traced by every tile.
  Set ``omni:sensor:LidarWpm:tiledSubSampling`` to ``0`` or ``1`` on tile zero
  to disable subsampling. Refer to
  :ref:`Fewer points or pixels than expected <sensors-troubleshooting-symptoms-fewer>`.
- **Changing tiledSubSampling at runtime has no effect.** A value that leaves
  a firing pattern, or the whole rotary scan, with no emitter rows is rejected.
  The last valid profile remains active. Reduce ``tiledSubSampling``; see
  :doc:`Retune the Sensor While It Runs <runtime_updates>`.
- **Setting tiledSubSampling has no effect.** Check that the full attribute
  name is ``omni:sensor:LidarWpm:tiledSubSampling`` and that it is authored on
  tile zero. USD attribute names are case-sensitive, including the capital
  ``S`` in ``SubSampling``. See
  :ref:`Runtime edits have no effect <sensors-troubleshooting-symptoms-retune-namespace>`.
- **Runtime and memory grow with every tile.** Each tile adds its transmitter
  and receiver workload and its share of the point cloud. Increasing ``tiledSubSampling`` on
  tile zero reduces the number of emitter rows traced and their storage. Refer to
  :ref:`Performance problems <sensors-troubleshooting-symptoms-slow>`.

The :doc:`Symptom Index <../../../troubleshooting/symptoms>` collects the
configuration symptoms of every model.

Related
-------

- :doc:`Outputs <../outputs>` — the tile-major point cloud, ``TilePointCounts``, ``TilePointOffsets``, ``tileCount`` and the per-tile pose params.
- :doc:`USD Attributes <../attributes>` — ``tiledSubSampling`` and the other attributes tile zero supplies.
- :doc:`Retune the Sensor While It Runs <runtime_updates>` — live edits on tile zero, and what a rejected edit leaves in place.
- :doc:`Sensor Outputs <../../../common/sensor_outputs>` — mapping an output, reading params and bounding a read by ``Counts``.
- :doc:`USD Attributes, Lidar generic core model <../../lidar_core/attributes>` — the model that does not tile: one RenderProduct per sensor.
