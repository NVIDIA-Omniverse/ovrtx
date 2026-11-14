.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-cameras-lens-calibration:

.. _sensors-cameras-howto-lens-calibration:

Lens Calibration
================

Overview
--------

Lens-distortion API schemas let a camera reproduce measured camera intrinsics
and distortion. ovrtx supports OpenCV pinhole and fisheye calibration,
lookup-table-based generalized projection, and omni-directional stereo.

When you apply one of these schemas, its calibration parameters drive
projection instead of ``focalLength`` and the aperture attributes. Depth of
field still uses ``focalLength``, ``focusDistance``, and ``fStop``.

.. figure:: ../../img/camera-lens-calibration.avif
   :width: 700
   :alt: Robot lineup rendered through OpenCV pinhole, OpenCV fisheye, and omni-directional stereo cameras
   :align: center

   *Three camera views of the same scene showing three different lens
   calibration schemata. Clockwise from top-left:
   OmniLensDistortionOpenCvPinholeAPI, OmniLensDistortionOpenCvFisheyeAPI,
   OmniLensDistortionOmniDirectionalStereoAPI*

To fit calibration parameters from checkerboard photographs, run
:doc:`Python: Camera calibration <../../examples/python_camera_calibration>`.
The example includes the photographs, an OpenCV calibration script and output checks.

Creating A Calibrated Camera
----------------------------

Apply one lens-distortion API schema to a ``Camera`` prim. The following
examples create the same OpenCV pinhole calibration.

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../tests/docs/usd/data/camera_lens_calibration.usda
         :language: usda
         :start-after: # [snippet:doc-camera-lens-calibration]
         :end-before: # [/snippet:doc-camera-lens-calibration]
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-camera-lens-calibration-python]
         :end-before: # [/snippet:doc-camera-lens-calibration-python]
         :dedent:

See :doc:`../../examples/python_camera_lens_calibration` for a runnable
example.

.. _sensors-cameras-lens-calibration-schemas:

Available Schemas
-----------------

.. _sensors-recipes-calibration-not-kannala-brandt-k3:

.. csv-table::
   :header: "Applied API schema", "Purpose"
   :widths: 44, 56
   :class: compact-table

   "``OmniLensDistortionOpenCvPinholeAPI``", "Uses OpenCV pinhole projection with radial, tangential, and thin-prism coefficients."
   "``OmniLensDistortionOpenCvFisheyeAPI``", "Uses OpenCV fisheye projection with four radial coefficients."
   "``OmniLensDistortionLutAPI``", "Defines projection with ray-direction and ray-position textures."
   "``OmniLensDistortionOmniDirectionalStereoAPI``", "Renders one eye of a 360-degree stereo projection."
   "``OmniLensDistortionFthetaAPI``", "Preserves calibration data that uses the NVIDIA f-theta model."
   "``OmniLensDistortionKannalaBrandtK3API``", "Preserves calibration data that uses the Kannala-Brandt K3 model."
   "``OmniLensDistortionRadTanThinPrismAPI``", "Preserves calibration data that uses the radial-tangent thin-prism model."

For new calibrated cameras, prefer the OpenCV, LUT, or omni-directional stereo
schemas. Use the compatibility schemas when preserving existing calibration
data.

.. _sensors-cameras-lens-calibration-pinhole:
.. _sensors-recipes-calibration-pinhole-attributes:

OpenCV Pinhole
--------------

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 60, 40
   :class: compact-table

   "``token omni:lensdistortion:model = ""opencvPinhole""``", "Selects OpenCV pinhole projection."
   "``int2 omni:lensdistortion:opencvPinhole:imageSize = (2048, 1024)``", "Calibration resolution in pixels."
   "``float omni:lensdistortion:opencvPinhole:fx = 900``", "Horizontal focal length in calibration pixels."
   "``float omni:lensdistortion:opencvPinhole:fy = 800``", "Vertical focal length in calibration pixels."
   "``float omni:lensdistortion:opencvPinhole:cx = 1024``", "Horizontal principal point in calibration pixels."
   "``float omni:lensdistortion:opencvPinhole:cy = 512``", "Vertical principal point in calibration pixels."
   "``float omni:lensdistortion:opencvPinhole:k1 = 0``", "Radial coefficient."
   "``float omni:lensdistortion:opencvPinhole:k2 = 0``", "Radial coefficient."
   "``float omni:lensdistortion:opencvPinhole:k3 = 0``", "Radial coefficient."
   "``float omni:lensdistortion:opencvPinhole:k4 = 0``", "Radial coefficient."
   "``float omni:lensdistortion:opencvPinhole:k5 = 0``", "Radial coefficient."
   "``float omni:lensdistortion:opencvPinhole:k6 = 0``", "Radial coefficient."
   "``float omni:lensdistortion:opencvPinhole:p1 = 0``", "Tangential coefficient."
   "``float omni:lensdistortion:opencvPinhole:p2 = 0``", "Tangential coefficient."
   "``float omni:lensdistortion:opencvPinhole:s1 = 0``", "Thin-prism coefficient."
   "``float omni:lensdistortion:opencvPinhole:s2 = 0``", "Thin-prism coefficient."
   "``float omni:lensdistortion:opencvPinhole:s3 = 0``", "Thin-prism coefficient."
   "``float omni:lensdistortion:opencvPinhole:s4 = 0``", "Thin-prism coefficient."

.. figure:: ../../img/camera-lens-calibration-pinhole.avif
   :width: 752
   :alt: Robot lineup rendered through an OpenCV pinhole camera
   :align: center

   *OpenCV pinhole projection with radial and tangential distortion.*

.. _sensors-cameras-lens-calibration-fisheye:
.. _sensors-recipes-calibration-fisheye-attributes:

OpenCV Fisheye
--------------

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 60, 40
   :class: compact-table

   "``token omni:lensdistortion:model = ""opencvFisheye""``", "Selects OpenCV fisheye projection."
   "``int2 omni:lensdistortion:opencvFisheye:imageSize = (2048, 1024)``", "Calibration resolution in pixels."
   "``float omni:lensdistortion:opencvFisheye:fx = 900``", "Horizontal focal length in calibration pixels."
   "``float omni:lensdistortion:opencvFisheye:fy = 800``", "Vertical focal length in calibration pixels."
   "``float omni:lensdistortion:opencvFisheye:cx = 1024``", "Horizontal principal point in calibration pixels."
   "``float omni:lensdistortion:opencvFisheye:cy = 512``", "Vertical principal point in calibration pixels."
   "``float omni:lensdistortion:opencvFisheye:k1 = 0.00245``", "Radial coefficient."
   "``float omni:lensdistortion:opencvFisheye:k2 = 0``", "Radial coefficient."
   "``float omni:lensdistortion:opencvFisheye:k3 = 0``", "Radial coefficient."
   "``float omni:lensdistortion:opencvFisheye:k4 = 0``", "Radial coefficient."

.. _sensors-recipes-calibration-fisheye-k1-default:

The fisheye ``k1`` default is nonzero, so applying the schema without authoring
coefficients introduces some distortion. Author all four coefficients for a
measured calibration; the :doc:`calibration script
<../../examples/python_camera_calibration>` does this automatically.

.. figure:: ../../img/camera-lens-calibration-fisheye.avif
   :width: 640
   :alt: Robot lineup rendered through an OpenCV fisheye camera
   :align: center

   *OpenCV fisheye projection using four equidistant distortion coefficients.*

``imageSize`` makes an OpenCV calibration independent of output resolution.
When the RenderProduct resolution differs, ovrtx scales ``fx``, ``fy``, ``cx``,
and ``cy`` to the output resolution.

.. _sensors-cameras-lens-calibration-lut:

Generalized Projection
----------------------

``OmniLensDistortionLutAPI`` defines non-parametric projection with two
floating-point textures.

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 60, 40
   :class: compact-table

   "``token omni:lensdistortion:model = ""lut""``", "Selects lookup-table projection."
   "``float omni:lensdistortion:lut:nominalWidth = 1936``", "Calibrated sensor width."
   "``float omni:lensdistortion:lut:nominalHeight = 1216``", "Calibrated sensor height."
   "``float2 omni:lensdistortion:lut:opticalCenter = (970.94244, 600.3748)``", "Optical center in calibrated sensor coordinates."
   "``asset omni:lensdistortion:lut:rayEnterDirectionTexture = @@``", "Maps normalized image-plane positions to normalized camera-space ray directions stored in RGB."
   "``asset omni:lensdistortion:lut:rayExitPositionTexture = @@``", "Inverse map from camera-space ray directions to normalized image-plane positions stored in RG. Directions index the texture using octahedral encoding after negating their Z component."

Both lookup textures must have the same aspect ratio. Until both textures are
available, the camera renders as a pinhole camera. The textures define the
projection; ``nominalWidth``, ``nominalHeight`` and ``opticalCenter`` do not
reshape the texture-based projection.

.. warning::

   Low-resolution lookup textures can produce artifacts at larger output
   resolutions.

.. _sensors-cameras-lens-calibration-ods:

Omni-Directional Stereo
-----------------------

``OmniLensDistortionOmniDirectionalStereoAPI`` configures one eye of a
360-degree stereo camera. Use separate left- and right-eye cameras. Each eye
produces an equirectangular panorama covering 360° horizontally and 180°
vertically. Use a 2:1 output resolution for equal angular sampling along both
axes.

Each ray starts at an eye position offset sideways from the camera center by
half the interpupillary distance. This offset rotates with the ray's azimuth,
so the eye positions follow the viewing direction around the panorama.

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 64, 36
   :class: compact-table

   "``token omni:lensdistortion:model = ""omniDirectionalStereo""``", "Selects omni-directional stereo projection."
   "``bool omni:lensdistortion:omniDirectionalStereo:isLeftEye = false``", "Selects the left eye when true and the right eye when false."
   "``float omni:lensdistortion:omniDirectionalStereo:interpupillaryDistance = 0.064``", "Eye separation in meters."

.. figure:: ../../img/camera-lens-calibration-omnidirectional-stereo.avif
   :width: 1024
   :alt: Robot lineup rendered as an omni-directional stereo panorama
   :align: center

   *A 1024 by 512 single-eye omni-directional stereo panorama.*

.. _sensors-cameras-lens-calibration-resolution:

Calibration resolution versus output resolution
-----------------------------------------------

``imageSize`` makes an OpenCV calibration independent of the output
resolution, for the pinhole and the fisheye schema alike. Set it to the
resolution of the images the calibration was solved from and author ``fx``,
``fy``, ``cx`` and ``cy`` in pixels of those images. When the RenderProduct's
resolution differs from ``imageSize``, the renderer scales the four values to
the output resolution, so the rendered field of view is the one you
calibrated; if the aspect ratio differs as well, the horizontal field of view
is kept and the vertical one is cropped or extended to fill the output.

Related
-------

- :doc:`../../examples/python_camera_calibration`
- :doc:`usd_camera_attributes`
- :doc:`decoding_outputs`
- :doc:`rolling_shutter`
- `OpenCV camera calibration documentation <https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html>`_
