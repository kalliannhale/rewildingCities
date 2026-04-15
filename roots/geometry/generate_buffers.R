# ============================================================
# roots/geometry/generate_buffers.R
# Generate concentric ring (donut) buffers around features
# ============================================================
# Produces ring geometries at specified intervals. Each ring is
# a donut: the area between distance (d-interval) and distance d,
# with the original feature subtracted. This is the geometric
# foundation for TPM-M gradient analysis.
#
# Output: GeoPackage with columns: feature_id, distance_m, geometry
# Each row is one ring for one feature.
# ============================================================

library(rewildr)
library(sf)

args <- parse_primitive_args()

input_path  <- get_input(args$inputs, "features")
output_path <- args$output
interval    <- as.numeric(get_param(args$params, "interval_m", 30))
max_dist    <- as.numeric(get_param(args$params, "max_distance_m", 500))
id_field    <- get_param(args$params, "id_field", NULL)

w <- warnings_collector()

with_primitive_error_handling({

  features <- safe_read_sf(input_path, warnings = w)

  # Determine ID field
  if (is.null(id_field)) {
    # Try common candidates
    candidates <- c("park_id", "feature_id", "id", "ID", "FID")
    id_field <- intersect(candidates, names(features))[1]
    if (is.na(id_field)) {
      # Use row numbers
      features$feature_id <- seq_len(nrow(features))
      id_field <- "feature_id"
      w$add("info", "generate_buffers",
        "No ID field found. Using row numbers as feature_id.")
    }
  }

  distances <- seq(interval, max_dist, by = interval)
  n_features <- nrow(features)
  n_rings <- length(distances)

  w$add("info", "generate_buffers",
    sprintf("Generating %d rings (%gm to %gm at %gm intervals) for %d features.",
      n_rings, interval, max_dist, interval, n_features))

  # Pre-allocate list
  ring_list <- vector("list", n_features * n_rings)
  idx <- 0L

  for (i in seq_len(n_features)) {
    feat <- features[i, ]
    feat_id <- feat[[id_field]]

    for (j in seq_along(distances)) {
      idx <- idx + 1L
      d_outer <- distances[j]
      d_inner <- d_outer - interval

      tryCatch({
        outer_buf <- st_buffer(feat, dist = d_outer)

        if (d_inner > 0) {
          inner_buf <- st_buffer(feat, dist = d_inner)
          ring <- st_difference(outer_buf, inner_buf)
        } else {
          # First ring: donut between feature boundary and first distance
          ring <- st_difference(outer_buf, feat)
        }

        ring_list[[idx]] <- st_sf(
          feature_id = feat_id,
          distance_m = d_outer,
          geometry = st_geometry(ring)
        )
      }, error = function(e) {
        # Skip this ring, log warning
        w$add("warning", "generate_buffers",
          sprintf("Ring at %gm for feature %s failed: %s",
            d_outer, feat_id, e$message))
      })
    }
  }

  # Combine, dropping NULLs from failed rings
  ring_list <- ring_list[!sapply(ring_list, is.null)]
  rings <- do.call(rbind, ring_list)

  n_success <- nrow(rings)
  n_expected <- n_features * n_rings
  if (n_success < n_expected) {
    w$add("warning", "generate_buffers",
      sprintf("%d of %d rings failed geometry construction.",
        n_expected - n_success, n_expected))
  }

  safe_write_sf(rings, output_path, warnings = w)

  meta <- extract_vector_metadata(rings)

  primitive_success(
    metadata = c(meta, list(
      n_features = n_features,
      n_distances = n_rings,
      interval_m = interval,
      max_distance_m = max_dist,
      n_rings_produced = n_success,
      id_field = id_field
    )),
    warnings = w
  )

}, warnings = w)