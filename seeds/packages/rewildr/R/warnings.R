#' Create a Warnings Collector
#'
#' Creates a mutable warnings list that can accumulate warnings
#' throughout primitive execution. Each warning carries a level,
#' the primitive that generated it, and a human-readable message.
#'
#' @param primitive Name of the primitive using this collector.
#'   If provided, it becomes the default for all warnings added
#'   via the shorthand methods (info/warn/critical). Can be
#'   overridden per-warning via the `add` method.
#' @return A warnings collector (list with functions)
#' @export
#' @examples
#' w <- warnings_collector("validate_raster")
#' w$info("CRS is EPSG:4326")
#' w$warn("14 geometries invalid")
#' w$critical("40% NoData in study area")
#' w$get()
warnings_collector <- function(primitive = NULL) {

  warnings <- list()

  list(
    #' Add a warning with explicit level, primitive, and message.
    #' This is the full-control method. The shorthand methods
    #' (info/warn/critical) call this internally.
    add = function(level, primitive_name, message) {
      if (!level %in% c("info", "warning", "critical")) {
        stop("Warning level must be 'info', 'warning', or 'critical'")
      }
      warnings <<- append(warnings, list(
        list(
          level = level,
          primitive = primitive_name,
          message = message
        )
      ))
      invisible(NULL)
    },

    #' Add an info-level warning using the default primitive name.
    info = function(message) {
      if (is.null(primitive)) {
        stop("No default primitive set. Use add(level, primitive, message) or pass primitive to warnings_collector().")
      }
      warnings <<- append(warnings, list(
        list(level = "info", primitive = primitive, message = message)
      ))
      invisible(NULL)
    },

    #' Add a warning-level warning using the default primitive name.
    warn = function(message) {
      if (is.null(primitive)) {
        stop("No default primitive set. Use add(level, primitive, message) or pass primitive to warnings_collector().")
      }
      warnings <<- append(warnings, list(
        list(level = "warning", primitive = primitive, message = message)
      ))
      invisible(NULL)
    },

    #' Add a critical-level warning using the default primitive name.
    critical = function(message) {
      if (is.null(primitive)) {
        stop("No default primitive set. Use add(level, primitive, message) or pass primitive to warnings_collector().")
      }
      warnings <<- append(warnings, list(
        list(level = "critical", primitive = primitive, message = message)
      ))
      invisible(NULL)
    },

    #' Get all accumulated warnings as a list.
    get = function() {
      warnings
    },

    #' Check if any warnings have been added.
    has_warnings = function() {
      length(warnings) > 0
    },

    #' Check if any critical warnings exist.
    has_critical = function() {
      any(sapply(warnings, function(w) w$level == "critical"))
    },

    #' Count warnings, optionally filtered by level.
    count = function(level = NULL) {
      if (is.null(level)) {
        length(warnings)
      } else {
        sum(sapply(warnings, function(w) w$level == level))
      }
    }
  )
}