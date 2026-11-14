.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-generic-wpm-howto:

How-To
======

Build a first capture with :doc:`Set Up a Sensor <setup>` and
:doc:`Sample a Depth Grid <depth_sampling>`. Together they define the sensor,
its transmitter and receiver layouts, the emitted rays and the requested output.
Each recipe has a USDA layer and an equivalent Python authoring example.

The scan and finite-width beam recipes modify that depth configuration.
Independent receivers, mechanical propagation and stored alternatives start
from the base sensor instead. Choose the next recipe by the geometry,
firing schedule or receiver connections your application needs:

.. toctree::
   :maxdepth: 1

   setup
   depth_sampling
   scan
   beam_sampling
   receiver_layouts
   mechanical_propagation
   runtime_updates

Related
-------

- :doc:`USD Attributes <../attributes>` — the model controls and pattern requirements.
- :doc:`Outputs <../outputs>` — contribution channels and layout.
- :doc:`Python example <../../../../examples/python_generic_wpm>` — run the recipes and save their results.
- :doc:`C example <../../../../examples/c_generic_wpm>` — read the same recipes through the C API.
