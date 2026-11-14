.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary

C: USD Plugin Paths
===================

This example lists ovrtx's schema directories, checks their plugin descriptors,
and publishes the paths for the
bundled USD runtime. Both static and shared loaders use the same source.
It takes no arguments and prints its result to the console.

Before running, follow the :doc:`C/C++ setup <../c_api/getting_started>`.
This example uses the loader API without creating a renderer or an ovstage
instance. It does not render images.

Start in the public ovrtx repository root, ``rendering/ovrtx/public`` in a
Kit checkout. Build and run both loaders with these commands:

.. tab-set::

   .. tab-item:: Windows (PowerShell)

      .. code-block:: pwsh

         cd examples/c/usd-plugin-paths
         cmake -B build
         cmake --build build --config Release
         .\build\static\Release\usd-plugin-paths.exe
         .\build\shared\Release\usd-plugin-paths-dynamic.exe

   .. tab-item:: Linux

      .. code-block:: bash

         cd examples/c/usd-plugin-paths
         cmake -B build -DCMAKE_BUILD_TYPE=Release
         cmake --build build
         ./build/static/usd-plugin-paths
         ./build/shared/usd-plugin-paths-dynamic

Each program prints the plugin directories followed by
``Published N schema directories for the bundled USD runtime.``,
where ``N`` depends on the installed package. No files are generated.

Enumerate and Register Paths
-----------------------------

The following code enumerates borrowed directory strings:

.. literalinclude:: ../../examples/c/usd-plugin-paths/main.cpp
   :language: cpp
   :start-after: // [snippet:plugin-paths-enumerate-c]
   :end-before: // [/snippet:plugin-paths-enumerate-c]
   :dedent:

Enumeration alone does not check the filesystem. The example fails with
``Schema plugin descriptor missing: ...`` and exit code 1 if any enumerated
directory lacks ``plugInfo.json``, including when
``OMNI_USD_PLUGINS_BASE_PATH`` points at a nonexistent root. The CI check runs
this negative case in a new process for each loader.

.. literalinclude:: ../../examples/c/usd-plugin-paths/main.cpp
   :language: cpp
   :start-after: // [snippet:plugin-paths-validate-c]
   :end-before: // [/snippet:plugin-paths-validate-c]
   :dedent:

Publish the paths before the bundled USD runtime first uses its registry.
In an application that creates ovstage first, do this before initializing
ovstage:

.. literalinclude:: ../../examples/c/usd-plugin-paths/main.cpp
   :language: cpp
   :start-after: // [snippet:plugin-paths-register-c]
   :end-before: // [/snippet:plugin-paths-register-c]
   :dedent:

:c:func:`ovrtx_register_schema_paths()` always returns ``OVRTX_API_SUCCESS``.
That status does not prove that a USD runtime has loaded the schemas.
The :doc:`Python example <python_usd_plugin_paths>`
demonstrates that check with external OpenUSD. An equivalent external C++
OpenUSD check requires that installation's headers and compatible libraries;
these are not included in the ovrtx C API package.

See :doc:`../core/usd_plugin_paths` for path ownership and registration order.
