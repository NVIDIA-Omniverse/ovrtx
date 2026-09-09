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
depend on nothing but the radius.

The radius is a USD attribute the run rewrites between renders, which is what makes the checks
exact: at radius 0 the weight table is ``{1.0}``, the blur is the identity, and the published AOV
has to equal ``LdrColor`` byte for byte.

Running
-------

.. code-block:: bash

   uv run main.py                                # CUDA
   uv run main.py --scene blur_scene_slang.usda  # Slang

The first step compiles the kernel and can take up to a minute on a cold shader cache. A successful
run writes ``_output/input.png`` and ``_output/blurred.png`` and prints::

    radius 0, pixels differing from the input: 0
    radius 8, sharpest edge: 122 -> 24
    radius 8, sharpest edge after one pass: 55
    radius 8, mean brightness drift: 0.003
    weight tables built: 2 (radii 8, 0)

The Weights
-----------

Built once per distinct radius rather than once per frame. The ``warning`` is what makes that
countable: over some fifty rendered frames it appears twice.

.. filtered-literalinclude:: ../../examples/python/spg-blur/BlurKernel.cu.lua
   :language: lua
   :start-after: -- [snippet:blur-weights]
   :end-before: -- [/snippet:blur-weights]
   :exclude-pattern: ^\s*--\s*\[/?snippet:

The Two Launches
----------------

The horizontal pass takes one thread per output pixel, which is what SPG derives when the launch
script states nothing:

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

Reading Back the Half-Finished Blur
-----------------------------------

The first pass feeds the second pass and a RenderVar of its own, so all three stages are readable
from the host. The run checks that the sharpest edge in the image falls at each step, which only
holds if the fan-out reached both consumers. The three figures move with the render; their order
does not.

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
