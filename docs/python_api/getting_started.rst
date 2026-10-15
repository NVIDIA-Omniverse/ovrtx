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
renderer-owned scene APIs used by that mode have been deprecated since ovrtx 0.4,
and scene ownership will move entirely to ovstage in a future release.

All the examples in `the repository <https://github.com/NVIDIA-Omniverse/ovrtx>`__ contain ``pyproject.toml`` files that are tested with uv. Python 3.10-3.13 are supported; on Windows, use Python 3.11 or newer.

If installation fails, first verify that you are using a supported Python version and that your environment can reach PyPI. If you need a specific release artifact, GitHub Releases also contain Python wheels that can be installed explicitly.

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

ovrtx and ovstage Load Order
----------------------------

Importing ``ovrtx`` and ``ovstage`` does not load either OpenUSD-dependent
runtime. The minimal example creates ``ovrtx.Renderer`` first; renderer creation
registers ovrtx's schema paths and loads the ovrtx runtime/OpenUSD, after which
``ovstage.Stage`` loads the ovstage runtime against the same initialized OpenUSD.

If an application must create ``ovstage.Stage`` first, call
``ovrtx.register_schema_paths()`` before stage construction. That call loads only
the ovrtx shared loader and publishes discovery paths; it does not initialize the
renderer or OpenUSD. Creating the stage may then load the ovstage runtime/OpenUSD,
and a later ``ovrtx.Renderer`` uses the paths that were already registered.
``ovstage.library_version()`` also creates a temporary native instance, so make
the schema call before that probe in a stage-first process.

Minimal Example
---------------

.. filtered-literalinclude:: ../../examples/python/minimal/main.py
   :language: python
   :start-after: # its affiliates is strictly prohibited.
   :exclude-pattern: ^\s*#\s*\[/?snippet:

The example above is provided as a Python project in the ``examples/python/minimal`` directory in `the repository <https://github.com/NVIDIA-Omniverse/ovrtx>`__.

Reading Simulation Time
-----------------------

The ``products`` returned by :py:meth:`~ovrtx.Renderer.step()` expose the
renderer's simulation clock in seconds. Use
:py:attr:`~ovrtx.RenderProductSetOutputs.simulation_end_time` to timestamp
external logs or a HUD after a completed step. You do not need to accumulate
``delta_time`` in a separate Python clock.

For example, log the simulation time from the results produced above:

.. code-block:: python

   import logging

   logging.basicConfig(level=logging.INFO)
   logging.info("Simulation time: %.6f s", products.simulation_end_time)

:py:attr:`~ovrtx.RenderProductSetOutputs.simulation_start_time` and
:py:attr:`~ovrtx.RenderProductSetOutputs.simulation_end_time` describe the whole
step window. Each :py:class:`~ovrtx.FrameOutput` has its own
:py:attr:`~ovrtx.FrameOutput.start_time` and
:py:attr:`~ovrtx.FrameOutput.end_time` for the sensor's capture window.
Use those frame timestamps when synchronizing individual sensor outputs.

With :py:meth:`~ovrtx.Renderer.step_async()`, read the same timestamps from
the results returned by ``.wait().fetch()``. They belong to that step even
if later steps have already completed. Calling
:py:meth:`~ovrtx.Renderer.reset()` with ``time=T`` sets the next step's
simulation start time to ``T``.

Next Steps
----------

* Explore more :doc:`../examples/index` including the :doc:`Planet System <../examples/python_planet_system>` demo with GPU-accelerated animation.
* Refer to the :doc:`index` for the full Python API.
