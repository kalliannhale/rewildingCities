# ============================================================
# roots/statistics/classify_clusters.R
# Classify z-score raster into hot/cold spot categories
# ============================================================
# Takes a Gi* z-score raster (from local_gi_star.R) and
# classifies each cell into hot spot, cold spot, or
# not significant at user-specified confidence levels.
#
# Produces:
#   Primary: classified raster (integer codes)
#   Secondary: summary CSV (area/proportion per category)
#
# Classification codes:
#    99 = hot spot 99%    -99 = cold spot 99%
#    95 = hot spot 95%    -95 = cold spot 95%
#    90 = hot spot 90%    -90 = cold spot 90%
#     0 = not significant
#
# Tiers are EXCLUSIVE: a cell classified at 99% is NOT also
# counted in the 95% tier. The 95% tier means "significant at
# 95% but NOT at 99%."
#
# Contract (rewildr):
#   Input:  z_scores (gi_star_z_scores raster)
#   Params: confidence_levels (numeric vector), classification_mode
#   Output: classified GeoTIFF + secondary summary CSV
# ============================================================

library(rewildr)
library(terra)

# --- Parse arguments ---
args <- parse_primitive_args()

input_path    <- get_input(args$inputs, "z_scores")
output_path   <- args$output
conf_levels   <- as.numeric(get_param(args$params, "confidence_levels", c(0.90, 0.95, 0.99)))
class_mode    <- get_param(args$params, "classification_mode", "standard_three_tier")

w <- warnings_collector()

with_primitive_error_handling({

  # --- Load z-score raster ---
  z_raster <- rast(input_path)

  if (nlyr(z_raster) > 1) {
    w$add("info", "classify_clusters",
      paste0("Input has ", nlyr(z_raster), " layers. Using first layer as z-scores."))
    z_raster <- z_raster[[1]]
  }

  z_vals <- values(z_raster)[, 1]
  valid_mask <- !is.na(z_vals)
  z_valid <- z_vals[valid_mask]

  if (length(z_valid) == 0) {
    primitive_failure(
      error = "No valid data",
      message = "Z-score raster contains no valid cells.",
      warnings = w
    )
  }

  # --- Handle binary mode ---
  if (class_mode == "binary") {
    conf_levels <- 0.95
    w$add("info", "classify_clusters",
      "Binary mode: classifying at 95% confidence only.")
  }

  # --- Sort confidence levels descending (highest priority first) ---
  conf_sorted  <- sort(conf_levels, decreasing = TRUE)
  z_thresholds <- qnorm(1 - (1 - conf_sorted) / 2)

  # --- Classify (exclusive tiers) ---
  classification <- rep(0L, length(z_valid))

  for (i in seq_along(conf_sorted)) {
    z_thresh <- z_thresholds[i]
    conf_int <- as.integer(round(conf_sorted[i] * 100))

    # Hot: z >= threshold AND not already classified at higher tier
    hot_mask <- z_valid >= z_thresh & classification == 0L
    classification[hot_mask] <- conf_int

    # Cold: z <= -threshold AND not already classified
    cold_mask <- z_valid <= -z_thresh & classification == 0L
    classification[cold_mask] <- -conf_int
  }

  # --- Build classified raster ---
  class_raster <- rast(z_raster)
  values(class_raster) <- NA_integer_
  class_raster[valid_mask] <- classification
  names(class_raster) <- "cluster_class"

  writeRaster(class_raster, output_path, overwrite = TRUE)

  # --- Build summary table ---
  summary_rows <- list()

  for (i in seq_along(conf_sorted)) {
    conf_int <- as.integer(round(conf_sorted[i] * 100))

    n_hot  <- sum(classification == conf_int)
    n_cold <- sum(classification == -conf_int)

    summary_rows[[length(summary_rows) + 1]] <- data.frame(
      category   = paste0("hot_spot_", conf_int, "_exclusive"),
      confidence = conf_sorted[i],
      n_cells    = n_hot,
      pct_valid  = round(n_hot / length(z_valid) * 100, 2),
      stringsAsFactors = FALSE
    )
    summary_rows[[length(summary_rows) + 1]] <- data.frame(
      category   = paste0("cold_spot_", conf_int, "_exclusive"),
      confidence = conf_sorted[i],
      n_cells    = n_cold,
      pct_valid  = round(n_cold / length(z_valid) * 100, 2),
      stringsAsFactors = FALSE
    )
  }

  n_ns <- sum(classification == 0L)
  summary_rows[[length(summary_rows) + 1]] <- data.frame(
    category   = "not_significant",
    confidence = NA_real_,
    n_cells    = n_ns,
    pct_valid  = round(n_ns / length(z_valid) * 100, 2),
    stringsAsFactors = FALSE
  )

  summary_df <- do.call(rbind, summary_rows)

  # Write summary as secondary output alongside primary raster
  summary_path <- sub("\\.tif$", "_summary.csv", output_path)
  write.csv(summary_df, summary_path, row.names = FALSE)

  # --- Log key results ---
  hot_total  <- sum(classification > 0)
  cold_total <- sum(classification < 0)

  w$add("info", "classify_clusters",
    sprintf("Classification complete: %d hot (%.1f%%), %d cold (%.1f%%), %d neutral (%.1f%%)",
      hot_total, hot_total / length(z_valid) * 100,
      cold_total, cold_total / length(z_valid) * 100,
      n_ns, n_ns / length(z_valid) * 100))

  # --- Report ---
  meta <- extract_raster_metadata(class_raster)

  primitive_success(
    metadata = c(meta, list(
      n_valid_cells    = length(z_valid),
      n_hot_spots      = hot_total,
      n_cold_spots     = cold_total,
      n_not_significant = n_ns,
      pct_hot          = round(hot_total / length(z_valid) * 100, 2),
      pct_cold         = round(cold_total / length(z_valid) * 100, 2),
      confidence_levels = conf_sorted,
      classification_mode = class_mode,
      tiers_are_exclusive = TRUE,
      secondary = list(
        summary = summary_path
      )
    )),
    warnings = w
  )

}, warnings = w)
