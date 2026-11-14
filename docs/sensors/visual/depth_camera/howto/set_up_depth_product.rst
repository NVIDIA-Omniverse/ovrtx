.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-visual-depth-camera-howto-set-up-depth-product:

Set Up a Depth Product
======================

**Goal.** Apply the depth model's API schema to a ``Camera`` and configure its
RenderProduct to request the three renderer inputs and five sensor outputs.

**Before you start.** Have a camera scene and understand
:doc:`RenderProducts and RenderVars <../../../common/output_configuration>`.
New to ovrtx? Start with :doc:`../../../first_sensor`.
See :doc:`../index` for the model's capabilities and limits.

.. _sensors-visual-depth-camera-howto-set-up-depth-product-recipe:

Apply the schema and request the outputs
----------------------------------------

The model's attributes are authored on the ``Camera`` prim. Apply
``OmniSensorGenericDepthSensorSingleViewAPI`` to it and author the depth parameters
there; the RenderProduct points its ``rel camera`` at that camera and requests
the outputs, and carries no depth attributes of its own. There is no sensor
prim. Where the schema applies, and the identity attributes it brings, is on
:doc:`../attributes`; applying an API schema in general is on
:doc:`Sensor Configuration <../../../common/sensor_configuration>`.

.. _sensors-depth-sensor-runs-when-requested:
.. _sensors-visual-depth-camera-howto-set-up-depth-product-runs-when-requested:

The scene below is complete. The camera applies the schema and authors five of
the attributes; the product points at that camera and lists all eight RenderVars
in ``orderedVars``: the three inputs the model reads, ``LdrColor``,
``DistanceToImagePlaneSD`` and ``Camera3dPositionSD``, then the five
``DepthSensor*`` outputs it writes. This example requests all five outputs; you can omit the outputs you do not need.
Requesting ``DepthSensor*`` outputs enables the post-processing pipeline;
applying the schema sets its parameters. :ref:`The required set
<sensors-visual-depth-camera-outputs-required-vars>` explains the input and
output requirements.

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../../tests/docs/usd/data/depth_sensor_render_product.usda
         :language: usda
         :start-after: # [snippet:doc-depth-sensor-render-product]
         :end-before: # [/snippet:doc-depth-sensor-render-product]
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-depth-sensor-render-product-python]
         :end-before: # [/snippet:doc-depth-sensor-render-product-python]
         :dedent:

The five values shown are the schema defaults, written out; the other ten
attributes take theirs. The generated :doc:`Sensor API Schemas
<../../../reference/schemas>` table lists every attribute with its type and
default, and :doc:`../attributes` explains what each does. Every RenderVar in
``orderedVars`` is a prim of its own whose ``sourceName`` names the output it
carries (:ref:`sensors-common-output-configuration-rendervar`); here they are
children of the product, and they can equally live in a shared ``Vars`` scope
that several products reference
(:ref:`sensors-common-output-configuration-independent-products`). The three
inputs are ordinary camera outputs, described on :doc:`Cameras: Outputs
<../../../cameras/outputs>`.

.. note::

   Match the product's ``resolution`` to the real depth stream's output mode.
   Configure ``focalLengthPixel`` and ``sensorSizePixel`` from the same camera
   calibration, and keep the rendered Camera prim's intrinsics consistent with
   it. :ref:`The optics group <sensors-visual-depth-camera-attributes-optics>`
   explains the relationship and how to use a different output resolution.

.. _sensors-depth-sensor-per-product:
.. _sensors-visual-depth-camera-howto-set-up-depth-product-per-product:

Several products, cameras and projections
-----------------------------------------

**The parameters belong to the product, not to the camera.** Two depth products
rendered in the same step can have different parameter values, so comparing two
devices in one scene is one product per device, each with its own attribute
values, and the step result contains each product's frames; stepping several
products at once is described on :doc:`Output Configuration
<../../../common/output_configuration>`.

**Cameras can use different projections.** One product's camera can be a
pinhole and another's an OpenCV fisheye, authored as :doc:`Lens Calibration
<../../../cameras/lens_calibration>` describes. The model does not take
the projection into account: it shifts every sample along its image row by the
same disparity formula whatever lens produced the image. The formula and the
attributes in it are on :doc:`../attributes`.

**A tiled product shares one parameter set.** A product whose ``rel camera``
lists several cameras renders each camera into its own tile of one frame
(:ref:`sensors-common-output-configuration-rel-camera`). The depth simulation
then runs once over that whole frame with the one set of parameters authored
on the product, shared by every camera in it. When each camera needs its own
baseline, optics or noise, give each camera its own product instead
(:ref:`sensors-common-output-configuration-independent-products`).

.. _sensors-visual-depth-camera-howto-set-up-depth-product-run-and-read:

Run and read
------------

Step the renderer with the product's path in its set of render products, as for
any camera, and warm it up before you judge the result
(:ref:`sensors-common-output-configuration-warmup`; :ref:`Invalid measurements
<sensors-visual-depth-camera-outputs-invalid-entries>` has the note on a
capture taken too early). Each returned frame holds one output per RenderVar,
keyed by the RenderVar's full prim path, here
``/Render/CameraDepthSingleView/DepthSensorDistance``, not by its
``sourceName``. Map each output and read its tensor as :doc:`Sensor Outputs
<../../../common/sensor_outputs>` describes for every sensor
(:ref:`sensors-common-sensor-outputs-mapping`); the five depth outputs are
images at the product's resolution.

This model ships without a public example. The product authored on this page is
the complete configuration, and the steps above run and read it.

.. _sensors-visual-depth-camera-howto-set-up-depth-product-verify:

Verify it worked
----------------

Check the visualization first, then the numbers.

- **Look at the visualization.** ``DepthSensorOutputVisualization`` is the one
  output meant for viewing. Set ``rgbDepthOutputMode`` to a mode that shows
  distance; mode ``3`` is the quickest check, because a pixel with no
  measurement is black there. Author a realistic ``maxDistance`` before you
  judge the gradient itself, or it stays uniform. :ref:`Outputs
  <sensors-visual-depth-camera-outputs-visualization>` lists the modes.
- **Read the distance.** ``DepthSensorDistance`` should be non-zero over
  textured, lit surfaces inside the range limits. What a zero in it means, and
  why large empty regions are normal on an untextured scene, is on :ref:`Invalid
  measurements <sensors-visual-depth-camera-outputs-invalid-entries>`.
- **Know what you are reading.** :doc:`../outputs` explains what each output
  carries and the two frames the distance image and the point cloud are
  expressed in.

When it goes wrong
------------------

**The distance is zero everywhere.** Check the request first: a missing input or
output stops the simulation and the reason is logged as an error (:ref:`The
required set <sensors-visual-depth-camera-outputs-required-vars>`). Then render
more frames before you judge it; where the color has not resolved yet, the
confidence test has no texture to pass
(:ref:`sensors-common-output-configuration-warmup`).

**An output is missing from the frame although its RenderVar is authored.** You
are probably looking it up by ``sourceName``; the frame keys its outputs by the
RenderVar's full prim path (:ref:`Run and read
<sensors-visual-depth-camera-howto-set-up-depth-product-run-and-read>`).

**Large regions are empty on a scene that renders.** That is the confidence test
at work on smooth, untextured surfaces, where it leaves holes by design;
:doc:`Tune Noise, Quantization and Confidence <noise_and_confidence>` raises
coverage through scene texture, lighting contrast, the simulated IR projector or
the threshold.

**The distance image and the point cloud disagree.** They are expressed in
different frames and, on a stage whose ``metersPerUnit`` is not 1, in different
units; :ref:`Two frames <sensors-visual-depth-camera-outputs-two-frames>` and
:ref:`Units <sensors-visual-depth-camera-outputs-units>` say which is which.

Anything else is on the :doc:`Symptom Index <../../../troubleshooting/symptoms>`.

Related
-------

- :doc:`Camera single-view stereo depth model <../index>` — what the model reproduces from one rendered view.
- :doc:`USD Attributes <../attributes>` — the fourteen attributes in their groups, with units, clamps and relations.
- :doc:`Outputs <../outputs>` — the required set, the five outputs, what a zero means, the two frames and the visualization modes.
- :doc:`Build a Profile from a Spec Sheet <spec_sheet_profile>` — making the product behave like a real device, from its datasheet.
