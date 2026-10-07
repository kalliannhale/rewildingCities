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
   sf::write_sf(obj, path, delete_dsn = TRUE),
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

# ═══════════════════════════════════════════════════════════════════════════════
# TABULAR I/O
#
# Vector and raster each had a safe reader and writer; tabular never did, so
# every primitive hand-rolled write.csv and nothing knew what format the
# vocabulary had declared. That is how files named .parquet came to hold CSV
# (C-35).
#
# The orchestrator names every output from the vocabulary
# (`<step>_<output>.<format>`), so the extension IS the declared format. These
# helpers read the format from the path rather than taking it as a parameter,
# which leaves exactly one place where a format decision can be made.
#
# The writer is strict: writing is a claim, and it writes only what the
# extension says. The reader is liberal: acquisition caches are CSV by
# declaration, and the vocabulary accepts csv at I/O with parquet canonical.
# ═══════════════════════════════════════════════════════════════════════════════

# Parquet files begin and end with these four bytes.
.PARQUET_MAGIC <- charToRaw("PAR1")

.table_ext <- function(path) {
 tolower(tools::file_ext(path))
}

.has_parquet_magic <- function(path) {
 con <- file(path, "rb")
 on.exit(close(con))
 head <- readBin(con, what = "raw", n = 4)
 identical(head, .PARQUET_MAGIC)
}

.require_arrow <- function(path, warnings) {
 if (!requireNamespace("arrow", quietly = TRUE)) {
   primitive_failure(
     error = "Parquet support not installed",
     message = sprintf(
       paste0("Path: %s\nReading or writing parquet needs the R package ",
              "'arrow', which is not installed in this environment. ",
              "Install it with: mamba install -c conda-forge r-arrow"),
       path),
     warnings = warnings
   )
 }
}

#' Safely Read Tabular Data
#'
#' Reads a table, choosing the reader from the file extension. Accepts
#' .parquet and .csv. A file named .parquet that is not parquet on disk is
#' refused by name rather than misread, because files written before C-35 was
#' fixed carry exactly that lie.
#'
#' @param path Path to file
#' @param warnings Warnings collector
#' @return data.frame (never a tibble, so base indexing behaves as expected)
#' @export
safe_read_table <- function(path, warnings = NULL) {

 if (!file.exists(path)) {
   primitive_failure(
     error = "Tabular input not found",
     message = sprintf("Path: %s", path),
     warnings = warnings
   )
 }

 ext <- .table_ext(path)

 if (ext == "parquet") {
   if (!.has_parquet_magic(path)) {
     primitive_failure(
       error = "File is not parquet",
       message = sprintf(
         paste0("Path: %s\nThe file is named .parquet but does not begin with ",
                "the parquet signature. It was probably written as CSV before ",
                "C-35 was fixed. Re-run the step that produced it; every ",
                "artifact is re-derivable."),
         path),
       warnings = warnings
     )
   }
   .require_arrow(path, warnings)
   return(tryCatch(
     as.data.frame(arrow::read_parquet(path)),
     error = function(e) {
       primitive_failure(
         error = "Failed to read parquet",
         message = sprintf("Path: %s\nError: %s", path, e$message),
         warnings = warnings
       )
     }
   ))
 }

 if (ext == "csv") {
   # check.names = FALSE: R's default silently rewrites column names that are
   # not syntactic, so "Percent of households with broadband" would arrive as
   # "Percent.of.households.with.broadband" and no declaration naming the
   # published column could find it. A reader that renames what it reads is
   # making a silent choice (RWR-1).
   return(tryCatch(
     utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE),
     error = function(e) {
       primitive_failure(
         error = "Failed to read CSV",
         message = sprintf("Path: %s\nError: %s", path, e$message),
         warnings = warnings
       )
     }
   ))
 }

 primitive_failure(
   error = "Unsupported tabular format",
   message = sprintf(
     "Path: %s\nExtension '.%s' is not a tabular format this reader knows. Known: .parquet, .csv",
     path, ext),
   warnings = warnings
 )
}

#' Safely Write Tabular Data
#'
#' Writes a table in exactly the format its extension declares. .parquet
#' writes real parquet; .csv writes CSV; anything else is refused by name.
#' An sf object is refused rather than having its geometry dropped quietly:
#' the caller decides, explicitly, with sf::st_drop_geometry().
#'
#' @param df data.frame to write
#' @param path Output path
#' @param warnings Warnings collector
#' @return The path, invisibly
#' @export
safe_write_table <- function(df, path, warnings = NULL) {

 if (inherits(df, "sf")) {
   primitive_failure(
     error = "Spatial object passed to a tabular writer",
     message = sprintf(
       paste0("Path: %s\nThis is an sf object. Writing it as a table would ",
              "either fail or drop its geometry without saying so. Call ",
              "sf::st_drop_geometry() first if a plain table is intended, or ",
              "use safe_write_sf() for spatial output."),
       path),
     warnings = warnings
   )
 }

 if (!is.data.frame(df)) {
   primitive_failure(
     error = "Not a data frame",
     message = sprintf("Path: %s\nsafe_write_table() expects a data.frame.", path),
     warnings = warnings
   )
 }

 # write.csv(row.names = FALSE) never wrote row names; keep parquet the same.
 rownames(df) <- NULL

 dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
 ext <- .table_ext(path)

 if (ext == "parquet") {
   .require_arrow(path, warnings)
   tryCatch(
     arrow::write_parquet(df, path),
     error = function(e) {
       primitive_failure(
         error = "Failed to write parquet",
         message = sprintf("Path: %s\nError: %s", path, e$message),
         warnings = warnings
       )
     }
   )
   return(invisible(path))
 }

 if (ext == "csv") {
   tryCatch(
     utils::write.csv(df, path, row.names = FALSE),
     error = function(e) {
       primitive_failure(
         error = "Failed to write CSV",
         message = sprintf("Path: %s\nError: %s", path, e$message),
         warnings = warnings
       )
     }
   )
   return(invisible(path))
 }

 primitive_failure(
   error = "Unsupported tabular format",
   message = sprintf(
     "Path: %s\nExtension '.%s' is not a tabular format this writer knows. Known: .parquet, .csv",
     path, ext),
   warnings = warnings
 )
}

#' Build a Path for a Secondary Output
#'
#' Derives a secondary output's path from the primary's: same directory, same
#' stem, a suffix, and the secondary's own extension. Replaces sub() on the
#' extension, which returns its input unchanged when the pattern does not
#' match, and so once pointed two outputs at one file (REG-2).
#'
#' @param output_path The primary output path
#' @param suffix What distinguishes the secondary, e.g. "diagnostics"
#' @param ext The secondary's own extension, without the dot
#' @param warnings Warnings collector
#' @return A path guaranteed to differ from output_path
#' @export
sibling_path <- function(output_path, suffix, ext, warnings = NULL) {

 if (!nzchar(suffix %||% "") || !nzchar(ext %||% "")) {
   primitive_failure(
     error = "Invalid secondary output name",
     message = "sibling_path() needs a non-empty suffix and extension.",
     warnings = warnings
   )
 }

 stem <- tools::file_path_sans_ext(output_path)
 out <- paste0(stem, "_", suffix, ".", ext)

 if (identical(normalizePath(out, mustWork = FALSE),
               normalizePath(output_path, mustWork = FALSE))) {
   primitive_failure(
     error = "Secondary output would overwrite the primary",
     message = sprintf("Primary: %s\nSecondary: %s", output_path, out),
     warnings = warnings
   )
 }

 out
}