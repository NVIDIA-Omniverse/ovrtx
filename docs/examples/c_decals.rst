.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

C: Decals
=========

Loads the same local decal scene as the Python example through an attached runtime stage, renders it, and saves the color output.

.. pull-quote::

   *"Create a minimal C API example that loads USD-authored decals through a runtime stage, renders them, and saves the color output."*

.. figure:: ../img/example-decals.avif
   :alt: Red RTX lettering and three silver NVIDIA logos distributed across a curved green logo
   :align: center

   *Enlarged silver NVIDIA logos (priority 10) overlap red RTX lettering
   (priority 0). Cutouts reveal the lower decal or the green receiver.*

Both examples consume the same USD authoring. For decal sizing, masks, and
the priority comparison with equivalent USDA and usd-core Python snippets,
see :ref:`decals_example_ordering` and :doc:`python_decals`.

The example populates the stage, advances its write floor, and renders the scene:

.. literalinclude:: ../../examples/c/decals/main.cpp
   :language: cpp
   :start-after: // [snippet:doc-decals-c-render]
   :end-before: // [/snippet:doc-decals-c-render]
   :dedent:

It maps :ref:`LdrColor <camera-output-tables>` to CPU memory and writes a PNG:

.. literalinclude:: ../../examples/c/decals/main.cpp
   :language: cpp
   :start-after: // [snippet:doc-decals-c-save]
   :end-before: // [/snippet:doc-decals-c-save]
   :dedent:

Prerequisites
-------------

- CMake 3.16 or newer and a C++17 compiler
- An NVIDIA RTX-capable GPU and a supported driver

Building and Running
--------------------

.. code-block:: bash

   cd examples/c/decals
   cmake -B build -DCMAKE_BUILD_TYPE=Release
   cmake --build build --config Release

Run ``decals-dynamic`` from ``build/shared`` for a single-configuration
generator or ``build/shared/Release`` for a multi-configuration generator. A
successful run writes ``decals.png`` beside the executable.
