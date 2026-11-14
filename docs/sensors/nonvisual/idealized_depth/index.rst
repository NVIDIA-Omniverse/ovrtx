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

.. _sensors-nonvisual-idealized-depth-index:
.. _sensors-nonvisual-idealized-depth:
.. _sensors-models-ids:

Idealized depth model
=====================

.. _sensors-nonvisual-idealized-depth-held-back:

.. note::

   Draft. The Idealized depth model has no output that ovrtx delivers yet, so
   this section is held back from the published documentation until it does.
   Its pages are written to the same standard, link out to the published pages
   and are linked from none of them; where they describe the output, they
   describe the semantics of the output to come.

This page is the overview of the Idealized depth model: what it simulates, what
it is for, what it leaves out by design, and where its attributes, tasks and
outputs are described. The model produces synthetic depth by ray tracing. Where
the other non-visual models reproduce the physical limitations of a device, this
one produces perfect depth measurements: an ideal sensor that measures the
distance to every surface it is pointed at, with no optical aberration, no
measurement uncertainty and no environmental interference.

.. _sensors-ids-idealized-on-purpose:

**That is a deliberate choice, not an unfinished one.** The
:doc:`Lidar generic core model <../lidar_core/index>`, the
:doc:`Radar generic wpmDmat model <../radar_wpm_dmat/index>` and the
:doc:`Acoustic generic wpm model <../acoustic_wpm/index>` exist to reproduce
what a real device would have measured: its beam shape, its dropped returns,
its noise. This model exists to answer a different question: what was actually
there. It is suited to work that needs ground-truth depth as a reference
baseline: validating an algorithm, generating a synthetic dataset, benchmarking
a sensor against the geometry it was pointed at. Results from it do not
transfer to a physically modeled sensor, and are not meant to. For depth as a
stereo camera would report it, with that camera's disparity noise, quantization
and holes, use the :doc:`Camera single-view stereo depth model
<../../visual/depth_camera/index>` instead; it reads a rendered view rather than
tracing rays of its own.

What it simulates
-----------------

You author an emitter set: a set of rays, each leaving an origin in a direction,
laid out as one of five shapes, from a spherical grid of angles around one point
to a planar grid of parallel rays. Each frame, the model fires every emitter at
once and traces each ray against the scene on the renderer's direct ray-tracing
path, the path all :doc:`Non-Visual Sensors <../index>` share. For each
ray it reports whether a surface was met and, if so, the distance from the ray's
origin to the first surface along it, together with a material identifier and
an object identifier for that surface; the object identifier names the object
only when some RenderProduct in the scene requests a stable-ID output, and
:doc:`outputs` says what each field holds and when. That is the whole model:
rays are generated from an emitter shape and report geometric hits.

The output is one entry per emitter, every frame, whether or not the ray hit
anything, so the entry count follows from the emitter attributes alone. An entry
is a measurement when its ``VALID`` flag is set, which the model sets exactly
when the ray found a surface. :doc:`outputs` describes the entries.

.. figure:: ../../../img/sensors/nonvisual/idealized_depth_point_cloud.avif
   :alt: A dense field of concentric rings of points on a square ground plane around a sensor marked by a white dot, with an empty circle directly below the sensor, and the face of a cube ahead that leaves a wedge without points on the plane behind it. Points are yellow near the sensor and turn orange, magenta and blue with distance against a color bar from 0 to 45 m.
   :align: center
   :width: 1000

   One frame of the Idealized depth model over a 60 m square ground plane and
   one cube, with the schema's default ``SPHERICAL`` emitter set: 400 rows by
   3600 columns, elevation -20 to 20 degrees and the full circle of azimuth, at
   0.1 degree spacing. Every ``VALID`` entry is drawn as one point, placed from
   its origin along its azimuth and elevation at the reported distance, and
   colored by that distance. The sensor, the white dot, sits 1 m above the
   plane, so the rows draw rings on it from 2.9 m outward, where the lowest row
   meets the ground, and none nearer. The cube's face returns the grid without
   a gap up to the top row, which crosses it below the cube's upper edge, and
   leaves the plane behind it without points. Entries whose ray met nothing are
   not drawn.

What you author
---------------

The model is instantiated as an ``OmniIDS`` prim with ``OmniSensorGenericIDSAPI``
applied; :doc:`attributes` gives the identification strings the schema sets. The
attributes live under ``omni:sensor:Core``, a namespace shared with the Lidar
generic core model (:ref:`The shared Core namespace
<sensors-nonvisual-idealized-depth-attributes-core-namespace>`).
:doc:`attributes` explains the attributes themselves: the emitter shape
``omni:sensor:Core:type`` selects, what each shape reads, and the defaults,
whose ray budget is not small; :doc:`Sensor API Schemas
<../../reference/schemas>` holds the generated tables. There is no emitter count
to author: the set follows from the attributes, and an emitter attribute edited
on a running sensor takes effect, as :doc:`attributes` describes.

No example in the ovrtx package uses this model. Authoring the prim, attaching a
RenderProduct and reading what a step delivers follow the pattern every sensor
shares, which :doc:`Your First Lidar Sensor <../../first_sensor>` walks through.

.. _sensors-nonvisual-idealized-depth-not-modeled:

What it does not model
----------------------

By design the model leaves out return strength, range limits of its own,
multiple returns, per-entry timing, noise and uncertainty, and atmospheric
attenuation. Each is an absence you can rely on; what each one fixes in the
output fields is stated once on :doc:`outputs`, in its section on the field
consequences of what is not modeled.

The range window is the renderer's. The prim has no near- or far-range
attribute, and the model sets no range window of its own: its rays are traced
over the renderer's default window of 5 cm to 10 km. A surface nearer than 5 cm
is passed through, one beyond 10 km is a miss, and within the window the first
surface the ray meets is what is reported.

The rays are instantaneous, the sensor is not: the output records the sensor's
pose at both ends of the frame window, and which pose the rays are traced from
depends on the renderer's :ref:`motion BVH <sensors-common-output-configuration-motion-bvh>` (:ref:`Pose across the frame
<sensors-nonvisual-idealized-depth-outputs-pose>`).

In this section
---------------

Read :doc:`attributes` when you author the prim: the shared ``omni:sensor:Core``
namespace, the defaults and the ray budget they imply, the five emitter shapes
and what each one reads, the prerequisites of the ``BOX`` and
``GRIDLESS_SPHERICAL`` shapes, and what changes on a running sensor. The emitter
group is the group that reshapes the output.

The :doc:`how-to pages <howto/index>` each solve one task. There is one so far,
choosing an emitter shape: size the ray budget, pick the shape for the geometry
you want sampled, author only the attributes that shape reads, and satisfy the
prerequisites of the two shapes that have them.

:doc:`outputs` is where you read what comes back: one entry per emitter,
spherical coordinates in the sensor's own frame placed from a per-entry origin,
the identity fields and the echoed emitter configuration, the field consequences
of what the model does not simulate, and the sensor's pose across the frame.

.. toctree::
   :maxdepth: 1

   attributes
   howto/index
   outputs

Related
-------

- :doc:`USD Attributes <attributes>` — the shared ``omni:sensor:Core`` namespace, the defaults and their ray budget, the five emitter shapes and what changes on a running sensor.
- :doc:`How-To <howto/index>` — choosing and sizing an emitter shape.
- :doc:`Outputs <outputs>` — one entry per emitter, the coordinates, identity and echoed configuration each frame carries, and the pose across the frame.
- :doc:`Your First Lidar Sensor <../../first_sensor>` — the authoring, rendering and reading pattern every sensor shares.
- :doc:`Sensor Configuration <../../common/sensor_configuration>` — prims, applied schemas and which model runs.
- :doc:`Output Configuration <../../common/output_configuration>` — RenderProducts, RenderVars, render settings and the motion BVH.
- :doc:`Sensor Outputs <../../common/sensor_outputs>` — the composite output, mapping what a step delivers and the ``VALID`` bit.
- :ref:`C API <c-api-sensor-types>` and :ref:`Python API <python-api-render-outputs>` — the C and Python definition of the output container.
- :doc:`Non-Visual Sensor Materials <../../../materials/nonvisual_sensor_materials>` — the two material systems, and how the non-visual material labels are authored and read back.
- :doc:`Runtime Parameter Updates <../../common/runtime_updates>` — what an edit on a running sensor does.
- :doc:`Glossary <../../reference/glossary>` — scan, sweep and the other terms that mean different things per model.
- :doc:`Lidar generic core model <../lidar_core/index>` — the physically modeled scanning lidar to compare against.
- :doc:`Radar generic wpmDmat model <../radar_wpm_dmat/index>` — the physically modeled automotive radar to compare against.
- :doc:`Acoustic generic wpm model <../acoustic_wpm/index>` — the physically modeled ultrasonic sensor to compare against.
- :doc:`Camera single-view stereo depth model <../../visual/depth_camera/index>` — depth as a stereo camera reports it, from a rendered view.
