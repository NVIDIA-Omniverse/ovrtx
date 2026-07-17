/* Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
 *
 * NVIDIA CORPORATION and its licensors retain all intellectual property
 * and proprietary rights in and to this software, related documentation
 * and any modifications thereto.  Any use, reproduction, disclosure or
 * distribution of this software and related documentation without an express
 * license agreement from NVIDIA CORPORATION is strictly prohibited.
 */

#ifndef PATH_DICTIONARY_TYPES_H
#define PATH_DICTIONARY_TYPES_H

#include <stdint.h>
#include "../types.h"

#ifdef __cplusplus
extern "C"
{
#endif

    typedef struct path_dictionary_context_t path_dictionary_context_t;

    /* Path dictionary vtable for managing tokens, paths and path lists */
    typedef struct path_dictionary_vtable_t path_dictionary_vtable_t;

    /*
     * Path dictionary instance bundle.
     *
     * `vtable` is owned and populated by the owner subsystem (e.g. ovstage);
     * callers MUST NOT free it.
     *
     * `context` is opaque implementation state. Its lifetime equals the
     * dictionary's lifetime, which is in turn fixed by the owner's contract
     * (see e.g. `ovstage_api.h::get_path_dictionary`). When the dictionary
     * is destroyed, every token, prim path and outstanding path-list
     * reference minted through it is invalidated simultaneously.
     */
    typedef struct path_dictionary_instance_t
    {
        path_dictionary_vtable_t* vtable;
        path_dictionary_context_t* context; /**< Implementation-specific data */
    } path_dictionary_instance_t;

#ifdef __cplusplus
}
#endif

#endif /* PATH_DICTIONARY_TYPES_H */

