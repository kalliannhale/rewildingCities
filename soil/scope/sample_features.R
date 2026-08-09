# ============================================================
# soil/scope/sample_features.R
# Subsample vector features for faster iteration
# ============================================================
# Injected by the orchestrator when a profile enables feature
# sampling (e.g. --profile dev runs against 25 stratified parks
# instead of all 2,055). Supports five sampling methods:
#
#   random      — uniform random sample of n features
#   stratified  — n_per_stratum from each group in stratify_by
#                 (with "auto" mode: walks a candidate field list)
#   first_n     — the first n features as-ordered; deterministic.
#                 Reserved for a future API-pushdown layer where
#                 acquisition itself can limit n.
#   filtered    — subset by an sf/dplyr filter expression
#   explicit    — select features by feature_ids list
#
# Method, parameters, and resolved field names are all recorded
# in envelope metadata for full reproducibility.
# ============================================================

library(rewildr)
library(sf)
library(dplyr)

args <- parse_primitive_args()

input_path  <- get_input(args$inputs, "features")
output_path <- args$output

method        <- get_param(args$params, "method", "random")
n             <- as.integer(get_param(args$params, "n", 50))
n_per_stratum <- as.integer(get_param(args$params, "n_per_stratum", 5))
stratify_by   <- get_param(args$params, "stratify_by", "auto")
seed          <- as.integer(get_param(args$params, "seed", 42))
filter_expr   <- get_param(args$params, "filter", NULL)
feature_ids   <- get_param(args$params, "feature_ids", NULL)

w <- warnings_collector("sample_features")

# Candidate fields to walk when stratify_by = "auto"
STRATIFY_AUTO_CANDIDATES <- c("borough", "boro", "neighborhood", "district")

with_primitive_error_handling({

  features <- safe_read_sf(input_path, warnings = w)
  n_before <- nrow(features)

  # ── Hard errors: meaningless or impossible requests ──
  if (method == "random" && n == 0) {
    stop("sample_features: n=0 would produce an empty sample. ",
         "If you want to skip sampling, disable feature_sampling in the profile.")
  }
  if (method == "explicit" && (is.null(feature_ids) || length(feature_ids) == 0)) {
    stop("sample_features: method='explicit' requires non-empty feature_ids list.")
  }
  if (method == "filtered" && (is.null(filter_expr) || nchar(filter_expr) == 0)) {
    stop("sample_features: method='filtered' requires a non-empty filter expression.")
  }

  # ── Branch on method ──
  resolved_stratify_by <- NA_character_

  features_sampled <- switch(method,

    "random" = {
      set.seed(seed)
      take_n <- min(n, n_before)
      if (take_n < n) {
        w$add("warning", "sample_features",
          sprintf("Requested n=%d but only %d features available. Taking all.",
            n, n_before))
      }
      idx <- sample.int(n_before, take_n)
      features[idx, ]
    },

    "stratified" = {
      # Resolve "auto" → first matching candidate field, deterministically
      if (identical(stratify_by, "auto")) {
        available <- intersect(STRATIFY_AUTO_CANDIDATES, names(features))
        if (length(available) == 0) {
          w$add("warning", "sample_features",
            sprintf(paste0("stratify_by='auto' found no matching field ",
                           "(tried: %s). Falling back to random sampling."),
              paste(STRATIFY_AUTO_CANDIDATES, collapse = ", ")))
          set.seed(seed)
          take_n <- min(n_per_stratum * 5, n_before)  # rough fallback target
          idx <- sample.int(n_before, take_n)
          resolved_stratify_by <- NA_character_  # signal: fell back
          features[idx, ]
        } else {
          resolved_stratify_by <- available[1]
          set.seed(seed)
          features %>%
            group_by(.data[[resolved_stratify_by]]) %>%
            group_modify(~ {
              take <- min(n_per_stratum, nrow(.x))
              if (take < n_per_stratum) {
                w$add("info", "sample_features",
                  sprintf("Stratum '%s' has only %d features; taking all.",
                    as.character(.y[[1]]), nrow(.x)))
              }
              slice_sample(.x, n = take)
            }) %>%
            ungroup() %>%
            st_as_sf()
        }
      } else {
        # Explicit stratify_by field name
        if (!stratify_by %in% names(features)) {
          stop(sprintf("sample_features: stratify_by='%s' is not a column in features. ",
                       "Available: %s"),
               stratify_by, paste(names(features), collapse = ", "))
        }
        resolved_stratify_by <- stratify_by
        set.seed(seed)
        features %>%
          group_by(.data[[resolved_stratify_by]]) %>%
          group_modify(~ {
            take <- min(n_per_stratum, nrow(.x))
            if (take < n_per_stratum) {
              w$add("info", "sample_features",
                sprintf("Stratum '%s' has only %d features; taking all.",
                  as.character(.y[[1]]), nrow(.x)))
            }
            slice_sample(.x, n = take)
          }) %>%
          ungroup() %>%
          st_as_sf()
      }
    },

    "first_n" = {
      # Deterministic: no randomness, no seed.
      # Future: an acquisition layer can implement this as
      # "fetch first n features from the source" rather than
      # fetching all and discarding.
      take_n <- min(n, n_before)
      if (take_n < n) {
        w$add("warning", "sample_features",
          sprintf("Requested first_n=%d but only %d features available. Taking all.",
            n, n_before))
      }
      features[seq_len(take_n), ]
    },

    "filtered" = {
      # Evaluate the filter expression in the features' data context.
      # Wrapped in tryCatch so a bad expression is a primitive-level error,
      # not a silent empty result.
      result <- tryCatch({
        features %>% filter(eval(parse(text = filter_expr)))
      }, error = function(e) {
        stop(sprintf("sample_features: filter expression failed to parse or evaluate: %s. Expression: %s",
                     conditionMessage(e), filter_expr))
      })
      if (nrow(result) == 0) {
        w$add("warning", "sample_features",
          sprintf("Filter expression '%s' matched zero features.", filter_expr))
      }
      result
    },

    "explicit" = {
      # Match feature_ids against the first column that looks like an identifier.
      # Convention: 'id' first, then any column ending in '_id'.
      id_field <- if ("id" %in% names(features)) {
        "id"
      } else {
        id_candidates <- grep("_id$", names(features), value = TRUE)
        if (length(id_candidates) == 0) {
          stop("sample_features: method='explicit' requires an 'id' column or a column ending in '_id'.")
        }
        id_candidates[1]
      }
      matches <- features[[id_field]] %in% feature_ids
      n_matched <- sum(matches)
      if (n_matched < length(feature_ids)) {
        w$add("warning", "sample_features",
          sprintf("explicit selection: %d of %d feature_ids matched in column '%s'.",
            n_matched, length(feature_ids), id_field))
      }
      features[matches, ]
    },

    # Unknown method
    stop(sprintf("sample_features: unknown method '%s'. ",
                 "Valid: random, stratified, first_n, filtered, explicit."),
         method)
  )

  n_after <- nrow(features_sampled)

  w$add("info", "sample_features",
    sprintf("Sampled %d of %d features using method='%s'.",
      n_after, n_before, method))

  safe_write_sf(features_sampled, output_path, warnings = w)

  meta <- extract_vector_metadata(features_sampled)

  # Envelope metadata — every choice the primitive made must be visible here.
  # The `sampling_layer` field is the API-pushdown hook noted in the doc:
  # Sprint 8+ can introduce sampling_layer = "api" without changing this
  # primitive's contract.
  primitive_success(
    metadata = c(meta, list(
      features_before     = n_before,
      features_after      = n_after,
      method              = method,
      seed                = if (method %in% c("random", "stratified")) seed else NULL,
      stratify_by         = if (method == "stratified") resolved_stratify_by else NULL,
      filter_expression   = if (method == "filtered") filter_expr else NULL,
      n_feature_ids       = if (method == "explicit") length(feature_ids) else NULL,
      sampling_layer      = "r_primitive"
    )),
    warnings = w
  )

}, warnings = w)
