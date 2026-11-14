:orphan:

.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-nonvisual-idealized-depth-howto:

How-To
======

.. note::

   Draft. The Idealized depth model has no output that ovrtx delivers yet, so
   this section is held back from the published documentation until it does.
   Its pages are written to the same standard and link out to the published
   pages; no published page links here.

One page per task you carry out with the Idealized depth model. There is one
page so far, on choosing the emitter shape, because the emitter set is what
this model asks you to design. An emitter is one ray the model fires each
frame, from an origin in a direction, and the model reports what every ray
found, so the emitter set decides which geometry is sampled and how much work
a frame is. The page shows how to make that choice and links out for the why:
what each attribute means stays on :doc:`../attributes`, and what the model
reports per frame and per entry stays on :doc:`../outputs`.

:doc:`emitter_shape` walks through the decision in five steps: size the ray
budget from the schema defaults and ``omni:sensor:frameRate``, pick one of the
five shapes ``omni:sensor:Core:type`` offers for the geometry you want
sampled, author only the attributes that shape reads, satisfy the
prerequisites of the two shapes that have them, ``GRIDLESS_SPHERICAL`` and
``BOX``, and, once the model has an output, confirm the delivered entry count
against the emitter count the attributes imply. Read it before the sensor
first produces, because the defaults are not small, and again before you
reshape a running sensor. The defaults and what they fire, the shape table and
the prerequisites themselves are stated once, on :doc:`../attributes`.

.. toctree::
   :maxdepth: 1

   emitter_shape

Related
-------

- :doc:`Idealized depth model <../index>` — what the model simulates, what it leaves out by design and why the section is held back.
- :doc:`USD Attributes <../attributes>` — the five emitter shapes, what each reads, the defaults and what changes on a running sensor.
- :doc:`Outputs <../outputs>` — one entry per emitter, and the coordinates and identity each entry carries.
