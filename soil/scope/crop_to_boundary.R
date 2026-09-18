# ============================================================
# soil/scope/crop_to_boundary.R
# Crop a raster to a vector boundary with optional buffer
# ============================================================

library(rewildr)
library(terra)
terra::terraOptions(progress=0)
library(sf)

args <- parse_primitive_args()

raster_path   <- get_input(args$inputs, "raster")
boundary_path <- get_input(args$inputs, "boundary")
output_path   <- args$output
buffer_m      <- as.numeric(get_param(args$params, "buffer_m", 0))
# Sprint 9: cropping and masking are DIFFERENT operations and bundling them
# made the destructive one a silent side effect of the scoping one. Cropping
# reduces a raster's extent; masking deletes every value outside the geometry.
# When the boundary is a set of analysis features rather than a study area,
# masking erases exactly the surroundings a gradient analysis measures. So
# masking is now asked for, not assumed. Default stays TRUE for callers that
# relied on the old behaviour. C-40.
do_mask       <- isTRUE(as.logical(get_param(args$params, "mask", TRUE)))

w <- warnings_collector("crop_to_boundary")

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

  # Crop the extent; mask only if asked.
  r_cropped <- crop(r, vect(boundary_buffered))
  r_out <- if (do_mask) mask(r_cropped, vect(boundary_buffered)) else r_cropped

  if (do_mask) {
    w$add("info", "crop_to_boundary",
      "Masked to the boundary geometry: cells outside it are now NoData.")
  } else {
    w$add("info", "crop_to_boundary",
      "Extent cropped; values outside the boundary are RETAINED (mask = false).")
  }

  # Document extent after
  ext_after <- ext(r_out)

  n_before <- sum(!is.na(values(r)))
  n_after  <- sum(!is.na(values(r_out)))
  retained <- if (n_before > 0) n_after / n_before * 100 else 0

  # Retention is reported at the severity it deserves. Losing nearly all of a
  # raster is not an incidental fact: it silently voids anything measured
  # downstream, which is how a plausible-looking result gets published.
  # severity depends on WHICH operation ran. when masking, lost cells are lost
  # DATA and a collapse voids the analysis. when cropping only, lost cells are
  # simply outside the study area, which is the entire point: trimming a scene
  # to a city discards most of it by design. a threshold without that context
  # cries wolf. C-41.
  if (!do_mask) {
    w$info(sprintf(
      paste("Extent cropped to the boundary: %d of %d cells retained (%.1f%%).",
            "Values outside the boundary were not deleted; the reduction is",
            "extent, not data."), n_after, n_before, retained))
  } else if (retained < 10) {
    w$critical(sprintf(
      paste("Cropping retained only %.1f%% of valid cells (%d of %d).",
            "If the boundary is a set of analysis features rather than a study",
            "area, masking has deleted the surroundings the analysis needs.",
            "Consider mask = false, or cropping to a study boundary."),
      retained, n_after, n_before))
  } else if (retained < 50) {
    w$warn(sprintf("Cropping retained %.1f%% of valid cells (%d of %d).",
                   retained, n_after, n_before))
  } else {
    w$info(sprintf("Cropped from %d to %d valid cells (%.1f%% retained).",
                   n_before, n_after, retained))
  }

  safe_write_rast(r_out, output_path, warnings = w)

  meta <- extract_raster_metadata(r_out)

  # modifyList merges by name; c() concatenates and can duplicate a key the
  # extractor already emitted. No collision here today, but the contract
  # should not depend on that staying true.
  primitive_success(
    metadata = modifyList(meta, list(
      extent_before = as.list(as.vector(ext_before)),
      extent_after = as.list(as.vector(ext_after)),
      buffer_m = buffer_m,
      masked = do_mask,
      cells_before = n_before,
      cells_after = n_after,
      cells_retained_pct = round(retained, 2)
    )),
    warnings = w
  )

}, warnings = w)