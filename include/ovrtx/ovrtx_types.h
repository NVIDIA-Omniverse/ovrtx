/* Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
 *
 * NVIDIA CORPORATION and its licensors retain all intellectual property
 * and proprietary rights in and to this software, related documentation
 * and any modifications thereto.  Any use, reproduction, disclosure or
 * distribution of this software and related documentation without an express
 * license agreement from NVIDIA CORPORATION is strictly prohibited.
 */

#ifndef OVRTX_TYPES_H
#define OVRTX_TYPES_H

#define OVRTX_VERSION_MAJOR 0
#define OVRTX_VERSION_MINOR 4
#define OVRTX_VERSION_PATCH 1

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#include "../ovx/dlpack/dlpack.h"
#include "../ovx/types.h"
#include "../ovx/path_dictionary/path_dictionary.h"

#ifdef __cplusplus
extern "C"
{
#endif

    /** @defgroup ovrtx_core_types Core renderer types
     *  @{
     */

    typedef struct ovrtx_renderer_t ovrtx_renderer_t;

    /** @} */ // end of ovrtx_core_types

    /** @defgroup ovrtx_handle_types Handle types
     *  @{
     */

    /** Handle representing a USD stage. */
    typedef uint64_t ovrtx_usd_handle_t;
    /** Handle representing an event. */
    typedef uint64_t ovrtx_event_handle_t;
    /** Handle representing a persistent attribute binding. */
    typedef uint64_t ovrtx_attribute_binding_handle_t;
    /** Handle representing a resource mapping that can be used to unmap it. */
    typedef uint64_t ovrtx_map_handle_t;
    /** Handle to the result of a @ref ovrtx_step() operation. */
    typedef uint64_t ovrtx_step_result_handle_t;
    /** Handle to a rendered output; pass to @ref ovrtx_map_render_var_output() to access its data. */
    typedef uint64_t ovrtx_render_var_output_handle_t;
    /** Handle to the mapping of a rendered output that can be used to unmap it with @ref ovrtx_unmap_render_var_output(). */
    typedef uint64_t ovrtx_render_var_output_map_handle_t;
    /** Identifier of a particular asynchronous operation such as @ref ovrtx_open_usd_from_file() that can be used to poll or wait. */
    typedef uint64_t ovrtx_op_id_t;

    /**
    * Sentinel value representing an invalid/null ovrtx handle.
    * Valid handles non-zero, so 0 is reserved to indicate "no handle" or "invalid handle".
    * Zero initialization of structures containing handles is valid API usage to indicate
    * that no valid handle is provided.
    */
    #define OVRTX_INVALID_HANDLE 0

    /** @} */ // end of ovrtx_handle_types

    /** @defgroup ovrtx_result_types Result and status types
     *  @{
     */

    /**
     * Return status from a synchronous function call.
     */
    typedef enum
    {
        OVRTX_API_SUCCESS = 0, /**< The function completed successfully. */
        OVRTX_API_ERROR = 1, /**< The function generated an error. The associated error message can be queried with 
                                  @ref ovrtx_get_last_error(). */
        OVRTX_API_TIMEOUT = 2, /**< The timeout passed to the function was reached. */
    } ovrtx_api_status_t;

    /**
     * Result from a synchronous function call. The status of the call can be checked with the @ref ovrtx_result_t::status member.
     */
    typedef struct
    {
        ovrtx_api_status_t status; /**< Status of the call. */
    } ovrtx_result_t;

    /**
     * @brief Result from an asynchronous function call.
     *
     * Contains the API call status and the operation index. A non-zero operation index can be used to poll or wait
     * on completion, while OVRTX_INVALID_HANDLE means the operation could not be enqueued.
     *
     * Note that if OVRTX_CONFIG_SYNC_MODE is active any error from the async operation itself will cause status to
     * be OVRTX_API_ERROR and the error is obtainable using ovrtx_get_last_error(). In addition to this a valid
     * operation index is still delivered and can be waited on (even though the operation has already failed).
     */
    typedef struct
    {
        ovrtx_api_status_t status; /**< Status of the API call. */
        ovrtx_op_id_t op_index; /**< Non-zero operation identifier if operation enqueued successfully, OVRTX_INVALID_HANDLE otherwise. */
    } ovrtx_enqueue_result_t;

    typedef enum
    {
        OVRTX_EVENT_PENDING = 0,
        OVRTX_EVENT_COMPLETED = 1,
        OVRTX_EVENT_FAILURE = 2,
    } ovrtx_event_status_t;

    /** @} */ // end of ovrtx_result_types

    /** @defgroup ovrtx_op_wait_types Per-operation wait result types
     *  @{
     */

    /** Result of waiting on an @ref ovrtx_op_id_t with @ref ovrtx_wait_op(). */
    typedef struct
    {
        /** List of operation ids that errored since last wait call. */
        ovrtx_op_id_t* error_op_ids;
        size_t num_error_ops;

        /** The lowest operation id that is still pending, or 0 if all operations are complete. */
        ovrtx_op_id_t lowest_pending_op_id;
    } ovrtx_op_wait_result_t;

    /** @} */ // end of ovrtx_op_wait_types

    /** @defgroup ovrtx_sync_types Stream synchronization types
     *  @{
     */

    /** Represents a timeout duration in nanoseconds. */
    typedef struct
    {
        uint64_t time_out_ns;
    } ovrtx_timeout_t;

    /** Represents a CUDA event to wait for on a particular stream. */
    typedef struct
    {
        uintptr_t stream; /**< Cuda stream to synchronize to. 0 = no synchronization. 1 = default cuda stream, >1 specific stream */
        uintptr_t wait_event; /**< Event to wait on before operation (0 = none) */
    } ovrtx_cuda_sync_t;

    typedef struct
    {
        int32_t device_type; /**< DLDevice device_type */
        int32_t device_id;   /**< DLDevice device_id */
    } ovrtx_device_t;

    typedef struct
    {
        ovrtx_device_t device; /**< device to create the synchronization event on */
    } ovrtx_event_description_t;

    /** @} */ // end of ovrtx_sync_types


    /** @defgroup ovrtx_attribute_types Stage attribute writer types
     *  @{
     */

    typedef enum
    {
        OVRTX_DIRTY_MASK_REPLACE = 0, /**< Replace consumer dirty mask */
        OVRTX_DIRTY_MASK_OR = 1, /**< OR masks together */
        OVRTX_DIRTY_MASK_AND = 2 /**< AND masks together */
    } ovrtx_write_bits_t;

    typedef enum
    {
        OVRTX_DATA_ACCESS_ASYNC = 0, /**< Accesses the inputs asynchronously as part of the stream execution, 
                                        so the input lifetime must remain valid until completion (use ovrtx_wait_op). */
        OVRTX_DATA_ACCESS_SYNC = 1, /**< Copies all input data synchronously, 
                                        so the data is no longer accessed when the call returns. */
    } ovrtx_data_access_t;

    /** A list of paths to prims in the runtime stage. */
    typedef struct ovrtx_prim_list_t
    {
        const ovx_string_t* prim_paths;
        size_t num_paths;
    } ovrtx_prim_list_t;

    typedef struct
    {
        int32_t device_type; /**< device_type from DLDevice */
        int32_t device_id;   /**< device_id from DLDevice */
    } ovrtx_mapping_desc_t;

    /** Describes how to handle attempts to write to paths in the runtime stage that do not exist. */
    typedef enum ovrtx_binding_prim_mode_t
    {
        OVRTX_BINDING_PRIM_MODE_EXISTING_ONLY = 0, /**< Only existing attributes on existingprims are written to, prims that do not exist are ignored */
        OVRTX_BINDING_PRIM_MODE_MUST_EXIST = 1, /**< All attributes and prims must exist to write any data successfully */
        OVRTX_BINDING_PRIM_MODE_CREATE_NEW = 2, /**< New attribute/prim pairs are created when written to */
    } ovrtx_binding_prim_mode_t;

    /** Used to differentiate the intended data layout and usage of a given attribute type. 
     *  
     * For example a transform attribute can be written as different data layouts that are automatically converted into renderer's
     * data layout. This enum is used to differentiate between data layouts written to the same attribute.
     */
    typedef enum ovrtx_attribute_semantic_t
    {
        OVRTX_SEMANTIC_NONE = 0, 
        OVRTX_SEMANTIC_XFORM_MAT4x4 = 1, /**< Transform of a prim expressed as row-major 4x4 matrix of double (kDLFloat, 64, 16) */
        OVRTX_SEMANTIC_XFORM_POS3d_ROT4f_SCALE3f = 2, /**< Transform of a prim expressed as 3xdouble position, 4xfloat rotation and 3xfloat scale (kDLUInt, 8, 56) */
        OVRTX_SEMANTIC_XFORM_POS3d_ROT3x3f = 3, /**< Transform of a prim expressed as 3xdouble position, 3x3float row-major rotation matrix (kDLUInt, 8, 64) */
        OVRTX_SEMANTIC_PATH_STRING = 4, /**< Prim paths expressed as ovx_string_t (kDLUInt, 128, 1). The strings must be valid for the duration of the write_attribute call. Only synchronous data access is supported.*/
        OVRTX_SEMANTIC_TOKEN_STRING = 5,  /**< String token expressed as ovx_string_t (kDLUInt, 128, 1). The strings must be valid for the duration of the write_attribute call. Only synchronous data access is supported.*/
        OVRTX_SEMANTIC_TOKEN_ID = 6, /**< Raw token identifier (kDLUInt, 64, 1). Returned by query for attributes whose Fabric base type is Token. Resolve to a string via the path dictionary. */
        OVRTX_SEMANTIC_PATH_ID = 7, /**< Raw path identifier (kDLUInt, 64, 1). Returned by query for attributes whose Fabric base type is Path. Resolve to a string via the path dictionary. */
        OVRTX_SEMANTIC_TAG = 8, /**< Name-only attribute with no value or storage. Returned by query for Fabric tag attributes. No data should be read. */
    }ovrtx_attribute_semantic_t;

    /*
    * Input attribute element type for OVRTX_SEMANTIC_XFORM_MAT4x4
    */ 
    typedef struct ovrtx_xform_matrix44d_t
    {
        double v[16]; // row-major matrix 4x4 double values
    } ovrtx_xform_matrix44d_t;

    /*
    * Input attribute element type for OVRTX_SEMANTIC_XFORM_POS3d_ROT4f_SCALE3f
    */
    typedef struct ovrtx_xform_pos3d_rot4f_scale3f_t
    {
        double position[3];
        float rot_quat_xyzw[4];
        float scale[3];
        uint32_t padding;
    } ovrtx_xform_pos3d_rot4f_scale3f_t;

    /*
    * Input attribute element type for OVRTX_SEMANTIC_XFORM_POS3d_ROT3x3f
    */
    typedef struct ovrtx_xform_pos3d_rot3x3f_t
    {
        double position[3];
        float rot_matrix[9];  /* 3x3 row-major rotation matrix */
        uint32_t padding;
    } ovrtx_xform_pos3d_rot3x3f_t;

    /** Describes the type of an attribute to be written to the runtime stage. */
    typedef struct  
    {
        DLDataType dtype; /**< Data type */
        bool is_array;  /**< Whether this attribute is an array attribute. Array attributes are variable length per attribute */
        ovrtx_attribute_semantic_t semantic; /**< The interpretation of this array data in a USD stage */
    }ovrtx_attribute_type_t;

    /** Flags giving hints to the renderer about the expected use of a binding. */
    typedef enum ovrtx_binding_flag_t
    {
        OVRTX_BINDING_FLAG_NONE = 0,
        /**< Indicates that the renderer should optimize it's underlying data structures for frequent high volume writes 
             to this binding. The last created binding with this flag will be prioritized. */
        OVRTX_BINDING_FLAG_OPTIMIZE = 1 << 0,  
    }ovrtx_binding_flag_t;

    /** Describes a binding to an attribute on a list of prims so that they can be written to. */
    typedef struct
    {
        ovrtx_prim_list_t prim_list; /**< Explicit list of prims when no handle provided */
        ovx_primpath_list_t prims_list_handle; /**< Handle to a persistent prim list */

        ovx_string_or_token_t attribute_name; /**< Name of the attribute*/
        ovrtx_attribute_type_t attribute_type; /**< Type of the attribute being bound */

        ovrtx_binding_prim_mode_t prim_mode; /**< Mode to determine how prims are handled */
        ovrtx_binding_flag_t flags; /**< Additional flags to control the binding behavior */
    } ovrtx_binding_desc_t;

    /** Represents either an ovrtx_binding_desc_t or an ovrtx_attribute_binding_handle_t allowing either to be passed to 
     *  @ref ovrtx_write_attribute() and @ref ovrtx_map_attribute().
     *  
     * The use of persistent bindings allows for more optimal writes in the renderer when an attribute will be written to 
     * repeatedly.
     *
     * If @ref ovrtx_binding_desc_or_handle_t::binding_handle is non-zero then it will be used, otherwise 
     * @ref ovrtx_binding_desc_or_handle_t::binding_desc will be used.
     */
    typedef struct
    {
        ovrtx_binding_desc_t binding_desc; /**< binding description if no handle provided */
        ovrtx_attribute_binding_handle_t binding_handle; /**< handle to a persistent binding */
    } ovrtx_binding_desc_or_handle_t;


    typedef struct
    {
        /** @name Input buffers as an array of tensors. 
         *
         * For array attributes the array length must 
         * match the number of prims in the attribute binding otherwise it must be 1. The tensor
         * object (not the data) are copied during the call and don't have to persist for longer than
         * the duration of the call. 
         * @{
         */
        DLTensor* tensors; /**< Array of tensors. */
        uint64_t tensor_count; /**< Number of tensors in the array. */
        /** @} */

        /** @name Dirty bit tracking for selective updates. 
          * The dirty bit array is copied and must not persist longer than the call. 
          * @{
          */
        uint8_t* dirty_bits; /**< Bitvector: 1 bit per prim for dirty tracking */
        size_t dirty_bits_size; /**< Size of dirty_bits array: (prim_count + 7) / 8 */
        /** @} */

        /** @name Synchronization
         * @{
         */
        /** Optional synchronization hint used to guard access to the input data inside the renderer */
        ovrtx_cuda_sync_t access_cuda_sync;
        /** Optional synchronization hint used to signal that the input data is no longer accessed by the renderer */
        ovrtx_cuda_sync_t done_cuda_sync;
        /** @} */
    } ovrtx_input_buffer_t;

    /** Optional destination for @ref ovrtx_read_attribute() scalar read data.
     *
     * When the @c tensor pointer is non-null the read writes directly into the
     * caller-provided buffer instead of allocating internal storage.  The tensor
     * must be pre-allocated with shape [prim_count] and a matching element size,
     * including @c DLTensor::dtype.lanes for multi-component attributes.
     * For GPU tensors (@c kDLCUDA) the data is copied via cudaMemcpy.
     * Must be NULL for array attributes (variable-length per prim).
     */
    typedef struct
    {
        DLTensor* tensor;                       /**< Pre-allocated destination (NULL = use internal buffer) */
        ovrtx_cuda_sync_t access_cuda_sync;     /**< Event to wait on before writing to the tensor */
        ovrtx_cuda_sync_t done_cuda_sync;       /**< Event to signal after writing is complete */
    } ovrtx_read_dest_t;

    /** @deprecated Use ovrtx_render_var_output_t tensors[]->dl instead.
     *  Kept for source compatibility with existing consumers. */
    typedef struct
    {
        DLTensor dl; /**< Zero-copy tensor (required) */
        ovrtx_cuda_sync_t cuda_sync; /**< Optional CUDA synchronization hints associated with this buffer */
    } ovrtx_output_buffer_t;

    /** Named render variable param represented as a DLTensor with labels.
     *
     * The DLTensor's dtype encodes the value type (e.g. kDLFloat/32 for float,
     * kDLUInt/64 for uint64_t) and shape encodes scalar vs. array
     * (e.g. {1} for scalar, {N} for array, {4,4} for a matrix).
     * Param values are always CPU-resident: param.device is {kDLCPU, 0}.
     */
    typedef struct
    {
        DLTensor dl; /**< Value tensor (dtype encodes type, shape encodes scalar/array) */
        ovx_string_t name; /**< Entry name (e.g. "frameId", "timestampNs") */
        ovx_string_t doc; /**< Human-readable description */
    } ovrtx_render_var_param_t;

    /** Mapped attribute that can be written to until unmapped. */
    typedef struct
    {
        ovrtx_map_handle_t map_handle; /**< Map handle for unmap operation */
        DLTensor dl; /**< Mapped memory as tensor, valid until unmap */
    } ovrtx_attribute_mapping_t;

    /** @} */ // end of ovrtx_attribute_types

    /** @defgroup ovrtx_query_types Stage query types
     *  @{
     */

    /** Handle to the result of a @ref ovrtx_query_prims() operation. */
    typedef uint64_t ovrtx_query_handle_t;

    typedef enum ovrtx_filter_kind_t
    {
        OVRTX_FILTER_PRIM_TYPE = 0,     /**< Match by USD prim type name (e.g., "Mesh", "SphereLight") */
        OVRTX_FILTER_HAS_ATTRIBUTE = 1, /**< Match by attribute existence (e.g., "points", "normals") */
    } ovrtx_filter_kind_t;

    typedef struct ovrtx_filter_t
    {
        ovrtx_filter_kind_t kind;   /**< What property to match */
        ovx_string_or_token_t name; /**< Prim type name or attribute name */
    } ovrtx_filter_t;

    typedef enum ovrtx_attribute_filter_mode_t
    {
        OVRTX_ATTRIBUTE_FILTER_NONE = 0,     /**< Do not report attributes (lightweight) */
        OVRTX_ATTRIBUTE_FILTER_ALL = 1,      /**< Report every attribute on each group */
        OVRTX_ATTRIBUTE_FILTER_SPECIFIC = 2, /**< Report only the named subset of attributes */
    } ovrtx_attribute_filter_mode_t;

    typedef struct ovrtx_attribute_filter_t
    {
        ovrtx_attribute_filter_mode_t mode; /**< Which attributes to report */
        const ovx_string_or_token_t* attribute_names; /**< Attribute names (used when mode is SPECIFIC) */
        size_t attribute_name_count;                   /**< Number of entries in attribute_names */
    } ovrtx_attribute_filter_t;

    typedef struct ovrtx_query_desc_t
    {
        const ovrtx_filter_t* require_all;  /**< Filters the prim must match (AND) */
        size_t require_all_count;           /**< Number of require_all filters */
        const ovrtx_filter_t* require_any;  /**< Filters the prim must match at least one of (OR) */
        size_t require_any_count;           /**< Number of require_any filters */
        const ovrtx_filter_t* exclude;      /**< Filters the prim must not match (NOT) */
        size_t exclude_count;               /**< Number of exclude filters */

        ovrtx_attribute_filter_t attribute_filter; /**< Which attributes to report per group */
    } ovrtx_query_desc_t;

    /** Describes a single attribute on a group of prims in the query result.
     *  The name is a token that can be resolved to a string via the path dictionary's
     *  get_strings_from_tokens. */
    typedef struct ovrtx_attribute_desc_t
    {
        ovx_token_t name; /**< Attribute name token (resolve via path dictionary) */
        ovrtx_attribute_type_t type; /**< Attribute data type, array-ness, and semantic */
    } ovrtx_attribute_desc_t;

    /** A group of prims sharing the same attribute schema, returned by @ref ovrtx_fetch_query_results().
     *
     * All prims in a group are guaranteed to have the same set of attributes.
     * The @ref ovrtx_query_prim_group_t::prim_list_handle can be plugged directly into
     * @ref ovrtx_binding_desc_t::prims_list_handle for subsequent read or write operations.
     */
    typedef struct ovrtx_query_prim_group_t
    {
        size_t prim_count;                  /**< Number of prims in this group */
        ovx_primpath_list_t prim_list_handle; /**< Handle to the prim paths in this group */

        const ovrtx_attribute_desc_t* attributes; /**< Array of attribute descriptors (NULL if not requested) */
        size_t attribute_count;                    /**< Number of entries in attributes */
    } ovrtx_query_prim_group_t;

    /** Result of a @ref ovrtx_query_prims() operation retrieved via @ref ovrtx_fetch_query_results().
     *
     * Contains one group per matching bucket. All pointers are valid until
     * @ref ovrtx_release_query_results() is called.
     */
    typedef struct ovrtx_query_result_t
    {
        const ovrtx_query_prim_group_t* groups; /**< Array of prim groups */
        size_t group_count;                      /**< Number of groups */
        size_t total_prim_count;                 /**< Sum of prim_count across all groups */
    } ovrtx_query_result_t;

    /** @} */ // end of ovrtx_query_types

    /** @defgroup ovrtx_read_types Stage attribute read types
     *  @{
     */

    /** Handle to the result of a @ref ovrtx_read_attribute() operation.
     *  The same handle is passed to @ref ovrtx_fetch_read_result() and
     *  @ref ovrtx_release_read_result(). */
    typedef uint64_t ovrtx_read_handle_t;

    /** Attribute read output retrieved via @ref ovrtx_fetch_read_result().
     *
     * For scalar attributes @ref ovrtx_read_output_t::buffer_count is 1 and the single tensor
     * has shape [prim_count]. For array attributes @ref ovrtx_read_output_t::buffer_count equals
     * @ref ovrtx_read_output_t::prim_count with one tensor per prim of variable length.
     * Multi-component C attribute tensors encode component count in @c DLTensor::dtype.lanes.
     *
     * When a user-provided destination tensor was passed to @ref ovrtx_read_attribute(),
     * buffer_count is 0 (the data was written directly into the caller's tensor).
     */
    typedef struct ovrtx_read_output_t
    {
        ovrtx_output_buffer_t* buffers;     /**< Array of output tensors (NULL when dest tensor was used) */
        size_t buffer_count;                /**< Number of buffers (1 for scalar, prim_count for array, 0 if dest tensor) */
        size_t prim_count;                  /**< Number of prims that were actually read */
        bool is_array;                      /**< True if the attribute is variable-length per prim (resolved from stage) */
    } ovrtx_read_output_t;

    /** @} */ // end of ovrtx_read_types

    /** @defgroup ovrtx_sensor_types Sensor simulation types
     *  @{
     */

    /** Set of RenderProducts that will be stepped. */
    typedef struct ovrtx_render_product_set_t
    {
        const ovx_string_t* render_products; /**< Array of paths to RenderProduct prims in the stage. */
        size_t num_render_products; /**< Number of paths in the array. */
    } ovrtx_render_product_set_t;

    /** Enum representing the status of an asynchronous operation. */
    typedef enum
    {
        OVRTX_RENDERER_EVENT_PENDING = 0, /**< Operation still in progress */
        OVRTX_RENDERER_EVENT_COMPLETED = 1, /**< Operation completed successfully */
        OVRTX_RENDERER_EVENT_FAILED = 2 /**< Operation failed with error */
    } ovrtx_renderer_event_status_t;

    /** Name an associated handle of a particular RenderVar's output in a RenderProduct output.  */
    typedef struct
    {
        ovx_string_t render_var_name; /**< Name of the associated render var */
        ovrtx_render_var_output_handle_t output_handle; /**< Handle to the rendered output. */
    } ovrtx_render_product_render_var_output_t;

    /** Path-tracing accumulation status for a rendered frame. */
    typedef struct
    {
        uint32_t progression; /**< PT sample accumulation progress since the last reset, increments each time an output is renderered to */
        bool converged;         /**< True when a stop criterion was reached (ex: omni:rtx:pt:samplesPerPixel) */
    } ovrtx_accumulation_status_t;

    /** Output of a particular RenderProduct for a particular frame. 
     *
     * May contain one or more RenderVar outputs in @ref ovrtx_render_product_frame_output_t::output_render_vars which may
     * each be mapped to get access to the output data using @ref ovrtx_map_render_var_output().
     */
    typedef struct
    {
        double frame_start_time; /**< Sensor time (based on step(delta_time) history) when the sensor simulation for this frame started */
        double frame_end_time; /**< Sensor time (based on step(delta_time) history) when the sensor simulation for this frame ended */
        ovrtx_render_product_render_var_output_t* output_render_vars; /**< Pointer to array of render var outputs */
        size_t render_var_count; /**< Number of render var outputs for this render product frame */
        ovrtx_accumulation_status_t accumulation_status; /**< Path-tracing accumulation status for this frame */
    } ovrtx_render_product_frame_output_t;

    /** The output of a particular RenderProduct for a particular @ref ovrtx_step() operation. 
     */
    typedef struct
    {
        ovx_string_t render_product_path; /**< Path of the render product that produced this output */
        float output_frames_produced; /**< Decimal value representing the amount of frames produced */
        ovrtx_render_product_frame_output_t* output_frames; /**< pointer to array of output frames */
        size_t output_frame_count; /**< Number of frames for this render product */
    } ovrtx_render_product_output_t;

    /**
     * The set of RenderProduct outputs for a @ref ovrtx_step() operation.
     * 
     * Depending on the sensor configuration, each @ref ovrtx_step() may produce zero or more frames for each RenderProduct
     * in the @ref ovrtx_render_product_set_t passed to @ref ovrtx_step().
     */
    typedef struct
    {
        ovrtx_event_status_t status; /**< Current operation status */
        ovx_string_t error_message; /**< Error description if failed, NULL if succeeded */
        double simulation_start_time; /**< Sensor time (based on step(delta_time) history) when the step which produced this output started */
        double simulation_end_time; /**< Sensor time (based on step(delta_time) history) when the step which produced this output ended */
        ovrtx_render_product_output_t* outputs; /**< Array of outputs returned */
        size_t output_count; /**< Number of outputs in the array */
        double start_time; /**< Sensor time (based on step(delta_time) history) when the sensor simulation for this step started */
        double end_time; /**< Sensor time (based on step(delta_time) history) when the sensor simulation for this step ended */
    } ovrtx_render_product_set_outputs_t;

#define OVRTX_RENDER_VAR_PICK_HIT "ovrtx_pick_hit"

    /** @defgroup ovrtx_pick_types Pick query and pick-hit buffer layout
     *  @{
     */

#define OVRTX_PICK_FLAG_GIZMO (1u << 0)
#define OVRTX_PICK_FLAG_INCLUDE_TRACKED_INFO (1u << 1)

    /** Pick rectangle in normalized RenderProduct coordinates. Values use [0, 1] top-left-origin NDC:
     *  x increases left-to-right and y increases top-to-bottom. The rectangle uses the same convention as
     *  the old pixel API: @c right_ndc and @c bottom_ndc mark the edge just past the last included pixel.
     *  For example, pixel (x, y) on a width x height RenderProduct is
     *  [x / width, y / height, (x + 1) / width, (y + 1) / height]; the full RenderProduct is [0, 0, 1, 1].
     *  Out-of-bounds values are rejected; boundary values may be clamped to the valid range to account for
     *  floating-point roundoff. */
    typedef struct ovrtx_pick_query_desc_t
    {
        ovx_string_t render_product_path;
        float left_ndc;
        float top_ndc;
        float right_ndc;
        float bottom_ndc;
        uint32_t flags;
    } ovrtx_pick_query_desc_t;

    /**
     * Schema-identity / schema-version handshake for the multi-tensor render variable
     * @ref OVRTX_RENDER_VAR_PICK_HIT. The mapped output exposes both as named ``uint32``
     * params (``magic`` and ``version``); consumers must validate
     * ``magic == OVRTX_PICK_HIT_MAGIC`` and ``version == OVRTX_PICK_HIT_VERSION``
     * before reading the v1 tensor schema. The number of valid records is published as
     * the ``hitCount`` param. Hits contain @ref ovx_primpath_t handles only; resolve to
     * UTF-8 with the renderer path dictionary if needed.
     */
#define OVRTX_PICK_HIT_MAGIC 0x56505448u  /**< 'VPTH' */
#define OVRTX_PICK_HIT_VERSION 1u

    /** @} */

    /** @defgroup ovrtx_selection_style_types Selection-outline / fill styling
     *  @{
     *
     * The selection outline pass supports two layers of styling:
     *
     * 1. Per-group state (outline color, fill color) — set at runtime via
     *    @ref ovrtx_set_selection_group_styles. The slot is keyed by the
     *    per-prim group id passed to @ref ovrtx_set_selection_outline_group.
     *
     * 2. Global state (outline thickness, fill mode) — set at renderer creation
     *    via @ref OVRTX_CONFIG_SELECTION_OUTLINE_WIDTH and
     *    @ref OVRTX_CONFIG_SELECTION_FILL_MODE. Changing these at runtime
     *    requires destroying and recreating the renderer.
     *
     * Outline dashing/stippling is **not supported** by the underlying RTX
     * outline pipeline and is intentionally not exposed here.
     */

    /** Selection-outline interior (fill) mode. Mirrors @c OutlineMode in the underlying RTX shader.
     *  Set globally via @ref OVRTX_CONFIG_SELECTION_FILL_MODE at renderer creation. */
    typedef enum ovrtx_selection_fill_mode_t
    {
        /** No interior fill (outline edge only). */
        OVRTX_SELECTION_FILL_MODE_EDGE_ONLY = 0,
        /** Global intersection color shared by all groups (kGlobalColorForInterior). */
        OVRTX_SELECTION_FILL_MODE_GLOBAL = 1,
        /** Use each group's outline color as its interior fill (kOutlineColorForInterior). */
        OVRTX_SELECTION_FILL_MODE_GROUP_OUTLINE_COLOR = 2,
        /** Use each group's dedicated fill/shade color as its interior fill (kShadeColorForInterior). */
        OVRTX_SELECTION_FILL_MODE_GROUP_FILL_COLOR = 3,
    } ovrtx_selection_fill_mode_t;

    /** Motion BVH (ray-traced motion) mode for sensor and motion-sensitive pipelines.
     *  Set via @ref OVRTX_CONFIG_MOTION_BVH at renderer creation. */
    typedef enum ovrtx_motion_bvh_t
    {
        /** Motion BVH disabled (default when the config entry is omitted). */
        OVRTX_MOTION_BVH_DISABLE = 0,
        /** Motion BVH enabled from renderer creation. */
        OVRTX_MOTION_BVH_ENABLE = 1,
        /** Motion BVH enabled at runtime when a non-visual sensor or motion-sensitive camera is rendered. */
        OVRTX_MOTION_BVH_AUTO = 2,
    } ovrtx_motion_bvh_t;

    /** Visual styling for one selection-outline group. RGBA components in [0..1]. */
    typedef struct ovrtx_selection_group_style_t
    {
        /** Outline edge color (matches @c /persistent/app/viewport/outline/color). */
        float outline_color[4];
        /** Interior fill color (matches @c /persistent/app/viewport/outline/shadeColor;
         *  used when @ref OVRTX_CONFIG_SELECTION_FILL_MODE selects per-group fill modes). */
        float fill_color[4];
    } ovrtx_selection_group_style_t;

    /** @} */ // end of ovrtx_selection_style_types


    /** Specifies which device (CPU or GPU) should be used to map a given output. */
    typedef enum
    {
        /**< Provide the data in whatever format is most efficient. */
        OVRTX_MAP_DEVICE_TYPE_DEFAULT = 0,
        /**< Read back output from GPU to CPU. This will incur synchronization and copy. */
        OVRTX_MAP_DEVICE_TYPE_CPU = 1,
        /**< Raw CUDA device memory as dltensor. This will likely incur an additional copy when used for image outputs. */
        OVRTX_MAP_DEVICE_TYPE_CUDA = 2, 
        /**< CUDA array represented in dltensor as kDLCUDA / kDLOpaqueHandle. This saves a copy for image outputs, but is not supported for other outputs. */
        OVRTX_MAP_DEVICE_TYPE_CUDA_ARRAY = 3,
    } ovrtx_map_device_type_t;

    /** Description of the device and synchronization for mapping an output to be passed to @ref ovrtx_map_render_var_output().
     *
     *  The device_type applies to tensors only. Param entries are always mapped to CPU
     *  regardless of this setting.
     */
    typedef struct
    {
        ovrtx_map_device_type_t device_type; /**< Requested device for tensors (params are always CPU) */
        uintptr_t sync_stream; /**< CUDA stream to synchronize production of the output with. 
                                Providing a stream here means that after the map call returns the output
                                data can immediately be accessed on a cuda stream that is synchronized to the provided stream.
                                 0 = no synchronization. 1 = default cuda stream, >1 specific stream */
        
    } ovrtx_map_output_description_t;


    /** One tensor slot in a mapped render variable output (DLPack view plus labels).
     *
     *  Lifetime: pointers are valid from ovrtx_map_render_var_output() until ovrtx_unmap_render_var_output().
     */
    typedef struct
    {
        const DLTensor* dl; /**< DLPack tensor (device per map request; may be CUDA array as opaque handle) */
        const ovx_string_t* name; /**< Tensor name (e.g. channel or slice); never NULL when num_tensors > 0 */
        const ovx_string_t* doc; /**< Human-readable tensor description; may point to an empty string */
    } ovrtx_render_var_tensor_t;

    /** The output of a particular RenderVar for a particular RenderProduct on a particular frame.
     *
     *  Contains zero or more named tensor slots (@ref ovrtx_render_var_tensor_t) and zero or more named param entries.
     *  Tensor data may reside on CPU or CUDA depending on the map request.
     *  Params are always CPU-resident.
     *
     *  Lifetime: valid from ovrtx_map_render_var_output() until ovrtx_unmap_render_var_output().
     *
     *  @note ABI break from pre-0.3: the ovrtx_output_buffer_t buffer field has been removed.
     *        Consumers must migrate to the tensors[]/params[] layout.
     */
    typedef struct
    {
        ovrtx_event_status_t status; /**< Current operation status */
        ovx_string_t error_message; /**< Error description if failed, NULL if succeeded */
        ovrtx_render_var_output_map_handle_t map_handle; /**< Handle to use for unmap */
        ovrtx_cuda_sync_t cuda_sync; /**< Single sync covering all tensors */

        ovx_string_t name; /**< Render variable name (e.g., "PointCloud", "HdrColor") */
        ovx_string_t type; /**< Semantic type identifier */
        ovx_string_t doc; /**< Human-readable description */
        int version; /**< Output schema version */

        size_t num_tensors; /**< Number of tensors in this output (may be 0) */
        const ovrtx_render_var_tensor_t* tensors; /**< Array of num_tensors tensor descriptors */

        size_t num_params; /**< Number of param entries in this output (may be 0) */
        const ovrtx_render_var_param_t* params; /**< Array of num_params entries (always CPU) */
    } ovrtx_render_var_output_t;

    /** @} */ // end of ovrtx_sensor_types

    /** @defgroup ovrtx_op_status_types Operation status types
     *  @{
     */

    /**
     * Named resource counter for tracking progress of specific resource types.
     *
     * Counter semantics:
     * - name: Identifies the resource type (e.g., "shaders", "textures", "materials")
     * - current: Number of items processed so far
     * - total: Total items to process, or 0 if the total is not yet known
     */
    typedef struct ovrtx_op_counter_t
    {
        ovx_string_t name;     /**< Counter name (e.g., "shaders", "textures") */
        uint64_t current;      /**< Number of items processed so far */
        uint64_t total;        /**< Total number of items to process (0 if unknown) */
    } ovrtx_op_counter_t;

    /**
     * Operation status information for long-running operations.
     *
     * Progress semantics:
     * - Range [0.0, 1.0] where 1.0 = complete
     * - Negative value indicates indeterminate progress
     */
    typedef struct ovrtx_op_status_t
    {
        ovrtx_op_id_t op_id;            /**< Operation ID this status refers to */
        ovrtx_event_status_t state;     /**< PENDING, COMPLETED, or FAILURE */

        /** Progress as fraction [0.0, 1.0], or negative if indeterminate */
        double progress;

        /** Named resource counters (variable count, operation-dependent) */
        ovrtx_op_counter_t* counters;
        size_t counter_count;
    } ovrtx_op_status_t;

    /** @} */ // end of ovrtx_op_status_types

    /** @defgroup ovrtx_log_types Logging types
     *  @{
     */

    /**
     * Log severity levels for operation messages.
     */
    typedef enum ovrtx_log_severity_t
    {
        OVRTX_LOG_INFO = -1,     /**< Informational message */
        OVRTX_LOG_WARNING = 0,  /**< Warning (operation continues) */
        OVRTX_LOG_ERROR = 1,    /**< Error (operation may have failed) */
        OVRTX_LOG_FATAL = 2,    /**< Fatal error (operation may have failed) */
    } ovrtx_log_severity_t;

    /**
     * Callback function type for receiving log messages.
     *
     * The callback is process-global (see ovrtx_set_log_callback) and may be
     * invoked from any thread. The implementation serializes invocations so
     * the callback body itself does not need its own mutex, but it must still
     * be thread-safe with respect to whatever data it touches outside.
     *
     * The message string is only valid for the duration of the callback.
     * If the message needs to be retained, copy it before returning.
     *
     * @param severity Severity level of the message
     * @param timestamp Wall-clock time in seconds since the epoch
     * @param message Log message text (valid only during callback)
     * @param user_data User-provided context from ovrtx_set_log_callback
     */
    typedef void (*ovrtx_log_callback_t)(ovrtx_log_severity_t severity,
                                         double timestamp,
                                         ovx_string_t message,
                                         void* user_data);

    /** @} */ // end of ovrtx_log_types

    /** @defgroup ovrtx_config_types Configuration types
     *  @{
     */

    /** Texture streaming mode.
     *  Set via @ref OVRTX_CONFIG_TEXTURE_STREAMING_MODE at renderer creation.
     *  The setting is process-global and applies to all active renderer instances. */
    typedef enum ovrtx_texture_streaming_mode_t
    {
        /** Disable texture streaming. Textures are created as regular resources. */
        OVRTX_TEXTURE_STREAMING_DISABLE = 0,
        /** Enable texture streaming and process texture feedback synchronously. */
        OVRTX_TEXTURE_STREAMING_SYNCHRONOUS = 1,
        /** Enable texture streaming and process texture feedback asynchronously (default). */
        OVRTX_TEXTURE_STREAMING_ASYNCHRONOUS = 2,
    } ovrtx_texture_streaming_mode_t;

    /** Key type tag for @ref ovrtx_config_entry_t; selects which key and value union members are valid. */
    typedef enum ovrtx_config_key_type_t
    {
        OVRTX_CONFIG_KEY_TYPE_BOOL,
        OVRTX_CONFIG_KEY_TYPE_INT64,
        OVRTX_CONFIG_KEY_TYPE_UINT64,
        OVRTX_CONFIG_KEY_TYPE_DOUBLE,
        OVRTX_CONFIG_KEY_TYPE_STRING,
        OVRTX_CONFIG_KEY_TYPE_BLOB,
        OVRTX_CONFIG_KEY_TYPE_COUNT
    } ovrtx_config_key_type_t;

    /** Boolean config keys. Value type: bool. Used at init and create_renderer (must match). */
    typedef enum ovrtx_config_bool_t
    {
        /** If true, stream operations execute synchronously (enqueue blocks). Init and create_renderer. */
        OVRTX_CONFIG_SYNC_MODE,
        /** If true, enables internal profiling. Init and create_renderer. */
        OVRTX_CONFIG_ENABLE_PROFILING,
        /** If true, uses GPU world transform propagation during rendering. Create_renderer. */
        OVRTX_CONFIG_READ_GPU_TRANSFORMS,
        /** If true, keeps the renderer system alive after all instances are destroyed (for reuse). Create_renderer. */
        OVRTX_CONFIG_KEEP_SYSTEM_ALIVE,
        /** If true, uses Vulkan; if false, uses DX12 (Windows only). Create_renderer.
         *  When not specified, defaults to platform default (DX12 on Windows, Vulkan on Linux). */
        OVRTX_CONFIG_USE_VULKAN,
        /** If true, enables the selection outline postprocessing pass. Create_renderer.
         *  When not specified, defaults to false. */
        OVRTX_CONFIG_SELECTION_OUTLINE_ENABLED,
        /** API key for the geometry streaming opt-in flag. Create_renderer. */
        OVRTX_CONFIG_ENABLE_GEOMETRY_STREAMING,
        /** API key for the geometry streaming LOD opt-in flag. Create_renderer. */
        OVRTX_CONFIG_ENABLE_GEOMETRY_STREAMING_LOD,
        /** If false, disables Sensor Processing Graphs (SPG), default: enabled.
         * This is a global setting, applying to all active renderer instances. */
        OVRTX_CONFIG_ENABLE_SPG,
        /** If true, suppresses runtime deprecation warnings emitted by legacy OVRTX APIs.
         * Compile-time deprecation diagnostics are unaffected. Create_renderer. */
        OVRTX_CONFIG_SUPPRESS_DEPRECATION_WARNINGS,
        OVRTX_CONFIG_BOOL_COUNT
    } ovrtx_config_bool_t;

    /** String config keys. Value type: ovx_string_t. Used at init and create_renderer (must match). */
    typedef enum ovrtx_config_string_t
    {
        /** Path to OVRTX binary package root. Loader uses for dylib and resources.
         * Init and create_renderer (must match). */
        OVRTX_CONFIG_BINARY_PACKAGE_ROOT_PATH,
        /** Log file path for carb logging. Applied when first renderer is created. Init and create_renderer. */
        OVRTX_CONFIG_LOG_FILE_PATH,
        /** Log level for carb logging (e.g. "verbose", "info", "warn", "error"). Init and create_renderer. */
        OVRTX_CONFIG_LOG_LEVEL,
        /** Comma-separated CUDA device indices to use (e.g. "0,1,2"). Create_renderer. */
        OVRTX_CONFIG_ACTIVE_CUDA_GPUS,
        /** Protocol-prefixed datastore cache configuration used by UJITSO.
         * Supported values: "grpcdns://host:port", "grpcdns_notls://host:port", and "local://path".
         * System-level; init and create_renderer values must match when both are specified. */
        OVRTX_CONFIG_DATASTORE_CACHE,
        OVRTX_CONFIG_STRING_COUNT
    } ovrtx_config_string_t;

    /** Int64 config keys. Value type: int64_t. Used at create_renderer. */
    typedef enum ovrtx_config_int64_t
    {
        /** Selection outline width in pixels. Valid range 0..15 (15 is the underlying RTX outline pipeline cap).
         *  Init-time only; changing requires renderer recreation. Default: 2 (set by the underlying renderer). */
        OVRTX_CONFIG_SELECTION_OUTLINE_WIDTH,
        /** Selection-outline interior (fill) mode. Value type: @ref ovrtx_selection_fill_mode_t.
         *  Out-of-range values are clamped by the renderer.
         *  Init-time only; changing requires renderer recreation.
         *  Default: @ref OVRTX_SELECTION_FILL_MODE_GLOBAL. */
        OVRTX_CONFIG_SELECTION_FILL_MODE,
        /** Motion BVH mode. Value type: @ref ovrtx_motion_bvh_t.
         *  Init-time only; changing requires renderer recreation.
         *  When not specified, defaults to @ref OVRTX_MOTION_BVH_DISABLE. */
        OVRTX_CONFIG_MOTION_BVH,
        /** DomeLight baking resolution (texels) used when an MDL material drives a DomeLight's image
         *  source. Applies renderer-wide to all dome lights. Valid range 1..8192; out-of-range values
         *  are clamped by the renderer. When provided it takes precedence; when omitted the renderer
         *  leaves the setting untouched (default 4096 on a fresh renderer).
         *  Init-time only; changing requires renderer recreation. */
        OVRTX_CONFIG_DOME_BAKING_RESOLUTION = 4,
        /** Texture streaming mode. Value type: @ref ovrtx_texture_streaming_mode_t.
         *  Invalid values cause renderer creation to fail. When omitted, defaults to
         *  @ref OVRTX_TEXTURE_STREAMING_ASYNCHRONOUS.
         *  Process-global; changing affects all active renderer instances. */
        OVRTX_CONFIG_TEXTURE_STREAMING_MODE = 5,
        OVRTX_CONFIG_INT64_COUNT = 6
    } ovrtx_config_int64_t;

    /** Uint64 config keys (reserved for future use). Value type: uint64_t. */
    typedef enum ovrtx_config_uint64_t
    {
        OVRTX_CONFIG_UINT64_COUNT
    } ovrtx_config_uint64_t;

    /** Double config keys (reserved for future use). Value type: double. */
    typedef enum ovrtx_config_double_t
    {
        OVRTX_CONFIG_DOUBLE_COUNT
    } ovrtx_config_double_t;

    /** Blob config keys (reserved for future use). Value type: ptr + size. */
    typedef enum ovrtx_config_blob_t
    {
        OVRTX_CONFIG_BLOB_COUNT
    } ovrtx_config_blob_t;

    /** A config entry. key_type selects which member of key and value is valid. */
    typedef struct
    {
        ovrtx_config_key_type_t key_type;
        union
        {
            ovrtx_config_bool_t bool_key;
            ovrtx_config_int64_t int64_key;
            ovrtx_config_uint64_t uint64_key;
            ovrtx_config_double_t double_key;
            ovrtx_config_string_t string_key;
            ovrtx_config_blob_t blob_key;
        } key;
        union
        {
            bool bool_value;
            int64_t int_value;
            uint64_t uint_value;
            double double_value;
            ovx_string_t string_value;
            struct
            {
                const void* data;
                size_t size;
            } blob_value;
        } value;
    } ovrtx_config_entry_t;

    /** Config passed to @ref ovrtx_initialize() and @ref ovrtx_create_renderer().
     * Non-null required; empty (entry_count 0) means defaults. */
    typedef struct
    {
        const ovrtx_config_entry_t* entries;
        size_t entry_count;
    } ovrtx_config_t;

    /** @} */ // end of ovrtx_config_types

    /** @ingroup ovrtx_sync_types */
    /** @ref ovrtx_timeout_t constant for infinity (i.e. block indefinitely) */
    static const ovrtx_timeout_t ovrtx_timeout_infinite = { (size_t)-1 }; /* .time_out_ns = would require C++20 */

#ifdef __cplusplus
}
#endif

#endif /* OVRTX_TYPES_H */
