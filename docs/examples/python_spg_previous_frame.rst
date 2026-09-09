.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Python: SPG Previous Frame
==========================

An SPG node that reads the same AOV twice, once as the renderer produced it this frame and once as
it was one frame ago, and publishes the difference. Whatever moved lights up; whatever held still
goes dark.

Running
-------

.. code-block:: bash

   uv run main.py                                  # CUDA
   uv run main.py --scene motion_scene_slang.usda  # Slang

The first step compiles the kernel and can take up to a minute on a cold shader cache. A successful
run writes three PNGs to ``_output/`` and prints::

    pixels changed while moving: 3281
    pixels changed while still:  50

The Scene
---------

The whole mechanism is the ``:-1`` on one ``sourceName``. Highlighted: the two RenderVars the node
reads, which name the same AOV at two different times.

.. literalinclude:: ../../examples/python/spg-previous-frame/motion_scene.usda
   :language: usda
   :start-after: # [snippet:render-graph]
   :end-before: # [/snippet:render-graph]
   :emphasize-lines: 11, 19
   :caption: ``motion_scene.usda``

The Node
--------

Two ordinary ``opaque`` ports. Nothing here says one of them is a past frame:

.. filtered-literalinclude:: ../../examples/python/spg-previous-frame/MotionKernel.usda
   :language: usda
   :start-after: # [snippet:motion-shader-definition]
   :end-before: # [/snippet:motion-shader-definition]
   :exclude-pattern: ^\s*#\s*\[/?snippet:

.. filtered-literalinclude:: ../../examples/python/spg-previous-frame/MotionKernel.cu.lua
   :language: lua
   :start-after: -- [snippet:motion-launch]
   :end-before: -- [/snippet:motion-launch]
   :exclude-pattern: ^\s*--\s*\[/?snippet:

What the Run Proves
-------------------

A node wired to the live AOV twice would report a near-zero count while the ball moves as well as
while it holds still. The moving half is what shows that ``:-1`` resolved to a past frame.

The count while still is not zero, and should not be expected to be: a path-traced render keeps
refining, so consecutive frames of a static scene differ slightly. Neither count repeats exactly
between runs. The gap between them is what carries the result.

Refer to :doc:`../spg/do/previous_frame` for how ``:-N`` behaves for N up to 8, and for how it
differs from a stateful output.
