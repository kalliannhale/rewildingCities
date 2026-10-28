# ============================================================
# soil/transform/assign_geoid.R
# a Census GEOID on a boundary layer, derived from its own code
# ============================================================
# A table of indicator values names its units by Census GEOID. A
# boundary layer from a state GIS office usually does not carry one:
# Maine's dissolved counties carry COUNTY and CNTYCODE ('01'). The
# GEOID is derivable from what the layer does carry, the state FIPS
# followed by the county FIPS zero-padded to three digits, and the
# manifest records that this was verified across all sixteen Maine
# counties. So the join becomes a derivation this step performs and
# records, never a match on county names.
#
# What it refuses, because each would produce a join that looks right
# and is not:
#   ~ a county code that is empty or not all digits
#   ~ a code longer than the declared width, which padding would hide
#   ~ two features receiving the same GEOID
#   ~ an output field that already exists, which this would overwrite
#
# Inputs:
#   boundaries: a vector layer with a county code field
# Params:
#   state_fips:   two-digit state FIPS, e.g. "23"
#   county_field: the field holding the county code, e.g. "CNTYCODE"
#   county_width: digits in a county FIPS (default 3)
#   output_field: the field to write (default "GEOID")
# Output:
#   the same features, with the GEOID field added
# ============================================================

library(rewildr)

args <- parse_primitive_args()

input_path   <- get_input(args$inputs, "boundaries")
output_path  <- args$output
state_fips   <- as.character(require_param(args$params, "state_fips"))
county_field <- as.character(require_param(args$params, "county_field"))
county_width <- as.integer(get_param(args$params, "county_width", 3))
output_field <- as.character(get_param(args$params, "output_field", "GEOID"))

w <- warnings_collector("assign_geoid")

with_primitive_error_handling({

  if (!grepl("^[0-9]{2}$", state_fips)) {
    primitive_failure(
      "Malformed state FIPS",
      sprintf("state_fips '%s' must be exactly two digits, e.g. \"23\" for Maine.", state_fips),
      warnings = w)
  }

  sf_obj <- safe_read_sf(input_path, w)

  if (!county_field %in% names(sf_obj)) {
    primitive_failure(
      "County field not found",
      sprintf("No field '%s'. Fields: %s",
              county_field,
              paste(setdiff(names(sf_obj), attr(sf_obj, "sf_column")), collapse = ", ")),
      warnings = w)
  }

  if (output_field %in% names(sf_obj)) {
    primitive_failure(
      "Output field exists",
      sprintf("The layer already has '%s'. This step adds a GEOID and will not overwrite one.",
              output_field),
      warnings = w)
  }

  code <- trimws(as.character(sf_obj[[county_field]]))
  bad <- is.na(code) | !grepl("^[0-9]+$", code)
  if (any(bad)) {
    primitive_failure(
      "Unusable county codes",
      sprintf("%d feature(s) have an empty or non-numeric %s: %s",
              sum(bad), county_field,
              paste(head(unique(code[bad]), 5), collapse = ", ")),
      warnings = w)
  }

  too_long <- nchar(code) > county_width
  if (any(too_long)) {
    primitive_failure(
      "County codes wider than declared",
      paste0(sprintf("%d code(s) in %s are longer than %d digits (e.g. %s). ",
                     sum(too_long), county_field, county_width, code[too_long][1]),
             "Padding cannot shorten a code; check county_width or the field."),
      warnings = w)
  }

  geoid <- paste0(state_fips, formatC(as.integer(code), width = county_width, flag = "0"))

  dup <- unique(geoid[duplicated(geoid)])
  if (length(dup) > 0) {
    primitive_failure(
      "GEOID not unique",
      paste0(sprintf("%d GEOID(s) would be shared by more than one feature: %s. ",
                     length(dup), paste(head(dup, 5), collapse = ", ")),
             "A join on a duplicated key multiplies rows. Dissolve to one feature per county first."),
      warnings = w)
  }

  sf_obj[[output_field]] <- geoid

  w$info(paste0(
    sprintf("%s derived for %d feature(s) as '%s' + %s zero-padded to %d digits ",
            output_field, nrow(sf_obj), state_fips, county_field, county_width),
    sprintf("(e.g. %s '%s' -> %s).", county_field, code[1], geoid[1])))

  safe_write_sf(sf_obj, output_path, w)

  md <- extract_vector_metadata(sf_obj, id_field = output_field)
  md$geoid_derivation <- list(
    state_fips = state_fips, county_field = county_field,
    county_width = county_width, output_field = output_field)

  primitive_success(metadata = md, warnings = w)

}, warnings = w)
