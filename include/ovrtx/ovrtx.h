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

/* Opaque forward declarations for ovstage interop parameters. Full definitions
 * live in <ovstage/ovstage_api/ovstage_api_types.h> (included transitively
 * from <ovstage/ovstage.h>). Token-identical to those definitions so both
 * headers can coexist in the same translation unit in either include order. */
#ifndef OVSTAGE_ORDINAL_T_DECLARED
#define OVSTAGE_ORDINAL_T_DECLARED
typedef uint64_t ovstage_ordinal_t;
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
     * before the registry is first consulted (typically when the first stage is opened).
     * Each subsystem calls its own equivalent (e.g.
     * `ovphysx_prepare_usd_plugins()`, `ovrtx_register_schema_paths(...)`) before any of
     * them initialize, after which the order of initialize calls no longer matters.
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
     * - Also publishes the same process environment that the ovrtx loader sets before
     *   loading ovrtx.dylib (Hydra/USD toggles, MDL search paths, MaterialX search
     *   paths, and resolver MDL-bypass env).
     * - Idempotent for matching roots: the first call performs registration; subsequent
     *   calls with the same effective root are no-ops.
     * - **First-call wins.** Once schema/plugin paths have been registered against an
     *   effective binary package root, subsequent calls (here, or via @ref ovrtx_initialize() /
     *   @ref ovrtx_create_renderer()) that resolve to a different effective root log a
     *   warning to stderr and are no-ops; `PXR_PLUGINPATH_NAME` stays anchored at the
     *   first-registered root (the contract is one-shot per process, since USD's plug
     *   system reads it once during static initialization).
     * - Calling this after USD has already been loaded and the schema registry populated
     *   has no retroactive effect on previously-discovered schemas.
     * - This function does not allocate the ovrtx system, start Carbonite, load renderer
     *   plugins, or apply general Carb settings; it only adjusts process-global
     *   environment used by USD discovery and USD-facing MDL/MaterialX setup.
     *
     * @return Always **OVRTX_API_SUCCESS**. This API does not surface failure through
     *         the return code or @ref ovrtx_get_last_error(); a mismatched root logs a
     *         warning to stderr instead. (This is the one exception to the file-level
     *         return-value rule above.)
     */
    ovrtx_result_t ovrtx_register_schema_paths(const ovrtx_config_t* config);

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
     * @return
     * - **OVRTX_API_SUCCESS** if the system was released successfully (though might still be loaded),
     * - **OVRTX_API_ERROR** if the system shutdown failed or was not initialized.
     */
    ovrtx_result_t ovrtx_shutdown();

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
     * Destroy a renderer instance.
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
     * Must be called before the first step, and matched by ovrtx_detach_ovstage()
     * before either the renderer or the stage is destroyed. Re-attaching or
     * swapping the attached stage is not currently supported.
     *
     * Use ovrtx_update_from_stage() after ovstage population work and
     * ovrtx_step_with_stage() to render a committed stage state.
     *
     * @param renderer Renderer instance from ovrtx_create_renderer().
     * @param stage ovstage instance to attach. Must be initialized.
     * @return
     * - **OVRTX_API_SUCCESS** if the renderer was attached successfully,
     * - **OVRTX_API_ERROR** if the renderer is already attached, the stage is
     *   invalid, or the attach failed.
     */
    ovrtx_result_t ovrtx_attach_ovstage(ovrtx_renderer_t* renderer,
                                         ovstage_instance_t* stage);

    /**
     * Detach a previously-attached ovstage instance from this renderer.
     *
     * The renderer returns to standalone mode and no longer renders data from
     * the detached stage.
     *
     * Attaching a different stage after detach is not currently supported.
     *
     * @param renderer Renderer instance previously passed to ovrtx_attach_ovstage().
     * @return
     * - **OVRTX_API_SUCCESS** if the renderer was detached successfully,
     * - **OVRTX_API_ERROR** if the renderer is not currently attached, or the
     *   detach failed.
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
     * @param add_usd_handle Handle obtained from ovrtx_add_usd_reference_from_file() or ovrtx_add_usd_reference_from_string()
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
     * The source path must exist in the stage.
     * The target paths must not already exist in the stage.
     * Relationship targets, path values, and USD attribute connections that
     * point inside the source subtree are rebased to each target subtree. External
     * paths are copied unchanged.
     * @param instance Renderer instance
     * @param source_path_in_usd Path to the source path to clone
     * @param target_paths Array of target paths to clone to
     * @param num_target_paths Number of target paths to clone to
     * @return
     * - **OVRTX_API_SUCCESS** if the path was cloned successfully,
     * - **OVRTX_API_ERROR** if the path cloning failed.
     */
    OVRTX_DEPRECATED("Use ovstage_clone(instance, source_path, target_paths, num_target_paths, ordinal) on the attached ovstage instance, then advance the write floor and render via ovrtx_update_from_stage / ovrtx_step_with_stage.")
    ovrtx_enqueue_result_t ovrtx_clone_usd(ovrtx_renderer_t* instance,
                                           ovx_string_t source_path_in_usd,
                                           const ovx_string_t* target_paths,
                                           size_t num_target_paths);

    /**
     * Enqueue an asynchronous operation to reset the runtime stage representation to an empty stage.
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
     *                    manage the lifetime.
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
     *                    manage the lifetime.
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
     * @param map_handle Handle to the attribute mapping to unmap
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
     * @param instance Renderer instance
     * @param binding_handle Handle to the attribute binding to destroy
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
     * @param binding_handle_or_desc Binding identifying prims and attribute to read
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
     * For scalar attributes the result contains a single tensor of shape [prim_count].
     * For array attributes the result contains one tensor per prim with variable length.
     * Multi-component C attribute tensors encode component count in @c DLTensor::dtype.lanes:
     * for example, a point3f[] array with 10 points is shape [10] with lanes=3, and
     * a 4x4 double matrix attribute for N prims is shape [N] with lanes=16.
     * When a destination tensor was provided to @ref ovrtx_read_attribute(), buffer_count is 0.
     *
     * All pointers in the output are valid until @ref ovrtx_release_read_result() is called
     * with the same read handle.
     *
     * @param instance Renderer instance
     * @param read_handle Handle obtained from @ref ovrtx_read_attribute()
     * @param timeout Timeout for the operation
     * @param[out] out_read_output Read data
     * @return
     * - **OVRTX_API_SUCCESS** if the read result was fetched successfully,
     * - **OVRTX_API_ERROR** if the fetch failed,
     * - **OVRTX_API_TIMEOUT** if the result could not be obtained within the timeout.
     */
    OVRTX_DEPRECATED("Fetch read results on an ovstage instance via ovstage_fetch_read_next; release each group with ovstage_release_group.")
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
     * @param read_handle Handle from @ref ovrtx_read_attribute()
     * @param before_destroy_cuda_sync Optional CUDA synchronization to wait for before
     *                                  freeing GPU resources (zero-initialized = no sync)
     * @return
     * - **OVRTX_API_SUCCESS** if the result was released successfully,
     * - **OVRTX_API_ERROR** if the release failed.
     */
    OVRTX_DEPRECATED("Release read resources on an ovstage instance via ovstage_release_read; also call ovstage_release_group for any groups previously fetched with ovstage_fetch_read_next.")
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
     * @param query_handle Handle obtained from @ref ovrtx_query_prims()
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
     * @param query_handle Handle obtained from @ref ovrtx_query_prims()
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
     * @param delta_time Time step to simulate
     * @param out_step_result_handle [out] Handle to the step result
     * @return
     * - **OVRTX_API_SUCCESS** if the step was enqueued successfully,
     * - **OVRTX_API_ERROR** if the step enqueue failed.
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
     * @param instance Renderer instance (must be attached to an ovstage).
     * @param render_products Render products to simulate during this step.
     * @param delta_time Time step to simulate.
     * @param ordinal ovstage ordinal selecting the committed state to render.
     * @param out_step_result_handle [out] Handle to the step result.
     * @return
     * - **OVRTX_API_SUCCESS** if the step was enqueued successfully,
     * - **OVRTX_API_ERROR** if the renderer is not attached, the ordinal is not
     *   committed, or the enqueue failed.
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
     * ids; resolve strings via @ref ovrtx_get_path_dictionary() if needed. The query rectangle is
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
     * The operation is renderer-only and stream-ordered: it does not write to Fabric
     * or an attached ovstage, and it takes effect on the next @ref ovrtx_step or
     * @ref ovrtx_step_with_stage that occurs after this op completes.
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
     * The operation is renderer-only and stream-ordered: it does not write to Fabric
     * or an attached ovstage, and it takes effect on the next @ref ovrtx_step or
     * @ref ovrtx_step_with_stage that occurs after this op completes.
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
     * Set per-group visual styling (outline color and fill color) for one or more selection groups.
     *
     * Group ids are uint8 (0..255) and match the per-prim group id passed to
     * @ref ovrtx_set_selection_outline_group.
     * @p group_ids and @p styles are parallel arrays of length @p count.
     *
     * The operation is stream-ordered: it takes effect on the next @ref ovrtx_step that occurs
     * after this op completes. If multiple writes target the same group id (in this call or across
     * calls), the last writer wins.
     *
     * Global state (outline thickness, fill mode) is configured via @ref OVRTX_CONFIG_SELECTION_OUTLINE_WIDTH
     * and @ref OVRTX_CONFIG_SELECTION_FILL_MODE at renderer creation time.
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
     * @param time Time to reset the simulation to
     * @return
     * - **OVRTX_API_SUCCESS** if the reset was enqueued successfully,
     * - **OVRTX_API_ERROR** if the reset enqueue failed.
     */
    ovrtx_enqueue_result_t ovrtx_reset(ovrtx_renderer_t* instance,
                                    double time);

    /**
     * Query the results of a prior enqueued step operation.
     * This operation is synchronous and will block until the results are available or the timeout
     * has passed. By passing 0 as the timeout this operation becomes a non-blocking poll operation
     * that returns immediately if the results are not yet available.
     * The complete production of render outputs is not determined by the completion of the
     * asynchronous ovrtx_step() operation within the stream, so it is not possible to ensure this
     * operations returns the results immediately by waiting for a stream synchronization event
     * signaled after the ovrtx_step() operation.
     * The result of this operation contains information about what results each render product has produced.
     * Each render product can have produced 0-n frames of output for m render vars.
     * This operation doesn't return the actual output data, but rather a handle to the output data which can then
     * be mapped to retrieve the actual output data.
     * All strings and pointers inside the result are valid until the result is destroyed by ovrtx_destroy_results().
     * @param instance Renderer instance
     * @param result_handle Handle to the step result to query
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
     * @param output_handle Handle to the output to map
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
     * @param map_handle Handle to the map to unmap.
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
     * @param instance Renderer instance
     * @param result_handle Handle to the step result to destroy
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
     * @param op_id Non-zero operation id to wait for. @ref OVRTX_INVALID_HANDLE is not waitable
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
     * @param op_id Operation ID to query (from ovrtx_enqueue_result_t.op_index)
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
     * Query for an internal extension interface by name.
     * @param name The name of the extension
     * @param vtable [out] Vtable with function pointers for the extension
     * @return
     * - **OVRTX_API_SUCCESS** if the extension was queried successfully,
     * - **OVRTX_API_ERROR** if the extension is unavailable or if the system is not initialized yet.
     */
   ovrtx_result_t ovrtx_query_extension(const char* name,
        const void** vtable);


    /** @} */ // end of ovrtx_extension

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
     * thread.
     * @param op_id Operation id to get the error string for
     */
    ovx_string_t ovrtx_get_last_op_error(ovrtx_op_id_t op_id);

    /*--------------------------------------------------*/
    /* Logging callback */
    /*--------------------------------------------------*/

    /**
     * Set a process-global callback that receives every carb log message produced
     * by ovrtx (and by any plugin or framework code loaded under it).
     *
     * The callback is shared across the whole ovrtx process, not per-renderer:
     * its lifetime is tied to ovrtx_initialize / ovrtx_shutdown, not to any
     * particular renderer instance. As a result the callback receives messages
     * emitted before the first ovrtx_create_renderer (framework startup, plugin
     * loading, the OVRTX logging banner) as well as messages emitted during and
     * after ovrtx_destroy_renderer (e.g. asset eviction during teardown).
     *
     * Only one callback can be active at a time; calling this function replaces
     * the previous callback. Pass NULL as @p callback to disable delivery.
     *
     * Calling this function before ovrtx_initialize or after ovrtx_shutdown
     * returns OVRTX_API_ERROR with a descriptive error string accessible via
     * ovrtx_get_last_error().
     *
     * The callback does NOT carry per-renderer attribution. ovrtx may add a v2
     * callback type with (renderer, op_id) once per-op TLS plumbing exists.
     *
     * Thread safety: The callback may be invoked from any thread. The
     * implementation guarantees that callbacks are serialized for the process
     * (no concurrent invocations).
     *
     * Channel filter syntax
     * ---------------------
     * @p channel_filter is a comma-separated list of `<channel_prefix>=<level>`
     * entries (RUST_LOG-style). The channel prefix is matched against carb's
     * dotted source name; longest matching prefix wins. Per-channel rules
     * override @p severity for matched channels. Channels not matched by any
     * rule use @p severity as their threshold. The empty / NULL filter is
     * equivalent to "every channel uses @p severity".
     *
     * Accepted level names (case-insensitive):
     *     "verbose" (alias "debug"), "info", "warn" (alias "warning"),
     *     "error", "fatal".
     *
     * Whitespace around tokens and trailing commas are tolerated; empty entries
     * are skipped. Malformed entries (missing `=`, unknown level name, empty
     * channel name) cause this function to return OVRTX_API_ERROR with a
     * descriptive ovrtx_get_last_error() string and leave the previously
     * installed callback state unchanged.
     *
     * Examples:
     *   - `""`                                     no rules; every channel uses @p severity
     *   - `"omni.usd=error"`                       omni.usd* uses error+, everything else uses @p severity
     *   - `"carb=warn,carb.tasking=verbose"`       carb.tasking uses verbose+, other carb.* uses warn+,
     *                                              everything else uses @p severity
     *
     * @param severity Default severity threshold applied to channels not
     *                 matched by an explicit rule in @p channel_filter. Use
     *                 OVRTX_LOG_INFO to receive INFO and above by default;
     *                 OVRTX_LOG_ERROR to filter out everything but errors by
     *                 default. Note that ovrtx_log_severity_t does not expose
     *                 carb's lower verbose / debug levels: those are dropped
     *                 by the default and can only be received by an explicit
     *                 per-channel rule like "carb.tasking=verbose" in @p
     *                 channel_filter.
     * @param channel_filter Optional comma-separated `<channel>=<level>` list.
     *                       Pass NULL to apply @p severity uniformly.
     * @param callback Callback function to receive log messages, or NULL to disable
     * @param user_data User-provided context passed to each callback invocation
     * @return OVRTX_API_SUCCESS if callback was set successfully,
     *         OVRTX_API_ERROR if the system is not initialized or the filter
     *         string failed to parse
     */
    ovrtx_result_t ovrtx_set_log_callback(ovrtx_log_severity_t severity,
        const ovx_string_t* channel_filter,
        ovrtx_log_callback_t callback,
        void* user_data);

    /**
     * Flush all pending log messages through the global callback.
     *
     * This operation blocks until all log messages generated up to this point
     * have been delivered through the log callback. This is useful when you
     * need to ensure all logs have been processed before proceeding (e.g.,
     * after an operation completes or fails, or before tearing the system
     * down).
     *
     * If no log callback is set, this function returns immediately with success.
     *
     * Calling this function before ovrtx_initialize or after ovrtx_shutdown
     * returns OVRTX_API_ERROR.
     *
     * Note: This only flushes messages generated before this call. Messages
     * generated concurrently or after this call may not be included.
     *
     * @param timeout Maximum time to wait for flush to complete
     * @return OVRTX_API_SUCCESS if all pending logs were flushed,
     *         OVRTX_API_TIMEOUT if flush did not complete within timeout,
     *         OVRTX_API_ERROR if flush failed (system not initialized)
     */
    ovrtx_result_t ovrtx_flush_log(ovrtx_timeout_t timeout);

    /*--------------------------------------------------*/

    /** @} */ // end of ovrtx_error

#ifdef __cplusplus
}
#endif

#endif /* OVRTX_H */
