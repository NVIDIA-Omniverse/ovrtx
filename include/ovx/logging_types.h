/* Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
 *
 * NVIDIA CORPORATION and its licensors retain all intellectual property
 * and proprietary rights in and to this software, related documentation
 * and any modifications thereto.  Any use, reproduction, disclosure or
 * distribution of this software and related documentation without an express
 * license agreement from NVIDIA CORPORATION is strictly prohibited.
 */

#ifndef OVX_LOGGING_TYPES_H
#define OVX_LOGGING_TYPES_H

#include "types.h"

#include <stdint.h>


#ifdef __cplusplus
extern "C"
{
#endif

    /** @defgroup ovx_log_types Logging types
     *  @{
     */

     /**
      * Log severity levels for operation messages.
      */
    typedef enum ovx_log_severity_t
    {
        OVX_LOG_VERBOSE = -2, /**< Verbose/debug message */
        OVX_LOG_INFO = -1,    /**< Informational message */
        OVX_LOG_WARNING = 0,  /**< Warning (operation continues) */
        OVX_LOG_ERROR = 1,    /**< Error (operation may have failed) */
        OVX_LOG_FATAL = 2,    /**< Fatal error (operation may have failed) */
    } ovx_log_severity_t;

     /**
      * Metadata associated with a log message emitted by the runtime.
      *
      * This struct is passed to the log callback for each message, providing
      * rich contextual information to aid in debugging and analysis.  Note that
      * all of the strings in this object are only value for the duration of the
      * log callback call.  If they need to be stored or queued for later use,
      * they must be copied during the callback.
      */
    typedef struct ovx_log_message_t
    {
        /** The size of this object in bytes.  This is used as a versioning method for this
         *  struct and can be used to verify whether specific fields are valid.  This is
         *  used by checking if the byte offset of a given field is less than this value.
         *  If the offset is larger than or equal to this value, it is not safe to access
         *  that field.  When this happens, it means that the object came from an earlier
         *  version of this struct.
         *
         *  All fields up to and including `message` may be assumed to always be present and
         *  valid.  Any fields after `message` must have their offset checked against this
         *  value to determine if they are valid or not.
         */
        size_t thisSize;

        /** Severity level of the message.  This will be one of the `OVX_LOG_*` log
         *  severity names.
         */
        ovx_log_severity_t severity;

        /** The name of the OV library that is emitting this log message.  This will be constant
         *  for all log messages emitted by a given OV library for the lifetime of the library.
         */
        ovx_string_t libraryName;

        /** The log channel name that this log message was emitted against.  This channel
         *  name will be present and non-empty for all log messages.
         */
        ovx_string_t channel;

        /** Wall-clock time in nanoseconds since the Unix epoch of midnight January 1, 1970.
         *  Note that this value may be subject to wall-clock adjustments (e.g. NTP) and
         *  should not be used for precise timing measurements; use @ref elapsedTimeNs
         *  instead for that purpose.
         */
        uint64_t timestampNs;

        /** Elapsed time in nanoseconds since the start of the process.  This time value
         *  is derived from the steady clock and will not be subject to wall-clock
         *  adjustments.  The epoch of this timestamp should be considered arbitrary and
         *  should only be used for relative timing measurements.
         */
        uint64_t elapsedTimeNs;

        /** Source file path where the log message was generated. */
        ovx_string_t filePath;

        /** Source line number where the log message was generated. */
        uint32_t lineNumber;

        /** Source function name where the log message was generated. */
        ovx_string_t functionName;

        /** System specific ID of the process that generated the log message. */
        uint32_t processId;

        /** System specific ID of the thread that generated the log message. */
        uint32_t threadId;

        /** Monotonically increasing sequence number for ordering messages.  This value can
         *  be used to reorder a log postmortem if messages are received or stored out of
         *  order.
         */
        uint64_t sequenceNumber;

        /** The log message text (UTF-8 string) itself. */
        ovx_string_t message;
    } ovx_log_message_t;

    /**
     * Callback function type for receiving log messages.
     *
     * The callback is process-global and may be invoked from any thread.  If the host app
     * uses the same callback function for multiple OV libraries, it must protect access to
     * any resources used inside the callback function since it may be called concurrently
     * from multiple threads.
     *
     * The strings passed in the message data are only valid for the duration of
     * the callback.  If the message needs to be retained, copy it before returning.
     *
     * @param[in] message   The log message and associated metadata.  All string
     *                      fields are only valid during the callback.
     * @param[in] user_data User-provided context from ovrtx_set_log_callback
     */
    typedef void (*ovx_log_callback_t)(const ovx_log_message_t* message,
        void* user_data);

    /** @} */ // end of ovx_log_types


#ifdef __cplusplus
}
#endif
#endif /* OVX_LOGGING_TYPES_H */
