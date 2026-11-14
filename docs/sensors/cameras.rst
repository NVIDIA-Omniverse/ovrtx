.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-cameras-tutorials:
.. _sensors-cameras-howto:
.. _sensors-cameras-index:

.. _sensors-cameras:

Cameras
========

A camera renders color images and scene data from a USD Camera prim. A
:doc:`RenderProduct <common/output_configuration>` selects the camera, resolution
and outputs to capture.

Camera outputs
--------------

Camera outputs include a tone-mapped image for display and a linear HDR image for
image processing and compositing. The same view can also produce surface normals,
distances, motion, segmentation, bounding boxes and object identifiers.
:doc:`Camera Outputs <cameras/outputs>` lists the available outputs, their formats
and units; :doc:`Decoding camera outputs <cameras/decoding_outputs>` shows how to
request and read them in Python and C.

.. figure:: ../img/sensors/camera/camera_outputs_hero.avif
   :alt: Robot lineup shown as color, surface normals, distance and semantic segmentation in a two-by-two grid
   :align: center
   :width: 1288

   Color (top left), surface normals (top right), distance to the camera (bottom
   left) and semantic segmentation (bottom right), from the same viewpoint.

Render modes
------------

ovrtx provides three different modes, each targeting a different balance of throughput and fidelity.
:doc:`Render Modes <cameras/render_modes>` describes Real-Time Path Tracing for
path-traced lighting with real-time denoising, Path Tracing for accumulated
reference images, and Minimal for higher throughput without path-traced lighting.
Each RenderProduct selects its mode.

Path Tracing can separate lighting contributions into compositing passes using
:doc:`Light Path Expressions <cameras/light_path_expressions>`. Its
:doc:`spectral rendering option <cameras/render_modes/spectral_rendering>` models
wavelength-dependent light transport and camera spectral response.

.. figure:: ../img/light-path-expressions.avif
   :alt: Full rendered image alongside diffuse reflection, glossy reflection, glossy transmission and caustics passes
   :align: center
   :width: 700

   A Path Tracing image and four Light Path Expression passes: diffuse reflection,
   glossy reflection, glossy transmission and caustics.

Camera attributes
-----------------

:doc:`Camera attributes <cameras/usd_camera_attributes>` control projection,
focus, clipping and exposure. :doc:`Lens Calibration <cameras/lens_calibration>`
adds OpenCV pinhole and fisheye distortion, lookup-table projections and
omni-directional stereo.

.. figure:: ../img/camera-lens-calibration.avif
   :alt: Robot lineup rendered with OpenCV pinhole, OpenCV fisheye and omni-directional stereo projections
   :align: center
   :width: 700

   The same scene with OpenCV pinhole, OpenCV fisheye and omni-directional stereo
   projections (clockwise from top left).

:doc:`Rolling Shutter <cameras/rolling_shutter>` samples rows or columns at
different times, producing skew when the camera or scene moves.
:doc:`Sensor Scheduling <common/multi_rate>` schedules cameras at
different capture rates. :doc:`Scene Partitions <cameras/scene_partitions>` lets
cameras render isolated environments within one stage.

.. _sensors-cameras-index-beyond:

Sensor modeling
----------------

The :doc:`Camera generic core model <visual/camera_core/index>` adds a color
filter array, sensor noise, compression and image signal processing to rendered
images. The :doc:`Camera single-view stereo depth model <visual/depth_camera/index>`
produces depth images with disparity noise, quantization and missing measurements.

.. figure:: ../img/sensors/visual/visual_sensors_strip.avif
   :align: center
   :alt: Robot lineup shown as rendered color, camera-core ISP output, and a depth visualization.
   :width: 100%

   The robot lineup from three cameras at the same pose. Left: rendered
   ``LdrColor``. Center: ``OmniCameraSensorPostIsp`` with a sample camera
   profile. Right: ``DepthSensorOutputVisualization``, black where no
   measurement is reported.

.. toctree::
   :maxdepth: 1

   cameras/render_modes
   cameras/usd_camera_attributes
   cameras/lens_calibration
   cameras/rolling_shutter
   cameras/scene_partitions
   cameras/outputs
   cameras/decoding_outputs
   cameras/light_path_expressions

Related
-------

- :doc:`cameras/render_modes`
- :doc:`cameras/usd_camera_attributes`
- :doc:`cameras/lens_calibration`
- :doc:`cameras/outputs`
