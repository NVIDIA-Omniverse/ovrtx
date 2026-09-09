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
 * The only public operations on these handles are the vtable slots in
 * path_dictionary_vtable.h (plus the inline wrappers in
 * path_dictionary_utils.h).
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

#include "path_dictionary_vtable.h"
#include "path_dictionary_utils.h"

#endif /* PATH_DICTIONARY_INTERFACE_H */
