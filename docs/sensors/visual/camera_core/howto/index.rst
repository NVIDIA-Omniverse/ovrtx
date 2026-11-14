.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-visual-camera-core-howto:

How-To
======

Start from a camera that renders an image (:doc:`../../../cameras`).
The model processes its linear ``HdrColor`` image through the stages listed
in :doc:`../outputs`.

Follow :doc:`image_pipeline` to apply the schema and request a primary output
and optional diagnostic taps. Then configure each part:

- :doc:`input_image` — select HDR precision and a compatible render mode; ``LdrColor`` is not an input.
- :doc:`color_filter_array` — choose the 2×2 mosaic, weight triples, pattern token and code range.
- :doc:`companding_and_isp` — configure RAW compression and the ISP that decodes it.

.. toctree::
   :maxdepth: 1

   image_pipeline
   input_image
   color_filter_array
   companding_and_isp

Related
-------

- :doc:`USD Attributes <../attributes>` — the attribute groups behind each stage, their units and relations.
- :doc:`Outputs <../outputs>` — the seven output names, the two primary outputs, the diagnostic taps and the format each stage writes.
- :doc:`Cameras <../../../cameras>` — the lens, shutter, render mode and output-decoding decisions of the camera this model runs on.
- :doc:`Sensor Configuration <../../../common/sensor_configuration>` — applying a schema to a prim and overriding its attributes.
- :doc:`Output Configuration <../../../common/output_configuration>` — how a RenderProduct and its RenderVars fit together.
- :doc:`Sensor Outputs <../../../common/sensor_outputs>` — mapping an image output and reading it back.
- :doc:`Symptom Index <../../../troubleshooting/symptoms>` — what to check when a how-to's result is not what you expected.
