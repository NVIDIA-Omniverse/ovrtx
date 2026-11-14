.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-generic-wpm:
.. _sensors-nonvisual-generic-wpm-index:

Generic wpm model
=================

.. warning::

   This feature is **experimental** and under **active development**.
   This version is intended for **early adopters only** and may be unstable.

The Generic wpm model simulates wave paths between transmitters, scene geometry
and receivers. Configure transmitter positions, receiver positions, emitted rays
and their connections independently. Choose it when you need raw path data
for your own sensor processing. WPM stands for *wave propagation model*.

.. figure:: ../../../img/sensors/nonvisual/generic_wpm_depth_ranges.avif
   :align: center
   :width: 100%
   :alt: A three-row, five-column angular range sample of a wall. The center sample is 11 meters away and oblique samples have longer radial ranges.

   *The depth-sampling example derives radial ranges from valid direct returns
   to an enclosure wall. Uniform angular samples are not pinhole-camera pixels.*

Simulation
----------

**Independent geometry.** Free, Grid and Gaussian patterns describe the
transmitters, receivers and rays. Transmitter and receiver patterns use Free
or Grid geometry; ray patterns also support Gaussian sampling. A selected
transmitter pattern assigns one ray bundle and one receiver-connection rule
to all its transmitters. Refer to :doc:`USD Attributes <attributes>`.

**Reusable sampling.** A ray bundle describes where rays start and which
directions they sample relative to a transmitter. The same bundle is emitted
at each transmitter pose. This separates the placement of emitting elements
from the sampling around each element. Choose explicit rays for an irregular
set of directions, a grid for regular sampling, or a Gaussian bundle for an
angular spread. See :doc:`Sample a Finite-Width Beam <howto/beam_sampling>`.

**Scalar propagation.** Electromagnetic or mechanical paths yield contributions
from scene interactions toward receivers. Firing offsets place emissions within
a complete capture. Refer to :doc:`USD Attributes <attributes>` for propagation
and timing controls.

Outputs
-------

The :doc:`Contributions output <outputs>` contains per-path geometry, distance,
velocity, timing, scalar power and validity. Optional channels describe the hit
triangle. Every capture has a dense layout across tiles, transmitters, rays,
bounces and receiver slots; read it using the output's parameters and validity.
Refer to :doc:`Outputs <outputs>` for the contract and :doc:`Sensor Outputs
<../../common/sensor_outputs>` for shared mapping and ownership.

Features at a glance
--------------------

- Create a sensor and its output request (:doc:`Set Up a Sensor <howto/setup>`).
- Choose angular, planar or cylindrical sampling (:doc:`Sample a Depth Grid <howto/depth_sampling>`).
- Sample all azimuths with authored firing times (:doc:`Configure a Full-Circle Scan <howto/scan>`).
- Sample a Gaussian beam and neighboring receivers (:doc:`Sample a Finite-Width Beam <howto/beam_sampling>`).
- Select independent receiver positions and ordered subsets (:doc:`Connect Independent Transmitters and Receivers <howto/receiver_layouts>`).
- Select scalar mechanical paths (:doc:`Select Mechanical Propagation <howto/mechanical_propagation>`).
- Switch stored alternatives between captures (:doc:`Switch Stored Patterns <howto/runtime_updates>`).
- Read contribution channels and parameters (:doc:`Outputs <outputs>`).

Applications
------------

Use this model for depth sampling, lidar-style angular scans, finite-width beams,
bistatic or multistatic layouts, and acoustic layouts when your application
supplies the measurement processing. It delivers raw path contributions rather
than finished detector measurements. Your application interprets those paths
according to the measurement it needs: for example, deriving a direct-return
distance or processing paths between separated transmitters and receivers.
Refer to :ref:`model scope
<sensors-troubleshooting-limitations-generic-wpm>` for the processing boundary.

Choose the :doc:`Lidar generic wpm model <../lidar_wpm/index>` for lidar detector
returns, the :doc:`Radar generic wpmDmat model <../radar_wpm_dmat/index>` for radar
detections, or the :doc:`Acoustic generic wpm model <../acoustic_wpm/index>` for
echo envelopes. Independent configurations use separate RenderProducts;
:doc:`runtime selection <howto/runtime_updates>` changes the active pattern
without replacing stored alternatives.

Sensor definition
-----------------

Apply ``OmniSensorGenericWpmAPI`` to an ``OmniGeneralSensor`` prim and author
its ``omni:sensor:GenericWpm:`` attributes. The schema supplies the transmitter,
receiver, ray and mapping APIs, but no complete default pattern. Start with
:doc:`Set Up a Sensor <howto/setup>`, then add a complete pattern.

This minimal prim emits one ray from one transmitter and evaluates return paths
to one co-located receiver. The USD Python tab assumes an existing USD ``stage``.

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../../../tests/docs/usd/data/generic_wpm_minimal.usda
         :language: usda
         :start-after: # [snippet:doc-generic-wpm-minimal]
         :end-before: # [/snippet:doc-generic-wpm-minimal]
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../../../tests/docs/usd/test_generic_wpm_usda.py
         :language: python
         :start-after: # [snippet:doc-generic-wpm-imports-python]
         :end-before: # [/snippet:doc-generic-wpm-imports-python]
         :dedent:

      .. literalinclude:: ../../../../tests/docs/usd/test_generic_wpm_usda.py
         :language: python
         :start-after: # [snippet:doc-generic-wpm-minimal-python]
         :end-before: # [/snippet:doc-generic-wpm-minimal-python]
         :dedent:

The :doc:`Python example <../../../examples/python_generic_wpm>` saves named
channels and parameters and can display hit samples. The :doc:`C example
<../../../examples/c_generic_wpm>` saves valid records with their logical slots.
Both run the same recipe layers. Shared prim and output setup is described by
:doc:`Sensor Configuration <../../common/sensor_configuration>` and
:doc:`Output Configuration <../../common/output_configuration>`.

Configuration and outputs
-------------------------

.. toctree::
   :maxdepth: 1

   attributes
   howto/index
   outputs

Related
-------

- :doc:`Your First Lidar Sensor <../../first_sensor>` — the shared sensor workflow.
- :doc:`Non-Visual Sensor Materials <../../../materials/nonvisual_sensor_materials>` — author surface labels.
- :doc:`Glossary <../../reference/glossary>` — shared terminology.
