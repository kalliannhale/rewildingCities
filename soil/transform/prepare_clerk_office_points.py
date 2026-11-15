"""
soil/transform/prepare_clerk_office_points.py  |  rewildingCities

Municipal clerks' offices as a point layer (Sprint 06, step 3: the fourth
carrier). what is placed, and why, is the clerk_office_carriers method's to
say (D-212); this file says only how.

  ~ the list is a state's clerk list, one row per municipality, read through
    a crosswalk passed whole as `clerks_reading` (D-206). its header must be
    exactly the declared header, in order, because the file names two
    columns twice; a column is read by its declared position and its name
    is checked there. a column the crosswalk does not name is never read:
    clerks' and registrars' names, phones and faxes never enter a run
  ~ a point is an address point that already stands: the state's 911
    address file, read through `addresses_reading`. an office is placed
    where the address point its street address names stands, never by its
    row's code and never where no point stands (D-234, D-237)
  ~ an exact match is the house number, the street and the ZIP, the street
    spelled through USPS Publication 28 (`streets`, D-238): every
    directional word becomes its abbreviation and a street's last word, if
    it follows a name, becomes its suffix's primary name, on both sides
    alike. nothing else is forgiven: no fuzzy match, no guessed suffix
  ~ one point per distinct office (D-237). its feature id is the address
    point's own SITE_UID, and every row whose address names it is a
    municipality it answers for, kept on the point (SERVES-1). a row's code
    is a check and a serves-key, never a placer
  ~ listed, never placed, each with its reason: no street address
    (no_street_address), a post office box (po_box_only), a line that does
    not open with a house number (number_not_read), no ZIP (no_zip), an
    address in another state (address_in_another_state), no address point
    at that number, street and ZIP (no_match), more than one that neither
    the building rule nor the run's choice settles (tie)
  ~ a tie is first read as one building (a rule): when exactly one
    candidate carries no unit, building, floor or room, it is the building
    and the others are doors inside it (placed_by building_point). a tie
    that survives is a campus, several structures under one address, and
    the method's choice campus_ties says what it becomes: listed, or the
    one candidate the address file classes as its declared municipal class
    (placed_by municipal_class, flagged tie_broken_by_class). a class never
    finds an office; it only chooses among points one address already
    named, and every such point carries how many candidates stood there and
    how far apart
  ~ the list's encoding is declared, never sniffed: its own fact, in its
    manifest declaration, which the run's copy must agree with (D-192). the
    address file's layer and CRS are declared in its crosswalk and checked
    against the file itself
  ~ points are reprojected from the file's CRS to EPSG:4326 by pyproj's
    default operation for that pair, which the receipt names

Contract (pr_io): argv <inputs_json> <output_path> <params_json>
Inputs:  clerks     the state's clerk list as downloaded (csv)
         addresses  the state's 911 address file as downloaded
Params:
  encoding           required: as the list declares it (source.clerks_encoding)
  state              required: two-letter postal code
  clerks_reading     required: the list's crosswalk, via $crosswalks.<name>
  addresses_reading  required: the address file's crosswalk, via $crosswalks.<name>
  streets            required: the usps_pub28 crosswalk, via $crosswalks.usps_pub28
  campus_ties        required: listed | municipal_class, the method's choice
Output: geojson points, one feature per placed office. ~
"""

from __future__ import annotations

import csv
import io
import json
import math
import re

import pandas as pd

CLERK_ROLES = ["municipality", "street", "street_note", "city_state_zip", "geocode"]
ADDRESS_ROLES = ["site_uid", "number", "number_suffix", "predir", "street_name", "suffix",
                 "postdir", "zip", "town", "state", "place_type", "placement", "landmark",
                 "unit", "building", "floor", "room"]
SUBADDRESS = ["unit", "building", "floor", "room"]
CAMPUS_TIES = ("listed", "municipal_class")
PO_BOX = re.compile(r"^\s*P\.?\s*O\.?\s*BOX\b", re.I)
NUMBERED = re.compile(r"^(\d+)([A-Z]?)\s+(\S.*)$")
LAST_LINE = re.compile(r"\b([A-Z]{2})\s+(\d{5})(?:-\d{4})?\s*$")
ZIP5 = re.compile(r"^\d{5}")


class ClerkOfficesRefused(ValueError):
    """a list, an address file, or a declaration that cannot be read as declared."""


# ── how a street is spelled (USPS Publication 28) ────────────────────────────
def build_spelling(streets) -> dict:
    """every C1 form to its primary name, and every directional word to its
    abbreviation. a form C1 lists in two groups must be resolved by name."""
    if not isinstance(streets, dict):
        raise ClerkOfficesRefused("streets must be the usps_pub28 crosswalk, a mapping")
    suffixes, resolved = streets.get("suffixes"), streets.get("resolved")
    directionals = streets.get("directionals")
    if not isinstance(suffixes, dict) or not suffixes:
        raise ClerkOfficesRefused("the streets crosswalk declares no suffixes")
    if not isinstance(resolved, dict) or not isinstance(directionals, dict) or not directionals:
        raise ClerkOfficesRefused("the streets crosswalk declares no resolved or no directionals")
    owners: dict = {}
    for primary, group in suffixes.items():
        forms = group.get("forms") if isinstance(group, dict) else None
        if not forms or primary not in forms:
            raise ClerkOfficesRefused(f"suffix {primary!r} lists no forms, or not its own name")
        for form in forms:
            owners.setdefault(str(form), []).append(str(primary))
    to_primary = {}
    for form, groups in owners.items():
        if len(groups) == 1:
            to_primary[form] = groups[0]
        elif form in resolved and resolved[form] in groups:
            to_primary[form] = resolved[form]
        else:
            raise ClerkOfficesRefused(
                f"{form!r} is listed in {', '.join(groups)} and the crosswalk's resolved "
                f"names {'no group for it' if form not in resolved else repr(resolved[form])}")
    for form in resolved:
        if len(owners.get(form, [])) < 2:
            raise ClerkOfficesRefused(f"resolved names {form!r}, which is not in two groups")
    words = {str(k).upper(): str(v).upper() for k, v in directionals.items()}
    abbreviations = set(words.values())
    return {"suffix": to_primary, "direction": {**words, **{a: a for a in abbreviations}},
            "abbreviations": abbreviations}


def normalize_street(text, spelling: dict):
    """one spelling of a street, or None if nothing is left of it."""
    s = re.sub(r"[.,']", "", str(text or "").upper()).replace("-", " ")
    words = [spelling["direction"].get(w, w) for w in s.split()]
    if not words:
        return None
    last = len(words) - 1
    while last > 0 and words[last] in spelling["abbreviations"]:
        last -= 1
    if last >= 1:
        words[last] = spelling["suffix"].get(words[last], words[last])
    return " ".join(words)


# ── the clerk list ───────────────────────────────────────────────────────────
def check_clerks_reading(reading) -> dict:
    if not isinstance(reading, dict):
        raise ClerkOfficesRefused("clerks_reading must be the list's crosswalk, a mapping")
    header, columns = reading.get("header"), reading.get("columns")
    if not isinstance(header, list) or not header:
        raise ClerkOfficesRefused("the list's crosswalk declares no header")
    if not isinstance(columns, dict):
        raise ClerkOfficesRefused("the list's crosswalk declares no columns")
    missing = [r for r in CLERK_ROLES if r not in columns]
    if missing:
        raise ClerkOfficesRefused(f"the list's crosswalk lacks {', '.join(missing)}")
    for role, spec in columns.items():
        if (not isinstance(spec, dict) or not isinstance(spec.get("position"), int)
                or not 0 <= spec["position"] < len(header)
                or header[spec["position"]] != spec.get("name")):
            raise ClerkOfficesRefused(
                f"column {role} must name a position in the header and the header's name there")
    positions = [spec["position"] for spec in columns.values()]
    if len(set(positions)) != len(positions):
        raise ClerkOfficesRefused("two roles are declared at one position")
    return reading


def read_clerks(raw: bytes, encoding: str, reading: dict) -> pd.DataFrame:
    """the declared columns, by position, renamed to their roles, every value text."""
    reading = check_clerks_reading(reading)
    try:
        text = raw.decode(encoding)
    except (UnicodeDecodeError, LookupError) as e:
        raise ClerkOfficesRefused(f"the list is not {encoding}: {e}")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows or rows[0] != reading["header"]:
        got = rows[0] if rows else []
        raise ClerkOfficesRefused(f"the list's header is {got}, not the declared {reading['header']}")
    body = [r for r in rows[1:] if any(c.strip() for c in r)]
    if not body:
        raise ClerkOfficesRefused("the list holds no rows")
    width = len(reading["header"])
    short = [i + 2 for i, r in enumerate(body) if len(r) != width]
    if short:
        raise ClerkOfficesRefused(f"line(s) {short[:5]} do not hold {width} fields")
    table = pd.DataFrame({role: [r[spec["position"]].strip() for r in body]
                          for role, spec in reading["columns"].items()})
    blank = table["municipality"] == ""
    if blank.any():
        raise ClerkOfficesRefused(f"{int(blank.sum())} row(s) name no municipality")
    twice = table["municipality"][table["municipality"].duplicated(keep=False)]
    if len(twice):
        raise ClerkOfficesRefused(f"municipality listed twice: {twice.iloc[0]}")
    return table


def clerk_keys(table: pd.DataFrame, state: str, spelling: dict) -> pd.DataFrame:
    """each row's match key, or the reason it has none."""
    keys, reasons, zips = [], [], []
    for r in table.itertuples(index=False):
        street = r.street.upper()
        last_line = LAST_LINE.search(r.city_state_zip.upper())
        key, reason, zip5 = None, None, last_line.group(2) if last_line else None
        numbered = NUMBERED.match(street)
        if not street:
            reason = "no_street_address"
        elif PO_BOX.match(street):
            reason = "po_box_only"
        elif not numbered or normalize_street(numbered.group(3), spelling) is None:
            reason = "number_not_read"
        elif not last_line:
            reason = "no_zip"
        elif last_line.group(1) != state:
            reason = "address_in_another_state"
        else:
            key = (f"{int(numbered.group(1))}{numbered.group(2)}|"
                   f"{normalize_street(numbered.group(3), spelling)}|{zip5}")
        keys.append(key)
        reasons.append(reason)
        zips.append(zip5)
    return table.assign(key=keys, reason=reasons, zip=zips)


# ── the address points ───────────────────────────────────────────────────────
def check_addresses_reading(reading) -> dict:
    if not isinstance(reading, dict):
        raise ClerkOfficesRefused("addresses_reading must be the address file's crosswalk, a mapping")
    for key in ("layer", "crs", "municipal_class"):
        if not isinstance(reading.get(key), str) or not reading[key]:
            raise ClerkOfficesRefused(f"the address file's crosswalk declares no {key}")
    columns = reading.get("columns")
    if not isinstance(columns, dict):
        raise ClerkOfficesRefused("the address file's crosswalk declares no columns")
    missing = [r for r in ADDRESS_ROLES if not columns.get(r)]
    if missing:
        raise ClerkOfficesRefused(f"the address file's crosswalk lacks {', '.join(missing)}")
    return reading


def read_address_points(path: str, reading: dict) -> tuple[pd.DataFrame, str]:
    """the declared layer's declared columns, renamed to their roles, with
    longitude and latitude in EPSG:4326, and the operation that made them."""
    import pyogrio
    from pyproj import Transformer
    reading = check_addresses_reading(reading)
    layers = [name for name, _ in pyogrio.list_layers(path)]
    if reading["layer"] not in layers:
        raise ClerkOfficesRefused(f"the address file holds no layer {reading['layer']}; it holds {layers}")
    info = pyogrio.read_info(path, layer=reading["layer"])
    if str(info.get("crs")) != reading["crs"]:
        raise ClerkOfficesRefused(f"the address layer is in {info.get('crs')}, not the declared {reading['crs']}")
    by_field = {field: role for role, field in reading["columns"].items()}
    absent = [f for f in by_field if f not in list(info["fields"])]
    if absent:
        raise ClerkOfficesRefused(f"the address layer lacks the declared field(s) {', '.join(absent)}")
    frame = pyogrio.read_dataframe(path, layer=reading["layer"], columns=list(by_field))
    transformer = Transformer.from_crs(reading["crs"], "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(frame.geometry.x.to_numpy(), frame.geometry.y.to_numpy())
    points = pd.DataFrame(frame.drop(columns="geometry")).rename(columns=by_field)
    points = points.astype(object).where(points.notna(), "").astype(str).apply(lambda c: c.str.strip())
    return points.assign(longitude=lon, latitude=lat), _operation(transformer, reading["crs"])


def _operation(transformer, crs: str) -> str:
    """the operation pyproj used, named; a transformer holding several
    candidates names none until it is used, and some versions never do, so
    the versions are named instead of nothing."""
    import pyproj
    used = getattr(transformer, "last_used_operation", None)
    if used is not None and getattr(used, "description", ""):
        return used.description
    if not str(transformer.description).startswith("unavailable"):
        return transformer.description
    return (f"{crs} to EPSG:4326 by pyproj {pyproj.__version__} (PROJ "
            f"{pyproj.proj_version_str}); the operation chosen was not reported")


def address_keys(points: pd.DataFrame, spelling: dict) -> pd.DataFrame:
    """each address point's match key, or None when its number or ZIP cannot be read."""
    number = points["number"].str.replace(r"\.0$", "", regex=True)
    good_number = number.str.fullmatch(r"\d+")
    zip5 = points["zip"].str.extract(r"^(\d{5})", expand=False)
    street_text = (points["predir"] + " " + points["street_name"] + " " + points["suffix"]
                   + " " + points["postdir"]).str.strip()
    spelled = {s: normalize_street(s, spelling) for s in street_text.unique()}
    street = street_text.map(spelled)
    key = (number.where(good_number, "").map(lambda n: str(int(n)) if n else "")
           + points["number_suffix"].str.upper() + "|" + street.fillna("") + "|" + zip5.fillna(""))
    readable = good_number & zip5.notna() & street.notna()
    return points.assign(key=key.where(readable, None))


# ── matching ─────────────────────────────────────────────────────────────────
def _spread_m(points: pd.DataFrame) -> float:
    """the greatest distance between any two candidates, in metres (haversine)."""
    lon = points["longitude"].astype(float).tolist()
    lat = points["latitude"].astype(float).tolist()
    far = 0.0
    for i in range(len(lon)):
        for j in range(i + 1, len(lon)):
            p1, p2 = math.radians(lat[i]), math.radians(lat[j])
            a = (math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2)
                 * math.sin(math.radians(lon[j] - lon[i]) / 2) ** 2)
            far = max(far, 2 * 6371008.8 * math.asin(math.sqrt(a)))
    return far


def settle_tie(found: pd.DataFrame, campus_ties: str, municipal_class: str):
    """the one point a tie settles on, and how, or (None, None)."""
    bare = found[(found[SUBADDRESS] == "").all(axis=1)]
    if len(bare) == 1:
        return bare.iloc[0], "building_point"
    if campus_ties == "municipal_class":
        civic = found[found["place_type"] == municipal_class]
        if len(civic) == 1:
            return civic.iloc[0], "municipal_class"
    return None, None


def _listed(r, reason: str, candidates: int | None = None) -> dict:
    item = {"feature_id": r.municipality, "municipality": r.municipality,
            "geocode": r.geocode or None, "street": r.street or None,
            "zip": r.zip if isinstance(r.zip, str) else None, "reason": reason}
    if candidates is not None:
        item["candidates"] = candidates
    return item


def place(clerks: pd.DataFrame, points: pd.DataFrame, state: str, spelling: dict,
          operation: str = "", campus_ties: str = "listed",
          municipal_class: str = "") -> tuple[dict, dict]:
    """the placed offices as a geojson FeatureCollection, and what the receipt
    says of every row that was not placed."""
    if campus_ties not in CAMPUS_TIES:
        raise ClerkOfficesRefused(f"campus_ties {campus_ties!r} is not one of {', '.join(CAMPUS_TIES)}")
    if campus_ties == "municipal_class" and not municipal_class:
        raise ClerkOfficesRefused("campus_ties municipal_class needs the address file's declared municipal_class")
    keyed = clerk_keys(clerks, state, spelling)
    points = address_keys(points, spelling)
    wanted = {k for k in keyed["key"] if isinstance(k, str)}
    candidates = points[points["key"].isin(wanted)]
    by_key = {k: g for k, g in candidates.groupby("key")}
    listed, offices = [], {}
    for r in keyed.itertuples(index=False):
        if isinstance(r.reason, str):
            listed.append(_listed(r, r.reason))
            continue
        found = by_key.get(r.key)
        if found is None:
            listed.append(_listed(r, "no_match"))
            continue
        how, tie = "exact", None
        if len(found) > 1:
            point, how = settle_tie(found, campus_ties, municipal_class)
            if point is None:
                listed.append(_listed(r, "tie", candidates=len(found)))
                continue
            tie = {"candidates": len(found), "spread_m": round(_spread_m(found), 1)}
        else:
            point = found.iloc[0]
        if not point["site_uid"]:
            raise ClerkOfficesRefused(f"the address point matched for {r.municipality} has no "
                                      f"site id; an office cannot be named")
        office = offices.setdefault(point["site_uid"], {"point": point, "rows": [], "how": how, "tie": tie})
        office["rows"].append(r)
    features = []
    for site_uid, office in sorted(offices.items()):
        point, rows = office["point"], sorted(office["rows"], key=lambda x: x.municipality)
        how, tie = office["how"], office["tie"] or {}
        names = [x.municipality for x in rows]
        notes = sorted({x.street_note for x in rows if x.street_note})
        flags = (["shared_office"] if len(rows) > 1 else []) + (
            ["tie_broken_by_class"] if how == "municipal_class" else []) + [
            f"placement:{point['placement'] or 'none'}", f"place_type:{point['place_type'] or 'none'}"]
        features.append({"type": "Feature",
                         "geometry": {"type": "Point",
                                      "coordinates": [float(point["longitude"]), float(point["latitude"])]},
                         "properties": {
            "feature_id": site_uid,
            "name": f"Municipal clerk, {names[0]}" + (f" (and {len(names) - 1} more)" if len(names) > 1 else ""),
            "municipalities": "; ".join(names),
            "geocodes": "; ".join(sorted({x.geocode for x in rows if x.geocode})) or None,
            "rows_served": len(rows), "street": rows[0].street, "zip": rows[0].zip,
            "street_notes": "; ".join(notes) or None, "e911_town": point["town"] or None,
            "place_type": point["place_type"] or None, "placement": point["placement"] or None,
            "landmark": point["landmark"] or None, "placed_by": how,
            "tie_candidates": tie.get("candidates"), "tie_spread_m": tie.get("spread_m"),
            "flags": ";".join(flags)}})
    coords = [f["geometry"]["coordinates"] for f in features]
    bbox = ([min(c[0] for c in coords), min(c[1] for c in coords),
             max(c[0] for c in coords), max(c[1] for c in coords)] if coords else None)
    reasons = {}
    for item in listed:
        reasons[item["reason"]] = reasons.get(item["reason"], 0) + 1
    meta = {"data_category": "vector", "crs": "EPSG:4326", "feature_count": len(features),
            "geometry_type": "Point", "bbox": bbox, "total_area_m2": 0.0,
            "id_field": "feature_id", "spatial_unit": "municipal_clerk_office",
            "attribute_fields": list(features[0]["properties"]) if features else [],
            "rows_read": len(keyed), "rows_placed": sum(len(o["rows"]) for o in offices.values()),
            "shared_offices": sum(1 for o in offices.values() if len(o["rows"]) > 1),
            "campus_ties": campus_ties,
            "offices_by_placed_by": dict(sorted(
                {h: sum(1 for o in offices.values() if o["how"] == h)
                 for h in {o["how"] for o in offices.values()}}.items())),
            "address_points_read": len(points),
            "address_points_unkeyed": int(points["key"].isna().sum()),
            "reprojection": operation or None,
            "listed_by_reason": dict(sorted(reasons.items())), "listed_rows": listed}
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
    w = WarningsCollector("prepare_clerk_office_points")
    with primitive_error_handling(w):
        p = args["params"]
        with open(get_input(args["inputs"], "clerks"), "rb") as fh:
            raw = fh.read()
        try:
            state = str(require_param(p, "state"))
            spelling = build_spelling(require_param(p, "streets"))
            clerks = read_clerks(raw, require_param(p, "encoding"), require_param(p, "clerks_reading"))
            addresses_reading = require_param(p, "addresses_reading")
            points, operation = read_address_points(get_input(args["inputs"], "addresses"),
                                                    addresses_reading)
            collection, meta = place(clerks, points, state, spelling, operation,
                                     str(require_param(p, "campus_ties")),
                                     addresses_reading.get("municipal_class", ""))
        except ClerkOfficesRefused as e:
            primitive_failure("Clerk office points refused", str(e))
        w.info(f"{meta['feature_count']} office(s) placed for {meta['rows_placed']} of "
               f"{meta['rows_read']} row(s) ({meta['shared_offices']} shared); listed, not "
               f"placed: {meta['listed_by_reason'] or 'none'}")
        with open(args["output"], "w", encoding="utf-8") as fh:
            json.dump(collection, fh, ensure_ascii=False)
        primitive_success(meta, w)


if __name__ == "__main__":
    main()
