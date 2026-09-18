#' Extract Vector Metadata
#'
#' Extracts metadata from an sf object for the envelope.
#'
#' @param sf_obj An sf object
#' @param id_field Optional name of the ID field
#' @return A list of metadata fields
#' @export
#' seeds/packages/rewildr/R/metadata.R
extract_vector_metadata <- function(sf_obj, id_field = NULL) {
 
 if (!inherits(sf_obj, "sf")) {
   stop("Input must be an sf object")
 }
 
 bbox <- as.vector(sf::st_bbox(sf_obj))
 names(bbox) <- NULL
 
 # Sprint 9: sf::st_geometry_type() returns SQL/MM constants in caps
 # ("MULTIPOLYGON"); the envelope schema follows GeoJSON (RFC 7946), which
 # spells them CamelCase ("MultiPolygon"). Both conventions are right in
 # their own world and nothing translated between them, so every vector
 # envelope failed this enum. Same shape as the terra dtype mismatch: a
 # hand-written enum meeting a library's own vocabulary needs an explicit
 # crosswalk, never a silent pass-through.
 .geom_type_map <- c(
   POINT = "Point",
   MULTIPOINT = "MultiPoint",
   LINESTRING = "LineString",
   MULTILINESTRING = "MultiLineString",
   POLYGON = "Polygon",
   MULTIPOLYGON = "MultiPolygon",
   GEOMETRYCOLLECTION = "GeometryCollection"
 )
 geom_types_native <- unique(as.character(sf::st_geometry_type(sf_obj)))
 geom_types <- unname(.geom_type_map[geom_types_native])
 unmapped <- geom_types_native[is.na(geom_types)]
 geom_types <- geom_types[!is.na(geom_types)]
 
 # Get attribute fields (excluding geometry)
 attr_fields <- setdiff(names(sf_obj), attr(sf_obj, "sf_column"))
 
 # Calculate total area for polygons
 # total_area_m2 is an OPTIONAL enrichment, so its computation must never
 # take the primitive down with it. st_area() needs either s2 (for
 # geographic coordinates) or lwgeom as a fallback, and on an env where
 # neither is available it errors — killing a whole run over a field the
 # schema does not even require. An unknown rests empty; the reason is
 # reported. C-30.
 total_area <- NULL
 area_unavailable <- NULL
 if (any(grepl("polygon", tolower(geom_types)))) {
   total_area <- tryCatch(
     as.numeric(sum(sf::st_area(sf_obj))),
     error = function(e) { area_unavailable <<- conditionMessage(e); NULL }
   )
 }
 
 crs_obj <- sf::st_crs(sf_obj)
 crs_string <- if (!is.na(crs_obj)) {
   epsg <- crs_obj$epsg
   if (!is.null(epsg) && !is.na(epsg)) paste0("EPSG:", epsg) else crs_obj$input
 } else {
   NA_character_
 }

 # a length-1 character vector serializes as a SCALAR, not a one-element
 # array, and the schema types this as an array. as.list() forces the array
 # form for any length including one ~ the same failure that turned a single
 # id_field into its sorted characters downstream (C-36), caught here at the
 # point of emission so no primitive has to remember.
 metadata <- list(
   feature_count = nrow(sf_obj),
   bbox = bbox,
   crs = crs_string,
   attribute_fields = as.list(attr_fields),
   geometry_type_native = if (length(geom_types_native) == 1)
                            geom_types_native[1] else geom_types_native
 )

 # assigned conditionally, because list(x = NULL) yields {} in JSON rather
 # than omitting the key. an unmapped geometry type is reported as native
 # only, so the file's own word survives and the schema is not fed a lie.
 # a real layer can hold both Polygon and MultiPolygon; the schema accepts
 # a string or an array, so the envelope reports what the layer IS rather
 # than rounding a mixed layer to its general case. C-23.
 if (length(geom_types) > 0) {
   metadata$geometry_type <- if (length(geom_types) == 1) geom_types[1] else geom_types
 }
 if (length(unmapped) > 0) {
   metadata$geometry_type_unmapped <- unmapped
 }
 
 if (!is.null(total_area)) {
   metadata$total_area_m2 <- total_area
 } else if (!is.null(area_unavailable)) {
   metadata$total_area_unavailable <- area_unavailable
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
 
 # Sprint 9: terra::minmax() reads the file's CACHED statistics and returns
 # the empty-reduction sentinel Inf/-Inf when a GeoTIFF carries none. Those
 # serialize as the STRINGS "Inf"/"-Inf", which the envelope schema rightly
 # refuses (it wants numbers). So: trust the cache when it is real, compute
 # from the cells when it is not, and report null rather than a fiction when
 # the raster genuinely holds no values.
 val_range <- terra::minmax(rast_obj)
 range_source <- "cached_statistics"
 if (!is.finite(val_range[1, 1]) || !is.finite(val_range[2, 1])) {
   computed <- range(terra::values(rast_obj), na.rm = TRUE)
   if (is.finite(computed[1]) && is.finite(computed[2])) {
     val_range[1, 1] <- computed[1]
     val_range[2, 1] <- computed[2]
     range_source <- "computed_from_cells"
   } else {
     range_source <- "unavailable"
   }
 }

 # Sprint 9: terra::datatype() speaks GDAL ("INT2U", "FLT4S"); the envelope
 # schema's dtype enum speaks numpy ("uint16", "float32"). Nothing translated
 # between them, so every raster envelope failed this check silently until a
 # step began asserting a canonical type. The native code is kept beside the
 # mapped one, because throwing away what the file actually said would be a
 # silent choice.
 .terra_dtype_map <- c(
   INT1U = "uint8",  INT1S = "int8",
   INT2U = "uint16", INT2S = "int16",
   INT4U = "uint32", INT4S = "int32",
   INT8U = "uint32", INT8S = "int32",
   FLT4S = "float32", FLT8S = "float64"
 )
 dtype_native <- terra::datatype(rast_obj)[1]
 dtype_mapped <- unname(.terra_dtype_map[dtype_native])
 
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
   value_range_source = range_source,
   dtype_native = dtype_native,
   crs = ifelse(is.na(terra::crs(rast_obj)) || terra::crs(rast_obj) == "",
                NA_character_,
                paste0(terra::crs(rast_obj, describe=TRUE)$authority, ":",
                       terra::crs(rast_obj, describe=TRUE)$code))
 )
 
 # Sprint 9 correction: in R, list(x = NULL) creates an element that IS
 # NULL, and jsonlite renders that as {} — an empty object, not an absent
 # key. A schema expecting a string rightly refuses it. The only way to
 # genuinely omit a key is to not add it, so both of these are assigned
 # conditionally AFTER the list is built (the pattern `units` already used).
 if (range_source != "unavailable") {
   metadata$value_range <- list(min = val_range[1, 1], max = val_range[2, 1])
 }

 if (!is.na(dtype_mapped)) {
   metadata$dtype <- dtype_mapped
 }

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
   # as.list() so a single-column table emits an array, not a scalar
   variables = as.list(vars)
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
