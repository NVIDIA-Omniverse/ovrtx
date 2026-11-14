.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-visual-depth-camera-howto-noise-and-confidence:

Tune Noise, Quantization and Confidence
=======================================

**Goal.** Tune depth noise and coverage, using a noise-free run and the
model's confidence map to check the result. Noise and quantization move
measurements along image rows; confidence determines which pixels receive them.

**Before you start.** Set up a depth product that delivers all five outputs
(:doc:`set_up_depth_product`). Author the attributes below on its ``Camera``
with ``OmniSensorGenericDepthSensorSingleViewAPI`` applied. See
:doc:`../attributes` for their units and interactions, and
:ref:`invalid entries <sensors-visual-depth-camera-outputs-invalid-entries>`
for what zero means in ``DepthSensorDistance``.

.. _sensors-visual-depth-camera-howto-noise-and-confidence-noise-off:
.. _sensors-depth-sensor-noise-off:

Get a noise-free run
--------------------

Set ``noiseMean`` to zero:

.. code-block:: usda

    float omni:sensor:depthSensor:noiseMean = 0.0

A zero step switches quantization and the Gaussian jitter off together,
whatever ``noiseSigma`` holds (:ref:`the noise attributes
<sensors-visual-depth-camera-attributes-noise>` say why). Every measurement
retains its reprojected pixel position. Use this run to identify missing
measurements caused by occlusion, the range limits
or the confidence test rather than from noise. Setting ``noiseSigma`` to zero
on its own is not the same: with ``noiseMean`` above zero the disparity is
still quantized.

.. _sensors-visual-depth-camera-howto-noise-and-confidence-shape:

Shape the noise
---------------

Set ``noiseMean`` above zero to enable the stage, then tune the other two
values in the direction you need: raise ``noiseSigma`` for more scatter, and
raise ``noiseDownscaleFactorPixel`` to move pixels in coarser patches. All
three use rendered-image pixels: the first two measure disparity and the third
sets the spatial scale of the noise. Tune them against the device's output at
the same resolution; what each one does is on :ref:`the noise attributes
<sensors-visual-depth-camera-attributes-noise>`. A run with more scatter than
the defaults, in two-pixel patches, is authored like this:

.. code-block:: usda

    float omni:sensor:depthSensor:noiseMean = 0.25
    float omni:sensor:depthSensor:noiseSigma = 0.5
    float omni:sensor:depthSensor:noiseDownscaleFactorPixel = 2.0

The stage changes each measurement's pixel position along its row while
preserving its distance value. Expected effects include pixels with no assigned
measurement, irregular object boundaries and selection of the nearer sample
when two samples project to the same pixel. These effects vary between frames
even in a static scene. On a slanted surface a displaced
measurement also shows up at a pixel whose own distance differs. The
single-pixel cleanup of ``outlierRemovalEnabled`` runs before this stage
(:doc:`Outputs <../outputs>` has the stage order), so it does not fill noise
speckle. Which values match a real device is a tuning question a spec sheet
rarely answers (:doc:`Build a Profile from a Spec Sheet <spec_sheet_profile>`):
start from the defaults and compare against recordings of the device.

.. _sensors-visual-depth-camera-howto-noise-and-confidence-coverage:

Increase depth coverage
-----------------------

Once occlusion holes, the near limit and the range limits are accounted for
(:doc:`Outputs <../outputs>` lists the stages that discard a value), an empty
region in ``DepthSensorDistance`` is the confidence test at work: the pixel's
source in the rendered view did not show enough texture. The following three
changes can increase coverage and can be combined.

**Give the scene texture or contrast.** Add texture to the materials, or light
the scene so that surfaces show gradients, before adjusting the model's
attributes: the test measures visible detail in the rendered image, so a flat,
evenly lit wall or a region that renders to uniform white or black gives it
nothing (:ref:`the texture term
<sensors-visual-depth-camera-attributes-confidence>`).

**Switch on the simulated IR projector.** Set ``effectiveDistance`` above zero,
in meters: within that distance a surface is accepted whether or not it has
texture, at any threshold above zero (:ref:`the IR term
<sensors-visual-depth-camera-attributes-confidence>` describes the decrease in
IR confidence beyond that distance). Use this parameter to accept measurements
on untextured surfaces near the camera.

**Increase** ``confidenceThreshold`` **to accept more pixels.** The applied
threshold decreases nonlinearly as the authored value increases. Adjust the
authored value toward 1 and read the
:ref:`direction warning and the remap table <sensors-visual-depth-camera-attributes-confidence-remap>`
before selecting a value. Decrease the authored value to require greater
confidence. A pixel with zero texture confidence requires a positive IR term
to pass.

For a 3 m projector range and permissive confidence, author on the ``Camera``:

.. code-block:: usda

    float omni:sensor:depthSensor:effectiveDistance = 3.0
    float omni:sensor:depthSensor:confidenceThreshold = 0.99

.. figure:: ../../../../img/sensors/visual/depth_confidence_coverage.avif
   :alt: Two-by-two grid. Top left: a mostly dark confidence map with white outlines along the walls' edges, the tall box and the sphere. Top right: a confidence map that is white across the whole image area with scattered black specks. Bottom left: a depth image that is black except along those edges. Bottom right: a depth image covering nearly the whole image area, with black occlusion holes beside the box and the sphere and a black band on the left.
   :width: 1000

   Coverage increases as the applied threshold decreases. Left: the mode 6 confidence map (top) and
   ``DepthSensorDistance`` (bottom) of a Cornell box test scene's fisheye depth
   product at a ``confidenceThreshold`` of ``0.5``; right: the same two images
   at ``0.99``. White in the confidence map is a pixel that passed and gray the
   raw texture gradient of one that failed; black in the distance image is a
   zero, no measurement. At ``0.5`` only edges and highlights pass; at ``0.99``
   nearly the whole view does. The simulated IR projector is off,
   ``effectiveDistance`` at its default of ``0``, and noise is off, so the
   threshold is the only difference between the columns.

.. _sensors-visual-depth-camera-howto-noise-and-confidence-check:

Verify it worked
----------------

Judge coverage from ``DepthSensorDistance`` and from the confidence map, before
and after each change.

- Set ``rgbDepthOutputMode`` to ``6`` and look at
  ``DepthSensorOutputVisualization``: a pixel that passed is white, the rest
  show their raw texture gradient, so a dark area is a surface with too little
  texture to exceed the applied threshold. With the IR projector disabled,
  brighter rejected pixels have confidence values closer to that threshold.
  The other modes are in
  :ref:`the mode table <sensors-visual-depth-camera-outputs-visualization>`.
- Count the measurements. A zero distance denotes an invalid measurement, regardless of cause and
  there is no separate validity channel, so filter on a non-zero distance or on
  the point's ``w`` component, ``1`` for a measurement and ``0`` for none
  (:ref:`invalid measurements <sensors-visual-depth-camera-outputs-invalid-entries>`).
  With the two outputs mapped to the CPU and viewed as NumPy arrays
  (:doc:`Sensor Outputs <../../../common/sensor_outputs>` has the mapping
  call):

  .. code-block:: python

      coverage = (distance[..., 0] > 0).mean()   # DepthSensorDistance, (H, W, 1)
      valid = points[..., 3] > 0                  # DepthSensorPointCloudPosition, (H, W, 4)

- Render enough frames first. Warm the renderer up before you judge coverage
  (the warm-up note is under
  :ref:`invalid measurements <sensors-visual-depth-camera-outputs-invalid-entries>`),
  and compare only frames rendered with the same warm-up. With noise on, compare
  several frames, because the speckle flickers and one frame overstates or
  understates coverage; a noise-free run
  (:ref:`above <sensors-visual-depth-camera-howto-noise-and-confidence-noise-off>`)
  is the cleaner reference for a coverage comparison.

When it goes wrong
------------------

**Coverage fell when you lowered** ``confidenceThreshold``. A higher threshold
keeps more pixels, not fewer: move toward 1 in large steps and read the
:ref:`direction warning and the remap table <sensors-visual-depth-camera-attributes-confidence-remap>`
first.

**Speckle is still there with** ``noiseSigma`` **at zero.** With ``noiseMean``
above zero the disparity is still quantized; only a zero ``noiseMean`` switches
quantization and the jitter off together (:ref:`above
<sensors-visual-depth-camera-howto-noise-and-confidence-noise-off>`).

**An untextured surface stays empty whatever the threshold.** No threshold
recovers a pixel with no texture signal at all; only the simulated IR projector
does, ``effectiveDistance`` above zero, within that distance (:ref:`above
<sensors-visual-depth-camera-howto-noise-and-confidence-coverage>`).

Anything else is on the :doc:`Symptom Index <../../../troubleshooting/symptoms>`.

Related
-------

- :doc:`USD Attributes <../attributes>` — the noise, confidence and range-limit groups, the remap table and the direction warning.
- :doc:`Outputs <../outputs>` — what a zero means, the visualization modes, the stage order and the warm-up note.
- :doc:`Set Up a Depth Product <set_up_depth_product>` — the RenderProduct these attributes are authored on.
- :doc:`Camera single-view stereo depth model <../index>` — the simulated effects and supported uses.
- :doc:`Runtime Parameter Updates <../../../common/runtime_updates>` — the rules every model shares for editing attributes while the simulation runs.
