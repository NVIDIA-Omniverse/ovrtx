.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-lidar-wpm-howto-runtime-updates:

Retune the Sensor While It Runs
===============================

The Lidar generic wpm model accepts parameter updates while it runs.
Presentation edits preserve the scan in progress; other accepted parameter
edits start a new scan with the updated profile. Rejected updates preserve
the last valid configuration. See :doc:`Runtime Parameter Updates
<../../../common/runtime_updates>` for submitting and checking an update.

Before you start. See :doc:`../../../common/validation` to check a proposed parameter set and
:doc:`../attributes` for model-specific constraints.

.. _sensors-nonvisual-lidar-wpm-howto-runtime-updates-live:
.. _sensors-lidar-wpm-live-updates:

Supported updates
-----------------

All model attributes support runtime edits, including ``scanType``,
``rayType`` and firing-pattern arrays. See :doc:`firing_pattern` for the
instance rules and :doc:`../../../common/runtime_updates` for submitting edits.

Each accepted update replaces the complete profile. Unless it changes only
the presentation attributes listed below, it discards the scan in progress.
Subsequent outputs contain only returns produced with the new profile.

Changing the RenderVar list does not rebuild this model. It retains its
configuration until the sensor prim is recreated, unlike the other models
listed under :doc:`output-request changes <../../../common/runtime_updates>`.

.. _sensors-nonvisual-lidar-wpm-howto-runtime-updates-presentation-only:

Presentation-only attributes
----------------------------

Eight attributes are presentation-only and preserve the current scan:

- ``omni:sensor:LidarWpm:intensityProcessing``
- ``omni:sensor:LidarWpm:intensityMappingType``
- ``omni:sensor:LidarWpm:intensityScale``
- ``omni:sensor:LidarWpm:intensityMappingEncoding``
- ``omni:sensor:LidarWpm:elementsCoordsType``
- ``omni:sensor:LidarWpm:outputMotionCompensationState``
- ``omni:sensor:LidarWpm:outputFrameOfReference``
- ``omni:sensor:LidarWpm:customFrameOfReferenceTrafo``

These updates re-encode existing detections without retracing the scene or
repeating detection. They preserve the returns' validity, count and order.
See :ref:`coordinate updates <sensors-nonvisual-lidar-wpm-outputs-one-encoding>`
for mid-scan edits and the parameters that report the selected encoding.

.. _sensors-nonvisual-lidar-wpm-howto-runtime-updates-rejected:
.. _sensors-lidar-wpm-invalid-update:

Rejected updates
----------------

Each update validates the complete parameter set as
:ref:`one batch <sensors-common-runtime-updates-batch>`. A rejection is logged
as an error. The :doc:`validation utility <../../../common/validation>` reports
the same reason when checking a layer before rendering.

An invalid initial configuration prevents publication until corrected. Each
attempt to run the model fails and logs the reason.

A rejected runtime update preserves the last valid profile, derived state and
scan progress. Check the :ref:`renderer log
<sensors-common-runtime-updates-quiet-refusal>` and validation report when an
edit appears ineffective.

.. _sensors-nonvisual-lidar-wpm-howto-runtime-updates-outside:

Update limitations
------------------

.. _sensors-nonvisual-lidar-wpm-howto-runtime-updates-removed-pattern:
.. _sensors-lidar-wpm-removed-pattern:

Recreate the sensor after deleting or renaming a firing-pattern instance.
Emptying an existing array is still a parameter update and is validated as
such; see :ref:`pattern edits
<sensors-nonvisual-lidar-wpm-howto-firing-pattern-edit>`.

Runtime edits must satisfy the same product-wide :ref:`capacity limits <sensors-nonvisual-lidar-wpm-attributes-capacity-limits>` as initial configuration.

.. _sensors-nonvisual-lidar-wpm-howto-runtime-updates-tiled:

Only tile zero's attributes are read on a tiled product. Edits to other tiles
have no effect and produce no error. See :doc:`tile_lidars` for the shared
profile and per-tile transforms.

.. _sensors-nonvisual-lidar-wpm-howto-runtime-updates-verify:

Verification
------------

Verify edits in the published point cloud. The stage can contain a rejected
value; see :doc:`Runtime Parameter Updates <../../../common/runtime_updates>`.
:doc:`Sensor Outputs <../../../common/sensor_outputs>` describes access to
frames, tensors and params; :doc:`Outputs <../outputs>` lists this model's
channels and params.

- **After a presentation-only edit**, compare the point cloud published before
  the edit with the first one published after it. The params ``coordsType``,
  ``frameOfReference`` and ``motionCompensationState`` report the coordinate
  settings, so a mismatch with what you authored means the edit did not reach
  the model. For the same detected returns, presentation edits preserve counts,
  validity and order while converting ``Coordinates``: a change from
  the sensor frame to the world frame moves every point by the sensor's pose,
  and a change from spherical to cartesian is the trigonometric conversion of
  the same ranges and angles. Consecutive publications may contain different
  returns because the scan, scene or noise has advanced; equal counts and
  point-by-point correspondence are not guaranteed across frames.
- **After any other edit**, the next point cloud is a fresh scan built only
  from frames traced with the new profile, and the profile shows in the
  output's structure: the ``receiversPerTile`` and ``maxReturns`` params follow
  the firing patterns and return count now authored, the capacity-shaped
  tensors are sized from them, and the valid points carry only the
  ``ChannelId`` and ``FiringPatternIndex`` values of the patterns now authored.
  These integers do not depend on the model's noise; compare them rather than
  the intensity values.
- **When nothing changed**, run the validation check on the layer and look for
  the refusal in the renderer's log before you look at the scene. An unchanged output alone does not prove rejection; check echoed params
  on frames produced after the update and use a scene that exposes its effect.

.. _sensors-nonvisual-lidar-wpm-howto-runtime-updates-symptoms:

Potential issues
----------------

Look for the error in the renderer's log first, then run the
:doc:`validation check <../../../common/validation>` on the layer;
:doc:`the symptom index <../../../troubleshooting/symptoms>` collects the
symptoms every model shares.

- **The sensor has never published anything.** The initial parameter set failed
  validation. Look for malformed firing arrays, invalid ranges, non-positive
  physical parameters, unsupported token combinations, or a direct
  return-processing mode paired with ``rayType = gaussianBeam``.
- **A live edit appears to do nothing.** Either the complete parameter set was
  invalid and the previous valid profile stays active, or the edit was made on
  a tile other than tile zero of a tiled product. Check the validation report,
  then the tile.
- **A subsampling factor had no effect.** It was refused; lower the factor.
  :ref:`Subsampling <sensors-nonvisual-lidar-wpm-attributes-tiled-subsampling>`
  states what a factor must leave in place.
- **A whole batch of edits had no effect.** One value in the batch was
  malformed; refer to :ref:`Batch validation <sensors-common-runtime-updates-batch>`.

Related
-------

- :doc:`Runtime Parameter Updates <../../../common/runtime_updates>` — update delivery, outcomes and batch validation.
- :doc:`Sensor Definition Validation <../../../common/validation>` — validation reports.
- :doc:`USD Attributes <../attributes>` — controls, defaults, subsampling and capacity limits.
- :doc:`ovstage Integration <../../../../core/ovstage_integration>` — the stage update loop.
