# ============================================================
# soil/transform/derive_indicator.R  (was roots/indicators/, moved by D-99)
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
# measurement tuple (unit, indicator, value, published_by, method, time)
# so a second publisher's claim about the same county can sit beside
# this one later without a schema change. D-19.
#
# A unit is an (authority, code) pair, and a Census GEOID is unique only
# within its level: 23001 is Androscoggin County, House District 1 and
# Senate District 1 (GRAPH-1). So the caller declares whose codes these
# are, from Contract 3, section 1, with no default, and the declaration is
# written on every row and into every measurement_id (D-131, D-132).
#
# What it deliberately does not do:
#   ~ derive a margin of error for a ratio. The registry cannot yet
#     say whether a ratio is a proportion, and the Census formulas
#     differ; a margin from the wrong one is a plausible wrong number.
#     Ratio rows say `not_derived`. A passthrough's margin is the
#     published one. D-18, IND-3.
#   ~ round. Replication is checked at full precision.
#   ~ guess why a value is empty. Since ACS-7 the provider keeps each
#     Census code it emptied in a <variable>_annotation column. The one
#     read here is -333333333 on a passthrough's margin: a median in an
#     open-ended category, written as a `bound` ("50.0 or more"), not
#     as a measurement. The value stays the Census's encoding (51, 9),
#     which sorts correctly, so a rank over it is still right.
#
# canopy/indicators/preview.py does the same arithmetic in Python. The
# two must agree exactly; tests/test_derive_indicator_oracle.py holds
# them to it. D-16.
#
# Inputs:
#   source: an indicator_source table (parquet or CSV), one row per unit
# Params:
#   unit_authority: required, whose codes name the units, one of
#                 Contract 3's five (D-131): us_census_geoid (state,
#                 county, town, tract), us_census_sldl (Maine House),
#                 us_census_sldu (Maine Senate), us_census_aiannh (Census
#                 tribal area), megis (Maine civil division)
#   indicators:   list of declarations, each from $indicators.<id>
#   spatial_unit: what each row is, e.g. "county"
#   time:         the vintage window of the source, e.g. "2020-2024"
#   published_by: who published the source, e.g. "us_census_acs" (D-187)
#   joins_to:     semantic type of the units this table joins to
#   unit_column:  the source column naming each unit (default "GEOID")
#   unit_pad:     zero-pad unit codes to this width, for a published file
#                 that lost leading zeros (CII-6); default none
#   name_column:  the source column with a readable name (default "NAME")
#   reliability:  optional, the declared small-sample rule (D-106):
#                 {min_households, max_cv}. Without it, no reliability note.
# Every value also says what it rests on (Sprint 02): the count from its
# declaration's `rests_on`, add minus subtract, or why there is none. An
# open-ended median's value rests empty, its bound in words (D-105).
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
published_by <- get_param(args$params, "published_by", NA_character_)
joins_to     <- get_param(args$params, "joins_to", NULL)
unit_authority <- get_param(args$params, "unit_authority", NULL)
unit_column  <- as.character(get_param(args$params, "unit_column", "GEOID"))
unit_pad     <- get_param(args$params, "unit_pad", NULL)
name_column  <- as.character(get_param(args$params, "name_column", "NAME"))
reliability  <- get_param(args$params, "reliability", NULL)

w <- warnings_collector("derive_indicator")

# the publisher was `authority` until D-187. that word now means only who
# assigns a unit's code, so the old param is refused by name, never read:
# read, it would leave every value with no publisher and no boundary rule.
if (!is.null(args$params[["authority"]])) {
  primitive_failure(
    "Renamed parameter",
    paste0("`authority` is now `published_by`: it names who published the ",
           "source, and `authority` means only who assigns a unit's code (D-187)."),
    warnings = w)
}

# Contract 3, section 1. Also written in build_places.py and
# canopy/indicators/preview.py until one seed file holds them (AUTH-1).
KNOWN_UNIT_AUTHORITIES <- c("us_census_geoid", "us_census_sldl", "us_census_sldu",
                            "us_census_aiannh", "megis")

# Refused by name, never defaulted: a silent default is how a House
# district came to key as a county (GRAPH-1, D-131).
.unit_authority <- function(x) {
  x <- if (is.null(x)) character(0) else trimws(as.character(unlist(x)))
  if (length(x) != 1 || is.na(x) || !nzchar(x)) {
    primitive_failure(
      "No unit authority",
      paste0("`unit_authority` is required: whose codes name these units, one of ",
             paste(KNOWN_UNIT_AUTHORITIES, collapse = ", "),
             " (Contract 3, section 1). A Census GEOID is unique only within its ",
             "level, so 23001 is a county, a House district and a Senate district ",
             "(GRAPH-1, D-131)."),
      warnings = w)
  }
  if (!x %in% KNOWN_UNIT_AUTHORITIES) {
    primitive_failure(
      "Unknown unit authority",
      sprintf("`unit_authority` '%s' is not one of %s (Contract 3, section 1; D-131).",
              x, paste(KNOWN_UNIT_AUTHORITIES, collapse = ", ")),
      warnings = w)
  }
  x
}

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

# What a value rests on: the count behind it, from the declaration's
# rests_on, add minus subtract, in the same row of the same release. Returns
# the counts and, where there is none, why. preview._rests_on is its twin.
.rests_on <- function(df, ro) {
  n <- nrow(df)
  if (is.null(ro)) {
    primitive_failure(
      "Malformed declaration",
      "A declaration has no `rests_on`. Declarations come from $indicators.<id>, which always carries it (Sprint 02).",
      warnings = w)
  }
  if (!is.null(ro$not_published)) {
    return(list(count = rep(NA_real_, n), reason = rep(as.character(ro$not_published), n)))
  }
  add <- unlist(ro$add)
  sub <- unlist(ro$subtract)
  vars <- c(add, sub)
  m <- as.data.frame(lapply(vars, function(v) as.numeric(df[[v]])))
  names(m) <- vars
  empty <- apply(is.na(as.matrix(m)), 1, function(row) paste(vars[row], collapse = ", "))
  count <- rowSums(as.matrix(m[, add, drop = FALSE]))
  if (length(sub) > 0) count <- count - rowSums(as.matrix(m[, sub, drop = FALSE]))
  count[empty != ""] <- NA_real_
  reason <- ifelse(empty != "", paste0("source count empty: ", empty), NA_character_)
  list(count = count, reason = reason)
}

# The declared small-sample rule, in plain words (D-106). The same strings as
# preview._reliability_note: counts as %.0f, percentages as %.1f, on both sides.
.reliability_note <- function(value, households, counts, cv, rule) {
  n <- length(value)
  if (is.null(rule)) return(rep(NA_character_, n))
  floor_h <- rule$min_households
  ceiling_cv <- rule$max_cv
  label <- if (is.null(counts)) "households" else counts
  vapply(seq_len(n), function(i) {
    if (is.na(value[i])) return(NA_character_)
    said <- character(0)
    if (!is.null(floor_h) && !is.na(households[i]) && households[i] < floor_h) {
      said <- c(said, sprintf("rests on %.0f %s, fewer than the %.0f the small-sample rule asks for",
                              households[i], label, floor_h))
    }
    if (!is.null(ceiling_cv) && !is.na(cv[i]) && cv[i] > ceiling_cv) {
      said <- c(said, sprintf("its margin of error is wide: a coefficient of variation of %.1f%%, above the %.1f%% the small-sample rule allows",
                              cv[i] * 100, ceiling_cv * 100))
    }
    if (length(said) == 0) return(NA_character_)
    paste0("read with care: ", paste(said, collapse = "; and "), ".")
  }, character(1))
}

# ACS-7. The Census code on a median's margin meaning the median falls
# in the lowest or highest category. preview.py holds the same constant.
OPEN_ENDED <- -333333333

# What an open-ended median claims, in words. preview._bound_label writes
# the same strings; the oracle test holds the two to each other.
.bound_label <- function(v, edges) {
  if (is.null(edges)) return(rep("open-ended interval (edges not declared)", length(v)))
  lo <- as.numeric(edges$lower)
  hi <- as.numeric(edges$upper)
  ifelse(v >= hi, sprintf("%.1f or more", hi),
         ifelse(v < lo, sprintf("less than %.1f", lo),
                "open-ended interval (value inside the declared edges)"))
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

  unit_authority <- .unit_authority(unit_authority)
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

    ro <- d$rests_on
    if (is.null(ro$not_published)) needed <- c(needed, unlist(ro$add), unlist(ro$subtract))
    absent <- setdiff(needed, names(df))
    if (length(absent) > 0) {
      primitive_failure(
        "Source missing variables",
        paste0(sprintf("Indicator '%s' needs %s, which the source does not hold. ",
                       id, paste(absent, collapse = ", ")),
               "It was probably acquired before this indicator was listed; re-acquire the source."),
        warnings = w)
    }

    # the value's own emptiness is judged on what derives it, not on the
    # count it rests on; an empty count is reported in households_reason.
    value_vars <- if (kind == "ratio") c(numerator, denominator) else column
    reason <- .empty_reason(df, value_vars)
    moe <- rep(NA_real_, nrow(df))
    bound <- rep(NA_character_, nrow(df))

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

      ann_col <- paste0(moe_col, "_annotation")
      edges <- der$open_ended
      if (ann_col %in% names(df)) {
        code <- suppressWarnings(as.numeric(as.character(df[[ann_col]])))
        open <- !is.na(value) & !is.na(code) & code == OPEN_ENDED
        if (any(open)) {
          moe_status[open] <- "open_ended"
          bound[open] <- .bound_label(value[open], edges)
          # D-105: the encoding is not a measurement. The value rests empty,
          # the bound says what is known, and no ranking can use it.
          value[open] <- NA_real_
          moe[open] <- NA_real_
          reason[open] <- paste0("open-ended median: ", bound[open])
          w$info(sprintf(
            "%s: %d unit(s) have an open-ended median, so their value rests empty (D-105): the Census publishes only the end category, and `bound` says which, in words. They stand outside any ranking.",
            id, sum(open)))
          odd <- open & startsWith(bound, "open-ended interval")
          if (any(odd)) {
            w$warn(sprintf(
              "%s: %d open-ended median(s) could not be placed past a declared edge (%s). Declare or check `open_ended`.",
              id, sum(odd), bound[odd][1]))
          }
        }
      } else if (!is.null(edges)) {
        w$warn(sprintf(
          "%s declares open-ended edges but the source has no %s column, so no open-ended median can be recognised. It was probably acquired before ACS-7; re-acquire the source.",
          id, ann_col))
      }
    }

    rest <- .rests_on(df, ro)
    cv <- rep(NA_real_, nrow(df))
    has_cv <- !is.na(value) & !is.na(moe) & moe_status == "published" & value != 0
    cv[has_cv] <- (moe[has_cv] / 1.645) / abs(value[has_cv])
    note <- .reliability_note(value, rest$count, ro$counts, cv, reliability)

    n_empty <- sum(is.na(value))
    if (n_empty > 0) {
      w$warn(paste0(
        sprintf("%s: %d of %d unit(s) have no value. ", id, n_empty, nrow(df)),
        "Where the reason is an empty source value, the Census code behind it is in the source's <variable>_annotation column when it was acquired after ACS-7."))
    }

    pieces[[length(pieces) + 1]] <- data.frame(
      # indicator:authority:code, so ids stay unique when tables from
      # different levels are read together (D-132)
      measurement_id = paste(id, unit_authority, geoid, sep = ":"),
      unit_authority = unit_authority,
      unit_code      = geoid,
      name           = unit_name,
      indicator      = id,
      value          = value,
      moe            = moe,
      moe_status     = moe_status,
      bound          = bound,
      empty_reason   = reason,
      households     = rest$count,
      households_counts = if (is.null(ro$counts)) NA_character_ else ro$counts,
      households_reason = rest$reason,
      cv             = cv,
      reliability_note = note,
      published_by   = published_by,
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