#' Extract Vector Metadata
#'
#' Extracts metadata from an sf object for the envelope.
#'
#' @param sf_obj An sf object
#' @param id_field Optional name of the ID field
#' @return A list of metadata fields
#' @export
extract_vector_metadata <- function(sf_obj, id_field = NULL) {
 
 if (!inherits(sf_obj, "sf")) {
   stop("Input must be an sf object")
 }
 
 bbox <- as.vector(sf::st_bbox(sf_obj))
 names(bbox) <- NULL
 
 geom_types <- unique(as.character(sf::st_geometry_type(sf_obj)))
 
 # Get attribute fields (excluding geometry)
 attr_fields <- setdiff(names(sf_obj), attr(sf_obj, "sf_column"))
 
 # Calculate total area for polygons
 total_area <- NULL
 if (any(grepl("polygon", tolower(geom_types)))) {
   total_area <- as.numeric(sum(sf::st_area(sf_obj)))
 }
 
 metadata <- list(
   feature_count = nrow(sf_obj),
   geometry_type = if (length(geom_types) == 1) geom_types else geom_types,
   bbox = bbox,
   attribute_fields = attr_fields
 )
 
 if (!is.null(total_area)) {
   metadata$total_area_m2 <- total_area
 }
 
 if (!is.null(id_field) && id_field %in% attr_fields) {
   metadata$id_field <- id_field
 }
 
 metadata
}

#' Extract Raster Metadata
#'
#' Extracts metadata from a terra SpatRaster for the envelope.
#'
#' @param rast_obj A terra SpatRaster
#' @param units Optional units string
#' @param measurement_type Optional: "absolute", "relative", "anomaly", "categorical"
#' @return A list of metadata fields
#' @export
extract_raster_metadata <- function(rast_obj, units = NULL, measurement_type = NULL) {
 
 if (!inherits(rast_obj, "SpatRaster")) {
   stop("Input must be a terra SpatRaster")
 }
 
 ext <- as.vector(terra::ext(rast_obj))
 names(ext) <- NULL
 
 # Get value range (excluding NA)
 val_range <- terra::minmax(rast_obj)
 
 # Calculate nodata percentage
 total_cells <- terra::ncell(rast_obj)
 na_cells <- terra::global(is.na(rast_obj), "sum")[1, 1]
 nodata_pct <- (na_cells / total_cells) * 100
 
 metadata <- list(
   resolution_m = terra::res(rast_obj)[1],
   dimensions = list(
     rows = terra::nrow(rast_obj),
     cols = terra::ncol(rast_obj)
   ),
   bbox = ext,
   band_count = terra::nlyr(rast_obj),
   nodata_percentage = round(nodata_pct, 2),
   value_range = list(
     min = val_range[1, 1],
     max = val_range[2, 1]
   ),
   dtype = terra::datatype(rast_obj)
 )
 
 if (!is.null(units)) {
   metadata$units <- units
 }
 
 if (!is.null(measurement_type)) {
   metadata$measurement_type <- measurement_type
 }
 
 metadata
}

#' Extract Tabular Metadata
#'
#' Extracts metadata from a data frame for the envelope.
#'
#' @param df A data frame
#' @param id_field Optional name of the ID field
#' @param spatial_unit Optional description of what each row represents
#' @return A list of metadata fields
#' @export
extract_tabular_metadata <- function(df, id_field = NULL, spatial_unit = NULL) {
 
 if (!is.data.frame(df)) {
   stop("Input must be a data frame")
 }
 
 # For sf objects, exclude geometry
 vars <- names(df)
 if (inherits(df, "sf")) {
   vars <- setdiff(vars, attr(df, "sf_column"))
 }
 
 metadata <- list(
   row_count = nrow(df),
   column_count = length(vars),
   variables = vars
 )
 
 if (!is.null(id_field) && id_field %in% vars) {
   metadata$id_field <- id_field
 }
 
 if (!is.null(spatial_unit)) {
   metadata$spatial_unit <- spatial_unit
 }
 
 # Calculate data quality metrics
 complete_cases <- sum(complete.cases(df[, vars, drop = FALSE]))
 total_cells <- nrow(df) * length(vars)
 na_cells <- sum(is.na(df[, vars, drop = FALSE]))
 
 metadata$data_quality <- list(
   complete_cases = complete_cases,
   missing_percentage = round((na_cells / total_cells) * 100, 2)
 )
 
 metadata
}
