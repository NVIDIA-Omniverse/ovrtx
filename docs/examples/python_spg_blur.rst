.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Python: SPG Separable Blur
==========================

Two chained SPG nodes blur ``LdrColor``, first along x and then along y, and publish the result as
``LdrBlurred``. The tap weights are built in the launch script rather than on the GPU, because they
depend only on the radius.

The radius is a USD attribute the run rewrites between renders: at radius 0 the weight table is
``{1.0}`` and the blur is the identity.

Running
-------

.. code-block:: bash

   uv run main.py                                # CUDA
   uv run main.py --scene blur_scene_slang.usda  # Slang

The first step compiles the kernel and can take up to 5 minutes on a cold shader cache. A successful
run writes five PNGs to ``_output/``: ``input.png``, the rendered ``LdrColor``;
``blurred-one-pass.png``, after the horizontal pass only; ``blurred.png``, after both passes at
radius 8; and, once the radius is set to 0, ``radius-0-input.png`` and ``radius-0.png``, that
frame's ``LdrColor`` and the published AOV, which match pixel for pixel.

The Weights
-----------

Each of the two blur nodes builds its table for the first radius and again when the radius changes,
rather than once per frame: the radius changes once during the run, so each node builds its table
twice.

.. filtered-literalinclude:: ../../examples/python/spg-blur/BlurKernel.cu.lua
   :language: lua
   :start-after: -- [snippet:blur-weights]
   :end-before: -- [/snippet:blur-weights]
   :exclude-pattern: ^\s*--\s*\[/?snippet:

The Two Launches
----------------

The horizontal pass takes one thread per output pixel, which is SPG's default launch geometry:

.. filtered-literalinclude:: ../../examples/python/spg-blur/BlurKernel.cu.lua
   :language: lua
   :start-after: -- [snippet:blur-horizontal-launch]
   :end-before: -- [/snippet:blur-horizontal-launch]
   :exclude-pattern: ^\s*--\s*\[/?snippet:

The vertical pass gives each thread a whole column to walk, so the iteration domain is the width
alone and the geometry has to be stated:

.. filtered-literalinclude:: ../../examples/python/spg-blur/BlurKernel.cu.lua
   :language: lua
   :start-after: -- [snippet:blur-vertical-launch]
   :end-before: -- [/snippet:blur-vertical-launch]
   :exclude-pattern: ^\s*--\s*\[/?snippet:
   :emphasize-lines: 22-23

Sharing Code Between the Passes
-------------------------------

Both passes run the same tap loop. On Slang it lives in its own module beside the shader, reached
with ``import BlurTaps;``:

.. filtered-literalinclude:: ../../examples/python/spg-blur/BlurTaps.slang
   :language: hlsl
   :start-after: // [snippet:blur-module]
   :end-before: // [/snippet:blur-module]
   :exclude-pattern: ^\s*//\s*\[/?snippet:

CUDA has no equivalent. One include directory is searched and it is never the ``.cu``'s own, so
the two CUDA passes share the loop through a ``__device__`` function in the same file. Refer to
:doc:`../spg/do/precompiled`.

Changing the Radius
-------------------

``inputs:radius`` is connected to nothing, so writing it on the Shader prim takes effect on the
next step with no reset:

.. filtered-literalinclude:: ../../examples/python/spg-blur/main.py
   :language: python
   :start-after: # [snippet:blur-write-radius]
   :end-before: # [/snippet:blur-write-radius]
   :exclude-pattern: ^\s*#\s*\[/?snippet:

Refer to :doc:`../spg/do/upload_data`, :doc:`../spg/do/caching`,
:doc:`../spg/do/launch_geometry` and :doc:`../spg/do/runtime_changes` for the same material in
prose.
