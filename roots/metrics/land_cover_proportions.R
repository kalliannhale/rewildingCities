# ============================================================
# roots/metrics/land_cover_proportions.R
# Compute land cover proportions within zones using crosswalk
# ============================================================
# Takes a classified land cover raster and zone geometries,
# reclassifies via a crosswalk YAML, and computes the
# proportion of each target class (blue/green/grey) per zone.
#
# This replaces the v1 NDVI-threshold hack with direct pixel
# classification, making it accurate and city-agnostic.
#
# Inputs:
#   land_cover: classified raster
#   zones: vector geometries (e.g., buffer rings)
# Params:
#   crosswalk_path: YAML mapping source classes to target classes
#   id_fields: zone identifier columns
# Output:
#   CSV with zone IDs + proportion columns per target class
# ============================================================

library(rewildr)
library(terra)
library(sf)
library(exactextractr)
library(yaml)

args <- parse_primitive_args()

lc_path        <- get_input(args$inputs, "land_cover")
zones_path     <- get_input(args$inputs, "zones")
output_path    <- args$output
crosswalk_path <- get_param(args$params, "crosswalk_path", NULL)
id_fields      <- get_param(args$params, "id_fields", c("feature_id", "distance_m"))

w <- warnings_collector()

with_primitive_error_handling({

  lc <- safe_read_rast(lc_path, warnings = w)
  zones <- safe_read_sf(zones_path, warnings = w)

  # CRS match
  matched <- validate_crs_match(lc, zones, warnings = w, transform_to = 1)
  zones <- matched$obj2

  # --- Load crosswalk ---
  if (is.null(crosswalk_path)) {
    primitive_failure("Missing parameter",
      "crosswalk_path is required. Provide a YAML mapping source classes to target classes.",
      warnings = w)
  }

  if (!file.exists(crosswalk_path)) {
    primitive_failure("File not found",
      sprintf("Crosswalk file not found: %s", crosswalk_path),
      warnings = w)
  }

  crosswalk <- yaml::read_yaml(crosswalk_path)

  # Expected structure:
  # from: "NYC LiDAR 8-Class"
  # to: "Nanjing 3-Class Study"
  # mappings:
  #   vegetation: [1, 2]    # Tree Canopy, Grass/Shrubs
  #   water: [4]
  #   impervious: [5, 6, 7, 8]

  mappings <- crosswalk$mappings
  target_classes <- names(mappings)

  w$add("info", "land_cover_proportions",
    sprintf("Crosswalk: '%s' -> '%s' with %d target classes: %s",
      crosswalk$from %||% "unknown",
      crosswalk$to %||% "unknown",
      length(target_classes),
      paste(target_classes, collapse = ", ")))

  # --- Build reclassification matrix ---
  # Map each source class value to a target class index
  target_lookup <- list()
  for (tc in target_classes) {
    source_values <- mappings[[tc]]
    for (sv in source_values) {
      target_lookup[[as.character(sv)]] <- tc
    }
  }

  # --- Extract and classify per zone ---
  available_ids <- intersect(id_fields, names(zones))
  if (length(available_ids) == 0) {
    zones$zone_id <- seq_len(nrow(zones))
    available_ids <- "zone_id"
  }

  lc_extracts <- exact_extract(lc, zones)

  result_list <- vector("list", length(lc_extracts))

  for (i in seq_along(lc_extracts)) {
    ext_data <- lc_extracts[[i]]

    if (is.null(ext_data) || nrow(ext_data) == 0) {
      row <- as.list(rep(NA_real_, length(target_classes)))
      names(row) <- paste0("prop_", target_classes)
      result_list[[i]] <- as.data.frame(row, stringsAsFactors = FALSE)
      next
    }

    pixel_values <- ext_data$value
    # Weight by coverage fraction if available
    weights <- if ("coverage_fraction" %in% names(ext_data)) {
      ext_data$coverage_fraction
    } else {
      rep(1, length(pixel_values))
    }

    # Classify each pixel
    total_weight <- sum(weights[!is.na(pixel_values)])

    props <- list()
    for (tc in target_classes) {
      source_vals <- mappings[[tc]]
      mask <- pixel_values %in% source_vals & !is.na(pixel_values)
      props[[paste0("prop_", tc)]] <- if (total_weight > 0) {
        round(sum(weights[mask]) / total_weight, 4)
      } else {
        NA_real_
      }
    }

    result_list[[i]] <- as.data.frame(props, stringsAsFactors = FALSE)
  }

  prop_df <- do.call(rbind, result_list)

  # Combine with zone IDs
  zone_ids <- st_drop_geometry(zones[, available_ids, drop = FALSE])
  output_df <- cbind(zone_ids, prop_df)

  # --- Validate proportions ---
  prop_cols <- paste0("prop_", target_classes)
  row_sums <- rowSums(output_df[, prop_cols], na.rm = TRUE)
  bad_sums <- sum(row_sums < 0.95 | row_sums > 1.05, na.rm = TRUE)

  if (bad_sums > 0) {
    w$add("warning", "land_cover_proportions",
      sprintf("%d zones have proportions summing outside [0.95, 1.05]. ",
        bad_sums,
        "Some source classes may not be mapped in the crosswalk."))
  }

  # Check for unmapped classes
  all_pixel_vals <- unique(unlist(lapply(lc_extracts, function(x) x$value)))
  all_pixel_vals <- all_pixel_vals[!is.na(all_pixel_vals)]
  mapped_vals <- unlist(mappings)
  unmapped <- setdiff(all_pixel_vals, mapped_vals)

  if (length(unmapped) > 0) {
    w$add("warning", "land_cover_proportions",
      sprintf("Source raster contains classes not in crosswalk: %s. These pixels are excluded from proportions.",
        paste(unmapped, collapse = ", ")))
  }

  write.csv(output_df, output_path, row.names = FALSE)

  primitive_success(
    metadata = list(
      semantic_type = "land_cover_proportions",
      data_category = "tabular",
      n_zones = nrow(zones),
      target_classes = target_classes,
      crosswalk_from = crosswalk$from %||% "unknown",
      crosswalk_to = crosswalk$to %||% "unknown",
      n_unmapped_classes = length(unmapped),
      unmapped_classes = if (length(unmapped) > 0) unmapped else NULL,
      id_fields = available_ids
    ),
    warnings = w
  )

}, warnings = w)