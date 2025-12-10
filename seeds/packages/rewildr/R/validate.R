#' Validate CRS Match
#'
#' Checks if two spatial objects have matching CRS.
#' Optionally transforms to match.
#'
#' @param obj1 First spatial object (sf or SpatRaster)
#' @param obj2 Second spatial object (sf or SpatRaster)
#' @param warnings Warnings collector to append to
#' @param transform_to Which object's CRS to transform to (1 or 2)
#' @return List with validated/transformed objects
#' @export
validate_crs_match <- function(obj1, obj2, warnings = NULL, transform_to = 2) {
 
 crs1 <- get_crs_string(obj1)
 crs2 <- get_crs_string(obj2)
 
 if (crs1 != crs2) {
   if (!is.null(warnings)) {
     warnings$info(sprintf(
       "CRS mismatch: transforming from %s to %s",
       if (transform_to == 2) crs1 else crs2,
       if (transform_to == 2) crs2 else crs1
     ))
   }
  
   if (transform_to == 2) {
     obj1 <- transform_to_crs(obj1, obj2)
   } else {
     obj2 <- transform_to_crs(obj2, obj1)
   }
 }
 
 list(obj1 = obj1, obj2 = obj2)
}

#' Get CRS String
#' @keywords internal
get_crs_string <- function(obj) {
 if (inherits(obj, "sf")) {
   as.character(sf::st_crs(obj)$wkt)
 } else if (inherits(obj, "SpatRaster")) {
   as.character(terra::crs(obj))
 } else {
   stop("Object must be sf or SpatRaster")
 }
}

#' Transform to CRS
#' @keywords internal
transform_to_crs <- function(obj, target) {
 if (inherits(obj, "sf")) {
   if (inherits(target, "sf")) {
     sf::st_transform(obj, sf::st_crs(target))
   } else {
     sf::st_transform(obj, terra::crs(target))
   }
 } else if (inherits(obj, "SpatRaster")) {
   if (inherits(target, "SpatRaster")) {
     terra::project(obj, target)
   } else {
     terra::project(obj, sf::st_crs(target)$wkt)
   }
 }
}

#' Validate Geometry
#'
#' Checks for invalid geometries and optionally repairs them.
#'
#' @param sf_obj An sf object
#' @param warnings Warnings collector
#' @param repair If TRUE, attempts to repair invalid geometries
#' @return The validated (and possibly repaired) sf object
#' @export
validate_geometry <- function(sf_obj, warnings = NULL, repair = TRUE) {
 
 invalid_mask <- !sf::st_is_valid(sf_obj)
 invalid_count <- sum(invalid_mask)
 
 if (invalid_count > 0) {
   if (repair) {
     sf_obj <- sf::st_make_valid(sf_obj)
    
     # Check if repair worked
     still_invalid <- sum(!sf::st_is_valid(sf_obj))
    
     if (still_invalid > 0) {
       if (!is.null(warnings)) {
         warnings$warn(sprintf(
           "%d geometries invalid, %d could not be repaired",
           invalid_count, still_invalid
         ))
       }
     } else {
       if (!is.null(warnings)) {
         warnings$info(sprintf(
           "%d invalid geometries were repaired",
           invalid_count
         ))
       }
     }
   } else {
     if (!is.null(warnings)) {
       warnings$warn(sprintf(
         "%d features have invalid geometry",
         invalid_count
       ))
     }
   }
 }
 
 sf_obj
}

#' Validate Spatial Overlap
#'
#' Checks if two spatial objects overlap.
#'
#' @param obj1 First spatial object
#' @param obj2 Second spatial object
#' @param warnings Warnings collector
#' @param min_overlap_pct Minimum overlap percentage to consider valid
#' @return TRUE if sufficient overlap, FALSE otherwise
#' @export
validate_spatial_overlap <- function(obj1, obj2, warnings = NULL, min_overlap_pct = 0) {
 
 bbox1 <- get_bbox(obj1)
 bbox2 <- get_bbox(obj2)
 
 # Check for any overlap
 no_overlap <-
   bbox1["xmax"] < bbox2["xmin"] ||
   bbox1["xmin"] > bbox2["xmax"] ||
   bbox1["ymax"] < bbox2["ymin"] ||
   bbox1["ymin"] > bbox2["ymax"]
 
 if (no_overlap) {
   if (!is.null(warnings)) {
     warnings$critical("Input spatial extents do not overlap")
   }
   return(FALSE)
 }
 
 # Calculate overlap percentage (relative to obj1)
 overlap_xmin <- max(bbox1["xmin"], bbox2["xmin"])
 overlap_xmax <- min(bbox1["xmax"], bbox2["xmax"])
 overlap_ymin <- max(bbox1["ymin"], bbox2["ymin"])
 overlap_ymax <- min(bbox1["ymax"], bbox2["ymax"])
 
 overlap_area <- (overlap_xmax - overlap_xmin) * (overlap_ymax - overlap_ymin)
 obj1_area <- (bbox1["xmax"] - bbox1["xmin"]) * (bbox1["ymax"] - bbox1["ymin"])
 
 overlap_pct <- (overlap_area / obj1_area) * 100
 
 if (overlap_pct < 100 && !is.null(warnings)) {
   warnings$warn(sprintf(
     "Spatial overlap is %.1f%% of first input extent",
     overlap_pct
   ))
 }
 
 overlap_pct >= min_overlap_pct
}

#' Get Bounding Box
#' @keywords internal
get_bbox <- function(obj) {
 if (inherits(obj, "sf")) {
   as.vector(sf::st_bbox(obj))
 } else if (inherits(obj, "SpatRaster")) {
   ext <- terra::ext(obj)
   c(xmin = ext$xmin, ymin = ext$ymin, xmax = ext$xmax, ymax = ext$ymax)
 }
}
