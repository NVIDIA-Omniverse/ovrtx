.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-acoustic-howto-live-retuning:

Retune the Sensor While It Runs
===============================

Nearly every Acoustic generic wpm model attribute can change while the sensor
runs, including the operating mode selected by
``omni:sensor:WpmAcoustic:enableInterference``. Use output parameters and
controlled comparisons to check the effect of an update. See
:ref:`supported updates <sensors-nonvisual-acoustic-attributes-runtime-updates>`
for the mode-dependent exception, and :doc:`Runtime Parameter Updates
<../../../common/runtime_updates>` for update outcomes and batch validation.

Before you start. Start with the sensor from :doc:`set_up_sensor` and step past its
:ref:`startup frames <sensors-nonvisual-acoustic-outputs-first-frames>`.
Use frames containing echo data for the baseline comparison. See
:doc:`../../../common/runtime_updates` for shared update behavior.

.. _sensors-nonvisual-acoustic-howto-live-retuning-expect:

Update behavior
---------------

An accepted edit applies from the next frame built after it. It may reallocate
resources and take longer to apply, including for scalar changes such as
``noiseMax`` or ``sampleDuration``.
The ``frameId`` param continues counting across the edit (:ref:`Runtime updates <sensors-nonvisual-acoustic-attributes-runtime-updates>`). A refused
parameter set changes nothing and shows only in the log (:ref:`refusals show in
the log <sensors-common-runtime-updates-quiet-refusal>`), so the rest of this
page reads the output, not the stage.

Validate the update
-------------------

Validation checks the attribute types and the
``omni:sensor:WpmAcoustic:signalMode`` value, not physical plausibility
(:ref:`what validation checks
<sensors-nonvisual-acoustic-attributes-index-repair>`), so check the ranges
yourself against the attribute descriptions on :doc:`USD Attributes
<../attributes>`. The :doc:`sensor definition validation utility
<../../../common/validation>` runs the same checks on a parameter set or on a
prim in a USD file, so you can check an intended edit before you author it on
the running sensor.

Complete each firing sequence's :ref:`four arrays
<sensors-nonvisual-acoustic-attributes-parallel-arrays>` before stepping.
Use :ref:`valid mount and group indices
<sensors-nonvisual-acoustic-attributes-index-repair>` and the full
:ref:`namespace and instance name
<sensors-nonvisual-acoustic-attributes-namespaces>`. Omitting ``m001``,
``g001`` or ``seq001`` creates an unrelated attribute the model ignores.
When diagnosing rejection, change one parameter at a time.

.. _sensors-nonvisual-acoustic-howto-live-retuning-verify:

Verification
------------

.. _sensors-nonvisual-acoustic-howto-live-retuning-echoed-params:

Echoed parameters
^^^^^^^^^^^^^^^^^

Reading a stage attribute confirms authorship, not model acceptance. Check
``centerFrequencyHz`` and ``sampleDurationUs`` in a frame produced after the
update: they report the accepted ``centerFrequency`` and ``sampleDuration``
values. Discard frames already in flight when the edit was submitted. See
:ref:`output params <sensors-nonvisual-acoustic-outputs-params>`; the reader on
:doc:`../outputs` also retrieves ``numSignalWays`` and ``cycleIndex``.

.. _sensors-nonvisual-acoustic-howto-live-retuning-counts:

Output layout and validity
^^^^^^^^^^^^^^^^^^^^^^^^^^

For attributes without an echoed parameter, compare outputs before and after
a change with an observable structural effect:

- Add a mount, or add a firing event on a channel id no event used before, and
  ``numSignalWays`` changes (:ref:`Params
  <sensors-nonvisual-acoustic-outputs-params>`). :doc:`Lay Out a Transducer
  Array <array_topology>` has the authoring steps.
- Enlarge a receiver group instead, and ``numSignalWays`` stays put while the
  number of signal ways whose ``Flags`` entry carries ``VALID`` rises, as long
  as the added receiver receives an echo. Count the ``VALID`` bits among the
  first ``numSignalWays`` entries of ``Flags``, as :ref:`Validity
  <sensors-nonvisual-acoustic-outputs-validity>` describes.

The ``VALID`` bit is independent of the noise basic mode adds to the envelope.
However, unchanged counts do not prove rejection: an accepted edit may leave
the layout or detected echoes unchanged. Use echoed params where available,
check the renderer log for rejection, and compare controlled scenes.

Account for shared signal ways and sequence selection:

- A signal way is one receiver on one channel id, whichever transmitter fired.
  Adding a receiver to a group adds no ``VALID`` signal way if that receiver
  already receives echoes on the same channel id through another event of the same firing
  sequence. Grow a group whose event is alone on its channel id, or give the
  event a channel id of its own first.
- Each frame traces one firing sequence, and the ``cycleIndex`` param says
  which. A change to one sequence's events or groups shows only in the frames
  that trace that sequence, so compare frames with the same ``cycleIndex``.

Take the "before" frame once the sensor delivers echo data (:ref:`Startup frames <sensors-nonvisual-acoustic-outputs-first-frames>`) and the "after" frame from a
step after the edit, and compare a few frames on each side, matched by
``cycleIndex``, rather than a single pair.

Start with the default topology: mount ``m001``, receiver group ``g001``
and one firing event on channel ``0``. This gives ``numSignalWays = 1``.

1. **Add a second mount.** Place ``m002`` beside ``m001``.
   ``numSignalWays`` becomes ``2`` (two mounts × one channel), even before
   ``m002`` belongs to a receiver group.
2. **Add the mount to the receiver group.** Include ``m002`` in ``g001``.
   ``numSignalWays`` remains ``2``. The second signal way gets the ``VALID``
   bit when ``m002`` receives an echo.
3. **Add a firing event on a second channel.** Use channel ``1``.
   ``numSignalWays`` becomes ``4`` (two mounts × two channels).

Read ``numSignalWays`` from a frame built after each edit. The number of
valid signal ways still depends on which receivers receive echoes.

.. _sensors-nonvisual-acoustic-howto-live-retuning-symptoms:

Potential issues
----------------

Read the output rather than the stage, and look for the refusal in the log;
the :doc:`Symptom Index <../../../troubleshooting/symptoms>` collects the
symptoms every model shares.

- **Nothing changes when you retune.** The stage shows the new value and the
  output does not: the parameter set was refused, which changes nothing and
  shows only in the log, or the frame you compared was already in flight when
  you edited. Refer to :ref:`Runtime edits have no effect <sensors-troubleshooting-symptoms-retune>`.
- **The attribute is one that does not change while the sensor runs.** An
  edit to ``gainCoeffs`` or ``directivityCoeffs`` alone while
  the interference mode is on takes effect only when the basic mode is next
  selected. Refer to :ref:`Runtime updates <sensors-nonvisual-acoustic-attributes-runtime-updates>`.
- **Nothing reads the attribute at all.** It is authored without its namespace
  or without its ``m001``, ``g001`` or ``seq001`` instance segment, so it is a
  different attribute that nothing reads. Refer to :ref:`the namespace entry
  <sensors-troubleshooting-symptoms-retune-namespace>` of the Symptom Index and
  to :ref:`namespaces <sensors-nonvisual-acoustic-attributes-namespaces>`.
- **A firing sequence you edited has arrays of different lengths.** It is four
  parallel arrays; author all four together, with the same length, before you
  step. Refer to :ref:`the parallel arrays
  <sensors-nonvisual-acoustic-attributes-parallel-arrays>`.

Related
-------

- :doc:`Runtime Parameter Updates <../../../common/runtime_updates>` — shared update behavior, the four outcomes and the batch rule.
- :doc:`USD Attributes <../attributes>` — what each attribute means, the array topology and what changes live on this model.
- :doc:`Outputs <../outputs>` — signal ways, the ``SignalWays`` channels and params, validity and the first frames.
- :doc:`Python: Acoustic Sensor <../../../../examples/python_sensor_acoustic>` — the runnable example whose reader :doc:`Outputs <../outputs>` shows, on the one-mount default topology this page's worked case starts from.
