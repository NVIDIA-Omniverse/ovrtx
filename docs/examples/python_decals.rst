.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

Python: Decals
==============

Projects three red RTX wordmarks and three silver metallic NVIDIA logos onto the curved green logo from the shared test scene. Loads the scene through an attached runtime stage and renders its camera.

.. pull-quote::

   *"Create a minimal Python example that loads USD-authored decals through a runtime stage, renders them, and saves the color output."*

.. figure:: ../img/example-decals.avif
   :alt: Enlarged red RTX lettering overlapped by silver NVIDIA logos on a curved green logo
   :align: center

   *Silver NVIDIA logos (priority 10) overlap red RTX lettering (priority 0).
   Cutouts reveal the lower decal or the green receiver.*

The example loads the shared scene and renders enough frames for image quality:

.. literalinclude:: ../../examples/python/decals/main.py
   :language: python
   :start-after: # [snippet:doc-decals-python-render]
   :end-before: # [/snippet:doc-decals-python-render]
   :dedent:

It then maps :ref:`LdrColor <camera-output-tables>` to the CPU and writes a PNG:

.. literalinclude:: ../../examples/python/decals/main.py
   :language: python
   :start-after: # [snippet:doc-decals-python-save]
   :end-before: # [/snippet:doc-decals-python-save]
   :dedent:

Prerequisites
-------------

- Python 3.10-3.13
- `uv <https://docs.astral.sh/uv/>`_
- An NVIDIA RTX-capable GPU and a supported driver

Running
-------

.. code-block:: bash

   cd examples/python/decals
   uv run main.py --png

A successful run writes ``_output/decals.png``. Run without ``--png`` to open
Rerun, or use ``--rrd _output/decals.rrd`` to save a recording. An optional
path after ``--png`` selects a different PNG location. Both output options
can be combined.

Scene and Masks
---------------

The scene reuses the base logo geometry, green plastic material, grid, and
studio environment. Six ``OmniDecal`` prims are bound only to the logo mesh:
three red RTX wordmarks and three silver NVIDIA logos. Silver has
priority 10 and red has priority 0. The upper silver logo intentionally
overlaps the upper RTX wordmark. A third RTX wordmark follows the lower-right
curve and overlaps the right-hand NVIDIA logo. The example uses
``frontAndBack`` so both surface sides receive the decals.

To enlarge a planar decal, increase the local X and Y components of
``xformOp:scale``. This scene doubles both components: the upper RTX decal
uses ``(16, 16, 12)``, the left and lower-right RTX decals use
``(13, 13, 12)``, and the silver decals use ``(10.6, 10.6, 12)``. The local Z scale remains 12
to preserve the projection depth. The local ``extent`` remains
``[(-0.5, -0.5, -0.5), (0.5, 0.5, 0.5)]``. Larger decals still appear
only on bound receiver surfaces; they do not bridge the hole or extend
past the mesh boundary.

The grayscale masks define cutout opacity: white applies the decal and
black exposes the next lower decal, or the receiver where no lower decal
applies. Both masks preserve the original logo
artwork. Colors and metallic reflections are supplied by the
materials, not painted into the masks.

The following equivalent snippets set parameters on the silver decal's
OmniSurface shader. Alpha mode 1 reads the mask's red channel explicitly;
``metalness = 1`` gives the decal a metallic response.

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/data/ovrtx-test-decals.usda
         :language: usda
         :start-after: # [snippet:doc-decal-silver-mask-usda]
         :end-before: # [/snippet:doc-decal-silver-mask-usda]
         :dedent:

   .. tab-item:: usd-core Python

      .. literalinclude:: ../../tests/docs/usd/test_decals_usda.py
         :language: python
         :start-after: # [snippet:doc-decal-silver-mask-python]
         :end-before: # [/snippet:doc-decal-silver-mask-python]
         :dedent:

The committed masks are ready to use. To regenerate them from the source
images in the example's ``artwork/`` directory, run:

.. code-block:: bash

   uv run --no-project --with pillow generate_masks.py

.. _decals_example_ordering:

Overlapping Decals
------------------

Set ``omni:decal:priority`` on each ``OmniDecal`` to control overlap.
Higher values are on top. Use distinct priorities when the order matters;
changing the order of the receiver's binding relationships is not a
replacement for setting priority.

These Path Tracing renders use the same geometry, masks, and decal transforms. Only the
red decals' priority changes. Look at the upper NVIDIA eye crossing the
red ``R``: silver covers red at priority 10 versus 0; red covers silver
when raised to 20. The lower-right RTX wordmark also crosses the right-hand
NVIDIA logo, demonstrating the same reversal. The masks' black areas remain
cut out in either order.

.. tab-set::

   .. tab-item:: Silver above red

      .. figure:: ../img/example-decals.avif
         :alt: Silver NVIDIA decals cover the upper red R and lower-right red X with silver priority 10 and red priority 0

         *Default: silver 10, red 0.*

   .. tab-item:: Red above silver

      .. figure:: ../img/example-decals-red-on-top.avif
         :alt: Upper red R and lower-right red X cover the silver NVIDIA decals after red priority is raised to 20

         *Reordered: red 20, silver 10. Placement and size are unchanged.*

The following equivalent snippets author the priority override in a stronger
layer above ``ovrtx-test-decals.usda``. In the Python tab, ``stage`` is a
USD stage whose root layer sublayers that scene. The complete USDA layer is
``tests/docs/data/ovrtx-test-decals-red-on-top.usda``. ``RedRTXB`` and
``RedRTXC`` inherit from ``RedRTXA``, so this override raises all three red
decals. Load the resulting composed stage to render the new order.

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/data/ovrtx-test-decals-red-on-top.usda
         :language: usda
         :start-after: # [snippet:doc-decal-ordering-usda]
         :end-before: # [/snippet:doc-decal-ordering-usda]

   .. tab-item:: usd-core Python

      .. literalinclude:: ../../tests/docs/usd/test_decals_usda.py
         :language: python
         :start-after: # [snippet:doc-decal-ordering-python]
         :end-before: # [/snippet:doc-decal-ordering-python]
         :dedent:
