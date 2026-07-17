.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Renderer Configuration
======================

The renderer owns ovrtx's GPU resources, stream-ordered work queue, and
rendering pipeline. In **standalone mode** it also owns a runtime stage that
you load USD into. In **attached mode** (ovrtx 0.4+) it renders scene state
managed by an external ovstage instance instead. Create one renderer before
loading USD or stepping RenderProducts.

Creating a Renderer
-------------------

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../examples/python/minimal/main.py
         :language: python
         :start-after: # [snippet:create-renderer]
         :end-before: # [/snippet:create-renderer]
         :dedent:

      Configuration entries are passed through ``RendererConfig``:

      .. literalinclude:: ../../tests/docs/python/test_support_api.py
         :language: python
         :start-after: # [snippet:doc-renderer-config]
         :end-before: # [/snippet:doc-renderer-config]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../examples/c/minimal/main.cpp
         :language: cpp
         :start-after: // [snippet:create-renderer]
         :end-before: // [/snippet:create-renderer]
         :dedent:

      Version and config-entry setup use :c:type:`ovrtx_config_t`:

      .. literalinclude:: ../../tests/docs/c/test_support_api.cpp
         :language: cpp
         :start-after: // [snippet:doc-version-and-config-c]
         :end-before: // [/snippet:doc-version-and-config-c]
         :dedent:

Configuration Entries
---------------------

Common configuration entries include:

.. tab-set::

   .. tab-item:: Python

      .. list-table::
         :header-rows: 1

         * - ``RendererConfig`` entry
           - Description
         * - ``log_file_path=...``
           - Write renderer logs to a file.
         * - ``log_level=...``
           - Set log verbosity.
         * - ``binary_package_root_path=...``
           - Point to a custom binary package root. May include
             ``${executable_dir}`` (see :c:macro:`OVX_CONFIG_EXECUTABLE_DIR_TOKEN`)
             to anchor the path at the running executable's directory.
         * - ``keep_system_alive=True``
           - Keep shared graphics resources alive after the last renderer.
         * - ``active_cuda_gpus="0,1"``
           - Restrict renderer-level CUDA-visible devices.
         * - ``use_vulkan=True``
           - Select the Vulkan backend where supported.
         * - ``motion_bvh=...``
           - Motion BVH mode: ``"disable"`` (default), ``"enable"``, or ``"auto"``.
             Sensors that require motion effects (for example, lidar, radar, acoustic, rolling-shutter camera)
             should use ``"auto"`` or ``"enable"``.

   .. tab-item:: C

      .. list-table::
         :header-rows: 1

         * - Config-entry helper
           - Description
         * - :c:func:`ovrtx_config_entry_log_file_path`
           - Write renderer logs to a file.
         * - :c:func:`ovrtx_config_entry_log_level`
           - Set log verbosity.
         * - :c:func:`ovrtx_config_entry_binary_package_root_path`
           - Point to a custom binary package root. May include
             :c:macro:`OVX_CONFIG_EXECUTABLE_DIR_TOKEN` to anchor the path at the
             running executable's directory.
         * - :c:func:`ovrtx_config_entry_keep_system_alive`
           - Keep shared graphics resources alive after the last renderer.
         * - :c:func:`ovrtx_config_entry_active_cuda_gpus`
           - Restrict renderer-level CUDA-visible devices.
         * - :c:func:`ovrtx_config_entry_use_vulkan`
           - Select the Vulkan backend where supported.
         * - :c:func:`ovrtx_config_entry_motion_bvh`
           - Motion BVH mode: ``OVRTX_MOTION_BVH_DISABLE`` (default),
             ``OVRTX_MOTION_BVH_ENABLE``, or ``OVRTX_MOTION_BVH_AUTO``.

Renderer-level ``active_cuda_gpus`` must be compatible with any per-RenderProduct
``deviceIds`` allow-list. Refer to :ref:`render-product-device-pinning`.

Runtime Package Layout
----------------------

With dynamic linking, ovrtx expects the binary package ``bin`` layout to stay
together next to ``libovrtx-dynamic.so`` or ``ovrtx-dynamic.dll``. The runtime
package includes directories such as ``cache``, ``library``, ``libs``, ``mdl``,
``plugins``, ``rendering-data``, and ``usd_plugins``.

Set ``binary_package_root_path`` only when static linking ovrtx or when a custom
deployment layout separates the loader library from the package directories.
When the package ``bin/`` directory lives next to your executable, pass
``OVX_CONFIG_EXECUTABLE_DIR_TOKEN`` (``"${executable_dir}"``) instead of
resolving the executable directory in client code.

Multi-Renderer Processes
------------------------

For processes that create and destroy multiple renderers, initialize ovrtx once
up front when using the C API, then shut it down once all renderers are gone.

.. literalinclude:: ../../examples/c/vulkan-interop/src/main.cpp
   :language: cpp
   :start-after: // [snippet:initialize-and-create-renderer]
   :end-before: // [/snippet:initialize-and-create-renderer]
   :dedent:

On Linux headless systems, repeatedly creating and destroying renderers can
force shared graphics resources to unload and reload. If that causes native
driver crashes, configure ``keep_system_alive=True`` and initialize ovrtx before
creating renderers. If the issue persists, set
``VK_LOADER_DISABLE_DYNAMIC_LIBRARY_UNLOADING=1`` in the process environment.

Cleanup
-------

Python releases renderer resources when the ``Renderer`` object is destroyed.
In C, cleanup is explicit:

.. literalinclude:: ../../examples/c/minimal/main.cpp
   :language: cpp
   :start-after: // [snippet:unmap-and-cleanup]
   :end-before: // [/snippet:unmap-and-cleanup]
   :dedent:
