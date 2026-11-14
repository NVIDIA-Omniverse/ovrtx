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

.. _sensors-nonvisual-idealized-depth-outputs:

Outputs
=======

.. note::

   Draft. The Idealized depth model has no output that ovrtx delivers yet, so
   this section is held back from the published documentation until it does.
   This page describes what the model computes for every frame and every
   entry, written as the contract of a future composite output: the tensor and
   param names below are provisional, the semantics are not.

This page explains what the Idealized depth model reports: how many entries a
frame holds, where each entry's measurement is and in what unit, which identity
and configuration the frame carries, which fields are fixed because the model
does not simulate the effect behind them, and how the sensor's pose is recorded
across the frame. The model is deliberately not a physical sensor: rays are
generated from an emitter shape and report geometric hits, so reading its
output is mostly knowing which entry belongs to which ray. How you map and read
a composite output in general is on :doc:`Sensor Outputs
<../../common/sensor_outputs>`; the field definitions of the container are on
:ref:`C API <c-api-sensor-types>` and :ref:`Python API <python-api-render-outputs>`.

.. _sensors-nonvisual-idealized-depth-outputs-entries:

One entry per emitter
---------------------

An *emitter* is one ray the model fires every frame, from an origin in a
direction; :doc:`USD Attributes <attributes>` explains how the emitter set is
generated from ``omni:sensor:Core:type`` and the attributes that shape reads.
**There is one entry per emitter, every frame, whether or not the ray hit
anything.** The entry count is the emitter count of the configuration the frame
was traced with. It is delivered with every frame, and it changes only when an
emitter attribute does; what a live edit does to a frame already in flight is on
:doc:`USD Attributes <attributes>` under "Runtime updates", and :doc:`Runtime
Parameter Updates <../../common/runtime_updates>` has the rules every model
shares. Bound the read by that count first, as :ref:`Delivered entry count <sensors-common-sensor-outputs-counts-bound>` describes for every
variable-size output, then filter.

**An entry is a measurement only when its valid flag is set.** The model sets
the ``VALID`` bit exactly when the ray found a surface inside the renderer's
range window (the :doc:`Overview <index>` lists the window with the other
limits), and it sets no other flag bit. Test the bit as :ref:`Checking validity <sensors-common-sensor-outputs-valid-bit>` describes,
and do not read a non-``VALID`` entry's distance, object identifier or material
identifier as a statement about the scene: the ray hit nothing, and those fields
hold no measurement there.

**Entries are ordered the way the emitter set was generated.** For the three
grid shapes, ``SPHERICAL``, ``PLANAR`` and ``CYLINDRICAL``, the entry at index
``r × numCols + c`` belongs to row ``r`` and column ``c``, rows counted upward
(from ``minRowUnit`` for ``SPHERICAL`` and ``PLANAR``, from the origin's height
for ``CYLINDRICAL``, which does not read ``minRowUnit``) and columns from
``minColUnit`` upward; ``GRIDLESS_SPHERICAL`` delivers its rows one after the
other, each with its own column count, and ``BOX`` one face after the other.
Whatever the shape, each entry carries its own azimuth, elevation and origin, so
the position in the list is never needed to know where a ray went.

.. _sensors-nonvisual-idealized-depth-outputs-coordinates:

Coordinates
-----------

**Coordinates are spherical and in the sensor's own frame**, both fixed by the
model rather than authored: this prim has no coordinate-representation or
frame-of-reference attribute, and every frame reports spherical coordinates in
the ``SENSOR`` frame of reference (``coordsType`` ``1`` and ``frameOfReference``
``0`` in the shared param vocabulary). The sensor frame is the ISO 8855 frame
that :ref:`The sensor frame <sensors-common-sensor-outputs-sensor-frame>`
defines once for every ``SENSOR``-frame output, and :ref:`Orienting the prim
<sensors-common-sensor-configuration-orientation>` says how the prim's own axes
map onto it.

The three components of an entry are, in this order:

- the emitter's **azimuth** in degrees,
- the emitter's **elevation** in degrees, and
- the **distance** from the ray's origin to the hit point, in meters.

The two angles are the direction the emitter was generated with. They are
constant per emitter for as long as the emitter attributes are unchanged, and
they are filled on every entry, hit or not; only the distance is a measurement.

**A hit is placed from the entry's own origin, not from the sensor's.** Every
entry also carries the origin its ray left from, as a position in the sensor
frame in meters, and the hit point lies at that origin plus the distance along
the direction the two angles name. For ``SPHERICAL``, ``GRIDLESS_SPHERICAL`` and
``BOX`` every origin is the authored ``omni:sensor:Core:origin``, so angles and
distance alone place the hit. For ``PLANAR`` and ``CYLINDRICAL`` the origins are
spread out and the angles alone do not: every ``PLANAR`` entry reports azimuth
``0`` and elevation ``-90``, a ray pointing straight down in the sensor frame
from its own point on the plane, and every ``CYLINDRICAL`` entry reports
elevation ``0`` from an origin raised to its ring's height. Add the origin
before you place a point from any shape; it costs nothing on the shapes that
share one.

**A scan is an instant, not a sweep.** Every ray leaves at the start of the
frame's time window, so the entries of one frame describe the scene at one
instant and nothing needs deskewing; the :doc:`Glossary
<../../reference/glossary>` keeps the distinction between a scan and a sweep.

.. _sensors-nonvisual-idealized-depth-outputs-distance-unit:
.. _sensors-ids-distance-unit:

Distance is in meters
^^^^^^^^^^^^^^^^^^^^^

The distance is in meters whatever the stage's ``metersPerUnit``, like the
distance component of the lidar and radar point clouds and like this model's
per-entry origins and recorded poses. On a stage whose ``metersPerUnit`` is not
1, do not scale the distance by the stage unit; convert the geometry you compare
it with instead.

.. _sensors-nonvisual-idealized-depth-outputs-identity:

Identity and the echoed configuration
-------------------------------------

**Every entry carries two fields about what its ray hit, filled whether or not
you ask for them and with no attribute to turn them off.** The two fields:

- An **object identifier**, the renderer's 128-bit stable identifier of the hit
  object, filled under the same conditions as the Lidar generic core model's
  ``ObjectId`` (:ref:`sensors-nonvisual-lidar-core-outputs-object-id`).
- A **material identifier**, the non-visual material of the hit surface encoded
  as one number: the same value the Lidar generic core model's ``MaterialId``
  channel carries. That model's Outputs page says how to decode it
  (:ref:`sensors-nonvisual-lidar-core-outputs-material-id`).

On an entry without the ``VALID`` flag the ray hit nothing and no identity was
written, so what those two fields hold there is not meaningful.

.. _sensors-nonvisual-idealized-depth-outputs-echoed-configuration:

**Every frame echoes the emitter configuration it was traced with**, so a frame
can always be matched to the configuration that produced it, including the
frame that finished with the previous set after an edit. The echo holds, with
provisional param names:

.. list-table::
   :header-rows: 1
   :widths: 30 14 56

   * - Param (provisional)
     - Type
     - Value
   * - ``emitterType``
     - ``uint32``
     - The shape: ``0`` ``SPHERICAL``, ``1`` ``PLANAR``, ``2`` ``CYLINDRICAL``,
       ``3`` ``GRIDLESS_SPHERICAL``, ``4`` ``BOX``.
   * - ``numRows``, ``numCols``
     - ``uint32``
     - The row and column counts as authored. ``GRIDLESS_SPHERICAL`` and ``BOX``
       echo them as authored too; their entry counts follow from the other
       attributes instead.
   * - ``minColUnit``, ``maxColUnit``, ``minRowUnit``, ``maxRowUnit``
     - ``float32``
     - The column and row window as authored, each in the unit the chosen shape
       gives it, degrees or meters; the shape table on :doc:`USD Attributes
       <attributes>` lists them per shape (``CYLINDRICAL``, for example, echoes
       an azimuth window in degrees and a height in meters).
   * - ``origin``
     - ``float32`` ``[3]``
     - The authored ``omni:sensor:Core:origin``, in meters in the sensor frame.
   * - ``elementSize``
     - ``float32``
     - One scalar, the first component of the authored ``elementSize``, which
       is the value ``GRIDLESS_SPHERICAL`` reads. The per-axis spacing a ``BOX``
       reads is not echoed, and neither are the box corners.
   * - ``radius``
     - ``float32``
     - The distance in meters at which ``elementSize`` is defined.

The frame also carries the params the non-visual point clouds share (:ref:`the
shared params <sensors-common-sensor-outputs-shared-params>`), with this
model's meanings: ``frameId`` is the model's frame counter, ``timestampNs``
stamps the start of the frame's time window, ``modality`` is ``4``,
``coordsType`` is ``1`` and ``frameOfReference`` is ``0`` on every frame, the
six frame-start and frame-end params are the poses and timestamps described
under :ref:`Pose across the frame
<sensors-nonvisual-idealized-depth-outputs-pose>`, and ``maxPoints`` is the
capacity of the per-entry tensors, as :ref:`Allocated capacity <sensors-common-sensor-outputs-capacity>` explains for every variable-size
output. This model fills no ``modelToAppTransform``: the param holds no
transform, not even an identity, so do not apply it; the entries are already in
the sensor frame. The two lidar-only params, ``motionCompensationState`` and
``compactionType``, are not published.

.. _sensors-nonvisual-idealized-depth-outputs-velocities:
.. _sensors-ids-velocities:

**The output carries no per-entry velocity.** An entry says where a surface was,
not how it moved; a consumer that needs the motion of what was hit compares
frames, or uses a model that reports it, such as the ``Velocity`` channel of the
:doc:`Lidar generic core model <../lidar_core/outputs>`.

.. _sensors-nonvisual-idealized-depth-outputs-shaping-attributes:

**Which attributes shape the output.** The emitter group alone:
``omni:sensor:Core:type`` and the attributes the chosen shape reads set the entry
count, every entry's fixed azimuth, elevation and origin, the order of the
entries and the echoed configuration; :doc:`USD Attributes <attributes>` defines
them and :doc:`Choose an Emitter Shape <howto/emitter_shape>` puts them in
working order. ``omni:sensor:frameRate`` sets how often a frame is produced
(:doc:`Sensor Scheduling <../../common/multi_rate>`). No attribute
selects the coordinate representation, the frame of reference or the fields a
frame carries, and the model reads no channel list from its RenderVar: every
field on this page arrives with every frame.

.. _sensors-nonvisual-idealized-depth-outputs-absences:

Field consequences of what is not modeled
-----------------------------------------

The :doc:`Overview <index>` lists what the model leaves out by design: return
strength, range limits of its own, multiple returns, per-entry timing, noise and
atmospheric attenuation. Each absence fixes a field of the output, and you can
rely on the fixed value:

- **The per-entry scalar that carries a lidar's return strength is zero** for
  every entry, every frame, wherever the composite output carries one: this
  model has no reflectance, intensity or power to put in it. A surface either
  was hit or was not, and the ``VALID`` flag is the whole answer.
- **There is no echo index**, because one ray produces at most one entry: the
  first surface the ray meets inside the range window is reported, nothing
  behind it.
- **Every entry's time offset is zero.** All rays leave at the start of the
  frame's time window, so the frame's start timestamp is the time of every
  entry.
- **Atmospheric attenuation removes no entry.** The ``VALID`` flag is set
  whenever the ray met a surface inside the range window, whatever the distance
  to it.
- **The distance is the traced distance, unmodified**: no range error, no
  angular error and no dropped returns.

.. _sensors-nonvisual-idealized-depth-outputs-pose:

Pose across the frame
---------------------

**The sensor's pose is tracked across the frame even though the rays are not.**
A frame's trace spans a time window, and the output records the sensor's
position in meters and its orientation as a quaternion at both ends of it, each
with its timestamp: the frame-start pose at the window's start and the
frame-end pose at its end (how a step result places each frame's capture in time
is under :ref:`sensors-common-sensor-outputs-frames`). It is the rays that are
instantaneous, not the sensor: all of them leave at the window's start, so a
moving sensor's entries are measured from the frame-start pose, and the
frame-end pose tells you where the sensor was when the frame closed.

Measuring from that pose needs the renderer's :ref:`motion BVH <sensors-common-output-configuration-motion-bvh>`, with ``AUTO`` or ``ENABLE``,
a choice made when the renderer is created. With it, every ray is traced from
the sensor's pose at the window's start against the scene as it is at that
instant. Without it, every ray is traced from the sensor's pose at the end of
the window against a scene that does not move, and both recorded poses are that
end pose; only the two timestamps mark the window's start and end.

Related
-------

- :doc:`Idealized depth model <index>` — what the model is for, what it leaves out by design and why the section is held back.
- :doc:`USD Attributes <attributes>` — the emitter shapes and the attributes each reads, the defaults and what changes on a running sensor.
- :doc:`How-To <howto/index>` — choosing and sizing an emitter shape.
- :doc:`Sensor Outputs <../../common/sensor_outputs>` — mapping an output, the sensor frame and component order, bounding a read, the shared params.
- :ref:`C API <c-api-sensor-types>` and :ref:`Python API <python-api-render-outputs>` — the C and Python definition of the container.
- :doc:`Non-Visual Sensor Materials <../../../materials/nonvisual_sensor_materials>` — the two material systems, and how the non-visual material labels are authored and read back.
- :doc:`Output Configuration <../../common/output_configuration>` — the RenderProduct and RenderVar that request an output, and the motion BVH.
- :doc:`Sensor Scheduling <../../common/multi_rate>` — ``omni:sensor:frameRate`` and when frames are delivered.
