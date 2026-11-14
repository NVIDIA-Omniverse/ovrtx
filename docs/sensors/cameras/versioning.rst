.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-cameras-versioning:

Model Versioning
================

A camera-attached sensor states which revision of its pipeline it wants, and
ovrtx runs that revision or nothing at all. Because there is no fallback to a
nearby revision, a scene that renders today produces the same pixels after the
pipeline gains new revisions.

This applies to the Camera generic core model and the Camera single-view stereo
depth model. Both are
applied to a ``Camera`` prim and both request a version the same way, so
everything below holds for either unless a section says otherwise.

Two independent values make up the request.

.. list-table::
   :header-rows: 1
   :widths: 18 30 52

   * - Value
     - Authored as
     - Meaning
   * - Schema version
     - The applied API schema class name
     - ``OmniSensorGenericCameraCoreAPI`` and
       ``OmniSensorGenericDepthSensorSingleViewAPI`` select schema 1. A ``_N``
       suffix selects schema ``N``, so ``OmniSensorGenericCameraCoreAPI_2``
       selects schema 2. The schema version governs the set of attributes the
       sensor understands.
   * - Model version
     - ``omni:sensor:modelVersion``
     - The behavior revision within that schema. The model version governs how
       the pipeline processes the image.

Exactly one ``OmniSensorGeneric*`` class may be applied to the camera prim. A
prim with none of them, or with two different ones, has no unambiguous schema
version and is rejected.

SPG Graph Compatibility
-----------------------

.. warning::

   SPG does not currently enforce version compatibility between nodes within
   a graph. Graph authors must ensure that sensor pipeline nodes correspond
   to the same resolved sensor version. Mixing nodes from different versions
   within a single graph is unsupported and results in undefined behavior.

This restriction applies within a single graph. Separate cameras may request
different sensor versions, with each request resolved independently.

Example USD
-----------

A Camera Core camera pinned to schema 1, model 0:

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../tests/docs/usd/data/camera_core_versioning.usda
         :language: usda
         :start-after: # [snippet:doc-camera-core-versioning]
         :end-before: # [/snippet:doc-camera-core-versioning]
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-camera-core-versioning-python]
         :end-before: # [/snippet:doc-camera-core-versioning-python]
         :dedent:

A depth sensor camera pinned to schema 1, model 0. The sensor parameters are
authored on the same prim as the request:

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../tests/docs/usd/data/depth_sensor_versioning.usda
         :language: usda
         :start-after: # [snippet:doc-depth-sensor-versioning]
         :end-before: # [/snippet:doc-depth-sensor-versioning]
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-depth-sensor-versioning-python]
         :end-before: # [/snippet:doc-depth-sensor-versioning-python]
         :dedent:

Writing ``omni:sensor:modelVersion``
------------------------------------

The attribute is a string holding either a single unsigned decimal integer or
the word ``latest``, which is matched without regard to case. Revisions are
numbered from ``0``, so ``"0"`` is the first revision of any schema.

``latest`` resolves to the highest revision declared for the requested schema.
It is convenient while a scene is under development, but it means the pipeline
behavior can change when ovrtx ships a new revision. Author a specific number
for content that must stay reproducible.

Anything else is malformed and rejected. In particular, dotted forms are not
accepted, so ``"1.0"`` and ``"0.0.0"`` are errors rather than requests for
revision 1 or 0. Leading signs, surrounding whitespace, and trailing characters
are rejected for the same reason.

Supported Versions
------------------

Camera Core, applied as ``OmniSensorGenericCameraCoreAPI``:

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Schema
     - Model
     - Pipeline
   * - 1
     - 0
     - The current Camera Core pipeline.

Depth sensor, applied as ``OmniSensorGenericDepthSensorSingleViewAPI``:

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Schema
     - Model
     - Pipeline
   * - 1
     - 0
     - The current single-view depth pipeline.

Unresolvable Requests
---------------------

If the requested pair is not in the table above, the camera is not built and
not scheduled. It produces no outputs for that sensor, and the reason is logged
once for the affected render product. The renderer does not substitute a
different revision, so an unsupported request is visible as absent output
rather than as output that quietly came from another version of the pipeline.

Rejecting one camera does not affect any other. Cameras in the same scene may
request different versions, and each is resolved on its own.

The Version Is Fixed Once Accepted
----------------------------------

The version is read when a render product first reaches the renderer, and it
holds for the life of that render product. Editing the applied schema class or
``omni:sensor:modelVersion`` afterward is rejected and logged; the already
accepted pipeline keeps running with the version it was built for. Every other
sensor attribute remains editable while the scene runs.

To render the same camera at a different version, remove its render product and
add it again with the new request authored.

Deprecated Versions
-------------------

A revision may be marked deprecated before it is removed. A deprecated revision
is rejected like an unsupported one by default. To allow soft-deprecated
revisions, configure :py:attr:`ovrtx.RendererConfig.sensors_allowed_deprecation_base`
in Python or :c:func:`ovrtx_config_entry_sensors_allowed_deprecation_base()` in C
when creating the renderer. Set the value to the running ovrtx version in plain
``major.minor.patch`` form. The value must match exactly and must be revisited
after every ovrtx upgrade.

A warning is emitted when a deprecated revision is accepted for a render
product. The version decision is cached, so subsequent frames do not repeat the
warning. Treat this opt-in as a short-term migration aid.

Migrating Depth Sensor Content
------------------------------

Bringing the depth sensor under this contract moved where it is authored. Older
content does not load, and there is no compatibility path: it has to be
re-authored.

.. list-table::
   :header-rows: 1
   :widths: 24 38 38

   * - What
     - Before
     - Now
   * - API schema
     - ``OmniSensorDepthSensorSingleViewAPI``
     - ``OmniSensorGenericDepthSensorSingleViewAPI``
   * - Applied to
     - The ``RenderProduct`` prim
     - The ``Camera`` prim
   * - Parameters
     - ``omni:rtx:post:depthSensor:*``
     - ``omni:sensor:depthSensor:*``
   * - Version request
     - Not expressed
     - ``omni:sensor:modelVersion``, defaulting to ``latest``

Moving the API onto the camera is what lets one scene hold depth cameras at
different versions: the request now travels with the camera it describes rather
than with the product that reads it.

Because ``omni:sensor:modelVersion`` defaults to ``latest``, content that
re-authors the schema and attributes but leaves the version alone keeps
tracking the newest revision. Author a specific number for content that must
stay reproducible.

Related
-------

- :doc:`Camera generic core model <../visual/camera_core/index>` — the camera sensor model whose
  revision this page's request selects.
- :doc:`Camera single-view stereo depth model <../visual/depth_camera/index>` — the depth model
  under the same contract.
- :doc:`USD Camera Attributes <usd_camera_attributes>` — the camera prim's attributes, including the sensor APIs
  applied to it.
