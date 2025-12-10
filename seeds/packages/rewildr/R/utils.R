#' Null Coalescing Operator
#'
#' @param a First value
#' @param b Default value if a is NULL
#' @return a if not NULL, otherwise b
#' @export
`%||%` <- function(a, b) if (is.null(a)) b else a

#' Safely Read Vector Data
#'
#' Reads spatial vector data with error handling.
#'
#' @param path Path to file
#' @param warnings Warnings collector
#' @return sf object
#' @export
safe_read_sf <- function(path, warnings = NULL) {
 tryCatch(
   sf::read_sf(path),
   error = function(e) {
     primitive_failure(
       error = "Failed to read vector data",
       message = sprintf("Path: %s\nError: %s", path, e$message),
       warnings = warnings
     )
   }
 )
}

#' Safely Read Raster Data
#'
#' Reads raster data with error handling.
#'
#' @param path Path to file
#' @param warnings Warnings collector
#' @return SpatRaster object
#' @export
safe_read_rast <- function(path, warnings = NULL) {
 tryCatch(
   terra::rast(path),
   error = function(e) {
     primitive_failure(
       error = "Failed to read raster data",
       message = sprintf("Path: %s\nError: %s", path, e$message),
       warnings = warnings
     )
   }
 )
}

#' Safely Write Vector Data
#'
#' Writes spatial vector data with error handling.
#'
#' @param obj sf object
#' @param path Output path
#' @param warnings Warnings collector
#' @export
safe_write_sf <- function(obj, path, warnings = NULL) {
 
 # Ensure directory exists
 dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
 
 tryCatch(
   sf::write_sf(obj, path),
   error = function(e) {
     primitive_failure(
       error = "Failed to write vector data",
       message = sprintf("Path: %s\nError: %s", path, e$message),
       warnings = warnings
     )
   }
 )
}

#' Safely Write Raster Data
#'
#' Writes raster data with error handling.
#'
#' @param obj SpatRaster object
#' @param path Output path
#' @param warnings Warnings collector
#' @export
safe_write_rast <- function(obj, path, warnings = NULL) {
 
 # Ensure directory exists
 dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
 
 tryCatch(
   terra::writeRaster(obj, path, overwrite = TRUE),
   error = function(e) {
     primitive_failure(
       error = "Failed to write raster data",
       message = sprintf("Path: %s\nError: %s", path, e$message),
       warnings = warnings
     )
   }
 )
}
