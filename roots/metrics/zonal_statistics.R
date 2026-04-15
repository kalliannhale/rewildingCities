# ============================================================
# roots/metrics/zonal_statistics.R
# Extract raster statistics within vector zones
# ============================================================
# General-purpose zonal extraction. Takes any raster and any
# set of zone geometries, extracts the requested statistic
# per zone. Used by PCI analysis (LST per ring), land cover
# proportions, and any future zonal workflow.
#
# Output: CSV with zone identifiers + extracted values
# ============================================================

library(rewildr)
library(terra)
library(sf)
library(exactextractr)

args <- parse_primitive_args()

raster_path <- get_input(args$inputs, "raster")
zones_path  <- get_input(args$inputs, "zones")
output_path <- args$output
stat        <- get_param(args$params, "statistic", "median")
id_fields   <- get_param(args$params, "id_fields", c("feature_id", "distance_m"))
band        <- as.integer(get_param(args$params, "band", 1))

w <- warnings_collector()

with_primitive_error_handling({

  r <- safe_read_rast(raster_path, warnings = w)
  zones <- safe_read_sf(zones_path, warnings = w)

  # CRS match
  matched <- validate_crs_match(r, zones, warnings = w, transform_to = 1)
  zones <- matched$obj2

  # Select band
  if (nlyr(r) > 1) {
    w$add("info", "zonal_statistics",
      sprintf("Multi-band raster. Using band %d.", band))
    r <- r[[band]]
  }

  # Validate id_fields exist
  available_ids <- intersect(id_fields, names(zones))
  if (length(available_ids) == 0) {
    zones$zone_id <- seq_len(nrow(zones))
    available_ids <- "zone_id"
    w$add("warning", "zonal_statistics",
      paste("None of the requested id_fields found. Using row numbers.",
            "Requested:", paste(id_fields, collapse = ", ")))
  }

  # Extract
  valid_stats <- c("mean", "median", "min", "max", "sum",
                    "count", "stdev", "variance", "majority")
  if (!stat %in% valid_stats) {
    primitive_failure("Invalid parameter",
      sprintf("Statistic '%s' not supported. Options: %s",
        stat, paste(valid_stats, collapse = ", ")),
      warnings = w)
  }

  w$add("info", "zonal_statistics",
    sprintf("Extracting '%s' from %d zones.", stat, nrow(zones)))

  extracted <- exact_extract(r, zones, stat)

  # Build output table
  result_df <- st_drop_geometry(zones[, available_ids, drop = FALSE])
  result_df[[paste0("lst_", stat)]] <- extracted

  # Track extraction quality
  n_na <- sum(is.na(extracted))
  if (n_na > 0) {
    w$add("warning", "zonal_statistics",
      sprintf("%d of %d zones returned NA (no raster coverage).",
        n_na, length(extracted)))
  }

  # Write
  write.csv(result_df, output_path, row.names = FALSE)

  primitive_success(
    metadata = list(
      semantic_type = "zonal_statistics",
      data_category = "tabular",
      n_zones = nrow(zones),
      n_valid = sum(!is.na(extracted)),
      n_na = n_na,
      statistic = stat,
      value_range = if (any(!is.na(extracted)))
        as.list(round(range(extracted, na.rm = TRUE), 4)) else NULL,
      id_fields = available_ids
    ),
    warnings = w
  )

}, warnings = w)