# ============================================================
# soil/transform/build_place_outlines.R
# Display outlines for the places table, from 2024 TIGER/Line faces
# ============================================================
# One outline per place at one level of the geography graph, dissolved from
# the 2024 topological faces (D-126, D-142). Land faces only: a face counts
# as land by the Census's own convention (LAND_FLAGS below), so perennial
# water, ocean and lakes alike, leaves every outline. Moosehead and Sebago
# are holes.
#
# Levels and their keys, derived from the face codes and never matched by
# name (D-144):
#   state    STATEFP                              us_census_geoid
#   county   STATEFP + COUNTYFP                   us_census_geoid
#   cousub   STATEFP + COUNTYFP + COUSUBFP        us_census_geoid
#   sldl     state_fips + SLDLST, three digits    us_census_sldl
#   sldu     state_fips + SLDUST, three digits    us_census_sldu
#   aiannh   each face's 2020 block, through the  us_census_aiannh
#            spine's aiannh + aiannh_comptyp
# Tribal outlines are 2020 places, as places keys them: a 2020 block never
# crosses a boundary of an entity it tabulates (FACE-1), and TRIBE-5 below
# checks that on the state's own data.
#
# These are publication outlines. They are never an input to analysis: no
# primitive in either registry takes their types (tests/test_place_outlines.py).
#
# Refuses: a key the faces make that places does not hold at this level; a
# place at this level with no land face, by name (a finding, not a failure to
# work around); a tribal row without its note; two places with one shape.
# ============================================================

library(rewildr)
library(sf)

# the Census's land convention (TIGER/Line user note 7, faces ALAND): G glacier,
# I intermittent water, L land and S marsh count as land. P perennial water does
# not. soil/transform/build_block_spine.py holds the same list as LAND_FLAGS;
# tests/test_place_outlines.py holds the two equal (D-144, LWFLAG-1)
LAND_FLAGS <- c("G", "I", "L", "S")

LEVEL_AUTHORITY <- c(state = "us_census_geoid", county = "us_census_geoid",
                     cousub = "us_census_geoid", sldl = "us_census_sldl",
                     sldu = "us_census_sldu", aiannh = "us_census_aiannh")
TRIBAL_NOTE <- "census_tribal_area"      # a boundary's note, on every tribal row
TABLE_NOTE <- "census_tribal_places"     # the places table's own note (D-149)
FACE_FIELDS <- c("STATEFP20", "COUNTYFP20", "TRACTCE20", "BLOCKCE20", "STATEFP",
                 "COUNTYFP", "COUSUBFP", "SLDLST", "SLDUST", "LWFLAG", "ATOTAL")

zfill <- function(x, n) {
  x <- ifelse(is.na(x), "", as.character(x))
  short <- nchar(x) < n
  x[short] <- paste0(strrep("0", n - nchar(x[short])), x[short])
  x
}

# codes are text. rewildr's CSV reader infers types, which would turn "001"
# into 1, so a CSV is read here with every column as text (D-144)
read_codes_table <- function(path, w) {
  if (grepl("\\.csv$", path, ignore.case = TRUE)) {
    t <- tryCatch(
      utils::read.csv(path, colClasses = "character", na.strings = "",
                      check.names = FALSE),
      error = function(e) primitive_failure(
        "Failed to read CSV", sprintf("Path: %s\nError: %s", path, e$message),
        warnings = w))
  } else {
    t <- safe_read_table(path, warnings = w)
  }
  t[] <- lapply(t, function(col) if (is.list(col)) col else as.character(col))
  t
}

# a county's faces zip, or a zip of county zips (FACE-2). GDAL does not open
# the nested form, so both levels are unpacked into a temporary folder
read_faces <- function(path, w) {
  root <- tempfile("faces_")
  dir.create(root)
  utils::unzip(path, exdir = root)
  inner <- sort(list.files(root, pattern = "\\.zip$", recursive = TRUE,
                           full.names = TRUE, ignore.case = TRUE))
  for (z in inner) {
    dest <- file.path(root, sub("\\.zip$", "", basename(z), ignore.case = TRUE))
    dir.create(dest, showWarnings = FALSE)
    utils::unzip(z, exdir = dest)
  }
  shps <- sort(list.files(root, pattern = "_faces\\.shp$", recursive = TRUE,
                          full.names = TRUE, ignore.case = TRUE))
  if (length(shps) == 0) {
    primitive_failure("Faces table not found",
                      sprintf("no _faces.shp in %s", path), warnings = w)
  }
  tables <- lapply(shps, function(s) {
    f <- safe_read_sf(s, warnings = w)
    missing <- setdiff(FACE_FIELDS, names(f))
    if (length(missing) > 0) {
      primitive_failure("Unexpected faces layout",
                        sprintf("%s lacks %s", basename(s), paste(missing, collapse = ", ")),
                        warnings = w)
    }
    f[, FACE_FIELDS]
  })
  faces <- do.call(rbind, tables)
  w$info(sprintf("faces: read %d face(s) from %d table(s)", nrow(faces), length(shps)))
  faces
}

args <- parse_primitive_args()
w <- warnings_collector("build_place_outlines")

with_primitive_error_handling({

  level <- as.character(require_param(args$params, "level"))
  if (!level %in% names(LEVEL_AUTHORITY)) {
    primitive_failure("Unknown level",
                      sprintf("level '%s' is not one of: %s", level,
                              paste(names(LEVEL_AUTHORITY), collapse = ", ")),
                      warnings = w)
  }
  authority <- LEVEL_AUTHORITY[[level]]
  state_fips <- zfill(as.character(require_param(args$params, "state_fips")), 2)

  faces <- read_faces(get_input(args$inputs, "faces"), w)
  places <- read_codes_table(get_input(args$inputs, "places"), w)
  for (col in c("authority", "code", "level", "name", "context_note")) {
    if (!col %in% names(places)) {
      primitive_failure("Unexpected places layout",
                        sprintf("places lacks '%s'", col), warnings = w)
    }
  }
  faces$ATOTAL <- suppressWarnings(as.numeric(faces$ATOTAL))
  faces$ATOTAL[is.na(faces$ATOTAL)] <- 0
  faces$land <- faces$LWFLAG %in% LAND_FLAGS

  # --- keys, derived from the face codes (D-144) ---
  if (level == "aiannh") {
    faces <- faces[faces$STATEFP20 == state_fips, ]
    spine <- read_codes_table(get_input(args$inputs, "spine"), w)
    for (col in c("GEOID", "aiannh", "aiannh_comptyp")) {
      if (!col %in% names(spine)) {
        primitive_failure("Unexpected spine layout",
                          sprintf("the spine lacks '%s'", col), warnings = w)
      }
    }
    block <- paste0(faces$STATEFP20, faces$COUNTYFP20, faces$TRACTCE20, faces$BLOCKCE20)
    unknown <- !block %in% spine$GEOID
    if (any(unknown)) {
      w$warn(sprintf("%d face(s) lie in 2020 blocks the spine does not hold; they are in no tribal outline",
                     sum(unknown)))
    }
    tribal <- !is.na(spine$aiannh) & spine$aiannh != ""
    area_of <- setNames(paste0(spine$aiannh[tribal], spine$aiannh_comptyp[tribal]),
                        spine$GEOID[tribal])
    faces$code <- unname(area_of[block])
  } else {
    faces <- faces[faces$STATEFP == state_fips, ]
    faces$code <- switch(level,
      state  = faces$STATEFP,
      county = paste0(faces$STATEFP, faces$COUNTYFP),
      cousub = paste0(faces$STATEFP, faces$COUNTYFP, faces$COUSUBFP),
      sldl   = paste0(state_fips, zfill(faces$SLDLST, 3)),
      sldu   = paste0(state_fips, zfill(faces$SLDUST, 3)))
  }
  faces <- faces[!is.na(faces$code), ]

  # --- every outline has a place, and every place an outline ---
  mine <- places[places$level == level, ]
  if (nrow(mine) == 0) {
    primitive_failure("No places at this level",
                      sprintf("places holds no row at level '%s'", level), warnings = w)
  }
  off_authority <- unique(mine$authority[mine$authority != authority])
  if (length(off_authority) > 0) {
    primitive_failure("Places at this level under another authority",
                      sprintf("level '%s' is keyed by %s; places also has %s",
                              level, authority, paste(off_authority, collapse = ", ")),
                      warnings = w)
  }
  land <- faces[faces$land, ]
  outline_codes <- sort(unique(land$code))
  stray <- setdiff(outline_codes, mine$code)
  if (length(stray) > 0) {
    primitive_failure("Outline without a place",
      sprintf(paste("%d code(s) the faces make at level %s are not in places, e.g. %s.",
                    "Keys are derived from the face codes and never matched by name (D-144)."),
              length(stray), level, paste(head(stray, 5), collapse = ", ")),
      warnings = w)
  }
  bare <- setdiff(mine$code, outline_codes)
  if (length(bare) > 0) {
    water_only <- intersect(bare, faces$code)
    named <- paste(bare, mine$name[match(bare, mine$code)])
    primitive_failure("Place with no land faces",
      sprintf(paste("%d place(s) at level %s have no land face, so no outline: %s.",
                    "%d of them have only water faces. This is a finding for the",
                    "ledger, not a check to work around (D-144)."),
              length(bare), level, paste(head(named, 10), collapse = "; "),
              length(water_only)),
      warnings = w)
  }

  # --- the dissolve, planar (S2-1): TIGER faces share their edges exactly ---
  s2_was <- sf::sf_use_s2()
  suppressMessages(sf::sf_use_s2(FALSE))
  rows <- split(seq_len(nrow(land)), land$code)
  codes <- names(rows)
  geom <- sf::st_geometry(land)
  merged <- suppressMessages(lapply(rows, function(r) sf::st_union(geom[r])[[1]]))
  merged <- sf::st_sfc(unname(merged), crs = sf::st_crs(land))
  if (any(sf::st_geometry_type(merged) == "GEOMETRYCOLLECTION")) {
    merged <- suppressWarnings(sf::st_collection_extract(merged, "POLYGON"))
  }
  merged <- sf::st_cast(merged, "MULTIPOLYGON")
  suppressMessages(sf::sf_use_s2(s2_was))

  if (length(merged) != length(codes)) {
    primitive_failure("Dissolve produced the wrong number of geometries",
                      sprintf("%d place(s) but %d geometry(ies)", length(codes), length(merged)),
                      warnings = w)
  }
  if (length(codes) > 1) {
    wkb <- vapply(sf::st_as_binary(merged),
                  function(b) paste(as.character(b), collapse = ""), character(1))
    dup <- duplicated(wkb)
    if (any(dup)) {
      primitive_failure("Distinct places share one geometry",
                        sprintf("%d of %d outline(s) are identical to another, e.g. %s (GEO-1)",
                                sum(dup), length(codes), codes[dup][1]),
                        warnings = w)
    }
  }

  wet <- unique(faces$code[!faces$land])
  idx <- match(codes, mine$code)
  outlines <- sf::st_sf(
    authority = authority, code = codes, level = level,
    name = mine$name[idx], context_note = mine$context_note[idx],
    water_clipped = codes %in% wet,
    geometry = merged)

  if (level == "aiannh") {
    unnoted <- is.na(outlines$context_note) | outlines$context_note != TRIBAL_NOTE
    if (any(unnoted)) {
      primitive_failure("Tribal outline without its note",
                        sprintf("%d outline(s), e.g. %s (Contract 1, rule 9)",
                                sum(unnoted), outlines$code[unnoted][1]),
                        warnings = w)
    }
  }

  # --- TRIBE-5: do the block-built outlines nest in the Census's 2020 areas? ---
  if (level == "aiannh") {
    tol <- as.numeric(require_param(args$params, "tribe_tolerance_m2"))
    layers <- lapply(c("reservations", "trust_lands"), function(n) {
      l <- safe_read_sf(get_input(args$inputs, n), warnings = w)
      if (!"GEOID" %in% names(l)) {
        primitive_failure("Unexpected tribal layout",
                          sprintf("%s lacks GEOID", n), warnings = w)
      }
      l$GEOID <- as.character(l$GEOID)
      l[, "GEOID"]
    })
    census <- do.call(rbind, layers)
    census <- sf::st_make_valid(sf::st_transform(census, sf::st_crs(outlines)))
    water_by_code <- tapply(faces$ATOTAL[!faces$land], faces$code[!faces$land], sum)
    beyond <- 0L
    for (i in seq_len(nrow(outlines))) {
      code <- outlines$code[i]
      label <- paste(code, outlines$name[i])
      layer <- census[census$GEOID == code, ]
      if (nrow(layer) == 0) {
        w$warn(sprintf("TRIBE-5 %s: no feature in the Census 2020 layers to compare with", label))
        next
      }
      a <- sf::st_geometry(outlines)[i]
      b <- sf::st_union(sf::st_geometry(layer))
      res <- tryCatch(c(
        as.numeric(sum(sf::st_area(sf::st_difference(a, b)))),
        as.numeric(sum(sf::st_area(sf::st_difference(b, a))))),
        error = function(e) {
          w$warn(sprintf("TRIBE-5 %s: could not compare (%s)", label, conditionMessage(e)))
          NULL
        })
      if (is.null(res)) next
      water <- if (code %in% names(water_by_code)) as.numeric(water_by_code[[code]]) else 0
      w$info(sprintf(paste("TRIBE-5 %s: outline outside the Census 2020 layer %.0f m2;",
                           "layer outside the outline %.0f m2; perennial water left out",
                           "of its blocks %.0f m2"), label, res[1], res[2], water))
      if (res[1] > tol || res[2] > water + tol) {
        beyond <- beyond + 1L
        w$warn(sprintf("TRIBE-5 %s: the difference is more than water (tolerance %.0f m2); record it in the ledger",
                       label, tol))
      }
    }
    w$info(sprintf("TRIBE-5: %d of %d tribal outline(s) differ from the Census 2020 layers by more than water",
                   beyond, nrow(outlines)))
  }

  # --- write, measure (SIZE-1), report ---
  safe_write_sf(outlines, args$output, warnings = w)
  clipped <- sum(outlines$water_clipped)
  size_bytes <- as.integer(file.size(args$output))
  vertex_count <- nrow(sf::st_coordinates(outlines))

  meta <- extract_vector_metadata(outlines, id_field = "code")
  meta$spatial_unit <- level
  meta$level <- level
  meta$authority <- authority
  meta$size_bytes <- size_bytes
  meta$vertex_count <- vertex_count
  # every outline descends from places, so rule 9 binds both notes to every
  # outline: places' own (census_tribal_places) and its tribal inputs'
  # (census_tribal_area) (D-146, D-149, NOTE-2). as.list keeps an array under
  # auto_unbox (C-36)
  meta$context_notes <- as.list(c(TRIBAL_NOTE, TABLE_NOTE))
  if (clipped > 0) {
    meta$publication <- list(list(
      step = "clipped",
      detail = sprintf(paste("perennial water removed: faces whose LWFLAG is not one of",
                             "%s were left out before the dissolve (D-142)"),
                       paste(LAND_FLAGS, collapse = ", ")),
      count = as.integer(clipped)))
  }

  w$info(sprintf("outlines: %d place(s) at level %s from %d land face(s); %d lost water area; %d bytes, %d vertices (SIZE-1)",
                 nrow(outlines), level, nrow(land), clipped, size_bytes, vertex_count))

  primitive_success(meta, w)

}, warnings = w)
