.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Python: Light Path Expressions
==============================

This example sublayers the robot-lineup scene, adds diffuse-reflection,
glossy-reflection, glossy-transmission, and caustics LPE RenderVars alongside
:ref:`HdrColor <camera-output-tables>`, renders them in Path Tracing mode, and
converts the results to sRGB ``uint8`` images for Rerun or PNG output.

.. figure:: ../img/light-path-expressions.avif
   :alt: Beauty, diffuse reflection, glossy reflection, glossy transmission, and caustics outputs from the robot-lineup scene
   :align: center

   *The beauty image and four LPE outputs rendered from the same camera.*

.. pull-quote::

   *“Create a compact ovrtx example that composes an existing scene with
   reflection, transmission, and caustics LPE RenderVars, renders them with
   HdrColor, and records sRGB ``uint8`` images.”*

See :doc:`../sensors/cameras/light_path_expressions` for LPE syntax, authoring,
labels, and limitations.

Authoring
---------

The example layer applies the PathTracing settings schema, disables radiance caching,
and requests beauty plus four LPE outputs. The USDA and ``usd-core`` snippets
below author equivalent RenderProducts.

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../examples/python/lpes/lpe-layer.usda
         :language: usda
         :start-after: # [snippet:doc-example-lpe-render-vars]
         :end-before: # [/snippet:doc-example-lpe-render-vars]

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-example-lpe-render-vars-python]
         :end-before: # [/snippet:doc-example-lpe-render-vars-python]
         :dedent:

Reading The Outputs
-------------------

The example maps every returned RenderVar, copies it before unmapping, and
converts linear floating-point outputs to display-ready sRGB images.

.. literalinclude:: ../../examples/python/lpes/main.py
   :language: python
   :start-after: # [snippet:doc-read-lpe-outputs]
   :end-before: # [/snippet:doc-read-lpe-outputs]
   :dedent:

Running
-------

.. code-block:: bash

   uv run main.py
   uv run main.py --rrd _output/lpes.rrd
   uv run main.py --no-rr --png _output/light-path-expressions.png

The first run may take up to 5 minutes while shaders compile and cache.
