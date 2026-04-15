# ============================================================
# roots/geometry/calculate_geometry.R
# Calculate geometric properties of vector features
# ============================================================
# Computes area, perimeter, centroid coordinates, and bounding
# box dimensions for each feature. Used as an early step to
# attach geometric attributes before downstream analysis.
# ============================================================

library(rewildr)
library(sf)

args <- parse_primitive_args()

input_path  <- get_input(args$inputs, "features")
output_path <- args$output
id_field    <- get_param(args$params, "id_field", NULL)

w <- warnings_collector()

with_primitive_error_handling({

  features <- safe_read_sf(input_path, warnings = w)

  if (is.null(id_field)) {
    candidates <- c("park_id", "feature_id", "id", "ID")
    id_field <- intersect(candidates, names(features))[1]
    if (is.na(id_field)) {
      features$feature_id <- seq_len(nrow(features))
      id_field <- "feature_id"
    }
  }

  # Area and perimeter
  areas_m2 <- as.numeric(st_area(features))
  perimeters_m <- tryCatch({
    as.numeric(st_length(st_cast(st_boundary(features), "MULTILINESTRING")))
  }, error = function(e) {
    w$add("warning", "calculate_geometry",
      sprintf("Perimeter calculation failed: %s. Using NA.", e$message))
    rep(NA_real_, nrow(features))
  })

  # Centroids
  centroids <- st_centroid(features, of_largest_polygon = TRUE)
  coords <- st_coordinates(centroids)

  # Bounding box per feature
  bboxes <- t(sapply(seq_len(nrow(features)), function(i) {
    bb <- st_bbox(features[i, ])
    c(bb_width = bb["xmax"] - bb["xmin"],
      bb_height = bb["ymax"] - bb["ymin"])
  }))

  result_df <- data.frame(
    feature_id = features[[id_field]],
    area_m2 = round(areas_m2, 2),
    area_ha = round(areas_m2 / 10000, 4),
    perimeter_m = round(perimeters_m, 2),
    centroid_x = round(coords[, 1], 2),
    centroid_y = round(coords[, 2], 2),
    bbox_width = round(bboxes[, 1], 2),
    bbox_height = round(bboxes[, 2], 2),
    stringsAsFactors = FALSE
  )

  write.csv(result_df, output_path, row.names = FALSE)

  primitive_success(
    metadata = list(
      semantic_type = "feature_geometry",
      data_category = "tabular",
      n_features = nrow(features),
      area_range_ha = as.list(round(range(areas_m2 / 10000), 4)),
      id_field = id_field
    ),
    warnings = w
  )

}, warnings = w)