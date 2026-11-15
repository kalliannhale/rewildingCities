"""
soil/transform/prepare_health_center_points.py  |  rewildingCities

HRSA's health center sites for one state, as a point layer (Sprint 06, step
3: the third carrier). what is placed, and why, is the health_center_carriers
method's to say (D-212); this file says only how.

  ~ a feature is one site, named by its BPHC Assigned Number, unique on the
    file. the Health Center Number names the grantee, never a site
  ~ the file is a daily snapshot, not a release: our copy is the evidence.
    every row's Data Warehouse Record Create Date must be the declared
    snapshot date, or the copy is not the one declared
  ~ the columns read, and HRSA's codes, are a crosswalk, seeds/crosswalks/
    health_centers/hrsa_health_center_sites.yml, passed whole as `reading`
    (D-206). a column it does not name is never read; a status, site type,
    location type or center type it does not declare refuses the run
  ~ a site is in the state its own fields name, never its grantee's: the
    grantee's state only finds the rows HRSA holds with no site state, so
    they can be listed
  ~ listed, never placed, each with its reason: a site with no point
    (no_point_given), an administrative site (administrative_site), a
    mobile unit (mobile_unit), a site whose address HRSA withholds
    (address_withheld), a site not open (not_open), a site whose own fields
    name another state (located_in_another_state). a point is never made
    for a site HRSA gives none
  ~ every placed site carries its adjectives as HRSA writes them, with
    seasonal and look_alike as booleans and a flags string, so a map can
    show or hide them
  ~ the encoding is declared, never sniffed: the snapshot's own fact, in its
    manifest declaration, which the run's copy must agree with (D-192)
  ~ coordinates are written as HRSA gives them, X as longitude and Y as
    latitude; the geocode's datum is not yet read from HRSA's documentation,
    so the receipt names none

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:  snapshot    the sites CSV as downloaded
Params:
  encoding       required: as the snapshot declares it (source.sites_encoding)
  snapshot_date  required: YYYY-MM-DD, as the snapshot declares it
                 (source.sites_snapshot_date)
  state          required: two-letter postal code
  state_fips     required: two-digit state FIPS
  reading        required: the hrsa_health_center_sites crosswalk, via
                 $crosswalks.hrsa_health_center_sites
Output: geojson points, one feature per placed site. ~
"""

from __future__ import annotations

import io
import json
from datetime import datetime

import pandas as pd

ROLES = ["site_key", "health_center_number", "name", "health_center", "street", "city",
         "site_state", "zip", "hours", "setting", "status", "location_type", "site_type",
         "center_type", "operator", "organization_state", "longitude", "latitude",
         "county_fips", "state_fips", "record_date"]
CODE_MAPS = {"statuses": ("group", {"open", "closed"}),
             "site_types": ("group", {"service", "administrative"}),
             "location_types": ("group", {"fixed", "mobile"}),
             "center_types": ("look_alike", {True, False})}
COLUMN_OF = {"statuses": "status", "site_types": "site_type",
             "location_types": "location_type", "center_types": "center_type"}


class HealthCenterPointsRefused(ValueError):
    """a sites file, or a declaration, that cannot be read as declared."""


def check_reading(reading) -> dict:
    """the crosswalk carries every role and code map the reading needs."""
    if not isinstance(reading, dict):
        raise HealthCenterPointsRefused(
            "reading must be the hrsa_health_center_sites crosswalk, a mapping")
    columns = reading.get("columns")
    if not isinstance(columns, dict):
        raise HealthCenterPointsRefused("the crosswalk declares no columns")
    missing = [r for r in ROLES if not columns.get(r)]
    if missing:
        raise HealthCenterPointsRefused(f"the crosswalk's columns lack {', '.join(missing)}")
    headers = list(columns.values())
    twice = sorted({h for h in headers if headers.count(h) > 1})
    if twice:
        raise HealthCenterPointsRefused(f"header(s) declared for two roles: {', '.join(twice)}")
    for key in ("record_date_format", "no_state"):
        if not isinstance(reading.get(key), str) or not reading[key]:
            raise HealthCenterPointsRefused(f"the crosswalk declares no {key}")
    for name, (field, allowed) in CODE_MAPS.items():
        codes = reading.get(name)
        if not isinstance(codes, dict) or not codes:
            raise HealthCenterPointsRefused(f"the crosswalk declares no {name}")
        for code, entry in codes.items():
            if not isinstance(entry, dict) or entry.get(field) not in allowed:
                raise HealthCenterPointsRefused(
                    f"{name} {code!r} declares no {field} among {sorted(map(str, allowed))}")
    if not isinstance(reading.get("withheld_settings"), list):
        raise HealthCenterPointsRefused("the crosswalk declares no withheld_settings list")
    return reading


def read_sites(raw: bytes, encoding: str, reading: dict) -> pd.DataFrame:
    """the file's declared columns, renamed to their roles, every value text."""
    reading = check_reading(reading)
    try:
        text = raw.decode(encoding)
    except (UnicodeDecodeError, LookupError) as e:
        raise HealthCenterPointsRefused(f"the file is not {encoding}: {e}")
    table = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    by_header = {h: role for role, h in reading["columns"].items()}
    absent = [h for h in by_header if h not in table.columns]
    if absent:
        raise HealthCenterPointsRefused(f"the file lacks the declared column(s) {', '.join(absent)}")
    if table.empty:
        raise HealthCenterPointsRefused("the file holds no rows")
    return table[list(by_header)].rename(columns=by_header).apply(lambda c: c.str.strip())


def check_snapshot(table: pd.DataFrame, snapshot_date: str, reading: dict) -> None:
    """every row was written on the declared day, or this is another copy."""
    try:
        declared = datetime.strptime(str(snapshot_date), "%Y-%m-%d").date()
    except ValueError:
        raise HealthCenterPointsRefused(f"snapshot_date {snapshot_date!r} is not YYYY-MM-DD")
    days = set()
    for v in table["record_date"].unique():
        try:
            days.add(datetime.strptime(v, reading["record_date_format"]).date())
        except ValueError:
            raise HealthCenterPointsRefused(
                f"record date {v!r} is not {reading['record_date_format']}")
    if days != {declared}:
        raise HealthCenterPointsRefused(
            f"the file's record dates are {', '.join(sorted(map(str, days)))}, not the "
            f"declared snapshot {declared}; this is not the copy declared")


def _check_codes(rows: pd.DataFrame, reading: dict) -> None:
    for name, column in COLUMN_OF.items():
        undeclared = sorted(set(rows[column]) - set(reading[name]))
        if undeclared:
            first = rows[rows[column] == undeclared[0]]["site_key"].iloc[0]
            raise HealthCenterPointsRefused(
                f"{column} value(s) {', '.join(map(repr, undeclared))} are not declared in "
                f"the crosswalk's {name} (first seen on {first}); declare each with its "
                f"meaning before it is counted")


def _listed(r, reason: str) -> dict:
    return {"feature_id": r.site_key, "name": r.name, "health_center": r.health_center,
            "city": r.city or None, "reason": reason}


def _coordinate(v):
    n = pd.to_numeric(v, errors="coerce") if v else None
    return None if n is None or pd.isna(n) else float(n)


def points_from(table: pd.DataFrame, state: str, state_fips: str,
                reading: dict) -> tuple[dict, dict]:
    """the state's placed sites as a geojson FeatureCollection, and what the
    receipt says of every site that was not placed."""
    reading = check_reading(reading)
    keys = table["site_key"]
    if (keys == "").any():
        raise HealthCenterPointsRefused(f"{int((keys == '').sum())} site(s) have no "
                                        f"{reading['columns']['site_key']}")
    twice = keys[keys.duplicated(keep=False)]
    if len(twice):
        raise HealthCenterPointsRefused(f"feature id used twice: {twice.iloc[0]}")
    no_state = reading["no_state"]
    ours = ((table["site_state"] == state) | (table["state_fips"] == state_fips)
            | ((table["organization_state"] == state)
               & table["site_state"].isin([no_state, ""])))
    rows = table[ours]
    if rows.empty:
        raise HealthCenterPointsRefused(f"no site has state {state} or state FIPS {state_fips}")
    _check_codes(rows, reading)

    withheld = set(reading["withheld_settings"])
    listed, features = [], []
    for r in rows.itertuples(index=False):
        lon, lat = _coordinate(r.longitude), _coordinate(r.latitude)
        status = reading["statuses"][r.status]["group"]
        site = reading["site_types"][r.site_type]["group"]
        location = reading["location_types"][r.location_type]
        if r.setting in withheld:
            listed.append(_listed(r, "address_withheld"))
            continue
        if lon is None or lat is None:
            listed.append(_listed(r, "no_point_given"))
            continue
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise HealthCenterPointsRefused(f"{r.site_key} has coordinates {lon}, {lat}, "
                                            f"which are not a longitude and latitude")
        if r.site_state != state or r.state_fips != state_fips:
            listed.append(_listed(r, "located_in_another_state"))
            continue
        if status != "open":
            listed.append(_listed(r, "not_open"))
            continue
        if site == "administrative":
            listed.append(_listed(r, "administrative_site"))
            continue
        if location["group"] == "mobile":
            listed.append(_listed(r, "mobile_unit"))
            continue
        seasonal = bool(location.get("seasonal", False))
        look_alike = bool(reading["center_types"][r.center_type]["look_alike"])
        flags = (["seasonal"] if seasonal else []) + (["look_alike"] if look_alike else [])
        flags += [f"setting:{r.setting}", f"operator:{r.operator}"]
        features.append({"type": "Feature",
                         "geometry": {"type": "Point", "coordinates": [lon, lat]},
                         "properties": {
            "feature_id": r.site_key, "name": r.name, "health_center": r.health_center,
            "health_center_number": r.health_center_number, "street": r.street or None,
            "city": r.city or None, "zip": r.zip or None, "county_fips": r.county_fips or None,
            "site_type": r.site_type, "location_type": r.location_type, "setting": r.setting,
            "center_type": r.center_type, "operator": r.operator,
            "hours_per_week": r.hours or None, "seasonal": seasonal, "look_alike": look_alike,
            "flags": ";".join(flags)}})
    coords = [f["geometry"]["coordinates"] for f in features]
    bbox = ([min(c[0] for c in coords), min(c[1] for c in coords),
             max(c[0] for c in coords), max(c[1] for c in coords)] if coords else None)
    reasons = {}
    for item in listed:
        reasons[item["reason"]] = reasons.get(item["reason"], 0) + 1
    meta = {"data_category": "vector", "crs": "EPSG:4326", "feature_count": len(features),
            "geometry_type": "Point", "bbox": bbox, "total_area_m2": 0.0,
            "id_field": "feature_id", "spatial_unit": "health_center_site",
            "attribute_fields": list(features[0]["properties"]) if features else [],
            "seasonal_sites": sum(f["properties"]["seasonal"] for f in features),
            "look_alike_sites": sum(f["properties"]["look_alike"] for f in features),
            "listed_by_reason": dict(sorted(reasons.items())),
            "listed_sites": listed}
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
    w = WarningsCollector("prepare_health_center_points")
    with primitive_error_handling(w):
        p = args["params"]
        with open(get_input(args["inputs"], "snapshot"), "rb") as fh:
            raw = fh.read()
        try:
            reading = require_param(p, "reading")
            snapshot_date = str(require_param(p, "snapshot_date"))
            table = read_sites(raw, require_param(p, "encoding"), reading)
            check_snapshot(table, snapshot_date, reading)
            collection, meta = points_from(table, require_param(p, "state"),
                                           str(require_param(p, "state_fips")), reading)
        except HealthCenterPointsRefused as e:
            primitive_failure("Health center points refused", str(e))
        meta["snapshot_date"] = snapshot_date
        w.info(f"{meta['feature_count']} site(s) placed ({meta['seasonal_sites']} seasonal, "
               f"{meta['look_alike_sites']} look-alike); listed, not placed: "
               f"{meta['listed_by_reason'] or 'none'}")
        with open(args["output"], "w", encoding="utf-8") as fh:
            json.dump(collection, fh, ensure_ascii=False)
        primitive_success(meta, w)


if __name__ == "__main__":
    main()
