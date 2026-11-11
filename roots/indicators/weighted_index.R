# ============================================================
# roots/indicators/weighted_index.R
# a weighted mean of declared components, then CII's percentile
# ============================================================
# Two uses, one rule:
#
#   level "pillars"    each pillar's weighted mean of its
#                      indicators' z-scores, from standings
#   level "composite"  the weighted mean of the five pillar
#                      percentiles, from this primitive's own
#                      pillar output
#
# A unit gets an index only when every component is present. A
# pillar with a gap is dropped, never averaged over what remains,
# and the composite needs all five pillars. Both rules were
# recovered from CII's file: a county missing two or more
# indicators keeps only the pillars with no gap, and has no overall
# index. Imputation (impute_nearest_neighbor) runs first, so a
# county missing exactly one indicator keeps everything.
#
# Weights arrive as $weights.<id>, a declared and hashed artifact.
# CII's own allocation is unpublished; every output row says which
# weighting produced it, and whether that weighting is CII's.
#
# The percentile is CII's: average rank over the largest rank,
# times 100 (CII-8). Held to canopy/index_oracle.weighted_index().
#
# A unit is an (authority, code) pair (D-19, Contract 3 section 1), so
# every row carries its unit_authority and its id is
# index:unit_authority:code, as every value's is (D-132). An index ranks
# units against each other, so all of them must be under one authority:
# counties ranked beside districts were never measured beside each other,
# and that is refused by name, not averaged (SEAM-1, D-190).
#
# Inputs:
#   components: indicator_standings (pillars) or indicator_index (composite),
#               each row carrying its unit_authority
# Params:
#   weights: $weights.<id>
#   level:   "pillars" or "composite"
# Output:
#   indicator_index, long-form: one row per unit and index
# ============================================================

library(rewildr)

args <- parse_primitive_args()

input_path  <- get_input(args$inputs, "components")
output_path <- args$output
weights     <- require_param(args$params, "weights")
level       <- as.character(require_param(args$params, "level"))

w <- warnings_collector("weighted_index")

cii_percentile <- function(x) {
  r <- rank(x, ties.method = "average")
  r / max(r) * 100
}

with_primitive_error_handling({

  if (!level %in% c("pillars", "composite")) {
    primitive_failure("Unknown level", "level must be \"pillars\" or \"composite\".", warnings = w)
  }
  pillars <- weights$pillars
  if (is.null(pillars) || length(pillars) == 0) {
    primitive_failure("No pillars", "The weighting declares no pillars. Pass it as $weights.<id>.", warnings = w)
  }

  df <- safe_read_table(input_path, w)

  # whose codes these are, said once for every unit, or refused (D-190)
  if (!"unit_authority" %in% names(df)) {
    primitive_failure("No unit authority",
      paste0("The input has no unit_authority column, so no index row could say whose ",
             "code it carries. Rerun the standings from values that name their units (D-132, D-190)."),
      warnings = w)
  }
  ua_all <- trimws(as.character(df$unit_authority))
  if (any(is.na(ua_all) | !nzchar(ua_all))) {
    primitive_failure("No unit authority",
      sprintf("%d row(s) name no unit_authority (D-132, D-190).", sum(is.na(ua_all) | !nzchar(ua_all))),
      warnings = w)
  }
  unit_authority <- sort(unique(ua_all), method = "radix")
  if (length(unit_authority) > 1) {
    primitive_failure("Units under more than one authority",
      paste0("An index ranks units against each other, and these are under ",
             paste(unit_authority, collapse = " and "),
             ": units of different levels were never measured beside each other. ",
             "Build one index per authority (SEAM-1, D-190)."),
      warnings = w)
  }

  if (level == "pillars") {
    need <- c("unit_code", "indicator", "z")
    comp_col <- "indicator"; score_col <- "z"
    groups <- lapply(names(pillars), function(pid) list(
      id = pid, name = pillars[[pid]]$name,
      comps = unlist(pillars[[pid]]$components)))
  } else {
    need <- c("unit_code", "index", "percentile")
    comp_col <- "index"; score_col <- "percentile"
    groups <- list(list(id = "overall", name = "Overall Index",
      comps = setNames(vapply(names(pillars), function(pid) as.numeric(pillars[[pid]]$chips), numeric(1)),
                       names(pillars))))
  }
  if (length(setdiff(need, names(df))) > 0) {
    primitive_failure("Unexpected input",
      sprintf("For level '%s' the input needs %s.", level, paste(need, collapse = ", ")), warnings = w)
  }

  units <- sort(unique(as.character(df$unit_code)), method = "radix")
  all_comps <- unique(unlist(lapply(groups, function(g) names(g$comps))))
  absent <- setdiff(all_comps, unique(df[[comp_col]]))
  if (length(absent) > 0) {
    primitive_failure("Components missing from the input",
      sprintf("The weighting names %s, which the input does not hold.", paste(absent, collapse = ", ")),
      warnings = w)
  }

  V <- matrix(NA_real_, nrow = length(units), ncol = length(all_comps), dimnames = list(units, all_comps))
  keep <- df[[comp_col]] %in% all_comps
  V[cbind(match(df$unit_code[keep], units), match(df[[comp_col]][keep], all_comps))] <- as.numeric(df[[score_col]][keep])
  name_of <- if ("name" %in% names(df)) tapply(as.character(df$name), df$unit_code, function(x) x[1]) else NULL
  imputed <- if (level == "pillars" && "imputed" %in% names(df)) df[df$imputed %in% TRUE, c("unit_code", "indicator")] else NULL

  pieces <- list()
  for (g in groups) {
    comps <- g$comps
    num <- rep(0, length(units)); den <- 0
    for (c in names(comps)) {
      num <- num + comps[[c]] * V[, c]
      den <- den + comps[[c]]
    }
    score <- num / den
    gap <- apply(is.na(V[, names(comps), drop = FALSE]), 1, function(r) paste(names(comps)[r], collapse = ", "))
    has <- !is.na(score)
    pct <- rep(NA_real_, length(units))
    pct[has] <- cii_percentile(score[has])
    n_imp <- if (!is.null(imputed)) {
      vapply(units, function(u) sum(imputed$unit_code == u & imputed$indicator %in% names(comps)), integer(1))
    } else rep(0L, length(units))
    pieces[[length(pieces) + 1]] <- data.frame(
      unit_authority = unit_authority,
      unit_code = units,
      name = if (!is.null(name_of)) as.character(name_of[units]) else "",
      index = g$id, index_name = g$name,
      score = score, percentile = pct,
      n_components = length(comps),
      missing_components = ifelse(gap == "", NA_character_, gap),
      n_imputed_components = n_imp,
      weighting = weights$id %||% NA_character_,
      weighting_is_publishers = isTRUE(weights$is_publishers_weighting),
      stringsAsFactors = FALSE)
    n_drop <- sum(!has)
    if (n_drop > 0) {
      w$info(sprintf("%s: %d unit(s) have a missing component and no index; a gap is never averaged over.",
                     g$name, n_drop))
    }
  }
  out <- do.call(rbind, pieces)
  # index:authority:code, so ids stay unique when tables from different
  # levels are read together, as every value's are (D-132, D-190)
  out$measurement_id <- paste(out$index, out$unit_authority, out$unit_code, sep = ":")

  if (!isTRUE(weights$is_publishers_weighting)) {
    w$warn(sprintf("Weighting '%s' is not the publisher's. CII's own allocation is unpublished, so these indices will not reproduce CII's exactly.",
                   weights$id %||% "(unnamed)"))
  }

  safe_write_table(out, output_path, w)

  md <- extract_tabular_metadata(out, id_field = "measurement_id", spatial_unit = "unit")
  md$crs <- NA
  md$analysis_type <- "descriptive"
  md$level <- level
  md$weighting <- list(id = weights$id, declared_in = weights$declared_in,
                       sha256 = weights$declaration_sha256,
                       is_publishers_weighting = isTRUE(weights$is_publishers_weighting))
  md$joins_to <- "governance_unit"
  md$interpretation_notes <- as.list(c(
    "An index is relative: a percentile says how a unit compares, never whether it is enough.",
    "A unit with a missing component has no index for that group, never a partial average.",
    sprintf("Weights: %s%s.", weights$id %||% "(unnamed)",
            if (isTRUE(weights$is_publishers_weighting)) "" else ", not the publisher's")))

  primitive_success(metadata = md, warnings = w)

}, warnings = w)
