# ============================================================
# soil/transform/dissolve_by_field.R
# Dissolve polygons into one multipart feature per attribute value
# ============================================================
# General-purpose aggregation. Source boundary data is often held as
# arc-derived polygons ~ one per landmass, per tidal split, per island ~
# while an analysis wants one feature per administrative unit. Maine's
# county layer holds 7,196 polygons for 16 counties, 7,156 of them islands.
#
# This is a REDUCTION and it is declared as one. Feature count collapses,
# geometry becomes multipart, and any attribute that varied within a group
# is lost. None of that is incidental: a denominator built from the wrong
# grain silently divides by the wrong number, and every rate computed from
# it inherits the error with clean provenance. So the collapse is measured
# and reported: how many went in, how many came out, what was dropped and
# why.
#
# The dissolve field becomes the output's id_field, because after a
# dissolve it IS the key ~ one feature per value, by construction. That is
# the join grammar loam projects, handed over honestly rather than minted.
# ============================================================

library(rewildr)
library(sf)

args <- parse_primitive_args()

features_path <- get_input(args$inputs, "features")
output_path   <- args$output

# no safe default: dissolving on the wrong field is a silent, plausible,
# wrong answer, so this must be declared.
field         <- require_param(args$params, "field")

# optional attribute filters, applied before the dissolve. these are
# SEMANTIC choices (exclude islands, exclude water) and each one is named
# in the warnings with how many features it removed.
filters       <- get_param(args$params, "filters", NULL)
drop_blank    <- isTRUE(as.logical(get_param(args$params, "drop_blank", TRUE)))

w <- warnings_collector("dissolve_by_field")

with_primitive_error_handling({

  features <- safe_read_sf(features_path, warnings = w)
  n_start <- nrow(features)

  if (!field %in% names(features)) {
    primitive_failure(
      "Field not found",
      sprintf("Cannot dissolve on '%s': the layer carries %s.",
              field, paste(setdiff(names(features),
                                   attr(features, "sf_column")), collapse = ", ")),
      warnings = w)
  }

  # --- attribute filters, each reported ---
  if (!is.null(filters) && length(filters) > 0) {
    for (fname in names(filters)) {
      keep_value <- as.character(filters[[fname]])
      if (!fname %in% names(features)) {
        w$warn(sprintf("Filter field '%s' not present; filter skipped.", fname))
        next
      }
      before <- nrow(features)
      features <- features[as.character(features[[fname]]) %in% keep_value, ]
      w$add("info", "dissolve_by_field",
        sprintf("Filter %s in (%s): kept %d of %d features (dropped %d).",
                fname, paste(keep_value, collapse = ", "),
                nrow(features), before, before - nrow(features)))
    }
  }

  # --- blank dissolve values ---
  values <- trimws(as.character(features[[field]]))
  n_blank <- sum(values == "" | is.na(values))
  if (n_blank > 0) {
    if (drop_blank) {
      features <- features[!(values == "" | is.na(values)), ]
      values <- trimws(as.character(features[[field]]))
      w$warn(sprintf(
        paste("Dropped %d feature(s) with no '%s' value. These cannot belong",
              "to a unit and would otherwise dissolve into one anonymous",
              "group. Set drop_blank: false to keep them."),
        n_blank, field))
    } else {
      w$warn(sprintf(
        paste("%d feature(s) carry no '%s' value and will dissolve into a",
              "single blank-named group."), n_blank, field))
    }
  }

  if (nrow(features) == 0) {
    primitive_failure(
      "Nothing left to dissolve",
      "Every feature was removed by the filters or the blank-value rule.",
      warnings = w)
  }

  # --- the dissolve ---
  geom_col <- attr(features, "sf_column")
  groups <- unique(trimws(as.character(features[[field]])))
  geoms <- vector("list", length(groups))

  for (i in seq_along(groups)) {
    part <- features[trimws(as.character(features[[field]])) == groups[i], ]
    geoms[[i]] <- sf::st_union(sf::st_geometry(part))
  }

  dissolved <- sf::st_sf(
    setNames(list(groups), field),
    geometry = sf::st_sfc(do.call(c, lapply(geoms, function(g) g[[1]])),
                          crs = sf::st_crs(features))
  )

  n_end <- nrow(dissolved)
  w$add("info", "dissolve_by_field",
    sprintf("Dissolved %d polygon(s) into %d unit(s) by '%s' ~ a %.0fx reduction.",
            nrow(features), n_end, field, nrow(features) / max(n_end, 1)))

  if (n_end == nrow(features)) {
    w$add("info", "dissolve_by_field",
      "Every feature was already its own unit; the dissolve changed nothing.")
  }

  # attributes that varied within a group are GONE, and saying so is the
  # point: a reader who expects them back is reading a reduction as a
  # rename.
  dropped_fields <- setdiff(names(features), c(field, geom_col))
  if (length(dropped_fields) > 0) {
    w$warn(sprintf(
      paste("Dropped %d attribute(s) that could vary within a unit: %s.",
            "A dissolve keeps only the field it grouped on."),
      length(dropped_fields), paste(dropped_fields, collapse = ", ")))
  }

  safe_write_sf(dissolved, output_path, warnings = w)

  meta <- extract_vector_metadata(dissolved, id_field = field)

  primitive_success(
    metadata = modifyList(meta, list(
      # after a dissolve the grouping field IS the key, one feature per
      # value by construction. handed over rather than minted.
      id_field = field,
      spatial_unit = field,
      dissolved_by = field,
      feature_count_before = n_start,
      feature_count_after = n_end,
      features_after_filters = nrow(features),
      blank_dropped = if (drop_blank) n_blank else 0L,
      attributes_dropped = as.list(dropped_fields)
    )),
    warnings = w
  )

}, warnings = w)
