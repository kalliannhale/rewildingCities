#' Create a Warnings Collector
#'
#' Creates a mutable warnings list that can accumulate warnings
#' throughout primitive execution.
#'
#' @return A warnings collector (list with functions)
#' @export
#' @examples
#' w <- warnings_collector()
#' w$add("info", "CRS was transformed")
#' w$warn("3 features excluded")
#' w$get()
warnings_collector <- function() {
 
  warnings <- list()
 
  list(
    add = function(level, message) {
      if (!level %in% c("info", "warning", "critical")) {
        stop("Warning level must be 'info', 'warning', or 'critical'")
      }
      warnings <<- append(warnings, list(
        list(level = level, message = message)
      ))
      invisible(NULL)
    },
   
    info = function(message) {
      warnings <<- append(warnings, list(
        list(level = "info", message = message)
      ))
      invisible(NULL)
    },
   
    warn = function(message) {
      warnings <<- append(warnings, list(
        list(level = "warning", message = message)
      ))
      invisible(NULL)
    },
   
    critical = function(message) {
      warnings <<- append(warnings, list(
        list(level = "critical", message = message)
      ))
      invisible(NULL)
    },
   
    get = function() {
      warnings
    },
   
    has_warnings = function() {
      length(warnings) > 0
    },
   
    has_critical = function() {
      any(sapply(warnings, function(w) w$level == "critical"))
    },
   
    count = function(level = NULL) {
      if (is.null(level)) {
        length(warnings)
      } else {
        sum(sapply(warnings, function(w) w$level == level))
      }
    }
  )
}