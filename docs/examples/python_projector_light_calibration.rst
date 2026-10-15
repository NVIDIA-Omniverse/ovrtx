.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

Python: Projector Light Calibration
===================================

.. |projector-calibration-caption| replace:: The generated direction texture
   applies radial, tangential, thin-prism, and sensor-tilt terms from the
   example OpenCV calibration. Projected image:
   `Chelsea the cat <https://scikit-image.org/docs/stable/api/skimage.data.html#skimage.data.chelsea>`__,
   photographed by Stefan van der Walt and dedicated to the public domain under
   `CC0 1.0 Universal <https://creativecommons.org/publicdomain/zero/1.0/>`__.

This example converts an OpenCV pinhole calibration into an RTX projector-light
direction texture. It then renders the same textured projector with its default
pinhole mapping and the generated calibration mapping.

.. figure:: ../img/light-projector-direction-texture.avif
   :alt: Pinhole and OpenCV-calibrated projector-light outputs
   :align: center

   |projector-calibration-caption|

The generator starts from an OpenCV image size, camera matrix, and distortion
vector:

.. literalinclude:: ../../examples/python/projector-light-calibration/generate_direction_texture.py
   :language: python
   :start-after: # [snippet:doc-projector-opencv-calibration]
   :end-before: # [/snippet:doc-projector-opencv-calibration]

It decodes every square-lookup texel into an octahedral direction:

.. literalinclude:: ../../examples/python/projector-light-calibration/generate_direction_texture.py
   :language: python
   :start-after: # [snippet:doc-projector-octahedral-directions]
   :end-before: # [/snippet:doc-projector-octahedral-directions]
   :dedent:

It then uses OpenCV to project front-facing directions into image UVs and marks
directions outside the image:

.. literalinclude:: ../../examples/python/projector-light-calibration/generate_direction_texture.py
   :language: python
   :start-after: # [snippet:doc-projector-opencv-project]
   :end-before: # [/snippet:doc-projector-opencv-project]
   :dedent:

The final lookup is a square OpenEXR image with float32 R and G channels:

.. literalinclude:: ../../examples/python/projector-light-calibration/generate_direction_texture.py
   :language: python
   :start-after: # [snippet:doc-projector-write-direction-texture]
   :end-before: # [/snippet:doc-projector-write-direction-texture]
   :dedent:

The example generates the lookup before rendering the pinhole and calibrated
outputs:

.. literalinclude:: ../../examples/python/projector-light-calibration/main.py
   :language: python
   :start-after: # [snippet:doc-projector-generate-and-render]
   :end-before: # [/snippet:doc-projector-generate-and-render]
   :dedent:

Run the complete example with one of these commands:

.. code-block:: bash

   cd examples/python/projector-light-calibration
   uv run main.py
   uv run main.py --rrd _output/projector-light-calibration.rrd
   uv run main.py --no-rr --png _output/projector-light-calibration.png

Use ``generate_direction_texture.py`` directly when you only need the OpenEXR
asset:

.. code-block:: bash

   uv run generate_direction_texture.py \
     --output _output/projector-opencv-direction.exr \
     --texture-size 1024

See :doc:`../lights/rect_light` for the lookup format, shader conventions, and
projector-light authoring attributes.
