# ============================================================
# soil/validate/validate_raster.R
# Diagnose raster data — CRS, resolution, NoData, value range
# ============================================================
# TRUE PASSTHROUGH: checks the raster, accumulates warnings,
# but does NOT write a new file. The output path is set to the
# original input path — the data passes through untouched.
# The envelope documents what was found, but no bytes are copied.
#
# This is registered with passthrough: true in soil/_registry.yml
# so the orchestrator knows not to expect a new file at output_path.
# ============================================================

library(rewildr)
library(terra)

args <- parse_primitive_args()

input_path       <- get_input(args$inputs, "raster")
output_path      <- args$output
expected_crs     <- get_param(args$params, "expected_crs", NULL)
max_nodata_pct   <- as.numeric(get_param(args$params, "max_nodata_percent", 20))
expected_range   <- get_param(args$params, "expected_value_range", NULL)
expected_units   <- get_param(args$params, "expected_units", NULL)

w <- warnings_collector("validate_raster")

with_primitive_error_handling({

  r <- safe_read_rast(input_path, warnings = w)

  # --- CRS check ---
  r_crs <- crs(r, describe = TRUE)
  if (is.na(crs(r)) || crs(r) == "") {
    w$critical("Raster has no CRS defined.")
  } else {
    w$info(paste0("CRS: ", r_crs$authority, ":", r_crs$code,
                  " (", r_crs$name, ")"))
    if (!is.null(expected_crs)) {
      expected_clean <- sub("^EPSG:", "", expected_crs)
      if (r_crs$code != expected_clean) {
        w$warn(paste0("CRS is ", r_crs$authority, ":", r_crs$code,
                      " but expected ", expected_crs, ". Reprojection needed."))
      }
    }
  }

  # --- Resolution ---
  res_xy <- res(r)
  w$info(sprintf("Resolution: %.2f x %.2f %s",
    res_xy[1], res_xy[2],
    if (!is.na(crs(r))) "map units" else "unknown units"))

  # --- NoData ---
  n_total <- ncell(r)
  n_na <- sum(is.na(values(r)))
  pct_na <- round(n_na / n_total * 100, 1)

  if (pct_na > max_nodata_pct) {
    w$critical(sprintf(
      "NoData is %.1f%% (threshold: %.0f%%). Results may be unreliable.",
      pct_na, max_nodata_pct))
  } else if (pct_na > 0) {
    w$info(sprintf("NoData: %.1f%% of cells.", pct_na))
  }

  # --- Value range ---
  val_range <- range(values(r), na.rm = TRUE)
  if (!is.null(expected_range)) {
    exp_min <- expected_range[[1]]
    exp_max <- expected_range[[2]]
    if (val_range[1] < exp_min || val_range[2] > exp_max) {
      w$warn(sprintf(
        "Value range [%.2f, %.2f] outside expected [%.2f, %.2f]. Check units.",
        val_range[1], val_range[2], exp_min, exp_max))
    }
  }

  # --- Band count ---
  n_bands <- nlyr(r)
  if (n_bands > 1) {
    w$info(sprintf("Multi-band raster with %d bands. Primitives may use band 1 by default.", n_bands))
  }

  # --- PASSTHROUGH: no file written, report input path as output ---
  meta <- extract_raster_metadata(r)

  primitive_success(
    metadata = c(meta, list(
      nodata_percent = pct_na,
      value_range = as.list(val_range),
      expected_units = expected_units,
      passthrough = TRUE,
      original_path = input_path
    )),
    warnings = w
  )

}, warnings = w)