/* Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
 *
 * NVIDIA CORPORATION and its licensors retain all intellectual property
 * and proprietary rights in and to this software, related documentation
 * and any modifications thereto.  Any use, reproduction, disclosure or
 * distribution of this software and related documentation without an express
 * license agreement from NVIDIA CORPORATION is strictly prohibited.
 */

#ifndef PATH_DICTIONARY_INTERFACE_H
#define PATH_DICTIONARY_INTERFACE_H

#include "path_dictionary_types.h"

#ifdef __cplusplus
extern "C"
{
#endif

    /*
     * Path dictionary interface
     * =========================
     *
     * What the dictionary does
     * ------------------------
     * The dictionary interns three kinds of values so cooperating systems can
     * share opaque 64-bit handles instead of marshalling strings:
     *   - tokens          (ovx_token_t)         : interned strings
     *   - prim paths      (ovx_primpath_t)      : interned sequences of tokens
     *   - prim path lists (ovx_primpath_list_t) : ordered sets of prim paths
     *
     * The only public operations on these handles are the vtable slots below
     * (plus the inline wrappers in path_dictionary_utils.h).
     *
     * Owner / dictionary lifetime
     * ---------------------------
     * A `path_dictionary_instance_t*` is produced by some owner subsystem.
     * For example, for ovstage the owner is `ovstage_instance_t`; see
     * `ovstage_api.h::get_path_dictionary` for the concrete contract. Callers
     * MUST NOT free `vtable` / `context` — the owner does that. When the
     * owner reports the dictionary is gone, every handle previously minted
     * through it is invalidated simultaneously. There is no per-handle
     * liveness query.
     *
     * Handle lifetime regimes
     * -----------------------
     * Two distinct regimes coexist:
     *
     *   Tokens and prim paths  : dict-lifetime, no per-handle release.
     *     They are deduplicated/interned — equal strings yield equal
     *     ovx_token_t and equal token sequences yield equal ovx_primpath_t.
     *     They remain valid for the entire lifetime of the dictionary and
     *     become invalid all at once when the dictionary is destroyed.
     *
     *   Path lists             : explicitly refcounted.
     *     `create_path_list_from_*` returns a fresh handle with one
     *     reference owned by the caller. `add_path_list_reference`
     *     increments; `release_path_list_reference` decrements and erases
     *     storage at zero. Each `create_*` and each `add_*` MUST be paired
     *     with exactly one `release_*`.
     *
     * Borrow vs ownership in result structs
     * -------------------------------------
     * When path-list handles appear inside result structs from owner APIs
     * (e.g. `ovstage_read_group_t::prims.list`), they are *borrows*: the
     * producing op already holds a reference and will release it when the
     * producing handle is released. Consumers who need the list to outlive
     * the producing handle MUST call `add_path_list_reference` before
     * releasing the producing handle, and pair that with their own
     * `release_path_list_reference` when done. Tokens and prim paths
     * returned in result structs need no pinning — they survive as long as
     * the dictionary itself.
     *
     * Strings returned by `get_strings_from_tokens` point into dict-owned
     * storage; they are valid for the dictionary's lifetime and must NOT be
     * freed by the caller. Error strings inside `ovx_api_result_t` are
     * different — those are paired with `release_error`.
     *
     * Thread safety
     * -------------
     * Every vtable slot is callable from any thread; implementations
     * serialize internally. Concurrent `add_*` / `release_*` on the same
     * handle is well-defined provided the caller's overall bookkeeping is
     * consistent (e.g. the caller does not call `release_*` more times than
     * it owns references).
     *
     * Sentinel handling
     * -----------------
     * `OVX_INVALID_TOKEN`, `OVX_INVALID_PRIMPATH`, `OVX_INVALID_PRIMPATH_LIST`
     * are never produced on success by any `create_*` slot.
     * `add_path_list_reference` and `release_path_list_reference` accept
     * `OVX_INVALID_PRIMPATH_LIST` as a no-op `OVX_API_SUCCESS`. An unknown
     * (e.g. already-released) non-zero handle returns `OVX_API_ERROR`.
     */
    typedef struct path_dictionary_vtable_t
    {
        /* Intern `num_strings` strings as tokens. Output handles are
           dict-lifetime — no per-handle release. Equal input strings yield
           equal output tokens. Empty input strings and strings containing
           embedded NUL bytes are rejected with `OVX_API_ERROR`. */
        ovx_api_result_t (*create_tokens_from_strings)(path_dictionary_context_t* instance,
                                            const ovx_string_t* strings,
                                            size_t num_strings, 
                                            ovx_token_t* out_tokens);

        /* Intern prim paths described as concatenated token arrays. Output
           handles are dict-lifetime. Equal token sequences yield equal output
           paths. The input tokens must have been minted from this dictionary. */
        ovx_api_result_t (*create_paths_from_tokens)(path_dictionary_context_t* instance,
                                            const ovx_token_t* tokens_per_path,
                                            const size_t* num_tokens_per_path, 
                                            size_t num_paths, 
                                            ovx_primpath_t* out_prim_paths);

        /* Intern prim paths described as strings. Output handles are
           dict-lifetime. Equivalent paths yield equal output handles. Empty
           strings and strings containing embedded NUL bytes are rejected with
           `OVX_API_ERROR`. */
        ovx_api_result_t (*create_paths_from_strings)(path_dictionary_context_t* instance,
                                            const ovx_string_t* path_strings,
                                            size_t num_paths, 
                                            ovx_primpath_t* out_prim_paths);

        /* Create a fresh prim-path list from an array of prim path handles.
           The returned `*out_path_list` carries refcount=1 owned by the
           caller, which MUST be released exactly once via
           `release_path_list_reference` (or transferred into a holder that
           will). Identical inputs do NOT deduplicate to the same handle —
           every successful call mints a new list. `num_paths` may be zero to
           mint a valid empty list; in that case `paths` may be NULL. */
        ovx_api_result_t (*create_path_list_from_paths)(path_dictionary_context_t* instance,
                                                const ovx_primpath_t* paths,
                                                size_t num_paths, 
                                                ovx_primpath_list_t* out_path_list);

        /* Same as `create_path_list_from_paths` but takes strings; the
           strings are interned as paths first. Returns refcount=1 to the
           caller; same release contract. `num_paths` may be zero to mint a valid
           empty list; in that case `path_strings` may be NULL. Empty strings and
           strings containing embedded NUL bytes are rejected with `OVX_API_ERROR`. */
        ovx_api_result_t (*create_path_list_from_strings)(path_dictionary_context_t* instance,
                                                const ovx_string_t* path_strings,
                                                size_t num_paths,
                                                ovx_primpath_list_t* out_path_list);

        /* Increment the reference count on an existing path list. Each
           successful add MUST be paired with one `release_path_list_reference`.
           `OVX_INVALID_PRIMPATH_LIST` is a no-op `OVX_API_SUCCESS`. An
           unknown (e.g. already-released) handle returns `OVX_API_ERROR`. */
        ovx_api_result_t (*add_path_list_reference)(path_dictionary_context_t* instance,
                                    ovx_primpath_list_t path_list);

        /* Decrement the reference count on a path list. Erases the entry and
           invalidates the handle when the count reaches zero. After erasure
           the handle is unknown and subsequent operations return
           `OVX_API_ERROR`. `OVX_INVALID_PRIMPATH_LIST` is a no-op
           `OVX_API_SUCCESS`. Replaces the legacy `destroy_path_list` slot. */
        ovx_api_result_t (*release_path_list_reference)(path_dictionary_context_t* instance,
                                    ovx_primpath_list_t path_list);

        /* Resolve tokens to strings. Each `out_strings[i].ptr` references
           dict-owned storage and is valid for the dictionary's lifetime; do
           NOT free. */
        ovx_api_result_t (*get_strings_from_tokens)(path_dictionary_context_t* instance,
                                        const ovx_token_t* tokens,
                                        size_t num_tokens,
                                        ovx_string_t* out_strings);

        /* Decompose prim paths into token arrays into a caller-supplied
           `token_buffer`. Returns how many paths fit in the buffer via
           `out_num_paths_processed` (callers retry with a bigger buffer if
           short). The token handles themselves are dict-lifetime; the
           per-path pointers in `out_tokens_per_path` index into
           `token_buffer` and are valid for as long as the buffer is. */
        ovx_api_result_t (*get_tokens_from_paths)(path_dictionary_context_t* instance,
                                        const ovx_primpath_t* prim_paths,
                                        size_t num_paths,
                                        ovx_token_t* token_buffer,
                                        size_t token_buffer_size,
                                        ovx_token_t** out_tokens_per_path,
                                        size_t* out_num_tokens_per_path,
                                        size_t* out_num_paths_processed);


        /* Number of paths in a path list. The caller must currently hold at
           least one reference on `path_list`; a released (unknown) handle
           returns `OVX_API_ERROR`. */
        ovx_api_result_t (*get_num_paths_from_path_list)(path_dictionary_context_t* instance,
                                            ovx_primpath_list_t path_list,
                                            size_t* out_num_paths);

        /* Read up to `max_paths` entries from a path list starting at
           `start_offset`. The returned `ovx_primpath_t` values are
           dict-lifetime and remain valid independently of the list's
           refcount. The caller must currently hold at least one reference on
           `path_list`; released handles return `OVX_API_ERROR`. */
        ovx_api_result_t (*get_paths_from_path_list)(path_dictionary_context_t* instance,
                                            ovx_primpath_list_t path_list,
                                            size_t start_offset,
                                            size_t max_paths,
                                            ovx_primpath_t* out_paths,
                                            size_t* out_num_paths);

        /* Release the string buffer attached to an `ovx_api_result_t::error`.
           Do NOT call on strings returned by `get_strings_from_tokens`
           (those reference dict-owned storage). */
        void (*release_error)(path_dictionary_context_t* context, 
                                ovx_string_t error);

    } path_dictionary_vtable_t;

#ifdef __cplusplus
}
#endif

#include "path_dictionary_utils.h"

#endif /* PATH_DICTIONARY_INTERFACE_H */
