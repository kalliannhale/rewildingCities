# ============================================================
# soil/filter/mask_raster_by_class.R
# Mask out specific land cover classes from a raster
# ============================================================
# General-purpose spatial filter: given a target raster (e.g.,
# LST) and a classified raster (e.g., land cover), set pixels
# in the target to NA wherever the classified raster matches
# specified class values.
#
# Primary use case: remove water pixels from LST before buffer
# zone extraction, preventing coastal/riverine contamination
# of thermal gradient analyses.
#
# Generalizable to any case where a categorical raster should
# gate what's visible in a continuous raster: mask out shadows,
# clouds, buildings, roads, etc.
#
# Inputs:
#   target: the raster to mask (e.g., LST)
#   classifier: the classified raster (e.g., land cover)
# Params:
#   mask_classes: integer vector of class values to mask out
#   mask_label: human-readable name for what's being masked
#   crosswalk_path: optional — if provided, reads class values
#     from a named group in the crosswalk instead of mask_classes
#   crosswalk_group: which group to mask (e.g., "water")
# Output:
#   masked raster (same as target, with masked pixels set to NA)
# ============================================================

library(rewildr)
library(terra)
library(yaml)

args <- parse_primitive_args()

target_path     <- get_input(args$inputs, "target")
classifier_path <- get_input(args$inputs, "classifier")
output_path     <- args$output
mask_classes     <- get_param(args$params, "mask_classes", NULL)
mask_label       <- get_param(args$params, "mask_label", "masked classes")
crosswalk_path   <- get_param(args$params, "crosswalk_path", NULL)
crosswalk_group  <- get_param(args$params, "crosswalk_group", NULL)

w <- warnings_collector()

with_primitive_error_handling({

  target     <- safe_read_rast(target_path, warnings = w)
  classifier <- safe_read_rast(classifier_path, warnings = w)

  # --- Resolve mask classes from crosswalk if provided ---
  if (!is.null(crosswalk_path) && !is.null(crosswalk_group)) {
    if (!file.exists(crosswalk_path)) {
      primitive_failure("File not found",
        sprintf("Crosswalk not found: %s", crosswalk_path), warnings = w)
    }
    cw <- yaml::read_yaml(crosswalk_path)
    cw_classes <- cw$mappings[[crosswalk_group]]

    if (is.null(cw_classes)) {
      primitive_failure("Invalid crosswalk group",
        sprintf("Group '%s' not found in crosswalk. Available: %s",
          crosswalk_group, paste(names(cw$mappings), collapse = ", ")),
        warnings = w)
    }

    mask_classes <- as.integer(cw_classes)
    mask_label <- crosswalk_group

    w$add("info", "mask_raster_by_class",
      sprintf("Resolved mask classes from crosswalk group '%s': %s",
        crosswalk_group, paste(mask_classes, collapse = ", ")))
  }

  if (is.null(mask_classes) || length(mask_classes) == 0) {
    primitive_failure("Missing parameter",
      "Either mask_classes or crosswalk_path + crosswalk_group required.",
      warnings = w)
  }

  # --- Align rasters ---
  matched <- validate_crs_match(target, classifier, warnings = w, transform_to = 1)
  classifier <- matched$obj2

  # Resample classifier to target resolution if needed
  if (!compareGeom(target, classifier, stopOnError = FALSE)) {
    w$add("info", "mask_raster_by_class",
      "Resampling classifier to match target raster resolution (nearest neighbor).")
    classifier <- resample(classifier, target, method = "near")
  }

  # --- Count pixels before masking ---
  n_valid_before <- sum(!is.na(values(target)))

  # --- Build mask ---
  # Pixels where classifier matches any mask class become NA in target
  class_vals <- values(classifier)[, 1]
  is_masked <- class_vals %in% mask_classes

  target_masked <- target
  values(target_masked)[is_masked] <- NA

  n_valid_after <- sum(!is.na(values(target_masked)))
  n_masked <- n_valid_before - n_valid_after
  pct_masked <- round(n_masked / max(n_valid_before, 1) * 100, 1)

  w$add("info", "mask_raster_by_class",
    sprintf("Masked %d pixels (%.1f%%) classified as %s.",
      n_masked, pct_masked, mask_label))

  if (pct_masked > 30) {
    w$add("warning", "mask_raster_by_class",
      sprintf("%.1f%% of valid pixels were masked as %s. ",
        pct_masked, mask_label,
        "This is a large proportion and may affect downstream analyses. ",
        "Verify the classifier raster aligns correctly with the target."))
  }

  safe_write_rast(target_masked, output_path, warnings = w)

  meta <- extract_raster_metadata(target_masked)

  primitive_success(
    metadata = c(meta, list(
      mask_classes = mask_classes,
      mask_label = mask_label,
      n_pixels_masked = n_masked,
      pct_masked = pct_masked,
      n_valid_before = n_valid_before,
      n_valid_after = n_valid_after
    )),
    warnings = w
  )

}, warnings = w)
