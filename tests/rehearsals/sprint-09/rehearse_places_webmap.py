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

run it from the rewildingCities repo root. ~
"""

from __future__ import annotations

import argparse
import copy as _copy
import hashlib
import json
import os
import sys
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


def canonical(doc) -> str:
    """keys sorted, no spaces: the text two equal documents always share."""
    return json.dumps(doc, sort_keys=True, separators=(",", ":"))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --- reading the canonical store ---------------------------------------------

def read_version(base: str, artifact: str) -> tuple[str, bytes]:
    """a harvest's current version, its bytes checked against its sha256."""
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


def build(base: str) -> tuple[dict, dict]:
    """(web map, report). told from the profile's current version, placed on
    each level's current outline; nothing invented, every row left out named."""
    profile_version, raw = read_version(base, PROFILE)
    rows, ctx = tell_all(json.loads(raw), ROOT)
    level_of = {label: lv for lv, label in LEVELS.items()}
    by_level: dict = {lv: [] for lv in ORDER}
    for r in rows:
        by_level[level_of[r["level"]]].append(r)

    report = {"profile_version": profile_version, "skipped_levels": dict(ctx.skipped),
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
    args = ap.parse_args()
    plot_dir = ROOT / "plots" / PLOT

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
