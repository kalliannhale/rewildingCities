# ============================================================
# roots/statistics/correlation_analysis.R
# Pearson + partial correlation with bootstrap CIs
# ============================================================
# Computes Pearson correlations between a response variable and
# a set of predictors, with optional bootstrap confidence
# intervals (no normality assumption). Then computes partial
# correlations controlling for specified variables.
#
# This addresses the v1 gap: standard Pearson without bootstrap,
# and aligns with Xiao et al.'s methodology.
#
# Inputs:
#   data: CSV with response and predictor columns
# Params:
#   response: name of the response column (e.g., "PCI")
#   predictors: character vector of predictor column names
#   control_vars: variables to control for in partial correlation
#   n_boot: number of bootstrap resamples (0 = skip bootstrap)
#   conf_level: confidence level for bootstrap CIs
# Output:
#   CSV with correlation results (r, p, CI_low, CI_high, partial_r, partial_p)
# ============================================================

library(rewildr)

args <- parse_primitive_args()

input_path   <- get_input(args$inputs, "data")
output_path  <- args$output
response     <- get_param(args$params, "response", "PCI")
predictors   <- get_param(args$params, "predictors")
control_vars <- get_param(args$params, "control_vars", NULL)
n_boot       <- as.integer(get_param(args$params, "n_boot", 1000))
conf_level   <- as.numeric(get_param(args$params, "conf_level", 0.95))

w <- warnings_collector()

with_primitive_error_handling({

  df <- read.csv(input_path, stringsAsFactors = FALSE)

  # Validate columns
  all_needed <- c(response, predictors, control_vars)
  missing <- setdiff(all_needed, names(df))
  if (length(missing) > 0) {
    primitive_failure("Missing columns",
      sprintf("Columns not found: %s", paste(missing, collapse = ", ")),
      warnings = w)
  }

  # Complete cases for analysis columns
  analysis_cols <- c(response, predictors, control_vars)
  cc <- complete.cases(df[, analysis_cols])
  n_dropped <- sum(!cc)
  df_clean <- df[cc, ]

  if (n_dropped > 0) {
    w$add("warning", "correlation_analysis",
      sprintf("Dropped %d rows with missing values (%d remaining).",
        n_dropped, nrow(df_clean)))
  }

  if (nrow(df_clean) < 10) {
    primitive_failure("Insufficient data",
      sprintf("Only %d complete cases. Need at least 10.", nrow(df_clean)),
      warnings = w)
  }

  y <- df_clean[[response]]

  # --- Pearson correlations ---
  pearson_results <- lapply(predictors, function(pred) {
    x <- df_clean[[pred]]
    ct <- cor.test(x, y, method = "pearson")
    list(variable = pred, r = ct$estimate, p = ct$p.value)
  })

  # --- Bootstrap CIs ---
  boot_results <- if (n_boot > 0) {
    w$add("info", "correlation_analysis",
      sprintf("Computing %d bootstrap resamples for confidence intervals.", n_boot))

    lapply(predictors, function(pred) {
      x <- df_clean[[pred]]
      boot_r <- replicate(n_boot, {
        idx <- sample(nrow(df_clean), replace = TRUE)
        cor(x[idx], y[idx], use = "complete.obs")
      })
      alpha <- (1 - conf_level) / 2
      ci <- quantile(boot_r, probs = c(alpha, 1 - alpha), na.rm = TRUE)
      list(ci_low = ci[1], ci_high = ci[2])
    })
  } else {
    lapply(predictors, function(pred) list(ci_low = NA, ci_high = NA))
  }

  # --- Partial correlations ---
  partial_results <- if (!is.null(control_vars) && length(control_vars) > 0) {
    w$add("info", "correlation_analysis",
      sprintf("Computing partial correlations controlling for: %s",
        paste(control_vars, collapse = ", ")))

    available_controls <- intersect(control_vars, names(df_clean))
    if (length(available_controls) < length(control_vars)) {
      w$add("warning", "correlation_analysis",
        sprintf("Some control variables unavailable. Using: %s",
          paste(available_controls, collapse = ", ")))
    }

    lapply(predictors, function(pred) {
      tryCatch({
        # Residualize both response and predictor on controls
        control_formula <- as.formula(
          paste("~", paste(available_controls, collapse = " + ")))
        control_matrix <- model.matrix(control_formula, data = df_clean)[, -1, drop = FALSE]

        y_resid <- residuals(lm(y ~ control_matrix))
        x_resid <- residuals(lm(df_clean[[pred]] ~ control_matrix))

        ct <- cor.test(x_resid, y_resid)
        list(partial_r = ct$estimate, partial_p = ct$p.value)
      }, error = function(e) {
        w$add("warning", "correlation_analysis",
          sprintf("Partial correlation failed for %s: %s", pred, e$message))
        list(partial_r = NA, partial_p = NA)
      })
    })
  } else {
    lapply(predictors, function(pred) list(partial_r = NA, partial_p = NA))
  }

  # --- Assemble results ---
  result_df <- data.frame(
    variable  = sapply(pearson_results, `[[`, "variable"),
    r         = round(sapply(pearson_results, `[[`, "r"), 4),
    p_value   = sapply(pearson_results, `[[`, "p"),
    ci_low    = round(sapply(boot_results, `[[`, "ci_low"), 4),
    ci_high   = round(sapply(boot_results, `[[`, "ci_high"), 4),
    partial_r = round(sapply(partial_results, `[[`, "partial_r"), 4),
    partial_p = sapply(partial_results, `[[`, "partial_p"),
    stringsAsFactors = FALSE
  )

  # Sort by absolute Pearson r descending
  result_df <- result_df[order(-abs(result_df$r)), ]

  # Significance markers
  result_df$significance <- ifelse(result_df$p_value < 0.001, "***",
    ifelse(result_df$p_value < 0.01, "**",
      ifelse(result_df$p_value < 0.05, "*", "")))

  write.csv(result_df, output_path, row.names = FALSE)

  # Top correlates for metadata
  top3 <- head(result_df$variable, 3)

  primitive_success(
    metadata = list(
      semantic_type = "correlation_results",
      data_category = "tabular",
      n_observations = nrow(df_clean),
      n_predictors = length(predictors),
      n_bootstrap = n_boot,
      conf_level = conf_level,
      control_vars = control_vars,
      top_correlates = top3,
      response = response
    ),
    warnings = w
  )

}, warnings = w)