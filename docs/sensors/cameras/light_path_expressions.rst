.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Light Path Expressions
======================

Light Path Expressions (LPEs) select the light-transport paths accumulated into
a RenderVar. Use them to split a Path Tracing image into compositing passes such
as diffuse reflection, glossy reflection, emission, direct light, or caustics.

.. figure:: ../../img/light-path-expressions.avif
   :alt: Beauty, diffuse reflection, glossy reflection, glossy transmission, and caustics outputs from one scene
   :align: center
   :target: ../../examples/python_lpes.html

   *One Path Tracing image separated into beauty and four LPE outputs. Each LPE
   contains only the light-transport paths matched by its expression.*

LPEs are available in ``PathTracing`` mode. Author each expression as the
``sourceName`` of a ``RenderVar``, set its ``sourceType`` to ``lpe``, and target
the RenderVar from the RenderProduct's ``orderedVars`` relationship.

Author LPE Outputs
------------------

The RenderProduct in the snippet below requests the beauty output plus diffuse- and glossy-reflection
LPEs. Disable radiance caching when LPE outputs must contain all contributions by adding
``bool omni:rtx:pt:radianceCache:enabled = false`` to the ``RenderProduct``.
Cached contributions do not retain their path history and are omitted from LPE
outputs even though they remain present in the beauty output.

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../../tests/docs/usd/data/light_path_expressions.usda
         :language: usda
         :start-after: # [snippet:doc-lpe-render-vars]
         :end-before: # [/snippet:doc-lpe-render-vars]

   .. tab-item:: Python

      .. literalinclude:: ../../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-lpe-render-vars-python]
         :end-before: # [/snippet:doc-lpe-render-vars-python]
         :dedent:

Syntax
------

An LPE is a regular expression over the events along a light-transport path.
Expressions can run from the eye or camera (``E``) to a light (``L``), or in
the reverse direction. Every expression, including every branch of an
alternation, must contain exactly one eye marker and one light marker.

A scattering event combines an interaction type and scattering mode inside
angle brackets. For example, ``<RD>`` means diffuse reflection, ``<RG>`` means
glossy reflection, and ``<TS>`` means specular transmission. An optional
single-quoted label restricts an event to a named scene object, as in
``<RD'ground'>``.

Read ``E<RD>.*L`` from left to right as:

1. Start at the camera (``E``).
2. Match a diffuse-reflection event (``<RD>``).
3. Match zero or more additional scattering events (``.*``).
4. End at any light (``L``).

Terminal Tokens
~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 15 25 60

   * - Token
     - Category
     - Meaning
   * - ``E``
     - Path endpoint
     - Eye or camera vertex.
   * - ``L``
     - Path endpoint
     - Any light.
   * - ``La``
     - Light subtype
     - Area light. RTX currently produces this marker.
   * - ``Le``
     - Light subtype
     - Environment or background light. RTX currently produces this marker.
   * - ``Lp``
     - Light subtype
     - Point light. This marker parses but RTX does not currently produce it.
   * - ``Lm``
     - Light subtype
     - Matte lookup or backplate light. This marker parses but RTX does not currently produce it.
   * - ``Lv``
     - Light subtype
     - Emissive volume. This marker parses but RTX does not currently produce it.
   * - ``I``
     - Path endpoint
     - Irradiance marker.
   * - ``R``
     - Event type
     - Reflection.
   * - ``T``
     - Event type
     - Transmission.
   * - ``V``
     - Event type
     - Volume scattering.
   * - ``D``
     - Scattering mode
     - Diffuse scattering.
   * - ``G``
     - Scattering mode
     - Glossy scattering.
   * - ``S``
     - Scattering mode
     - Ideal specular (delta) scattering. Rough specular reflection or transmission is classified as glossy (``G``).
   * - ``'name'``
     - Label
     - A geometry or light label authored in USD.
   * - ``.``
     - Wildcard
     - Any ordinary scattering event; it does not match the special ``E``, ``L``, or ``I`` markers.

Operators And Quantifiers
~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Syntax
     - Meaning
   * - ``AB``
     - Match ``A`` followed by ``B``.
   * - ``A|B``
     - Match either ``A`` or ``B``. Every branch must contain one ``E`` and one ``L``.
   * - ``A?``
     - Match zero or one occurrence of ``A``.
   * - ``A*``
     - Match zero or more occurrences of ``A``.
   * - ``A+``
     - Match one or more occurrences of ``A``.
   * - ``A{n}``
     - Match exactly ``n`` occurrences of ``A``.
   * - ``A{n,m}``
     - Match between ``n`` and ``m`` occurrences of ``A``, inclusive.
   * - ``A{n,}``
     - Match at least ``n`` occurrences of ``A``.
   * - ``(...)``
     - Group a subexpression.
   * - ``[...]``
     - Match any member of a set, such as ``[DG]``.
   * - ``[^...]``
     - Match anything except members of a set.
   * - ``^expression``
     - Complement the complete expression. Complement is valid only at the top level.
   * - ``A & B``
     - Match paths accepted by both expressions.
   * - ``name: expression``
     - Declare a reusable expression variable.
   * - ``$name``
     - Use a previously declared expression variable.

Quantifiers bind most tightly, followed by concatenation, then alternation.
``<TS>`` is one specular-transmission event; unbracketed ``TS`` means two
consecutive abbreviated events.

Common Expressions
~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Expression
     - Output
   * - ``E.*L``
     - All light paths.
   * - ``E<RD>.*L``
     - Diffuse reflection visible from the camera.
   * - ``E<RG>.*L``
     - Glossy reflection visible from the camera.
   * - ``EDG.*L``
     - Caustics.
   * - ``EL``
     - Directly visible emission.
   * - ``E.{2,}L``
     - Indirect illumination with at least two scattering events.

Labels
------

Labels restrict an event to named scene elements. Author
``primvars:omni:label`` as a uniform token on geometry and ``omni:label`` as a
uniform token on lights. For example, ``E<RD'ground'>.*L`` selects diffuse
reflection at geometry labelled ``ground``, while ``E.*<L'key'>`` selects paths
ending at a light labelled ``key``.

Read And Visualize Outputs
--------------------------

After stepping the RenderProduct, map each LPE output like any other camera
RenderVar. LPE outputs use the same linear floating-point image representation
as :ref:`HdrColor <camera-output-tables>`. See :doc:`../../examples/python_lpes`
for a runnable example that reads, converts, and displays all requested outputs.

Limitations
-----------

* A RenderProduct can request at most nine LPE RenderVars. Additional LPEs are ignored.
* LPE outputs are supported only in ``PathTracing`` mode.
* Leave ``omni:rtx:pt:radianceCache:enabled`` disabled when LPE outputs must be
  complete. When it is enabled, cached contributions remain in beauty but are
  omitted from LPE outputs because they do not retain path history.
* Area (``La``) and environment (``Le``) light markers are produced. Point
  (``Lp``), emissive-volume (``Lv``), and matte (``Lm``) markers parse but do
  not currently match renderer contributions.
* Volume-scattering events are currently classified as glossy (``VG``).

Further Reading
---------------

* :doc:`render_modes/path_tracing`
* :doc:`outputs`
* :doc:`../sensor_outputs`
* :doc:`../../examples/python_lpes`
* `OpenUSD UsdRenderVar documentation <https://openusd.org/release/api/class_usd_render_var.html>`_
