#!/usr/bin/env Rscript

# ============================================================
# soil/validate/assign_feature_id.R
#
# Identity primitive: stamps a uniform `feature_id` onto vector
# features, copied from an experiment-declared source column.
# Validates that the column exists and that its values are unique
# and non-missing, so every downstream consumer can trust
# feature_id as the join key. Identity is minted once.
#
# WRITES OUTPUT: new file with `feature_id` added.
# ============================================================

library(sf)
sf::sf_use_s2(FALSE)
library(rewildr)

# --- Parse arguments ---
args <- parse_primitive_args()

features_path <- get_input(args$inputs, "features", required = TRUE)
output_path   <- args$output
params        <- args$params

source_field <- get_param(params, "source_field")

if (is.null(source_field)) {
  primitive_failure(
    error = "Missing required parameter",
    message = "source_field is required: declare which column holds each feature's identity (e.g. gispropnum). Identity is never guessed."
  )
}

# --- Initialize warnings collector ---
w <- warnings_collector("assign_feature_id")

# --- Load vector data ---
sf_obj <- tryCatch(
  sf::st_read(features_path, quiet = TRUE),
  error = function(e) {
    primitive_failure(error = "Failed to read vector file", message = e$message)
  }
)

n_features <- nrow(sf_obj)
w$info(sprintf("Loaded %d features", n_features))

# --- Source column must exist ---
if (!(source_field %in% names(sf_obj))) {
  primitive_failure(
    error = "Source column not found",
    message = sprintf("source_field '%s' is not a column. Available: %s",
                      source_field, paste(names(sf_obj), collapse = ", "))
  )
}

source_values <- sf_obj[[source_field]]

# --- No missing identities ---
n_missing <- sum(is.na(source_values))
if (n_missing > 0) {
  primitive_failure(
    error = "Identity column has missing values",
    message = sprintf("source_field '%s' has %d NA value(s). Every feature needs an identity to be joinable.",
                      source_field, n_missing)
  )
}

# --- Identities must be unique (a duplicate silently double-counts in the join) ---
n_unique <- length(unique(source_values))
if (n_unique < n_features) {
  primitive_failure(
    error = "Identity column is not unique",
    message = sprintf("source_field '%s' has %d duplicate value(s) across %d features. A non-unique id would join one park's rings to another's interior. Use a column that is unique per feature (e.g. globalid).",
                      source_field, n_features - n_unique, n_features)
  )
}

# --- Stamp feature_id (character, so the join key is type-stable downstream) ---
sf_obj$feature_id <- as.character(source_values)
w$info(sprintf("Stamped feature_id from '%s' (%d unique values)", source_field, n_unique))

# --- Write output ---
sf::st_write(sf_obj, output_path, delete_dsn = TRUE, quiet = TRUE)
w$info(sprintf("Wrote identified features to %s", basename(output_path)))

# --- Metadata + success ---
metadata <- extract_vector_metadata(sf_obj)
metadata$identity <- list(source_field = source_field, n_features = n_features, n_unique = n_unique)

primitive_success(metadata, w)
