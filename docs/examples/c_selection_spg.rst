.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

C: Custom Selection with SPG
============================

Draw custom selection outlines and patterned fills by processing ``LdrColor``
and ``SelectionState`` with a Slang Sensor Processing Graph (SPG) node.
The renderer supplies selection groups and visibility at output resolution;
SPG controls colors, outline widths and shapes, and visible and hidden fills.
The C++ example presents ``CustomSelection`` in its own Vulkan/CUDA viewer.

.. figure:: ../../img/example-selection-spg.avif
   :alt: Custom selection outlines and patterned fills on a sphere, torus, and cube
   :align: center
   :width: 700px

   *Three selection groups use cyan rounded outlines, purple square outlines,
   and orange diamond outlines on textured ground under a studio HDRI.*

Wiring the Render Outputs
-------------------------

The scene requests the two input AOVs, connects them to the Slang node, and
publishes its result as ``CustomSelection``. The following excerpt also defines
style inputs that can be edited without rebuilding the viewer:

.. literalinclude:: ../../examples/c/selection-spg/selection_scene.usda
   :language: usda
   :start-after: # [snippet:selection-spg-render-graph]
   :end-before: # [/snippet:selection-spg-render-graph]
   :prepend: #usda 1.0

Assigning Selection Groups
--------------------------

Use the :doc:`selection API <../scene/picking>` to assign geometry to groups.
After the initial setup step completes, the example resolves the sphere, torus,
and cube paths and assigns groups 1, 2, and 3 respectively:

.. literalinclude:: ../../examples/c/selection-spg/src/main.cpp
   :language: cpp
   :start-after: // [snippet:selection-spg-initial-selection]
   :end-before: // [/snippet:selection-spg-initial-selection]
   :dedent:

Styling the Selection
---------------------

Each ``SelectionState`` pixel contains four coverage samples. In each sample,
bits 0–7 identify the selection group and bit 8 indicates visibility. Group zero
means no selected geometry. The following Slang shader expands the mask,
decodes and composites each coverage sample independently, and averages the
results:

.. literalinclude:: ../../examples/c/selection-spg/SelectionOutline.slang
   :language: hlsl
   :start-after: // [snippet:selection-spg-outline-kernel]
   :end-before: // [/snippet:selection-spg-outline-kernel]

The Lua launch script checks input shapes, allocates the output image, and binds
the images and styling parameters in the shader's binding order:

.. literalinclude:: ../../examples/c/selection-spg/SelectionOutline.slang.lua
   :language: lua
   :start-after: -- [snippet:selection-spg-launch]
   :end-before: -- [/snippet:selection-spg-launch]

Edit the inline shader inputs to change outline width and shape, fill opacity,
dash period, and hidden-fill patterns. The initial styles are:

.. list-table::
   :header-rows: 1
   :widths: 15 10 40 35

   * - Object
     - Group
     - Visible style
     - Hidden fill
   * - Sphere
     - 1
     - Cyan, rounded outline, translucent solid fill
     - Stippling
   * - Torus
     - 2
     - Purple, thin square outline, no fill
     - Cross-hatching
   * - Cube
     - 3
     - Orange, diamond outline, striped fill
     - Single-direction hatching

Edit the Slang shader to change the drawing algorithm. See
:doc:`../spg/overview` for the SPG authoring reference and
:doc:`../sensors/cameras/outputs` for the full ``SelectionState`` output format.

Prerequisites
-------------

- CMake 3.18 or newer and a C++17 compiler
- An NVIDIA RTX-capable GPU and a supported driver
- CUDA Toolkit 12.0 or newer
- Vulkan SDK 1.3.250 or newer, including ``glslc``
- On Linux, the GLFW development dependencies for your window system

Building and Running
--------------------

The CMake helpers find installed ovrtx and ovstage SDK packages through
``CMAKE_PREFIX_PATH``, or fetch them when absent. Dependency downloads require
internet access. Build and run from the example directory:

.. code-block:: bash

   cd examples/c/selection-spg
   cmake -S . -B _build -DCMAKE_BUILD_TYPE=Release
   cmake --build _build --config Release
   ./_build/ovrtx-selection-spg

On Windows, run ``_build/Release/ovrtx-selection-spg.exe``.
For headless output, run either the default RTPT scene or its PT variant:

.. code-block:: bash

   ./_build/ovrtx-selection-spg --headless --num-frames 100
   ./_build/ovrtx-selection-spg --usd selection_pt.usda --headless --num-frames 100

On Windows, use the same arguments with the executable path above.
Headless mode writes ``out.png`` with all three group styles. The viewer reads
editable USD, Lua, and Slang assets directly from the source directory; changes
take effect on the next launch. The scene renders at 1920 × 1080 independently
of window size.

Viewer Controls
---------------

- Left-click or drag to replace the selection, preserving each object's group.
- Shift-click to toggle an object. Shift-clicking empty background preserves
  the selection; Shift-drag replaces it.
- Right-drag to orbit; use the wheel to dolly.

Select only the sphere to see dashed hidden outlines and stippling behind the cube.

Limitations
-----------

``SelectionState`` represents the nearest selected surface only. Objects in the
same group form a combined mask. Expanded outlines inherit visibility from their
selected source samples; they do not query scene depth beneath the expanded
stroke. Adaptive coverage can miss features thinner than the center sampling
pattern.

XR foveation unwarp is unsupported for this AOV. When unwarp is authored, the
renderer clears ``SelectionState`` and logs a warning; beauty output continues.
