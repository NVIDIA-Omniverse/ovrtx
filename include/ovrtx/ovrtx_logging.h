/* Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
 *
 * NVIDIA CORPORATION and its licensors retain all intellectual property
 * and proprietary rights in and to this software, related documentation
 * and any modifications thereto.  Any use, reproduction, disclosure or
 * distribution of this software and related documentation without an express
 * license agreement from NVIDIA CORPORATION is strictly prohibited.
 */

#ifndef OVRTX_LOGGING_H
#define OVRTX_LOGGING_H

#include <ovx/logging_types.h>
#include <ovrtx/ovrtx_types.h>


#ifdef __cplusplus
extern "C"
{
#endif

/** Default log level for the ovrtx library.  This value should be defined on
 *  a per-library basis so that each can potentially set its own unique default
 *  log severity level.
 */
#define OVRTX_LOG_DEFAULT OVX_LOG_WARNING


    /*--------------------------------------------------*/
    /* Logging callback */
    /*--------------------------------------------------*/

    /**
     * Set a process-global callback that receives every log message produced
     * by the ovrtx library (and by any plugin or framework code loaded under it).
     *
     * The callback is shared across the whole process, not per-renderer or
     * component: its lifetime follows the ovrtx system, not any particular
     * component instance.
     *
     * Only one callback can be active at a time; calling this function replaces
     * the previous callback. Pass NULL as @p callback to disable delivery.
     *
     * Lifetime: The caller retains ownership of @p user_data. Keep it and the
     * callback function valid until a successful call to this function disables
     * or replaces the callback, or until system shutdown completes. Disabling or
     * replacing the callback waits for any active invocations to finish; after
     * the call returns successfully, the previous context may be freed. Destroying
     * a renderer can trigger system shutdown if it releases the final reference
     * (for example, after implicit initialization). A final ovrtx_shutdown() can
     * return before shutdown completes if an API call still holds a loader
     * reference. Keep the callback and context valid until all in-flight API
     * calls return and system shutdown completes.
     *
     * Do not call this function from inside the log callback: it waits for the
     * active invocation to finish and would deadlock.
     *
     * Calling this function before ov*_initialize() or after ov*_shutdown()
     * returns OV*_API_ERROR with a descriptive error string accessible via
     * ov*_get_last_error().
     *
     * The callback does NOT carry per-renderer attribution. ovrtx may add a v2
     * callback type with (renderer, op_id) once per-op TLS plumbing exists.
     *
     * @note Thread safety: The callback may be invoked from any thread.  The callbacks
     *       will occur on the thread that originally emits the log message.
     *       Multiple callbacks may be performed concurrently on multiple
     *       threads.  The callback implementation must be thread safe with
     *       the resources that it touches.
     *
     * Callback implementations should perform their work as quickly as possible and
     * return.  Since the callbacks are performed on the thread that generates the
     * log message, any long-running callbacks could affect the performance of the
     * library.
     *
     * Channel filter syntax
     * ---------------------
     * @p channel_filter is a comma-separated list of `<channel_prefix>=<level>`
     * entries (RUST_LOG-style). The channel prefix is matched against carb's
     * dotted source name; longest matching prefix wins. Per-channel rules
     * override @p severity for matched channels. Channels not matched by any
     * rule use @p severity as their threshold. The empty / NULL filter is
     * equivalent to "every channel uses @p severity".  Wildcard characters are
     * not supported in the channel prefix strings.
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
     *   - `"carb=warn,carb.tasking=verbose"`       carb.tasking uses verbose, other carb.* uses warn,
     *                                              everything else uses @p severity
     *
     * @param severity Default severity threshold applied to channels not
     *                 matched by an explicit rule in @p channel_filter. Use
     *                 OVX_LOG_INFO to receive INFO and above by default;
     *                 OVX_LOG_ERROR to filter out everything but errors by
     *                 default.
     * @param channel_filter Optional comma-separated `<channel>=<level>` list.
     *                       Pass NULL to apply @p severity uniformly.
     *                       The filter is parsed during this call; its storage
     *                       need only remain valid until this function returns.
     * @param callback Callback function to receive log messages, or NULL to disable
     * @param user_data Caller-owned context passed to each callback invocation.
     *                  Must remain valid until the callback is successfully
     *                  disabled or replaced, or system shutdown completes.
     * @return OVRTX_API_SUCCESS if callback was set successfully,
     *         OVRTX_API_ERROR if the system is not initialized or the filter
     *         string failed to parse.
     */
    ovrtx_result_t ovrtx_set_log_callback(ovx_log_severity_t severity,
        const ovx_string_t* channel_filter,
        ovx_log_callback_t callback,
        void* user_data);

    /**
     * Flush all pending log messages through the global callback.
     *
     * This operation blocks until all log messages that are pending a callback
     * up to this point have been delivered through the log callback. This is
     * useful when you need to ensure all logs have been processed before
     * proceeding (e.g., after an operation completes or fails, or before tearing
     * the system down).
     *
     * If no log callback is set, this function returns immediately with success.
     *
     * Calling this function before ovrtx_initialize or after ovrtx_shutdown
     * returns OVRTX_API_ERROR.
     *
     * Note: This only flushes messages generated before this call. Messages
     *       generated concurrently or after this call may not be included.
     *
     * @param timeout Maximum time in nanoseconds to wait for flush to complete.
     * @return OVRTX_API_SUCCESS if all pending logs were flushed,
     *         OVRTX_API_TIMEOUT if flush did not complete within timeout,
     *         OVRTX_API_ERROR if flush failed (system not initialized), or
     *         OVRTX_API_ERROR if this is called from within a callback function.
     */
    ovrtx_result_t ovrtx_flush_log(ovrtx_timeout_t timeout);

    /*--------------------------------------------------*/


#ifdef __cplusplus
}
#endif

#endif /* OVRTX_LOGGING_H */
