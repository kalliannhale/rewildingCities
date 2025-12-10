#' Parse Primitive Arguments
#'
#' Standard argument parsing for rewildingCities primitives.
#' Expects: <inputs_json_or_path> <output_path> <params_json_or_path>
#'
#' @param args Character vector of command line arguments. 
#'   If NULL, reads from commandArgs(trailingOnly = TRUE).
#' @return A list with `inputs`, `output`, and `params`.
#' @export
parse_primitive_args <- function(args = NULL) {
 
 if (is.null(args)) {
   args <- commandArgs(trailingOnly = TRUE)
 }
 
 if (length(args) < 3) {
   primitive_failure(
     error = "Invalid arguments",
     message = "Usage: primitive.R <inputs_json> <output_path> <params_json>"
   )
 }
 
 inputs_arg <- args[1]
 output_path <- args[2]
 params_arg <- args[3]
 
 # Parse inputs - could be JSON string or file path
 inputs <- parse_json_arg(inputs_arg, "inputs")
 
 # Parse params - could be JSON string or file path
 params <- parse_json_arg(params_arg, "params")
 
 list(
   inputs = inputs,
   output = output_path,
   params = params
 )
}

#' Parse a JSON Argument
#'
#' Handles both inline JSON strings and file paths.
#'
#' @param arg The argument string
#' @param name Name for error messages
#' @return Parsed list
#' @keywords internal
parse_json_arg <- function(arg, name) {
 
 # Check if it's a file path
 if (file.exists(arg)) {
   tryCatch(
     jsonlite::read_json(arg),
     error = function(e) {
       primitive_failure(
         error = sprintf("Failed to parse %s file", name),
         message = e$message
       )
     }
   )
 } else {
   # Try to parse as inline JSON
   tryCatch(
     jsonlite::fromJSON(arg, simplifyVector = TRUE),
     error = function(e) {
       primitive_failure(
         error = sprintf("Failed to parse %s JSON", name),
         message = e$message
       )
     }
   )
 }
}

#' Get Input Path by Name
#'
#' Convenience function to extract a named input path.
#'
#' @param inputs The inputs list from parse_primitive_args()
#' @param name The input name
#' @param required If TRUE, fails if input is missing
#' @return The file path string
#' @export
get_input <- function(inputs, name, required = TRUE) {
 
 path <- inputs[[name]]
 
 if (is.null(path)) {
   if (required) {
     primitive_failure(
       error = "Missing required input",
       message = sprintf("Input '%s' is required but not provided", name)
     )
   }
   return(NULL)
 }
 
 if (!file.exists(path)) {
   primitive_failure(
     error = "Input file not found",
     message = sprintf("Input '%s' path does not exist: %s", name, path)
   )
 }
 
 path
}

#' Get Parameter with Default
#'
#' @param params The params list from parse_primitive_args()
#' @param name The parameter name
#' @param default Default value if not provided
#' @return The parameter value
#' @export
get_param <- function(params, name, default = NULL) {
 params[[name]] %||% default
}

#' Null coalescing operator
#' @keywords internal
`%||%` <- function(a, b) if (is.null(a)) b else a
