"""
soil/transform/prepare_school_points.py  |  rewildingCities

NCES EDGE's public school geocodes for one state, as a point layer (Sprint
06, step 3: the second carrier). what is placed, and why, is the
school_carriers method's to say (D-212); this file says only how.

  ~ a feature is one school, named by NCESSCH, the twelve-digit NCES school
    identifier (state FIPS, LEA code, school code), unique on the file
  ~ the file has no header row. its columns, in order, and NCES's codes are
    a crosswalk, seeds/crosswalks/schools/nces_edge_geocode.yml, passed whole
    as `reading` (D-206, D-226). a row whose field count differs from the
    declared columns is refused, never realigned
  ~ fields are pipe-separated, and a field holding a pipe is quoted, so the
    file is read with a quote-aware reader, never split on the pipe
  ~ a school is in the state where NCES's point stands (STFIP, assigned from
    its latitude and longitude), never where its operator sits (OPSTFIPS):
    a rule (D-230). the Bureau of Indian Education operates Maine's three
    Wabanaki community schools under code 59, and an operator filter would
    silently drop them. a school whose operator is not the state is placed
    and flagged with its operator's code and meaning
  ~ a school reported in the state (STATE) whose point NCES assigns to
    another state is listed, never placed; located_in decides the rest
  ~ M (missing) and N (not applicable) are NCES's markers, declared in the
    crosswalk, never read as values. a school with no coordinates is listed
  ~ the encoding is declared, never sniffed: the release's own fact, in its
    manifest declaration, which the run's copy must agree with (D-192)
  ~ coordinates are written as NCES gives them. NCES's geography is NAD83
    (EPSG:4269); a GeoJSON reader assumes EPSG:4326. the two differ by about
    a meter in Maine, well inside a geocode's precision, and the receipt
    names the source datum as source_crs

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:  release   the EDGE public school geocode zip
Params:
  member      required: the text table's path inside the zip, as the release
              declares it (source.geocode_member)
  encoding    required: its encoding, as the release declares it
              (source.geocode_encoding)
  state       required: two-letter postal code, matched to STATE
  state_fips  required: two-digit state FIPS, matched to STFIP and OPSTFIPS
  reading     required: the nces_edge_geocode crosswalk, via
              $crosswalks.nces_edge_geocode: columns (in order), separator,
              quote, missing, not_applicable, operating_codes
Output: geojson points, one feature per placed school. ~
"""

from __future__ import annotations

import csv
import io
import json
import zipfile

import pandas as pd

NEEDED = ["NCESSCH", "LEAID", "NAME", "OPSTFIPS", "STREET", "CITY", "STATE", "ZIP",
          "STFIP", "CNTY", "NMCNTY", "LOCALE", "LAT", "LON", "CD", "SLDL", "SLDU",
          "SCHOOLYEAR"]


class SchoolPointsRefused(ValueError):
    """a geocode file, or a declaration, that cannot be read as declared."""


def check_reading(reading) -> dict:
    """the crosswalk carries what reading the file needs, each once."""
    if not isinstance(reading, dict):
        raise SchoolPointsRefused("reading must be the nces_edge_geocode crosswalk, a mapping")
    columns = reading.get("columns")
    if not isinstance(columns, list) or not columns:
        raise SchoolPointsRefused("the crosswalk declares no columns")
    twice = sorted({c for c in columns if columns.count(c) > 1})
    if twice:
        raise SchoolPointsRefused(f"column(s) declared twice: {', '.join(twice)}")
    missing = [c for c in NEEDED if c not in columns]
    if missing:
        raise SchoolPointsRefused(f"the crosswalk's columns lack {', '.join(missing)}")
    for key in ("separator", "quote", "missing", "not_applicable"):
        if not isinstance(reading.get(key), str) or not reading[key]:
            raise SchoolPointsRefused(f"the crosswalk declares no {key}")
    codes = reading.get("operating_codes")
    if not isinstance(codes, dict):
        raise SchoolPointsRefused("the crosswalk declares no operating_codes")
    for code, entry in codes.items():
        if not isinstance(entry, dict) or not entry.get("meaning"):
            raise SchoolPointsRefused(f"operating code {code} declares no meaning")
    return reading


def read_geocodes(raw: bytes, encoding: str, reading: dict) -> pd.DataFrame:
    """the headerless table, every row split by a quote-aware reader and held
    to the declared column count."""
    reading = check_reading(reading)
    try:
        text = raw.decode(encoding)
    except (UnicodeDecodeError, LookupError) as e:
        raise SchoolPointsRefused(f"the file is not {encoding}: {e}")
    columns = reading["columns"]
    rows = list(csv.reader(io.StringIO(text), delimiter=reading["separator"],
                           quotechar=reading["quote"]))
    rows = [r for r in rows if r]
    if not rows:
        raise SchoolPointsRefused("the file holds no rows")
    wrong = [(n, len(r)) for n, r in enumerate(rows, 1) if len(r) != len(columns)]
    if wrong:
        n, k = wrong[0]
        raise SchoolPointsRefused(
            f"{len(wrong)} row(s) do not have the {len(columns)} declared columns; "
            f"line {n} has {k}")
    if rows[0][0] == columns[0]:
        raise SchoolPointsRefused("the first row repeats the column names; the release "
                                  "was declared headerless")
    return pd.DataFrame(rows, columns=columns, dtype=str)


def _value(v, reading):
    v = (v or "").strip()
    return None if v in ("", reading["missing"], reading["not_applicable"]) else v


def _listed(r, reason: str, reading: dict) -> dict:
    return {"feature_id": r.NCESSCH, "name": r.NAME, "city": _value(r.CITY, reading),
            "state": _value(r.STATE, reading), "located_state_fips": _value(r.STFIP, reading),
            "reason": reason}


def points_from(table: pd.DataFrame, state: str, state_fips: str,
                reading: dict) -> tuple[dict, dict]:
    """the state's placed schools as a geojson FeatureCollection, and what the
    receipt says of every school that was not placed."""
    reading = check_reading(reading)
    located = table["STFIP"] == state_fips
    reported = table["STATE"] == state
    rows = table[located | reported].copy()
    if rows.empty:
        raise SchoolPointsRefused(f"no school has STFIP {state_fips} or STATE {state}")
    blank = rows[rows["NCESSCH"].str.strip().isin(["", reading["missing"]])]
    if len(blank):
        raise SchoolPointsRefused(f"{len(blank)} school(s) have no NCESSCH, "
                                  f"first: {blank['NAME'].iloc[0]}")
    twice = rows[rows["NCESSCH"].duplicated(keep=False)]
    if len(twice):
        raise SchoolPointsRefused(f"feature id used twice: {twice['NCESSCH'].iloc[0]}")

    elsewhere, unplaced, features = [], [], []
    codes = reading["operating_codes"]
    for r in rows.itertuples():
        lat = pd.to_numeric(_value(r.LAT, reading), errors="coerce")
        lon = pd.to_numeric(_value(r.LON, reading), errors="coerce")
        if pd.isna(lat) or pd.isna(lon):
            unplaced.append(_listed(r, "no_coordinates", reading))
            continue
        if r.STFIP != state_fips:
            elsewhere.append(_listed(r, "located_in_another_state", reading))
            continue
        flags = []
        if r.OPSTFIPS != state_fips:
            meaning = (codes.get(r.OPSTFIPS) or {}).get("meaning", "another state")
            flags.append(f"operator_{r.OPSTFIPS}:{meaning}")
        if r.STATE != state:
            flags.append(f"reported_state_{r.STATE}")
        features.append({"type": "Feature",
                         "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
                         "properties": {
            "feature_id": r.NCESSCH, "ncessch": r.NCESSCH, "leaid": r.LEAID, "name": r.NAME,
            "street": _value(r.STREET, reading), "city": _value(r.CITY, reading),
            "zip": _value(r.ZIP, reading), "county_fips": _value(r.CNTY, reading),
            "operating_state_fips": r.OPSTFIPS, "locale": _value(r.LOCALE, reading),
            "nces_cd": _value(r.CD, reading), "nces_sldl": _value(r.SLDL, reading),
            "nces_sldu": _value(r.SLDU, reading), "school_year": r.SCHOOLYEAR,
            "flags": ";".join(flags) or None}})
    years = sorted(set(rows["SCHOOLYEAR"]))
    coords = [f["geometry"]["coordinates"] for f in features]
    bbox = ([min(c[0] for c in coords), min(c[1] for c in coords),
             max(c[0] for c in coords), max(c[1] for c in coords)] if coords else None)
    meta = {"data_category": "vector", "crs": "EPSG:4326", "source_crs": "EPSG:4269",
            "feature_count": len(features), "geometry_type": "Point", "bbox": bbox,
            "total_area_m2": 0.0, "id_field": "feature_id", "spatial_unit": "public_school",
            "attribute_fields": list(features[0]["properties"]) if features else [],
            "school_years": years,
            "operated_elsewhere": [f["properties"]["feature_id"] for f in features
                                   if f["properties"]["operating_state_fips"] != state_fips],
            "located_elsewhere": elsewhere,
            "unplaced_schools": unplaced}
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
    w = WarningsCollector("prepare_school_points")
    with primitive_error_handling(w):
        p = args["params"]
        member = require_param(p, "member")
        with zipfile.ZipFile(get_input(args["inputs"], "release")) as z:
            if member not in z.namelist():
                primitive_failure("Geocode file not found", f"{member} is not in the zip; "
                                  f"it holds {z.namelist()}")
            raw = z.read(member)
        try:
            reading = require_param(p, "reading")
            table = read_geocodes(raw, require_param(p, "encoding"), reading)
            collection, meta = points_from(table, require_param(p, "state"),
                                           require_param(p, "state_fips"), reading)
        except SchoolPointsRefused as e:
            primitive_failure("School points refused", str(e))
        if len(meta["school_years"]) != 1:
            w.warn(f"the state's rows span school years {meta['school_years']}")
        w.info(f"{meta['feature_count']} school(s) placed, "
               f"{len(meta['operated_elsewhere'])} operated outside the state and flagged; "
               f"{len(meta['located_elsewhere'])} located in another state and "
               f"{len(meta['unplaced_schools'])} without coordinates listed, not placed")
        with open(args["output"], "w", encoding="utf-8") as fh:
            json.dump(collection, fh, ensure_ascii=False)
        primitive_success(meta, w)


if __name__ == "__main__":
    main()
