.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-reference-index:

Reference
=========

Look up schema declarations, output types and sensor terminology here.
For behavior and examples, use the guides linked below.

Reference pages
---------------

- :doc:`Sensor API Schemas <schemas>` — generated declarations for sensor
  prims and API schemas, including attribute names, types and defaults.
- :doc:`Lens Distortion Schemas <schemas_lens_distortion>` — generated
  declarations for the lens-distortion APIs applied to USD Camera prims.
- :doc:`Glossary <glossary>` — sensor terms and abbreviations, with links to
  their detailed definitions.
- :ref:`C API <c-api-sensor-types>` and
  :ref:`Python API <python-api-render-outputs>` — output container definitions.

The generated schema reference includes prims and APIs without a model guide
in these docs. A schema declaration alone does not establish model support.

Attribute and output guides
---------------------------

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 40 60

   * - Looking for
     - Where to look
   * - Model attributes, output channels, units and validity rules
     - Each model's USD Attributes and Outputs pages under
       :doc:`Visual Sensors <../visual/index>` or
       :doc:`Non-Visual Sensors <../nonvisual/index>`
   * - Camera attributes
     - :doc:`USD Camera Attributes <../cameras/usd_camera_attributes>`
   * - Render-mode selection
     - :doc:`Render Modes <../cameras/render_modes>`
   * - Rolling-shutter attributes
     - :doc:`Rolling Shutter <../cameras/rolling_shutter>`
   * - Lens-model selection and calibration attributes
     - :doc:`Lens Calibration <../cameras/lens_calibration>`
   * - Applying schemas and configuring shared sensor attributes
     - :doc:`Sensor Configuration <../common/sensor_configuration>`
   * - Reading outputs, mapping memory and handling variable-size data
     - :doc:`Sensor Outputs <../common/sensor_outputs>`
   * - Configuration problems and model limitations
     - :doc:`Troubleshooting <../troubleshooting/index>`

.. toctree::
   :hidden:
   :maxdepth: 1

   schemas
   schemas_lens_distortion
   glossary

Related
-------

- :doc:`Common Concepts <../common/index>` — the shared sensor workflow.
- :doc:`Cameras <../cameras>` — camera capabilities and configuration.
