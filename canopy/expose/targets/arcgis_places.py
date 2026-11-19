"""
canopy/expose/targets/arcgis_places.py ~ the explorer's places map (Sprint 09, zip 9b1)

one web map holds every place the explorer shows, one layer per level, each
place's told fields inside the map's own JSON as a feature collection (D-361):
the places are copied into the item (file storage, no hosted feature layer),
from canonical copies the bucket holds. nothing here reads the profile: the
words come from the told copy (D-370), the geometry from display copies.

  points   every level but the towns, from each outline's `markers` copy, one
           point on the place's own surface (D-367, D-377), in Web Mercator to
           the cm
  shapes   the towns, from the towns' web_250m copy (D-369), each ring in Web
           Mercator rounded to 1 m and wound Esri's way: outer rings clockwise,
           holes counterclockwise, the opposite of GeoJSON's RFC 7946

never an invalid shape (D-368): a shaped level is rounded to 1 m; if any place
comes back invalid, emptied or with a ring collapsed, the whole level is rounded
to 0.1 m, so neighbours keep one edge; if that fails too, nothing is built and
the places are named. tribal points are drawn last, on top (STACK-1).

the map is written in D-362's form, every whole float an integer, as ArcGIS
stores it, so the hash of what is sent is the hash of what is stored, and the
door records and checks that one hash (D-372). the door owns the whole map: a
move rewrites it, and any other change to it is a change by hand (D-380). ~
"""

from __future__ import annotations

import copy as _copy
import hashlib
import html
import json

from .arcgis_webmap import (BASEMAP, MADE_PLACES, SPEC_VERSION, WEB_MERCATOR, _esri_type, _li,
                            _mark, _mercator, extent_of)
from .base import Built, PublishRefusal

OID = "OBJECTID"
ORDER = ("state", "county", "sldu", "sldl", "cousub", "aiannh")   # the last drawn on top
SHAPED = ("cousub",)
OUTLINES = {"state": "outline_state_outline", "county": "outline_counties_outline",
            "sldu": "outline_senate_outline", "sldl": "outline_house_outline",
            "cousub": "outline_towns_outline", "aiannh": "outline_tribal_outline"}
TOWNS_COPY = "web_250m"
POINTS_COPY = "markers"
SHOWN = ("about", "note", "carriers", "cannot_answer", "withheld")
POINT_DECIMALS = 2
FILL = {"type": "esriSFS", "style": "esriSFSSolid", "color": [37, 52, 148, 40],
        "outline": {"type": "esriSLS", "style": "esriSLSSolid",
                    "color": [37, 52, 148, 255], "width": 0.75}}
LEVEL_LABELS = {"state": "State", "county": "County", "cousub": "Town or city",
                "sldl": "Maine House district", "sldu": "Maine Senate district",
                "aiannh": "Census tribal area"}


def canonical(doc) -> str:
    """keys sorted, no spaces: the text two equal documents always share."""
    return json.dumps(doc, sort_keys=True, separators=(",", ":"))


def door_form(doc):
    """D-362's form: every whole float written as an integer, as ArcGIS stores it."""
    if isinstance(doc, dict):
        return {k: door_form(v) for k, v in doc.items()}
    if isinstance(doc, list):
        return [door_form(v) for v in doc]
    if isinstance(doc, float) and doc.is_integer():
        return int(doc)
    return doc


def map_sha256(doc: dict) -> str:
    """the one hash the door sends, records and checks for a places map (D-372)."""
    return hashlib.sha256(canonical(door_form(doc)).encode("utf-8")).hexdigest()


# ── rings, as Esri holds them ────────────────────────────────────────────
def _signed_area(ring) -> float:
    """twice the shoelace area of a closed ring: above zero counterclockwise."""
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:]))


def _rounder(decimals: int):
    if decimals == 0:
        return lambda v: int(round(v))
    return lambda v: round(v, decimals)


def esri_ring(coords, outer: bool, decimals: int = 0) -> list | None:
    """one ring in Web Mercator by the door's _mercator, rounded to `decimals`
    places of a meter, a vertex the rounding repeats dropped, closed, wound
    clockwise when outer and counterclockwise when a hole. None when the
    rounding collapses it: fewer than three corners, or no area left."""
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
    if (area > 0) == outer:          # outer wants below zero (clockwise), a hole above
        out.reverse()
    return out


def _invalid_reason(polygons: list) -> str | None:
    """shapely's reason the rebuilt shape is invalid, or None when it is valid.
    polygons is [(shell, [holes])], every ring as written."""
    import shapely
    polys = [shapely.Polygon(shell, holes) for shell, holes in polygons]
    whole = polys[0] if len(polys) == 1 else shapely.MultiPolygon(polys)
    return None if whole.is_valid else str(shapely.is_valid_reason(whole))


def esri_polygon(geometry: dict, decimals: int = 0) -> tuple[list, dict]:
    """(rings, what the rounding did) for one GeoJSON Polygon or MultiPolygon."""
    kind = geometry.get("type")
    if kind == "Polygon":
        parts = [geometry["coordinates"]]
    elif kind == "MultiPolygon":
        parts = geometry["coordinates"]
    else:
        raise PublishRefusal(f"a town's shape is a {kind}, not a polygon",
                             "draw the towns' copy again from the outline")
    rings, polygons, collapsed = [], [], 0
    for part in parts:
        shell = esri_ring(part[0], True, decimals)
        if shell is None:
            collapsed += len(part)
            continue
        holes = []
        for ring in part[1:]:
            h = esri_ring(ring, False, decimals)
            if h is None:
                collapsed += 1
            else:
                holes.append(h)
        polygons.append((shell, holes))
        rings += [shell] + holes
    if not polygons:
        return rings, {"collapsed": collapsed, "invalid": None, "gone": True}
    return rings, {"collapsed": collapsed, "invalid": _invalid_reason(polygons), "gone": False}


def rings_level(features: dict, decimals: int) -> dict:
    """{key: rings} for every place, and what the rounding broke."""
    out = {"rings": {}, "invalid": [], "gone": [], "collapsed": []}
    for key, geometry in features.items():
        rings, did = esri_polygon(geometry, decimals)
        if did["gone"]:
            out["gone"].append(key)
            continue
        if did["collapsed"]:
            out["collapsed"].append(key)
        if did["invalid"]:
            out["invalid"].append((key, did["invalid"]))
        out["rings"][key] = rings
    return out


def _trouble(res: dict) -> list[str]:
    return ([f"{len(res['invalid'])} invalid ({res['invalid'][0][0][1]}: "
             f"{res['invalid'][0][1]})"] if res["invalid"] else []) + \
           ([f"{len(res['gone'])} emptied"] if res["gone"] else []) + \
           ([f"{len(res['collapsed'])} with a ring collapsed"] if res["collapsed"] else [])


def shaped_level(level: str, features: dict) -> tuple[dict, int, list]:
    """(rings by key, decimals used, why it went finer) under D-368's rule."""
    tried = []
    for d in (0, 1):
        res = rings_level(features, d)
        trouble = _trouble(res)
        if not trouble:
            return res["rings"], d, tried
        tried.append(f"at {'1 m' if d == 0 else '0.1 m'}: {', '.join(trouble)}")
    raise PublishRefusal(f"the {LEVEL_LABELS.get(level, level)} shapes cannot be rounded "
                         f"without breaking one ({'; '.join(tried)}), so none is sent (D-368)",
                         "read the copy's own `rounded` record (ROUND-2), then draw the "
                         "copy at another tolerance")


# ── layers ───────────────────────────────────────────────────────────────
def fields_for(rows: list[dict]) -> list[dict]:
    """the told fields, typed from their own values as the door types them."""
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


def _extent(xs, ys) -> dict:
    pad = 1000
    return {"xmin": min(xs) - pad, "ymin": min(ys) - pad, "xmax": max(xs) + pad,
            "ymax": max(ys) + pad, "spatialReference": dict(WEB_MERCATOR)}


def layer_for(level: str, plot: str, rows: list[dict], geometry: dict, shaped: bool) -> dict:
    """one level as a feature collection layer inside the web map."""
    fields = fields_for(rows)
    features = [{"geometry": geometry[(r["authority"], r["code"])],
                 "attributes": dict(r, **{OID: i})} for i, r in enumerate(rows, start=1)]
    if shaped:
        xs = [p[0] for f in features for ring in f["geometry"]["rings"] for p in ring]
        ys = [p[1] for f in features for ring in f["geometry"]["rings"] for p in ring]
    else:
        xs = [f["geometry"]["x"] for f in features]
        ys = [f["geometry"]["y"] for f in features]
    gtype = "esriGeometryPolygon" if shaped else "esriGeometryPoint"
    symbol = FILL if shaped else _mark(6)
    label = LEVEL_LABELS.get(level, level)
    return {
        "id": f"rewilding-places-{level}",
        "title": f"{label} ({plot})",
        "layerType": "ArcGISFeatureLayer",
        "visibility": True,
        "opacity": 1,
        "featureCollection": {
            "showLegend": True,
            "layers": [{
                "layerDefinition": {
                    "name": label, "type": "Feature Layer", "geometryType": gtype,
                    "objectIdField": OID, "displayField": "name", "fields": fields,
                    "extent": _extent(xs, ys),
                    "drawingInfo": {"renderer": {"type": "simple", "symbol": symbol}},
                },
                "featureSet": {"geometryType": gtype, "spatialReference": dict(WEB_MERCATOR),
                               "features": features},
                "popupInfo": {
                    "title": "{name}",
                    "popupElements": [{"type": "fields"}],
                    "showAttachments": False,
                    "fieldInfos": [{"fieldName": f["name"], "label": f["name"],
                                    "isEditable": False, "visible": f["name"] in SHOWN}
                                   for f in fields],
                },
            }],
        },
    }


def _key(props: dict) -> tuple[str, str]:
    return (str(props.get("authority")), str(props.get("code")))


def points_of(geojson: dict) -> dict:
    """{(authority, code): {x, y}} from a markers copy, in Web Mercator to the cm."""
    rnd = _rounder(POINT_DECIMALS)
    out = {}
    for f in geojson.get("features") or []:
        g = f.get("geometry") or {}
        if g.get("type") != "Point":
            raise PublishRefusal("a markers copy holds a geometry that is not a point",
                                 "draw it again with canonical --display --markers")
        x, y = _mercator(*g["coordinates"][:2])
        out[_key(f.get("properties") or {})] = {"x": rnd(x), "y": rnd(y)}
    return out


def shapes_of(geojson: dict) -> dict:
    return {_key(f.get("properties") or {}): f.get("geometry") or {}
            for f in geojson.get("features") or []}


def places_webmap(places: dict, version: str) -> tuple[dict, dict]:
    """(web map in D-362's form, report): every told row placed on its level's
    geometry by (authority, code), every row left out named, never invented."""
    by_level: dict = {lv: [] for lv in ORDER}
    label_of = {v: k for k, v in LEVEL_LABELS.items()}
    for r in places["told"]["rows"]:
        lv = label_of.get(r.get("level"))
        if lv is None:
            raise PublishRefusal(f"a told row has level '{r.get('level')}', which the places "
                                 f"map does not draw", "tell the profile again")
        by_level[lv].append(r)
    report = {"levels": {}, "left_out": []}
    layers, lonlat = [], []
    for lv in ORDER:
        rows = by_level[lv]
        parent = places["levels"].get(lv)
        if parent is None:
            raise PublishRefusal(f"no geometry was read for the {LEVEL_LABELS[lv]} level",
                                 "read every level's copy before building")
        shaped = lv in SHAPED
        line = {"told": len(rows), "copy": parent["copy"], "shaped": shaped}
        if shaped:
            feats = shapes_of(parent["geojson"])
            wanted = {k: g for k, g in feats.items()
                      if k in {(r["authority"], r["code"]) for r in rows}}
            rings, decimals, finer = shaped_level(lv, wanted)
            geometry = {k: {"rings": v} for k, v in rings.items()}
            line.update({"decimals": decimals, "finer_because": finer})
        else:
            geometry = points_of(parent["geojson"])
            line["decimals"] = POINT_DECIMALS
        placed = [r for r in rows if (r["authority"], r["code"]) in geometry]
        left = [r for r in rows if (r["authority"], r["code"]) not in geometry]
        line["placed"] = len(placed)
        report["levels"][lv] = line
        report["left_out"] += [f"{r.get('name')} ({r['code']}, {LEVEL_LABELS[lv]})" for r in left]
        if any(r.get("withheld") for r in left):
            raise PublishRefusal("the state's row, which tells what the tool keeps in, has no "
                                 "place on the state's markers copy (D-376)",
                                 "draw the state outline's markers copy, then publish")
        if placed:
            layers.append(layer_for(lv, places["plot"], placed, geometry, shaped))
            for f in parent["geojson"].get("features") or []:
                if _key(f.get("properties") or {}) in {(r["authority"], r["code"]) for r in placed}:
                    lonlat.append(_corner(f.get("geometry") or {}))
    xs = [p[0] for pair in lonlat for p in pair]
    ys = [p[1] for pair in lonlat for p in pair]
    webmap = {
        "operationalLayers": layers,
        "baseMap": _copy.deepcopy(BASEMAP),
        "spatialReference": dict(WEB_MERCATOR),
        "authoringApp": "rewildingCities",
        "authoringAppVersion": version,
        "version": SPEC_VERSION,
        "initialState": {"viewpoint": {"targetGeometry": extent_of(
            [min(xs), min(ys), max(xs), max(ys)])}},
    }
    return door_form(webmap), report


def _corner(geometry: dict) -> tuple:
    """the (lon, lat) corners of a geometry's box, for the map's extent."""
    flat = []

    def walk(c):
        if c and isinstance(c[0], (int, float)):
            flat.append(c)
        else:
            for x in c:
                walk(x)
    walk(geometry.get("coordinates") or [])
    lons, lats = [c[0] for c in flat], [c[1] for c in flat]
    return ((min(lons), min(lats)), (max(lons), max(lats)))


# ── the item's words ─────────────────────────────────────────────────────
def description_of(places: dict, report: dict, sha: str, version: str) -> tuple[str, str, str]:
    """(description, license_info, access_information) from the bucket's records
    alone, with no time in them: the same records always write the same words."""
    e = html.escape
    licenses = places.get("licenses") or {}
    notes, terms, credits, steps, seen = {}, [], [], [], set()
    for p in places["parents"]:
        gate = p["allow_doc"].get("gate") or {}
        notes.update(gate.get("context_text") or {})
        for row in gate.get("license") or []:
            if (row.get("dataset"), row.get("term")) in seen:
                continue
            seen.add((row.get("dataset"), row.get("term")))
            term = licenses.get(row.get("term")) or {}
            label = term.get("name") or row.get("term")
            terms.append(f"{e(str(row.get('dataset')))}: {e(str(label))} ({e(str(row.get('term')))})")
            if term.get("attribution") == "required":
                credits.append(str(label))
        own = (p["env"].get("provenance") or [{}])[-1]
        steps += [f"{e(p['role'])}, {e(str(s.get('step')))}: {e(str(s.get('detail')))}"
                  for s in own.get("publication") or []]
    for lv, line in report["levels"].items():
        if line["shaped"]:
            unit = "1 m" if line["decimals"] == 0 else "0.1 m"
            steps.append(f"{e(LEVEL_LABELS[lv])}: each ring put in Web Mercator by the door, "
                         f"rounded to {unit} and wound clockwise (holes counterclockwise)"
                         + (f"; rounded finer because {e('; '.join(line['finer_because']))}"
                            if line["finer_because"] else "") + " (D-368)")
        else:
            steps.append(f"{e(LEVEL_LABELS[lv])}: each point put in Web Mercator by the door, "
                         f"rounded to 1 cm")
    told = places["told"]
    counts = [f"{e(LEVEL_LABELS[lv])}: {line['placed']} of {line['told']} told places drawn, "
              f"as {'shapes' if line['shaped'] else 'points'}"
              for lv, line in report["levels"].items()]
    parts = [
        f"<p><b>Places in the {e(places['plot'])} plot</b>, one layer per level, the "
        f"explorer's map. Every place's words are told from canonical version "
        f"<code>{told['profile_sha256']}</code> of the place profile; the map's own hash is "
        f"<code>{sha}</code>.</p>",
        "<p><b>The places are held inside this map.</b> They are copied from the canonical "
        "store, so this item's sharing decides who can read them. The door writes the whole "
        "map; change it in Experience Builder, never by saving it in Map Viewer.</p>",
        _li(counts),
        "<h3>Left out, and why</h3>",
        _li([e(x) + ": no place in its level's copy" for x in report["left_out"]]),
        "<h3>Context notes</h3>",
        _li([f"<b>{e(k)}</b>: {e(str(v))}" for k, v in sorted(notes.items())]),
        "<h3>Where the data is stored</h3>",
        _li([f"{e(p['role'])}: <code>{e(p['url'])}</code> (version <code>{p['sha256']}</code>, "
             f"allow record <code>{p['allow']}</code>)" for p in places["parents"]]
            + [f"refusal record: <code>{e(told['refusals_url'])}</code>"]),
        "<h3>License</h3>", _li(terms),
        "<h3>What changed on the way out</h3>", _li(steps),
        *_credit(places),
        f"<p>Made by the rewildingCities publish door {e(version)}. The door rewrites this "
        f"description and this map, which carry the notes and the places.</p>",
    ]
    license_info = "; ".join(sorted({str((licenses.get(r.get("term")) or {}).get("name")
                                          or r.get("term"))
                                     for p in places["parents"]
                                     for r in (p["allow_doc"].get("gate") or {}).get("license")
                                     or []}))
    access = "; ".join(sorted(set(credits))) + ("; " if credits else "") + \
        "rewildingCities canonical store"
    return "\n".join(parts), license_info, access


def _credit(places: dict) -> list[str]:
    c = places.get("credit")
    if not c:
        return []
    e = html.escape
    citation = str(c["citation"]).format(title=places["title"],
                                         version=places["told"]["profile_sha256"][:12],
                                         url=places["told"]["version_url"] + "/")
    return ["<h3>Credit and citation</h3>",
            _li([e(str(c["credit"])), f"Suggested citation: {e(citation)}",
                 e(str(c["data_guide"]))])]


def build_places(places: dict, version: str) -> Built:
    """the item for the places the door read: its map, its words, its hash."""
    data, report = places_webmap(places, version)
    sha = map_sha256(data)
    description, license_info, access = description_of(places, report, sha, version)
    snippet = (f"Every place in the {places['plot']} plot, told from canonical profile "
               f"{places['told']['profile_sha256'][:12]}, held inside this map")[:250]
    return Built(title=places["title"][:256], snippet=snippet, description=description,
                 tags=["rewildingCities", places["plot"], "places", "explorer"],
                 license_info=license_info, access_information=access, data=data,
                 layer_id="places", url="",
                 extra={"made": MADE_PLACES, "map_sha256": sha, "report": report,
                        "owns_title": True})
