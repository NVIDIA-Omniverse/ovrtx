.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-visual-index:

Visual Sensors
==============

This section describes two post-processing pipelines that simulate camera
sensor outputs from renderer outputs. Each model reads AOVs from a
RenderProduct and publishes its results on that same RenderProduct. The models
that trace the scene to simulate non-visual measurements are under
:doc:`Non-Visual Sensors <../nonvisual/index>`.

.. figure:: ../../img/sensors/visual/visual_sensors_strip.avif
   :align: center
   :alt: Robot lineup shown as rendered color, camera-core ISP output, and a depth visualization.
   :width: 100%

   The robot lineup from three cameras at the same pose. Left: rendered
   ``LdrColor``. Center: ``OmniCameraSensorPostIsp`` with a sample camera
   profile. Right: ``DepthSensorOutputVisualization``, black where no
   measurement is reported.

The :doc:`Cameras <../cameras>` section and its
:doc:`Outputs <../cameras/outputs>` page describe the render modes and the AOVs
a camera product can deliver, such as
``LdrColor``, ``HdrColor``, distance and segmentation. This section describes
post-processing of those AOVs. Each model's Outputs page lists its required
inputs. Apply ``OmniSensorGenericCameraCoreAPI`` to the ``Camera`` prim for the
Camera generic core model, and ``OmniSensorGenericDepthSensorSingleViewAPI`` to
the ``Camera`` prim for the Camera single-view stereo depth model. Both models
use the existing camera and product prims. A camera carries one of the two
schemas, never both; requesting a model's outputs on the camera's RenderProduct
runs its pipeline, and the schema supplies the parameters.
:doc:`Sensor Configuration <../common/sensor_configuration>` states that rule
under :ref:`Creating a sensor <sensors-common-sensor-configuration-model>`, and
:doc:`Output Configuration <../common/output_configuration>` how a RenderProduct
requests outputs.

Each model has a directory of its own below. Its overview says what the model
simulates and in what vocabulary, where it begins relative to the rendered view
and what it leaves to other parts of ovrtx; under it hang the USD attributes the
model answers to, one how-to page per task, and an Outputs page that says what
each output holds and which attributes shape it. Read the overview first, then
the others as you need them.

The models
----------

The **Camera generic core model**, a ``Camera`` prim with
``OmniSensorGenericCameraCoreAPI`` applied, is for consumers that expect frames
the way a camera sensor sends them, RAW or processed by an image signal
processor (ISP), rather than the renderer's clean output. It delivers the image
at each stage of the sensor and ISP chain, so a perception stack or an ISP under
test can be fed from a simulated scene. Start with the
:doc:`overview <camera_core/index>`; its :doc:`Outputs <camera_core/outputs>`
page lists the outputs each stage publishes.

The **Camera single-view stereo depth model**, a ``Camera`` prim with
``OmniSensorGenericDepthSensorSingleViewAPI`` applied, is for consumers that expect a
stereo depth camera's output, with occlusion holes, disparity noise and
quantization. From one rendered view it delivers a depth image and a per-pixel
point cloud. The :doc:`overview <depth_camera/index>` describes the model;
:doc:`Outputs <depth_camera/outputs>` lists its outputs.

The two models are independent pipelines that can share one RenderProduct. Which
camera outputs each one reads is stated on its own pages:
:ref:`Where the model begins <sensors-visual-camera-core-boundary>` for the
Camera generic core model and
:ref:`Inputs <sensors-visual-depth-camera-outputs-inputs>` for the Camera
single-view stereo depth model.

.. toctree::
   :maxdepth: 1

   camera_core/index
   depth_camera/index

Related
-------

- :doc:`Cameras <../cameras>` — the section that makes the picture these models start from.
- :doc:`Cameras: Outputs <../cameras/outputs>` — every AOV per render mode, the distance outputs among them.
- :doc:`Render Modes <../cameras/render_modes>` — the render modes behind the input image and what each one delivers.
- :doc:`Sensor Outputs <../common/sensor_outputs>` — mapping an output and reading it back.
- :doc:`Glossary <../reference/glossary>` — AOV and the other terms every sensor page shares, defined once.
