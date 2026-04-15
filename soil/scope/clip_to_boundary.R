# ============================================================
# soil/scope/clip_to_boundary.R
# Clip vector features to a boundary polygon
# ============================================================
# Filters or intersects features against a boundary.
# "filter" mode keeps features whose centroid falls within.
# "intersect" mode clips geometries to the boundary.
# ============================================================

library(rewildr)
library(sf)

args <- parse_primitive_args()

features_path <- get_input(args$inputs, "features")
boundary_path <- get_input(args$inputs, "boundary")
output_path   <- args$output
method        <- get_param(args$params, "method", "filter")

w <- warnings_collector()

with_primitive_error_handling({

  features <- safe_read_sf(features_path, warnings = w)
  boundary <- safe_read_sf(boundary_path, warnings = w)

  matched <- validate_crs_match(features, boundary, warnings = w, transform_to = 2)
  features <- matched$obj1

  n_before <- nrow(features)

  if (method == "filter") {
    centroids <- st_centroid(features, of_largest_polygon = TRUE)
    within <- st_within(centroids, st_union(boundary), sparse = FALSE)[, 1]
    features_clipped <- features[within, ]
  } else if (method == "intersect") {
    features_clipped <- st_intersection(features, st_union(boundary))
  } else {
    primitive_failure("Invalid parameter",
      sprintf("Unknown method: %s. Options: filter, intersect", method),
      warnings = w)
  }

  n_after <- nrow(features_clipped)

  w$add("info", "clip_to_boundary",
    sprintf("Clipped from %d to %d features using '%s' method.",
      n_before, n_after, method))

  safe_write_sf(features_clipped, output_path, warnings = w)
  meta <- extract_vector_metadata(features_clipped)

  primitive_success(
    metadata = c(meta, list(
      n_before = n_before,
      n_after = n_after,
      clip_method = method
    )),
    warnings = w
  )

}, warnings = w)