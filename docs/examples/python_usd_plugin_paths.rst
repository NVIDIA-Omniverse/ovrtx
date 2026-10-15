.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

Python: USD Plugin Paths
=========================

This example registers ovrtx's physical-lighting schema with an external
OpenUSD installation and verifies its provider and fallback values.
It creates a stage in memory and prints the result.

Before running, follow the :doc:`Python setup <../python_api/getting_started>`.
The ovrtx package and its schema resources must be installed. This example does
not create a renderer or require GPU rendering.

Start in the public ovrtx repository root, ``rendering/ovrtx/public`` in a
Kit checkout. The commands below work in Windows PowerShell and Linux shells:

.. code-block:: console

   cd examples/python/usd-plugin-paths
   uv run main.py
   uv run --group dev pytest -q

A successful run prints ``Schema loaded: PhysicalLightIlluminantAPI``, the
provider's name and resource directory, and the default illuminant ``white``.
It exits with an error if the provider differs from the expected ovrtx plugin,
or if the schema or its fallback is unavailable. No files are generated.

Register the Schema
-------------------

The example asks :py:func:`ovrtx.usd_plugin_paths()` for the installed schema
directories and selects ``physical_lighting``. Registering only the family used by
the application avoids importing unrelated schema definitions.

Register it before creating a stage or looking up definitions in
``Usd.SchemaRegistry``:

.. literalinclude:: ../../examples/python/usd-plugin-paths/main.py
   :language: python
   :start-after: # [snippet:plugin-paths-external-python]
   :end-before: # [/snippet:plugin-paths-external-python]
   :dedent:

Verify the Schema
------------------

The following code checks which plugin supplies ``PhysicalLightIlluminantAPI``
and compares its resource directory with the path returned by ovrtx.
It then explicitly applies the schema to a RectLight and reads the type and fallback
of ``physical:illuminant`` without writing a value. The provider check matters
because different definitions can have the same fallback:

.. literalinclude:: ../../examples/python/usd-plugin-paths/main.py
   :language: python
   :start-after: # [snippet:plugin-paths-verify-python]
   :end-before: # [/snippet:plugin-paths-verify-python]
   :dedent:

Validation
-----------

The project pins ``usd-core==26.3`` and targets x86-64 Windows and Linux.
Its tests run successful, missing, late, and environment-based registration
in separate processes. They also run this example and check that enumeration
preserves the environment and returns stable paths.
One test registers a copy of the existing schema from another directory.
The fallback still resolves, but the example rejects the unexpected location.
The tests also reject a nonexistent schema root and check that the explicit
bundled registration call publishes paths without registering them with external
OpenUSD. They do not create ovstage or establish which duplicate provider an
application should use.

See :doc:`../core/usd_plugin_paths` for registration order, path ownership,
and the distinction between external OpenUSD and ovrtx's bundled USD runtime.
