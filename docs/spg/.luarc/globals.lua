---@meta

--- SPG sandbox global functions
--- This file provides type annotations for IDE IntelliSense only; it is NOT executed at runtime.

--- Log an info-level message to the SPG logger.
---@param msg string
function info(msg) end

--- Log a warning-level message to the SPG logger.
---@param msg string
function warning(msg) end

--- Print values to the SPG log (info level). Concatenates all arguments with tabs.
---@param ... any
function print(...) end

--- Assert a condition. Throws an SPG error if the condition is false.
---@param condition boolean
---@param msg? string  Optional error message
---@return boolean     Returns true if assertion passed
function assert(condition, msg) end
