.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

USD Camera Attributes
=====================

Overview
--------

The `UsdGeomCamera <https://openusd.org/release/api/class_usd_geom_camera.html>`_
schema defines the standard camera model used by ovrtx.

Use these attributes to control projection, focus, clipping, and exposure on
the camera targeted by a RenderProduct.

Units
-----

OpenUSD expresses ``focalLength``, aperture, and aperture offsets in tenths of a
scene unit so that camera projection remains stable when an entire stage is
scaled. On a centimeter stage, a value of 25 represents 25 mm. On a meter stage,
the same 25 mm focal length is authored as 0.25. Distances such as
``focusDistance`` and ``clippingRange`` use ordinary scene units.

Lens
----

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 46, 54
   :class: compact-table

   "``float focalLength = 50``", "In tenths of a scene unit. Longer values narrow perspective field of view."
   "``float focusDistance = 0``", "In scene units. Sets the distance of perfect focus."
   "``float fStop = 0``", "F-number controlling depth-of-field blur. Zero disables depth of field."
   "``token projection = ""perspective""``", "Selects ``perspective`` or ``orthographic`` projection."

Aperture
--------

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 46, 54
   :class: compact-table

   "``float horizontalAperture = 20.955``", "Filmback width in tenths of a scene unit."
   "``float horizontalApertureOffset = 0``", "Horizontal projection-center offset in tenths of a scene unit."
   "``float verticalAperture = 15.2908``", "Filmback height in tenths of a scene unit."
   "``float verticalApertureOffset = 0``", "Vertical projection-center offset in tenths of a scene unit."

Clipping
--------

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 46, 54
   :class: compact-table

   "``float4[] clippingPlanes``", "Plane equations adding arbitrary clipping planes."
   "``float2 clippingRange = (1, 1000000)``", "Near and far distances in scene units."

Exposure
--------

Camera brightness is a combination of exposure time and other properties of the
camera system. OpenUSD separates physical exposure from depth of field and
motion blur. Author ``exposure:fStop`` for image brightness and ``fStop`` for
depth of field. Likewise, ``exposure:time`` controls brightness independently of
``shutter:open`` and ``shutter:close``, which describe the motion-blur interval.

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 46, 54
   :class: compact-table

   "``float exposure = 0``", "Base-2 compensation in stops. One doubles image-plane intensity; negative one halves it."
   "``float exposure:fStop = 1``", "F-number. Smaller values brighten the image."
   "``float exposure:iso = 100``", "ISO rating. Higher values brighten the image."
   "``float exposure:responsivity = 1``", "Scale for the camera system's response to light."
   "``float exposure:time = 1``", "Exposure duration in seconds. Longer values brighten the image."

Creating A Camera
-----------------

The following examples author the same perspective camera on a stage whose scene
unit is one meter.

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../../tests/docs/usd/data/camera_attributes.usda
         :language: usda
         :start-after: # [snippet:doc-camera-attributes]
         :end-before: # [/snippet:doc-camera-attributes]

   .. tab-item:: USD Python

      .. literalinclude:: ../../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-camera-attributes-python]
         :end-before: # [/snippet:doc-camera-attributes-python]
         :dedent:

Further Reading
---------------

- :doc:`lens_calibration`
- :doc:`rolling_shutter`
- :doc:`scene_partitions`
- :doc:`../configuration`
