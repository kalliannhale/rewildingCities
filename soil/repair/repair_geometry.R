#!/usr/bin/env Rscript

# ============================================================
# soil/repair/repair_geometry.R
# 
# Repair primitive: fixes invalid geometries using st_make_valid().
# Documents how many features were repaired.
# 
# WRITES OUTPUT: Creates new file with repaired geometries.
# ============================================================

library(sf)
sf::sf_use_s2(FALSE)
library(rewildr)

# --- Parse arguments ---
args <- parse_primitive_args()

features_path <- get_input(args$inputs, "features", required = TRUE)
output_path <- args$output
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

n_features <- nrow(sf_obj)
w$info(sprintf("Loaded %d features", n_features))

# --- Check validity before repair ---
validity_before <- sf::st_is_valid(sf_obj)
n_invalid_before <- sum(!validity_before, na.rm = TRUE)

if (n_invalid_before == 0) {
  w$info("All geometries already valid. No repair needed.")
} else {
  w$info(sprintf("Found %d invalid geometries (%.1f%%)", 
                 n_invalid_before, 
                 (n_invalid_before / n_features) * 100))
}

# --- Apply st_make_valid ---
sf_repaired <- sf::st_make_valid(sf_obj)

# --- Check validity after repair ---
validity_after <- sf::st_is_valid(sf_repaired)
n_invalid_after <- sum(!validity_after, na.rm = TRUE)

n_repaired <- n_invalid_before - n_invalid_after

if (n_repaired > 0) {
  w$info(sprintf("Repaired %d geometries", n_repaired))
}

if (n_invalid_after > 0) {
  w$warn(sprintf(
    "%d geometries still invalid after repair. Manual review recommended.",
    n_invalid_after
  ))
}

# --- Handle geometry collection explosion ---
# st_make_valid can turn polygons into geometry collections
geom_types_after <- unique(as.character(sf::st_geometry_type(sf_repaired)))

if ("GEOMETRYCOLLECTION" %in% geom_types_after) {
  w$warn("Repair created GEOMETRYCOLLECTION geometries. May need further processing.")
}

# --- Write output ---
sf::st_write(sf_repaired, output_path, delete_dsn = TRUE, quiet = TRUE)

w$info(sprintf("Wrote repaired features to %s", basename(output_path)))

# --- Extract metadata ---
metadata <- extract_vector_metadata(sf_repaired)

# Add CRS to metadata
crs <- sf::st_crs(sf_repaired)
metadata$crs <- if (!is.na(crs)) {
  if (!is.null(crs$epsg) && !is.na(crs$epsg)) {
    sprintf("EPSG:%d", crs$epsg)
  } else {
    crs$wkt
  }
} else {
  NULL
}

# Add repair summary to metadata
metadata$repair <- list(
  invalid_before = n_invalid_before,
  invalid_after = n_invalid_after,
  repaired_count = n_repaired
)

# --- Return success ---
primitive_success(metadata, w)
