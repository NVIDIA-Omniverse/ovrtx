.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Getting Started in Python
=========================

`ovrtx <https://pypi.org/project/ovrtx/>`_ and
`ovstage <https://pypi.org/project/ovstage/>`_ are distributed on PyPI. Use `uv <https://docs.astral.sh/uv/getting-started/installation/>`_
to install both packages for the current attached-stage workflow:

.. code-block:: bash

   uv add ovrtx ovstage

``pip`` also works:

.. code-block:: bash

   pip install ovrtx ovstage

ovstage is optional when maintaining standalone compatibility code. The
renderer-owned scene APIs used by that mode are deprecated in ovrtx 0.4 and
will move entirely to ovstage in a future release.

All the examples in `the repository <https://github.com/NVIDIA-Omniverse/ovrtx>`__ contain ``pyproject.toml`` files that are tested with uv. Python 3.10-3.13 are supported.

If installation fails, first verify that you are using Python 3.10-3.13 and that your environment can reach PyPI. If you need a specific release artifact, GitHub Releases also contain Python wheels that can be installed explicitly.

ovrtx runtime validation requires an NVIDIA RTX-capable GPU, a supported NVIDIA driver, internet access, and execution outside sandboxed environments. The minimal example downloads scene assets from S3. Supported driver versions are listed in :doc:`../driver_requirements`.

To get started, first clone `the repository <https://github.com/NVIDIA-Omniverse/ovrtx>`__ and run the first example with uv:

.. code-block:: bash

   git clone https://github.com/NVIDIA-Omniverse/ovrtx.git
   cd ovrtx/examples/python/minimal
   uv run main.py --png

`The minimal example <https://github.com/NVIDIA-Omniverse/ovrtx/tree/main/examples/python/minimal>`__ shows how to create the renderer, load an OpenUSD scene, and render a single image, copying the results back to the CPU for display.

A successful run writes ``_output/render.png``. The output should match the reference image below.

.. image:: ../../img/example-minimal.jpg
   :alt: Minimal example output
   :align: center

The first step from a newly built application will block for 1-2 minutes while shaders are compiled and cached.

Minimal Example
---------------

.. filtered-literalinclude:: ../../examples/python/minimal/main.py
   :language: python
   :start-after: # its affiliates is strictly prohibited.
   :exclude-pattern: ^\s*#\s*\[/?snippet:

The example above is provided as a Python project in the ``examples/python/minimal`` directory in `the repository <https://github.com/NVIDIA-Omniverse/ovrtx>`__.

Next Steps
----------

* Explore more :doc:`../examples/index` including the :doc:`Planet System <../examples/python_planet_system>` demo with GPU-accelerated animation.
* Refer to the :doc:`index` for the full Python API.
