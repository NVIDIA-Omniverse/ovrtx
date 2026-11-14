.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Python: Semantic Segmentation
=============================

Renders semantic segmentation from the bundled ``ovrtx-robot-lineup.usda`` scene through ``/World/Camera`` and streams labeled results to `rerun.io <https://rerun.io/>`_.

The example uses an inline USDA root layer with a relative ``subLayers`` arc to the source scene. The inline layer authors semantic-label overrides for each top-level robot payload, a ``RenderProduct`` targeting ``/World/Camera``, and one ``RenderVar`` for each requested AOV, so the original USD file is left untouched.

.. pull-quote::

   *“Create a Python example that composes an existing scene with semantic label overrides and camera annotation outputs, renders several camera AOVs including semantic segmentation and its ID map, decodes metadata into human-readable labels, logs a useful visual layout to a viewer, and supports headless image export.”*

.. image:: ../../img/example-semantic-segmentation.avif
   :alt: Semantic segmentation example output
   :align: center

Prerequisites
-------------

- Python 3.10-3.13
- `uv <https://docs.astral.sh/uv/>`_
- NVIDIA RTX-capable GPU
- Supported NVIDIA driver
- Internet access to download the remote payloads referenced by ``ovrtx-robot-lineup.usda``
- Unsandboxed runtime execution

Running
-------

.. code-block:: bash

   cd examples/python/semantic-segmentation
   uv run main.py

Options
^^^^^^^

.. list-table::
   :header-rows: 1

   * - Flag
     - Description
   * - ``--resolution WIDTH HEIGHT``
     - Set the render resolution
   * - ``--warmup-frames N``
     - Render warmup frames before logging
   * - ``--step-dt SECONDS``
     - Set the renderer step delta and Rerun simulation timestamp interval
   * - ``--grid-columns N``
     - Set the number of columns in the Rerun AOV grid blueprint
   * - ``--usd PATH``
     - Render a different USD file
   * - ``--no-spawn``
     - Do not spawn Rerun; write display PNGs for image AOVs to ``_output/``

The example decodes ``SemanticIdMap`` before logging ``SemanticSegmentation``. It remaps renderer semantic IDs into compact 16-bit Rerun class IDs, logs an ``AnnotationContext`` with the semantic labels, and displays the segmentation image in the Rerun blueprint grid.

The first step from a newly built application will block for up to 5 minutes while shaders are compiled and cached.

The example captures the static AOVs after 50 warmup frames by default. It then moves all seven robots between their rest pose and small offsets for ten frames with the camera and warehouse fixed, and captures only :ref:`TargetMotionSD <camera-output-tables>`. Motion direction is shown as hue and displacement as brightness, with 20 pixels at full brightness. In headless mode, static PNGs are saved before animation and are not overwritten. The raw motion output is also saved as ``_output/TargetMotionSD.npy``.

The example also captures instance segmentation, bounding boxes,
visibility, ID maps and camera parameters. Named fields are saved as
``_output/<sourceName>.npz``; CPU params use the ``param_`` prefix. Images and
remaining single-tensor outputs use ``.npy``. Shape and content diagnostics are
written to ``_output/capture.json``. First-frame ID-map deltas are saved in ``_output/initial/``;
after warmup the unchanged scene has no new IDs, so a zero-entry delta is expected.
Empty outputs and mapping failures are recorded without preventing the other
outputs from being captured. See :doc:`../sensors/cameras/decoding_outputs` for
Python and C API decoding examples.

Visualizing Buffer Outputs
--------------------------

The example reads named bounding-box, occlusion, and instance-map tensors and
joins runtime IDs through ``InstanceMap`` and ``StableIdSemanticIdMap`` to prim
paths. The overlays show robot geometry only. Raw box outputs show individual
parts; semantic box outputs show the seven top-level robot bounds.

For a 3D box, the eight local corners are transformed by its world matrix,
then the view and projection matrices decoded from ``CameraParams``. Matrices
use row vectors. Divide clip XY by W, map NDC X to image width, and invert NDC Y
for image coordinates. Each edge is clipped against the camera near plane.
The projection illustration supports pinhole cameras. Camera and box coordinates already share scene units; do not apply
``metersPerSceneUnit`` again.

The code below projects one decoded box onto the camera image:

.. literalinclude:: ../../examples/python/semantic-segmentation/main.py
   :language: python
   :start-after: # [snippet:doc-lineup-project-box]
   :end-before: # [/snippet:doc-lineup-project-box]
   :dedent:

``OcclusionSD`` is shown by coloring loose robot-part boxes from green to red.
It reports one ratio per instance, so this visualization is not a per-pixel
occlusion mask. Records with ratio -1 are omitted.

ID-map outputs pair an annotated scene with decoded IDs, paths and semantic
labels. ``CameraParams`` shows the camera matrices and the 3D boxes projected
with them. Delta-map illustrations use the first frame, when IDs are introduced;
the static frame after warmup correctly has no new entries.

Decoded records, including complete identifiers and strings, are saved in
``_output/decoded.json``. Box selection and drawing counts are saved in
``_output/visualization.json``.

Minimal capture
---------------

Run the example with ``--render-mode MinimalRendering --resolution 960 540 --no-spawn``
to save Minimal previews under ``_output/minimal/``. It captures static outputs after
50 warmup frames, then moves the robots for a separate motion image. Minimal requests
``LdrColor`` and the supported Synthetic Data outputs; it omits ``HdrColor``.
A small ambient fill keeps every robot visible; Minimal ignores dome lights.

Path Tracing capture
--------------------

Use ``--render-mode PathTracing --resolution 960 540 --samples-per-pixel 128 --no-spawn``
to save PT tensors, PNG previews, and ``capture.json`` under ``_output/pt/``.
Path Tracing takes one setup step to obtain geometry paths for selection, then
captures one static frame at 128 samples per pixel. It does not use RT warmup frames.
The robots then move for one separate motion frame; static outputs are already saved.
The report retains empty outputs for diagnosis. LPE RenderVars use expression source names.

The example authors the PT render product and its output requests as follows:

.. literalinclude:: ../../examples/python/semantic-segmentation/main.py
   :language: python
   :start-after: # [snippet:doc-pt-lineup-render-product]
   :end-before: # [/snippet:doc-pt-lineup-render-product]
   :dedent:

Multi-Matte masks use geometry IDs 1–7 for the robots. The source scene assigns
IDs 8, 9 and 10 to warehouse walls, shelves and pallets, respectively.
Material IDs 101 and 102 select the C forklift's body and painted panels;
103 and 104 select the B forklift's body and glass.
Warehouse floors use geometry ID 11. Each requested Multi-Matte RenderVar
selects four independent coverage masks with these attributes:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Attributes on the RenderVar
     - Meaning
   * - ``int omni:rtx:pt:multimatte:rId`` (and ``gId``, ``bId``, ``aId``)
     - ID selected by that RGBA component. Omitted IDs and -1 produce zero coverage.
   * - ``bool omni:rtx:pt:multimatte:rIsMat`` (and ``gIsMat``, ``bIsMat``, ``aIsMat``)
     - False selects geometry ``primvars:multimatte_id``; true selects material ``multimatte_id``.

Request the configured RenderVars in the RenderProduct's ``orderedVars``.
Their requests determine allocation; no ``channelCount`` attribute is needed.
Up to eight Multi-Matte RenderVars provide 32 masks. A sparse request such as
``PtMultiMatte7`` allocates only its four masks. Separate RenderVars may use the
same Multi-Matte source name with different selectors.
When legacy product/global selectors are enabled, unconfigured RenderVars retain
their RGB selectors and opaque alpha.

The first output selects walls, shelves and pallets in RGB, and floors in alpha.
``MultiMatte.png`` combines corresponding RGB slices from outputs 0–3.
The grey strip underneath shows each output's full-frame alpha mask.
Its labels use G for geometry IDs and M for material IDs, in RGBA order;
G-1 is the disabled alpha component of the fourth output.

Selection-state preview
-----------------------

PT and RTPT also capture ``SelectionState``. The humanoid, forklift C, and Kaya
use selection groups 1, 2, and 3. Their previews are cyan, orange, and purple:
visible samples are bright, hidden samples have 25% brightness, and background
is black. Each pixel averages four decoded coverage colors. The uint16 channels
must not be interpreted directly as RGBA.

The following function maps the classification to display colors:

.. literalinclude:: ../../examples/python/semantic-segmentation/main.py
   :language: python
   :start-after: # [snippet:doc-selection-state-preview]
   :end-before: # [/snippet:doc-selection-state-preview]

See :doc:`c_selection_spg` to use the same AOV for custom outlines and fills.

Selection uses geometry paths from the first frame’s StableIdMap; selecting a
parent robot Xform does not recursively select its parts.
