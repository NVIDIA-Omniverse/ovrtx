.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Rect Light
==========

.. |projector-caption| replace:: Projector mode emits the image from a pinhole
   instead of illuminating the scene as an area light. The area-light intensity
   is increased for visibility. Projected image:
   `Chelsea the cat <https://scikit-image.org/docs/stable/api/skimage.data.html#skimage.data.chelsea>`__,
   photographed by Stefan van der Walt and dedicated to the public domain under
   `CC0 1.0 Universal <https://creativecommons.org/publicdomain/zero/1.0/>`__.

A ``RectLight`` emits from one side of a rectangle along its local -Z axis.
Use it for panel lights, windows, and softboxes. It also uses the
:doc:`common light attributes <index>`.

.. figure:: ../img/light-type-rect.avif
   :alt: A test scene lit by a rectangular area light
   :align: center

   *A rect light produces illumination from a rectangular emitting surface.*

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 43, 57
   :class: compact-table

   "``float inputs:width = 1``", "Rectangle width along the local X axis, in scene units."
   "``float inputs:height = 1``", "Rectangle height along the local Y axis, in scene units."
   "``asset inputs:texture:file``", "Optional color texture that modulates emission across the rectangle."

The following examples create a 1.2-by-0.6 scene-unit panel light:

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/usd/data/light_types.usda
         :language: usda
         :start-after: # [snippet:doc-rect-light]
         :end-before: # [/snippet:doc-rect-light]
         :dedent: 4

   .. tab-item:: USD Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-rect-light-python]
         :end-before: # [/snippet:doc-rect-light-python]
         :dedent:

Projector Lights
----------------

A projector light turns a ``RectLight`` into a pinhole emitter. Instead of
emitting from the rectangular surface, it projects ``inputs:texture:file``
through the light center. Use this for slide projectors, patterned spotlights,
and calibrated projection systems.

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 46, 54
   :class: compact-table

   "``bool isProjector = false``", "Enables pinhole projector behavior. This control is supported only on ``RectLight``."
   "``asset inputs:texture:file``", "Color image to project. Without a texture, the projector emits its light color."
   "``asset projector:directionTexture:file``", "Optional float lookup texture that maps outgoing directions to UV coordinates in the projected color image. Use it to reshape or calibrate the projection."

The rect light's width and height define the default pinhole projection. Both
panels below use the same transform, dimensions, and texture. The area-light
intensity is increased to compensate for its much lower output at this small
size since its energy is emitted uniformly over all directions rather than being focused:

.. figure:: ../img/light-projector-enabled.avif
   :alt: Chelsea texture on an ordinary rect area light and projected through a rect projector light
   :align: center

   |projector-caption|

Authoring a Projector Light
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following examples enable a rect projector, assign Chelsea as its color
texture, and add a direction lookup:

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/usd/data/projector_lights.usda
         :language: usda
         :start-after: # [snippet:doc-projector-light]
         :end-before: # [/snippet:doc-projector-light]
         :dedent: 4

   .. tab-item:: USD Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-projector-light-python]
         :end-before: # [/snippet:doc-projector-light-python]
         :dedent:

Projection Direction Texture
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Without ``projector:directionTexture:file``, the projector uses a rectangular
pinhole mapping based on ``inputs:width`` and ``inputs:height``. A direction
texture replaces that mapping.

The direction texture is not a color image or a field of XYZ directions. It is
a floating-point lookup indexed by octahedrally encoded outgoing direction.
Its red and green channels store the UV coordinates used to sample
``inputs:texture:file``. Only values strictly between 0 and 1 emit light;
boundary values and values outside that range mask emission.

The following comparison uses the same Chelsea color texture. The second panel
uses a direction texture generated from an example OpenCV pinhole calibration:

.. figure:: ../img/light-projector-direction-texture.avif
   :alt: Chelsea projected with the default pinhole mapping and an OpenCV-calibrated direction mapping
   :align: center

   *The example-generated direction texture applies the OpenCV calibration
   without changing the projected color image.*

Generating A Direction Texture From OpenCV Calibration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Start with the calibrated image resolution, camera matrix, and distortion
coefficients. The matrix uses pixel units. The distortion vector follows
OpenCV's ordering for radial, tangential, thin-prism, and sensor-tilt terms:

.. literalinclude:: ../../examples/python/projector-light-calibration/generate_direction_texture.py
   :language: python
   :start-after: # [snippet:doc-projector-opencv-calibration]
   :end-before: # [/snippet:doc-projector-opencv-calibration]

The direction texture is indexed by an octahedral encoding of outgoing
directions. Generate one normalized direction at each texel center:

.. literalinclude:: ../../examples/python/projector-light-calibration/generate_direction_texture.py
   :language: python
   :start-after: # [snippet:doc-projector-octahedral-directions]
   :end-before: # [/snippet:doc-projector-octahedral-directions]
   :dedent:

Project the front-facing directions with ``cv2.projectPoints()`` and normalize
the resulting pixel coordinates to UV space. Store ``-1`` for directions that
OpenCV projects outside the image so the projector masks them:

.. literalinclude:: ../../examples/python/projector-light-calibration/generate_direction_texture.py
   :language: python
   :start-after: # [snippet:doc-projector-opencv-project]
   :end-before: # [/snippet:doc-projector-opencv-project]
   :dedent:

Finally, write the UV coordinates as float32 R and G channels in a square
OpenEXR image:

.. literalinclude:: ../../examples/python/projector-light-calibration/generate_direction_texture.py
   :language: python
   :start-after: # [snippet:doc-projector-write-direction-texture]
   :end-before: # [/snippet:doc-projector-write-direction-texture]
   :dedent:

.. note::

   The renderer samples the lookup with linear filtering. Values can blend
   across the boundary between valid UVs and the ``-1`` mask. Use enough lookup
   resolution for a smooth edge, and add an invalid guard band when you need a
   hard calibrated aperture boundary.

See :doc:`../examples/python_projector_light_calibration` for the complete
runnable example.
