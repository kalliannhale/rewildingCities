#' Report Primitive Success
#'
#' Outputs metadata as JSON to stdout and exits successfully.
#' Call this at the end of a successful primitive execution.
#'
#' @param metadata List of metadata fields
#' @param warnings Warnings collector or list of warnings
#' @export
primitive_success <- function(metadata, warnings = NULL) {
 
 # Extract warnings if collector
 if (is.list(warnings) && !is.null(warnings$get)) {
   warnings <- warnings$get()
 }
 
 output <- metadata
 output$warnings <- warnings %||% list()
 output$status <- "success"
 
 cat(jsonlite::toJSON(output, auto_unbox = TRUE, pretty = FALSE))
 quit(status = 0, save = "no")
}

#' Report Primitive Failure
#'
#' Outputs error as JSON to stdout and exits with error code.
#' Call this when the primitive cannot complete.
#'
#' @param error Short error type
#' @param message Detailed error message
#' @param warnings Optional warnings collector or list
#' @export
primitive_failure <- function(error, message, warnings = NULL) {
 
 # Extract warnings if collector
 if (is.list(warnings) && !is.null(warnings$get)) {
   warnings <- warnings$get()
 }
 
 output <- list(
   status = "failure",
   error = error,
   message = message,
   warnings = warnings %||% list()
 )
 
 cat(jsonlite::toJSON(output, auto_unbox = TRUE, pretty = FALSE))
 quit(status = 1, save = "no")
}

#' Wrap Primitive Execution
#'
#' Wraps primitive logic with standard error handling.
#' Catches errors and formats them consistently.
#'
#' @param expr Expression to evaluate
#' @param warnings Warnings collector to include on failure
#' @export
with_primitive_error_handling <- function(expr, warnings = NULL) {
 tryCatch(
   expr,
   error = function(e) {
     primitive_failure(
       error = "Execution error",
       message = conditionMessage(e),
       warnings = warnings
     )
   }
 )
}
