# ============================================================
# soil/filter/filter_by_area.R
# Filter vector features by area threshold
# ============================================================
# Excludes features smaller than min_area or larger than
# max_area. Following Xiao et al. (2023): parks < 0.09 ha
# may not generate measurable cooling at Landsat resolution.
# ============================================================

library(rewildr)
library(sf)

args <- parse_primitive_args()

input_path  <- get_input(args$inputs, "features")
output_path <- args$output
min_area_ha <- as.numeric(get_param(args$params, "min_area_ha", 0))
max_area_ha <- as.numeric(get_param(args$params, "max_area_ha", Inf))

w <- warnings_collector()

with_primitive_error_handling({

  features <- safe_read_sf(input_path, warnings = w)
  n_before <- nrow(features)

  areas_ha <- as.numeric(st_area(features)) / 10000

  keep <- areas_ha >= min_area_ha
  if (is.finite(max_area_ha)) {
    keep <- keep & areas_ha <= max_area_ha
  }

  features_filtered <- features[keep, ]
  n_after <- nrow(features_filtered)
  n_dropped <- n_before - n_after

  if (n_dropped > 0) {
    w$add("warning", "filter_by_area",
      sprintf("Excluded %d of %d features outside [%.2f, %s] ha range.",
        n_dropped, n_before, min_area_ha,
        if (is.finite(max_area_ha)) sprintf("%.2f", max_area_ha) else "Inf"))

    # Summary of excluded features
    excluded_areas <- areas_ha[!keep]
    w$add("info", "filter_by_area",
      sprintf("Excluded feature areas: min=%.4f ha, max=%.2f ha, median=%.4f ha.",
        min(excluded_areas), max(excluded_areas), median(excluded_areas)))
  } else {
    w$add("info", "filter_by_area",
      sprintf("All %d features within area range. None excluded.", n_before))
  }

  safe_write_sf(features_filtered, output_path, warnings = w)

  meta <- extract_vector_metadata(features_filtered)

  primitive_success(
    metadata = c(meta, list(
      n_before = n_before,
      n_after = n_after,
      n_excluded = n_dropped,
      min_area_ha = min_area_ha,
      max_area_ha = if (is.finite(max_area_ha)) max_area_ha else NULL
    )),
    warnings = w
  )

}, warnings = w)
