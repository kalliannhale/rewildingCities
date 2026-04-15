# ============================================================
# soil/scope/crop_to_boundary.R
# Crop a raster to a vector boundary with optional buffer
# ============================================================

library(rewildr)
library(terra)
library(sf)

args <- parse_primitive_args()

raster_path   <- get_input(args$inputs, "raster")
boundary_path <- get_input(args$inputs, "boundary")
output_path   <- args$output
buffer_m      <- as.numeric(get_param(args$params, "buffer_m", 0))

w <- warnings_collector()

with_primitive_error_handling({

  r <- safe_read_rast(raster_path, warnings = w)
  boundary <- safe_read_sf(boundary_path, warnings = w)

  # Ensure CRS match
  matched <- validate_crs_match(r, boundary, warnings = w, transform_to = 1)
  # transform boundary to raster CRS (cheaper than reprojecting raster)
  boundary <- matched$obj2

  # Apply buffer if requested
  if (buffer_m > 0) {
    boundary_buffered <- st_buffer(boundary, dist = buffer_m)
    w$add("info", "crop_to_boundary",
      sprintf("Applied %gm buffer to boundary before cropping.", buffer_m))
  } else {
    boundary_buffered <- boundary
  }

  # Document extent before
  ext_before <- ext(r)

  # Crop and mask
  r_cropped <- crop(r, vect(boundary_buffered))
  r_masked  <- mask(r_cropped, vect(boundary_buffered))

  # Document extent after
  ext_after <- ext(r_masked)

  n_before <- sum(!is.na(values(r)))
  n_after  <- sum(!is.na(values(r_masked)))

  w$add("info", "crop_to_boundary",
    sprintf("Cropped from %d to %d valid cells (%.1f%% retained).",
      n_before, n_after,
      if (n_before > 0) n_after / n_before * 100 else 0))

  safe_write_rast(r_masked, output_path, warnings = w)

  meta <- extract_raster_metadata(r_masked)

  primitive_success(
    metadata = c(meta, list(
      extent_before = as.list(as.vector(ext_before)),
      extent_after = as.list(as.vector(ext_after)),
      buffer_m = buffer_m,
      cells_before = n_before,
      cells_after = n_after
    )),
    warnings = w
  )

}, warnings = w)