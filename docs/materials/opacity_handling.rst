.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Opacity Handling
================

Path Tracing (PT) and Real-Time Path Tracing (RTPT) use material opacity to
control whether rays hit a surface or pass through its cutout regions. This lets
an opacity texture create holes in geometry, such as the gaps between leaves or
in a fence, without modeling each opening.

The renderer analyzes materials to determine whether cutout-opacity evaluation
is needed, matching known parameter names and their values. This works for
built-in materials with recognized controls, but custom MDL and MaterialX
materials may use parameters the renderer does not recognize. For those
materials, you can use ``omni:rtx:enableCutoutOpacity`` to override whether the
renderer allows cutout opacity. Disabling unnecessary cutout evaluation can
avoid extra work during ray intersections.
Scenes with many custom MDL or MaterialX materials may see performance issues
from this misclassification, manifesting as a high number of any-hit shader
invocations even though all the materials are fully opaque. You can diagnose
this in RTPT with the :ref:`any-hit debug view <debug-view-any-hit-count>`.

Overriding Cutout Opacity
-------------------------

Author ``omni:rtx:enableCutoutOpacity`` as a custom boolean attribute on the bound
**Material prim**, not on its Shader child, geometry, or RenderProduct. No applied
API schema is required.

To disable cutout opacity, add this declaration inside the existing Material prim:

.. code-block:: usda

   custom bool omni:rtx:enableCutoutOpacity = false

When the override applies, cutout holes become solid in both PT and RTPT. This
controls surface visibility; it does not disable transmission or refraction
through glass.

.. list-table::
   :header-rows: 1
   :widths: 20 80
   :class: compact-table

   * - Authored value
     - Behavior when no recognized opacity control is found
   * - ``false``
     - Disables cutout opacity, ignoring the material's cutout mask.
   * - ``true``
     - Allows the material's cutout opacity to be evaluated. It does not create
       holes in a material whose opacity is always one.
   * - Unauthored
     - Leaves cutout opacity allowed. The renderer can still skip evaluation
       when it determines that the material's opacity is always one.

Parameter Precedence
--------------------

This attribute is a fallback, not an unconditional override. Recognized material
controls take precedence: ``enable_opacity``, the material's registered
alpha-cutout enable parameter, and ``alpha_mode``. When one of these controls is
found, change the shader's opacity controls instead. The attribute cannot
overrule an ``alpha_mode`` that marks the material as opaque.

The override uses the renderer's per-instance opacity control, which is enabled
by default. If an application disables that control, this attribute is ignored.

.. note::

   ``omni:rtx:enableCutoutOpacity`` changes cutout-opacity handling in both PT and
   RTPT. The separate ``omni:rtx:enableTransmission`` attribute changes material
   translucency classification; it does not disable the transmission shader.
   See :ref:`rtpt-material-transmission-override` for that RTPT workflow.
