.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Material Binding
================

Materials in USD are assigned to geometry prims through the ``material:binding`` relationship. An ovstage write can change these bindings at runtime without reloading the scene.

To bind a material, write the ``material:binding`` attribute on the target geometry prim with the absolute path of the material prim as a path string.

.. note::

   The material prim must already exist in the stage (loaded from USD). This operation changes which existing material is assigned to a prim -- it does not create new materials.

Binding a Material
------------------

.. tab-set::

   .. tab-item:: Python

      Intern the material path, then write the relationship through an ovstage query with ``AttributeSemantic.RELATIONSHIP_PATH_ID``.

      .. literalinclude:: ../../tests/docs/python/test_base.py
         :language: python
         :start-after: # [snippet:doc-bind-material]
         :end-before: # [/snippet:doc-bind-material]
         :dedent:

   .. tab-item:: C

      Use the :c:func:`ovrtx_set_path_attributes()` convenience helper from ``<ovrtx/ovrtx_attributes.h>``. It wraps the path value into the single-element relationship array that USD requires.

      .. literalinclude:: ../../tests/docs/c/test_base.cpp
         :language: cpp
         :start-after: // [snippet:doc-bind-material-c]
         :end-before: // [/snippet:doc-bind-material-c]
         :dedent:
