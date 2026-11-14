.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-troubleshooting-index:

Troubleshooting
===============

Use these pages to diagnose sensor output and configuration problems:

- :doc:`symptoms` — missing output, incorrect values, ineffective edits and
  performance problems, with checks and corrective actions.
- :doc:`limitations` — model constraints and unsupported features.

Start by checking the renderer log and, where supported, running
:doc:`Sensor Definition Validation <../common/validation>`. Compare your setup
with the model's runnable example; lidar users can start with
:doc:`Your First Lidar Sensor <../first_sensor>`.

Inspect output counts, validity flags and parameters alongside the logs. See
:ref:`Diagnostics <sensors-troubleshooting-symptoms-diagnostics>` for log
configuration and useful output fields.

.. toctree::
   :hidden:
   :maxdepth: 1

   symptoms
   limitations

Related
-------

- :doc:`Sensor Definition Validation <../common/validation>` — check an authored definition before you render.
- :doc:`Runtime Parameter Updates <../common/runtime_updates>` — supported edits and how to identify rejected updates.
- :doc:`Sensor Outputs <../common/sensor_outputs>` — counts, validity, output parameters and memory mapping.
- :doc:`Glossary <../reference/glossary>` — the terms the symptom entries use.
