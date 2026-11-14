.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

..
   Generated from schemas/omni_lens_distortion/schema.usda by
   schemas/omni_sensors/generate-schema-docs.py.
   Edits made here are overwritten on the next run.

.. _sensors-reference-schemas-lens-distortion:

Lens Distortion Schemas
=======================

Array defaults longer than three entries are truncated for display with ``...``. Read the schema files shipped in the ovrtx package for the complete defaults.

API Schemas
-----------

OmniLensDistortionFthetaAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines properties for setting up a lensdistortion represented by the NVIDIA f-theta
model.

**Inherits from**: APISchemaBase

**Can only apply to**: Camera

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``token omni:lensdistortion:model = "ftheta"``
     - Allowed tokens: "ftheta"
   * - ``float omni:lensdistortion:ftheta:nominalWidth = 1936``
     - Width of the calibrated sensor
   * - ``float omni:lensdistortion:ftheta:nominalHeight = 1216``
     - Height of the calibrated sensor
   * - ``float2 omni:lensdistortion:ftheta:opticalCenter = (970.9424, 600.3748)``
     -
   * - ``float omni:lensdistortion:ftheta:maxFov = 200``
     -
   * - ``float omni:lensdistortion:ftheta:k0 = 0``
     -
   * - ``float omni:lensdistortion:ftheta:k1 = 0.00245``
     -
   * - ``float omni:lensdistortion:ftheta:k2 = 0``
     -
   * - ``float omni:lensdistortion:ftheta:k3 = 0``
     -
   * - ``float omni:lensdistortion:ftheta:k4 = 0``
     -

OmniLensDistortionKannalaBrandtK3API
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines properties for setting up a lens distortion represented by Kannala-Brandt
model.

**Inherits from**: APISchemaBase

**Can only apply to**: Camera

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``token omni:lensdistortion:model = "kannalaBrandtK3"``
     - Allowed tokens: "kannalaBrandtK3"
   * - ``float omni:lensdistortion:kannalaBrandtK3:nominalWidth = 1936``
     - Width of the calibrated sensor
   * - ``float omni:lensdistortion:kannalaBrandtK3:nominalHeight = 1216``
     - Height of the calibrated sensor
   * - ``float2 omni:lensdistortion:kannalaBrandtK3:opticalCenter = (970.9424, 600.3748)``
     -
   * - ``float omni:lensdistortion:kannalaBrandtK3:maxFov = 200``
     -
   * - ``float omni:lensdistortion:kannalaBrandtK3:k0 = 0``
     -
   * - ``float omni:lensdistortion:kannalaBrandtK3:k1 = 0.00245``
     -
   * - ``float omni:lensdistortion:kannalaBrandtK3:k2 = 0``
     -
   * - ``float omni:lensdistortion:kannalaBrandtK3:k3 = 0``
     -

OmniLensDistortionRadTanThinPrismAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines properties for setting up a lensdistortion represented by a radial-tangent
thin-prism model.

**Inherits from**: APISchemaBase

**Can only apply to**: Camera

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``token omni:lensdistortion:model = "radTanThinPrism"``
     - Allowed tokens: "radTanThinPrism"
   * - ``float omni:lensdistortion:radTanThinPrism:nominalWidth = 1936``
     - Width of the calibrated sensor
   * - ``float omni:lensdistortion:radTanThinPrism:nominalHeight = 1216``
     - Height of the calibrated sensor
   * - ``float2 omni:lensdistortion:radTanThinPrism:opticalCenter = (970.9424, 600.3748)``
     -
   * - ``float omni:lensdistortion:radTanThinPrism:maxFov = 200``
     -
   * - ``float omni:lensdistortion:radTanThinPrism:k0 = 0``
     -
   * - ``float omni:lensdistortion:radTanThinPrism:k1 = 0.00245``
     -
   * - ``float omni:lensdistortion:radTanThinPrism:k2 = 0``
     -
   * - ``float omni:lensdistortion:radTanThinPrism:k3 = 0``
     -
   * - ``float omni:lensdistortion:radTanThinPrism:k4 = 0``
     -
   * - ``float omni:lensdistortion:radTanThinPrism:k5 = 0``
     -
   * - ``float omni:lensdistortion:radTanThinPrism:p0 = -0.00037``
     -
   * - ``float omni:lensdistortion:radTanThinPrism:p1 = -0.00074``
     -
   * - ``float omni:lensdistortion:radTanThinPrism:s0 = -0.00058``
     -
   * - ``float omni:lensdistortion:radTanThinPrism:s1 = -0.00022``
     -
   * - ``float omni:lensdistortion:radTanThinPrism:s2 = 0.00019``
     -
   * - ``float omni:lensdistortion:radTanThinPrism:s3 = -0.0002``
     -

OmniLensDistortionLutAPI
~~~~~~~~~~~~~~~~~~~~~~~~

Defines lens distortion by a pre-generated lookup table, allowing any model to be mapped to the RTX camera
by generating two lookup tables, one for the ray entering, one for the ray leaving, which are used by the renderer to transform rays entering or leaving
the lens system.

Use the example script provided to see how to convert a custom lens model to the table format.

**Inherits from**: APISchemaBase

**Can only apply to**: Camera

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``token omni:lensdistortion:model = "lut"``
     - Allowed tokens: "lut"
   * - ``float omni:lensdistortion:lut:nominalWidth = 1936``
     - Width of the calibrated sensor
   * - ``float omni:lensdistortion:lut:nominalHeight = 1216``
     - Height of the calibrated sensor
   * - ``float2 omni:lensdistortion:lut:opticalCenter = (970.9424, 600.3748)``
     -
   * - ``asset omni:lensdistortion:lut:rayEnterDirectionTexture = @@``
     - Lookup table stored as an RGB image file where each RGB pixel value is the XYZ direction of rays entering
       the lens system in local camera space.
   * - ``asset omni:lensdistortion:lut:rayExitPositionTexture = @@``
     - Lookup table stored as an RGB image file where each RG pixel value is the [0, 1] U,V coordinate in normalized
       screen space where the ray for that pixel is emitted from on the image plane.

OmniLensDistortionOmniDirectionalStereoAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines properties for Omni-Directional Stereo (ODS) camera projection.
This schema configures a single-eye ODS camera.
isLeftEye selects the eye: true = left eye, false = right eye.
interpupillaryDistance (IPD, meters) sets eye separation, with symmetric offsets of -IPD/2 for left and +IPD/2 for right.
A stereo ODS output can be composed from left/right eye cameras, commonly stacked vertically (top/bottom).

**Inherits from**: APISchemaBase

**Can only apply to**: Camera

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``token omni:lensdistortion:model = "omniDirectionalStereo"``
     - Allowed tokens: "omniDirectionalStereo"
   * - ``bool omni:lensdistortion:omniDirectionalStereo:isLeftEye = false``
     - Whether this camera represents the left eye in the stereo pair.
   * - ``float omni:lensdistortion:omniDirectionalStereo:interpupillaryDistance = 0.064``
     - Interpupillary distance (IPD), also known as distance between the eyes, in meters.

OmniLensDistortionOpenCvFisheyeAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines properties for applying the OpenCV fisheye model.

**Inherits from**: APISchemaBase

**Can only apply to**: Camera

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``token omni:lensdistortion:model = "opencvFisheye"``
     - Allowed tokens: "opencvFisheye"
   * - ``int2 omni:lensdistortion:opencvFisheye:imageSize = (2048, 1024)``
     - Size of the image in pixels
   * - ``float omni:lensdistortion:opencvFisheye:cx = 1024``
     -
   * - ``float omni:lensdistortion:opencvFisheye:cy = 512``
     -
   * - ``float omni:lensdistortion:opencvFisheye:k1 = 0.00245``
     -
   * - ``float omni:lensdistortion:opencvFisheye:k2 = 0``
     -
   * - ``float omni:lensdistortion:opencvFisheye:k3 = 0``
     -
   * - ``float omni:lensdistortion:opencvFisheye:k4 = 0``
     -
   * - ``float omni:lensdistortion:opencvFisheye:fx = 900``
     -
   * - ``float omni:lensdistortion:opencvFisheye:fy = 800``
     -

OmniLensDistortionOpenCvPinholeAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines properties for applying the OpenCV pinhole model.

**Inherits from**: APISchemaBase

**Can only apply to**: Camera

Properties
^^^^^^^^^^

.. list-table::
   :widths: 60 40
   :class: compact-table
   :header-rows: 1

   * - USD declaration
     - Description
   * - ``token omni:lensdistortion:model = "opencvPinhole"``
     - Allowed tokens: "opencvPinhole"
   * - ``int2 omni:lensdistortion:opencvPinhole:imageSize = (2048, 1024)``
     - Size of the image in pixels
   * - ``float omni:lensdistortion:opencvPinhole:fx = 900``
     -
   * - ``float omni:lensdistortion:opencvPinhole:fy = 800``
     -
   * - ``float omni:lensdistortion:opencvPinhole:cx = 1024``
     -
   * - ``float omni:lensdistortion:opencvPinhole:cy = 512``
     -
   * - ``float omni:lensdistortion:opencvPinhole:k1 = 0``
     -
   * - ``float omni:lensdistortion:opencvPinhole:k2 = 0``
     -
   * - ``float omni:lensdistortion:opencvPinhole:p1 = 0``
     -
   * - ``float omni:lensdistortion:opencvPinhole:p2 = 0``
     -
   * - ``float omni:lensdistortion:opencvPinhole:k3 = 0``
     -
   * - ``float omni:lensdistortion:opencvPinhole:k4 = 0``
     -
   * - ``float omni:lensdistortion:opencvPinhole:k5 = 0``
     -
   * - ``float omni:lensdistortion:opencvPinhole:k6 = 0``
     -
   * - ``float omni:lensdistortion:opencvPinhole:s1 = 0``
     -
   * - ``float omni:lensdistortion:opencvPinhole:s2 = 0``
     -
   * - ``float omni:lensdistortion:opencvPinhole:s3 = 0``
     -
   * - ``float omni:lensdistortion:opencvPinhole:s4 = 0``
     -
