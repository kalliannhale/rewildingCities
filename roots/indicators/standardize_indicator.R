# ============================================================
# roots/indicators/standardize_indicator.R
# where each unit stands among a declared reference population
# ============================================================
# Two numbers per unit and indicator, both relative:
#
#   z           (oriented value - mean) / sd, where oriented means
#               negated for a higher_is_worse indicator, so a higher
#               z is always the better standing
#   percentile  CII's: the average rank of the oriented value,
#               divided by the LARGEST rank, times 100
#
# The percentile rule was recovered from CII's own published file.
# It reproduces 26 of CII's 27 per-indicator percentile columns
# across all 3 144 counties to their rounding (CII-8). Dividing by
# the largest rank rather than by n only matters when the top value
# is tied, and then it matters a great deal: rank / n would put
# CII's news outlet percentiles 22 points off.
#
# The z-score cannot be checked against CII, which does not publish
# one, so whether its SD divides by n - 1 or n is a required choice.
#
# A standing says how a unit compares, never whether its value is
# enough. If every county had poor broadband, the top one would
# still stand at 100. The reference population is declared, never
# inferred from whichever rows happen to be present: units with a
# value, outside any excluded states. A unit outside it keeps its
# row, with no standing and the reason why.
#
# canopy/indicator_preview.standings() does the same in Python; the
# two are held to each other by tests/test_standardize_oracle.py.
#
# Inputs:
#   values: indicator_values, long-form, from derive_indicator
# Params:
#   indicators:         list of $indicators.<id>, for each direction
#   sd:                 "sample" or "population", no default
#   exclude_state_fips: state FIPS outside the population, e.g. ["72"]
# Output:
#   indicator_standings, long-form, format from the output extension
# ============================================================

library(rewildr)

args <- parse_primitive_args()

values_path  <- get_input(args$inputs, "values")
output_path  <- args$output
declarations <- require_param(args$params, "indicators")
sd_rule      <- as.character(require_param(args$params, "sd"))
excluded     <- as.character(unlist(get_param(args$params, "exclude_state_fips", list())))

w <- warnings_collector("standardize_indicator")

with_primitive_error_handling({

  if (!sd_rule %in% c("sample", "population")) {
    primitive_failure(
      "Unknown SD convention",
      sprintf("sd '%s' must be \"sample\" or \"population\". There is no default: CII does not publish its z-scores, so the choice cannot be recovered and must be made in the open.", sd_rule),
      warnings = w)
  }
  if (is.data.frame(declarations) || !is.list(declarations) || length(declarations) == 0) {
    primitive_failure(
      "Declarations unusable",
      "`indicators` must be a non-empty list of $indicators.<id> declarations, passed as a params file (ARG-1).",
      warnings = w)
  }

  df <- safe_read_table(values_path, w)
  need <- c("indicator", "unit_code", "value")
  absent <- setdiff(need, names(df))
  if (length(absent) > 0) {
    primitive_failure(
      "Not long-form indicator values",
      sprintf("The input lacks %s. Expected the output of derive_indicator.",
              paste(absent, collapse = ", ")),
      warnings = w)
  }

  direction_of <- setNames(
    vapply(declarations, function(d) as.character(d$direction %||% NA), character(1)),
    vapply(declarations, function(d) as.character(d$id %||% NA), character(1)))

  in_table <- sort(unique(df$indicator))
  undeclared <- setdiff(in_table, names(direction_of))
  unused <- setdiff(names(direction_of), in_table)
  if (length(undeclared) > 0 || length(unused) > 0) {
    primitive_failure(
      "Declarations do not match the table",
      paste0(
        if (length(undeclared)) sprintf("In the table but not declared: %s. ", paste(undeclared, collapse = ", ")) else "",
        if (length(unused)) sprintf("Declared but not in the table: %s. ", paste(unused, collapse = ", ")) else "",
        "Every indicator standardised needs its direction stated, and every one stated must be present."),
      warnings = w)
  }
  bad_dir <- names(direction_of)[!direction_of %in% c("higher_is_better", "higher_is_worse")]
  if (length(bad_dir) > 0) {
    primitive_failure(
      "No direction",
      sprintf("No usable direction for: %s.", paste(bad_dir, collapse = ", ")),
      warnings = w)
  }

  pieces <- list()
  populations <- list()
  CARRIED <- c("empty_reason", "bound", "households", "households_counts",
               "households_reason", "reliability_note")

  for (id in in_table) {
    rows <- df[df$indicator == id, , drop = FALSE]
    sign <- if (direction_of[[id]] == "higher_is_better") 1 else -1
    value <- as.numeric(rows$value)
    state <- substr(as.character(rows$unit_code), 1, 2)

    outside <- ifelse(is.na(value), "no value",
               ifelse(state %in% excluded,
                      paste0("outside the reference population (state ", state, " excluded)"),
                      NA_character_))
    inside <- is.na(outside)
    n <- sum(inside)
    if (n < 2) {
      primitive_failure(
        "Reference population too small",
        sprintf("%s: %d unit(s) in the reference population; at least 2 are needed.", id, n),
        warnings = w)
    }

    oriented <- sign * value[inside]
    r <- rank(oriented, ties.method = "average")
    m <- mean(oriented)
    s <- if (sd_rule == "sample") stats::sd(oriented) else sqrt(sum((oriented - m)^2) / n)

    z <- rep(NA_real_, nrow(rows))
    pct <- rep(NA_real_, nrow(rows))
    pct[inside] <- r / max(r) * 100
    if (s > 0) {
      z[inside] <- (oriented - m) / s
    } else {
      outside[inside] <- "no variation in the reference population"
      w$warn(sprintf("%s: every unit in the reference population has the same value, so no z-score exists. A state value broadcast to counties looks exactly like this.", id))
    }

    n_out <- sum(!inside)
    if (n_out > 0) {
      w$info(sprintf("%s: %d of %d unit(s) are outside the reference population and keep their rows with no standing.",
                     id, n_out, nrow(rows)))
    }

    pieces[[length(pieces) + 1]] <- data.frame(
      measurement_id = if ("measurement_id" %in% names(rows)) rows$measurement_id else paste(id, rows$unit_code, sep = ":"),
      unit_authority = if ("unit_authority" %in% names(rows)) rows$unit_authority else NA_character_,
      unit_code      = as.character(rows$unit_code),
      name           = if ("name" %in% names(rows)) rows$name else "",
      indicator      = id,
      value          = value,
      direction      = direction_of[[id]],
      z              = z,
      percentile     = pct,
      outside_reason = outside,
      reference_n    = n,
      method         = paste0("standardize_indicator:sd_", sd_rule, ":cii_percentile"),
      time           = if ("time" %in% names(rows)) rows$time else NA_character_,
      stringsAsFactors = FALSE
    )
    # what each value rests on travels with its standing (Sprint 02): a
    # ranked value never loses its count, its reason, or its caveat. carried
    # unchanged from derive_indicator, NA where an older input lacks them.
    for (col in CARRIED) {
      piece <- pieces[[length(pieces)]]
      piece[[col]] <- if (col %in% names(rows)) rows[[col]] else NA
      pieces[[length(pieces)]] <- piece
    }
    populations[[id]] <- list(n = n, mean_oriented = m, sd = s)
  }

  out <- do.call(rbind, pieces)

  w$info(paste0(
    sprintf("Standardised %d indicator(s) with sd = %s, excluding state(s): %s. ",
            length(in_table), sd_rule, if (length(excluded)) paste(excluded, collapse = ", ") else "none"),
    "The percentile is checkable against CII; the z-score is not, because CII does not publish one."))

  safe_write_table(out, output_path, w)

  md <- extract_tabular_metadata(out, id_field = "measurement_id", spatial_unit = "unit")
  md$crs <- NA
  md$analysis_type <- "descriptive"
  md$indicators <- as.list(in_table)
  md$reference_population <- list(
    rule = "units with a value, outside excluded states",
    excluded_state_fips = as.list(excluded),
    sd = sd_rule,
    per_indicator = populations)
  md$interpretation_notes <- as.list(c(
    "A standing is relative: it says how a unit compares, never whether its value is sufficient.",
    "z is oriented so that higher is always the better standing; it is not checkable against CII.",
    "percentile follows CII's rule: average rank over the largest rank, times 100."))

  primitive_success(metadata = md, warnings = w)

}, warnings = w)
