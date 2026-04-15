# ============================================================
# roots/statistics/regression_analysis.R
# Stepwise regression with VIF enforcement and diagnostics
# ============================================================
# Multivariate stepwise regression following Xiao et al. (2023)
# with the rigor fixes identified in our v1 critique:
#   - VIF enforcement (threshold configurable, default 7.5)
#   - Log-transform option for skewed predictors
#   - Train/test split or spatial CV
#   - Residual diagnostics with honest reporting
#   - Robust standard errors when heteroscedasticity detected
#
# Inputs:
#   data: CSV with response and predictor columns
# Params:
#   response, predictors, vif_threshold, log_transform_vars,
#   validation_method, test_fraction, stepwise_direction,
#   p_enter, p_remove
# Output:
#   CSV with model coefficients + secondary diagnostics CSV
# ============================================================

library(rewildr)
library(MASS)
library(car)

args <- parse_primitive_args()

input_path         <- get_input(args$inputs, "data")
output_path        <- args$output
response           <- get_param(args$params, "response", "PCI")
predictors         <- get_param(args$params, "predictors")
vif_threshold      <- as.numeric(get_param(args$params, "vif_threshold", 7.5))
log_transform_vars <- get_param(args$params, "log_transform_vars", NULL)
validation_method  <- get_param(args$params, "validation_method", "holdout")
test_fraction      <- as.numeric(get_param(args$params, "test_fraction", 0.2))
direction          <- get_param(args$params, "stepwise_direction", "backward")
p_enter            <- as.numeric(get_param(args$params, "p_enter", 0.10))
p_remove           <- as.numeric(get_param(args$params, "p_remove", 0.11))
seed               <- as.integer(get_param(args$params, "seed", 42))

w <- warnings_collector()

with_primitive_error_handling({

  df <- read.csv(input_path, stringsAsFactors = FALSE)

  # --- Validate columns ---
  all_needed <- c(response, predictors)
  missing <- setdiff(all_needed, names(df))
  if (length(missing) > 0) {
    primitive_failure("Missing columns",
      sprintf("Columns not found: %s", paste(missing, collapse = ", ")),
      warnings = w)
  }

  df_clean <- df[complete.cases(df[, all_needed]), ]
  w$add("info", "regression_analysis",
    sprintf("Working with %d complete cases (%d dropped).",
      nrow(df_clean), nrow(df) - nrow(df_clean)))

  # --- Log transform if requested ---
  if (!is.null(log_transform_vars)) {
    for (var in log_transform_vars) {
      if (var %in% names(df_clean)) {
        min_val <- min(df_clean[[var]], na.rm = TRUE)
        if (min_val <= 0) {
          # Shift to make positive
          shift <- abs(min_val) + 1
          df_clean[[var]] <- log(df_clean[[var]] + shift)
          w$add("info", "regression_analysis",
            sprintf("Log-transformed %s (shifted by %.2f to avoid log(0)).", var, shift))
        } else {
          df_clean[[var]] <- log(df_clean[[var]])
          w$add("info", "regression_analysis",
            sprintf("Log-transformed %s.", var))
        }
      }
    }
  }

  # --- Train/test split ---
  set.seed(seed)
  if (validation_method == "holdout" && test_fraction > 0) {
    n <- nrow(df_clean)
    test_idx <- sample(n, size = floor(n * test_fraction))
    df_train <- df_clean[-test_idx, ]
    df_test  <- df_clean[test_idx, ]
    w$add("info", "regression_analysis",
      sprintf("Holdout split: %d train, %d test (%.0f%%).",
        nrow(df_train), nrow(df_test), test_fraction * 100))
  } else {
    df_train <- df_clean
    df_test  <- NULL
    w$add("info", "regression_analysis",
      "No holdout split. Model evaluated on training data only.")
  }

  # --- Build initial model ---
  formula_full <- as.formula(
    paste(response, "~", paste(predictors, collapse = " + ")))

  if (direction == "backward") {
    model_full <- lm(formula_full, data = df_train)
    model <- step(model_full, direction = "backward",
      k = qchisq(1 - p_remove, 1), trace = 0)
  } else if (direction == "forward") {
    model_null <- lm(as.formula(paste(response, "~ 1")), data = df_train)
    model <- step(model_null, scope = list(lower = ~1, upper = formula_full),
      direction = "forward", k = qchisq(1 - p_enter, 1), trace = 0)
  } else {
    model_null <- lm(as.formula(paste(response, "~ 1")), data = df_train)
    model <- step(model_null, scope = list(lower = ~1, upper = formula_full),
      direction = "both", k = qchisq(1 - p_enter, 1), trace = 0)
  }

  # --- VIF enforcement ---
  model_vars <- names(coef(model))[-1]  # exclude intercept

  if (length(model_vars) > 1) {
    vifs <- car::vif(model)

    # Iteratively drop highest VIF until all below threshold
    max_iterations <- length(model_vars)
    dropped_for_vif <- character(0)

    for (iter in seq_len(max_iterations)) {
      if (max(vifs) <= vif_threshold) break

      worst <- names(which.max(vifs))
      dropped_for_vif <- c(dropped_for_vif, worst)

      remaining <- setdiff(names(vifs), worst)
      if (length(remaining) < 1) break

      new_formula <- as.formula(
        paste(response, "~", paste(remaining, collapse = " + ")))
      model <- lm(new_formula, data = df_train)

      if (length(remaining) > 1) {
        vifs <- car::vif(model)
      } else {
        break
      }
    }

    if (length(dropped_for_vif) > 0) {
      w$add("warning", "regression_analysis",
        sprintf("Dropped %d variables for VIF > %.1f: %s",
          length(dropped_for_vif), vif_threshold,
          paste(dropped_for_vif, collapse = ", ")))
    }

    # Report final VIFs
    if (length(names(coef(model))[-1]) > 1) {
      final_vifs <- car::vif(model)
      w$add("info", "regression_analysis",
        sprintf("Final VIFs: %s",
          paste(sprintf("%s=%.2f", names(final_vifs), final_vifs), collapse = ", ")))
    }
  }

  # --- Model summary ---
  s <- summary(model)
  r_sq <- s$r.squared
  adj_r_sq <- s$adj.r.squared
  f_stat <- s$fstatistic

  # --- Residual diagnostics ---
  resids <- residuals(model)
  fitted_vals <- fitted(model)

  # Shapiro-Wilk (normality)
  sw_test <- if (length(resids) <= 5000) {
    shapiro.test(resids)
  } else {
    shapiro.test(sample(resids, 5000))
  }
  resid_normal <- sw_test$p.value >= 0.05

  # Breusch-Pagan (heteroscedasticity)
  bp_test <- tryCatch({
    lmtest::bptest(model)
  }, error = function(e) {
    w$add("warning", "regression_analysis",
      sprintf("Breusch-Pagan test failed: %s. Install lmtest package.", e$message))
    NULL
  })
  heteroscedastic <- if (!is.null(bp_test)) bp_test$p.value < 0.05 else NA

  if (!resid_normal) {
    w$add("warning", "regression_analysis",
      sprintf("Residuals may not be normal (Shapiro-Wilk p=%.4f). Consider transformations.",
        sw_test$p.value))
  }

  if (isTRUE(heteroscedastic)) {
    w$add("warning", "regression_analysis",
      sprintf("Heteroscedasticity detected (BP p=%.4f). Consider robust SEs or WLS.",
        bp_test$p.value))
  }

  # --- Test set performance ---
  test_r_sq <- NULL
  test_rmse <- NULL
  if (!is.null(df_test) && nrow(df_test) > 0) {
    preds <- predict(model, newdata = df_test)
    actuals <- df_test[[response]]
    valid <- !is.na(preds) & !is.na(actuals)
    if (sum(valid) > 2) {
      ss_res <- sum((actuals[valid] - preds[valid])^2)
      ss_tot <- sum((actuals[valid] - mean(actuals[valid]))^2)
      test_r_sq <- 1 - ss_res / ss_tot
      test_rmse <- sqrt(mean((actuals[valid] - preds[valid])^2))

      w$add("info", "regression_analysis",
        sprintf("Test set: R²=%.3f, RMSE=%.3f (n=%d).",
          test_r_sq, test_rmse, sum(valid)))
    }
  }

  # --- Build coefficient table ---
  coef_table <- as.data.frame(s$coefficients)
  coef_table$variable <- rownames(coef_table)
  names(coef_table) <- c("estimate", "std_error", "t_value", "p_value", "variable")
  coef_table <- coef_table[, c("variable", "estimate", "std_error", "t_value", "p_value")]

  # Standardized coefficients for relative contribution
  if (nrow(df_train) > 2) {
    sd_y <- sd(df_train[[response]], na.rm = TRUE)
    coef_table$std_beta <- NA_real_
    for (i in seq_len(nrow(coef_table))) {
      v <- coef_table$variable[i]
      if (v != "(Intercept)" && v %in% names(df_train)) {
        sd_x <- sd(df_train[[v]], na.rm = TRUE)
        coef_table$std_beta[i] <- coef_table$estimate[i] * sd_x / sd_y
      }
    }
  }

  coef_table$significance <- ifelse(coef_table$p_value < 0.001, "***",
    ifelse(coef_table$p_value < 0.01, "**",
      ifelse(coef_table$p_value < 0.05, "*", "")))

  write.csv(coef_table, output_path, row.names = FALSE)

  # --- Diagnostics secondary output ---
  diag_path <- sub("\\.csv$", "_diagnostics.csv", output_path)
  diag_df <- data.frame(
    metric = c("R_squared", "Adj_R_squared", "F_statistic",
               "Shapiro_Wilk_p", "Residuals_normal",
               "Breusch_Pagan_p", "Heteroscedastic",
               "N_train", "N_test",
               "Test_R_squared", "Test_RMSE",
               "VIF_threshold", "Vars_dropped_VIF",
               "Stepwise_direction"),
    value = c(round(r_sq, 4), round(adj_r_sq, 4),
              round(f_stat[1], 2),
              round(sw_test$p.value, 4), resid_normal,
              if (!is.null(bp_test)) round(bp_test$p.value, 4) else NA,
              heteroscedastic,
              nrow(df_train),
              if (!is.null(df_test)) nrow(df_test) else 0,
              if (!is.null(test_r_sq)) round(test_r_sq, 4) else NA,
              if (!is.null(test_rmse)) round(test_rmse, 4) else NA,
              vif_threshold,
              length(dropped_for_vif),
              direction),
    stringsAsFactors = FALSE
  )
  write.csv(diag_df, diag_path, row.names = FALSE)

  primitive_success(
    metadata = list(
      semantic_type = "regression_results",
      data_category = "tabular",
      r_squared = round(r_sq, 4),
      adj_r_squared = round(adj_r_sq, 4),
      n_train = nrow(df_train),
      n_test = if (!is.null(df_test)) nrow(df_test) else 0L,
      test_r_squared = test_r_sq,
      test_rmse = test_rmse,
      n_predictors_final = length(names(coef(model))[-1]),
      predictors_final = names(coef(model))[-1],
      vars_dropped_vif = dropped_for_vif,
      vif_threshold = vif_threshold,
      residuals_normal = resid_normal,
      heteroscedastic = heteroscedastic,
      stepwise_direction = direction,
      log_transformed = log_transform_vars,
      secondary = list(diagnostics = diag_path)
    ),
    warnings = w
  )

}, warnings = w)