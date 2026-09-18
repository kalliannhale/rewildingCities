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
#
# Sprint 8 patches (2026-05):
#   1. id_fields coerced via unlist() + as.character() to handle
#      jsonlite deserializing JSON arrays as R lists. Without this,
#      `zones[, j]` where j is a list crashes with
#      "Can't subset columns with `j`."
#   2. metadata now emits crs = NULL. The envelope schema requires
#      `crs` in the metadata block; for tabular outputs (no CRS),
#      explicit null is the schema-mandated way to declare absence.
#      Sentinel-driven honesty, not silent omission.
#
# Sprint 9 patch (2026-09):
#   3. metadata now flows through extract_tabular_metadata(), the
#      contract's own extractor, so the output declares row_count,
#      column_count, variables, and data_quality.complete_cases.
#      loam projects coverage from complete_cases / row_count; until
#      now that column rested empty because nothing emitted the
#      fields it reads. spatial_unit (what ONE ROW IS) becomes a
#      declared parameter: emitted when given, and named aloud in the
#      warnings when it is not. this primitive is general-purpose and
#      cannot know whether a zone is a park, a ring, or a tract; that
#      is a fact about the experiment's design, not about geometry.
#      an undeclared unit of analysis is a silent choice, so it is
#      made visible rather than defaulted.
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
# Sprint 8 patch 1: coerce to atomic character.
id_fields   <- as.character(unlist(
                  get_param(args$params, "id_fields", c("feature_id", "distance_m"))))
band        <- as.integer(get_param(args$params, "band", 1))
# Sprint 9 patch 3: what one row IS. declared, never inferred.
spatial_unit <- get_param(args$params, "spatial_unit", NULL)

w <- warnings_collector("zonal_statistics")

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

  # Sprint 9 patch 3: the tabular contract, extracted from the frame we
  # just wrote, then overlaid with what only this primitive knows.
  tab <- extract_tabular_metadata(result_df, spatial_unit = spatial_unit)

  if (is.null(spatial_unit)) {
    w$add("warning", "zonal_statistics",
      paste("No spatial_unit declared: this table does not say what ONE ROW IS.",
            "Downstream joins and commensurability checks cannot verify it against",
            "another table. Declare spatial_unit in the experiment step's params."))
  }

  extra <- list(
    semantic_type = "zonal_statistics",
    data_category = "tabular",
    crs = NA,  # Sprint 8 patch 2: explicit-null for non-spatial tabular output
    n_zones = nrow(zones),
    n_valid = sum(!is.na(extracted)),
    n_na = n_na,
    statistic = stat,
    id_fields = available_ids
  )
  if (any(!is.na(extracted))) {
    extra$value_range <- as.list(round(range(extracted, na.rm = TRUE), 4))
  }

  primitive_success(
    metadata = modifyList(tab, extra),
    warnings = w
  )

}, warnings = w)