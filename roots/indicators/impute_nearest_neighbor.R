# ============================================================
# roots/indicators/impute_nearest_neighbor.R
# CII's two-stage nearest-neighbour imputation, every value flagged
# ============================================================
# A unit missing exactly one indicator of the set borrows that
# indicator's z-score from a donor, chosen in two stages:
#
#   1. similarity: among units missing nothing, the ten with the
#      smallest sum of absolute z differences across the OTHER
#      indicators of the set
#   2. geography: of those ten, the one closest by great-circle
#      distance between unit locations
#
# Recovered from CII's published file: exactly 461 counties miss
# one indicator, and every one of them has all five pillars and an
# overall index. A unit missing two or more is not imputed; CII
# gives such a county no overall index, and the pillar step here
# does the same. CII's file does not say which values were
# imputed. This output does, on every row: imputed, and from whom.
#
# For exact agreement with canopy/index_oracle.impute(): sums run
# sequentially in declared order, squares are s * s, and every
# ranking breaks ties on the unit code in C-locale order.
#
# Inputs:
#   standings: indicator_standings from standardize_indicator
#   locations: unit_locations with GEOID, latitude, longitude
# Params:
#   indicators:      list of $indicators.<id>, the set compared across
#   k:               donors kept by similarity (default 10)
#   missing_exactly: impute units missing this many (default 1)
# Output:
#   indicator_standings, with imputed z filled and flagged
# ============================================================

library(rewildr)

args <- parse_primitive_args()

standings_path <- get_input(args$inputs, "standings")
locations_path <- get_input(args$inputs, "locations")
output_path    <- args$output
declarations   <- require_param(args$params, "indicators")
k              <- as.integer(get_param(args$params, "k", 10))
missing_exactly <- as.integer(get_param(args$params, "missing_exactly", 1))

w <- warnings_collector("impute_nearest_neighbor")

EARTH_RADIUS_KM <- 6371.0088

haversine_km <- function(lat1, lon1, lat2, lon2) {
  p1 <- lat1 * pi / 180; p2 <- lat2 * pi / 180
  s1 <- sin((p2 - p1) / 2)
  s2 <- sin((lon2 * pi / 180 - lon1 * pi / 180) / 2)
  h <- s1 * s1 + cos(p1) * cos(p2) * (s2 * s2)
  2 * EARTH_RADIUS_KM * asin(sqrt(h))
}

with_primitive_error_handling({

  if (is.data.frame(declarations) || !is.list(declarations) || length(declarations) < 2) {
    primitive_failure("Declarations unusable",
      "`indicators` must list at least two $indicators.<id>, passed as a params file (ARG-1).",
      warnings = w)
  }
  ids <- vapply(declarations, function(d) as.character(d$id), character(1))

  df <- safe_read_table(standings_path, w)
  need <- c("unit_code", "indicator", "z")
  if (length(setdiff(need, names(df))) > 0) {
    primitive_failure("Not standings",
      sprintf("The input lacks %s. Expected the output of standardize_indicator.",
              paste(setdiff(need, names(df)), collapse = ", ")),
      warnings = w)
  }
  absent <- setdiff(ids, unique(df$indicator))
  if (length(absent) > 0) {
    primitive_failure("Indicators not in the standings",
      sprintf("Declared but absent: %s.", paste(absent, collapse = ", ")), warnings = w)
  }

  loc <- safe_read_table(locations_path, w)
  if (length(setdiff(c("GEOID", "latitude", "longitude"), names(loc))) > 0) {
    primitive_failure("Locations unusable",
      "The locations table needs GEOID, latitude and longitude.", warnings = w)
  }
  if (is.numeric(loc$GEOID)) {
    primitive_failure("Location codes are numbers",
      "GEOID arrived as a number, so every code that began with 0 has lost it and would match nothing. Store locations as parquet with GEOID as a string.",
      warnings = w)
  }
  loc_code <- as.character(loc$GEOID)
  lat_of <- setNames(as.numeric(loc$latitude), loc_code)
  lon_of <- setNames(as.numeric(loc$longitude), loc_code)

  sub <- df[df$indicator %in% ids, , drop = FALSE]
  units <- sort(unique(as.character(sub$unit_code)), method = "radix")
  Z <- matrix(NA_real_, nrow = length(units), ncol = length(ids), dimnames = list(units, ids))
  Z[cbind(match(sub$unit_code, units), match(sub$indicator, ids))] <- as.numeric(sub$z)

  reason <- if ("outside_reason" %in% names(sub)) as.character(sub$outside_reason) else rep(NA_character_, nrow(sub))
  declared_out <- unique(sub$unit_code[!is.na(reason) & startsWith(reason, "outside the reference population (state")])
  inside <- units[!units %in% declared_out]
  Zi <- Z[inside, , drop = FALSE]

  n_missing <- rowSums(is.na(Zi))
  donors <- inside[n_missing == 0]
  targets <- inside[n_missing == missing_exactly]
  if (missing_exactly != 1) {
    primitive_failure("Unsupported", "Only units missing exactly one indicator can be imputed this way.", warnings = w)
  }
  if (length(donors) < k) {
    primitive_failure("Too few donors",
      sprintf("%d complete unit(s), fewer than k = %d.", length(donors), k), warnings = w)
  }

  imputed_z <- c(); imputed_from <- c(); target_ind <- c(); sim_of <- c(); km_of <- c(); shortlist_of <- c()
  no_location <- 0

  for (u in targets) {
    m <- which(is.na(Zi[u, ]))
    others <- setdiff(seq_along(ids), m)
    acc <- rep(0, length(donors))
    for (i in others) acc <- acc + abs(Zi[u, i] - Zi[donors, i])
    ord <- order(acc, donors, method = "radix")
    top <- ord[seq_len(min(k, length(ord)))]
    short <- donors[top]
    if (!u %in% loc_code) { no_location <- no_location + 1; next }
    placed <- short[short %in% loc_code]
    if (length(placed) == 0) { no_location <- no_location + 1; next }
    km <- haversine_km(lat_of[[u]], lon_of[[u]], lat_of[placed], lon_of[placed])
    s <- acc[top][short %in% loc_code]
    pick <- order(km, s, placed, method = "radix")[1]
    d <- placed[pick]
    key <- paste(u, ids[m], sep = "|")
    imputed_z[key] <- Zi[d, m]; imputed_from[key] <- d
    sim_of[key] <- s[pick]; km_of[key] <- km[pick]
    shortlist_of[key] <- paste(short, collapse = ",")
  }

  out <- df
  key <- paste(out$unit_code, out$indicator, sep = "|")
  hit <- key %in% names(imputed_z)
  out$imputed <- hit
  out$imputed_from <- ifelse(hit, imputed_from[key], NA_character_)
  out$imputation_similarity <- ifelse(hit, sim_of[key], NA_real_)
  out$imputation_distance_km <- ifelse(hit, km_of[key], NA_real_)
  out$imputation_shortlist <- ifelse(hit, shortlist_of[key], NA_character_)
  out$z[hit] <- imputed_z[key[hit]]
  if ("outside_reason" %in% names(out)) out$outside_reason[hit] <- NA_character_

  n_imp <- sum(hit)
  w$info(sprintf("Imputed %d value(s) for %d unit(s) missing exactly one of %d indicators, from %d complete donor(s), k = %d.",
                 n_imp, length(targets), length(ids), length(donors), k))
  if (no_location > 0) {
    w$warn(sprintf("%d unit(s) could not be imputed: no location for the unit or for any of its ten most similar donors.",
                   no_location))
  }
  n_multi <- sum(n_missing >= 2)
  if (n_multi > 0) {
    w$info(sprintf("%d unit(s) miss two or more indicators and are not imputed; the pillar step gives them only the pillars with no gap.",
                   n_multi))
  }

  safe_write_table(out, output_path, w)

  md <- extract_tabular_metadata(out, id_field = "measurement_id", spatial_unit = "unit")
  md$crs <- NA
  md$analysis_type <- "descriptive"
  md$imputation <- list(
    method = "two-stage nearest neighbour: similarity, then geography",
    similarity = "sum of absolute z differences across the other indicators",
    k = k, missing_exactly = missing_exactly,
    n_imputed = n_imp, n_donors = length(donors), n_not_imputed_no_location = no_location,
    distance = "great-circle, mean Earth radius 6371.0088 km")
  md$interpretation_notes <- as.list(c(
    "Imputed values are flagged on their rows with the donor, similarity, distance and shortlist.",
    "Percentiles are not recomputed for imputed values: CII's per-indicator percentiles precede imputation."))

  primitive_success(metadata = md, warnings = w)

}, warnings = w)
