"""
soil/transform/prepare_library_points.py  |  rewildingCities

the IMLS Public Libraries Survey's outlets for one state, as a point layer
(Sprint 06, step 3: the first carrier). what is placed, and why, is the
library_carriers method's to say (D-212); this file says only how.

  ~ a feature is one outlet, named FSCSKEY-FSCS_SEQ: FSCSKEY names a library
    system and repeats across its outlets, so it never names a point alone
  ~ an outlet's type is declared fixed or mobile. fixed outlets may be
    points; mobile outlets are listed in the receipt and never placed
  ~ a fixed outlet's structure status (STATSTRU) is declared once, with its
    meaning and one group (D-210):
        open        placed
        permanent   listed, never placed
        temporary   placed or listed, as the run's temporarily_closed choice
                    says (D-211)
    a blank status, or a code not declared, is refused, never guessed
  ~ an outlet type in neither list is refused, never guessed
  ~ the encoding is declared, never sniffed. Latin-1 and Windows-1252 agree
    on every byte but 0x80 to 0x9F: declared Latin-1, a file holding one of
    those is refused, since which encoding it is would be a guess; declared
    Windows-1252, a byte it does not define is refused
  ~ flags say what a reader must know: a hand-placed geocode (GEOMTYPE
    MANUAL), a status other than 00 with its declared meaning, and an outlet
    of a system the survey does not count as a public library (C_FSCS N)

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:  survey   the PLS release zip
Params:
  member              required: the outlet file's path inside the zip
  state               required: two-letter postal code, matched to STABR
  encoding            required: the declared encoding
  fixed_types         required: outlet types that may be points, e.g. [CE, BR]
  mobile_types        required: outlet types listed and never placed
  status_codes        required: STATSTRU code -> {meaning, group}
  temporarily_closed  required: placed or listed
Output: geojson points in EPSG:4326, one feature per placed outlet. ~
"""

from __future__ import annotations

import io
import json
import zipfile

import pandas as pd

KEEP = ["FSCSKEY", "FSCS_SEQ", "LIBNAME", "CITY", "CNTY", "C_OUT_TY", "C_FSCS",
        "STATSTRU", "GEOMTYPE", "GEOSCORE", "CENBLOCK", "LATITUDE", "LONGITUD"]
AMBIGUOUS = range(0x80, 0xA0)
GROUPS = ("open", "temporary", "permanent")
CLOSURE_CHOICES = ("placed", "listed")


class LibraryPointsRefused(ValueError):
    """an outlet file, or a declaration, that cannot be read as declared."""


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


def check_status_codes(status_codes) -> dict:
    """every declared code carries a meaning and one of the three groups."""
    if not isinstance(status_codes, dict) or not status_codes:
        raise LibraryPointsRefused("status_codes must declare at least one code")
    for code, entry in status_codes.items():
        if not isinstance(entry, dict) or not entry.get("meaning"):
            raise LibraryPointsRefused(f"status code {code} declares no meaning")
        if entry.get("group") not in GROUPS:
            raise LibraryPointsRefused(
                f"status code {code} has group {entry.get('group')!r}; "
                f"a group is one of {', '.join(GROUPS)}")
    return status_codes


def _listed(r, reason: str) -> dict:
    return {"feature_id": r.feature_id, "type": r.C_OUT_TY, "name": r.LIBNAME,
            "city": r.CITY, "status": r.STATSTRU, "reason": reason}


def points_from(table: pd.DataFrame, state: str, fixed_types, mobile_types,
                status_codes: dict, temporarily_closed: str) -> tuple[dict, dict]:
    """the state's placed outlets as a geojson FeatureCollection, and what the
    receipt says of every outlet that was not placed."""
    status_codes = check_status_codes(status_codes)
    if temporarily_closed not in CLOSURE_CHOICES:
        raise LibraryPointsRefused(
            f"temporarily_closed is {temporarily_closed!r}; it is one of "
            f"{', '.join(CLOSURE_CHOICES)}")
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

    fixed_rows = rows[rows["C_OUT_TY"].isin(fixed)]
    blank = fixed_rows[fixed_rows["STATSTRU"].isna() | (fixed_rows["STATSTRU"].str.strip() == "")]
    if len(blank):
        raise LibraryPointsRefused(
            f"fixed outlet(s) with no structure status: {', '.join(blank['feature_id'])}")
    undeclared = fixed_rows[~fixed_rows["STATSTRU"].isin(status_codes)]
    if len(undeclared):
        codes = sorted(set(undeclared["STATSTRU"]))
        raise LibraryPointsRefused(
            f"structure status code(s) {', '.join(codes)} are not declared in status_codes "
            f"(first seen on {undeclared['feature_id'].iloc[0]}); declare each with its "
            f"meaning and group")

    mobile_listed = [{"feature_id": r.feature_id, "type": r.C_OUT_TY, "name": r.LIBNAME,
                      "city": r.CITY} for r in rows[rows["C_OUT_TY"].isin(mobile)].itertuples()]
    closed_listed, features = [], []
    for r in fixed_rows.itertuples():
        group = status_codes[r.STATSTRU]["group"]
        if group == "permanent":
            closed_listed.append(_listed(r, "closed_permanently"))
            continue
        if group == "temporary" and temporarily_closed == "listed":
            closed_listed.append(_listed(r, "closed_temporarily"))
            continue
        flags = []
        if r.GEOMTYPE == "MANUAL":
            flags.append("manual_geocode")
        if r.STATSTRU != "00":
            flags.append(f"status_{r.STATSTRU}:{status_codes[r.STATSTRU]['meaning']}")
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
            "mobile_outlets": mobile_listed,
            "closed_outlets": closed_listed,
            "temporarily_closed": temporarily_closed}
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
                                           require_param(p, "status_codes"),
                                           require_param(p, "temporarily_closed"))
        except LibraryPointsRefused as e:
            primitive_failure("Library points refused", str(e))
        w.info(f"{meta['feature_count']} fixed outlet(s) placed; "
               f"{len(meta['mobile_outlets'])} mobile outlet(s) and "
               f"{len(meta['closed_outlets'])} closed outlet(s) listed, not placed "
               f"(temporarily_closed: {meta['temporarily_closed']})")
        with open(args["output"], "w") as fh:
            json.dump(collection, fh)
        primitive_success(meta, w)


if __name__ == "__main__":
    main()
