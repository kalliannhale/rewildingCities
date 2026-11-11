"""
soil/transform/prepare_library_points.py  |  rewildingCities

the IMLS Public Libraries Survey's outlets for one state, as a point layer
(Sprint 06, step 3: the first carrier).

  ~ a feature is one outlet, named FSCSKEY-FSCS_SEQ: FSCSKEY names a library
    system and repeats across its outlets, so it never names a point alone
  ~ only fixed outlets are points (the declared fixed_types, central and
    branch). a mobile outlet (bookmobile, books-by-mail) serves places and
    sits in none: in Maine's FY 2024 file each bookmobile wears its home
    library's coordinates, so as a point it would count a second library in
    the town where it is garaged. mobile outlets are listed by name in the
    receipt and get no point (SERVES-1)
  ~ an outlet type in neither list is refused, never guessed
  ~ the file's encoding is declared, never sniffed. Latin-1 and Windows-1252
    agree on every byte but 0x80 to 0x9F: declared Latin-1, a file holding one
    of those is refused, since which encoding it is would be a guess; declared
    Windows-1252, a byte it does not define is refused. the FY 2024 outlet
    file holds one such byte, 0x96, twice, each a dash between words
    ("TAZEWELL COUNTY PUBLIC LIBRARY – POCAHONTAS BRANCH"), which is
    Windows-1252's en dash and in Latin-1 a control character
  ~ flags say what a reader must know: a hand-placed geocode (GEOMTYPE
    MANUAL), a structure status other than no change, with its declared
    meaning or `unknown`, and an outlet of a system the survey does not
    count as a public library (C_FSCS N)

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:  survey   the PLS release zip
Params:
  member        required: the outlet file's path inside the zip
  state         required: two-letter postal code, matched to STABR
  encoding      required: the declared encoding (windows-1252 for FY 2024)
  fixed_types   required: outlet types that are points, e.g. [CE, BR]
  mobile_types  required: outlet types listed and never placed, e.g. [BS, BM]
  status_codes  required: STATSTRU code -> meaning, cited where declared
Output: geojson points in EPSG:4326, one feature per fixed outlet. ~
"""

from __future__ import annotations

import io
import json
import zipfile

import pandas as pd

KEEP = ["FSCSKEY", "FSCS_SEQ", "LIBNAME", "CITY", "CNTY", "C_OUT_TY", "C_FSCS",
        "STATSTRU", "GEOMTYPE", "GEOSCORE", "CENBLOCK", "LATITUDE", "LONGITUD"]
AMBIGUOUS = range(0x80, 0xA0)


class LibraryPointsRefused(ValueError):
    """an outlet file that cannot be read as declared, with why."""


def read_outlets(raw: bytes, encoding: str) -> pd.DataFrame:
    if encoding.lower().replace("_", "-") in ("latin-1", "latin1", "iso-8859-1"):
        hits = sorted({b for b in raw if b in AMBIGUOUS})
        if hits:
            raise LibraryPointsRefused(
                f"the file holds byte(s) {', '.join(hex(b) for b in hits)}, where Latin-1 "
                f"and Windows-1252 disagree; which encoding it is would be a guess")
    try:
        table = pd.read_csv(io.BytesIO(raw), dtype=str, encoding=encoding)
    except UnicodeDecodeError as e:
        raise LibraryPointsRefused(f"the file is not {encoding}: {e}")
    missing = [c for c in KEEP + ["STABR"] if c not in table.columns]
    if missing:
        raise LibraryPointsRefused(f"the outlet file lacks {', '.join(missing)}")
    return table


def points_from(table: pd.DataFrame, state: str, fixed_types, mobile_types,
                status_codes: dict) -> tuple[dict, dict]:
    """the state's fixed outlets as a geojson FeatureCollection, and what the
    receipt says of them."""
    rows = table[table["STABR"] == state].copy()
    if rows.empty:
        raise LibraryPointsRefused(f"no outlet has STABR {state}")
    fixed, mobile = set(fixed_types), set(mobile_types)
    unknown = sorted(set(rows["C_OUT_TY"]) - fixed - mobile)
    if unknown:
        raise LibraryPointsRefused(f"outlet type(s) {', '.join(unknown)} are in neither "
                                   f"fixed_types nor mobile_types")
    rows["feature_id"] = rows["FSCSKEY"] + "-" + rows["FSCS_SEQ"]
    twice = rows[rows["feature_id"].duplicated(keep=False)]
    if len(twice):
        raise LibraryPointsRefused(f"feature id used twice: {twice['feature_id'].iloc[0]}")

    mobile_rows = rows[rows["C_OUT_TY"].isin(mobile)]
    listed = [{"feature_id": r.feature_id, "type": r.C_OUT_TY, "name": r.LIBNAME,
               "city": r.CITY} for r in mobile_rows.itertuples()]
    features, unknown_status = [], set()
    for r in rows[rows["C_OUT_TY"].isin(fixed)].itertuples():
        flags = []
        if r.GEOMTYPE == "MANUAL":
            flags.append("manual_geocode")
        if r.STATSTRU not in (None, "00"):
            meaning = status_codes.get(r.STATSTRU)
            if meaning is None:
                unknown_status.add(r.STATSTRU)
            flags.append(f"status_{r.STATSTRU}:{meaning or 'unknown'}")
        if r.C_FSCS == "N":
            flags.append("not_fscs_public_library")
        lat, lon = pd.to_numeric(r.LATITUDE, errors="coerce"), pd.to_numeric(r.LONGITUD, errors="coerce")
        geometry = (None if pd.isna(lat) or pd.isna(lon)
                    else {"type": "Point", "coordinates": [float(lon), float(lat)]})
        features.append({"type": "Feature", "geometry": geometry, "properties": {
            "feature_id": r.feature_id, "fscskey": r.FSCSKEY, "fscs_seq": r.FSCS_SEQ,
            "name": r.LIBNAME, "city": r.CITY, "county_name": r.CNTY,
            "outlet_type": r.C_OUT_TY, "geomtype": r.GEOMTYPE, "geoscore": r.GEOSCORE,
            "cenblock": r.CENBLOCK, "flags": ";".join(flags) or None}})
    coords = [f["geometry"]["coordinates"] for f in features if f["geometry"]]
    bbox = ([min(c[0] for c in coords), min(c[1] for c in coords),
             max(c[0] for c in coords), max(c[1] for c in coords)] if coords else None)
    meta = {"data_category": "vector", "crs": "EPSG:4326", "feature_count": len(features),
            "geometry_type": "Point", "bbox": bbox, "total_area_m2": 0.0,
            "id_field": "feature_id", "spatial_unit": "library_outlet",
            "attribute_fields": list(features[0]["properties"]) if features else [],
            "mobile_outlets": listed,
            "status_codes_unknown": sorted(unknown_status)}
    return {"type": "FeatureCollection", "features": features}, meta


def main():
    try:
        from canopy.pr_io import (parse_primitive_args, get_input, require_param,
                                  WarningsCollector, primitive_success, primitive_failure,
                                  primitive_error_handling)
    except ImportError:
        from pr_io import (parse_primitive_args, get_input, require_param,
                           WarningsCollector, primitive_success, primitive_failure,
                           primitive_error_handling)
    args = parse_primitive_args()
    w = WarningsCollector("prepare_library_points")
    with primitive_error_handling(w):
        p = args["params"]
        member = require_param(p, "member")
        with zipfile.ZipFile(get_input(args["inputs"], "survey")) as z:
            if member not in z.namelist():
                primitive_failure("Outlet file not found", f"{member} is not in the zip; "
                                  f"it holds {z.namelist()}")
            raw = z.read(member)
        try:
            collection, meta = points_from(read_outlets(raw, require_param(p, "encoding")),
                                           require_param(p, "state"),
                                           require_param(p, "fixed_types"),
                                           require_param(p, "mobile_types"),
                                           require_param(p, "status_codes"))
        except LibraryPointsRefused as e:
            primitive_failure("Library points refused", str(e))
        w.info(f"{meta['feature_count']} fixed outlet(s) as points; "
               f"{len(meta['mobile_outlets'])} mobile outlet(s) listed, not placed")
        if meta["status_codes_unknown"]:
            w.warn(f"structure status code(s) with no declared meaning: "
                   f"{', '.join(meta['status_codes_unknown'])}; flagged `unknown`")
        with open(args["output"], "w") as fh:
            json.dump(collection, fh)
        primitive_success(meta, w)


if __name__ == "__main__":
    main()
