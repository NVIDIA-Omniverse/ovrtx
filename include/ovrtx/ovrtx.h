/* Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
 *
 * NVIDIA CORPORATION and its licensors retain all intellectual property
 * and proprietary rights in and to this software, related documentation
 * and any modifications thereto.  Any use, reproduction, disclosure or
 * distribution of this software and related documentation without an express
 * license agreement from NVIDIA CORPORATION is strictly prohibited.
 */

#ifndef OVRTX_H
#define OVRTX_H

#ifndef OVRTX_DEPRECATED
#    if defined(__cplusplus) && __cplusplus >= 201402L
#        define OVRTX_DEPRECATED(msg) [[deprecated(msg)]]
#    elif defined(__GNUC__) || defined(__clang__)
#        define OVRTX_DEPRECATED(msg) __attribute__((deprecated(msg)))
#    elif defined(_MSC_VER)
#        define OVRTX_DEPRECATED(msg) __declspec(deprecated(msg))
#    else
#        define OVRTX_DEPRECATED(msg)
#    endif
#endif

#include "ovrtx_types.h"
#include "ovrtx_data_provider.h"

/* Opaque forward declarations for ovstage interop parameters. Full definitions
 * live in <ovstage/ovstage_api/ovstage_api_types.h> (included transitively
 * from <ovstage/ovstage.h>). Token-identical to those definitions so both
 * headers can coexist in the same translation unit in either include order. */
#ifndef OVSTAGE_ORDINAL_T_DECLARED
#define OVSTAGE_ORDINAL_T_DECLARED
typedef int64_t ovstage_ordinal_t;
#endif

/** Smallest representable ordinal; the initial sealed empty floor, not writable. */
#ifndef OVSTAGE_ORDINAL_MIN
#define OVSTAGE_ORDINAL_MIN ((ovstage_ordinal_t)INT64_MIN)
#endif
/** Largest representable ordinal; also the current-value read end. */
#ifndef OVSTAGE_ORDINAL_MAX
#define OVSTAGE_ORDINAL_MAX ((ovstage_ordinal_t)INT64_MAX)
#endif
#ifndef OVSTAGE_INSTANCE_T_DECLARED
#define OVSTAGE_INSTANCE_T_DECLARED
typedef struct ovstage_instance_t ovstage_instance_t;
#endif

#ifdef __cplusplus
extern "C"
{
#endif

    /** @file
     * General notes
     * Return values:
     *   All operations return status of **OVRTX_API_SUCCESS** if the operation was enqueued successfully,
     *   **OVRTX_API_ERROR** if the operation failed to be enqueued or already failed to execute before
     *   the enqueue call returned.
     *   If an error is returned the error string is valid until the next API call from the current thread.
     *   Note that the error data lives in thread local storage so any operation that might trigger a fiber
     *   switch will also invalidate the error string.
     * Stream ordered asynchronous execution:
     *   All operations that are marked as asynchronous execute in a stream-ordered fashion.
     *   They might return handles that can be used in subsequent operations,
     *   but the actual objects or effects represented by those handles will not necessarily be produced
     *   when the enqueue function calls return.
     *   Stream synchronization events can be used to ensure stream execution for an enqueued function call and all prior calls
     *   have happened.
     *   Specifically a synchronization event ensures that input resources provided to previously enqueued operations
     *   will no longer be accessed after the synchronization event is signaled.
     *   Synchronization events can be device specific to allow ensuring that access to input resources on a certain device
     *   are completed before the synchronization event is signaled.
     *
     *   When a stream ordered operation is executed, the result of the operation will look as if all prior operations
     *   have been executed and completed serially. The underlying execution of operations might overlap, when the system
     *   determines that this will not affect the result of the operation.
     */

    /** @defgroup ovrtx_version Version query
     *  @{
     */

    /**
     * Get the ovrtx API version that the library was compiled with.
     *
     * This function can be called at any time, including before ovrtx_initialize().
     * It can be used to verify that the loaded library matches the header version at runtime.
     *
     * The compile-time version is also available via OVRTX_VERSION_MAJOR, OVRTX_VERSION_MINOR,
     * and OVRTX_VERSION_PATCH macros.
     *
     * @param[out] out_major Major version number
     * @param[out] out_minor Minor version number
     * @param[out] out_patch Patch version number
     */
    void ovrtx_get_version(uint32_t* out_major, uint32_t* out_minor, uint32_t* out_patch);

    /**
     * Get the complete build identity embedded in the loaded OVRTX loader binary that exports this API.
     *
     * This function is safe before ovrtx_initialize(). The returned pointer and all strings it references are immutable
     * and remain valid while the OVRTX loader library remains loaded. Callers should use struct_size to interpret future
     * append-only extensions safely.
     *
     * @return Build information for the loaded OVRTX loader library.
     */
    const ovrtx_build_info_t* ovrtx_get_build_info(void);

    /** @} */ // end of ovrtx_version

    /** @defgroup ovrtx_creation Creation and destruction operations
     *  @{
     */

    /**
     * Register ovrtx's USD schema/plugin discovery paths and lightweight USD/MDL
     * environment, without loading USD or initializing the renderer.
     *
     * This is intended for applications that share an OpenUSD runtime between multiple
     * subsystems (for example ovrtx and ovphysx). USD's schema registry and several
     * TfEnvSettings are populated only once for the process, so every subsystem that
     * contributes schema/plugin paths or USD-facing path environment must publish them
     * before OpenUSD is loaded: USD reads its plugin-path variable as its libraries
     * load, and anything published after that is never seen. Each subsystem calls its
     * own equivalent first, after which the order of initialize calls no longer
     * matters.
     *
     * Binary package root resolution (highest precedence first):
     *  1. The `OMNI_USD_PLUGINS_BASE_PATH` environment variable, if set.
     *  2. `OVRTX_CONFIG_BINARY_PACKAGE_ROOT_PATH` from @p config, if @p config is non-null
     *     and contains that entry. The path may include @ref OVX_CONFIG_EXECUTABLE_DIR_TOKEN,
     *     which the loader substitutes with the absolute directory of the running executable.
     *  3. The directory of the loaded ovrtx loader library (default).
     *
     * @param config Optional configuration (may be NULL). When non-null, the
     *               `OVRTX_CONFIG_BINARY_PACKAGE_ROOT_PATH` entry, if present, anchors the
     *               bundled `usd_plugins/` tree. Pass the same config (or one with an
     *               equivalent `binary_package_root_path`) that you will subsequently
     *               supply to @ref ovrtx_initialize() / @ref ovrtx_create_renderer().
     *
     * Notes:
     * - Safe to call before @ref ovrtx_initialize() and before @ref ovrtx_create_renderer().
     * - Publishes the process-global environment required before OpenUSD initializes:
     *   Hydra/USD toggles, MDL and MaterialX search paths, and the resolver's MDL bypass.
     * - Idempotent for matching roots: the first call performs registration; subsequent
     *   calls with the same effective root are no-ops.
     * - **First-call wins.** Once schema/plugin paths have been registered against an
     *   effective binary package root, subsequent calls (here, or via @ref ovrtx_initialize() /
     *   @ref ovrtx_create_renderer()) that resolve to a different effective root log a
     *   warning to stderr and are no-ops; `PXR_PLUGINPATH_NAME` stays anchored at the
     *   first-registered root (the contract is one-shot per process, since USD's plug
     *   system reads it once during static initialization).
     * - Also registers the same schemas with ovstage, when ovstage is loaded, so an
     *   attached ovstage resolves them as it populates. Call before ovstage's first
     *   populate. Never loads ovstage itself.
     * - Calling this after USD has already been loaded has no retroactive effect on the
     *   plugin-path keys, which were bound at load.
     * - This function does not allocate the ovrtx system, start the ovrtx runtime, load
     *   renderer plugins, or apply renderer settings; it only adjusts process-global
     *   environment used by USD discovery and USD-facing MDL/MaterialX setup.
     *
     * @return Always **OVRTX_API_SUCCESS**. This API does not surface failure through
     *         the return code or @ref ovrtx_get_last_error(); a mismatched root logs a
     *         warning to stderr instead. (This is the one exception to the file-level
     *         return-value rule above.)
     */
    ovrtx_result_t ovrtx_register_schema_paths(const ovrtx_config_t* config);

    /**
     * Number of USD schema/plugin directories ovrtx contributes for @p config.
     *
     * Companion to @ref ovrtx_get_usd_plugin_paths(): use this to size the destination
     * array, then fill it in a follow-up call. Does not touch any environment variable
     * and does not initialize the renderer. Same root-resolution rules as
     * @ref ovrtx_get_usd_plugin_paths() (see that function's docstring for the
     * first-call-wins pin).
     *
     * @param config Optional configuration (may be NULL). Root resolution matches
     *               @ref ovrtx_register_schema_paths().
     * @return Number of directories that @ref ovrtx_get_usd_plugin_paths() will
     *         populate when given sufficient capacity.
     */
    size_t ovrtx_get_usd_plugin_path_count(const ovrtx_config_t* config);

    /**
     * Enumerate ovrtx's USD schema/plugin directories for @p config into
     * @p out_paths, without mutating any environment variable.
     *
     * Intended use: when a process co-loads a separate OpenUSD runtime that reads
     * `PXR_PLUGINPATH_NAME` (for example `usd-core` in Python), the integrator calls
     * this to obtain ovrtx's contributions, filters out any directories that would
     * collide with the host runtime's built-in schemas (e.g. drop `usd_particle_field`
     * on OpenUSD versions that already ship `UsdVol` particle schemas), and appends
     * the remainder to `PXR_PLUGINPATH_NAME` **before** the external runtime opens
     * its first stage. See the timing note on @ref ovrtx_register_schema_paths()
     * for why "before the first stage open" is critical.
     *
     * Root resolution and first-call-wins pin:
     *   Root resolution matches @ref ovrtx_register_schema_paths()
     *   (`OMNI_USD_PLUGINS_BASE_PATH` env, then `OVRTX_CONFIG_BINARY_PACKAGE_ROOT_PATH`
     *   from @p config, then the loader library directory). Enumeration participates
     *   in the same first-call-wins pin as registration: whichever of this function,
     *   @ref ovrtx_register_schema_paths(), @ref ovrtx_initialize(), or
     *   @ref ovrtx_create_renderer() runs first pins the effective root for the
     *   process. A later call resolving a different root logs a mismatch warning to
     *   stderr and acts on the **pinned** root — enumeration returns the pinned
     *   root's paths, and registration registers the pinned root. This keeps the
     *   directories the integrator publishes to `PXR_PLUGINPATH_NAME` consistent
     *   with what ovrtx's bundled OpenUSD actually registers, regardless of the
     *   order the two APIs are called in.
     *
     * String lifetime:
     *   Each returned @ref ovx_string_t points into storage owned by the ovrtx loader
     *   and remains valid for the lifetime of the process. Callers must NOT free the
     *   `ptr` fields or otherwise modify the underlying bytes.
     *
     * @param config              Optional configuration (may be NULL). Root
     *                            resolution matches @ref ovrtx_register_schema_paths().
     * @param out_paths           Destination array. May be NULL when @p out_paths_capacity
     *                            is 0 — in that case only the count is returned. When
     *                            non-NULL, the first `min(count, capacity)` entries are
     *                            populated in a stable order (bundled schema plugins
     *                            first, then the rtx_settings directory).
     * @param out_paths_capacity  Number of `ovx_string_t` slots available in @p out_paths.
     * @return                    The total number of ovrtx plugin directories available
     *                            for @p config (unchanged by capacity — a return value
     *                            greater than @p out_paths_capacity signals truncation).
     */
    size_t ovrtx_get_usd_plugin_paths(const ovrtx_config_t* config,
                                      ovx_string_t* out_paths,
                                      size_t out_paths_capacity);

    /**
     * Programmatically opts out of the OVRTX library startup reporting functionality for this process.
     *
     * OVRTX sends one anonymous report that the library was initialized, from a background thread,
     * the first time OVRTX initializes successfully in a process: when ovrtx_initialize() succeeds, or
     * when ovrtx_create_renderer() initializes it implicitly. It reports at most once per process:
     * creating more renderers, or shutting OVRTX down completely and initializing it again, does not
     * report again. This call disables the report, and to take effect it must be called BEFORE the
     * ovrtx_initialize() (or implicitly initializing ovrtx_create_renderer()) that first initializes
     * OVRTX. Called afterwards it cannot take the report back, because this process has already used
     * up its one reporting opportunity; at best it
     * abandons a report that has not gone out yet, since the reporter waits briefly before assembling
     * anything. The opt-out lasts for the rest of the process, across ovrtx_shutdown() and
     * ovrtx_initialize() cycles. It does not load the OVRTX runtime or initialize anything; it can be
     * called before ovrtx_initialize().
     *
     * Note that if the `NVIDIA_OMNIVERSE_PRODUCT_TELEMETRY_DISABLED` environment variable is defined and
     * set to `1` for this process, this call will be unnecessary. The environment variable based
     * opt-out will always override the programmatic opt-out for the process: once observed it stays in
     * effect for the lifetime of the process, and no OVRTX call can clear it. When used, this
     * environment variable is expected to be defined for the process at launch time. Defining it
     * programmatically with a call such as `setenv()` is strongly discouraged since that can lead to a
     * race condition crash on Linux due to a known bug in the environment variable functions in glibc
     * in versions earlier than 2.41.
     *
     * Other Omniverse libraries in the same process, such as OVXR, send their own reports and have their
     * own opt-out functions; this call affects only OVRTX. `NVIDIA_OMNIVERSE_PRODUCT_TELEMETRY_DISABLED=1`
     * covers all of them.
     *
     * The startup event parameters contain the OVRTX library name and version. The surrounding request
     * also includes a UTC timestamp, the library build variant (`clientVariant`: `"Release"`, or
     * `"iBeta"` for a debug library), and fixed protocol and placeholder fields. See TELEMETRY.md for
     * the full request fields.
     *
     * The message is sent as plain-text JSON over an HTTP connection, with no encryption or obfuscation
     * of the body or the headers, and nothing is written to disk.
     *
     * Note that this startup report will *never* contain any of the following information:
     *   * a user name, user ID, email address, real name, or geographical location.
     *   * any information about the process including process ID, host app name, module names, etc.
     *   * any personal information about a user.
     *   * any intellectual property information related to the host app or its developer.
     *   * any kind of session identifier or even an anonymous user ID.
     *
     * The final ovrtx_shutdown() tears the reporter down and joins its worker thread, so it can block
     * there. Ordinarily that is a join on a thread that finished long ago. The one case that is not
     * bounded is a shutdown that lands while the worker sits in the platform DNS resolver, which takes
     * no timeout and cannot be cancelled; against a black-holing DNS server that can be tens of seconds.
     * An application that needs a hard bound on its own shutdown should opt out, which avoids the worker
     * thread entirely.
     *
     * Threading: safe to call from any thread without synchronization, with or without a live renderer.
     */
    void ovrtx_library_telemetry_opt_out(void);

    /**
     * Initialize the ovrtx loader or increase its ref count.
     *
     * It is allowed to call this function multiple times and for each successful call a
     * corresponding call to ovrtx_shutdown() is required.
     *
     * Note that explicit initialization is not required: creating a render instance with
     * ovrtx_create_renderer() will also initialize the system if needed. Calling
     * ovrtx_initialize() and ovrtx_shutdown() can be used to prevent system shutdown and
     * initialization if the renderer is recreated multiple times.
     * @param config Configuration for the ovrtx system (see @ref ovrtx_config.h). Must be
     *               non-null; may be empty (entry_count 0) for defaults.
     * @return
     * - **OVRTX_API_SUCCESS** if the system was initialized or ref-count was increased
     *   successfully,
     * - **OVRTX_API_ERROR** if initialization failed.
     */
    ovrtx_result_t ovrtx_initialize(const ovrtx_config_t* config);

    /**
     * Shuts down the ovrtx system or decreases it's ref count. One call per call to ovrtx_initialize() is required.
     * Note that any render instances that have not been destroyed will keep the system alive until they are destroyed.
     *
     * A host that exits without shutting down keeps its exit code and gets stdout/stderr flushed, but the process ends
     * in an exit handler that the ovrtx runtime installs (_exit() on Linux, TerminateProcess() on Windows), which
     * skips some exit handlers, static destructors and stream flushes. See "Process Exit" in the Application Flow
     * documentation.
     * @return
     * - **OVRTX_API_SUCCESS** if the system was released successfully (though might still be loaded),
     * - **OVRTX_API_ERROR** if the system shutdown failed or was not initialized.
     */
    ovrtx_result_t ovrtx_shutdown();

    /**
     * Register one provider instance for process-wide resource resolution.
     * @ingroup ovrtx_data_provider
     *
     * Call after ovrtx_initialize() and before submitting references that should use this
     * provider. No renderer instance is required. Descriptor strings and the instance pair
     * are copied; the application retains the immutable vtable, callback code and context
     * until successful removal or completed shutdown. Registration does not take ownership
     * of application storage. Failed registration retains nothing and leaves routes unchanged.
     * Namespace keys must be unique among live registrations. Matching explicit schemes
     * precede catch-alls; priority orders each group, with registration order breaking ties.
     * Application routes precede eligible built-in providers. Only root NOT_HANDLED reroutes.
     * Registration changes routing for future resolutions without changing existing pins.
     * Do not race shutdown or invoke lifecycle operations from provider operation callbacks.
     * Clears the calling thread's last error; failures set ovrtx_get_last_error(). Copy that
     * diagnostic before the next OVRTX API call on the same thread. Asynchronous provider
     * failures instead use their completion status/error; accessor methods return status directly.
     *
     * @param desc Non-NULL registration metadata with current size/version and valid callback capabilities.
     * Borrowed for this call; namespace/scheme strings are copied.
     * @param provider Non-NULL implementation pair with a non-NULL ABI-valid vtable. The context may be NULL.
     * @param[out] out_provider Non-NULL destination, set to a nonzero ID on success and zero on failure.
     * @return
     * - **OVRTX_DATA_OK** if registration succeeded.
     * - **OVRTX_DATA_INVALID_ARGUMENT** for null arguments, invalid sizes/versions, duplicate/invalid namespace,
     *   invalid URI scheme/capabilities, or missing required callbacks/pairs.
     * - **OVRTX_DATA_INVALID_STATE** when the system/service is unavailable or draining.
     */
    ovrtx_data_status_t ovrtx_register_data_provider(const ovrtx_data_provider_desc_t* desc,
                                                     const ovrtx_data_provider_t* provider,
                                                     ovrtx_data_provider_id_t* out_provider);

    /**
     * Remove an idle provider registration atomically without waiting for dependents.
     * @ingroup ovrtx_data_provider
     *
     * Retire consumers, requests, pins, maps and accessors first. BUSY leaves registration
     * and routing unchanged; release dependents and retry. On OK, no provider callback/state
     * remains borrowed by this registration, and the application may release its table,
     * context and code unless another registration uses them. Provider-owned background work
     * (including monitoring) must also be quiesced before destroying its state/code; unregister
     * accounts for runtime-held dependencies, not arbitrary application threads. The ID becomes invalid.
     * Removing one provider does not invalidate pins belonging to another provider.
     * Do not race shutdown or call from provider operation callbacks. Clears the calling
     * thread's last error and sets a diagnostic on failure; copy it before the next API call.
     *
     * @param provider Nonzero live registration ID returned by ovrtx_register_data_provider().
     * @return
     * - **OVRTX_DATA_OK** if removed; ownership of application storage is unchanged.
     * - **OVRTX_DATA_BUSY** while outstanding references or operations retain this provider.
     * - **OVRTX_DATA_INVALID_ARGUMENT** for zero, unknown, already-removed or non-removable IDs.
     * - **OVRTX_DATA_INVALID_STATE** when the system/service is unavailable.
     */
    ovrtx_data_status_t ovrtx_unregister_data_provider(ovrtx_data_provider_id_t provider);

    /** Notify consumers of a batch of changed canonical resource identifiers.
     * @ingroup ovrtx_data_provider
     * Publish all replacement revisions before calling, outside provider locks;
     * callbacks may enqueue reads/reloads. The batch is delivered together, but
     * does not establish an atomic snapshot across resources. Existing immutable
     * pins/leases remain valid and unchanged. Currently only MDL subscribes;
     * textures, SPG, IndeX and NuRec do not automatically reload from this event.
     * Subscribers are called synchronously on this calling thread; callbacks from concurrent
     * notifications may run on different threads. Return waits for notification callbacks,
     * but not for asynchronous reloads or compilation. Do not call recursively from a change
     * callback. No subscriber registration is forwarded to the provider; pin_flags express
     * per-pin tracking interest. Notifications may also be published without interested pins.
     * A tracked resource deletion is a change: publish the identifier and let a fresh pin
     * report NOT_FOUND. Tracking never authorizes changing bytes of an existing pin.
     *
     * @param provider Live provider registration that owns the identifiers.
     * @param identifiers Array of nonempty canonical identifiers returned by this
     * provider, with no embedded NUL. The array and strings are borrowed for this
     * call only. Duplicates are coalesced; an outer package identifier covers its
     * members only for well-formed USDZ bracket paths (including nested packages).
     * Other brackets in opaque identifiers do not imply containment. An inner package
     * identifier includes its enclosing closing brackets. Delivery order is unspecified.
     * @param identifier_count Number of array entries. Zero is a no-op for a live
     * provider and permits a null array; it does not mean all resources changed.
     * @return OVRTX_DATA_OK if accepted (even with no listeners),
     * OVRTX_DATA_INVALID_ARGUMENT for an invalid/removed provider or malformed
     * batch, or OVRTX_DATA_INVALID_STATE when the service is unavailable. The whole
     * batch is validated before delivery; malformed input delivers no events.
     * No notification is required when the logical resource never changes. Providers reporting
     * change_tracking_enabled must deliver changes for the interested pin lifetime. Not callable from a
     * provider operation callback, or concurrently with ovrtx shutdown.
     */
    ovrtx_data_status_t ovrtx_data_notify_changed(ovrtx_data_provider_id_t provider,
                                                const ovx_string_t* identifiers,
                                                uint64_t identifier_count);


    /**
     * Create a new renderer instance. System initialization is done automatically if
     * ovrtx_initialize() has not been called yet, but in that case the config must contain
     * both initialization and renderer settings. The system will be kept running until a
     * corresponding call to ovrtx_destroy_renderer().
     * @param config Configuration for the renderer (see @ref ovrtx_config.h). Must be non-null;
     *               may be empty (entry_count 0) for defaults. Keys are enum-based (e.g.
     *               OVRTX_CONFIG_SYNC_MODE, OVRTX_CONFIG_LOG_FILE_PATH,
     *               OVRTX_CONFIG_ACTIVE_CUDA_GPUS); build entries with
     *               ovrtx_config_entry_bool() and ovrtx_config_entry_string().
     * @param out_renderer [out] Renderer instance
     * @return
     * - **OVRTX_API_SUCCESS** if the renderer was created successfully,
     * - **OVRTX_API_ERROR** if the renderer creation failed.
     */
    ovrtx_result_t ovrtx_create_renderer(const ovrtx_config_t* config, ovrtx_renderer_t** out_renderer);

    /**
     * Read back the configuration entries supplied when a renderer was created.
     *
     * The returned config contains the explicit entries accepted by
     * ovrtx_create_renderer(), in their original order. It does not add omitted
     * defaults or expose internal settings derived from those entries.
     *
     * The entry array and any string or blob payloads are owned by @p renderer
     * and remain valid until ovrtx_destroy_renderer() is called. The caller must
     * not free or modify them. The caller owns only the outer @ref ovrtx_config_t
     * value written to @p out_config.
     *
     * @param renderer Renderer instance from ovrtx_create_renderer().
     * @param[out] out_config Borrowed view of the renderer's explicit config.
     * @return
     * - **OVRTX_API_SUCCESS** if the config was returned successfully,
     * - **OVRTX_API_ERROR** if either argument is null or the OVRTX system is unavailable.
     */
    ovrtx_result_t ovrtx_get_config(const ovrtx_renderer_t* renderer, ovrtx_config_t* out_config);

    /**
     * Destroy a renderer instance.
     *
     * If destruction of a valid renderer fails, the caller retains ownership
     * of the renderer. Do not use it for any other operation; retry
     * ovrtx_destroy_renderer() to finish cleanup.
     * @param renderer Renderer instance to destroy
     * @return
     * - **OVRTX_API_SUCCESS** if the renderer was destroyed successfully,
     * - **OVRTX_API_ERROR** if the renderer destruction failed.
     */
    ovrtx_result_t ovrtx_destroy_renderer(ovrtx_renderer_t* renderer);

    /**
     * Attach an externally-owned ovstage instance to this renderer. While
     * attached, the renderer renders the scene held by that ovstage instead of
     * one it builds itself.
     *
     * A successful attach retains the stage until ovrtx_detach_ovstage() or
     * renderer destruction. The caller may destroy its stage handle after
     * attach; that invalidates only the caller's handle and does not detach the
     * renderer. To switch stages, detach the current stage before attaching
     * another.
     * At most one ovrtx renderer may be attached to an ovstage instance at a
     * time. The stage may be attached to another renderer after it is detached.
     *
     * Use ovrtx_update_from_stage() after ovstage population work and
     * ovrtx_step_with_stage() to render a committed stage state.
     *
     * Attaching rebuilds the renderer's internal render state on the calling
     * thread, so wait for previously enqueued operations with ovrtx_wait_op()
     * before calling it; a step whose result ovrtx_fetch_results() has returned
     * counts as completed, together with the operations enqueued before it.
     * Note that an ovrtx_wait_op() timeout does not cancel
     * an operation: it keeps running, so a timed-out wait does not make it safe
     * to attach or detach. Attach and detach reject pending operations without
     * changing the renderer; wait for completion before retrying.
     * Callers must serialize attach and detach against each other and against
     * calls that enqueue operations on the same renderer. The pending-operation
     * check does not prevent another thread from enqueueing new work.
     *
     * OVRTX validates the ovstage runtime version during attachment. An
     * incompatible version returns OVRTX_API_ERROR without attaching; the
     * error diagnostic reports the expected and supplied versions.
     *
     * @param renderer Renderer instance from ovrtx_create_renderer().
     * @param stage ovstage instance to attach. Must be initialized and remain
     *              valid for the duration of this call.
     * @return
     * - **OVRTX_API_SUCCESS** if the renderer was attached successfully,
     * - **OVRTX_API_ERROR** if the renderer is already attached, the stage is
     *   already attached to another ovrtx renderer, operations are pending, the
     *   stage is invalid, or the attach failed. Rejection because operations
     *   are pending leaves the renderer unchanged. If attachment begins and
     *   then fails, internal state may have changed; do not use the renderer
     *   except to destroy it.
     */
    ovrtx_result_t ovrtx_attach_ovstage(ovrtx_renderer_t* renderer,
                                         ovstage_instance_t* stage);

    /**
     * Detach a previously-attached ovstage instance from this renderer.
     *
     * The renderer returns to standalone mode and no longer renders data from
     * the detached stage.
     *
     * After a successful detach, the renderer may attach the same or a different
     * initialized stage.
     *
     * This tears down internal render state, so the in-flight operation rules
     * described on ovrtx_attach_ovstage() apply here too. Rejection because
     * operations are pending leaves the attachment and render state unchanged;
     * the renderer remains usable and detach may be retried after completion.
     * If teardown itself fails, it may be partial; do not use the renderer
     * except to destroy it. The renderer retains any stage state still needed
     * for safe destruction, so the caller
     * may release its own stage handle before or after destroying the renderer.
     *
     * @param renderer Renderer instance previously passed to ovrtx_attach_ovstage().
     * @return
     * - **OVRTX_API_SUCCESS** if the renderer was detached successfully,
     * - **OVRTX_API_ERROR** if the renderer is not currently attached, operations
     *   are pending, or the detach failed.
     */
    ovrtx_result_t ovrtx_detach_ovstage(ovrtx_renderer_t* renderer);

    /**
     * Enqueue an update of the renderer's internal state from the attached
     * ovstage at the given ordinal. Only valid while attached.
     *
     * The stage must have committed at least once and stage_ordinal must not
     * exceed its write floor. Call this before ovrtx_step_with_stage() so the
     * renderer observes a stable committed snapshot.
     *
     * @param renderer Renderer instance.
     * @param stage_ordinal Ordinal on the attached stage to update from. Must
     *                      be <= the attached stage's write floor.
     * @return
     * - **OVRTX_API_SUCCESS** if the update was enqueued.
     * - **OVRTX_API_ERROR** if no stage is attached or the enqueue failed.
     */
    ovrtx_enqueue_result_t ovrtx_update_from_stage(ovrtx_renderer_t* renderer,
                                                   ovstage_ordinal_t stage_ordinal);

    /** @} */ // end of ovrtx_creation

    /** @defgroup ovrtx_stage_building Stage building operations
     *  @{
     */

    /**
     * Enqueue an asynchronous operation to open a USD file as the root layer of the runtime stage.
     *
     * This resets the current stage to empty and then loads the given file as the root sublayer.
     * Only one root layer can be active at a time; call this again to replace it.
     *
     * Note that errors occuring during loading (including a given USD file not being found) will be reported through the
     * @ref ovrtx_op_wait_result_t::error_op_ids list.
     *
     * @param instance Renderer instance
     * @param file_name Path to the USD file to open
     * @return
     * - **OVRTX_API_SUCCESS** if the operation was enqueued successfully.
     * - **OVRTX_API_ERROR** if the operation was not enqueued successfully.
     */
    OVRTX_DEPRECATED("Use ovstage_population_open_usd_from_file and render via ovrtx_attach_ovstage / ovrtx_step_with_stage.")
    ovrtx_enqueue_result_t ovrtx_open_usd_from_file(ovrtx_renderer_t* instance,
                                                     ovx_string_t file_name);

    /**
     * Enqueue an asynchronous operation to open a USD stage from inline USDA content.
     *
     * This resets the current stage to empty and then loads the given layer content as the root sublayer.
     * Only one root layer can be active at a time; call this again to replace it.
     *
     * @param instance Renderer instance
     * @param root_layer_content USDA content string for the root layer
     * @return
     * - **OVRTX_API_SUCCESS** if the operation was enqueued successfully.
     * - **OVRTX_API_ERROR** if the operation was not enqueued successfully.
     */
    OVRTX_DEPRECATED("Use ovstage_population_open_usd_from_string and render via ovrtx_attach_ovstage / ovrtx_step_with_stage.")
    ovrtx_enqueue_result_t ovrtx_open_usd_from_string(ovrtx_renderer_t* instance,
                                                       ovx_string_t root_layer_content);

    /**
     * Enqueue an asynchronous operation to add a USD file as a reference at the given prim path.
     *
     * A new prim is created at @p prefix_path and the layer is added as a reference on that prim.
     * The prefix path must be an absolute prim path (starting with '/') and must not already exist.
     *
     * @p out_handle is reserved when the add operation is enqueued. A non-zero handle does not mean the USD was
     * loaded. In normal async mode, execution errors are reported through @ref ovrtx_wait_op(). If
     * @ref OVRTX_CONFIG_SYNC_MODE is active, this function returns @ref OVRTX_API_ERROR for those execution errors.
     * Details can be queried with @ref ovrtx_get_last_error().
     *
     * @param instance Renderer instance
     * @param layer_file Path to the USD file to add as a reference
     * @param prefix_path Absolute prim path where the reference will be created
     * @param out_handle [out] Reserved handle for the added reference. It may be used to queue dependent
     *                   stream-ordered operations, but does not by itself indicate the load succeeded.
     * @return
     * - **OVRTX_API_SUCCESS** if the operation was enqueued successfully.
     * - **OVRTX_API_ERROR** if the operation was not enqueued successfully, or if an execution error occurs in sync mode.
     */
    OVRTX_DEPRECATED("Use ovstage_population_add_usd_reference_from_file followed by ovstage_population_apply_usd_changes.")
    ovrtx_enqueue_result_t ovrtx_add_usd_reference_from_file(ovrtx_renderer_t* instance,
                                                              ovx_string_t layer_file,
                                                              ovx_string_t prefix_path,
                                                              ovrtx_usd_handle_t* out_handle);

    /**
     * Enqueue an asynchronous operation to add inline USDA content as a reference at the given prim path.
     *
     * A new prim is created at @p prefix_path and the layer content is added as a reference on that prim.
     * The prefix path must be an absolute prim path (starting with '/') and must not already exist.
     *
     * @p out_handle is reserved when the add operation is enqueued. A non-zero handle does not mean the USD was
     * loaded. In normal async mode, execution errors are reported through @ref ovrtx_wait_op(). If
     * @ref OVRTX_CONFIG_SYNC_MODE is active, this function returns @ref OVRTX_API_ERROR for those execution errors.
     * Details can be queried with @ref ovrtx_get_last_error().
     *
     * @param instance Renderer instance
     * @param layer_content USDA content string for the reference layer
     * @param prefix_path Absolute prim path where the reference will be created
     * @param out_handle [out] Reserved handle for the added reference. It may be used to queue dependent
     *                   stream-ordered operations, but does not by itself indicate the load succeeded.
     * @return
     * - **OVRTX_API_SUCCESS** if the operation was enqueued successfully.
     * - **OVRTX_API_ERROR** if the operation was not enqueued successfully, or if an execution error occurs in sync mode.
     */
    OVRTX_DEPRECATED("Use ovstage_population_add_usd_reference_from_string followed by ovstage_population_apply_usd_changes.")
    ovrtx_enqueue_result_t ovrtx_add_usd_reference_from_string(ovrtx_renderer_t* instance,
                                                                ovx_string_t layer_content,
                                                                ovx_string_t prefix_path,
                                                                ovrtx_usd_handle_t* out_handle);

    /**
     * Enqueue an asynchronous operation to remove a previously added USD reference from the runtime stage.
     * All prims added to the stage during the add operation will be removed.
     * @param instance Renderer instance
     * @param add_usd_handle Handle obtained from ovrtx_add_usd_reference_from_file() or
     *                       ovrtx_add_usd_reference_from_string(). @ref OVRTX_INVALID_USD_HANDLE is
     *                       rejected immediately with @ref OVRTX_API_ERROR, an invalid operation
     *                       index, and details from @ref ovrtx_get_last_error().
     * @return
     * - **OVRTX_API_SUCCESS** if the usd file was removed successfully,
     * - **OVRTX_API_ERROR** if the usd file removal failed.
     */
    OVRTX_DEPRECATED("Use ovstage_population_remove_usd_reference followed by ovstage_population_apply_usd_changes.")
    ovrtx_enqueue_result_t ovrtx_remove_usd(ovrtx_renderer_t* instance,
                                            ovrtx_usd_handle_t add_usd_handle);

    /**
     * Enqueue an asynchronous operation to clone the subtree under the source path to
     * one or more target paths in the runtime stage representation.
     * The source path must exist in the stage and the target paths must not already
     * exist in it. Both are checked before anything is cloned, so a rejected batch
     * creates nothing, and the per-operation error string names the missing source or
     * the targets that already exist, e.g.
     * `ovrtx_clone_usd: target prim already exists at '/Tile3'`.
     * Relationship targets, path values, and USD attribute connections that
     * point inside the source subtree are rebased to each target subtree. External
     * paths are copied unchanged.
     * @param instance Renderer instance
     * @param source_path_in_usd Path to the source path to clone
     * @param target_paths Array of target paths to clone to
     * @param num_target_paths Number of target paths to clone to
     * @return
     * - **OVRTX_API_SUCCESS** if the operation was enqueued successfully,
     * - **OVRTX_API_ERROR** if the operation was not enqueued successfully. A missing
     *   source or an already-existing target fails the operation itself; observe it
     *   through @ref ovrtx_wait_op and @ref ovrtx_get_last_op_error.
     */
    OVRTX_DEPRECATED("Use ovstage_clone(instance, source_path, target_paths, num_target_paths, ordinal) on the attached ovstage instance, then advance the write floor and render via ovrtx_update_from_stage / ovrtx_step_with_stage.")
    ovrtx_enqueue_result_t ovrtx_clone_usd(ovrtx_renderer_t* instance,
                                           ovx_string_t source_path_in_usd,
                                           const ovx_string_t* target_paths,
                                           size_t num_target_paths);

    /**
     * Enqueue an asynchronous operation to reset the runtime stage representation to an empty stage.
     *
     * A successful reset invalidates all previously returned @ref ovrtx_usd_handle_t
     * reference handles. Their values stored by the caller are not cleared and
     * must not be reused. In asynchronous mode, @ref OVRTX_API_SUCCESS only
     * confirms enqueue; use @ref ovrtx_wait_op to observe execution completion.
     *
     * @param instance Renderer instance
     * @return
     * - **OVRTX_API_SUCCESS** if the stage was reset successfully,
     * - **OVRTX_API_ERROR** if the stage reset failed.
     */
    OVRTX_DEPRECATED("Use ovstage_population_reset_usd followed by ovstage_population_apply_usd_changes.")
    ovrtx_enqueue_result_t ovrtx_reset_stage(ovrtx_renderer_t* instance);

    /**
     * Enqueue an asynchronous operation to update the runtime stage representation from a specific USD time.
     * This operation will update all time-sampled attributes in the runtime stage representation to the provided USD time.
     * @param instance Renderer instance
     * @param usd_time USD time to update the stage to
     * @return
     * - **OVRTX_API_SUCCESS** if the stage was updated from the USD time successfully,
     * - **OVRTX_API_ERROR** if the stage update from USD time failed.
     */
    OVRTX_DEPRECATED("Use ovstage_population_apply_usd_time.")
    ovrtx_enqueue_result_t ovrtx_update_stage_from_usd_time(ovrtx_renderer_t* instance, double usd_time);

    /** @} */ // end of ovrtx_stage_building

    /** @defgroup ovrtx_attribute_write Stage attribute write operations
     *  @{
     */

    /**
     * Enqueue an asynchronous write operation from source data into the system's stage representation.
     * This write operation is not fully executed when the call returns and inputs with asynchronous access
     * must remain valid until the stream execution of this operation has completed.
     * @param instance Renderer instance
     * @param binding_handle_or_desc Handle or description of the binding to write to.
     *                    This binding defines the layout of the input data, both in terms
     *                    of attribute data encoding as well as the layout of prims. The binding
     *                    can be generated in place or a persistent handle can be provided to manually
     *                    manage the lifetime. A @ref ovrtx_binding_desc_or_handle_t::binding_handle
     *                    equal to @ref OVRTX_INVALID_ATTRIBUTE_BINDING_HANDLE selects the inline
     *                    @ref ovrtx_binding_desc_or_handle_t::binding_desc and is valid.
     * @param data_array Source data to write. Based on the input_access this source is used during the execution of the write operation,
     *                    not during the enqueue. So it is important that the data source remains valid
     *                    until the write operation has completed.
     *                    This can be determined through stream synchronization events using
     *                    ovrtx_signal_event() and ovrtx_wait_all_events().
     *                    When using asynchronous access of GPU input data, the cuda synchronization event
     *                    must be signaled when the input data is ready to be accessed.
     * @param data_access Determines the time of access to the input data.
     *                    With asynchronous access, the lifetime must be managed by the user,
     *                    while synchronous access incurs a synchronous copy during this call but
     *                    prevents any access after this call returns.
     * @return
     * - **OVRTX_API_SUCCESS** if the attribute was written successfully,
     * - **OVRTX_API_ERROR** if the attribute write failed.
     */
    OVRTX_DEPRECATED("Attribute writes should now be performed on an ovstage instance via ovstage_write_attribute; first obtain a query handle with ovstage_query or ovstage_query_from_path_list.")
    ovrtx_enqueue_result_t ovrtx_write_attribute(ovrtx_renderer_t* instance,
                                                const ovrtx_binding_desc_or_handle_t* binding_handle_or_desc,
                                                const ovrtx_input_buffer_t* data_array,
                                                ovrtx_data_access_t data_access);

    /**
     * Immediately provedes internal memory according to the binding description
     * to be written to by the user and later applied to the stage representation
     * via ovrtx_unmap_attribute()
     * @param instance Renderer instance
     * @param binding_handle_or_desc Handle or description of the binding to use to determine
     *                    the layout of the data to write. The binding
     *                    can be generated in place or a persistent handle can be provided to manually
     *                    manage the lifetime. A @ref ovrtx_binding_desc_or_handle_t::binding_handle
     *                    equal to @ref OVRTX_INVALID_ATTRIBUTE_BINDING_HANDLE selects the inline
     *                    @ref ovrtx_binding_desc_or_handle_t::binding_desc and is valid.
     * @param mapping_desc Description of the mapping to use
     * @param out_attribute_mapping [out] Handle to the attribute mapping
     * @return
     * - **OVRTX_API_SUCCESS** if the attribute was mapped successfully,
     * - **OVRTX_API_ERROR** if the attribute mapping failed.
     */
    OVRTX_DEPRECATED("Attribute mapping should now be performed on an ovstage instance via ovstage_map_attribute and ovstage_fetch_map_next; first obtain a query handle with ovstage_query or ovstage_query_from_path_list.")
    ovrtx_result_t ovrtx_map_attribute(ovrtx_renderer_t* instance,
                                        const ovrtx_binding_desc_or_handle_t* binding_handle_or_desc,
                                        ovrtx_mapping_desc_t mapping_desc,
                                        ovrtx_attribute_mapping_t* out_attribute_mapping);

    /**
     * Enqueue an asynchronous operation to take the data written by the user and do whatever necessary to
     * apply it to the system's stage representation.
     * Note that while the map operation is not asynchronous, the unmap operation is and it determines
     * the logical order of applying the written data to the stage.
     * Multiple mappings can be outstanding on the same stage data with the effects on the stage representation
     * depending on the order of the unmap operations.
     * The data written by the user must be ready when the unmap operation is called for CPU data and when
     * the cuda synchronization event is signaled for GPU data.
     * @param instance Renderer instance
     * @param map_handle Handle to the attribute mapping to unmap.
     *                   @ref OVRTX_INVALID_MAP_HANDLE is rejected immediately with
     *                   @ref OVRTX_API_ERROR, an invalid operation index, and details
     *                   from @ref ovrtx_get_last_error().
     * @param cuda_sync optional cuda synchronization to wait for before the mapped memory is accessed during the
     *                   application of the written data to the stage representation.
     * @return
     * - **OVRTX_API_SUCCESS** if the attribute was unmapped successfully,
     * - **OVRTX_API_ERROR** if the attribute unmap failed.
     */
    OVRTX_DEPRECATED("Unmap committed attribute writes on an ovstage instance via ovstage_unmap_attribute or ovstage_unmap_group.")
    ovrtx_enqueue_result_t ovrtx_unmap_attribute(ovrtx_renderer_t* instance,
                                                ovrtx_map_handle_t map_handle,
                                                ovrtx_cuda_sync_t cuda_sync);

    /**
     * Enqueue an asynchronous operation to create a persistent attribute binding that binds
     * a list of prims to a buffer layout.
     * This operation is an optimization to manage the lifetime of internal resources
     * used to perform write or map operations using this binding.
     * @param instance Renderer instance
     * @param description Description of the binding to create
     * @param out_attribute_binding_handle [out] Handle to the attribute binding
     * @return
     * - **OVRTX_API_SUCCESS** if the attribute binding was created successfully,
     * - **OVRTX_API_ERROR** if the attribute binding creation failed.
     */
    OVRTX_DEPRECATED("Persistent attribute bindings have no direct ovstage equivalent; obtain a reusable query handle with ovstage_query or ovstage_query_from_path_list instead.")
    ovrtx_enqueue_result_t ovrtx_create_attribute_binding(ovrtx_renderer_t* instance,
                                                            const ovrtx_binding_desc_t* description,
                                                            ovrtx_attribute_binding_handle_t* out_attribute_binding_handle);

    /**
     * Enqueue an asynchronous operation to destroy a persistent attribute binding.
     *
     * Successful destruction invalidates the binding handle. Copies stored by
     * the caller are not cleared and must not be reused. In asynchronous mode,
     * @ref OVRTX_API_SUCCESS only confirms enqueue; use @ref ovrtx_wait_op to
     * observe execution completion and @ref ovrtx_get_last_op_error for errors.
     *
     * @param instance Renderer instance
     * @param binding_handle Handle to the attribute binding to destroy. In asynchronous mode,
     *                       @ref OVRTX_INVALID_ATTRIBUTE_BINDING_HANDLE is enqueued and reported as an operation
     *                       execution error by @ref ovrtx_wait_op(); retrieve details with
     *                       @ref ovrtx_get_last_op_error(). In synchronous mode it returns
     *                       @ref OVRTX_API_ERROR with details from @ref ovrtx_get_last_error();
     *                       the returned operation index remains valid.
     * @return
     * - **OVRTX_API_SUCCESS** if the attribute binding was destroyed successfully,
     * - **OVRTX_API_ERROR** if the attribute binding destruction failed.
     */
    OVRTX_DEPRECATED("Release a query handle on an ovstage instance via ovstage_release_query.")
    ovrtx_enqueue_result_t ovrtx_destroy_attribute_binding(ovrtx_renderer_t* instance,
                                                        ovrtx_attribute_binding_handle_t binding_handle);

    /** @} */ // end of ovrtx_attribute_write

    /** @defgroup ovrtx_attribute_read Stage attribute read operations
     *  @{
     */

    /**
     * Enqueue an asynchronous stream-ordered read of attribute values from the runtime stage.
     *
     * The binding identifies which prims and which attribute to read. It reuses the same
     * @ref ovrtx_binding_desc_or_handle_t used for write operations:
     * - @ref ovrtx_binding_desc_t::prims_list_handle or @ref ovrtx_binding_desc_t::prim_list
     *   identifies the prims (typically obtained from a prior @ref ovrtx_query_prims() result).
     * - @ref ovrtx_binding_desc_t::attribute_name selects the attribute.
     * - @ref ovrtx_binding_desc_t::attribute_type serves as an optional type hint for reads;
     *   if zero-initialized the system returns the native type.
     * - @ref ovrtx_binding_desc_t::prim_mode determines behavior for missing prims
     *   (EXISTING_ONLY skips them, MUST_EXIST errors, CREATE_NEW is not supported).
     *
     * Persistent binding handles (@ref ovrtx_attribute_binding_handle_t) optimize repeated reads.
     *
     * The read sees the stage as-if all prior stream-ordered operations have completed.
     *
     * @param instance Renderer instance
     * @param binding_handle_or_desc Binding identifying prims and attribute to read. A
     *                               @ref ovrtx_binding_desc_or_handle_t::binding_handle equal
     *                               to @ref OVRTX_INVALID_ATTRIBUTE_BINDING_HANDLE selects the inline
     *                               @ref ovrtx_binding_desc_or_handle_t::binding_desc and is valid.
     * @param read_dest Optional destination tensor for scalar reads (NULL = allocate internally).
     *                  Must be NULL for array attributes. GPU tensors (kDLCUDA) are supported.
     * @param[out] out_read_handle Handle to the read result for use with @ref ovrtx_fetch_read_result()
     * @return
     * - **OVRTX_API_SUCCESS** if the read was enqueued successfully,
     * - **OVRTX_API_ERROR** if the read failed to enqueue.
     */
    OVRTX_DEPRECATED("Attribute reads should now be performed on an ovstage instance via ovstage_read_attributes; first obtain a query handle with ovstage_query or ovstage_query_from_path_list.")
    ovrtx_enqueue_result_t ovrtx_read_attribute(ovrtx_renderer_t* instance,
                                                const ovrtx_binding_desc_or_handle_t* binding_handle_or_desc,
                                                const ovrtx_read_dest_t* read_dest,
                                                ovrtx_read_handle_t* out_read_handle);

    /**
     * Fetch the results of a prior @ref ovrtx_read_attribute().
     *
     * This operation is synchronous and will block until the read completes or the timeout
     * is reached. Passing 0 as the timeout makes it a non-blocking poll.
     *
     * For fixed-size attributes the result contains one tensor with leading shape [prim_count].
     * For array attributes it contains one tensor per prim with variable length.
     * Result tensors use scalar lanes and type-aware trailing dimensions: a point3f[]
     * array with 10 points is shape [10,3], and a matrix-typed 4x4 double attribute
     * for N prims is shape [N,4,4]. An untyped 16-component tuple is [N,16].
     * When a destination tensor was provided to @ref ovrtx_read_attribute(), buffer_count is 0.
     *
     * All pointers in the output are valid until @ref ovrtx_release_read_result() is called
     * with the same read handle.
     *
     * @param instance Renderer instance
     * @param read_handle Handle obtained from @ref ovrtx_read_attribute().
     *                    @ref OVRTX_INVALID_READ_HANDLE is rejected with @ref OVRTX_API_ERROR
     *                    and details from @ref ovrtx_get_last_error().
     * @param timeout Timeout for the operation
     * @param[out] out_read_output Read data
     * @return
     * - **OVRTX_API_SUCCESS** if the read result was fetched successfully,
     * - **OVRTX_API_ERROR** if the fetch failed,
     * - **OVRTX_API_TIMEOUT** if the result could not be obtained within the timeout.
     */
    OVRTX_DEPRECATED(
        "Fetch read results on an ovstage instance via ovstage_fetch_read_next; release each group with ovstage_release_groups.")
    ovrtx_result_t ovrtx_fetch_read_result(ovrtx_renderer_t* instance,
                                           ovrtx_read_handle_t read_handle,
                                           ovrtx_timeout_t timeout,
                                           ovrtx_read_output_t* out_read_output);

    /**
     * Release resources associated with a prior @ref ovrtx_read_attribute().
     *
     * Safe to call whether or not @ref ovrtx_fetch_read_result() was invoked first;
     * use this to clean up after errors or when the fetched output is no longer needed.
     * After this call all pointers in any previously returned @ref ovrtx_read_output_t
     * become invalid.
     *
     * @param instance Renderer instance
     * @param read_handle Handle from @ref ovrtx_read_attribute().
     *                    @ref OVRTX_INVALID_READ_HANDLE is rejected with @ref OVRTX_API_ERROR
     *                    and details from @ref ovrtx_get_last_error().
     * @param before_destroy_cuda_sync Optional CUDA synchronization to wait for before
     *                                  freeing GPU resources (zero-initialized = no sync)
     * @return
     * - **OVRTX_API_SUCCESS** if the result was released successfully,
     * - **OVRTX_API_ERROR** if the release failed.
     */
    OVRTX_DEPRECATED(
        "Release read resources on an ovstage instance via ovstage_release_read; also call ovstage_release_groups for any groups previously fetched with ovstage_fetch_read_next.")
    ovrtx_result_t ovrtx_release_read_result(ovrtx_renderer_t* instance,
                                             ovrtx_read_handle_t read_handle,
                                             ovrtx_cuda_sync_t before_destroy_cuda_sync);

    /** @} */ // end of ovrtx_attribute_read

    /** @defgroup ovrtx_stage_query Stage query operations
     *  @{
     */

    /**
     * Enqueue an asynchronous stream-ordered query of the runtime stage.
     *
     * The query finds all prims matching the filter criteria in the @ref ovrtx_query_desc_t
     * and groups them by attribute schema (all prims in a group share the same attributes).
     *
     *
     * @param instance Renderer instance
     * @param query_desc Description of the query (filters, attribute reporting)
     * @param[out] out_query_handle Handle for use with @ref ovrtx_fetch_query_results()
     * @return
     * - **OVRTX_API_SUCCESS** if the query was enqueued successfully,
     * - **OVRTX_API_ERROR** if the query failed to enqueue.
     */
    OVRTX_DEPRECATED("Stage queries should now be performed on an ovstage instance via ovstage_query.")
    ovrtx_enqueue_result_t ovrtx_query_prims(ovrtx_renderer_t* instance,
                                             const ovrtx_query_desc_t* query_desc,
                                             ovrtx_query_handle_t* out_query_handle);

    /**
     * Retrieve the results of a prior @ref ovrtx_query_prims() operation.
     *
     * This operation is synchronous and will block until the query completes or the
     * timeout is reached. Passing 0 as the timeout makes it a non-blocking poll.
     *
     * The result contains one @ref ovrtx_query_prim_group_t per matching bucket. Each
     * group has a @ref ovrtx_query_prim_group_t::prim_list_handle that can be plugged
     * directly into @ref ovrtx_binding_desc_t::prims_list_handle for subsequent
     * read or write operations.
     *
     * All pointers in the result are valid until @ref ovrtx_release_query_results() is called.
     *
     * @param instance Renderer instance
     * @param query_handle Handle obtained from @ref ovrtx_query_prims().
     *                     @ref OVRTX_INVALID_QUERY_HANDLE is rejected with @ref OVRTX_API_ERROR
     *                     and details from @ref ovrtx_get_last_error().
     * @param timeout Timeout for the operation
     * @param[out] out_result Query result containing prim groups
     * @return
     * - **OVRTX_API_SUCCESS** if the results were retrieved successfully,
     * - **OVRTX_API_ERROR** if the retrieval failed,
     * - **OVRTX_API_TIMEOUT** if the result could not be obtained within the timeout.
     */
    OVRTX_DEPRECATED("Fetch query results on an ovstage instance via ovstage_fetch_query_result.")
    ovrtx_result_t ovrtx_fetch_query_results(ovrtx_renderer_t* instance,
                                             ovrtx_query_handle_t query_handle,
                                             ovrtx_timeout_t timeout,
                                             ovrtx_query_result_t* out_result);

    /**
     * Release all resources associated with a prior @ref ovrtx_query_prims() result.
     *
     * This destroys all @ref ovrtx_query_prim_group_t::prim_list_handle values in the result,
     * frees attribute descriptor arrays, and releases internal resources.
     *
     * After this call all pointers in the previously returned @ref ovrtx_query_result_t
     * become invalid.
     *
     * @param instance Renderer instance
     * @param query_handle Handle obtained from @ref ovrtx_query_prims().
     *                     @ref OVRTX_INVALID_QUERY_HANDLE is rejected with @ref OVRTX_API_ERROR
     *                     and details from @ref ovrtx_get_last_error().
     * @return
     * - **OVRTX_API_SUCCESS** if the results were released successfully,
     * - **OVRTX_API_ERROR** if the release failed.
     */
    OVRTX_DEPRECATED("Release query results on an ovstage instance via ovstage_release_query_result and ovstage_release_query.")
    ovrtx_result_t ovrtx_release_query_results(ovrtx_renderer_t* instance,
                                               ovrtx_query_handle_t query_handle);

    /**
     * Obtain the renderer's path dictionary for converting between handles and strings.
     *
     * The path dictionary can be used to:
     * - Convert @ref ovrtx_query_prim_group_t::prim_list_handle to string paths
     *   via get_paths_from_path_list / get_strings_from_tokens.
     * - Pre-resolve filter names to tokens via create_tokens_from_strings for
     *   repeated queries.
     * - Build prim lists from strings via create_path_list_from_strings.
     *
     * The returned instance is valid for the lifetime of the renderer.
     *
     * @param instance Renderer instance
     * @param[out] out_path_dictionary The renderer's path dictionary
     * @return
     * - **OVRTX_API_SUCCESS** if the path dictionary was retrieved successfully,
     * - **OVRTX_API_ERROR** if the retrieval failed.
     */
    ovrtx_result_t ovrtx_get_path_dictionary(ovrtx_renderer_t* instance,
                                             path_dictionary_instance_t* out_path_dictionary);

    /** @} */ // end of ovrtx_stage_query

    /** @defgroup ovrtx_sensor_simulation Sensor simulation operations
     *  @{
     */

    /**
     * Enqueue an asynchronous operation that will perform a sensor simulation step for all render products
     * in the provided render product set. The simulation step will be performed for the time span
     * [last_step_time, last_step_time + delta_time], where last_step_time is determined
     * by the history of previous calls to ovrtx_step() or ovrtx_reset().
     * When performing the sensor simulation, the result of prior stream ordered operations
     * affecting the stage since the last call of ovrtx_step() will be considered the state of the stage
     * at time (last_step_time + delta_time).
     * After the simulation step was executed, last_step_time will be updated to (last_step_time + delta_time)
     * for the next call to ovrtx_step().
     * @param instance Renderer instance
     * @param render_products Render products to simulate during this simulation step.
     *                        Accumulated sensor rendering history for all render products not in the
     *                        provided set will be discarded.
     * @param delta_time Finite, non-negative time step within the supported simulation time range
     * @param out_step_result_handle [out] Handle to the step result
     * @return
     * - **OVRTX_API_SUCCESS** if the step was enqueued successfully,
     * - **OVRTX_API_ERROR** if the step enqueue failed, or if @p render_products is malformed:
     *   a null array with a non-zero count, or any entry with a null `ptr`.
     */
    ovrtx_enqueue_result_t ovrtx_step(ovrtx_renderer_t* instance,
                                    ovrtx_render_product_set_t render_products,
                                    double delta_time,
                                    ovrtx_step_result_handle_t* out_step_result_handle);

    /**
     * Attached-mode counterpart of @ref ovrtx_step(). Use this while the renderer
     * is attached to an ovstage via @ref ovrtx_attach_ovstage(): `ordinal` selects
     * which committed state of the attached instance to render. Selecting a state
     * that has not been committed yet (i.e. ordinal > the attached stage's write
     * floor) is rejected.
     *
     * A default stage, an instance of "history_latest", keeps history off. It
     * holds the latest value of every cell and renders it for every committed
     * ordinal. A history-capable stage is an instance of "history_selective",
     * created with that name in the `implementation` member of
     * ovstage_instance_desc_t. History is on for the (prim, attribute) pairs
     * selected with ovstage_enable_history(). When the renderer was created
     * with OVRTX_CONFIG_ENABLE_HISTORY_PRESENTATION, such a stage renders the
     * retained values of the selected pairs at an `ordinal` below its write
     * floor. It returns to the live values afterwards. Without that key the renderer
     * makes no history calls, and a step at an ordinal below the write floor of
     * a history-capable stage fails with a reason that names the key. Unselected
     * pairs render at their latest values. The step fails with the reason when
     * the stage cannot present the ordinal.
     *
     * @param instance Renderer instance (must be attached to an ovstage).
     * @param render_products Render products to simulate during this step.
     * @param delta_time Finite, non-negative time step within the supported simulation time range.
     * @param ordinal ovstage ordinal selecting the committed state to render.
     * @param out_step_result_handle [out] Handle to the step result.
     * @return
     * - **OVRTX_API_SUCCESS** if the step was enqueued successfully,
     * - **OVRTX_API_ERROR** if the renderer is not attached, the ordinal is not
     *   committed, the enqueue failed, or @p render_products is malformed: a null
     *   array with a non-zero count, or any entry with a null `ptr`. The step
     *   operation itself fails, with the reason in ovrtx_get_last_op_error(), when a
     *   history-capable stage cannot present the requested ordinal.
     */
    ovrtx_enqueue_result_t ovrtx_step_with_stage(
        ovrtx_renderer_t* instance,
        ovrtx_render_product_set_t render_products,
        double delta_time,
        ovstage_ordinal_t ordinal,
        ovrtx_step_result_handle_t* out_step_result_handle);

    /**
     * Enqueue an NDC-space pick query for the next @ref ovrtx_step() that renders the given RenderProduct.
     * Results appear as the multi-tensor render variable @ref OVRTX_RENDER_VAR_PICK_HIT, with
     * named CPU tensors (``primPath``, ``objectType``, ``geometryInstanceId``, ``worldPositionM``,
     * ``worldNormal``) and ``uint32`` params (``magic`` = @ref OVRTX_PICK_HIT_MAGIC, ``version`` =
     * @ref OVRTX_PICK_HIT_VERSION, ``hitCount``). The ``primPath`` column stores @ref ovx_primpath_t
     * ids and is populated independently of the query flags; resolve strings via
     * @ref ovrtx_get_path_dictionary() if needed. For a one-pixel-equivalent pick,
     * @ref OVRTX_PICK_FLAG_INCLUDE_TRACKED_INFO requests tracked metadata for the first hit. Without that flag,
     * ``objectType``, ``geometryInstanceId``, ``worldPositionM``, and ``worldNormal`` remain zero-filled.
     * Multi-pixel picks leave those tracked metadata tensors zero-filled even when the flag is set.
     * The query rectangle is
     * specified in normalized RenderProduct coordinates using [0, 1] top-left-origin NDC. It uses the same
     * convention as the old pixel API: right/bottom mark the edge just past the last included pixel. For
     * example, pixel (x, y) on a width x height RenderProduct is [x / width, y / height, (x + 1) / width,
     * (y + 1) / height]; the full RenderProduct is [0, 0, 1, 1]. Out-of-bounds values are rejected
     * (boundary values may be clamped to the valid range to account for floating-point roundoff). If
     * multiple queries are enqueued for the same RenderProduct before a step, the last one wins.
     */
    ovrtx_enqueue_result_t ovrtx_enqueue_pick_query(ovrtx_renderer_t* instance,
                                                    const ovrtx_pick_query_desc_t* desc);

    /**
     * Set per-prim selection outline group ids for renderer-side outline drawing.
     *
     * Group ids are uint8 (0..255). Group 0 clears selection outline state for a prim;
     * non-zero group ids select the style configured by @ref ovrtx_set_selection_group_styles.
     * @p prim_path_ids must be @ref ovx_primpath_t values from this renderer's
     * own path dictionary, as returned by @ref ovrtx_get_path_dictionary(), or
     * from this renderer's pick-hit results. Path ids from any other path
     * dictionary are invalid. @p prim_path_ids and @p group_ids are parallel
     * arrays of length @p path_count.
     * Duplicate prim path ids are allowed; the last occurrence wins.
     *
     * The operation is renderer-only and stream-ordered: it does not write scene
     * attributes or mutate an attached ovstage, and it takes effect on the next
     * @ref ovrtx_step or @ref ovrtx_step_with_stage that occurs after this op completes.
     */
    ovrtx_enqueue_result_t ovrtx_set_selection_outline_group(ovrtx_renderer_t* instance,
                                                             const ovx_primpath_t* prim_path_ids,
                                                             size_t path_count,
                                                             const uint8_t* group_ids);

    /**
     * Set per-prim selection outline group ids using string prim paths.
     *
     * This is a convenience wrapper for callers that do not already have renderer path ids.
     * @p prim_paths and @p group_ids are parallel arrays of length @p path_count.
     * Duplicate prim paths are allowed; the last occurrence wins.
     *
     * Group ids, stream ordering, and renderer-only state semantics match
     * @ref ovrtx_set_selection_outline_group.
     */
    ovrtx_enqueue_result_t ovrtx_set_selection_outline_group_strings(ovrtx_renderer_t* instance,
                                                                     const ovx_string_t* prim_paths,
                                                                     size_t path_count,
                                                                     const uint8_t* group_ids);

    /**
     * Set per-prim pickability for renderer viewport picking.
     *
     * @p prim_path_ids must be @ref ovx_primpath_t values from this renderer's
     * own path dictionary, as returned by @ref ovrtx_get_path_dictionary(), or
     * from this renderer's pick-hit results. Path ids from any other path
     * dictionary are invalid. @p prim_path_ids and @p pickable are parallel
     * arrays of length @p path_count.
     * False excludes a prim from viewport picking where supported.
     *
     * The operation is renderer-only and stream-ordered: it does not write scene
     * attributes or mutate an attached ovstage, and it takes effect on the next
     * @ref ovrtx_step or @ref ovrtx_step_with_stage that occurs after this op completes.
     */
    ovrtx_enqueue_result_t ovrtx_set_pickable(ovrtx_renderer_t* instance,
                                              const ovx_primpath_t* prim_path_ids,
                                              size_t path_count,
                                              const bool* pickable);

    /**
     * Set per-prim pickability using string prim paths.
     *
     * This is a convenience wrapper for callers that do not already have renderer path ids.
     * @p prim_paths and @p pickable are parallel arrays of length @p path_count.
     *
     * Pickability, stream ordering, and renderer-only state semantics match
     * @ref ovrtx_set_pickable.
     */
    ovrtx_enqueue_result_t ovrtx_set_pickable_strings(ovrtx_renderer_t* instance,
                                                      const ovx_string_t* prim_paths,
                                                      size_t path_count,
                                                      const bool* pickable);

    /**
     * Set per-group visual styling (outline color, fill color, and outline width) for one or more selection groups.
     *
     * Group ids are uint8 (0..255) and match the per-prim group id passed to
     * @ref ovrtx_set_selection_outline_group.
     * @p group_ids and @p styles are parallel arrays of length @p count.
     *
     * The operation is stream-ordered: it takes effect on the next @ref ovrtx_step that occurs
     * after this op completes. If multiple writes target the same group id (in this call or across
     * calls), the last writer wins.
     *
     * Fill mode and the default outline width are configured via @ref OVRTX_CONFIG_SELECTION_FILL_MODE
     * and @ref OVRTX_CONFIG_SELECTION_OUTLINE_WIDTH at renderer creation time. Per-group width
     * override and omit-means-unchanged semantics are on
     * @ref ovrtx_selection_group_style_t::outline_width.
     *
     * Outline dashing is **not supported** by the underlying renderer.
     *
     * @param instance Renderer instance
     * @param group_ids Array of @p count group ids
     * @param styles Array of @p count styles, parallel to @p group_ids
     * @param count Number of (group_id, style) pairs
     * @return
     * - **OVRTX_API_SUCCESS** if the operation was enqueued successfully,
     * - **OVRTX_API_ERROR** if the operation failed to enqueue (null arguments, etc.).
     */
    ovrtx_enqueue_result_t ovrtx_set_selection_group_styles(ovrtx_renderer_t* instance,
                                                            const uint8_t* group_ids,
                                                            const ovrtx_selection_group_style_t* styles,
                                                            size_t count);

    /**
     * Enqueue an asynchronous operation to reset the accumulated sensor rendering history for all
     * render products and start future sensor simulation steps at the provided time.
     * After the reset was executed, last_step_time will be updated to the provided time for the next call to ovrtx_step().
     * @param instance Renderer instance
     * @param time Finite, non-negative time within the supported simulation time range
     * @return
     * - **OVRTX_API_SUCCESS** if the reset was enqueued successfully,
     * - **OVRTX_API_ERROR** if the reset enqueue failed.
     */
    ovrtx_enqueue_result_t ovrtx_reset(ovrtx_renderer_t* instance,
                                    double time);

    /**
     * Enqueue an operation that discards the temporal rendering history of RenderProducts.
     *
     * The clear applies to the first frame each RenderProduct produces after this operation, and stays pending
     * until that frame is produced. For a split exposure it applies from the next exposure's first split. Unlike
     * @ref ovrtx_reset, it keeps the sensor schedule, frame numbers and the simulation time. It also resets
     * sensor-model state such as lidar and radar random sequences.
     *
     * The cleared frame renders once: it does not wait for streaming and adds no initial quality frames, while
     * @c omni:rtx:quality:minSpp still applies. Pass @ref OVRTX_CLEAR_HISTORY_FLAG_FIRST_FRAME_QUALITY to render it
     * like the RenderProduct's first frame instead, or @p quality to choose the streaming wait and quality explicitly.
     * Frame 0 and the first frame of a RenderProduct that started paused by @c omni:sensor:frameLimit keep their
     * first-frame quality.
     * A RenderProduct resuming after frames dropped by @c omni:sensor:frameLimit keeps its history and its camera's
     * previous pose, but instance transforms from before the pause are not necessarily retained. Clear it before the
     * step that resumes it when prims moved during the pause, or to start that frame afresh; otherwise motion vectors
     * and temporal reprojection of the moved prims can be wrong on that frame.
     *
     * Clears that have not been applied yet merge: flags combine, a streaming wait and the highest quality win,
     * and tile lists are unioned. Clearing a whole RenderProduct also clears its tiles.
     *
     * With @p tiles, only those tiles of a single tiled RenderProduct are cleared, which drops DLSS and DLSS-RR
     * history for them. They apply to the next completed exposure, on its final split, which DLSS runs on. That render
     * drops them if it resets the RenderProduct's whole history. Flags and @p quality apply to that exposure as for a
     * whole clear, but its streaming wait and quality frames render every tile, and only the listed tiles are reset,
     * after the wait. A wait the exposure needs anyway, or another exposure's wait after a stage change, still resets
     * its whole history.
     * Tile indices outside the RenderProduct's tiles are ignored with a warning. They supersede the deprecated
     * @c omni:rtx:viewTile:renderHistoryReset attributes.
     *
     * @param instance Renderer instance
     * @param render_products RenderProducts to clear. An empty set clears every RenderProduct of the next step.
     * @param flags Bitwise OR of OVRTX_CLEAR_HISTORY_FLAG_* values, or 0.
     * @param quality Optional quality override for the cleared frame, or NULL.
     * @param tiles Optional tiles to clear, or NULL for whole RenderProducts. Requires exactly one RenderProduct.
     * @return
     * - **OVRTX_API_SUCCESS** if the clear was enqueued successfully,
     * - **OVRTX_API_ERROR** if the arguments are invalid. RenderProducts that are not stepped yet are not an error.
     */
    ovrtx_enqueue_result_t ovrtx_clear_history(ovrtx_renderer_t* instance,
                                               ovrtx_render_product_set_t render_products,
                                               uint32_t flags,
                                               const ovrtx_render_quality_t* quality,
                                               const ovrtx_tile_list_t* tiles);

    /**
     * Query the results of a prior enqueued step operation.
     * This operation is synchronous and will block until the results are available or the timeout
     * has passed. By passing 0 as the timeout this operation becomes a non-blocking poll operation
     * that returns immediately if the results are not yet available.
     * The complete production of render outputs is not determined by the completion of the
     * asynchronous ovrtx_step() operation within the stream, so it is not possible to ensure this
     * operations returns the results immediately by waiting for a stream synchronization event
     * signaled after the ovrtx_step() operation.
     * Conversely, once this function has returned the step's result, with OVRTX_API_SUCCESS or with
     * OVRTX_API_ERROR and status OVRTX_EVENT_FAILURE for a failed step, the step operation and every
     * operation enqueued before it have completed and left the operation stream, as after
     * ovrtx_wait_op() on the step's op_index, so they no longer count as pending for
     * ovrtx_attach_ovstage() and ovrtx_detach_ovstage(). This covers neither operations enqueued
     * after the step nor the errors of the operations enqueued before it, which only
     * ovrtx_wait_op() reports, and OVRTX_API_TIMEOUT implies nothing about the operation.
     * The result of this operation contains information about what results each render product has produced.
     * Each render product can have produced 0-n frames of output for m render vars.
     * This operation doesn't return the actual output data, but rather a handle to the output data which can then
     * be mapped to retrieve the actual output data.
     * All strings and pointers inside the result are valid until the result is destroyed by ovrtx_destroy_results().
     * @param instance Renderer instance
     * @param result_handle Handle to the step result to query.
     *                      @ref OVRTX_INVALID_STEP_RESULT_HANDLE is rejected with @ref OVRTX_API_ERROR
     *                      and details from @ref ovrtx_get_last_error().
     * @param timeout Timeout for the operation.
     *                Passing 0 will make the operation non-blocking and return immediately with the current status of the operation.
     * @param out_render_product_set_outputs [out] Render product set outputs
     * @return
     * - **OVRTX_API_SUCCESS** if the render product set outputs were retrieved successfully,
     * - **OVRTX_API_ERROR** if the operation failed,
     * - **OVRTX_API_TIMEOUT** if the result could not be obtained within the timeout.
     */
    ovrtx_result_t ovrtx_fetch_results(ovrtx_renderer_t* instance,
                                        ovrtx_step_result_handle_t result_handle,
                                        ovrtx_timeout_t timeout,
                                        ovrtx_render_product_set_outputs_t* out_render_product_set_outputs);

    /**
     * Maps the rendered output into user accessible memory when the result are available.
     * This operation is synchronous and will block until the output is mapped or the timeout has passed.
     * By passing 0 as the timeout this operation becomes a non-blocking poll operation
     * that returns immediately if the output is not yet mapped.
     * The complete production of render outputs is not determined by the completion of the
     * asynchronous ovrtx_step() operation within the stream, so it is not possible to ensure this
     * operations returns the results immediately by waiting for a stream synchronization event
     * signaled after the ovrtx_step() operation.
     * The result of this operation contains the actual rendered output memory, but it can contain cuda events that must be
     * synchronized to before actually accessing the output memory.
     * Calling map on a output_handle that is part of a step result after calling destroy_results on
     * the step result will return an error.
     *
     * Tensor layout contract for @ref ovrtx_render_var_output_t::tensors "ovrtx_render_var_output_t::tensors":
     * - A render variable carries `num_tensors` named tensor slots; each `tensors[i].dl` describes one slot.
     * - Image-shaped tensors are channel-last with:
     *   - `ndim = 3`
     *   - `shape = [height, width, channels]`
     *   - `dtype.lanes = 1`
     * - Non-image tensors may use different ranks/layouts (for example, 1D buffers for point clouds).
     * - Strides, when provided, are in elements (DLPack convention).
     * - Params (@ref ovrtx_render_var_output_t::params) are always CPU-resident DLPack tensors;
     *   their shape encodes scalar vs. array (e.g. `{1}` for scalar, `{N}` for array).
     * @param instance Renderer instance
     * @param output_handle Handle to the output to map.
     *                      @ref OVRTX_INVALID_RENDER_VAR_OUTPUT_HANDLE is rejected with @ref OVRTX_API_ERROR
     *                      and details from @ref ovrtx_get_last_error().
     * @param map_output_desc Description of the output to map
     * @param timeout Timeout for the operation.
     *                Passing 0 will make the operation non-blocking and return immediately with the current status of the operation.
     * @param out_render_var_output [out] Mapped render variable output
     * @return
     * - **OVRTX_API_SUCCESS** if the output was mapped successfully.
     * - **OVRTX_API_ERROR** if the output mapping failed.
     * - **OVRTX_API_TIMEOUT** if the result could not be obtained within the timeout.
     */
    ovrtx_result_t ovrtx_map_render_var_output(ovrtx_renderer_t* instance,
                                            ovrtx_render_var_output_handle_t output_handle,
                                            const ovrtx_map_output_description_t* map_output_desc,
                                            ovrtx_timeout_t timeout,
                                            ovrtx_render_var_output_t* out_render_var_output);

    /**
     * Unmaps the render variable output and frees resources associated with the prior ovrtx_map_render_var_output().
     * When this is called all access to the buffer provided by map_render_var_output must be done.
     * This call determines the lifetime of the resources made accessible through the prior map_render_var_output call and
     * this lifetime is independent of ovrtx_destroy_results().
     * It is safe to call unmap on a map_handle that was produced from a step result that has been destroyed by destroy_results.
     * @param instance Renderer instance.
     * @param map_handle Handle to the map to unmap. @ref OVRTX_INVALID_RENDER_VAR_OUTPUT_MAP_HANDLE is rejected
     *                   with @ref OVRTX_API_ERROR and details from
     *                   @ref ovrtx_get_last_error().
     * @param before_destroy_cuda_sync CUDA synchronization to wait for before the mapped memory is destroyed.
     * @return
     * - **OVRTX_API_SUCCESS** if the output was unmapped successfully,
     * - **OVRTX_API_ERROR** if the output unmapping failed.
     */
    ovrtx_result_t ovrtx_unmap_render_var_output(ovrtx_renderer_t* instance,
                                                ovrtx_render_var_output_map_handle_t map_handle,
                                                ovrtx_cuda_sync_t before_destroy_cuda_sync);

    /**
     * Releases all resources associated with the result of a sensor simulation step, with the exception of resources provided by calls to
     * ovrtx_map_render_var_output(). Those are only released through ovrtx_unmap_render_var_output().
     * Destroying a result does not wait for its step operation; unless ovrtx_fetch_results() has returned
     * the result, wait with ovrtx_wait_op() before ovrtx_attach_ovstage() or ovrtx_detach_ovstage().
     * @param instance Renderer instance
     * @param result_handle Handle to the step result to destroy.
     *                      @ref OVRTX_INVALID_STEP_RESULT_HANDLE is rejected with @ref OVRTX_API_ERROR
     *                      and details from @ref ovrtx_get_last_error().
     * @return
     * - **OVRTX_API_SUCCESS** if the step result was destroyed successfully,
     * - **OVRTX_API_ERROR** if the step result destruction failed.
     */
    ovrtx_result_t ovrtx_destroy_results(ovrtx_renderer_t* instance,
                                          ovrtx_step_result_handle_t result_handle);

    /** @} */ // end of ovrtx_sensor_simulation

    /** @defgroup ovrtx_stream Stream operations
     *  @{
     */

    /**
     * Wait for completion of all operations up to and including the specified operation id.
     * This operation is synchronous and will block until the operations are completed or the timeout has passed.
     * Passing 0 as the timeout makes the operation a non-blocking poll.
     * The out structure returns any errors observed since the last wait call and, on timeout, the
     * lowest still-pending op id.
     * For each op id in out_wait_result->error_op_ids, call ovrtx_get_last_op_error(op_id) to get
     * the corresponding error string.
     * Both out_wait_result->error_op_ids and strings returned by ovrtx_get_last_op_error() are
     * transient thread-local data and are invalidated by the next call to ovrtx_wait_op() on the
     * same thread. Consume/copy them before the next wait call.
     * @param instance Renderer instance
     * @param op_id Non-zero operation id to wait for. @ref OVRTX_INVALID_OP_ID is rejected
     *              with @ref OVRTX_API_ERROR and details from @ref ovrtx_get_last_error().
     * @param time_out Timeout for the operation
     * @param out_wait_result [out] Wait result information (error op ids and lowest pending op id)
     * @return
     * - **OVRTX_API_SUCCESS** if the operations were waited for successfully,
     * - **OVRTX_API_ERROR** if the wait failed (e.g., invalid op id),
     * - **OVRTX_API_TIMEOUT** if not all operations completed within the timeout.
     */
    ovrtx_result_t ovrtx_wait_op(ovrtx_renderer_t* instance,
            ovrtx_op_id_t op_id,
            ovrtx_timeout_t time_out,
            ovrtx_op_wait_result_t* out_wait_result);

    /*--------------------------------------------------*/
    /* Operation status query */
    /*--------------------------------------------------*/

    /**
     * Query the status of a long-running operation.
     *
     * This operation is synchronous and returns immediately with the current
     * status of the specified operation. The returned status structure contains
     * progress information and named resource counters.
     * All strings and pointers in out_status are valid until ovrtx_release_op_status
     * is called. This function must be paired with ovrtx_release_op_status.
     *
     * Counter semantics:
     * - name: Identifies the resource type (e.g., "shaders", "textures", "materials")
     * - current: Number of items processed so far
     * - total: Total items to process, or 0 if the total is not yet known
     * - The set of counters varies by operation type
     *
     * @param instance Renderer instance
     * @param op_id Operation ID to query (from ovrtx_enqueue_result_t.op_index).
     *              @ref OVRTX_INVALID_OP_ID is rejected with @ref OVRTX_API_ERROR
     *              and details from @ref ovrtx_get_last_error().
     * @param out_status [out] Status information for the operation
     * @return OVRTX_API_SUCCESS if status was retrieved successfully,
     *         OVRTX_API_ERROR if op_id is invalid or query failed
     */
    ovrtx_result_t ovrtx_query_op_status(ovrtx_renderer_t* instance,
        ovrtx_op_id_t op_id,
        ovrtx_op_status_t* out_status);

    /**
     * Release resources associated with a previously queried operation status.
     *
     * After this call, all pointers in the status structure become invalid.
     * This must be called for every successful ovrtx_query_op_status call.
     *
     * @param instance Renderer instance
     * @param status Status structure to release (previously obtained from
     *               ovrtx_query_op_status)
     * @return OVRTX_API_SUCCESS if released successfully,
     *         OVRTX_API_ERROR if release failed
     */
    ovrtx_result_t ovrtx_release_op_status(ovrtx_renderer_t* instance,
        ovrtx_op_status_t* status);

    /** @} */ // end of ovrtx_stream

    /** @defgroup ovrtx_extension Extension querying
     *  @{
     */

    /**
     * Query for an extension interface by name.
     *
     * This query entry point is part of the public OVRTX C API.
     * All extension names and vtable contracts are internal.
     *
     * @param name The name of the extension
     * @param vtable [out] Vtable with function pointers for the extension
     * @return
     * - **OVRTX_API_SUCCESS** if the extension was queried successfully,
     * - **OVRTX_API_ERROR** if unavailable, or if this extension requires initialization.
     */
    ovrtx_result_t ovrtx_query_extension(const char* name, const void** vtable);

    /** @} */ // end of ovrtx_extension

    /** @defgroup ovrtx_profiling Performance profiling
     *  @{
     */

    /** Predefined metric UID for default-render-target frames per second. */
#define OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_FPS 1ull

    /** Predefined metric UID for render-thread work time in milliseconds. */
#define OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_RENDER_THREAD_TIME 3ull

    /** Optional file-capture configuration. Strings are copied before start returns. */
    typedef struct ovrtx_profiling_config_t
    {
        /** Existing writable directory. {NULL, 0} uses the persistent user directory. */
        ovx_string_t output_path;
        /** Basename without an extension. {NULL, 0} generates a timestamp-based name.
         * Existing recordings are not overwritten; collisions add a timestamp suffix.
         */
        ovx_string_t file_name;
    } ovrtx_profiling_config_t;

    /** Start process-wide CPU/GPU/RTX profiling, with optional file capture.
     * Call after creating a renderer. config may be NULL; either string may be {NULL, 0}.
     * NULL config or both string pointers NULL disables file output.
     * Providing either string pointer enables file capture; an empty provided
     * string selects the default directory/name. Strings are UTF-8 views. When saving,
     * the output directory must already exist and be writable.
     * An already active profiling session is not replaced. Serialize capture-control calls
     * with renderer teardown; rendering may continue concurrently.
     * @param[in] config Optional output path/name configuration. NULL starts live-only profiling.
     * @return OVRTX_API_SUCCESS or OVRTX_API_ERROR; see ovrtx_get_last_error().
     */
    ovrtx_result_t ovrtx_start_profiling(const ovrtx_profiling_config_t* config);

    /** Stop profiling and flush and close any file capture. May block on output work.
     * Call before destroying the last renderer. Stopping when no capture is active succeeds.
     * @return OVRTX_API_SUCCESS or OVRTX_API_ERROR; see ovrtx_get_last_error().
     */
    ovrtx_result_t ovrtx_stop_profiling(void);

    /** @brief Inject a scalar value without execution attribution.
     * The sample's execution ID is zero. This does not create a metric or start profiling.
     * @param[in] metric_uid OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_FPS or
     *     OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_RENDER_THREAD_TIME.
     * @param[in] value Frames per second for FPS, or elapsed milliseconds for Render Thread.
     */
    void ovrtx_add_performance_metric_value(uint64_t metric_uid, double value);

    /** @brief Inject a scalar value attributed to the calling CPU thread.
     * This does not create a metric or start profiling.
     * @param[in] metric_uid OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_FPS or
     *     OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_RENDER_THREAD_TIME.
     * @param[in] value Frames per second for FPS, or elapsed milliseconds for Render Thread.
     */
    void ovrtx_add_performance_metric_value_with_thread_execution_id(uint64_t metric_uid, double value);

    /** @brief Inject a scalar value with an explicitly supplied execution identity.
     * The sample carries the supplied identity.
     * @param[in] metric_uid OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_FPS or
     *     OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_RENDER_THREAD_TIME.
     * @param[in] value Frames per second for FPS, or elapsed milliseconds for Render Thread.
     * @param[in] execution_id Caller-defined identity. Zero means unspecified.
     */
    void ovrtx_add_performance_metric_value_with_custom_execution_id(
        uint64_t metric_uid, double value, uint32_t execution_id);

    /** One sampled scalar value. Time is in nanoseconds since profiling started. */
    typedef struct ovrtx_performance_value_t
    {
        uint64_t timestamp_ns; /**< Sample timestamp in nanoseconds since profiling started; duration samples use their start time. */
        double value; /**< Sampled value in the corresponding metric's units. */
        uint64_t parent_uid; /**< Parent metric for this sample's invocation; zero means root or unspecified. */
        uint32_t execution_id; /**< CPU-thread or RTX-GPU identity; zero means unspecified. */
    } ovrtx_performance_value_t;

    /** Public metric information and its newly collected values.
     * Aggregate statistics cover the active profiling session, not only this update.
     * RTX stages are grouped under GPU/render-graph and viewport hierarchies.
     * RTX Memory categories are Geometry, Textures, Volumes, Gaussians, SPG,
     * Output Buffers and Internal, with Geometry subcategories where available.
     * Memory values use MiB; GPU, host and virtual-reservation scopes are separate.
     * Tracked host allocations are not process physical memory. Do not add inclusive
     * parents to their children, or reservations to allocations. Grouped RTX durations
     * can combine separate intervals and do not represent contiguous GPU occupancy.
     */
    typedef struct ovrtx_performance_metric_t
    {
        uint64_t uid; /**< Metric identity within the current profiling session; do not reuse across restarts. */
        uint64_t parent_uid; /**< Default hierarchy parent, or zero for a root; each value carries its invocation parent. */
        ovx_string_t name; /**< Borrowed UTF-8 display name. */
        ovx_string_t units; /**< Borrowed UTF-8 unit label; duration values normally use milliseconds. */
        ovx_string_t info; /**< Borrowed UTF-8 description of the measurement. */
        ovx_string_t group_name; /**< Borrowed UTF-8 category name. */
        const ovrtx_performance_value_t* values; /**< Borrowed sample span; read only value_count entries. */
        size_t value_count; /**< Number of samples in values; may be zero when this metric has no new sample. */
        double average; /**< Session-wide running average, in units; best-effort during concurrent injection. */
        double minimum; /**< Session-wide running minimum, in units; best-effort during concurrent injection. */
        double maximum; /**< Session-wide running maximum, in units; best-effort during concurrent injection. */
    } ovrtx_performance_metric_t;

    /** Owned update batch. Initialize to zero before its first use.
     * Strings and arrays remain valid until this container is updated or released.
     * Do not copy ownership or use the same container concurrently. Release before
     * destroying the last renderer; serialize reads with capture restart/teardown.
     */
    typedef struct ovrtx_performance_data_update_t
    {
        uint64_t collection_time_ns; /**< Collection time in nanoseconds since profiling started; not a sample-time boundary. */
        const ovrtx_performance_metric_t* metrics; /**< Borrowed metric array owned by this batch; read only metric_count entries. */
        size_t metric_count; /**< Number of entries in metrics. */
        ovx_string_t json; /**< Borrowed UTF-8 JSON from the JSON getter; empty after the structured getter. */
        void* handle; /**< Opaque owner managed by the update/release functions. Do not copy, replace or free it directly. */
    } ovrtx_performance_data_update_t;

    /** Collect one batch of public metrics without interrupting rendering.
     * Initialize the output container to zero, then retain and reuse it between calls.
     * The first call returns retained history; later calls return newly available samples.
     * Independent containers have independent progress, reset automatically after profiling restarts.
     * Within each metric, samples follow collection order across batches, not timestamp order.
     * Sample timestamps can precede an earlier returned sample or a previous collection time.
     * collection_time_ns is informational, not a cursor or a bound on sample timestamps.
     * Structured and JSON getters share progress.
     * Prefer copying every 500 ms-1 s (1-2 Hz), or 200-250 ms (4-5 Hz) for live UI.
     * At no more than 120 samples/s per metric, a 4 s interval accumulates 480 samples
     * and fits retained history if bursts, scheduling and copying stay within its margin.
     * Longer intervals make larger, slower batches; cost grows with metric/sample count.
     * Copying does not change sampling cadence, recover overwritten history or guarantee
     * a complete snapshot during concurrent updates.
     * The output container can be reused. Copy metric and sample data before updating or releasing it.
     * @param[in,out] out_data Non-null, initially zeroed container. Its previous borrowed views are invalidated.
     * @return OVRTX_API_SUCCESS or OVRTX_API_ERROR; see ovrtx_get_last_error().
     */
    ovrtx_result_t ovrtx_get_performance_data_update(ovrtx_performance_data_update_t* out_data);

    /** Collect the same public update as UTF-8 JSON in out_data->json.
     * JSON contains collection_time_ns and a metrics array. Each metric has uid,
     * parent_uid, name, units, info, group_name and values (timestamp_ns, value, parent_uid, execution_id).
     * Ownership, retained progress and polling guidance are identical to ovrtx_get_performance_data_update.
     * @param[in,out] out_data Non-null, initially zeroed or previously returned container; json is a borrowed view.
     * @return OVRTX_API_SUCCESS or OVRTX_API_ERROR; see ovrtx_get_last_error().
     */
    ovrtx_result_t ovrtx_get_performance_data_update_as_json(ovrtx_performance_data_update_t* out_data);

    /** @brief Release a batch and zero its container, invalidating every borrowed string and sample span.
     * Release before renderer teardown. Releasing an empty initialized container succeeds.
     * @param[in,out] data Non-null container initialized to zero or returned by an update function.
     * @return OVRTX_API_SUCCESS, or OVRTX_API_ERROR for an invalid argument; see ovrtx_get_last_error().
     */
    ovrtx_result_t ovrtx_release_performance_data_update(ovrtx_performance_data_update_t* data);

    /** @} */ // end of ovrtx_profiling

    /** @defgroup ovrtx_error Error handling
    *  @{
    */

    /**
     * Returns the error string for the latest API call on the calling thread. The string is
     * valid until the next API call on the same thread.
     */
    ovx_string_t ovrtx_get_last_error();

    /**
     * Returns the error string for the provided operation id from the last call to ovrtx_wait_op
     * on the calling thread. The string is valid until the next call to ovrtx_wait_op on the same
     * thread. This is a lookup-only identifier: @ref OVRTX_INVALID_OP_ID and any operation id
     * not present in the last wait result return an empty string rather than an API error.
     * @param op_id Operation id to get the error string for
     */
    ovx_string_t ovrtx_get_last_op_error(ovrtx_op_id_t op_id);

    /** @} */ // end of ovrtx_error

#ifdef __cplusplus
}
#endif

#endif /* OVRTX_H */
