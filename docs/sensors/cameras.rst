.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Cameras
=======

Camera sensors in ovrtx simulate physically accurate imaging and produce rendered outputs through RenderVar prims attached to a RenderProduct.

For how to configure RenderProducts and RenderVars, refer to :doc:`configuration`.

Example USD
-----------

A RenderProduct that outputs both ``LdrColor`` and ``HdrColor`` from a camera:

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/usd/data/camera_sensor_render_product.usda
         :language: usda
         :start-after: # [snippet:doc-camera-sensor-render-product]
         :end-before: # [/snippet:doc-camera-sensor-render-product]

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-camera-sensor-render-product-python]
         :end-before: # [/snippet:doc-camera-sensor-render-product-python]
         :dedent:

Accessing Outputs in Code
-------------------------

After stepping the renderer with a RenderProduct path, the outputs are available by name:

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_camera_sensors.py
         :language: python
         :start-after: # [snippet:doc-step-and-map-camera-outputs]
         :end-before: # [/snippet:doc-step-and-map-camera-outputs]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_camera_sensors.cpp
         :language: cpp
         :start-after: // [snippet:doc-step-and-map-camera-outputs-c]
         :end-before: // [/snippet:doc-step-and-map-camera-outputs-c]
         :dedent:

.. toctree::
   :maxdepth: 1

   cameras/render_modes
   cameras/outputs
