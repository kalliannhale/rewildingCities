# ============================================================
# roots/statistics/local_gi_star.R
# Getis-Ord Gi* Local Spatial Autocorrelation
# ============================================================
# Computes Gi* z-scores for each cell of an input raster.
# Outputs a single-band z-score raster. Classification into
# hot/cold spot categories is handled by classify_clusters.R.
#
# Contract (rewildr):
#   Input:  raster (land_surface_temperature or any continuous raster)
#   Params: weights_type ("distance_band" | "queen"), distance_m (numeric)
#   Output: single-band GeoTIFF of Gi* z-scores
# ============================================================

library(rewildr)
library(terra)
library(spdep)

# --- Parse arguments via the real rewildr contract ---
args <- parse_primitive_args()

input_path   <- get_input(args$inputs, "raster")
output_path  <- args$output
weights_type <- get_param(args$params, "weights_type", "distance_band")
distance_m   <- as.numeric(get_param(args$params, "distance_m", 200))

# --- Set up warnings collector ---
w <- warnings_collector()

# --- Load raster ---
with_primitive_error_handling({

  lst <- rast(input_path)

  # Basic validation
  n_total <- ncell(lst)
  n_valid <- sum(!is.na(values(lst)))
  pct_na  <- round((n_total - n_valid) / n_total * 100, 1)

  if (n_valid < 30) {
    primitive_failure(
      error = "Insufficient data",
      message = paste("Only", n_valid, "valid cells. Need at least 30 for Gi*."),
      warnings = w
    )
  }

  if (pct_na > 50) {
    w$add("critical", "local_gi_star",
      paste0("Raster has ", pct_na, "% NoData. Gi* results may be unreliable."))
  } else if (pct_na > 0) {
    w$add("info", "local_gi_star",
      paste0("Raster has ", pct_na, "% NoData cells excluded from analysis."))
  }

  if (n_valid > 500000) {
    w$add("warning", "local_gi_star",
      paste0(n_valid, " valid cells. Gi* computation may be slow. ",
             "Consider coarser resolution or smaller study area."))
  }

  # --- Convert to points for spdep ---
  pts <- as.data.frame(lst, xy = TRUE, na.rm = TRUE)
  colnames(pts) <- c("x", "y", "value")
  coords <- as.matrix(pts[, c("x", "y")])

  # --- Build spatial weights ---
  if (weights_type == "distance_band") {

    nb <- dnearneigh(coords, d1 = 0, d2 = distance_m)

    # Handle isolates
    n_isolates <- sum(card(nb) == 0)
    if (n_isolates > 0) {
      w$add("warning", "local_gi_star",
        paste0(n_isolates, " cells have no neighbors within ",
               distance_m, "m. Excluded from Gi* computation."))

      keep <- card(nb) > 0
      pts    <- pts[keep, ]
      coords <- coords[keep, ]
      nb     <- dnearneigh(coords, d1 = 0, d2 = distance_m)
    }

    lw <- nb2listw(nb, style = "B", zero.policy = TRUE)

  } else if (weights_type == "queen") {

    # For raster grid: use k nearest neighbors as proxy for queen
    # (true queen contiguity requires grid topology which spdep
    # handles awkwardly with irregular NA masks)
    nb <- knn2nb(knearneigh(coords, k = 8))
    lw <- nb2listw(nb, style = "B", zero.policy = TRUE)

    w$add("info", "local_gi_star",
      "Queen contiguity approximated via 8 nearest neighbors on irregular grid.")

  } else {
    primitive_failure(
      error = "Invalid parameter",
      message = paste("Unknown weights_type:", weights_type),
      warnings = w
    )
  }

  # --- Compute Gi* ---
  gi <- localG(pts$value, lw)
  z_scores <- as.numeric(gi)

  # --- Write z-score raster ---
  z_raster <- rast(lst)
  values(z_raster) <- NA_real_

  cell_indices <- cellFromXY(lst, coords)
  z_raster[cell_indices] <- z_scores
  names(z_raster) <- "gi_z_score"

  writeRaster(z_raster, output_path, overwrite = TRUE)

  # --- Extract raster metadata ---
  meta <- extract_raster_metadata(z_raster)

  # --- Report success ---
  primitive_success(
    metadata = c(meta, list(
      n_valid_cells  = length(z_scores),
      z_score_range  = round(range(z_scores), 3),
      z_score_mean   = round(mean(z_scores), 3),
      weights_type   = weights_type,
      distance_m     = distance_m,
      n_isolates_removed = if (exists("n_isolates")) n_isolates else 0L
    )),
    warnings = w
  )

}, warnings = w)
