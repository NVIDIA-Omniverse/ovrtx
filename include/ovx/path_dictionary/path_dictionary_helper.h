/* Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
 *
 * NVIDIA CORPORATION and its licensors retain all intellectual property
 * and proprietary rights in and to this software, related documentation
 * and any modifications thereto.  Any use, reproduction, disclosure or
 * distribution of this software and related documentation without an express
 * license agreement from NVIDIA CORPORATION is strictly prohibited.
 */

#ifndef PATH_DICTIONARY_HELPER_H
#define PATH_DICTIONARY_HELPER_H

#include "path_dictionary_types.h"
#include <stdbool.h>
#include <stddef.h>
#include <string.h>

static inline bool ovx_string_contains_embedded_nul(const ovx_string_t* string)
{
    return string && string->ptr && memchr(string->ptr, '\0', string->length) != NULL;
}

static inline bool ovx_string_has_null_data(const ovx_string_t* string)
{
    return string && !string->ptr && string->length != 0;
}

#endif /* PATH_DICTIONARY_HELPER_H */
