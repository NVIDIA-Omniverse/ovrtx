// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

#include <ovrtx/ovrtx_types.h>
#include <ovstage/ovstage_api/ovstage_api_types.h>
#include <ovx/path_dictionary/path_dictionary.h>

#ifdef __cplusplus
extern "C"
{
#endif

    /**
     * @defgroup ovrtx_data_provider Data providers
     * @brief Renderer-independent immutable asset pins, byte reads and structured accessors.
     *
     * The provider separates establishing resource identity, performing payload
     * I/O, and accessing the results. Conceptually, successful completions follow
     * this sequence (the provider operations are asynchronous):
     * @code
     * URI      -> pin_async()           -> resource, kind, size, revision, optional hash
     * resource -> read_async()          -> bytes
     * resource -> open_accessor_async(offset, size) -> independent accessor
     * accessor -> get_*()               -> prims, attributes, scalar values
     * accessor -> acquire_array_*()     -> leased immutable arrays
     * @endcode
     *
     * Pinning is analogous to name resolution and stat: it establishes identity
     * and metadata without reading or prefetching payload data. It does not
     * establish that a later payload read will succeed. Size may be unknown;
     * revision and optional content hash follow the identity rules below.
     *
     * read_async() for byte resources and open_accessor_async() for structured
     * resources are the payload I/O operations: they may have variable latency
     * and fail. Opening loads or prepares the selected resource before returning
     * an accessor. The optional map_async() is another payload-access operation
     * for byte resources and may likewise perform I/O.
     *
     * An accessor only traverses and accesses the immutable data already prepared
     * by opening. Its get_*() and acquire_array_*() methods are synchronous and
     * perform no additional I/O; acquiring an array borrows existing storage.
     * Accessor status codes still report invalid requests or unavailable data.
     * Release array leases before close_accessor(), and retain the resource pin
     * until all dependent reads, accessors and byte mappings have finished.
     *
     * Map every independent payload I/O operation in a streaming pipeline onto
     * this sequence: establish or reuse a pinned resource identity, explicitly
     * read/open that resource, then access the completed result. Further chunks
     * or dependencies require their own explicit provider I/O operations; never
     * hide a subsequent fetch inside accessor traversal. Opening one resource
     * does not require loading the entire dataset. Reuse one pin for multiple
     * independent open_accessor_async(offset, size) operations selecting different
     * portions of that resource. The provider and consumer agree on the meaning
     * of offset and size; they need not represent byte positions or byte counts.
     * Each successful open produces an independently owned accessor, with its own
     * array leases and close, over the selected prepared data. Closing one accessor
     * must not invalidate another accessor from the same pin.
     *
     * Register after ovrtx_initialize() and before submitting scene references.
     * Root identifiers are absolute paths or URIs. Matching explicit URI schemes (ASCII case-insensitive) precede empty
     * catch-all routes. Within each group, descending priority applies and ties
     * retain registration order. Only root NOT_HANDLED advances the chain.
     * Dependencies of an acquired pin go directly to that pin's provider.
     *
     * Provider callbacks are thread-safe and nonblocking. ACCEPTED owes exactly one
     * completion, possibly inline. RETRY and REJECTED owe none. The runtime retains
     * the request, reference, base pin and read destination through completion and
     * return of submission/cancellation calls. Cancellation is best effort and does
     * not release those objects early. Never throw across a callback boundary.
     *
     * Each asynchronous operation receives a completion function (done) and its
     * caller-owned user_data pointer, following the ovrtx/ovstage callback convention.
     * This is per-operation callback context supplied by the runtime/caller, separate
     * from the provider's typed context and the pinned resource handle. To complete,
     * pass it unchanged as the first argument: done(user_data, status, result, error).
     * The provider must not interpret, dereference or free user_data.
     *
     * For ACCEPTED, retain done and user_data until the one completion, including
     * cancellation. The caller keeps callback state alive until completion; done may
     * release it, so the provider must not use user_data after invoking done. For
     * RETRY or REJECTED, do not invoke done or retain either argument after returning.
     *
     * Pinning selects metadata only; it must not read or prefetch payload bytes.
     * A successful pin fixes immutable content and dependency context until unpin.
     * For one identifier, equal nonempty revision IDs mean equal data; different
     * IDs may still describe equal data. Empty revisions cannot deduplicate pins.
     * An optional content hash is algorithm-tagged SHA-256, independent of revision.
     * Consumers own persistent-cache validation and may compute content hashes;
     * local-file resolution uses modification time and size to validate deferred
     * reads, reporting STALE after a detected change. Zero length and unknown
     * length are distinct.
     *
     * Registration copies the descriptor strings and provider instance. The application
     * owns the immutable vtable, typed context and callback code until successful
     * removal or completed shutdown. The descriptor and instance records themselves
     * need remain valid only through the registration call. Length-delimited descriptor/resource strings need not be NUL-terminated;
     * a nonempty string requires a valid pointer and must not contain embedded NUL. An empty
     * string may use a NULL pointer. Error strings are diagnostic and callback-scoped.
     * Initialize every struct_size field to sizeof its record and each ABI field to the
     * corresponding version macro. The runtime requires at least the current record size
     * and an exact ABI version match where present; it ignores trailing extension bytes.
     * Credential rotation is provider-internal and does not require re-registration;
     * it must preserve the registered cache/authorization domain and existing pins.
     * BUSY removal is atomic and leaves registration unchanged. Retire consumers
     * before removing providers; do not call shutdown from a provider callback.
     * A provider that never completes ACCEPTED work can prevent safe shutdown.
     * @{
     */
/** Exact accessor layout version required by the runtime; independent of the provider ABI. */
#define OVRTX_DATA_ACCESSOR_ABI_VERSION 4u
/** Every opened accessor supplies the acquire_array_cpu/release_array_cpu pair. */
#define OVRTX_DATA_ACCESSOR_CAP_CPU_ARRAYS UINT64_C(1)
/** Every opened accessor supplies the acquire_array_gpu/release_array_gpu pair. */
#define OVRTX_DATA_ACCESSOR_CAP_GPU_ARRAYS UINT64_C(2)

    /** Shared status domain for provider operations, accessor methods and close. */
    typedef enum ovrtx_data_status_t
    {
        OVRTX_DATA_OK = 0, /**< Operation succeeded; consume the documented outputs. */
        OVRTX_DATA_NOT_HANDLED = 1, /**< Provider declines a root pin; only root resolution may try the next provider. */
        OVRTX_DATA_NOT_FOUND = 2, /**< Requested resource, prim or attribute does not exist. */
        OVRTX_DATA_UNSUPPORTED = 3, /**< Operation, representation, schema or required tracking is unavailable. */
        OVRTX_DATA_INVALID_ARGUMENT = 4, /**< An argument or returned record violates the operation contract. */
        OVRTX_DATA_ACCESS_DENIED = 5, /**< Provider authorization does not permit the requested access. */
        OVRTX_DATA_IO_ERROR = 6, /**< Payload or metadata I/O failed, including an invalid short read of known-size data. */
        OVRTX_DATA_STALE = 7, /**< The selected immutable revision can no longer be served; do not substitute newer data. */
        OVRTX_DATA_CANCELLED = 8, /**< An accepted operation completed after honoring cancellation. */
        OVRTX_DATA_BUSY = 9, /**< A synchronous removal/close cannot proceed while dependents remain; no ownership changes. */
        OVRTX_DATA_INVALID_STATE = 10, /**< The service or operation is unavailable in its current lifecycle state. */
        OVRTX_DATA_INVALID_HANDLE = 11, /**< An accessor or array lease handle is unknown or already released. */
        OVRTX_DATA_OUT_OF_RANGE = 12 /**< A selector is outside its domain, or a scalar sizing query needs more storage. */
    } ovrtx_data_status_t;

    /** Provider-owned, non-NULL prepared state, valid until successful close_accessor(). */
    typedef struct ovrtx_data_accessor_context_t ovrtx_data_accessor_context_t;
    /** Accessor-local array borrow identity. Zero is valid. Each live acquisition
     * has its own release obligation on its accessor. Copying does not acquire
     * a borrow, prove liveness, or identify the owning accessor. */
    typedef struct ovrtx_data_array_lease_id_t
    {
        uint64_t raw_id;
    } ovrtx_data_array_lease_id_t;

    /** Value-copy prim metadata; no independent ownership or lease. */
    typedef struct ovrtx_data_prim_info_t
    {
        ovx_token_t type_name; /**< Dictionary-owned type-name token, or zero when no type is supplied. */
    } ovrtx_data_prim_info_t;
    /** Prepared attribute layout shared by metadata, scalar reads and array leases. */
    typedef struct ovrtx_data_attribute_info_t
    {
        /** Packed element type; this API currently supports only:
         * - OVRTX_SEMANTIC_NONE: kDLUInt with 8/32/64 bits, kDLInt with 64 bits,
         *   or kDLFloat with 32/64 bits. dtype.lanes > 0 is the packed component count.
         * - OVRTX_SEMANTIC_TOKEN_ID: {kDLUInt, 64, 1}, storing dictionary-owned ovx_token_t.
         * Both forms support scalars and arrays. is_array distinguishes arrays
         * (including one-element arrays) from scalars. No other dtype/semantic
         * combinations are supported yet, even if ovrtx_attribute_type_t describes them.
         * Providers return UNSUPPORTED for unsupported attributes, without coercion. */
        ovrtx_attribute_type_t type;
        uint64_t count; /**< Logical element count; one for a scalar attribute. */
    } ovrtx_data_attribute_info_t;

    /** Borrowed CPU array and its release obligation; the record itself may be copied. */
    typedef struct ovrtx_data_cpu_array_t
    {
        ovrtx_data_array_lease_id_t lease; /**< Release exactly once using the matching accessor and memory kind. */
        const void* data; /**< Immutable bytes through lease release; non-NULL unless byte_size is zero. */
        uint64_t byte_size; /**< count * dtype.lanes * (dtype.bits / 8); tightly packed. */
        ovrtx_data_attribute_info_t layout; /**< Matches get_attribute_info; is_array is true. */
    } ovrtx_data_cpu_array_t;

    /** Caller-owned GPU selection descriptor, borrowed only during acquisition. */
    typedef struct ovrtx_data_gpu_access_desc_t
    {
        DLDevice device; /**< Requested CUDA device; acquisition does not migrate data. */
    } ovrtx_data_gpu_access_desc_t;
    /** Borrowed CUDA array, readiness information and explicit GPU lease. */
    typedef struct ovrtx_data_gpu_array_t
    {
        ovrtx_data_array_lease_id_t lease; /**< Release exactly once using the matching accessor and memory kind. */
        /** Immutable CUDA tensor on the requested device. dtype matches get_attribute_info;
         * ndim = 1, shape[0] = count, strides is NULL or {1}, and byte_offset locates
         * the first element. Tensor data, shape and strides remain valid through release. */
        DLTensor tensor;
        /** Producer readiness, using the OVStage handoff contract. Before accessing
         * tensor data, synchronize each nonzero field on tensor.device: stream 1
         * denotes the default stream, >1 a cudaStream_t to drain; wait_event is a
         * cudaEvent_t to wait on. Both zero means the data is already ready.
         * Provider-owned synchronization objects remain valid through lease release. */
        ovstage_cuda_sync_t cuda_sync;
    } ovrtx_data_gpu_array_t;

    /**
     * Access and traverse immutable data prepared by open_accessor_async().
     * Set struct_size to sizeof(ovrtx_data_accessor_vtable_t) and abi_version to
     * OVRTX_DATA_ACCESSOR_ABI_VERSION. Keep the table immutable until accessor close.
     * All methods are synchronous, thread-safe, and perform no I/O or hidden transfers.
     * All get_* callbacks are required; only capability-controlled array pairs may be NULL.
     * A live context is a precondition; NULL/dangling contexts cannot be safely validated.
     * Paths and tokens must originate from the dictionary supplied when opening.
     * The caller owns output records/buffers; providers do not retain their addresses.
     * Unless a method explicitly documents a sizing result, consume outputs only on OK.
     * Errors acquire no lease and transfer no ownership. Do not race successful close
     * against any call, or release against reads using the same lease. Token/path values
     * are borrowed dictionary handles, not independently owned strings. Scalar bytes are
     * copied; arrays are immutable borrows protected by explicit per-accessor leases.
     */
    typedef struct ovrtx_data_accessor_vtable_t
    {
        uint32_t struct_size; /**< Set to sizeof(ovrtx_data_accessor_vtable_t); must cover this ABI. */
        uint32_t abi_version; /**< Must equal OVRTX_DATA_ACCESSOR_ABI_VERSION. */
        /**
         * Copy a page of root prim paths from the prepared selection.
         *
         * The total and enumeration order are stable for this immutable accessor; no lexical
         * ordering is required. NULL storage is a count-only query and ignores capacity.
         * Otherwise copy exactly min(capacity, total - start_index) handles when start_index
         * is below total. At or beyond total (including UINT64_MAX), or with zero capacity,
         * succeed without writing storage. A short page is normal success, not OUT_OF_RANGE.
         * Always write the full sequence length to out_total on success, independent of
         * start_index and capacity. Entries beyond the written prefix remain untouched.
         * Performs no I/O or hidden transfers and acquires no ownership or leases. The caller
         * owns storage; copied handles remain dictionary-owned. Retain the dictionary while using them.
         * An empty selection succeeds with total zero.
         *
         * @param context Live, non-NULL accessor context returned by open_accessor_async(). Borrowed for this call.
         * @param start_index Zero-based start in the enumeration; indexes past the end are allowed.
         * @param[out] storage Optional caller-owned array of capacity prim-path handles; never retained.
         * @param capacity Storage capacity in elements, not bytes; ignored if storage is NULL.
         * @param[out] out_total Non-NULL destination for the full sequence length; consume only on success.
         * @return
         * - **OVRTX_DATA_OK** if out_total and the requested page were written, including empty pages.
         * - **OVRTX_DATA_INVALID_ARGUMENT** if out_total is NULL.
         */
        ovrtx_data_status_t (*get_roots)(ovrtx_data_accessor_context_t* context,
                                           uint64_t start_index,
                                           ovx_primpath_t* storage,
                                           uint64_t capacity,
                                           uint64_t* out_total);
        /**
         * Copy a page of immediate child prim paths from the prepared selection.
         *
         * The total and enumeration order are stable for this immutable accessor; no lexical
         * ordering is required. NULL storage is a count-only query and ignores capacity.
         * Otherwise copy exactly min(capacity, total - start_index) handles when start_index
         * is below total. At or beyond total (including UINT64_MAX), or with zero capacity,
         * succeed without writing storage. A short page is normal success, not OUT_OF_RANGE.
         * Always write the full sequence length to out_total on success, independent of
         * start_index and capacity. Entries beyond the written prefix remain untouched.
         * Performs no I/O or hidden transfers and acquires no ownership or leases. The caller
         * owns storage; copied handles remain dictionary-owned. Retain the dictionary while using them.
         * Excludes deeper descendants and children outside the prepared selection. A present
         * leaf succeeds with total zero, distinct from an absent prim.
         *
         * @param context Live, non-NULL accessor context returned by open_accessor_async(). Borrowed for this call.
         * @param prim Prim from this accessor's dictionary; must exist in the prepared selection.
         * @param start_index Zero-based start in the enumeration; indexes past the end are allowed.
         * @param[out] storage Optional caller-owned array of capacity prim-path handles; never retained.
         * @param capacity Storage capacity in elements, not bytes; ignored if storage is NULL.
         * @param[out] out_total Non-NULL destination for the full sequence length; consume only on success.
         * @return
         * - **OVRTX_DATA_OK** if out_total and the requested page were written, including empty pages.
         * - **OVRTX_DATA_NOT_FOUND** if prim is absent, even for a count-only or empty-page query.
         * - **OVRTX_DATA_INVALID_ARGUMENT** if out_total is NULL.
         */
        ovrtx_data_status_t (*get_children)(ovrtx_data_accessor_context_t* context,
                                           ovx_primpath_t prim,
                                           uint64_t start_index,
                                           ovx_primpath_t* storage,
                                           uint64_t capacity,
                                           uint64_t* out_total);
        /**
         * Copy a page of attribute-name tokens exposed by a prim.
         *
         * The total and enumeration order are stable for this immutable accessor; no lexical
         * ordering is required. NULL storage is a count-only query and ignores capacity.
         * Otherwise copy exactly min(capacity, total - start_index) handles when start_index
         * is below total. At or beyond total (including UINT64_MAX), or with zero capacity,
         * succeed without writing storage. A short page is normal success, not OUT_OF_RANGE.
         * Always write the full sequence length to out_total on success, independent of
         * start_index and capacity. Entries beyond the written prefix remain untouched.
         * Performs no I/O or hidden transfers and acquires no ownership or leases. The caller
         * owns storage; copied handles remain dictionary-owned. Retain the dictionary while using them.
         * Each name occurs once, including attributes whose types get_attribute_info() cannot
         * represent. A present attribute-free prim succeeds with total zero. No attribute
         * values are copied. Required independently of CPU/GPU array capabilities.
         *
         * @param context Live, non-NULL accessor context returned by open_accessor_async(). Borrowed for this call.
         * @param prim Prim from this accessor's dictionary; must exist in the prepared selection.
         * @param start_index Zero-based start in the enumeration; indexes past the end are allowed.
         * @param[out] storage Optional caller-owned array of capacity attribute-name handles; never retained.
         * @param capacity Storage capacity in elements, not bytes; ignored if storage is NULL.
         * @param[out] out_total Non-NULL destination for the full sequence length; consume only on success.
         * @return
         * - **OVRTX_DATA_OK** if out_total and the requested page were written, including empty pages.
         * - **OVRTX_DATA_NOT_FOUND** if prim is absent, even for a count-only or empty-page query.
         * - **OVRTX_DATA_INVALID_ARGUMENT** if out_total is NULL.
         */
        ovrtx_data_status_t (*get_attributes)(ovrtx_data_accessor_context_t* context,
                                           ovx_primpath_t prim,
                                           uint64_t start_index,
                                           ovx_token_t* storage,
                                           uint64_t capacity,
                                           uint64_t* out_total);
        /**
         * Copy metadata describing a prim in the prepared selection.
         *
         * This retrieves prim metadata, not an attribute list or attribute values. Use
         * get_attributes() to discover attribute names. The result
         * record is a value copy; any tokens in it remain owned by the supplied dictionary.
         * No lease is acquired, and a prim without a type name may return a zero type_name.
         *
         * @param context Live, non-NULL accessor context returned by open_accessor_async(). Borrowed for this call.
         * @param prim Prim path from this accessor's dictionary; must identify a prim in the prepared selection.
         * @param[out] info Non-NULL destination for the metadata record.
         * @return
         * - **OVRTX_DATA_OK** if info was written.
         * - **OVRTX_DATA_NOT_FOUND** if prim is absent.
         * - **OVRTX_DATA_INVALID_ARGUMENT** if info is NULL.
         */
        ovrtx_data_status_t (*get_prim_info)(ovrtx_data_accessor_context_t* context,
                                             ovx_primpath_t prim,
                                             ovrtx_data_prim_info_t* info);
        /**
         * Copy the storage type and logical element count of an attribute.
         *
         * The result describes prepared storage; it does not acquire or copy the payload.
         * Scalars have count one and is_array false. Arrays have is_array true even when count
         * is zero or one. dtype.lanes is the packed component count per logical element.
         * Only the type/semantic combinations documented by ovrtx_data_attribute_info_t are
         * supported; do not silently coerce other types. Enumeration may expose unsupported
         * attributes. This value copy acquires no lease and remains usable after the call.
         *
         * @param context Live, non-NULL accessor context returned by open_accessor_async(). Borrowed for this call.
         * @param prim Prim path from this accessor's dictionary; must identify a prim in the prepared selection.
         * @param attribute Attribute-name token from the same dictionary as prim.
         * @param[out] info Non-NULL destination for the attribute layout.
         * @return
         * - **OVRTX_DATA_OK** if info was written.
         * - **OVRTX_DATA_NOT_FOUND** if prim or attribute is absent.
         * - **OVRTX_DATA_UNSUPPORTED** if the attribute type/semantic cannot be represented.
         * - **OVRTX_DATA_INVALID_ARGUMENT** if info is NULL.
         */
        ovrtx_data_status_t (*get_attribute_info)(ovrtx_data_accessor_context_t* context,
                                                  ovx_primpath_t prim,
                                                  ovx_token_t attribute,
                                                  ovrtx_data_attribute_info_t* info);
        /**
         * Copy one scalar attribute into caller-owned storage.
         *
         * Storage is tightly packed, using dtype.lanes * (dtype.bits / 8) bytes and the layout
         * reported by get_attribute_info(). A NULL buffer or insufficient capacity is a sizing
         * query: set required_bytes and return OUT_OF_RANGE without copying. With sufficient
         * capacity, copy the whole scalar and set required_bytes to its size; never partially
         * copy a scalar. An array, including a one-element array, is not a scalar.
         * The copied bytes belong to the caller. A copied token remains dictionary-owned;
         * retain the dictionary when interpreting it. No array lease is created.
         *
         * @param context Live, non-NULL accessor context returned by open_accessor_async(). Borrowed for this call.
         * @param prim Prim path from this accessor's dictionary; must identify a prim in the prepared selection.
         * @param attribute Attribute-name token from the same dictionary as prim.
         * @param[out] buffer Destination of capacity_bytes bytes; may be NULL to query the required size.
         * @param capacity_bytes Available destination capacity in bytes.
         * @param[out] required_bytes Non-NULL size output, valid on OK and on the sizing-query OUT_OF_RANGE result.
         * @return
         * - **OVRTX_DATA_OK** if the entire scalar was copied.
         * - **OVRTX_DATA_OUT_OF_RANGE** if buffer is NULL or capacity_bytes is insufficient; required_bytes is set.
         * - **OVRTX_DATA_NOT_FOUND** if prim or attribute is absent.
         * - **OVRTX_DATA_UNSUPPORTED** if its type/semantic cannot be represented.
         * - **OVRTX_DATA_INVALID_ARGUMENT** if required_bytes is NULL or the attribute is an array.
         */
        ovrtx_data_status_t (*get_scalar_attribute)(ovrtx_data_accessor_context_t* context,
                                                    ovx_primpath_t prim,
                                                    ovx_token_t attribute,
                                                    void* buffer,
                                                    uint64_t capacity_bytes,
                                                    uint64_t* required_bytes);
        /**
         * Borrow an immutable, tightly packed CPU array from the prepared selection.
         *
         * This callback and release_array_cpu must both be non-NULL exactly when the provider
         * advertises OVRTX_DATA_ACCESSOR_CAP_CPU_ARRAYS. GPU support does not imply CPU support.
         * Acquisition performs no I/O, copying to another device, or hidden materialization.
         * The returned layout matches get_attribute_info(); byte_size equals count * dtype.lanes
         * * (dtype.bits / 8). A successful empty array still acquires a lease and may have NULL data.
         * Copy the result record as needed, but do not free or modify its data. Release each
         * successful lease exactly once on this accessor before closing it. Data is valid only
         * until that release; error results transfer no lease.
         *
         * @param context Live, non-NULL accessor context returned by open_accessor_async(). Borrowed for this call.
         * @param prim Prim path from this accessor's dictionary; must identify a prim in the prepared selection.
         * @param attribute Attribute-name token from the same dictionary as prim.
         * @param[out] array Non-NULL destination for the data pointer, layout, byte size, and lease ID.
         * @return
         * - **OVRTX_DATA_OK** if a lease and array view were returned, including for an empty array.
         * - **OVRTX_DATA_NOT_FOUND** if prim or attribute is absent.
         * - **OVRTX_DATA_UNSUPPORTED** if the type or prepared CPU representation is unavailable.
         * - **OVRTX_DATA_INVALID_ARGUMENT** if array is NULL or the attribute is scalar.
         */
        ovrtx_data_status_t (*acquire_array_cpu)(ovrtx_data_accessor_context_t* context,
                                                 ovx_primpath_t prim,
                                                 ovx_token_t attribute,
                                                 ovrtx_data_cpu_array_t* array);
        /**
         * Release one CPU array lease acquired from this accessor.
         *
         * The caller must finish all reads of the borrowed array before releasing it. On success
         * the lease and its data view become invalid, even if underlying storage is shared with
         * other leases. Release empty arrays as well. This does not close the accessor or release
         * its resource pin; other leases retain their own lifetime. This callback is required
         * only with OVRTX_DATA_ACCESSOR_CAP_CPU_ARRAYS and must otherwise be NULL.
         *
         * @param context Live, non-NULL accessor context returned by open_accessor_async(). Borrowed for this call.
         * @param lease Unreleased lease ID returned by acquire_array_cpu() on this accessor.
         * @return
         * - **OVRTX_DATA_OK** if the lease was released.
         * - **OVRTX_DATA_INVALID_HANDLE** if the lease is unknown or already released; no ownership is transferred.
         */
        ovrtx_data_status_t (*release_array_cpu)(ovrtx_data_accessor_context_t* context,
                                                 ovrtx_data_array_lease_id_t lease);
        /**
         * Borrow an immutable CUDA tensor already prepared on the requested device.
         *
         * This callback and release_array_gpu must both be non-NULL exactly when the provider
         * advertises OVRTX_DATA_ACCESSOR_CAP_GPU_ARRAYS. CPU support does not imply GPU support.
         * Do not initiate I/O, migrate data, or prepare another device representation here.
         * The returned DLTensor has ndim 1, shape[0] equal to the logical element count, packed
         * dtype matching get_attribute_info(), and strides NULL or {1}; honor byte_offset.
         * Before reading the tensor on tensor.device, the consumer synchronizes both nonzero
         * cuda_sync fields: stream 1 is the default stream, stream >1 is a cudaStream_t to drain,
         * and wait_event is a cudaEvent_t to wait on. Both zero means the data is already ready.
         * Tensor data, shape, strides, and synchronization objects remain provider-owned through
         * lease release. Do not free them. Finish device accesses before release_array_gpu().
         * Every successful acquisition, including an empty array, requires exactly one release
         * on this accessor before close. Error results transfer no lease.
         *
         * @param context Live, non-NULL accessor context returned by open_accessor_async(). Borrowed for this call.
         * @param prim Prim path from this accessor's dictionary; must identify a prim in the prepared selection.
         * @param attribute Attribute-name token from the same dictionary as prim.
         * @param access Non-NULL descriptor selecting the CUDA device; borrowed for this call.
         * @param[out] array Non-NULL destination for the tensor, readiness metadata, and lease ID.
         * @return
         * - **OVRTX_DATA_OK** if the tensor and lease were returned.
         * - **OVRTX_DATA_NOT_FOUND** if prim or attribute is absent.
         * - **OVRTX_DATA_UNSUPPORTED** for non-CUDA devices, unsupported types, or unavailable prepared representations.
         * - **OVRTX_DATA_INVALID_ARGUMENT** if access or array is NULL, or the attribute is scalar.
         */
        ovrtx_data_status_t (*acquire_array_gpu)(ovrtx_data_accessor_context_t* context,
                                                 ovx_primpath_t prim,
                                                 ovx_token_t attribute,
                                                 const ovrtx_data_gpu_access_desc_t* access,
                                                 ovrtx_data_gpu_array_t* array);
        /**
         * Release one GPU array lease after all consumer device accesses have completed.
         *
         * The caller must synchronize outstanding device work using this view before release;
         * this function is not a substitute for that synchronization. Success invalidates the
         * lease, tensor data/metadata pointers, and provider-owned synchronization objects for
         * this view. Other leases keep their own lifetime. Empty arrays also require release.
         * This does not close the accessor or unpin its resource. Required only when the provider
         * advertises OVRTX_DATA_ACCESSOR_CAP_GPU_ARRAYS; otherwise this callback must be NULL.
         *
         * @param context Live, non-NULL accessor context returned by open_accessor_async(). Borrowed for this call.
         * @param lease Unreleased lease ID returned by acquire_array_gpu() on this accessor.
         * @return
         * - **OVRTX_DATA_OK** if the lease was released.
         * - **OVRTX_DATA_INVALID_HANDLE** if the lease is unknown or already released; no ownership is transferred.
         */
        ovrtx_data_status_t (*release_array_gpu)(ovrtx_data_accessor_context_t* context,
                                                 ovrtx_data_array_lease_id_t lease);
    } ovrtx_data_accessor_vtable_t;

    /** Immutable structured result of open_accessor_async(); traversal performs no I/O. */
    typedef struct ovrtx_data_accessor_t
    {
        const ovrtx_data_accessor_vtable_t* vtable; /**< Non-NULL immutable table, borrowed until close succeeds. */
        ovrtx_data_accessor_context_t* context; /**< Non-NULL provider-owned state; never free directly. */
    } ovrtx_data_accessor_t;

    /** Process-local registration identity. Zero is invalid; IDs are not reused
     * during the process. Copying does not retain the provider or prove that it
     * remains registered. */
    typedef struct ovrtx_data_provider_id_t
    {
        uint64_t raw_id;
    } ovrtx_data_provider_id_t;
    /** Caller-owned opaque operation token for cancellation, borrowed through completion and submission/cancel return. */
    typedef struct ovrtx_data_request_t ovrtx_data_request_t;

    /** Submission result, separate from the asynchronous operation completion status. */
    typedef enum ovrtx_data_submit_t
    {
        OVRTX_DATA_ACCEPTED = 0, /**< Exactly one completion is owed, possibly inline. */
        OVRTX_DATA_RETRY = 1, /**< Temporary backpressure; retain no arguments and invoke no completion. Caller may resubmit. */
        OVRTX_DATA_REJECTED = 2 /**< Submission refused; retain no arguments and invoke no completion. No routing fallback. */
    } ovrtx_data_submit_t;

    /** Resource representation requested at pin time; the successful result must match. */
    typedef enum ovrtx_data_kind_t
    {
        OVRTX_DATA_BYTES = 1, /**< Encoded bytes served by positioned reads and optional maps. */
        OVRTX_DATA_STRUCTURED = 2 /**< Schema-defined data served by prepared accessors. */
    } ovrtx_data_kind_t;

/** Unknown byte length, or map-through-EOF size. Structured selectors are schema-defined.
 * Not a read_async read-to-EOF request. Zero byte length means a known empty resource. */
#define OVRTX_DATA_SIZE_UNKNOWN UINT64_MAX

    /** Pin-time access-cost hint, independent of identity. Structured resources use UNKNOWN. */
    typedef enum ovrtx_data_range_strategy_t
    {
        OVRTX_DATA_RANGE_UNKNOWN = 0, /**< No range-cost information is available. */
        OVRTX_DATA_RANGE_NATIVE = 1, /**< Reads ranges directly without whole-object materialization. */
        OVRTX_DATA_RANGE_CACHED_READ_THROUGH = 2, /**< Fetched data is cached for subsequent reads; not necessarily resident at pin time. */
        OVRTX_DATA_RANGE_MATERIALIZE_ONLY = 3, /**< Range access materializes the whole object, without a cross-read reuse guarantee. */
        OVRTX_DATA_RANGE_UNSUPPORTED = 4 /**< Subranges are unsupported; whole-object reads/maps may still succeed. */
    } ovrtx_data_range_strategy_t;

/** Request tracking if available; successful pin may report it disabled. Mutually exclusive
 * with REQUIRE_CHANGE_TRACKING. Neither flag requests no tracking; interest lasts until unpin. */
#define OVRTX_DATA_PIN_WATCH_CHANGES (UINT64_C(1) << 0)
/** Require tracking for this pin; unavailable tracking completes with UNSUPPORTED.
 * Mutually exclusive with WATCH_CHANGES. See pin_async for gap-free establishment and lifetime. */
#define OVRTX_DATA_PIN_REQUIRE_CHANGE_TRACKING (UINT64_C(1) << 1)

/** Advisory future whole-object access intent; never authorizes payload I/O during pinning. */
#define OVRTX_DATA_HINT_WHOLE_OBJECT (UINT64_C(1) << 0)

    /** Request options. NULL is equivalent to zero hints, timeout, priority and pin_flags.
     * For a non-NULL record, struct_size must be initialized to sizeof(ovrtx_data_request_options_t). Hints
     * never change revision, cancellation or completion guarantees. WHOLE_OBJECT
     * describes future access; it never permits payload loading during pinning.
     * Whole-object fallback reads also carry it on each positioned chunk, including
     * unknown-size resources. It is not an exclusive stream or cursor lease:
     * concurrent consumers may issue independent reads against the same pin.
     * The runtime retains this record through completion and submission/cancel return.
     * Unknown hint bits are ignored; unknown pin_flags or both tracking flags are invalid.
     * pin_flags must be zero for read, map and accessor requests. */
    typedef struct ovrtx_data_request_options_t
    {
        size_t struct_size; /**< Set to sizeof(ovrtx_data_request_options_t). */
        uint64_t hints; /**< Bitwise OVRTX_DATA_HINT_* values; unknown bits are ignored. */
        uint64_t timeout_ns; /**< Advisory budget in nanoseconds from submission; zero = unspecified, not a deadline guarantee. */
        int32_t priority; /**< Advisory scheduling priority; higher requests earlier service, zero = normal. */
        uint64_t pin_flags; /**< Pin-only OVRTX_DATA_PIN_* flags. WATCH_CHANGES requests optional
                            * tracking; REQUIRE_CHANGE_TRACKING fails with UNSUPPORTED when
                            * tracking cannot be established for this resource. */
    } ovrtx_data_request_options_t;

    /** Provider-owned state for a successful pin. The runtime passes this opaque handle
     * only to its owning provider and never dereferences it. Valid until unpin(). */
    typedef struct ovrtx_data_resource_handle_t ovrtx_data_resource_handle_t;

    /** Record and strings are callback-scoped. The runtime copies strings before
     * the completion returns. Only handle remains provider-owned until unpin().
     *
     * @par UDIM manifest schema
     * Request OVRTX_DATA_STRUCTURED, schema
     * "ovrtx.texture.udim", schema_version=1; advertise CPU_ARRAYS and accept
     * open_accessor_async(0, OVRTX_DATA_SIZE_UNKNOWN). In the supplied dictionary,
     * /udim.tile_ids is a u32 CPU array of unique IDs in [1001,9999]. For each ID,
     * /tiles/tile_&lt;id&gt;.asset is a scalar token naming a nonempty reference to pin
     * relative to this manifest resource. All array leases must be released
     * before close_accessor. The C++ helper ovrtx/providers/udim_manifest.hpp implements
     * this accessor from a tile list without renderer-private dependencies. An empty
     * tile list is valid. The built-in storage provider requires a supported tiling
     * marker in the innermost basename for both loose and packaged resources;
     * non-pattern STRUCTURED root requests return NOT_HANDLED; dependency requests
     * return UNSUPPORTED without rerouting. A valid pattern with no matching tiles
     * returns an empty manifest.
     *
     * @par Package references
     * Package references use outer[member], including nested outer[a.usdz[b]].
     * Resolve the outer resource through the owning provider and retain its byte
     * lease while member views are in use. ovrtx/providers/stored_package.hpp provides
     * validated, zero-copy views of stored ZIP/ZIP64 members used by USDZ;
     * compressed/encrypted members are unsupported. Views do not own storage.
     * The built-in provider resolves relative dependencies inside the innermost
     * package and rejects paths escaping it. Absolute paths and URI references
     * resolve outside the package using the same built-in provider; they do not
     * reroute to another provider. Custom providers define their own resolution.
     */
    typedef struct ovrtx_data_resource_t
    {
        size_t struct_size; /**< Set to sizeof(ovrtx_data_resource_t). */
        ovrtx_data_resource_handle_t* handle; /**< Non-NULL provider-owned pin; release exactly once with unpin. */
        ovx_string_t identifier; /**< Nonempty canonical identity within namespace_key; length-delimited, no embedded NUL. */
        ovx_string_t revision; /**< Equal nonempty IDs mean equal data for this identifier; empty disables cross-pin revision identity. */
        ovx_string_t content_hash; /**< Optional "sha256:<64 lowercase hex digits>"; callback-scoped, no embedded NUL. */
        ovrtx_data_kind_t kind; /**< Must equal the requested pin kind. */
        uint64_t byte_size; /**< Exact byte length (zero is empty), or SIZE_UNKNOWN; STRUCTURED requires SIZE_UNKNOWN. */
        ovx_string_t schema; /**< Nonempty schema identifier for STRUCTURED; callback-scoped, no embedded NUL. */
        uint32_t schema_version; /**< Nonzero version of schema for STRUCTURED. */
        /** Available at pin completion, before payload I/O. UNKNOWN if not known.
         * NATIVE reads ranges directly. CACHED_READ_THROUGH caches fetched data for
         * subsequent reads (not necessarily resident yet). MATERIALIZE_ONLY must
         * fetch the whole object and makes no cross-read cache guarantee.
         * UNSUPPORTED cannot serve subranges; a whole-object read/map may succeed.
         * This is a cost hint, not content identity. STRUCTURED uses UNKNOWN. */
        ovrtx_data_range_strategy_t range_strategy;
        bool change_tracking_enabled; /**< True only when requested tracking was established.
                                      * False is valid for optional or unrequested tracking.
                                      * This describes the pin, not immutable content identity. */
        /** Optional source modification time, in nanoseconds since the Unix epoch (UTC).
         * Valid only when has_modified_time is true; zero and negative values are valid.
         * Fixed for the lifetime of this pin. Source precision may be coarser than nanoseconds.
         * Equal timestamps do not imply equal content: this is neither a revision nor a hash,
         * and does not by itself authorize timestamp-based cache validation. For package
         * members, report the containing source's timestamp; virtual/aggregate resources
         * without a meaningful single source leave has_modified_time false. */
        int64_t modified_time_ns;
        /** True when modified_time_ns is available at pin completion. Optional for every
         * provider; false means unavailable and consumers must ignore modified_time_ns.
         * This metadata owns no storage and remains valid in a copied pin result. */
        bool has_modified_time;
    } ovrtx_data_resource_t;


    /** Callback-scoped map result; the bytes and opaque lease outlive the record until release_map(). */
    typedef struct ovrtx_data_byte_view_t
    {
        size_t struct_size; /**< Set to sizeof(ovrtx_data_byte_view_t). */
        const void* data; /**< Immutable CPU-readable bytes through release_map; NULL allowed only for an empty view. */
        uint64_t size; /**< Actual byte count, clipped to EOF; fits SIZE_MAX; this is a count, not a sentinel. */
        void* lease; /**< Non-NULL opaque release obligation, including for empty views. */
    } ovrtx_data_byte_view_t;

    /** Complete one accepted pin operation, exactly once, possibly inline.
     *
     * The caller copies the record and its strings during this call. OK transfers one pin
     * obligation even when cancellation races success; failures transfer nothing and require
     * NULL resource. This callback returns no status and may retire user_data. Never access
     * user_data after invoking it. Error text is optional diagnostic context, not a status override.
     *
     * @param user_data Unchanged opaque caller-owned context supplied to pin_async(); never dereference/free it.
     * @param status Terminal operation status; see pin_async(). NOT_HANDLED is only a root-routing decline.
     * @param resource Non-NULL ABI-valid callback-scoped record on OK, NULL otherwise. Its handle lives until unpin().
     * @param error Callback-scoped length-delimited diagnostic; empty is allowed. The caller copies it if needed.
     * @return No value; completion does not acknowledge subsequent consumer processing.
     */
    typedef void (*ovrtx_data_pin_done_t)(void* user_data,
                                         ovrtx_data_status_t status,
                                         const ovrtx_data_resource_t* resource,
                                         ovx_string_t error);

    /** Complete one accepted positioned read, exactly once, possibly inline.
     *
     * Stop accessing the destination before calling. The caller owns the destination, including
     * on failure; no buffer ownership is transferred. Output bytes are consumed only on OK.
     * A short successful read means EOF, subject to the pinned known-size checks in read_async().
     * The callback may retire user_data; do not use it again after invoking this callback.
     *
     * @param user_data Unchanged opaque caller-owned context supplied to read_async(); never dereference/free it.
     * @param status Terminal operation status; NOT_HANDLED and BUSY are invalid. See read_async().
     * @param bytes_read Number of bytes written, at most the requested size; consumed only on OK.
     * @param error Optional callback-scoped diagnostic; empty is allowed and status remains authoritative.
     * @return No value; no additional completion is permitted.
     */
    typedef void (*ovrtx_data_read_done_t)(void* user_data,
                                          ovrtx_data_status_t status,
                                          uint64_t bytes_read,
                                          ovx_string_t error);

    /** Complete one accepted structured open, exactly once, possibly inline.
     *
     * All preparation finishes before this callback. The caller copies the accessor record;
     * its context, table and prepared data remain live until successful close_accessor().
     * OK transfers one close obligation, including raced cancellation successes. Failures
     * pass NULL and transfer nothing. Do not access user_data after invoking this callback.
     *
     * @param user_data Unchanged opaque caller-owned context supplied to open_accessor_async(); never dereference/free it.
     * @param status Terminal operation status; NOT_HANDLED and BUSY are invalid. See open_accessor_async().
     * @param accessor Non-NULL callback-scoped record on OK, NULL otherwise; dictionary remains caller-owned.
     * @param error Optional callback-scoped diagnostic; empty is allowed and status remains authoritative.
     * @return No value; consumer accessor calls may follow successful completion.
     */
    typedef void (*ovrtx_data_accessor_done_t)(void* user_data,
                                              ovrtx_data_status_t status,
                                              const ovrtx_data_accessor_t* accessor,
                                              ovx_string_t error);

    /** Complete one accepted byte map, exactly once, possibly inline.
     *
     * The record is callback-scoped. OK transfers one release_map obligation, including empty
     * maps and raced cancellation successes; data remains immutable until that release.
     * Failure requires NULL view and transfers nothing. UNSUPPORTED permits read fallback;
     * other failures are terminal. Do not access user_data after invoking this callback.
     *
     * @param user_data Unchanged opaque caller-owned context supplied to map_async(); never dereference/free it.
     * @param status Terminal operation status; NOT_HANDLED and BUSY are invalid. See map_async().
     * @param view Non-NULL ABI-valid callback-scoped record on OK, NULL otherwise; lease must be non-NULL even if empty.
     * @param error Optional callback-scoped diagnostic; empty is allowed and status remains authoritative.
     * @return No value; no additional completion is permitted.
     */
    typedef void (*ovrtx_data_map_done_t)(void* user_data,
                                         ovrtx_data_status_t status,
                                         const ovrtx_data_byte_view_t* view,
                                         ovx_string_t error);

/** Exact descriptor/vtable layout version required by registration; independent of accessor ABI. */
#define OVRTX_DATA_PROVIDER_ABI_VERSION 5u

    /** Opaque implementation state passed to every provider operation. May be NULL for stateless providers. */
    typedef struct ovrtx_data_provider_context_t ovrtx_data_provider_context_t;

    /** Registration metadata, separate from the provider implementation.
     * Set struct_size to sizeof(ovrtx_data_provider_desc_t) and abi_version to OVRTX_DATA_PROVIDER_ABI_VERSION. */
    typedef struct ovrtx_data_provider_desc_t
    {
        size_t struct_size; /**< Set to sizeof(ovrtx_data_provider_desc_t). */
        uint32_t abi_version; /**< Must equal OVRTX_DATA_PROVIDER_ABI_VERSION. */
        ovx_string_t namespace_key; /**< Stable, unique among live registrations, nonempty cache/authorization domain; no embedded NUL. Copied at registration. */
        ovx_string_t uri_scheme; /**< ASCII URI scheme without ':', matched case-insensitively; empty is catch-all. Copied at registration. */
        int32_t priority; /**< Higher values run first within a route group; ties retain registration order. */
        uint64_t accessor_capabilities; /**< OVRTX_DATA_ACCESSOR_CAP_*; unknown bits are invalid; CPU/GPU arrays are independently optional.
                                         * Each advertised bit requires its acquire/release pair on every accessor;
                                         * unadvertised pairs must be NULL. Zero also permits scalar-only accessors. */
    } ovrtx_data_provider_desc_t;

    /** Immutable provider operations. Multiple instances may share one table.
     * Async operations pair done with caller-owned user_data; return user_data
     * unchanged as done's first argument, following the completion rules above.
     * Set struct_size to sizeof(ovrtx_data_provider_vtable_t) and abi_version to OVRTX_DATA_PROVIDER_ABI_VERSION. */
    typedef struct ovrtx_data_provider_vtable_t
    {
        size_t struct_size; /**< Set to sizeof(ovrtx_data_provider_vtable_t). */
        uint32_t abi_version; /**< Must equal OVRTX_DATA_PROVIDER_ABI_VERSION. */

        /**
         * Resolve a reference and establish an immutable resource identity without loading payload data.
         *
         * Required callback. With base NULL, reference is an absolute root path or URI. With a
         * base pin, resolve the dependency using that pin's provider and immutable dependency
         * context; an empty dependency reference is allowed by the API and is provider-defined.
         * Pinning may fetch metadata but must not read, prefetch, or map payload bytes, even with
         * WHOLE_OBJECT. A successful pin does not promise that subsequent payload I/O succeeds.
         * Complete with OK and a non-NULL resource record containing a non-NULL handle, the
         * requested kind, canonical identifier, and valid metadata. Set struct_size; use
         * SIZE_UNKNOWN for unknown length (zero means empty). STRUCTURED requires a nonempty
         * schema, nonzero schema_version, SIZE_UNKNOWN byte_size, and UNKNOWN range_strategy.
         * Equal nonempty revisions for one identifier mean
         * equal content; an empty revision provides no cross-pin deduplication identity.
         * The record and strings need live only through done(); the caller copies them. The
         * handle and immutable content/dependency identity remain provider-owned until unpin().
         * Successful completion transfers one pin obligation, even if cancellation races success.
         *
         * With WATCH_CHANGES, attempt tracking but allow success with change_tracking_enabled=false.
         * With REQUIRE_CHANGE_TRACKING, complete with UNSUPPORTED and NULL resource if tracking
         * cannot be established; success must report change_tracking_enabled=true. With neither flag,
         * no tracking is requested and change_tracking_enabled must be false. Both flags or
         * unknown pin_flags are INVALID_ARGUMENT.
         * Providers need not implement tracking, but must honor required-mode failure.
         * Establish tracking as part of snapshot selection: changes after the selected snapshot
         * must not fall into a gap before monitoring starts. Buffer such events until successful
         * completion has been invoked, then publish them through ovrtx_data_notify_changed()
         * outside provider operation callbacks and provider locks (schedule delivery if necessary).
         * Track the logical resource, including relevant package/dependency changes, through unpin().
         * Notifications do not mutate the pinned snapshot. Independent pins retain independent
         * interest; providers may share monitoring internally until the last interested pin ends.
         * A failed/cancelled pin that transfers no handle must release any provisional monitoring.
         * Consumers subscribe to the notification dispatcher before submitting interested pins and
         * retain early events until the pin's canonical identity is known. Notification delivery
         * can race consumer-side processing of the completion even after done() has returned.
         * Tracking support is per resource; advertising a provider-wide capability is not required.
         *
         * On failure, pass NULL resource; no pin transfers. Use NOT_HANDLED to decline a root so
         * the next route may run. Dependency failures never reroute. NOT_FOUND, UNSUPPORTED,
         * ACCESS_DENIED, IO_ERROR, STALE, and CANCELLED report terminal operation failures as
         * applicable; BUSY is not submission backpressure (return RETRY for that).
         * The caller retains request inputs through completion and return of submission/cancel.
         * For ACCEPTED, retain done/user_data until the one completion, including cancellation.
         * Do not access user_data after invoking done. For RETRY or REJECTED, retain no operation
         * arguments and invoke no completion. Submission must not block waiting for payload I/O.
         *
         * @param context Registered provider context, possibly NULL for a stateless provider. Borrowed, never freed here.
         * @param request Opaque caller-owned operation identity used by cancel(); do not dereference or free it.
         * @param base NULL for a root, otherwise a live handle from this provider retained through completion.
         * @param reference Borrowed length-delimited reference; need not be NUL-terminated.
         * @param kind Requested OVRTX_DATA_BYTES or OVRTX_DATA_STRUCTURED resource kind.
         * @param options Borrowed request options, including pin_flags; NULL means no tracking and default hints.
         * Unknown hint bits are ignored; invalid pin_flags are rejected.
         * @param done Non-NULL completion function; invoke exactly once if submission returns ACCEPTED.
         * @param user_data Opaque caller-owned completion context; pass unchanged to done and do not use afterward.
         * @return
         * - **OVRTX_DATA_ACCEPTED**: exactly one completion is owed, possibly inline before this call returns.
         * - **OVRTX_DATA_RETRY**: temporary submission backpressure; no completion or retained callback state. The caller may resubmit.
         * - **OVRTX_DATA_REJECTED**: submission refused; no completion or retained callback state. This is not a routing decline.
         */
        ovrtx_data_submit_t (*pin_async)(ovrtx_data_provider_context_t* context,
                                         ovrtx_data_request_t* request,
                                         ovrtx_data_resource_handle_t* base,
                                           ovx_string_t reference,
                                         ovrtx_data_kind_t kind,
                                         const ovrtx_data_request_options_t* options,
                                         ovrtx_data_pin_done_t done,
                                         void* user_data);

        /**
         * Release the provider-owned state for one successful pin.
         *
         * Required callback, called exactly once per successful pin after all dependent requests,
         * accessors, and byte mappings have retired. Release pin-owned resources and this pin's
         * change-tracking interest; the handle becomes invalid. Queued monitoring work must not
         * dereference that released pin state; independent monitoring tasks need their own ownership. Shared backing storage may remain alive for other pins or caches.
         * This is synchronous, nonblocking teardown with no failure channel. NULL, foreign,
         * or already-unpinned handles violate the calling contract; no recovery is guaranteed.
         * Do not invalidate independent pins or invoke outstanding completions from this release.
         *
         * @param context Registered provider context, possibly NULL for a stateless provider. Borrowed, never freed here.
         * @param resource Live handle returned by a successful pin_async() completion; consumed by this call.
         * @return
         * - No value. The resource pin is released when the call returns.
         */
        void (*unpin)(ovrtx_data_provider_context_t* context, ovrtx_data_resource_handle_t* resource);

        /**
         * Read a positioned byte range from an immutable byte-resource pin into caller storage.
         *
         * Required for providers serving BYTES; may be NULL for structured-only providers.
         * Concurrent reads have independent offsets: do not interpret calls as an exclusive
         * stream or shared cursor. WHOLE_OBJECT remains advisory on each positioned read.
         * Read at most size bytes beginning at offset and complete with OK and bytes_read.
         * A short successful read means EOF; offset at or beyond EOF returns zero. For a known
         * byte_size, return exactly min(size, byte_size - offset), or zero beyond EOF; premature
         * short success is treated as IO_ERROR. A zero-byte request permits a NULL destination.
         * The finite range must fit the address space and must not overflow offset + size;
         * SIZE_UNKNOWN has no read-to-EOF meaning for this callback.
         * Write only within destination[0..size). Stop accessing it before completing; it remains
         * caller-owned. Failure may leave partial writes, which the caller must not consume.
         * Complete using done(user_data, status, bytes_read, error); bytes_read must not exceed
         * size, and is consumed only for OK. Use an appropriate terminal status such as
         * ACCESS_DENIED, IO_ERROR, STALE,
         * UNSUPPORTED, or CANCELLED; NOT_HANDLED and BUSY are invalid payload completions.
         * The caller retains request inputs through completion and return of submission/cancel.
         * For ACCEPTED, retain done/user_data until the one completion, including cancellation.
         * Do not access user_data after invoking done. For RETRY or REJECTED, retain no operation
         * arguments and invoke no completion. Submission must not block waiting for payload I/O.
         *
         * @param context Registered provider context, possibly NULL for a stateless provider. Borrowed, never freed here.
         * @param request Opaque caller-owned operation identity used by cancel(); do not dereference or free it.
         * @param resource Live pin handle owned by this provider, retained by the caller through completion.
         * @param offset Absolute byte offset from the start of the pinned resource.
         * @param[out] destination Writable caller-owned buffer of size bytes; may be NULL only when size is zero.
         * @param size Maximum byte count, interpreted literally rather than as a read-to-EOF sentinel.
         * @param options Borrowed request options; NULL means defaults. Unknown hints are ignored; pin_flags must be zero.
         * @param done Non-NULL completion function; invoke exactly once if submission returns ACCEPTED.
         * @param user_data Opaque caller-owned completion context; pass unchanged to done and do not use afterward.
         * @return
         * - **OVRTX_DATA_ACCEPTED**: exactly one completion is owed, possibly inline before this call returns.
         * - **OVRTX_DATA_RETRY**: temporary submission backpressure; no completion or retained callback state. The caller may resubmit.
         * - **OVRTX_DATA_REJECTED**: submission refused; no completion or retained callback state. This is not a routing decline.
         */
        ovrtx_data_submit_t (*read_async)(ovrtx_data_provider_context_t* context,
                                          ovrtx_data_request_t* request,
                                          ovrtx_data_resource_handle_t* resource,
                                            uint64_t offset,
                                          void* destination,
                                            uint64_t size,
                                          const ovrtx_data_request_options_t* options,
                                          ovrtx_data_read_done_t done,
                                          void* user_data);

        /**
         * Load or prepare an independent structured selection from a pinned resource.
         *
         * Required together with close_accessor for providers serving STRUCTURED; both may be
         * NULL for byte-only providers. This is the explicit payload I/O/preparation boundary.
         * The provider/consumer schema defines offset and size: records, chunks, or another
         * region, not necessarily bytes. They are forwarded unchanged, without offset+size
         * arithmetic or byte bounds. Zero and SIZE_UNKNOWN have no generic special meaning.
         * Validate selectors against the schema; report INVALID_ARGUMENT or OUT_OF_RANGE when
         * invalid, and UNSUPPORTED when the requested selection/representation is unavailable.
         * Other terminal failures include ACCESS_DENIED, IO_ERROR, STALE, and CANCELLED.
         * NOT_HANDLED and BUSY are invalid payload completions.
         * On OK, pass a non-NULL accessor with a live non-NULL context and immutable, ABI-valid
         * vtable. All traversal/scalar callbacks are required, including attribute enumeration;
         * array acquire/release pairs must match the registered capability bits. The caller
         * copies the accessor record during done(); keep its context/vtable and all prepared
         * data alive until successful close_accessor(). Errors pass NULL and transfer no accessor.
         * Use the supplied dictionary for every returned path/token. The caller must keep the
         * dictionary and its backing owner alive through the accessor's lifetime. Preparation
         * must finish before completion; later accessor calls cannot fetch data or migrate it.
         * Multiple opens on one pin may overlap; each success has independent leases and close.
         * Failure, cancellation, or closure of one selection must not invalidate another.
         * The pin remains live until all selections, leases, and pending operations retire.
         * The caller retains request inputs through completion and return of submission/cancel.
         * For ACCEPTED, retain done/user_data until the one completion, including cancellation.
         * Do not access user_data after invoking done. For RETRY or REJECTED, retain no operation
         * arguments and invoke no completion. Submission must not block waiting for payload I/O.
         *
         * @param context Registered provider context, possibly NULL for a stateless provider. Borrowed, never freed here.
         * @param request Opaque caller-owned operation identity used by cancel(); do not dereference or free it.
         * @param resource Live pin handle owned by this provider, retained by the caller through completion.
         * @param offset Provider/schema-defined selection origin; forwarded unchanged.
         * @param size Provider/schema-defined selection extent; forwarded unchanged.
         * @param dictionary Non-NULL caller-owned dictionary, borrowed through preparation and accessor lifetime.
         * @param options Borrowed request options; NULL means defaults. Unknown hints are ignored; pin_flags must be zero.
         * @param done Non-NULL completion function; invoke exactly once if submission returns ACCEPTED.
         * @param user_data Opaque caller-owned completion context; pass unchanged to done and do not use afterward.
         * @return
         * - **OVRTX_DATA_ACCEPTED**: exactly one completion is owed, possibly inline before this call returns.
         * - **OVRTX_DATA_RETRY**: temporary submission backpressure; no completion or retained callback state. The caller may resubmit.
         * - **OVRTX_DATA_REJECTED**: submission refused; no completion or retained callback state. This is not a routing decline.
         */
        ovrtx_data_submit_t (*open_accessor_async)(ovrtx_data_provider_context_t* context,
                                                   ovrtx_data_request_t* request,
                                                   ovrtx_data_resource_handle_t* resource,
                                                     uint64_t offset,
                                                     uint64_t size,
                                                   path_dictionary_instance_t* dictionary,
                                                   const ovrtx_data_request_options_t* options,
                                                   ovrtx_data_accessor_done_t done,
                                                   void* user_data);

        /**
         * Destroy one prepared accessor after all its array leases have been released.
         *
         * Required together with open_accessor_async. Stop concurrent calls on this accessor
         * before closing; thread-safe queries do not permit racing context destruction.
         * On OK, destroy accessor-owned state and clear both fields of the supplied record.
         * All copies of this accessor then become invalid; the caller must not call its vtable
         * again. Do not destroy the caller's dictionary or release the underlying pin here.
         * Outstanding CPU/GPU leases require BUSY without destroying or clearing the accessor;
         * release them and retry. Errors transfer no ownership. Independent accessors remain valid.
         *
         * @param context Registered provider context, possibly NULL for a stateless provider. Borrowed, never freed here.
         * @param[in,out] accessor Non-NULL caller-held accessor record from this provider; cleared only on success.
         * @return
         * - **OVRTX_DATA_OK** if the accessor was closed and cleared.
         * - **OVRTX_DATA_BUSY** while array leases remain; accessor ownership is unchanged.
         * - **OVRTX_DATA_INVALID_ARGUMENT** for an invalid record argument.
         * - **OVRTX_DATA_INVALID_HANDLE** for an unknown or already-cleared accessor; arbitrary dangling/foreign contexts cannot be safely validated.
         */
        ovrtx_data_status_t (*close_accessor)(ovrtx_data_provider_context_t* context, ovrtx_data_accessor_t* accessor);

        /**
         * Request best-effort cancellation of an accepted asynchronous operation.
         *
         * Required callback. This is a nonblocking notification, not a join or ownership release.
         * The operation still owes exactly one completion. It may finish normally if cancellation
         * loses the race, or complete with CANCELLED; never complete twice. The runtime may
         * suppress a raced successful result and release its transferred pin/accessor/map.
         * Cancellation may race completion; a provider must tolerate a request no longer present
         * in its active-work bookkeeping. Do not dereference or free the opaque request token.
         * Request inputs and destinations stay live through completion and return of this call;
         * cancellation alone does not allow either side to release them early. Do not retain
         * user_data or write a destination after completing the operation.
         *
         * @param context Registered provider context, possibly NULL for a stateless provider. Borrowed, never freed here.
         * @param request Opaque caller-owned operation identity used by cancel(); do not dereference or free it.
         * @return
         * - No value. Return does not imply the operation has completed or its resources are released.
         */
        void (*cancel)(ovrtx_data_provider_context_t* context, ovrtx_data_request_t* request);

        /**
         * Acquire a leased, immutable CPU byte view of a positioned range.
         *
         * Optional callback paired with release_map; both must be NULL or both non-NULL.
         * read_async remains required for byte providers. This payload operation may perform
         * I/O/materialization, which is forbidden during pinning. Return an already CPU-readable
         * view; no deferred fetch is permitted when the consumer dereferences its data.
         * A finite size maps up to that many bytes; SIZE_UNKNOWN means through EOF. A short OK
         * view means EOF. For known resource length, view.size must equal the requested range
         * clipped to EOF; offset at or beyond EOF gives an empty view. A zero-size request also
         * returns an empty view. Finite offset+size must not overflow; returned sizes must fit
         * SIZE_MAX and must not overflow when added to offset.
         * On OK, pass a non-NULL record with struct_size set, non-NULL lease even for an empty
         * view, and non-NULL data when size is nonzero. The record is callback-scoped; its data
         * remains provider-owned and immutable until release_map(context, resource, lease).
         * Each successful map transfers one release obligation, including empty views and raced
         * cancellation successes. Errors pass NULL and transfer no lease.
         * An UNSUPPORTED completion permits read_async fallback; other errors are terminal.
         * Applicable failures include ACCESS_DENIED, IO_ERROR, STALE, and CANCELLED; NOT_HANDLED
         * and BUSY are invalid payload completions. Snapshot consumers try mapping before
         * positioned reads. Forward-only sources can materialize once here, including for
         * SIZE_UNKNOWN, but read_async must still honor independent offsets.
         * The caller retains request inputs through completion and return of submission/cancel.
         * For ACCEPTED, retain done/user_data until the one completion, including cancellation.
         * Do not access user_data after invoking done. For RETRY or REJECTED, retain no operation
         * arguments and invoke no completion. Submission must not block waiting for payload I/O.
         *
         * @param context Registered provider context, possibly NULL for a stateless provider. Borrowed, never freed here.
         * @param request Opaque caller-owned operation identity used by cancel(); do not dereference or free it.
         * @param resource Live pin handle owned by this provider, retained by the caller through completion.
         * @param offset Absolute byte offset from the start of the pinned resource.
         * @param size Maximum byte count, or OVRTX_DATA_SIZE_UNKNOWN to map through EOF.
         * @param options Borrowed request options; NULL means defaults. Unknown hints are ignored; pin_flags must be zero.
         * @param done Non-NULL completion function; invoke exactly once if submission returns ACCEPTED.
         * @param user_data Opaque caller-owned completion context; pass unchanged to done and do not use afterward.
         * @return
         * - **OVRTX_DATA_ACCEPTED**: exactly one completion is owed, possibly inline before this call returns.
         * - **OVRTX_DATA_RETRY**: temporary submission backpressure; no completion or retained callback state. The caller may resubmit.
         * - **OVRTX_DATA_REJECTED**: submission refused; no completion or retained callback state. This is not a routing decline.
         */
        ovrtx_data_submit_t (*map_async)(ovrtx_data_provider_context_t* context,
                                         ovrtx_data_request_t* request,
                                         ovrtx_data_resource_handle_t* resource,
                                           uint64_t offset,
                                           uint64_t size,
                                         const ovrtx_data_request_options_t* options,
                                         ovrtx_data_map_done_t done,
                                         void* user_data);
        /**
         * Release one byte-view lease returned by a successful map_async() completion.
         *
         * Required exactly when map_async is provided. Call exactly once per successful map,
         * including empty views, using the same provider context and resource pin. The caller
         * must finish all reads before releasing. The borrowed data and lease become invalid
         * when released; do not modify or free the data separately. Other maps retain their own
         * leases even when backing storage is shared. This does not unpin the resource: release
         * all maps before unpin(), and keep the pin live throughout this call.
         * This synchronous, nonblocking release has no error channel. NULL, foreign, or already
         * released leases violate the calling contract; callers must not rely on validation or
         * idempotent release. No completion callback is invoked.
         *
         * @param context Registered provider context, possibly NULL for a stateless provider. Borrowed, never freed here.
         * @param resource Live pin handle used by the matching map_async() operation; borrowed for this call.
         * @param lease Non-NULL, unreleased provider-owned lease from that map, consumed by this call.
         * @return
         * - No value. The map lease is released when the call returns.
         */
        void (*release_map)(ovrtx_data_provider_context_t* context, ovrtx_data_resource_handle_t* resource, void* lease);
    } ovrtx_data_provider_vtable_t;

    /** Provider implementation instance. Registration copies this pair; it borrows
     * the immutable vtable and context until successful unregister or shutdown. */
    typedef struct ovrtx_data_provider_t
    {
        const ovrtx_data_provider_vtable_t* vtable; /**< Non-NULL, immutable and live through removal/shutdown. */
        ovrtx_data_provider_context_t* context; /**< Application-owned state; may be NULL for stateless providers. */
    } ovrtx_data_provider_t;

    /** @} */

#ifdef __cplusplus
}
#endif

/** @addtogroup ovrtx_data_provider
 * Typed zero sentinels; copying a handle never acquires ownership.
 *
 * @{
 */
#ifdef __cplusplus
/** Invalid value for @ref ovrtx_data_provider_id_t. */
#define OVRTX_INVALID_DATA_PROVIDER_ID ovrtx_data_provider_id_t{0}
#else
/** Invalid value for @ref ovrtx_data_provider_id_t. */
#define OVRTX_INVALID_DATA_PROVIDER_ID ((ovrtx_data_provider_id_t){0})
#endif
/** @} */

#ifdef __cplusplus
extern "C++"
{
OVX_DEFINE_HANDLE_CPP_OPERATORS(ovrtx_data_array_lease_id_t)
OVX_DEFINE_HANDLE_CPP_OPERATORS(ovrtx_data_provider_id_t)
}
#endif
