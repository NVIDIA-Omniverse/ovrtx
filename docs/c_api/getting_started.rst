.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Getting Started in C
====================

ovrtx runtime validation requires an NVIDIA RTX-capable GPU, a supported NVIDIA driver, internet access, and execution outside sandboxed environments. The minimal example downloads scene assets from S3. Supported driver versions are listed in :doc:`../driver_requirements`.

The C/C++ examples require CMake 3.16 or newer, a C++17 compiler, and a development environment. Building the whole example set through the top-level ``examples/c/CMakeLists.txt`` needs CMake 3.18. Install the prerequisites for your platform:

.. tab-set::

   .. tab-item:: Windows

      Install `Visual Studio 2022 17.8 or newer <https://visualstudio.microsoft.com/>`_ (which provides CMake and a C++ toolchain). ovrtx binaries require the Microsoft VC runtime 14.38 or newer; VS 2022 17.8 is the oldest release that ships it. Older toolchains work only if you separately install a `VC redistributable <https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170>`_ of 14.38 or newer.

   .. tab-item:: Linux (Ubuntu)

      .. code-block:: bash

         sudo apt-get install build-essential cmake

Next, clone `the repository <https://github.com/NVIDIA-Omniverse/ovrtx>`__:

.. code-block:: bash

   git clone https://github.com/NVIDIA-Omniverse/ovrtx.git
   cd ovrtx/examples/c/minimal

Finally, configure, build, and run the minimal example for your platform:

.. tab-set::

   .. tab-item:: Windows

      .. code-block:: text

         cmake -B build
         cmake --build build --config Release
         .\build\static\Release\minimal.exe

   .. tab-item:: Linux

      .. code-block:: bash

         cmake -B build -DCMAKE_BUILD_TYPE=Release
         cmake --build build
         ./build/static/minimal

The minimal example shows how to create the renderer, load an OpenUSD scene, and render a single image. The results are copied back to the CPU for writing out as a PNG.

.. image:: ../../img/example-minimal.jpg
   :alt: Minimal example output
   :align: center

A successful run writes ``./out.png``. The output should match the reference image above.

The first step from a newly built application will block for 1-2 minutes while shaders are compiled and cached.

Installation
------------

CMake
^^^^^

ovrtx requires CMake 3.16 or newer; ``find_package(ovrtx)`` fails on older versions. ovrtx binary distributions can be found on the GitHub `Releases page <https://github.com/NVIDIA-Omniverse/ovrtx/releases>`__, and contain a CMake config.

The simplest way to add ovrtx as a dependency to your project is using CMake FetchContent:

.. filtered-literalinclude:: ../../examples/c/cmake/ovrtx.cmake
   :language: cmake
   :start-after: # [snippet:ovrtx_fetch]
   :end-before: # [/snippet:ovrtx_fetch]
   :omit-markers:
   :exclude-pattern: ^\s*#\s*AUTOREMOVE:

Note that the macro above is provided for convenience in ``ovrtx.cmake`` in the ``examples/c/cmake`` directory in `the repository <https://github.com/NVIDIA-Omniverse/ovrtx>`__.

Alternatively, download the appropriate package for your system from the `Releases page <https://github.com/NVIDIA-Omniverse/ovrtx/releases>`__, point
``CMAKE_PREFIX_PATH`` at the directory where you extracted the archive, and use ``find_package(ovrtx)``
from your ``CMakeLists.txt``. The macro above already takes this path when it can: it tries
``find_package(ovrtx QUIET)`` first and only downloads the package if that fails.

For a complete example ``CMakeLists.txt`` that includes package fetching, both
loader models, the Windows release-CRT setting, and runtime setup, see
``examples/c/minimal/CMakeLists.txt``. The example builds both models from the
same source:

.. filtered-literalinclude:: ../../examples/c/minimal/CMakeLists.txt
   :language: cmake
   :start-after: # [snippet:linking-models]
   :end-before: # [/snippet:linking-models]
   :dedent:

Model #1 links the static forwarding loaders (``ovrtx::ovrtx_static`` and
``ovstage::ovstage_static``). Model #2 links the shared forwarding loaders
(``ovrtx::ovrtx`` and ``ovstage::ovstage``). In both models, the runtime and
OpenUSD remain unloaded until the first initialization call. If ovstage may be
initialized first, call :c:func:`ovrtx_register_schema_paths` before that call.

Calling ``ovrtx_setup_runtime()`` is required, not optional: linking succeeds without it, but the
application will fail at runtime because it cannot locate the ``bin/`` payload described in
`Runtime Packaging and Deployment`_. The helper reads ``OVRTX_BINARY_DIR``, which
``find_package(ovrtx)`` sets to the package ``bin/`` directory, so you can also use that variable
directly if you prefer to stage the runtime yourself.

The setup above covers ovrtx alone. From ovrtx 0.4 onward an application normally also links
ovstage and attaches a stage to the renderer; see :doc:`/core/ovstage_integration` for that
combined setup.

For other build systems, download the appropriate package for your system from the `Releases page <https://github.com/NVIDIA-Omniverse/ovrtx/releases>`__. The headers are in the
``include`` directory and libraries are in ``lib`` and ``bin``, in either static or dynamic flavors.

Runtime Packaging and Deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

ovrtx requires several libraries and other runtime dependencies to be present and discoverable at runtime. These are all included in the ovrtx binary distribution under the ``bin`` directory:

.. code-block:: text

   bin/
   ├── libovrtx-dynamic.so / ovrtx-dynamic.dll
   ├── cache/
   ├── library/
   ├── libs/
   ├── mdl/
   ├── plugins/
   ├── rendering-data/
   └── usd_plugins/

The ovrtx shared loader automatically opens the runtime and its dependencies from this layout. If you need to deploy your application with a different layout, you can point ovrtx to the correct paths using the :c:func:`ovrtx_config_entry_binary_package_root_path` helper function when configuring the renderer. When the package ``bin/`` directory lives next to your executable, use :c:macro:`OVX_CONFIG_EXECUTABLE_DIR_TOKEN` (``"${executable_dir}"``) instead of resolving the executable directory in client code:

.. code-block:: c

   ovrtx_config_entry_t config_entries[] = {
       ovrtx_config_entry_binary_package_root_path(
           literal_to_ovx_string(OVX_CONFIG_EXECUTABLE_DIR_TOKEN))
   };

   ovrtx_config_t config;
   config.entries = config_entries;
   config.entry_count = sizeof(config_entries) / sizeof(config_entries[0]);

   ovrtx_renderer_t* renderer;
   ovrtx_result_t result = ovrtx_create_renderer(&config, &renderer);

Note that when static linking ovrtx, you must provide the binary package root path or ovrtx will not be able to find the required dependencies at runtime.

Sharing OpenUSD with Other Subsystems
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

ovrtx-owned OpenUSD (this section):
"""""""""""""""""""""""""""""""""""

When ovrtx shares its bundled OpenUSD runtime with other subsystems in the same process
(for example ovphysx), every subsystem must publish its USD schema and plugin discovery
paths *before OpenUSD is loaded* — USD reads the plugin path as its libraries load, and
builds the schema registry it feeds only once per process. Use
:c:func:`ovrtx_register_schema_paths` early so the order of subsequent initialize calls
does not matter:

.. code-block:: c

   // Register schema paths up front, then initialize subsystems in any order.
   // Pass the same config you will later supply to ovrtx_initialize / ovrtx_create_renderer
   // so the binary package root used during registration matches the one used at init.
   ovphysx_register_schema_paths();
   ovrtx_register_schema_paths(&config);

   ovrtx_create_renderer(&config, &renderer);

For default deployments where ovrtx lives next to the loader library, ``NULL`` is
acceptable and the loader-library directory is used as the root:

.. code-block:: c

   ovrtx_register_schema_paths(NULL);

For ovrtx-only applications this call is not required — :c:func:`ovrtx_initialize` /
:c:func:`ovrtx_create_renderer` register the same paths automatically.

Once schema paths have been registered against an effective binary package root, any
later :c:func:`ovrtx_register_schema_paths`, :c:func:`ovrtx_initialize`, or
:c:func:`ovrtx_create_renderer` call that resolves to a different root logs a warning
to stderr and is treated as a no-op against the first-registered root —
USD plugin-path registration is one-shot per process, so the first call wins.
:c:func:`ovrtx_get_usd_plugin_path_count` and
:c:func:`ovrtx_get_usd_plugin_paths` participate in the same pin: calling either before
any registration pins the enumerated root, and a later registration resolving a
different root warns and registers the pinned root, so the directories published to an
external OpenUSD always match what ovrtx's bundled OpenUSD registers. Use the same
``OVRTX_CONFIG_BINARY_PACKAGE_ROOT_PATH`` (or the same ``OMNI_USD_PLUGINS_BASE_PATH``
override) throughout the process. See the function's API documentation for the full
contract.

In an ovstage-attached application, the call also registers ovrtx's families with ovstage,
so they resolve as ovstage populates. Call it before ovstage's first populate.

External OpenUSD runtimes:
""""""""""""""""""""""""""

If the same process **also** uses OpenUSD outside ovrtx — for example a ``usd-core``
Python distribution, a Kit host, or any OpenUSD build that reads the upstream
``PXR_PLUGINPATH_NAME`` env var — choose one of the following integration models:

* :c:func:`ovrtx_register_schema_paths` (and the implicit registration done by
  :c:func:`ovrtx_initialize` / :c:func:`ovrtx_create_renderer`) always writes to the
  ovrtx-namespaced ``OV_PXR_PLUGINPATH_2511`` key. When
  ``OVRTX_PXR_SCHEMA_AUTO_REGISTER=1`` is set, it also publishes the same schema paths
  to upstream ``PXR_PLUGINPATH_NAME``.
* To select or filter the external runtime's paths yourself, leave the opt-in unset,
  obtain ovrtx's plugin directories via
  :c:func:`ovrtx_get_usd_plugin_paths`, drop any entries that collide with the external
  runtime's own built-in schemas, and append the remaining directories to
  ``PXR_PLUGINPATH_NAME``.
* **Timing is critical.** OpenUSD's plug registry is populated once during static
  initialization / the first schema lookup. Setting ``PXR_PLUGINPATH_NAME`` *after* the
  external OpenUSD runtime has already opened its first stage has no retroactive effect
  on schema discovery — the paths must be in place **before** the first stage is opened
  on that runtime.

.. code-block:: c

   // Enumerate ovrtx's schema plugin directories (no env-var mutation).
   size_t count = ovrtx_get_usd_plugin_path_count(NULL);
   ovx_string_t* paths = (ovx_string_t*)calloc(count, sizeof(ovx_string_t));
   if (count == 0 || paths != NULL)
   {
       ovrtx_get_usd_plugin_paths(NULL, paths, count);

       // Append the desired subset to PXR_PLUGINPATH_NAME BEFORE any external OpenUSD
       // opens its first stage. Filter out directories that collide with the external
       // runtime's built-in schemas as appropriate.
       //   ... integrator-owned append logic ...

       // Only after the append is done, hand control to the external OpenUSD runtime.
       //   external_openusd_open_stage(...);
   }

   free(paths);

The strings returned by :c:func:`ovrtx_get_usd_plugin_paths` are owned by ovrtx and
valid for the lifetime of the process; the caller must not free them.

Minimal Example
---------------

.. filtered-literalinclude:: ../../examples/c/minimal/main.cpp
   :language: cpp
   :start-after: // its affiliates is strictly prohibited.
   :exclude-pattern: ^\s*//\s*\[/?snippet:

.. image:: ../../img/example-minimal.jpg
   :alt: Minimal example output
   :align: center

Next Steps
----------

* Explore more :doc:`../examples/index` including the :doc:`Vulkan Interop <../examples/c_vulkan_interop>` example with real-time GPU rendering, click picking, marquee selection, and styled selection outlines with translucent fill.
* Refer to the :doc:`index` for the full C API reference.
