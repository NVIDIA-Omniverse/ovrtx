.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _spg-do-runtime:

Change Values and Rewire
========================

**Goal.** Retune or rewire a graph without reloading the scene.

**Before you start.** :doc:`values`, :doc:`chaining`.

The Shape
---------

A value-input is addressable on the Shader prim by its USD name. Write it, publish the edit by
advancing the write floor, then step:

.. filtered-literalinclude:: ../../../examples/python/spg-blur/main.py
   :language: python
   :start-after: # [snippet:blur-write-radius]
   :end-before: # [/snippet:blur-write-radius]
   :exclude-pattern: ^\s*#\s*\[/?snippet:
   :caption: ``main.py``, from the runnable :doc:`blur example <../../examples/python_spg_blur>`

How It Works
------------

``inputs:X`` **is the name that binds.** A value-input authored with the older ``params:X`` spelling
is also addressed as ``inputs:X``; ``params:X`` is not an addressable name. Refer to
:doc:`../ref/usd`.

**An unconnected input takes effect on the next step.** Nothing else has to be reset or reloaded.
The blur example changes its radius this way and renders again:

.. filtered-literalinclude:: ../../../examples/python/spg-blur/main.py
   :language: python
   :start-after: # [snippet:blur-runtime-radius]
   :end-before: # [/snippet:blur-runtime-radius]
   :exclude-pattern: ^\s*#\s*\[/?snippet:
   :caption: ``main.py``, from the runnable :doc:`blur example <../../examples/python_spg_blur>`

**A connected input ignores a direct write.** If ``inputs:X`` is connected to another prim, the
connection is the source of the value, so writing ``inputs:X`` succeeds and changes nothing. Write
the source attribute instead, then reset the renderer so the graph picks up the new value.

**Each node carries its own copy.** Two nodes referencing the same shader definition each have
their own ``inputs:X``, so retuning both means writing both.

**A changed value can cost more than the value.** Anything the launch script derives from it is
derived again, and a :doc:`cached computation <caching>` keyed on it runs again. That is the
intended behaviour, not a cost to avoid: it is how a new radius reaches a new weight table.

**Rewiring changes what runs.** Execution order comes from connections, so changing a connection
can make a node that was idle start running, or stop one that was running. Refer to
:ref:`Order comes from connections <spg-execution-order>`.

Verify It Worked
----------------

Choose a value with an exact effect and check it byte for byte, before and after the change,
against the same input AOV. A picture that changes but not in the way the value predicts means the
write landed somewhere other than the input you meant.

The :doc:`blur example <../../examples/python_spg_blur>` uses a blur radius of zero, which makes
the node the identity, and prints ``pixels differing from the input: 0``. A write that missed
leaves the previous radius in place and every pixel differs.

When It Goes Wrong
------------------

- The write reported success and nothing changed: the input is connected, so the connection is
  winning. Write the source attribute instead.
- The attribute would not bind: ovrtx's default binding mode skips attributes it cannot find rather
  than reporting them, so a misspelled name is silent. Bind with the mode that requires the
  attribute to exist while you are debugging.
- A node stopped running after a rewire: it now feeds nothing that is requested. Refer to
  :ref:`Nothing Appears <spg-symptom-nothing>`.

Related
-------

:doc:`values`, :doc:`chaining`, :doc:`caching`, :doc:`../ref/usd`,
:doc:`../../examples/python_spg_blur`
