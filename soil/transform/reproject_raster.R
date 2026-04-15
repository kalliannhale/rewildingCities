# ============================================================
# soil/transform/reproject_raster.R
# Reproject a raster to a target CRS
# ============================================================

library(rewildr)
library(terra)

args <- parse_primitive_args()

input_path  <- get_input(args$inputs, "raster")
output_path <- args$output
target_crs  <- get_param(args$params, "target_crs")
method      <- get_param(args$params, "method", "bilinear")

w <- warnings_collector()

with_primitive_error_handling({

  if (is.null(target_crs)) {
    primitive_failure("Missing parameter", "target_crs is required.", warnings = w)
  }

  r <- safe_read_rast(input_path, warnings = w)
  source_crs <- crs(r, describe = TRUE)

  # Check if reprojection is needed
  target_clean <- sub("^EPSG:", "", target_crs)
  if (!is.na(source_crs$code) && source_crs$code == target_clean) {
    w$add("info", "reproject_raster",
      paste0("Already in target CRS (", target_crs, "). Copying without transformation."))
    file.copy(input_path, output_path, overwrite = TRUE)
  } else {
    w$add("info", "reproject_raster",
      sprintf("Reprojecting from %s:%s to %s using %s resampling.",
        source_crs$authority, source_crs$code, target_crs, method))

    r_proj <- project(r, paste0("EPSG:", target_clean), method = method)
    safe_write_rast(r_proj, output_path, warnings = w)
    r <- r_proj
  }

  meta <- extract_raster_metadata(r)

  primitive_success(
    metadata = c(meta, list(
      source_crs = paste0(source_crs$authority, ":", source_crs$code),
      target_crs = target_crs,
      resampling_method = method
    )),
    warnings = w
  )

}, warnings = w)