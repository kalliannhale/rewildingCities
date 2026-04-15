# ============================================================
# soil/convert/scale_raster.R
# Apply scale/offset conversion to raster values
# ============================================================
# Converts raster values using: new = (old * scale) + offset
# Primary use case: Landsat DN to Celsius conversion, or
# Kelvin to Celsius (scale=1, offset=-273.15).
#
# Documents the transformation in the envelope so downstream
# primitives know what units the data is in.
# ============================================================

library(rewildr)
library(terra)

args <- parse_primitive_args()

input_path <- get_input(args$inputs, "raster")
output_path <- args$output
scale_factor <- as.numeric(get_param(args$params, "scale", 1))
offset <- as.numeric(get_param(args$params, "offset", 0))
from_unit <- get_param(args$params, "from_unit", "unknown")
to_unit <- get_param(args$params, "to_unit", "unknown")

w <- warnings_collector()

with_primitive_error_handling({

  r <- safe_read_rast(input_path, warnings = w)

  val_range_before <- range(values(r), na.rm = TRUE)

  # Apply transformation
  r_converted <- r * scale_factor + offset

  val_range_after <- range(values(r_converted), na.rm = TRUE)

  w$add("info", "scale_raster",
    sprintf("Converted from %s to %s: values [%.2f, %.2f] -> [%.2f, %.2f]",
      from_unit, to_unit,
      val_range_before[1], val_range_before[2],
      val_range_after[1], val_range_after[2]))

  # Sanity check
  if (to_unit == "celsius" && (val_range_after[2] > 80 || val_range_after[1] < -60)) {
    w$add("warning", "scale_raster",
      sprintf("Converted values [%.1f, %.1f] seem extreme for Celsius. Verify scale/offset.",
        val_range_after[1], val_range_after[2]))
  }

  safe_write_rast(r_converted, output_path, warnings = w)

  meta <- extract_raster_metadata(r_converted)

  primitive_success(
    metadata = c(meta, list(
      scale_factor = scale_factor,
      offset = offset,
      from_unit = from_unit,
      to_unit = to_unit,
      value_range_before = as.list(round(val_range_before, 4)),
      value_range_after = as.list(round(val_range_after, 4))
    )),
    warnings = w
  )

}, warnings = w)