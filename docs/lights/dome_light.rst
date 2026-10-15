.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Dome Light
==========

A ``DomeLight`` emits inwards from an environment surrounding the scene. Set a
high-dynamic-range texture to provide image-based lighting, or leave the texture
unset to use the :doc:`common color and intensity controls <index>`.

.. figure:: ../img/light-type-dome.avif
   :alt: A test scene illuminated by a high-dynamic-range environment on a dome light
   :align: center

   *A textured dome light supplies both environment illumination and a background.*

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 43, 57
   :class: compact-table

   "``asset inputs:texture:file``", "Color texture, normally a high-dynamic-range environment image."
   "``token inputs:texture:format = ""automatic""``", "Texture parameterization: ``automatic``, ``latlong``, ``mirroredBall``, ``angular``, or ``cubeMapVerticalCross``."

The following examples create a dome light using a latitude-longitude
environment texture:

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/usd/data/light_types.usda
         :language: usda
         :start-after: # [snippet:doc-dome-light]
         :end-before: # [/snippet:doc-dome-light]
         :dedent: 4

   .. tab-item:: USD Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-dome-light-python]
         :end-before: # [/snippet:doc-dome-light-python]
         :dedent:

Multiple Dome Lights
--------------------

.. figure:: ../img/light-multiple-domes.avif
   :alt: Objects lit by a studio dome against an outdoor dome background, with studio lights reflected in the chrome sphere
   :align: center

   *The outdoor dome supplies only the camera background. A second studio dome,
   hidden from direct camera rays, illuminates the objects and appears in the
   chrome sphere's reflection.*

ovrtx supports multiple dome lights in the same scene by default. Create a
separate ``DomeLight`` prim for each environment you want to combine. Each dome
can have its own texture, rotation, color, intensity, and exposure. This lets
you combine an environment with a separate studio-lighting texture or a
constant-color fill.

The domes' contributions add together; they are not automatically averaged or
normalized. Adding a second dome can therefore make the scene brighter. Adjust
each dome's :doc:`intensity and exposure <common_attributes>` to balance its
contribution. For example, two identical domes at half the original intensity
produce the same combined emission as one dome at the original intensity.

Choosing Which Domes Appear in the Background
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A dome can illuminate the scene without appearing in the camera's background.
For example, you can show an outdoor environment in the background while using
a second, hidden studio dome to light the subject. The **DomeLight**'s
``visibleInPrimaryRay`` attribute controls whether the light is visible to the camera or not.

When using :doc:`scene partitions <../sensors/cameras/scene_partitions>`, the
domes available to a camera depend on its partition. Multiple domes do not
bypass scene-partition isolation.

Using Separate Domes for the Background and Lighting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To show one environment to the camera while lighting the scene with a different
environment, create two dome lights and configure them as follows. Ensure
``omni:rtx:lights:visibilityOverride = "perLight"`` (the default) on the RenderProduct.

.. csv-table::
   :header: "Attribute", "Background dome", "Lighting dome"
   :widths: 40, 30, 30
   :class: compact-table

   "``inputs:texture:file``", "Image the camera should see", "Environment used for illumination"
   "``visibleInPrimaryRay``", "``true``", "``false``"
   "``inputs:diffuse``", "``0``", "``1``"
   "``inputs:specular``", "``0``", "``1``"

Setting both response multipliers to zero on the background dome removes its
diffuse and specular contributions while preserving its appearance to direct
camera rays. Hiding the lighting dome from primary rays removes it from the
background while retaining its illumination and reflections.

Keep both domes' intensities nonzero. Adjust the background dome's intensity or
exposure to control the visible background brightness, and adjust the lighting
dome's intensity or exposure to control illumination. Setting the background
dome's intensity to zero would also make its camera-visible image black.

.. _finite-dome-modes:

Finite Dome Modes
-----------------

Finite dome modes project the environment onto virtual ground, sphere, or box
geometry. They are useful when an infinite environment gives incorrect
parallax, scale, or horizon placement. The projection geometry affects dome
lighting and background rays; it does not create renderable USD geometry.

``OmniFiniteDomeLightAPI`` is auto-applied to every ``DomeLight`` and provides
six modes:

.. csv-table::
   :header: "Mode", "Behavior"
   :widths: 28, 72
   :class: compact-table

   "``infinite``", "Standard infinite environment-map lighting. This is the default."
   "``ground``", "Infinite environment with the lower portion projected onto a ground plane."
   "``sphere``", "Projects the environment onto a finite sphere. Rays that miss the sphere return black."
   "``box``", "Projects the environment onto a finite box. Rays that miss the box return black."
   "``sphereWithGround``", "Finite sphere plus a projected ground plane that replaces the lower portion."
   "``boxWithGround``", "Finite box plus a projected ground plane that replaces the lower portion."

The following comparison uses the same environment, camera, and subject for
all six modes:

.. figure:: ../img/light-finite-dome-modes.avif
   :alt: Comparison of infinite, ground, sphere, box, sphere with ground, and box with ground dome light modes
   :align: center

   *Finite modes project the same environment onto different virtual boundaries.*

Finite Dome Attributes
^^^^^^^^^^^^^^^^^^^^^^

Author these attributes on the ``DomeLight`` prim:

.. csv-table::
   :header: "USD declaration", "Description"
   :widths: 48, 52
   :class: compact-table

   "``token omni:rtx:domeLight:mode = ""infinite""``", "Selects the projection mode listed above."
   "``float omni:rtx:domeLight:radius = 100``", "Base radius for ``sphere`` and ``sphereWithGround``. The geometry transform's X scale multiplies this value."
   "``float3 omni:rtx:domeLight:size = (200, 200, 200)``", "Full width, height, and depth for ``box`` and ``boxWithGround``. The geometry transform scales each axis independently."
   "``float omni:rtx:domeLight:groundTextureScale = 0``", "Sets the projection's vanishing-point distance along its up axis. ovrtx uses the absolute value."
   "``rel coordSys:domeGeometry:binding``", "Optionally targets an Xformable prim that positions, rotates, and scales the finite boundary independently. The identity transform is used when no target is authored."

The ``DomeLight`` transform controls environment texture orientation and the
ground origin. The optional ``coordSys:domeGeometry:binding`` target controls
the finite sphere or box center, orientation, and scale. This separation lets
you orient the image independently from its projection boundary.

Radius
^^^^^^

The following comparison changes ``omni:rtx:domeLight:radius`` on a
``sphereWithGround`` dome:

.. figure:: ../img/light-finite-dome-radius.avif
   :alt: Sphere-with-ground dome lights with radius values of 50, 100, and 200
   :align: center

   *Radius changes the extent and curvature of the spherical projection boundary.*

Size
^^^^

The following comparison changes ``omni:rtx:domeLight:size`` on a
``boxWithGround`` dome:

.. figure:: ../img/light-finite-dome-size.avif
   :alt: Box-with-ground dome lights with sizes of 100 cubed, 200 cubed, and 400 by 200 by 300
   :align: center

   *Size controls the width, height, and depth of the box projection boundary.*

Ground Texture Scale
^^^^^^^^^^^^^^^^^^^^

The following comparison changes
``omni:rtx:domeLight:groundTextureScale`` on a ``boxWithGround`` dome:

.. figure:: ../img/light-finite-dome-ground-texture-scale.avif
   :alt: Box-with-ground dome lights with ground texture scale values of 10, 30, and 100
   :align: center

   *Ground texture scale changes the vanishing-point distance used to project the environment onto the ground.*

Authoring A Finite Dome
^^^^^^^^^^^^^^^^^^^^^^^

The following examples create a sphere-with-ground dome and bind separate
projection geometry. The API schema is already auto-applied to the dome light.

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/usd/data/finite_dome_lights.usda
         :language: usda
         :start-after: # [snippet:doc-finite-dome-light]
         :end-before: # [/snippet:doc-finite-dome-light]
         :dedent: 4

   .. tab-item:: USD Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-finite-dome-light-python]
         :end-before: # [/snippet:doc-finite-dome-light-python]
         :dedent:
