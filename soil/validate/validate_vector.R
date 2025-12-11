#!/usr/bin/env Rscript

# ============================================================
# soil/validate/validate_vector.R
# 
# Diagnostic primitive: validates vector layer health.
# Checks CRS, geometry validity, empty geometries, feature count.
# 
# PASSTHROUGH: Does not write output file. Returns input path.
# ============================================================

library(sf)
sf::sf_use_s2(FALSE)
library(rewildr)

# --- Parse arguments ---
args <- parse_primitive_args()

features_path <- get_input(args$inputs, "features", required = TRUE)
# output path ignored for passthrough primitives
params <- args$params

# --- Initialize warnings collector ---
w <- warnings_collector()

# --- Load vector data ---
sf_obj <- tryCatch(
  sf::st_read(features_path, quiet = TRUE),
  error = function(e) {
    primitive_failure(
      error = "Failed to read vector file",
      message = e$message
    )
  }
)

# --- Check: Feature count ---
n_features <- nrow(sf_obj)

if (n_features == 0) {
  w$critical("Vector layer contains no features")
} else {
  w$info(sprintf("Feature count: %d", n_features))
}

# --- Check: CRS defined ---
crs <- sf::st_crs(sf_obj)

if (is.na(crs)) {
  w$critical("CRS is not defined")
} else {
  crs_display <- if (!is.null(crs$epsg) && !is.na(crs$epsg)) {
    sprintf("EPSG:%d", crs$epsg)
  } else if (!is.null(crs$input)) {
    crs$input
  } else {
    "defined (non-EPSG)"
  }
  w$info(sprintf("CRS: %s", crs_display))
}

# --- Check: Geometry validity ---
validity <- sf::st_is_valid(sf_obj)
n_invalid <- sum(!validity, na.rm = TRUE)

if (n_invalid > 0) {
  w$warn(sprintf(
    "%d geometries invalid (%.1f%%). Consider running repair_geometry.",
    n_invalid,
    (n_invalid / n_features) * 100
  ))
} else {
  w$info("All geometries valid")
}

# --- Check: Empty geometries ---
is_empty <- sf::st_is_empty(sf_obj)
n_empty <- sum(is_empty)

if (n_empty > 0) {
  w$warn(sprintf(
    "%d empty geometries found (%.1f%%)",
    n_empty,
    (n_empty / n_features) * 100
  ))
}

# --- Check: Geometry type consistency ---
geom_types <- unique(as.character(sf::st_geometry_type(sf_obj)))

if (length(geom_types) == 1) {
  w$info(sprintf("Geometry type: %s", geom_types))
} else {
  w$warn(sprintf(
    "Mixed geometry types: %s",
    paste(geom_types, collapse = ", ")
  ))
}

# --- Extract metadata ---
metadata <- extract_vector_metadata(sf_obj)

# Add CRS to metadata (required by envelope schema)
metadata$crs <- if (!is.na(crs)) {
  if (!is.null(crs$epsg) && !is.na(crs$epsg)) {
    sprintf("EPSG:%d", crs$epsg)
  } else {
    crs$wkt
  }
} else {
  NULL
}

# Add validation summary to metadata
metadata$validation <- list(
  invalid_count = n_invalid,
  empty_count = n_empty,
  geometry_types = geom_types
)

# --- Return success ---
primitive_success(metadata, w)
