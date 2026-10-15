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

Python's ``renderer.config`` returns a detached ``RendererConfig`` copy. In C,
:c:func:`ovrtx_get_config` returns a borrowed view whose entry and payload
storage remains valid until the renderer is destroyed. Both surfaces report
only entries explicitly supplied at creation; omitted defaults and derived
internal settings are not included.

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
         * - ``suppress_deprecation_warnings=True``
           - Suppress Python and native runtime warnings from deprecated APIs.
             Compile-time C/C++ diagnostics are unaffected.
         * - ``keep_system_alive=True``
           - Keep shared graphics resources alive after the last renderer.
         * - ``enable_minimal=...``
           - Enable or disable Minimal at startup. Default: ``None`` (omitted).
         * - ``enable_realtimepathtracing=...``
           - Enable or disable real-time path tracing (RT2) at startup. Default: ``None``.
         * - ``enable_pathtracing=...``
           - Enable or disable PathTracing at startup. Default: ``None``.
         * - ``enable_mdl_displacement=True``
           - Enable MDL material displacement. Disabled when omitted or ``None``.
         * - ``enable_crash_reporter=False``
           - Do not start the ovrtx crash reporter, for hosts that own crash handling.
             Enabled when omitted or ``None``. See `Embedding in a Host Application`_.
         * - ``active_cuda_gpus="0,1"``
           - Restrict renderer-level CUDA-visible devices.
         * - ``datastore_cache="grpcdns://host:port"``
           - Configure the UJITSO datastore cache. ``grpcdns_notls://`` and ``local://`` are also supported.
             When omitted, existing cache defaults and environment configuration remain unchanged.
         * - ``cache_root_path=...``
           - Choose an absolute directory for writable caches. See :ref:`cache-locations`.
         * - ``enable_global_cache_root=True``
           - Use the platform cache directory. Enabled by default. See :ref:`cache-locations`.
         * - ``enable_geometry_streaming=True``
           - Opt in to geometry streaming. Disabled by default when omitted or ``None``.
         * - ``motion_bvh=...``
           - Motion BVH mode: ``"disable"`` (default), ``"enable"``, or ``"auto"``.
             Sensors that require motion effects (for example, lidar, radar, acoustic, rolling-shutter camera)
             should use ``"auto"`` or ``"enable"``.
         * - ``texture_streaming_mode=...``
           - Texture streaming mode: ``"disable"``, ``"synchronous"``, or
             ``"asynchronous"`` (default).

   .. tab-item:: C

      .. list-table::
         :header-rows: 1

         * - Config-entry helper
           - Description
         * - :c:func:`ovrtx_config_entry_log_file_path`
           - Write renderer logs to a file.
         * - :c:func:`ovrtx_config_entry_log_level`
           - Set log verbosity.
         * - :c:func:`ovrtx_config_entry_suppress_deprecation_warnings`
           - Suppress native runtime warnings from deprecated APIs.
             Compile-time deprecation diagnostics are unaffected.
         * - :c:func:`ovrtx_config_entry_binary_package_root_path`
           - Point to a custom binary package root. May include
             :c:macro:`OVX_CONFIG_EXECUTABLE_DIR_TOKEN` to anchor the path at the
             running executable's directory.
         * - :c:func:`ovrtx_config_entry_keep_system_alive`
           - Keep shared graphics resources alive after the last renderer.
         * - :c:func:`ovrtx_config_entry_enable_minimal`
           - Enable or disable Minimal at startup. Omitted by default.
         * - :c:func:`ovrtx_config_entry_enable_realtimepathtracing`
           - Enable or disable real-time path tracing (RT2) at startup. Omitted by default.
         * - :c:func:`ovrtx_config_entry_enable_pathtracing`
           - Enable or disable PathTracing at startup. Omitted by default.
         * - :c:func:`ovrtx_config_entry_enable_mdl_displacement`
           - Enable MDL material displacement. Disabled when omitted.
         * - :c:func:`ovrtx_config_entry_enable_crash_reporter`
           - Do not start the ovrtx crash reporter when ``false``, for hosts that own crash handling.
             Enabled when omitted. See `Embedding in a Host Application`_.
         * - :c:func:`ovrtx_config_entry_active_cuda_gpus`
           - Restrict renderer-level CUDA-visible devices.
         * - :c:func:`ovrtx_config_entry_datastore_cache`
           - Configure the UJITSO datastore cache with ``grpcdns://``,
             ``grpcdns_notls://``, or ``local://``.
         * - :c:func:`ovrtx_config_entry_cache_root_path()`
           - Choose an absolute directory for writable caches. See :ref:`cache-locations`.
         * - :c:func:`ovrtx_config_entry_enable_global_cache_root()`
           - Use the platform cache directory. Enabled by default. See :ref:`cache-locations`.
         * - :c:func:`ovrtx_config_entry_enable_geometry_streaming`
           - Opt in to geometry streaming. Disabled by default when omitted.
         * - :c:func:`ovrtx_config_entry_motion_bvh`
           - Motion BVH mode: ``OVRTX_MOTION_BVH_DISABLE`` (default),
             ``OVRTX_MOTION_BVH_ENABLE``, or ``OVRTX_MOTION_BVH_AUTO``.
         * - :c:func:`ovrtx_config_entry_texture_streaming_mode`
           - Texture streaming mode: ``OVRTX_TEXTURE_STREAMING_DISABLE``,
             ``OVRTX_TEXTURE_STREAMING_SYNCHRONOUS``, or
             ``OVRTX_TEXTURE_STREAMING_ASYNCHRONOUS`` (default).

Deprecation warnings remain enabled by default. Suppression is intended for
phased migrations where deprecated compatibility APIs must remain temporarily;
it does not change their behavior or removal schedule.

Texture streaming mode is process-global and applies to every active renderer
instance. Synchronous mode processes texture feedback synchronously; it does
not make every texture loading operation synchronous.

MDL material displacement is backed by the process-wide Carb setting
``/rtx/material/enableMDLDisplacement``. Renderer creation writes the configured
value, or ``False`` when the option is omitted, so it does not inherit stale
process state.

Renderer-level ``active_cuda_gpus`` must be compatible with any per-RenderProduct
``deviceIds`` allow-list. Refer to :ref:`render-product-device-pinning`.

.. _cache-locations:

Cache Locations
---------------

ovrtx caches compiled shaders and processed assets on disk so later runs can
reuse them. By default, writable caches use a directory for the current user
and ovrtx version:

.. list-table::
   :header-rows: 1

   * - Platform
     - Default cache directory
   * - Linux
     - ``$XDG_CACHE_HOME/ovrtx/<version>`` when ``XDG_CACHE_HOME`` is an
       absolute path; otherwise ``$HOME/.cache/ovrtx/<version>``.
   * - Windows
     - ``%LOCALAPPDATA%/ovrtx/<version>``.

``<version>`` is the ovrtx runtime's major.minor.patch version, for example
``0.7.0``. On Windows, ``%LOCALAPPDATA%`` normally points to
``C:\Users\<username>\AppData\Local``.

Choosing a Cache Directory
~~~~~~~~~~~~~~~~~~~~~~~~~~

Set ``cache_root_path`` in :py:class:`~ovrtx.RendererConfig`, or use
:c:func:`ovrtx_config_entry_cache_root_path()` in C. Choose an absolute path
to a directory your application can write to. ovrtx creates cache directories
as needed. The supplied root is used directly: ovrtx does not append
``ovrtx`` or a version directory.

Configure the cache root before creating the first renderer. The location
applies to all renderers in the process. If you supply a cache root to both
:c:func:`ovrtx_initialize()` and :c:func:`ovrtx_create_renderer()`, use the
same path string in both calls. To change the location, restart the application
with the new configuration. Existing caches are not moved to the new location.

The following snippets choose a cache directory before creating a renderer.
Replace the example path with a writable location for your application.

.. tab-set::

   .. tab-item:: Python

      .. code-block:: python

         import os
         import ovrtx

         cache_root = "C:/ovrtx-cache" if os.name == "nt" else "/tmp/ovrtx-cache"
         # Configure the process-wide location before the first renderer.
         config = ovrtx.RendererConfig(cache_root_path=cache_root)
         renderer = ovrtx.Renderer(config=config)
         # Load your scene and render here.
         renderer.destroy()

   .. tab-item:: C

      .. code-block:: c

         #include <ovrtx/ovrtx.h>
         #include <ovrtx/ovrtx_config.h>

         int main(void)
         {
             #ifdef _WIN32
             const char cache_root[] = "C:/ovrtx-cache";
             #else
             const char cache_root[] = "/tmp/ovrtx-cache";
             #endif

             // Keep the path alive until renderer creation returns.
             ovx_string_t path = {cache_root, sizeof(cache_root) - 1};
             ovrtx_config_entry_t entries[] = {
                 ovrtx_config_entry_cache_root_path(path),
             };
             ovrtx_config_t config = {entries, 1};
             ovrtx_renderer_t* renderer = NULL;
             ovrtx_result_t result = ovrtx_create_renderer(&config, &renderer);
             if (result.status == OVRTX_API_ERROR) {
                 // Report ovrtx_get_last_error() in your application's error handler.
                 return 1;
             }
             // Load your scene and render here.
             ovrtx_destroy_renderer(renderer);
             return 0;
         }

Changing the Linux Cache Base Directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On Linux, set ``XDG_CACHE_HOME`` to an absolute path before starting the
application to choose a different base directory for the default cache.
ovrtx appends ``ovrtx/<version>`` to this path. An explicit ``cache_root_path``
takes precedence over ``XDG_CACHE_HOME``.

``XDG_CACHE_HOME`` has no effect on Windows. Use ``cache_root_path`` to
choose a different cache directory there.

Clearing Caches
~~~~~~~~~~~~~~~

Stop applications using the cache before deleting its directory. ovrtx
recreates writable caches on subsequent runs. The next run can take longer
while shaders and assets are processed again.

Preserving the Previous Cache Location
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to preserve the previous behavior of putting caches next to the
ovrtx library, set ``enable_global_cache_root=False`` in Python, or use
:c:func:`ovrtx_config_entry_enable_global_cache_root()` with ``false`` in C.
This disables selection of the per-user cache directory. Existing custom
cache locations are preserved if already configured.

This option defaults to enabled when omitted (``None`` in Python). An explicit
``cache_root_path`` takes precedence over this option. In C, if either
:c:func:`ovrtx_initialize()` or :c:func:`ovrtx_create_renderer()` explicitly
enables it, that takes precedence over ``false`` in the other call.

Startup Render Mode Availability
--------------------------------

An ovrtx renderer instance is an :py:class:`ovrtx.Renderer` object in Python or
an ``ovrtx_renderer_t*`` handle returned by :c:func:`ovrtx_create_renderer()` in C.
The first ovrtx renderer instance initializes graphics resources shared by all
ovrtx renderer instances in the process. Configure their available rendering modes through
:py:class:`~ovrtx.RendererConfig` in Python, or pass the corresponding entries to
:c:func:`ovrtx_create_renderer()` in C. These entries are not applied by
:c:func:`ovrtx_initialize()`, which initializes the library separately.

For each option, ``True`` enables the mode and ``False`` disables it. Omission
(``None`` in Python) leaves that rendering mode's availability unchanged.
By default, all three rendering modes are enabled. At least one mode must remain
enabled; a configuration that disables every mode fails ovrtx renderer instance creation.

The following examples create an ovrtx renderer instance with only Minimal available. Disabling
PathTracing and RT2 allows ovrtx to avoid allocating resources needed only by those modes.

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_renderer_configuration.py
         :language: python
         :start-after: # [snippet:doc-create-minimal-only-renderer]
         :end-before: # [/snippet:doc-create-minimal-only-renderer]
         :dedent:

   .. tab-item:: C

      Initialize the library with :c:func:`ovrtx_initialize()` before this code,
      and call :c:func:`ovrtx_destroy_renderer()` when finished with the renderer.

      .. literalinclude:: ../../tests/docs/c/test_renderer_configuration.cpp
         :language: cpp
         :start-after: // [snippet:doc-create-minimal-only-renderer-c]
         :end-before: // [/snippet:doc-create-minimal-only-renderer-c]
         :dedent:

Each additional ovrtx renderer instance shares the initialized rendering mode availability. Omitted
options inherit it; an explicit conflicting value fails creation of the new
instance. For example, after the Minimal-only creation above, another ovrtx renderer instance
cannot enable RT2. The failed request does not change an existing ovrtx renderer instance,
release its memory, or trigger shader recompilation. ``renderer.config`` reports
the supplied entries rather than inherited values.

The choice remains fixed while any ovrtx renderer instance uses the shared graphics
resources, or while ``keep_system_alive=True`` retains them after the last instance
is destroyed. If every instance is created with ``keep_system_alive=False``, destroying
all instances releases the shared graphics resources. The next instance can enable RT2/PathTracing.

If an earlier instance used ``keep_system_alive=True`` (the default), first create a
temporary ovrtx renderer instance with ``keep_system_alive=False`` and omit all
``enable_*`` options. Its creation inherits the current rendering mode availability
and clears the keep-alive reference. Then destroy every ovrtx renderer instance,
including the temporary instance. Do not create another instance with
``keep_system_alive=True`` during teardown, as that would retain the resources again.

These examples continue from the Minimal-only instance above, clear retention,
destroy all instances, and create a new instance with Minimal, RT2, and PathTracing available.
The new instance performs graphics initialization again; this is not an in-place
configuration change.

.. tab-set::

   .. tab-item:: Python

      .. literalinclude:: ../../tests/docs/python/test_renderer_configuration.py
         :language: python
         :start-after: # [snippet:doc-reset-render-mode-availability]
         :end-before: # [/snippet:doc-reset-render-mode-availability]
         :dedent:

   .. tab-item:: C

      .. literalinclude:: ../../tests/docs/c/test_renderer_configuration.cpp
         :language: cpp
         :start-after: // [snippet:doc-reset-render-mode-availability-c]
         :end-before: // [/snippet:doc-reset-render-mode-availability-c]
         :dedent:

Destroy the new instance when finished. A C application can also release retained
graphics resources by calling :c:func:`ovrtx_shutdown()` after destroying its ovrtx
renderer instances and matching every :c:func:`ovrtx_initialize()` call with a shutdown call.

RenderProduct mode selection is separate: it chooses among the available modes.
If both Minimal and RT2 are enabled at startup, different RenderProducts can use
either mode. Selecting Minimal on a RenderProduct alone does not provide the
same memory savings as disabling PathTracing and RT2 at startup.

If a RenderProduct requests a disabled rendering mode, ovrtx logs a warning and
selects the first enabled rendering mode in RT2, PathTracing, then Minimal order. With only Minimal available,
an unavailable PathTracing or RT2 request renders in Minimal.

Supported Minimal sensor outputs and motion features remain available.

Backend Support
---------------

ovrtx 0.5 public packages use Vulkan on Windows and Linux. The former
``use_vulkan`` Python field, ``OVRTX_CONFIG_USE_VULKAN`` C key, and
``ovrtx_config_entry_use_vulkan()`` C helper have been removed. Passing the
retired C key from a pre-0.5 binary returns ``OVRTX_API_ERROR`` with a migration
diagnostic; recompile the application against the 0.5 headers and remove the
backend selection entry.

Runtime Package Layout
----------------------

With the shared-loader model, ovrtx expects the binary package ``bin`` layout to stay
together next to ``libovrtx-dynamic.so`` or ``ovrtx-dynamic.dll``. The runtime
package includes directories such as ``cache``, ``library``, ``libs``, ``mdl``,
``plugins``, ``rendering-data``, and ``usd_plugins``.

In C, set ``binary_package_root_path`` through
:c:func:`ovrtx_config_entry_binary_package_root_path` only when static linking
ovrtx or when a custom deployment layout separates the loader library from the
package directories.
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

Spectral Startup Configuration
------------------------------

Python ``RendererConfig.enable_spectral_rendering`` and C
:c:func:`ovrtx_config_entry_enable_spectral_rendering()` prepare spectral shaders,
materials, and physical illuminants when the first renderer is created.
Spectral rendering defaults to off. The choice persists for the process lifetime;
conflicting later values fail.
See :doc:`../sensors/cameras/render_modes/spectral_rendering` for
RenderProduct authoring and limitations.

Embedding in a Host Application
-------------------------------

ovrtx reports initialization failures, such as a missing GPU Foundation or CUDA
runtime, as errors from renderer creation; it never ends the host process.

By default the first renderer starts the ovrtx crash reporter, which installs
process-wide crash handlers and uploads crash dumps. A host application that
owns crash handling should disable it with Python
``RendererConfig(enable_crash_reporter=False)`` or C
:c:func:`ovrtx_config_entry_enable_crash_reporter()` on the first renderer. The
choice persists for the process lifetime; conflicting later values fail.
ovstage never starts a crash reporter.
