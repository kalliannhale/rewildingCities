# ============================================================
# roots/metrics/landscape_metrics.R
# Compute landscape metrics for features using classified raster
# ============================================================
# Calculates park/feature landscape characteristics from land
# cover data: PA (area), PP (perimeter), NDVI_veg, LSI, LPI,
# and optionally SHAPE_MN, PD, ED, AI via landscapemetrics.
#
# These are the explanatory variables for PCI regression,
# following Xiao et al. (2023) Table 1.
#
# Inputs:
#   features: vector geometries (e.g., park boundaries)
#   land_cover: classified raster
#   ndvi: NDVI raster
# Params:
#   id_field, compute_fragstats (bool)
# Output:
#   CSV with feature_id + all landscape metric columns
# ============================================================

library(rewildr)
library(sf)
library(terra)
library(exactextractr)

args <- parse_primitive_args()

features_path   <- get_input(args$inputs, "features")
lc_path         <- get_input(args$inputs, "land_cover")
ndvi_path       <- get_input(args$inputs, "ndvi", required = FALSE)
output_path     <- args$output
id_field        <- get_param(args$params, "id_field", NULL)
compute_fragstats <- as.logical(get_param(args$params, "compute_fragstats", FALSE))

w <- warnings_collector()

with_primitive_error_handling({

  features <- safe_read_sf(features_path, warnings = w)
  lc <- safe_read_rast(lc_path, warnings = w)

  # Determine ID field
  if (is.null(id_field)) {
    candidates <- c("park_id", "feature_id", "id", "ID")
    id_field <- intersect(candidates, names(features))[1]
    if (is.na(id_field)) {
      features$feature_id <- seq_len(nrow(features))
      id_field <- "feature_id"
    }
  }

  # CRS match
  matched <- validate_crs_match(lc, features, warnings = w, transform_to = 1)
  features <- matched$obj2

  n <- nrow(features)

  # --- Basic geometry metrics ---
  areas_m2 <- as.numeric(st_area(features))
  perimeters_m <- as.numeric(st_length(st_cast(st_boundary(features), "MULTILINESTRING")))

  PA <- areas_m2 / 10000  # hectares
  PP <- perimeters_m

  # LSI: Landscape Shape Index = P / (2 * sqrt(pi * A))
  LSI <- PP / (2 * sqrt(pi * areas_m2))

  # --- NDVI_veg (mean NDVI of vegetated area within feature) ---
  ndvi_veg <- rep(NA_real_, n)
  if (!is.null(ndvi_path)) {
    ndvi_r <- safe_read_rast(ndvi_path, warnings = w)
    matched_ndvi <- validate_crs_match(ndvi_r, features, warnings = w, transform_to = 1)
    features_for_ndvi <- matched_ndvi$obj2

    # Extract NDVI per feature, compute mean of vegetated pixels (NDVI > 0.2)
    ndvi_extracts <- exact_extract(ndvi_r, features)
    for (i in seq_len(n)) {
      vals <- ndvi_extracts[[i]]$value
      veg_vals <- vals[!is.na(vals) & vals > 0.2]
      if (length(veg_vals) > 0) {
        ndvi_veg[i] <- mean(veg_vals)
      }
    }
    w$add("info", "landscape_metrics",
      sprintf("NDVI_veg computed for %d features (threshold: NDVI > 0.2).",
        sum(!is.na(ndvi_veg))))
  } else {
    w$add("warning", "landscape_metrics",
      "NDVI raster not provided. NDVI_veg will be NA.")
  }

  # --- LPI: Largest Patch Index (from land cover within feature) ---
  lpi <- rep(NA_real_, n)
  lc_extracts <- exact_extract(lc, features)

  for (i in seq_len(n)) {
    ext <- lc_extracts[[i]]
    if (!is.null(ext) && nrow(ext) > 0) {
      vals <- ext$value[!is.na(ext$value)]
      if (length(vals) > 0) {
        class_counts <- table(vals)
        largest <- max(class_counts)
        lpi[i] <- round(largest / sum(class_counts) * 100, 2)
      }
    }
  }

  # --- Optional fragstats (SHAPE_MN, PD, ED, AI) ---
  shape_mn <- pd <- ed <- ai <- rep(NA_real_, n)

  if (compute_fragstats) {
    if (requireNamespace("landscapemetrics", quietly = TRUE)) {
      w$add("info", "landscape_metrics",
        "Computing fragstats metrics via landscapemetrics package.")

      for (i in seq_len(n)) {
        tryCatch({
          feat_lc <- crop(lc, vect(features[i, ]))
          feat_lc <- mask(feat_lc, vect(features[i, ]))

          if (sum(!is.na(values(feat_lc))) > 4) {
            lsm <- landscapemetrics::calculate_lsm(feat_lc,
              what = c("lsm_l_shape_mn", "lsm_l_pd", "lsm_l_ed", "lsm_l_ai"))
            for (r in seq_len(nrow(lsm))) {
              if (lsm$metric[r] == "shape_mn") shape_mn[i] <- lsm$value[r]
              if (lsm$metric[r] == "pd") pd[i] <- lsm$value[r]
              if (lsm$metric[r] == "ed") ed[i] <- lsm$value[r]
              if (lsm$metric[r] == "ai") ai[i] <- lsm$value[r]
            }
          }
        }, error = function(e) {
          # silently skip; metrics stay NA
        })
      }
    } else {
      w$add("warning", "landscape_metrics",
        "landscapemetrics package not installed. Fragstats metrics skipped.")
    }
  }

  # --- Assemble ---
  result_df <- data.frame(
    feature_id = features[[id_field]],
    PA = round(PA, 4),
    PP = round(PP, 2),
    LSI = round(LSI, 4),
    LPI = lpi,
    NDVI_veg = round(ndvi_veg, 4),
    SHAPE_MN = round(shape_mn, 4),
    PD = round(pd, 4),
    ED = round(ed, 4),
    AI = round(ai, 4),
    stringsAsFactors = FALSE
  )

  write.csv(result_df, output_path, row.names = FALSE)

  primitive_success(
    metadata = list(
      semantic_type = "landscape_metrics",
      data_category = "tabular",
      n_features = n,
      metrics_computed = c("PA", "PP", "LSI", "LPI", "NDVI_veg",
        if (compute_fragstats) c("SHAPE_MN", "PD", "ED", "AI") else NULL),
      id_field = id_field,
      ndvi_available = !is.null(ndvi_path),
      fragstats_computed = compute_fragstats
    ),
    warnings = w
  )

}, warnings = w)