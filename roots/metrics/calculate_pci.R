# ============================================================
# roots/metrics/calculate_pci.R
# Park Cooling Intensity via TPM-M gradient walk
# ============================================================
# Takes zonal statistics (LST per ring per feature) and the
# feature-interior LST, identifies the turning point for each
# feature, and computes PCI.
#
# TPM-M: PCI = LST_at_first_local_max - LST_inside_feature
#
# The "first local maximum" is the first ring where LST stops
# rising and begins to decline as you move outward from the
# feature boundary. This is the point where the feature's
# cooling influence ends.
#
# Also supports TPM-A (cumulative average to turning point).
#
# Inputs:
#   ring_stats: CSV from zonal_statistics (feature_id, distance_m, lst_median)
#   feature_stats: CSV from zonal_statistics (feature_id, lst_median for interior)
# Params:
#   method: "TPM-M" or "TPM-A"
#   min_rings: minimum rings before turning point can be declared
# Output:
#   CSV with feature_id, PCI, turning_point_distance_m, lst_park, lst_turning_point
# ============================================================

library(rewildr)

args <- parse_primitive_args()

ring_stats_path    <- get_input(args$inputs, "ring_stats")
feature_stats_path <- get_input(args$inputs, "feature_stats")
output_path        <- args$output
method             <- get_param(args$params, "method", "TPM-M")
min_rings          <- as.integer(get_param(args$params, "min_rings", 2))
lst_col            <- get_param(args$params, "lst_column", "lst_median")

w <- warnings_collector()

with_primitive_error_handling({

  ring_stats    <- read.csv(ring_stats_path, stringsAsFactors = FALSE)
  feature_stats <- read.csv(feature_stats_path, stringsAsFactors = FALSE)

  # Validate columns exist
  required_ring_cols <- c("feature_id", "distance_m", lst_col)
  missing_ring <- setdiff(required_ring_cols, names(ring_stats))
  if (length(missing_ring) > 0) {
    primitive_failure("Missing columns",
      sprintf("ring_stats missing: %s", paste(missing_ring, collapse = ", ")),
      warnings = w)
  }

  required_feat_cols <- c("feature_id", lst_col)
  missing_feat <- setdiff(required_feat_cols, names(feature_stats))
  if (length(missing_feat) > 0) {
    primitive_failure("Missing columns",
      sprintf("feature_stats missing: %s", paste(missing_feat, collapse = ", ")),
      warnings = w)
  }

  # Get unique features
  feature_ids <- unique(ring_stats$feature_id)
  n_features <- length(feature_ids)

  w$add("info", "calculate_pci",
    sprintf("Computing %s PCI for %d features.", method, n_features))

  # --- Gradient walk per feature ---
  results <- vector("list", n_features)

  for (i in seq_along(feature_ids)) {
    fid <- feature_ids[i]

    # Get interior LST
    feat_row <- feature_stats[feature_stats$feature_id == fid, ]
    if (nrow(feat_row) == 0 || is.na(feat_row[[lst_col]][1])) {
      results[[i]] <- data.frame(
        feature_id = fid, PCI = NA_real_,
        turning_point_m = NA_real_, lst_park = NA_real_,
        lst_turning_point = NA_real_, n_rings = 0L,
        status = "no_interior_lst", stringsAsFactors = FALSE)
      next
    }
    lst_park <- feat_row[[lst_col]][1]

    # Get ring LSTs, sorted by distance
    rings <- ring_stats[ring_stats$feature_id == fid, ]
    rings <- rings[order(rings$distance_m), ]
    ring_lsts <- rings[[lst_col]]
    ring_dists <- rings$distance_m
    n_rings_avail <- sum(!is.na(ring_lsts))

    if (n_rings_avail < min_rings) {
      results[[i]] <- data.frame(
        feature_id = fid, PCI = NA_real_,
        turning_point_m = NA_real_, lst_park = lst_park,
        lst_turning_point = NA_real_, n_rings = n_rings_avail,
        status = "insufficient_rings", stringsAsFactors = FALSE)
      next
    }

    # --- Find first local maximum ---
    # Walk outward. LST should generally rise (moving into urban
    # fabric). The turning point is the first ring where LST is
    # higher than the next ring (i.e., LST starts declining).
    turning_idx <- NA_integer_

    for (j in seq_len(length(ring_lsts) - 1)) {
      if (is.na(ring_lsts[j]) || is.na(ring_lsts[j + 1])) next

      # Current ring is higher than next ring = local max
      if (ring_lsts[j] > ring_lsts[j + 1] && j >= min_rings) {
        turning_idx <- j
        break
      }
    }

    if (is.na(turning_idx)) {
      # No turning point found — LST kept rising.
      # Use the outermost ring as a conservative estimate.
      last_valid <- max(which(!is.na(ring_lsts)))
      turning_idx <- last_valid

      results[[i]] <- data.frame(
        feature_id = fid,
        PCI = ring_lsts[turning_idx] - lst_park,
        turning_point_m = ring_dists[turning_idx],
        lst_park = lst_park,
        lst_turning_point = ring_lsts[turning_idx],
        n_rings = n_rings_avail,
        status = "no_turning_point_found",
        stringsAsFactors = FALSE)
      next
    }

    # --- Compute PCI ---
    lst_tp <- ring_lsts[turning_idx]

    if (method == "TPM-M") {
      pci <- lst_tp - lst_park
    } else if (method == "TPM-A") {
      # Average LST across all rings up to and including turning point
      ring_subset <- ring_lsts[1:turning_idx]
      pci <- mean(ring_subset, na.rm = TRUE) - lst_park
    } else {
      primitive_failure("Invalid parameter",
        sprintf("Unknown method: %s. Options: TPM-M, TPM-A", method),
        warnings = w)
    }

    results[[i]] <- data.frame(
      feature_id = fid, PCI = round(pci, 4),
      turning_point_m = ring_dists[turning_idx],
      lst_park = round(lst_park, 4),
      lst_turning_point = round(lst_tp, 4),
      n_rings = n_rings_avail,
      status = "success", stringsAsFactors = FALSE)
  }

  pci_df <- do.call(rbind, results)

  # --- Quality summary ---
  n_success <- sum(pci_df$status == "success", na.rm = TRUE)
  n_no_tp   <- sum(pci_df$status == "no_turning_point_found", na.rm = TRUE)
  n_insuf   <- sum(pci_df$status == "insufficient_rings", na.rm = TRUE)
  n_no_lst  <- sum(pci_df$status == "no_interior_lst", na.rm = TRUE)

  if (n_no_tp > 0) {
    w$add("warning", "calculate_pci",
      sprintf("%d features had no turning point (LST kept rising). Used outermost ring.",
        n_no_tp))
  }
  if (n_insuf > 0) {
    w$add("warning", "calculate_pci",
      sprintf("%d features had fewer than %d valid rings. PCI set to NA.",
        n_insuf, min_rings))
  }
  if (n_no_lst > 0) {
    w$add("warning", "calculate_pci",
      sprintf("%d features had no interior LST value. PCI set to NA.", n_no_lst))
  }

  # Check for negative PCI (potential water contamination)
  valid_pci <- pci_df$PCI[!is.na(pci_df$PCI)]
  n_negative <- sum(valid_pci < 0)
  if (n_negative > 0) {
    pct_neg <- round(n_negative / length(valid_pci) * 100, 1)
    w$add("warning", "calculate_pci",
      sprintf("%d features (%.1f%%) have negative PCI. These may be near water bodies ",
        n_negative, pct_neg,
        "or other cool features that contaminate the buffer. ",
        "Consider masking water from buffer zones."))
  }

  write.csv(pci_df, output_path, row.names = FALSE)

  primitive_success(
    metadata = list(
      semantic_type = "pci_results",
      data_category = "tabular",
      method = method,
      n_features = n_features,
      n_success = n_success,
      n_no_turning_point = n_no_tp,
      n_insufficient_rings = n_insuf,
      n_no_interior_lst = n_no_lst,
      n_negative_pci = n_negative,
      pci_range = if (length(valid_pci) > 0)
        as.list(round(range(valid_pci), 4)) else NULL,
      pci_mean = if (length(valid_pci) > 0)
        round(mean(valid_pci), 4) else NULL,
      pci_median = if (length(valid_pci) > 0)
        round(median(valid_pci), 4) else NULL,
      min_rings = min_rings,
      lst_column = lst_col
    ),
    warnings = w
  )

}, warnings = w)