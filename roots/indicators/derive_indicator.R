# ============================================================
# roots/indicators/derive_indicator.R
# indicator values from raw published counts, by declaration
# ============================================================
# The registry (seeds/indicators/) says what an indicator is: which
# numerator over which denominator, at what scale, or which published
# column passes through untouched. The orchestrator resolves each
# `$indicators.<id>` into that declaration and hands it here as a
# param, so this primitive never reads YAML and never decides what an
# indicator means. It only does the arithmetic it is told, and says
# so on every row. D-33.
#
# Output is long-form: one row per (unit, indicator), carrying the
# measurement tuple (unit, indicator, value, authority, method, time)
# so a second authority's claim about the same county can sit beside
# this one later without a schema change. D-19.
#
# What it deliberately does not do:
#   ~ derive a margin of error for a ratio. The registry cannot yet
#     say whether a ratio is a proportion, and the Census formulas
#     differ; a margin from the wrong one is a plausible wrong number.
#     Ratio rows say `not_derived`. A passthrough's margin is the
#     published one. D-18, IND-3.
#   ~ round. Replication is checked at full precision.
#   ~ guess why a value is empty. The provider keeps only a count of
#     the Census annotations it emptied (ACS-5).
#
# canopy/indicator_preview.py does the same arithmetic in Python. The
# two must agree exactly; tests/test_derive_indicator_oracle.py holds
# them to it. D-16.
#
# Inputs:
#   source: an indicator_source table (parquet or CSV) with GEOID
# Params:
#   indicators:   list of declarations, each from $indicators.<id>
#   spatial_unit: what each row is, e.g. "county"
#   time:         the vintage window of the source, e.g. "2020-2024"
#   authority:    who published the source, e.g. "us_census_acs"
#   joins_to:     semantic type of the units this table joins to
#   unit_column:  the source column naming each unit (default "GEOID")
#   unit_pad:     zero-pad unit codes to this width, for a published file
#                 that lost leading zeros (CII-6); default none
#   name_column:  the source column with a readable name (default "NAME")
# Output:
#   indicator_values, long-form, format from the output extension
# ============================================================

library(rewildr)

args <- parse_primitive_args()

source_path  <- get_input(args$inputs, "source")
output_path  <- args$output
declarations <- require_param(args$params, "indicators")
spatial_unit <- require_param(args$params, "spatial_unit")
time_label   <- get_param(args$params, "time", NA_character_)
authority    <- get_param(args$params, "authority", NA_character_)
joins_to     <- get_param(args$params, "joins_to", NULL)
unit_column  <- as.character(get_param(args$params, "unit_column", "GEOID"))
unit_pad     <- get_param(args$params, "unit_pad", NULL)
name_column  <- as.character(get_param(args$params, "name_column", "NAME"))

w <- warnings_collector("derive_indicator")

UNIT_AUTHORITY <- "us_census_geoid"

# Params from the orchestrator arrive through a file and read_json, which
# keeps a list of declarations as a list of lists. Inline JSON simplifies
# the same list into a data.frame whose nested fields are not recoverable
# cleanly. Refused by name rather than half-parsed (ARG-1).
.declarations_as_list <- function(x) {
  if (is.data.frame(x)) {
    primitive_failure(
      "Declarations arrived simplified",
      paste0("`indicators` arrived as a data.frame, which happens when params ",
             "are passed as inline JSON rather than a file. Pass params as a ",
             "JSON file, as the orchestrator does (ARG-1)."),
      warnings = w)
  }
  if (!is.list(x) || length(x) == 0) {
    primitive_failure(
      "No declarations",
      "`indicators` must be a non-empty list of $indicators.<id> declarations.",
      warnings = w)
  }
  x
}

.field <- function(d, name) {
  v <- d[[name]]
  if (is.null(v)) {
    primitive_failure(
      "Malformed declaration",
      sprintf("Declaration '%s' has no `%s`. Declarations come from $indicators.<id>; a hand-written one is not trusted.",
              d$id %||% "(unnamed)", name),
      warnings = w)
  }
  v
}

# Which of these variables is empty on each row, joined the way the preview
# joins them, so a reason reads identically from either implementation.
.empty_reason <- function(df, vars) {
  vapply(seq_len(nrow(df)), function(i) {
    empty <- vars[vapply(vars, function(v) is.na(df[[v]][i]), logical(1))]
    if (length(empty) == 0) NA_character_
    else paste0("source value empty: ", paste(empty, collapse = ", "))
  }, character(1))
}

with_primitive_error_handling({

  declarations <- .declarations_as_list(declarations)
  df <- safe_read_table(source_path, w)

  if (!unit_column %in% names(df)) {
    primitive_failure(
      "No unit key",
      sprintf("The source has no '%s' column, so no row can be named as a unit.", unit_column),
      warnings = w)
  }
  geoid <- trimws(as.character(df[[unit_column]]))
  if (!is.null(unit_pad)) {
    width <- as.integer(unit_pad)
    bad <- !grepl("^[0-9]+$", geoid) | nchar(geoid) > width
    if (any(bad)) {
      primitive_failure(
        "Unusable unit codes",
        sprintf("%d code(s) in '%s' are not digits or are wider than %d, e.g. %s. Padding would invent a different unit.",
                sum(bad), unit_column, width, geoid[bad][1]),
        warnings = w)
    }
    n_short <- sum(nchar(geoid) < width)
    geoid <- formatC(geoid, width = width, flag = "0")
    geoid <- gsub(" ", "0", geoid)
    if (n_short > 0) {
      w$info(sprintf("%d unit code(s) in '%s' had lost leading zeros and were padded to %d digits.",
                     n_short, unit_column, width))
    }
  }
  if (any(duplicated(geoid))) {
    primitive_failure(
      "Unit codes not unique",
      sprintf("%d unit code(s) appear more than once, e.g. %s.", sum(duplicated(geoid)), geoid[duplicated(geoid)][1]),
      warnings = w)
  }
  unit_name <- if (name_column %in% names(df)) as.character(df[[name_column]]) else rep("", nrow(df))

  pieces <- list()
  ids <- character(0)
  n_ratio <- 0

  for (d in declarations) {
    id   <- .field(d, "id")
    der  <- .field(d, "derivation")
    kind <- .field(der, "kind")
    ids  <- c(ids, id)

    if (kind == "ratio") {
      numerator   <- unlist(.field(der, "numerator"))
      denominator <- .field(der, "denominator")
      scale       <- as.numeric(.field(der, "scale"))
      needed      <- c(numerator, denominator)
    } else if (kind == "passthrough") {
      column <- .field(der, "column")
      needed <- column
    } else {
      primitive_failure(
        "Unknown derivation kind",
        sprintf("Indicator '%s' declares kind '%s'; this primitive knows ratio and passthrough.",
                id, kind),
        warnings = w)
    }

    absent <- setdiff(needed, names(df))
    if (length(absent) > 0) {
      primitive_failure(
        "Source missing variables",
        paste0(sprintf("Indicator '%s' needs %s, which the source does not hold. ",
                       id, paste(absent, collapse = ", ")),
               "It was probably acquired before this indicator was listed; re-acquire the source."),
        warnings = w)
    }

    reason <- .empty_reason(df, needed)
    moe <- rep(NA_real_, nrow(df))

    if (kind == "ratio") {
      n_ratio <- n_ratio + 1
      num <- rowSums(as.matrix(df[, numerator, drop = FALSE]))
      den <- as.numeric(df[[denominator]])
      value <- (num / den) * scale
      zero <- is.na(reason) & !is.na(den) & den == 0
      value[zero] <- NA_real_
      reason[zero] <- "zero denominator"
      value[!is.na(reason)] <- NA_real_
      moe_status <- rep("not_derived", nrow(df))
    } else {
      value <- as.numeric(df[[column]])
      moe_col <- sub("E$", "M", column)
      if (moe_col %in% names(df)) moe <- as.numeric(df[[moe_col]])
      moe_status <- ifelse(is.na(moe), "absent", "published")
    }

    n_empty <- sum(is.na(value))
    if (n_empty > 0) {
      w$warn(paste0(
        sprintf("%s: %d of %d unit(s) have no value. ", id, n_empty, nrow(df)),
        "Where the reason is an empty source value, the Census annotation behind it is not recoverable here (ACS-5)."))
    }

    pieces[[length(pieces) + 1]] <- data.frame(
      measurement_id = paste(id, geoid, sep = ":"),
      unit_authority = UNIT_AUTHORITY,
      unit_code      = geoid,
      name           = unit_name,
      indicator      = id,
      value          = value,
      moe            = moe,
      moe_status     = moe_status,
      empty_reason   = reason,
      authority      = authority,
      method         = paste0("derive_indicator:", kind),
      time           = time_label,
      stringsAsFactors = FALSE
    )
  }

  out <- do.call(rbind, pieces)

  if (n_ratio > 0) {
    w$info(paste0(
      sprintf("%d ratio indicator(s): margin of error not derived. ", n_ratio),
      "The registry cannot yet say whether a ratio is a proportion, and the Census formulas differ (D-18, IND-3)."))
  }
  w$info(sprintf("Derived %d indicator(s) for %d %s unit(s): %s.",
                 length(ids), nrow(df), spatial_unit, paste(ids, collapse = ", ")))

  safe_write_table(out, output_path, w)

  md <- extract_tabular_metadata(out, id_field = "measurement_id", spatial_unit = spatial_unit)
  md$crs <- NA
  md$analysis_type <- "descriptive"
  md$indicators <- as.list(ids)
  md$interpretation_notes <- as.list(c(
    "Long-form: one row per unit and indicator. Pivot on `indicator` to map one.",
    "Values are at full precision; nothing is rounded.",
    if (n_ratio > 0) "Ratio rows carry no derived margin of error (moe_status not_derived)."
  ))
  if (!is.null(joins_to)) md$joins_to <- joins_to

  primitive_success(metadata = md, warnings = w)

}, warnings = w)