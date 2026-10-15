.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

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
   :alt: Robot lineup rendered through OpenCV pinhole, OpenCV fisheye, and omni-directional stereo cameras
   :align: center

   *Three camera views of the same scene showing three different lens
   calibration schemata. Clockwise from top-left:
   OmniLensDistortionOpenCvPinholeAPI, OmniLensDistortionOpenCvFisheyeAPI,
   OmniLensDistortionOmniDirectionalStereoAPI*

Creating A Calibrated Camera
----------------------------

Apply one lens-distortion API schema to a ``Camera`` prim. The following
examples create the same OpenCV pinhole calibration.

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../../tests/docs/usd/data/camera_lens_calibration.usda
         :language: usda
         :start-after: # [snippet:doc-camera-lens-calibration]
         :end-before: # [/snippet:doc-camera-lens-calibration]

   .. tab-item:: USD Python

      .. literalinclude:: ../../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-camera-lens-calibration-python]
         :end-before: # [/snippet:doc-camera-lens-calibration-python]
         :dedent:

See :doc:`../../examples/python_camera_lens_calibration` for a runnable
example.

Available Schemas
-----------------

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
   :alt: Robot lineup rendered through an OpenCV pinhole camera
   :align: center

   *OpenCV pinhole projection with radial and tangential distortion.*

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

.. figure:: ../../img/camera-lens-calibration-fisheye.avif
   :alt: Robot lineup rendered through an OpenCV fisheye camera
   :align: center

   *OpenCV fisheye projection using four equidistant distortion coefficients.*

``imageSize`` makes an OpenCV calibration independent of output resolution.
When the RenderProduct resolution differs, ovrtx scales ``fx``, ``fy``, ``cx``,
and ``cy`` to the output resolution.

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
   "``asset omni:lensdistortion:lut:rayEnterDirectionTexture = @@``", "RGB image whose values contain normalized XYZ ray directions in camera space."
   "``asset omni:lensdistortion:lut:rayExitPositionTexture = @@``", "RGB image whose RG channels contain normalized screen-space ray origins."

.. warning::

   Low-resolution lookup textures can produce artifacts at larger output
   resolutions. Supported file formats, filtering, and failure behavior still
   need a portable public runtime test. The example on this page validates the
   OpenCV models, not LUT projection.

Omni-Directional Stereo
-----------------------

``OmniLensDistortionOmniDirectionalStereoAPI`` configures one eye of a
360-degree stereo camera. Use separate left- and right-eye cameras.

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 64, 36
   :class: compact-table

   "``token omni:lensdistortion:model = ""omniDirectionalStereo""``", "Selects omni-directional stereo projection."
   "``bool omni:lensdistortion:omniDirectionalStereo:isLeftEye = false``", "Selects the left eye when true and the right eye when false."
   "``float omni:lensdistortion:omniDirectionalStereo:interpupillaryDistance = 0.064``", "Eye separation in meters."

.. figure:: ../../img/camera-lens-calibration-omnidirectional-stereo.avif
   :alt: Robot lineup rendered as an omni-directional stereo panorama
   :align: center

   *A 1024 by 512 single-eye omni-directional stereo panorama.*

Further Reading
---------------

- :doc:`usd_camera_attributes`
- :doc:`rolling_shutter`
- `OpenCV camera calibration documentation <https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html>`_
