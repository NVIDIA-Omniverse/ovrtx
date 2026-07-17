.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

NVIDIA ovrtx
============

Omniverse RTX is the technology that provides real-time, physically accurate sensor simulation and rendering for `Physical AI <https://www.nvidia.com/en-us/glossary/generative-physical-ai/>`_, targeting robotics learning, synthetic data generation, and industrial and design workflows. **ovrtx** is the lightweight C and Python SDK that exposes Omniverse RTX—you use it to integrate that sensor simulation and visualization into your own applications.

In this documentation you will find getting started guides for Python and C, API references, and example projects.

* :doc:`Getting started in Python <python_api/getting_started>` - Refer to the :doc:`Python minimal example documentation <examples/python_minimal>` for more information on environment setup and prerequisites.
* :doc:`Getting started in C <c_api/getting_started>` - Refer to the :doc:`C minimal example documentation <examples/c_minimal>` for more information on environment setup and prerequisites.

.. note::

   ovrtx is currently **pre-release** software.

.. note::

   Starting with **ovrtx 0.4**, the renderer can attach to **ovstage** — an
   optional NVIDIA library that manages the runtime scene, ordinal-keyed writes,
   and change detection. Renderer-owned scene APIs remain available for
   standalone compatibility in 0.4, but are deprecated as scene ownership
   transitions entirely to ovstage in a future release. Refer to
   :doc:`core/ovstage_integration` for the attach-mode reference.

.. image:: ../img/warehouse.jpg
   :alt: Warehouse scene rendered with ovrtx RTX sensor simulation
   :align: center

Features
--------

* Physically accurate simulation of cameras, lidar, radar, and other sensors.
* Scalable simulation performance from reinforcement learning in-the-loop with tens of thousands of frames per second, through real-time, photorealistic, interactive viewport and navigation, to offline predictive rendering.
* `OpenUSD <https://aousd.org/>`_ scene description allowing interchange with a vast ecosystem of content creation, CAD, and simulation tools.
* Easy integration with Python simulation and learning ecosystem.

Support
-------

Report documentation issues, installation problems, and runtime issues through the NVIDIA Omniverse developer forum.

https://forums.developer.nvidia.com/c/omniverse/300

License
-------

The software and materials are governed by the `NVIDIA Software License Agreement <https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-software-license-agreement/>`_ and the `Product Specific Terms for NVIDIA AI Products <https://www.nvidia.com/en-us/agreements/enterprise-software/product-specific-terms-for-ai-products/>`_.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   python_api/getting_started
   c_api/getting_started
   driver_requirements

.. toctree::
   :maxdepth: 2
   :caption: API Usage

   core/application_flow
   core/renderer_configuration
   core/async_status_errors
   core/ovstage_integration

.. toctree::
   :maxdepth: 3
   :titlesonly:
   :caption: Sensors

   sensors/configuration
   sensors/sensor_outputs
   sensors/cameras
   sensors/nonvisual

.. toctree::
   :maxdepth: 2
   :caption: Sensor Processing Graphs

   spg/index

.. toctree::
   :maxdepth: 2
   :caption: Scene

   scene/loading_usd
   scene/stage_queries
   scene/attributes
   scene/transforms
   scene/attribute_bindings
   scene/attribute_mapping
   scene/cloning
   scene/material_binding
   scene/semantic_labels
   scene/picking

.. toctree::
   :maxdepth: 2
   :caption: Examples

   examples/index

.. toctree::
   :maxdepth: 2
   :caption: Python API

   python_api/index

.. toctree::
   :maxdepth: 2
   :caption: C API

   c_api/practical_patterns
   c_api/index

.. toctree::
   :caption: Links

   GitHub Repository <https://github.com/NVIDIA-Omniverse/ovrtx>

Indices and Tables
==================

* :ref:`genindex`
* :ref:`search`
