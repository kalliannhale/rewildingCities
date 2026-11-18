"""
rehearse_places_webmap.py ~ Sprint 09's second rehearsal: the places as one web map

session 2 pushed the towns as a separate Feature Collection item. Search,
Text and Table read it, but Experience Builder's Map widget reads only web
maps, and Map Viewer dropped the item when it saved one. Esri's web map
specification keeps a feature collection inside the web map's own JSON, so
this rehearsal sends every explorer level as one web map, one layer per level,
and reads it back.

everything comes from the canonical store, by public URL through CloudFront,
the way the door reads: the profile's current version, told by
canopy/wonder/telling.py, and each level's outline, each checked against its
own sha256. a place's point is display.py's marker, a point on the place's own
surface, projected to Web Mercator with the door's own _mercator, so the
rehearsal sends what the door would send. the state's outline was never written
canonically, so the state is left out and said so.

it writes nothing to the bucket. ArcGIS gets one item, private, in the test
target's folder, and places_webmap_sent.json beside this file records what
was sent. it lives in tests/rehearsals/sprint-09/ and is committed with
that record, since a rehearsal is evidence (session 2's first script was lost
with _sprint06/); what it finds goes in the ledger.

  python <this file>                 dry run: tell, place, build, report
  python <this file> --write         also send it, private, and read it back
  python <this file> --check         read the sent item back again (after each
                                     hand step in Experience Builder)
  python <this file> --polygons      the polygon size and validity read
                                     (EXPLORE-1): sends nothing, writes nothing
  python <this file> --polygons --tolerances 25,100,250,500 --decimals 0,1
                                --polygon-levels cousub
  python <this file> --polygons --write --tolerances 250 --decimals 0
                                --polygon-levels cousub
                                     send ONE shapes map, private, recorded in
                                     places_polygons_sent.json (never session
                                     3's record), and read it back
  python <this file> --polygons --check
                                     read the shapes map back again

the polygon read (Sprint 09 session 4) asks whether the places can be drawn as
shapes inside the one web map instead of as points. for each tolerance, each
level's outline is simplified as one coverage by the door's own
display._simplify_coverage (pinches opened as the door opens them; a refusal
caught and said, never a crash), then written as the web map would hold it:
Web Mercator by the door's _mercator, rounded to --decimals places of a meter,
every ring wound Esri's way (outer rings clockwise, holes counterclockwise:
the opposite of GeoJSON's RFC 7946). the whole outline is simplified, so
neighbours keep one edge, but only places with a told row are measured and
drawn. validity is read at three stages, each failure with shapely's reason:
the canonical outline, the simplified shape before rounding, and the rounded
rings, so a failure is laid at the step that caused it. it reports parts and
area kept per place (an island shrunk or gone), bytes per level, and two whole
maps per tolerance and rounding: every level shaped, and only --polygon-levels
shaped with every other level a point, in the points map's own layer order
(the last drawn on top). bytes are measured in D-362's form, every whole float
an integer. no limit is applied: LIMIT-1 has no source, so the suite's
4,000,000 is printed as a line to read against, not a pass.

the write (session 4) sends the points map with the named levels swapped for
shapes, and holds one rule: never send an invalid shape. a level is rounded to
--decimals; if any of its places comes back invalid, emptied or with a ring
collapsed, the whole level is rounded one place finer, so neighbours keep one
edge; if that fails too, nothing is sent. it sends D-362's form, so the stored
map should hash the same as the sent one.

run it from the rewildingCities repo root. ~
"""

from __future__ import annotations

import argparse
import copy as _copy
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path.cwd()
if not (ROOT / "canopy" / "wonder" / "telling.py").is_file():
    sys.exit("run this from the rewildingCities repo root")
sys.path.insert(0, str(ROOT))

from canopy.aws import display, s3  # noqa: E402
from canopy.expose.publish import DOMAIN_ENV, VERSION, _ask, default_fetch  # noqa: E402
from canopy.expose.targets import PublishRefusal, load_targets, registered  # noqa: E402
from canopy.expose.targets.arcgis_webmap import (BASEMAP, SPEC_VERSION, WEB_MERCATOR,  # noqa: E402
                                                 _esri_type, _mark, _mercator, extent_of)
from canopy.wonder.telling import LEVELS, tell_all  # noqa: E402

PLOT = "maine"
TARGET = "test"
PROFILE = "place_profile_profiles"
OUTLINES = {"county": "outline_counties_outline", "sldu": "outline_senate_outline",
            "sldl": "outline_house_outline", "cousub": "outline_towns_outline",
            "aiannh": "outline_tribal_outline"}
ORDER = ("state", "county", "sldu", "sldl", "cousub", "aiannh")
OID = "OBJECTID"
TITLE = "Rehearsal: Maine places as one web map (Sprint 09)"
SENT = Path(__file__).resolve().parent / "places_webmap_sent.json"
POLYGON_TITLE = "Rehearsal: Maine places, some levels as shapes (Sprint 09)"
POLYGON_SENT = Path(__file__).resolve().parent / "places_polygons_sent.json"


def canonical(doc) -> str:
    """keys sorted, no spaces: the text two equal documents always share."""
    return json.dumps(doc, sort_keys=True, separators=(",", ":"))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --- reading the canonical store ---------------------------------------------

_READ: dict = {}


def read_version(base: str, artifact: str) -> tuple[str, bytes]:
    """a harvest's current version, its bytes checked against its sha256.
    read once per run: the polygon read and the points map share each read."""
    if (base, artifact) not in _READ:
        _READ[(base, artifact)] = _read_version(base, artifact)
    return _READ[(base, artifact)]


def _read_version(base: str, artifact: str) -> tuple[str, bytes]:
    raw = default_fetch(f"{base}/{s3.pointer_key(PLOT, artifact)}")
    if raw is None:
        sys.exit(f"STOP: {artifact} has no current pointer in the bucket")
    pointer = json.loads(raw)
    version, name = pointer["sha256"], pointer["data"]
    data = default_fetch(f"{base}/{s3.version_prefix(PLOT, artifact, version)}/{name}")
    if data is None:
        sys.exit(f"STOP: {artifact} version {version[:12]} names {name}, which is not there")
    got = hashlib.sha256(data).hexdigest()
    if got != version:
        sys.exit(f"STOP: {artifact}'s bytes hash to {got[:12]}, not its version {version[:12]}")
    return version, data


def points_of(base: str, artifact: str) -> tuple[str, dict]:
    """(version, {(authority, code): (x, y)}): one point on each place's own
    surface, as display.py draws markers, then in Web Mercator to the cm."""
    version, data = read_version(base, artifact)
    frame = display._read_frame(data)
    for col in ("authority", "code"):
        if col not in frame.columns:
            sys.exit(f"STOP: {artifact} carries no '{col}' column, so no row can find its place")
    marked, _step = display._markers(frame, "code")
    out = {}
    for a, c, g in zip(marked["authority"], marked["code"], marked.geometry):
        x, y = _mercator(g.x, g.y)
        out[(str(a), str(c))] = (round(x, 2), round(y, 2), g.x, g.y)
    return version, out


# --- building the web map ----------------------------------------------------

def fields_for(rows: list[dict]) -> list[dict]:
    """the told fields, typed from their own values as the door types them;
    a string's length is the longest value it holds, never less than 256."""
    names: list[str] = []
    for r in rows:
        for k in r:
            if k not in names:
                names.append(k)
    out = [{"name": OID, "alias": OID, "type": "esriFieldTypeOID",
            "editable": False, "nullable": False}]
    for n in names:
        kind, length = _esri_type([r.get(n) for r in rows])
        f = {"name": n, "alias": n, "type": kind, "editable": False, "nullable": True}
        if length:
            f["length"] = length
        out.append(f)
    return out


def layer_for(level: str, rows: list[dict], points: dict) -> dict:
    fields = fields_for(rows)
    features = []
    for i, r in enumerate(rows, start=1):
        x, y, _lon, _lat = points[(r["authority"], r["code"])]
        features.append({"geometry": {"x": x, "y": y},
                         "attributes": dict(r, **{OID: i})})
    xs = [f["geometry"]["x"] for f in features]
    ys = [f["geometry"]["y"] for f in features]
    pad = 1000.0
    extent = {"xmin": min(xs) - pad, "ymin": min(ys) - pad, "xmax": max(xs) + pad,
              "ymax": max(ys) + pad, "spatialReference": dict(WEB_MERCATOR)}
    shown = ("about", "note", "carriers", "cannot_answer")
    return {
        "id": f"rewilding-places-{level}",
        "title": f"{LEVELS[level]} ({PLOT})",
        "layerType": "ArcGISFeatureLayer",
        "visibility": True,
        "opacity": 1,
        "featureCollection": {
            "showLegend": True,
            "layers": [{
                "layerDefinition": {
                    "name": LEVELS[level],
                    "type": "Feature Layer",
                    "geometryType": "esriGeometryPoint",
                    "objectIdField": OID,
                    "displayField": "name",
                    "fields": fields,
                    "extent": extent,
                    "drawingInfo": {"renderer": {"type": "simple", "symbol": _mark(6)}},
                },
                "featureSet": {"geometryType": "esriGeometryPoint",
                               "spatialReference": dict(WEB_MERCATOR),
                               "features": features},
                "popupInfo": {
                    "title": "{name}",
                    "popupElements": [{"type": "fields"}],
                    "showAttachments": False,
                    "fieldInfos": [{"fieldName": f["name"], "label": f["name"],
                                    "isEditable": False, "visible": f["name"] in shown}
                                   for f in fields],
                },
            }],
        },
    }


_TOLD: dict = {}


def told_by_level(base: str) -> tuple[str, dict, dict]:
    """(profile version, told rows by level, levels the telling skips): the
    one place both the points map and the polygon read get their rows, told
    once per run."""
    if base not in _TOLD:
        _TOLD[base] = _told_by_level(base)
    return _TOLD[base]


def _told_by_level(base: str) -> tuple[str, dict, dict]:
    profile_version, raw = read_version(base, PROFILE)
    rows, ctx = tell_all(json.loads(raw), ROOT)
    level_of = {label: lv for lv, label in LEVELS.items()}
    by_level: dict = {lv: [] for lv in ORDER}
    for r in rows:
        by_level[level_of[r["level"]]].append(r)
    return profile_version, by_level, dict(ctx.skipped)


def build(base: str) -> tuple[dict, dict]:
    """(web map, report). told from the profile's current version, placed on
    each level's current outline; nothing invented, every row left out named."""
    profile_version, by_level, skipped = told_by_level(base)

    report = {"profile_version": profile_version, "skipped_levels": skipped,
              "levels": {}}
    layers, lonlat = [], []
    for lv in ORDER:
        told = by_level[lv]
        line = {"told": len(told), "placed": 0, "left_out": [], "outline": None,
                "outline_places_without_row": 0, "longest": None}
        report["levels"][lv] = line
        artifact = OUTLINES.get(lv)
        if artifact is None:
            line["left_out"] = [f"{r['key']} (no canonical outline for this level yet)"
                                for r in told]
            continue
        outline_version, points = points_of(base, artifact)
        line["outline"] = f"{artifact} {outline_version[:12]}"
        placed = [r for r in told if (r["authority"], r["code"]) in points]
        line["left_out"] = [f"{r['key']} (no point in {artifact})"
                            for r in told if (r["authority"], r["code"]) not in points]
        line["placed"] = len(placed)
        keys = {(r["authority"], r["code"]) for r in told}
        line["outline_places_without_row"] = sum(1 for k in points if k not in keys)
        if not placed:
            continue
        longest = max(((k, len(str(v))) for r in placed for k, v in r.items()),
                      key=lambda kv: kv[1])
        line["longest"] = {"field": longest[0], "chars": longest[1]}
        layers.append(layer_for(lv, placed, points))
        lonlat += [points[(r["authority"], r["code"])][2:] for r in placed]

    lons, lats = [p[0] for p in lonlat], [p[1] for p in lonlat]
    bbox = [min(lons), min(lats), max(lons), max(lats)]
    report["bbox"] = bbox
    webmap = {
        "operationalLayers": layers,
        "baseMap": _copy.deepcopy(BASEMAP),
        "spatialReference": dict(WEB_MERCATOR),
        "authoringApp": "rewildingCities rehearsal",
        "authoringAppVersion": VERSION,
        "version": SPEC_VERSION,
        "initialState": {"viewpoint": {"targetGeometry": extent_of(bbox)}},
    }
    return webmap, report


def counts_of(webmap: dict) -> dict:
    """features per layer id; a layer stored in another shape counts as None,
    so a read back says what came back instead of crashing on it."""
    out = {}
    for layer in webmap.get("operationalLayers") or []:
        inner = ((layer.get("featureCollection") or {}).get("layers") or [{}])[0]
        features = (inner.get("featureSet") or {}).get("features")
        out[layer.get("id")] = None if features is None else len(features)
    return out


# --- the polygon read (EXPLORE-1) ---------------------------------------------

LIMIT_LINE = 4_000_000   # tests/test_telling.py's ITEM_BYTES, which names no source (LIMIT-1)
DEFAULT_TOLERANCES = (100, 250, 500)
DEFAULT_DECIMALS = (0,)
DEFAULT_SHAPED = ("cousub",)
SHOWN = 10               # places listed per line
FILL = {"type": "esriSFS", "style": "esriSFSSolid", "color": [37, 52, 148, 40],
        "outline": {"type": "esriSLS", "style": "esriSLSSolid",
                    "color": [37, 52, 148, 255], "width": 0.75}}


def door_form(doc):
    """D-362's form: every whole float written as an integer, as ArcGIS stores
    it, so bytes are measured as the door would send them."""
    if isinstance(doc, dict):
        return {k: door_form(v) for k, v in doc.items()}
    if isinstance(doc, list):
        return [door_form(v) for v in doc]
    if isinstance(doc, float) and doc.is_integer():
        return int(doc)
    return doc


def _signed_area(ring) -> float:
    """twice the shoelace area of a closed ring: above zero when it runs
    counterclockwise, below zero when clockwise."""
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:]))


def _rounder(decimals: int):
    if decimals == 0:
        return lambda v: int(round(v))
    return lambda v: round(v, decimals)


def esri_ring(coords, outer: bool, decimals: int = 0) -> list | None:
    """one ring as Esri JSON holds it: Web Mercator by the door's _mercator,
    rounded to `decimals` places of a meter, a vertex the rounding repeats
    dropped, closed, wound clockwise when outer and counterclockwise when a
    hole (Esri's rule, the opposite of RFC 7946). None when the rounding
    collapses it: fewer than three distinct corners, or no area left."""
    rnd = _rounder(decimals)
    out: list = []
    for c in coords:
        x, y = _mercator(c[0], c[1])
        p = [rnd(x), rnd(y)]
        if not out or p != out[-1]:
            out.append(p)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    if len(out) < 3:
        return None
    out.append(list(out[0]))
    area = _signed_area(out)
    if area == 0:
        return None
    if (area > 0) == outer:      # outer wants below zero (clockwise), a hole above
        out.reverse()
    return out


def esri_polygon(geom, decimals: int = 0) -> tuple[list, dict]:
    """(rings, what the rounding did) for one place: each part's outer ring,
    then its holes. the shape rebuilt from the rounded rings is checked for
    validity, and its reason kept, since rounding can pinch what simplifying
    left clean."""
    import shapely
    rings, polys, collapsed = [], [], 0
    for part in shapely.get_parts(geom):
        shell = esri_ring(part.exterior.coords, True, decimals)
        if shell is None:
            collapsed += 1 + len(part.interiors)
            continue
        holes = []
        for ring in part.interiors:
            h = esri_ring(ring.coords, False, decimals)
            if h is None:
                collapsed += 1
            else:
                holes.append(h)
        polys.append(shapely.Polygon(shell, holes))
        rings += [shell] + holes
    if not polys:
        return rings, {"collapsed": collapsed, "invalid": None, "gone": True}
    whole = polys[0] if len(polys) == 1 else shapely.MultiPolygon(polys)
    reason = None if whole.is_valid else shapely.is_valid_reason(whole)
    return rings, {"collapsed": collapsed, "invalid": reason, "gone": False}


def _keys(frame) -> list:
    return list(zip(frame["authority"].astype(str), frame["code"].astype(str)))


def invalid_in(frame, keys: set) -> list:
    """(key, shapely's reason) for every told place whose shape is not valid."""
    import numpy
    import shapely
    geoms = numpy.asarray(frame.geometry)
    bad = ~shapely.is_valid(geoms)
    return [(k, str(shapely.is_valid_reason(geoms[i])))
            for i, k in enumerate(_keys(frame)) if bad[i] and k in keys]


def simplify_level(frame, tolerance: int, keys: set) -> dict:
    """one level at one tolerance, by the door's own function on the whole
    outline, so neighbours keep one edge: what it kept of each told place
    (parts, area) and which shapes it left invalid, before any rounding."""
    import numpy
    import shapely
    started = time.monotonic()
    geoms = numpy.asarray(frame.geometry)
    vertices_before = int(shapely.get_num_coordinates(geoms).sum())
    try:
        simple, steps = display._simplify_coverage(frame, tolerance, "code", vertices_before)
    except s3.CanonicalRefusal as e:
        return {"refused": getattr(e, "reason", None) or str(e),
                "seconds": time.monotonic() - started}
    parts_before = shapely.get_num_geometries(geoms)
    parts_after = shapely.get_num_geometries(numpy.asarray(simple.geometry))
    area_before = numpy.asarray(frame.to_crs(display.PROJECTED).area)
    area_after = numpy.asarray(simple.to_crs(display.PROJECTED).area)
    out = {"simple": simple, "lost": [], "least_area": None,
           "opened": sum(s.get("count", 0) for s in steps if s.get("step") == "opened"),
           "invalid": invalid_in(simple, keys)}
    for i, key in enumerate(_keys(simple)):
        if key not in keys:
            continue
        kept = float(area_after[i] / area_before[i]) if area_before[i] else 1.0
        if out["least_area"] is None or kept < out["least_area"][1]:
            out["least_area"] = (key, kept)
        if parts_after[i] < parts_before[i]:
            out["lost"].append((key, int(parts_before[i]), int(parts_after[i]), kept))
    out["seconds"] = time.monotonic() - started
    return out


def rings_level(simple, keys: set, decimals: int) -> dict:
    """each told place's rings at `decimals`, and what the rounding did."""
    out = {"rings": {}, "collapsed": [], "invalid": [], "gone": [], "vertices": 0}
    for key, g in zip(_keys(simple), simple.geometry):
        if key not in keys:
            continue
        rings, did = esri_polygon(g, decimals)
        if did["gone"]:
            out["gone"].append(key)
            continue
        if did["collapsed"]:
            out["collapsed"].append((key, did["collapsed"]))
        if did["invalid"]:
            out["invalid"].append((key, did["invalid"]))
        out["rings"][key] = rings
        out["vertices"] += sum(len(r) for r in rings)
    return out


def polygon_layer_for(level: str, rows: list[dict], rings: dict) -> dict:
    """the level's layer as layer_for builds it, its geometry the place's
    rings instead of its point."""
    fields = fields_for(rows)
    features = [{"geometry": {"rings": rings[(r["authority"], r["code"])]},
                 "attributes": dict(r, **{OID: i})} for i, r in enumerate(rows, start=1)]
    xs = [p[0] for f in features for ring in f["geometry"]["rings"] for p in ring]
    ys = [p[1] for f in features for ring in f["geometry"]["rings"] for p in ring]
    pad = 1000
    extent = {"xmin": min(xs) - pad, "ymin": min(ys) - pad, "xmax": max(xs) + pad,
              "ymax": max(ys) + pad, "spatialReference": dict(WEB_MERCATOR)}
    shown = ("about", "note", "carriers", "cannot_answer")
    return {
        "id": f"rewilding-places-{level}",
        "title": f"{LEVELS[level]} ({PLOT})",
        "layerType": "ArcGISFeatureLayer",
        "visibility": True,
        "opacity": 1,
        "featureCollection": {
            "showLegend": True,
            "layers": [{
                "layerDefinition": {
                    "name": LEVELS[level],
                    "type": "Feature Layer",
                    "geometryType": "esriGeometryPolygon",
                    "objectIdField": OID,
                    "displayField": "name",
                    "fields": fields,
                    "extent": extent,
                    "drawingInfo": {"renderer": {"type": "simple", "symbol": FILL}},
                },
                "featureSet": {"geometryType": "esriGeometryPolygon",
                               "spatialReference": dict(WEB_MERCATOR),
                               "features": features},
                "popupInfo": {
                    "title": "{name}",
                    "popupElements": [{"type": "fields"}],
                    "showAttachments": False,
                    "fieldInfos": [{"fieldName": f["name"], "label": f["name"],
                                    "isEditable": False, "visible": f["name"] in shown}
                                   for f in fields],
                },
            }],
        },
    }


def _named(key, names: dict) -> str:
    return f"{names.get(key) or '?'} ({key[1]})"


def _list(items, names: dict, reasons: bool = False) -> str:
    """the first SHOWN places of items, each (key,) or (key, extra), with the
    extra said when it is a reason, and how many more there are."""
    said = []
    for item in items[:SHOWN]:
        line = _named(item[0], names)
        if reasons and len(item) > 1:
            line += f": {item[1]}"
        said.append(line)
    more = f" and {len(items) - SHOWN} more" if len(items) > SHOWN else ""
    return "; ".join(said) + more


def _map_bytes(points_map: dict, shaped: dict) -> int:
    """the points map with each level in `shaped` swapped for its polygon
    layer, in the points map's own layer order, measured in D-362's form."""
    layers = [shaped.get(l.get("id"), l) for l in points_map.get("operationalLayers") or []]
    return len(canonical(door_form(dict(points_map, operationalLayers=layers))).encode("utf-8"))


def _vs(total: int, points_bytes: int) -> str:
    return (f"{total:,} bytes (points map {points_bytes:,}; the suite's unsourced line "
            f"{LIMIT_LINE:,}: {'under' if total < LIMIT_LINE else 'OVER'})")


def outline_frames(base: str, by_level: dict, say: bool = False) -> dict:
    """{level: (artifact, version, frame, told rows on the outline, names)}
    for every level with a canonical outline, each read by its sha256. with
    say, each outline's own validity is printed, failures with their reasons."""
    frames = {}
    for lv in ORDER:
        artifact = OUTLINES.get(lv)
        if artifact is None:
            if say:
                print(f"  {lv:7} no canonical outline for this level yet: "
                      f"{len(by_level[lv])} told rows not drawn")
            continue
        version, data = read_version(base, artifact)
        frame = display._read_frame(data)
        for col in ("authority", "code"):
            if col not in frame.columns:
                sys.exit(f"STOP: {artifact} carries no '{col}' column")
        keys = set(_keys(frame))
        rows = [r for r in by_level[lv] if (r["authority"], r["code"]) in keys]
        names = {(r["authority"], r["code"]): r.get("name") for r in rows}
        frames[lv] = (artifact, version, frame, rows, names)
        if say:
            bad = invalid_in(frame, set(names))
            print(f"  {lv:7} {artifact} {version[:12]}: canonical outline "
                  + (f"{len(bad)} invalid: {_list(bad, names, reasons=True)}" if bad
                     else "every told place valid"))
    return frames


def polygon_read(base: str, tolerances: tuple, decimals: tuple, shaped_levels: tuple) -> None:
    """the size and validity read: for each tolerance and rounding, every
    level's shapes as the web map would hold them, measured beside the points
    map, and the map with shapes only for `shaped_levels`. sends nothing."""
    profile_version, by_level, _skipped = told_by_level(base)
    points_map, _report = build(base)
    plain = canonical(points_map)
    points_bytes = len(canonical(door_form(points_map)).encode("utf-8"))
    print(f"profile version {profile_version[:12]}")
    print(f"points map: {len(plain.encode('utf-8')):,} bytes as the rehearsal sends it, "
          f"canonical sha256 {sha(plain)[:12]}; {points_bytes:,} in D-362's form")
    order = [l.get("id", "").replace("rewilding-places-", "")
             for l in points_map.get("operationalLayers") or []]
    print(f"layers draw in this order, the last on top: {', '.join(order)}")
    print(f"shaped in the mixed map: {', '.join(shaped_levels)}; every other level a point")

    frames = outline_frames(base, by_level, say=True)

    for tol in tolerances:
        print(f"\n=== {tol} m ===")
        layers = {d: {} for d in decimals}
        refused = []
        for lv, (artifact, version, frame, rows, names) in frames.items():
            sim = simplify_level(frame, tol, set(names))
            if "refused" in sim:
                refused.append(lv)
                print(f"  {lv:7} {sim['seconds']:.1f}s  REFUSED: {sim['refused']}")
                continue
            least = sim["least_area"]
            print(f"  {lv:7} {sim['seconds']:.1f}s"
                  + (f"  least area kept {least[1]:.1%} at {_named(least[0], names)}"
                     if least else "")
                  + (f"  pinches opened in {sim['opened']}" if sim["opened"] else ""))
            if sim["lost"]:
                worst = sorted(sim["lost"], key=lambda t: (t[2] - t[1], t[3]))
                print(f"      {len(sim['lost'])} lost parts: "
                      + "; ".join(f"{_named(k, names)} {b} to {a}, {kept:.1%} kept"
                                  for k, b, a, kept in worst[:SHOWN]))
            print(f"      invalid after simplifying, before rounding: "
                  + (f"{len(sim['invalid'])}: {_list(sim['invalid'], names, reasons=True)}"
                     if sim["invalid"] else "none"))
            for d in decimals:
                res = rings_level(sim["simple"], set(names), d)
                drawn = [r for r in rows if (r["authority"], r["code"]) in res["rings"]]
                layer = polygon_layer_for(lv, drawn, res["rings"])
                layers[d][layer["id"]] = layer
                size = len(canonical(door_form(layer)).encode("utf-8"))
                unit = "1 m" if d == 0 else f"{10 ** -d:g} m"
                print(f"      rounded to {unit}: {size:,} bytes, {res['vertices']:,} vertices, "
                      f"drew {len(drawn)} of {len(by_level[lv])} told")
                if res["invalid"]:
                    print(f"        invalid after rounding: {len(res['invalid'])}: "
                          f"{_list(res['invalid'], names, reasons=True)}")
                if res["gone"]:
                    print(f"        emptied by the rounding: {len(res['gone'])}: "
                          f"{_list([(k,) for k in res['gone']], names)}")
                if res["collapsed"]:
                    n = sum(c for _k, c in res["collapsed"])
                    print(f"        {n} rings collapsed by the rounding in "
                          f"{len(res['collapsed'])} places: {_list(res['collapsed'], names)}")
        missing = f", WITHOUT {', '.join(refused)} (refused)" if refused else ""
        for d in decimals:
            unit = "1 m" if d == 0 else f"{10 ** -d:g} m"
            mixed = {lid: l for lid, l in layers[d].items()
                     if lid.replace("rewilding-places-", "") in shaped_levels}
            print(f"  at {tol} m, rounded to {unit}: every level shaped "
                  f"{_vs(_map_bytes(points_map, layers[d]), points_bytes)}{missing}")
            print(f"  at {tol} m, rounded to {unit}: shaped {', '.join(shaped_levels)} only "
                  f"{_vs(_map_bytes(points_map, mixed), points_bytes)}")
    print("\npolygon read: nothing sent, nothing written")


def _troubled(res: dict) -> list:
    """what the rounding broke in a level: an invalid shape, a place emptied,
    a ring collapsed (a hole or an island lost without a word)."""
    return ([f"invalid {len(res['invalid'])}"] if res["invalid"] else []) + \
           ([f"emptied {len(res['gone'])}"] if res["gone"] else []) + \
           ([f"rings collapsed in {len(res['collapsed'])}"] if res["collapsed"] else [])


def polygon_map(base: str, tolerance: int, decimals: int, shaped_levels: tuple):
    """(web map, what was chosen) to send: the points map with each level in
    shaped_levels drawn as shapes at `tolerance`, in the points map's own
    layer order (the last drawn on top). the rounding rule: a level is rounded
    to `decimals` places of a meter; if any of its places comes back invalid,
    emptied or with a ring collapsed, the WHOLE level is rounded one place
    finer, so neighbours keep one edge; if that fails too, nothing is sent."""
    _profile_version, by_level, _skipped = told_by_level(base)
    points_map, report = build(base)
    frames = outline_frames(base, by_level)
    shaped, chosen = {}, {}
    for lv in shaped_levels:
        artifact, version, frame, rows, names = frames[lv]
        sim = simplify_level(frame, tolerance, set(names))
        if "refused" in sim:
            sys.exit(f"STOP: {lv} at {tolerance} m was refused: {sim['refused']}")
        if sim["invalid"]:
            sys.exit(f"STOP: {lv} at {tolerance} m is invalid before any rounding: "
                     f"{_list(sim['invalid'], names, reasons=True)}")
        tried = []
        for d in (decimals, decimals + 1):
            res = rings_level(sim["simple"], set(names), d)
            trouble = _troubled(res)
            if not trouble:
                break
            tried.append(f"{d} decimals: {', '.join(trouble)}")
        else:
            sys.exit(f"STOP: {lv} cannot be rounded without breaking a shape ({'; '.join(tried)})")
        drawn = [r for r in rows if (r["authority"], r["code"]) in res["rings"]]
        layer = polygon_layer_for(lv, drawn, res["rings"])
        shaped[layer["id"]] = layer
        least = sim["least_area"]
        chosen[lv] = {"outline": f"{artifact} {version[:12]}", "tolerance_m": tolerance,
                      "decimals": d, "finer_because": tried, "drawn": len(drawn),
                      "told": len(by_level[lv]), "vertices": res["vertices"],
                      "least_area_kept": [_named(least[0], names), round(least[1], 4)]
                      if least else None,
                      "pinches_opened": sim["opened"]}
    layers = [shaped.get(l.get("id"), l) for l in points_map.get("operationalLayers") or []]
    webmap = dict(points_map, operationalLayers=layers)
    order = [l.get("id", "").replace("rewilding-places-", "") for l in layers]
    return webmap, {"bbox": report["bbox"], "profile_version": report["profile_version"],
                    "levels": chosen, "layer_order": order}


def send_polygons(base: str, tolerance: int, decimals: int, shaped_levels: tuple,
                  plot_dir: Path) -> None:
    """build the map, say what will be sent, then send it private to the test
    target, record it in POLYGON_SENT (never session 3's record) and read it
    back. the text sent is D-362's form, so the stored map should hash the same."""
    if POLYGON_SENT.is_file():
        prior = json.loads(POLYGON_SENT.read_text())
        sys.exit(f"STOP: {POLYGON_SENT.name} already records item {prior.get('item_id')}; "
                 f"read it back with --polygons --check, or move the record aside first, "
                 f"since a second write would replace the evidence of the first")
    webmap, chosen = polygon_map(base, tolerance, decimals, shaped_levels)
    text = canonical(door_form(webmap))
    print(f"profile version {chosen['profile_version'][:12]}")
    print(f"layers draw in this order, the last on top: {', '.join(chosen['layer_order'])}")
    for lv, c in chosen["levels"].items():
        unit = "1 m" if c["decimals"] == 0 else f"{10 ** -c['decimals']:g} m"
        print(f"  {lv}: shapes at {c['tolerance_m']} m, rounded to {unit}, drew {c['drawn']} "
              f"of {c['told']} told, {c['vertices']:,} vertices, least area kept "
              f"{c['least_area_kept']}"
              + (f"; rounded finer because {'; '.join(c['finer_because'])}"
                 if c["finer_because"] else ""))
    print(f"to send: {len(text.encode('utf-8')):,} bytes, canonical sha256 {sha(text)[:12]}")

    target, kind, session = sign_in(plot_dir)
    portal, token = session["portal"], session["token"]
    folder = portal.folder_id(target.owner, target.folder, token)
    x0, y0, x1, y1 = chosen["bbox"]
    shaped_said = ", ".join(f"{LEVELS[lv]} at {c['tolerance_m']} m"
                            for lv, c in chosen["levels"].items())
    doc = portal.post(
        f"content/users/{target.owner}/{folder}/addItem", token,
        type="Web Map", title=POLYGON_TITLE, tags="rewildingCities,maine,rehearsal",
        snippet=f"Private rehearsal: Maine's places told from profile version "
                f"{chosen['profile_version'][:12]}; {shaped_said} drawn as shapes, "
                f"every other level as points"[:250],
        description=("<p>A private rehearsal for Sprint 09, not the explorer. Every place is "
                     "told from the canonical profile and held inside this web map, one layer "
                     "per level. Some levels are drawn as simplified shapes and the rest as "
                     "points; the last layer is drawn on top. Do not open it in Map Viewer "
                     "and save it.</p>"),
        extent=f"{x0},{y0},{x1},{y1}", text=text)
    item_id = doc["id"]
    sent = {"item_id": item_id, "sha256": sha(text), "counts": counts_of(webmap),
            "profile_version": chosen["profile_version"], "form": "D-362",
            "layer_order": chosen["layer_order"], "levels": chosen["levels"]}
    POLYGON_SENT.write_text(json.dumps(sent, indent=2) + "\n")
    print(f"sent, as {target.owner} into '{target.folder}'; recorded in {POLYGON_SENT}")
    read_back(kind, session, item_id, sent)


def _ints(text: str, what: str, low: int) -> tuple:
    try:
        vals = tuple(int(t) for t in text.split(","))
    except ValueError:
        sys.exit(f"STOP: {what} takes whole numbers, comma separated; got {text!r}")
    if not vals or any(v < low for v in vals):
        sys.exit(f"STOP: every value of {what} is a whole number of at least {low}")
    return vals


# --- saying it ---------------------------------------------------------------

def say_report(report: dict, text: str) -> None:
    print(f"profile version {report['profile_version'][:12]}")
    if report["skipped_levels"]:
        print("levels the explorer does not show: "
              + ", ".join(f"{k} {v}" for k, v in sorted(report["skipped_levels"].items())))
    for lv in ORDER:
        line = report["levels"][lv]
        longest = line["longest"]
        print(f"  {lv:7} told {line['told']:4}  placed {line['placed']:4}  "
              f"outline places with no row {line['outline_places_without_row']}  "
              f"longest {longest['field'] + ' ' + str(longest['chars']) + ' chars' if longest else 'none'}"
              f"  ({line['outline'] or 'no outline'})")
        for why in line["left_out"]:
            print(f"      left out: {why}")
    print(f"web map: {len(text.encode('utf-8')):,} bytes, canonical sha256 {sha(text)[:12]}")


def read_back(kind, session, item_id: str, sent: dict) -> None:
    portal, token = session["portal"], session["token"]
    item = portal.item(item_id, token)
    if item is None:
        print(f"STOP: item {item_id} is not there")
        return
    data = portal.get(f"content/items/{item_id}/data", token)
    stored = canonical(data)
    same = sha(stored) == sent["sha256"]
    print(f"item {item_id}")
    print(f"  sharing: {item.get('access')}"
          + ("" if item.get("access") == "private" else "  <-- NOT PRIVATE: the step before this changed it"))
    print(f"  stored web map: {len(stored.encode('utf-8')):,} bytes, canonical sha256 "
          f"{sha(stored)[:12]}, {'SAME as sent' if same else 'DIFFERS from sent'}")
    got = counts_of(data) if data.get("operationalLayers") else {}
    print(f"  layers: {len(got)} of {len(sent['counts'])}")
    for lid, n in sent["counts"].items():
        print(f"    {lid}: {got.get(lid, 'missing')} of {n} features"
              + ("" if got.get(lid) == n else "  <-- DIFFERS"))
    print(f"  typeKeywords as stored: {', '.join(item.get('typeKeywords') or []) or 'none'}")
    print(f"  extent as stored: {item.get('extent') or 'none'}")


def sign_in(targets_dir: Path):
    kinds = registered(version=VERSION)
    targets = load_targets(targets_dir, kinds)
    target = targets[TARGET]
    if target.sharing != "private":
        sys.exit(f"STOP: the {TARGET} target shares at {target.sharing}; a rehearsal lands private")
    kind = kinds[target.kind]
    try:
        session = kind.sign_in(target, _ask(f"password for {target.owner} at {target.portal}: "))
    except PublishRefusal as e:
        sys.exit(f"STOP: {e.reason}")
    who = kind.whoami(session)
    if who != target.owner:
        sys.exit(f"STOP: the portal says this sign-in is {who}, not {target.owner}")
    return target, kind, session


def main() -> None:
    ap = argparse.ArgumentParser(description="Sprint 09 rehearsal: the places as one web map")
    ap.add_argument("--write", action="store_true", help="send it, private, and read it back")
    ap.add_argument("--check", action="store_true", help="read the sent item back again")
    ap.add_argument("--polygons", action="store_true",
                    help="the polygon size read: sends nothing, writes nothing")
    ap.add_argument("--tolerances", default=",".join(str(t) for t in DEFAULT_TOLERANCES),
                    help="meters, comma separated, for --polygons (default 100,250,500)")
    ap.add_argument("--decimals", default=",".join(str(d) for d in DEFAULT_DECIMALS),
                    help="decimal places of a meter for the rings, comma separated (default 0)")
    ap.add_argument("--polygon-levels", default=",".join(DEFAULT_SHAPED),
                    help="levels shaped in the mixed map, comma separated (default cousub)")
    args = ap.parse_args()
    plot_dir = ROOT / "plots" / PLOT

    if args.polygons:
        if args.write and args.check:
            sys.exit("STOP: --write sends and --check reads back; give one")
        if args.check:
            if not POLYGON_SENT.is_file():
                sys.exit(f"STOP: {POLYGON_SENT} does not exist, so no shapes map has been sent")
            sent = json.loads(POLYGON_SENT.read_text())
            _target, kind, session = sign_in(plot_dir)
            read_back(kind, session, sent["item_id"], sent)
            return
        tolerances = _ints(args.tolerances, "--tolerances", 1)
        decimals = _ints(args.decimals, "--decimals", 0)
        shaped = tuple(v.strip() for v in args.polygon_levels.split(",") if v.strip())
        unknown = [v for v in shaped if v not in OUTLINES]
        if not shaped or unknown:
            sys.exit(f"STOP: --polygon-levels names levels with an outline "
                     f"({', '.join(OUTLINES)}); got {args.polygon_levels!r}")
        if args.write and (len(tolerances) != 1 or len(decimals) != 1):
            sys.exit("STOP: --polygons --write sends one map: give exactly one "
                     "--tolerances and one --decimals")
        domain = os.environ.get(DOMAIN_ENV)
        if not domain:
            sys.exit(f"STOP: {DOMAIN_ENV} is not set; activate the rewilding env")
        if args.write:
            send_polygons(f"https://{domain}", tolerances[0], decimals[0], shaped, plot_dir)
            return
        polygon_read(f"https://{domain}", tolerances, decimals, shaped)
        return

    if args.check:
        if not SENT.is_file():
            sys.exit(f"STOP: {SENT} does not exist, so nothing has been sent yet")
        sent = json.loads(SENT.read_text())
        _target, kind, session = sign_in(plot_dir)
        read_back(kind, session, sent["item_id"], sent)
        return

    domain = os.environ.get(DOMAIN_ENV)
    if not domain:
        sys.exit(f"STOP: {DOMAIN_ENV} is not set; activate the rewilding env")
    webmap, report = build(f"https://{domain}")
    text = canonical(webmap)
    say_report(report, text)
    if not args.write:
        print("dry run: nothing sent. add --write to send it, private, to the test folder")
        return

    target, kind, session = sign_in(plot_dir)
    portal, token = session["portal"], session["token"]
    folder = portal.folder_id(target.owner, target.folder, token)
    x0, y0, x1, y1 = report["bbox"]
    doc = portal.post(
        f"content/users/{target.owner}/{folder}/addItem", token,
        type="Web Map", title=TITLE, tags="rewildingCities,maine,rehearsal",
        snippet=f"Private rehearsal: Maine's places told from profile version "
                f"{report['profile_version'][:12]}, one layer per level, inside this web map",
        description=("<p>A private rehearsal for Sprint 09, not the explorer. Every place is "
                     "told from the canonical profile and held inside this web map, one layer "
                     "per level. Do not open it in Map Viewer and save it.</p>"),
        extent=f"{x0},{y0},{x1},{y1}", text=text)
    item_id = doc["id"]
    sent = {"item_id": item_id, "sha256": sha(text), "counts": counts_of(webmap),
            "profile_version": report["profile_version"]}
    SENT.write_text(json.dumps(sent, indent=2) + "\n")
    print(f"sent, as {target.owner} into '{target.folder}'; recorded in {SENT}")
    read_back(kind, session, item_id, sent)


if __name__ == "__main__":
    main()
