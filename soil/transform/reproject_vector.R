#!/usr/bin/env Rscript

# ============================================================
# soil/transform/reproject_vector.R
# 
# Transform primitive: reprojects vector to target CRS.
# Documents source and target CRS.
# 
# WRITES OUTPUT: Creates new file with transformed geometries.
# ============================================================

library(sf)
sf::sf_use_s2(FALSE)
library(rewildr)

# --- Parse arguments ---
args <- parse_primitive_args()

features_path <- get_input(args$inputs, "features", required = TRUE)
output_path <- args$output
params <- args$params

target_crs <- get_param(params, "target_crs")

if (is.null(target_crs)) {
  primitive_failure(
    error = "Missing required parameter",
    message = "target_crs is required for reproject_vector"
  )
}

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

n_features <- nrow(sf_obj)
w$info(sprintf("Loaded %d features", n_features))

# --- Check source CRS ---
source_crs <- sf::st_crs(sf_obj)

if (is.na(source_crs)) {
  primitive_failure(
    error = "Cannot reproject: source CRS is not defined",
    message = "Run validate_vector first to check CRS"
  )
}

source_crs_display <- if (!is.null(source_crs$epsg) && !is.na(source_crs$epsg)) {
  sprintf("EPSG:%d", source_crs$epsg)
} else if (!is.null(source_crs$input)) {
  source_crs$input
} else {
  "unknown"
}

# --- Parse target CRS ---
target_crs_obj <- tryCatch(
  sf::st_crs(target_crs),
  error = function(e) {
    primitive_failure(
      error = "Invalid target CRS",
      message = e$message
    )
  }
)

if (is.na(target_crs_obj)) {
  primitive_failure(
    error = "Invalid target CRS",
    message = sprintf("Could not parse: %s", target_crs)
  )
}

target_crs_display <- if (!is.null(target_crs_obj$epsg) && !is.na(target_crs_obj$epsg)) {
  sprintf("EPSG:%d", target_crs_obj$epsg)
} else {
  target_crs
}

# --- Check if already in target CRS ---
if (source_crs == target_crs_obj) {
  w$info(sprintf("Already in target CRS (%s). No transformation needed.", target_crs_display))
  sf_transformed <- sf_obj
} else {
  # --- Transform ---
  w$info(sprintf("Transforming from %s to %s", source_crs_display, target_crs_display))
  
  sf_transformed <- sf::st_transform(sf_obj, target_crs_obj)
  
  w$info("Transformation complete")
}

# --- Write output ---
sf::st_write(sf_transformed, output_path, delete_dsn = TRUE, quiet = TRUE)

w$info(sprintf("Wrote transformed features to %s", basename(output_path)))

# --- Extract metadata ---
metadata <- extract_vector_metadata(sf_transformed)

# Add CRS to metadata
metadata$crs <- target_crs_display

# Add transform summary to metadata
metadata$transform <- list(
  source_crs = source_crs_display,
  target_crs = target_crs_display,
  transformed = !(source_crs == target_crs_obj)
)

# --- Return success ---
primitive_success(metadata, w)

