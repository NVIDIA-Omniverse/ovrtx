:orphan:

.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-idealized-depth-howto-emitter-shape:

Choose an Emitter Shape
=======================

.. note::

   Draft. The Idealized depth model delivers no output in ovrtx yet, so this
   section is held back from the published documentation. The steps describe
   the model as it is implemented; the last step depends on an output that
   does not exist in ovrtx today.

This page walks you through choosing and sizing the emitter set of the
Idealized depth model. An *emitter* is one ray the model fires every frame.
The set is generated from a handful of ``omni:sensor:Core:*`` attributes, and
one token, ``omni:sensor:Core:type``, picks the shape that generates it. There
is no count to author: how many rays the sensor fires, and so how many entries
every frame delivers, follows from the shape and its parameters.
:doc:`USD Attributes <../attributes>` defines each attribute named here; this
page puts them in working order.

Step 1: size the ray budget
---------------------------

Every emitter is one traced ray and one output entry per frame, whether or not
the ray meets a surface, so the emitter count sets both the tracing work and
the size of every frame. Decide it first.

The schema defaults fire 1,440,000 rays per frame;
:ref:`Defaults and the ray budget <sensors-nonvisual-idealized-depth-attributes-defaults>`
on the attributes page writes them out and states what they cost. Multiply
rays per frame by ``omni:sensor:frameRate`` for rays per second;
:doc:`Sensor Scheduling <../../../common/multi_rate>` explains the
frame rate. Set the counts and the angular window to what your task needs
before the sensor first runs.

How the count follows from the attributes depends on the shape:

- ``SPHERICAL``, ``PLANAR`` and ``CYLINDRICAL`` fire ``numRows`` × ``numCols``
  rays, each axis stepping span ÷ count. The default grid samples every 0.1°
  both ways; a 64 × 1024 grid over the default 360° by ±20° window samples
  every 0.625° in elevation and 0.35° in azimuth with 65,536 rays.
- ``GRIDLESS_SPHERICAL`` derives its count from the angle that ``elementSize``
  subtends at the distance ``radius``: the rows are the elevation window
  divided by that angle, and each row holds the azimuth window divided by a
  step that widens as the row moves away from the horizon. An element of
  0.1 m at 10 m is a 0.57° step; over ±20° and 360° that is 70 rows and about
  43,000 rays. Doubling the element size roughly quarters the count.
- ``BOX`` samples the six faces of the box at ``elementSize`` spacing per axis,
  so each face holds roughly (extent ÷ spacing) points along each of its two
  axes and the count grows with the square of the sampling density. The
  schema's default box, 20 m on a side sampled every 0.2 m in x and y and
  every 0.5 m in z, fires 36,400 rays per frame.

:ref:`The sampling rules <sensors-nonvisual-idealized-depth-attributes-sampling>`
on the attributes page state where each grid starts and stops and in which
frame the angles and origins are counted.

Step 2: pick the shape
----------------------

Pick the shape for the geometry you want sampled. Angles are counted in the
sensor's frame, azimuth from straight ahead and elevation from the horizontal
plane, positive upward;
:doc:`Sensor Configuration <../../../common/sensor_configuration>` explains how
the prim's orientation sets where straight ahead is. The
:ref:`shape table <sensors-nonvisual-idealized-depth-attributes-emitter-shapes>`
on the attributes page defines each shape in full; in brief:

- ``SPHERICAL``, the default: a uniform angular grid from one origin, rows are
  elevation and columns are azimuth. The spinning-lidar view of a scene.
- ``PLANAR``: a uniform grid on a plane, emitting parallel rays. The origins are
  spread over the sensor's horizontal plane and every ray points straight down
  in the sensor's frame: an orthographic depth map of whatever lies below the
  plane. Aim it by rotating the prim.
- ``CYLINDRICAL``: a stack of horizontal rings, each row one ring of rays raised
  above the previous one. A horizontal sweep over the azimuth window, repeated
  at several heights.
- ``GRIDLESS_SPHERICAL``: spherical sampling whose ray spacing does not change
  with elevation, for the same spatial resolution at every elevation at a ray
  count that follows from the field of view.
- ``BOX``: rays from one origin aimed at evenly spaced points on the six faces
  of an axis-aligned box, a fixed spatial spacing on the faces rather than a
  fixed angular step: a surface nearer than a face is sampled more densely,
  one farther away more sparsely.

Step 3: author what the shape reads
-----------------------------------

Author only the attributes your shape reads; the others are ignored for that
shape, and the row and column units change meaning with it, degrees for the
angular shapes and meters for the spatial ones. The
:ref:`shape table <sensors-nonvisual-idealized-depth-attributes-emitter-shapes>`
lists what each shape reads. Two entries are easy to misread: ``CYLINDRICAL``
reads ``maxRowUnit`` as its height and ignores ``minRowUnit``, and
``elementSize`` is per-axis spacing for ``BOX`` but one scalar, its first
component, for ``GRIDLESS_SPHERICAL``;
:ref:`One attribute, two meanings <sensors-nonvisual-idealized-depth-attributes-element-size>`
has the detail.

Step 4: satisfy the prerequisites
---------------------------------

- ``GRIDLESS_SPHERICAL`` needs a positive, finite ``radius`` that you author
  yourself, together with the shape or before switching a running sensor to
  it; the schema default does not supply one.
  :ref:`The GRIDLESS_SPHERICAL shape <sensors-nonvisual-idealized-depth-attributes-gridless-radius>`
  on the attributes page says what the radius means. A ``GRIDLESS_SPHERICAL``
  prim with its radius authored beside the shape, 0.1 m elements at 10 m over
  the default window:

  .. code-block:: usda

      def OmniIDS "depth_sensor" (
          prepend apiSchemas = ["OmniSensorGenericIDSAPI"]
      )
      {
          token omni:sensor:Core:type = "GRIDLESS_SPHERICAL"
          float3 omni:sensor:Core:elementSize = (0.1, 0.1, 0.1)
          float omni:sensor:Core:radius = 10.0
          float omni:sensor:Core:minRowUnit = -20.0
          float omni:sensor:Core:maxRowUnit = 20.0
          float omni:sensor:Core:minColUnit = 0.0
          float omni:sensor:Core:maxColUnit = 360.0
      }

- ``BOX`` needs all three components of ``elementSize`` positive and the
  corners ``bottomLeft`` and ``topRight`` in order; the schema defaults comply.
  The box requirements are checked at creation and on every edit;
  :ref:`The BOX shape <sensors-nonvisual-idealized-depth-attributes-box-spacing>`
  on the attributes page states them.
- The grid shapes need at least one row and one column; a grid without rays is
  accepted but produces nothing.

Every emitter attribute takes a live edit, and a frame already in flight
finishes with the set it started with; the attributes page's
:ref:`Runtime updates <sensors-nonvisual-idealized-depth-attributes-runtime-updates>`
section has the details.

Step 5: confirm the shape
-------------------------

.. note::

   Draft. This step applies once the model has an ovrtx output.

Every frame delivers one entry per emitter, and the entry count is the emitter
count of the configuration the frame was traced with, so the first frame
confirms your arithmetic: compare the delivered count with ``numRows`` ×
``numCols`` for a grid shape, or with the estimate from step 1 for the derived
shapes. The frame also echoes the emitter configuration it was traced with
(shape, counts, units, origin, element size and radius), so a grid or gridless
frame can be matched to the configuration that produced it; a ``BOX``'s
corners and per-axis spacing are not echoed. :doc:`Outputs <../outputs>`
describes the entries and the echoed configuration.

Related
-------

- :doc:`USD Attributes <../attributes>` — the emitter attributes, the five-shape table and the rules of a live edit.
- :doc:`Outputs <../outputs>` — one entry per emitter, the per-entry angles and origin, the echoed configuration.
- :doc:`Idealized depth model <../index>` — what the model is for and what it does not model.
- :doc:`How-To <index>` — the hub of this model's procedures.
- :doc:`Sensor Configuration <../../../common/sensor_configuration>` — the prim's orientation, the output frame and the shared attributes.
- :doc:`Sensor Scheduling <../../../common/multi_rate>` — ``omni:sensor:frameRate`` and how often a frame is scheduled.
- :doc:`Runtime Parameter Updates <../../../common/runtime_updates>` — what happens to an edit on a running sensor.
- :doc:`Sensor API Schemas <../../../reference/schemas>` — the generated table of ``OmniSensorGenericIDSAPI``.
