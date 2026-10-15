.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

.. _usd-plugin-paths:

USD Plugin Paths and Schema Registration
========================================

USD schemas describe prim types, attribute types, and fallback values.
ovrtx ships schema plugins for renderer settings, sensors, lens distortion,
particle fields, and other capabilities. An application that creates USD
through its own OpenUSD installation must make the required schema definitions
available before it first uses the schema registry.

There are two separate consumers: your external OpenUSD (for example Python's
``usd-core``) and the USD runtime used by ovstage population. Registering with
one does not register with the other.

Choose the Registration Path
----------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Application workflow
     - Required action
   * - `Register with External OpenUSD`_
     - Author with your own OpenUSD installation. Enumerate ovrtx's directories, select the required families, and register them with that installation.
   * - `Register for the Bundled USD Runtime`_
     - Populate an ovstage scene. Publish ovrtx's schema paths before initializing ovstage, or initialize the renderer first.

Register with External OpenUSD
------------------------------

:py:func:`ovrtx.usd_plugin_paths()` returns schema directories without changing
plugin-path environment variables. C uses
:c:func:`ovrtx_get_usd_plugin_path_count()` and
:c:func:`ovrtx_get_usd_plugin_paths()`.

Enumeration does not check whether each directory exists. Select the families
your application needs, register them with its OpenUSD installation, and
verify that their schema definitions are available.

The following Python code registers the physical-lighting family. The C tab
shows the equivalent directory enumeration for a caller integrating its own
OpenUSD installation:

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../examples/python/usd-plugin-paths/main.py
         :language: python
         :start-after: # [snippet:plugin-paths-external-python]
         :end-before: # [/snippet:plugin-paths-external-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../examples/c/usd-plugin-paths/main.cpp
         :language: cpp
         :start-after: // [snippet:plugin-paths-enumerate-c]
         :end-before: // [/snippet:plugin-paths-enumerate-c]
         :dedent:

C returns the total directory count even when the supplied array is smaller.
Each ``ovx_string_t`` contains a length and an ovrtx-owned pointer; do not free
the strings or assume null termination. They remain valid for the process lifetime.

.. warning::

   Register external plugins before the first ``Usd.SchemaRegistry`` lookup
   or stage open. Late registration does not rebuild cached schema definitions.
   Set ``PXR_PLUGINPATH_NAME`` before importing ``pxr`` when using the environment
   alternative. Run ordering checks in new processes.

The example selects only ``physical_lighting``, the family it uses, and is tested
with ``usd-core==26.3``. This does not establish compatibility with every
OpenUSD version or binary plugin.

.. warning::

   Different plugins can provide the same schema alias. For example, recent
   external OpenUSD versions already define particle schemas also supplied by
   ovrtx's ``usd_particle_field`` family. OpenUSD may select a provider without
   reporting a conflict. A successful render or matching fallback value does not
   identify the selected provider. Check the plugin and its resource directory
   as well as the schema's fallback values.

   Selecting only ``physical_lighting`` avoids that overlap in this example.
   It is not a general rule to discard OV schemas whenever OpenUSD provides
   the same alias; the provider must meet your application's compatibility needs.

Verify a Schema
~~~~~~~~~~~~~~~

After registration, explicitly apply ``PhysicalLightIlluminantAPI`` to a RectLight.
These equivalent USDA and Python examples use the existing ovrtx schema:

.. tab-set::

   .. tab-item:: USDA

      .. literalinclude:: ../../tests/docs/usd/data/plugin_physical_light.usda
         :language: usda
         :start-after: # [snippet:doc-plugin-physical-light]
         :end-before: # [/snippet:doc-plugin-physical-light]

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/usd/test_usd_python_examples.py
         :language: python
         :start-after: # [snippet:doc-plugin-physical-light-python]
         :end-before: # [/snippet:doc-plugin-physical-light-python]
         :dedent:

The Python check verifies that ``physical:illuminant`` is absent before applying
this schema, then reads its token fallback ``white`` without authoring a value.
It also checks that the selected schema comes from ``physicalLighting`` in the
directory returned by ovrtx. Writing a custom attribute would not prove that
registration worked.

The C tab checks that each enumerated directory contains a plugin descriptor.
That catches a nonexistent package root before publishing paths. Resolving the
schema and its fallback with an external C++ OpenUSD installation also requires
that installation's headers and libraries; ovrtx's C API does not expose its
schema registry.

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../examples/python/usd-plugin-paths/main.py
         :language: python
         :start-after: # [snippet:plugin-paths-verify-python]
         :end-before: # [/snippet:plugin-paths-verify-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../examples/c/usd-plugin-paths/main.cpp
         :language: cpp
         :start-after: // [snippet:plugin-paths-validate-c]
         :end-before: // [/snippet:plugin-paths-validate-c]
         :dedent:

Register for the Bundled USD Runtime
------------------------------------

Call :py:func:`ovrtx.register_schema_paths()` before initializing ovstage in
a stage-first application. This publishes ovrtx's paths for the bundled USD
runtime. It does not register them with a separate external OpenUSD instance.

If ovstage is already loaded, the function also forwards the paths directly
to it. Registration must still happen before the first operation that reads
USD schema definitions, including population and schema-aware export.
Registering before ovstage initialization avoids that timing dependency.

Call the registration function before creating ovstage. The C tab uses the
same configuration as path enumeration:

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../examples/python/usd-plugin-paths/main.py
         :language: python
         :start-after: # [snippet:plugin-paths-register-python]
         :end-before: # [/snippet:plugin-paths-register-python]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../examples/c/usd-plugin-paths/main.cpp
         :language: cpp
         :start-after: // [snippet:plugin-paths-register-c]
         :end-before: // [/snippet:plugin-paths-register-c]
         :dedent:

If the application initializes the renderer before ovstage, renderer
initialization publishes these paths automatically. External OpenUSD still
needs the separate registration described above.

Enumeration and registration share a first-call-wins package-root selection.
A later request for another root warns and keeps the pinned root. Enumeration
therefore has this process-state effect even though it does not change environment
variables.

The following Python test uses two existing package roots, ``root_a`` and
``root_b``, each containing a copy of the installed schema resources. In a fresh
process, requesting B after A still returns and publishes A's paths. The test
also checks the warning on stderr and runs with registration as the first call:

.. literalinclude:: ../../examples/python/usd-plugin-paths/test_example.py
   :language: python
   :start-after: # [snippet:plugin-paths-first-root-wins-python]
   :end-before: # [/snippet:plugin-paths-first-root-wins-python]

.. warning::

   :c:func:`ovrtx_register_schema_paths()` always returns
   ``OVRTX_API_SUCCESS``, including for a root mismatch. Its return value
   does not prove that the paths exist or that the USD runtime can resolve the
   schemas. Verify the required schema definitions before using them.

Importing ``ovrtx`` registers paths automatically only when
``OVRTX_PXR_SCHEMA_AUTO_REGISTER=1``. The opt-in also publishes paths to the
upstream ``PXR_PLUGINPATH_NAME``. Keep it unset when you need to select paths
yourself. The bundled runtime uses its own versioned plugin-path environment key;
prefer the public functions over hard-coding that key.

Further Reading
---------------

* :doc:`../examples/python_usd_plugin_paths`
* :doc:`../examples/c_usd_plugin_paths`
* :doc:`application_flow`
* :doc:`ovstage_integration`
