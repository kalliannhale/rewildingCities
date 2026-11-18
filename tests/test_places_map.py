"""
tests/test_places_map.py ~ the explorer's places map (zip 9b1, D-361 to D-372)

sessions 3 and 4's rehearsals, held in the suite: every place told from the
told copy and placed on its level's display copy by (authority, code), the
towns as shapes wound Esri's way and every other level as points, tribal
points drawn last; the rounding rule refuses what it should (D-368); the map is
sent in D-362's form, so a portal that stores a whole float as an integer
stores the same map, and the door records and checks that one hash (D-372).
the places map is its own entry kind under the key `places`, owed a move when
a parent moves, and every entry names its kind (D-371).

the bucket, the portal and the gate are the door's fakes (test_publish_door.py),
loaded by path so its tests are not collected twice. ~
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from canopy.aws import display, s3, told
from canopy.expose import publish as door
from canopy.expose.targets import PublishRefusal, registered
from canopy.expose.targets import arcgis_places as ap

_spec = importlib.util.spec_from_file_location(
    "_door_fakes", Path(__file__).with_name("test_publish_door.py"))
fakes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fakes)

DOMAIN, PLOT = fakes.DOMAIN, "demo"
BASE = f"https://{DOMAIN}"
PROFILE_SHA, PROFILE_ALLOW = "p" * 64, "9" * 64
NOTE = {"census_tribal_area": "the boundary is the Census Bureau's"}


class StoringPortal(fakes.FakePortal):
    """the fake portal, storing a whole float as an integer, as ArcGIS does
    (5615270.0 comes back 5615270, D-362)."""

    def post(self, url, data=None, headers=None, timeout=None):
        if data and "text" in data:
            data = dict(data, text=json.dumps(ap.door_form(json.loads(data["text"]))))
        return super().post(url, data=data, headers=headers, timeout=timeout)


# ── the places, in lon/lat near Maine ────────────────────────────────────
def _square(x, y, d=0.01):
    """a closed square, wound counterclockwise as RFC 7946 writes an outer ring."""
    return [[x, y], [x + d, y], [x + d, y + d], [x, y + d], [x, y]]


TOWNS = {"2300100001": _square(-70.00, 44.00), "2300100002": _square(-69.99, 44.00)}
POINTS = {"state": {"23": (-69.2, 45.3)}, "county": {"23001": (-70.2, 44.1)},
          "sldu": {"2300001": (-70.1, 44.2)}, "sldl": {"2300101": (-70.05, 44.05)},
          "aiannh": {"2595": (-68.7, 44.95)}}
LEVEL = {"state": "State", "county": "County", "sldu": "Maine Senate district",
         "sldl": "Maine House district", "cousub": "Town or city",
         "aiannh": "Census tribal area"}


def row(level, code, name, **extra):
    r = {"key": f"us_census_geoid:{code}", "authority": "us_census_geoid", "code": code,
         "name": name, "level": LEVEL[level], "about": f"{name} is in Maine.",
         "note": "No context note.", "carriers": "1 public library.",
         "cannot_answer": "Nothing is missing for this place.",
         "profile_version": "0.4.0", "built_at": "2026-11-18T00:00:00+00:00"}
    r.update(extra)
    return r


def rows():
    return [row("state", "23", "Maine", withheld="This tool holds 1 kind of data that this "
                                                 "map does not show."),
            row("county", "23001", "Androscoggin County"),
            row("sldu", "2300001", "Senate District 1"),
            row("sldl", "2300101", "House District 1"),
            row("cousub", "2300100001", "Auburn city"),
            row("cousub", "2300100002", "Lewiston city"),
            row("cousub", "2300357936", "Penobscot Indian Island Reservation"),
            row("aiannh", "2595", "Penobscot Reservation")]


def _fc(features):
    return {"type": "FeatureCollection", "features": features}


def _feature(code, geometry):
    return {"type": "Feature", "geometry": geometry,
            "properties": {"authority": "us_census_geoid", "code": code, "name": code}}


def garden(tmp_path, sharing="private"):
    root = fakes.garden(tmp_path, {"test": {
        "kind": "arcgis", "portal": fakes.PORTAL, "owner": "RDS_NU",
        "owner_kind": "institutional", "folder": "rc test", "sharing": sharing, "groups": []}})
    for rel in told.TOLD_INPUTS:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(f"# {rel}\n")
    return root


def bucket(root, *, profile=PROFILE_SHA, record=None, the_rows=None, towns=None,
           omit=None, versions=None):
    """the bucket by URL: the profile and its told copy, the refusal record,
    and each outline's current version with its display copy."""
    pages = {}
    record = record or {"plot": PLOT, "withheld": [{"semantic_type": "news_outlet_points",
                                                    "refusals": [{"rule": 5}]}]}
    rbody = told.document_bytes(record)
    rsha = told._sha(rbody)
    pages[f"{BASE}/{s3.pointer_key(PLOT, told.REFUSALS)}"] = json.dumps({"sha256": rsha})
    pages[f"{BASE}/{told.refusals_keys(PLOT, rsha)['data']}"] = rbody.decode()
    v = f"{BASE}/{s3.version_prefix(PLOT, told.PROFILE, profile)}"
    pages[f"{BASE}/{s3.pointer_key(PLOT, told.PROFILE)}"] = json.dumps(
        {"sha256": profile, "allow": PROFILE_ALLOW, "data": "data.json"})
    pages[f"{v}/allow/{PROFILE_ALLOW}.json"] = json.dumps({"gate": {
        "context_text": NOTE, "license": [{"dataset": "acs", "term": "geo"}]}})
    pages[f"{v}/envelope.json"] = json.dumps({"metadata": {"semantic_type": "place_profile"}})
    name = told.told_name(told.told_inputs(root), rsha)
    keys = told.told_keys(PLOT, profile, name)
    pages[f"{BASE}/{keys['json']}"] = told.document_bytes(
        {"profile_version": profile, "refusals_version": rsha,
         "rows": the_rows if the_rows is not None else rows()}).decode()
    pages[f"{BASE}/{keys['envelope']}"] = json.dumps({
        "metadata": {"semantic_type": "place_profile", "derived_from": profile},
        "provenance": [{"primitive": "tell_places",
                        "publication": [{"step": "told", "detail": "8 places told"}]}],
        "warnings": []})
    for lv, harvest in ap.OUTLINES.items():
        if omit == lv:
            continue
        sha = (versions or {}).get(lv, (lv[0] * 64)[:64])
        allow = "a" * 64
        ov = f"{BASE}/{s3.version_prefix(PLOT, harvest, sha)}"
        pages[f"{BASE}/{s3.pointer_key(PLOT, harvest)}"] = json.dumps(
            {"sha256": sha, "allow": allow, "data": "data.parquet"})
        pages[f"{ov}/allow/{allow}.json"] = json.dumps({"gate": {
            "context_text": NOTE, "license": [{"dataset": "faces", "term": "geo"}]}})
        pages[f"{ov}/envelope.json"] = json.dumps({"metadata": {"data_category": "vector"}})
        if lv in ap.SHAPED:
            shapes = towns or TOWNS
            fc = _fc([_feature(c, {"type": "Polygon", "coordinates": [ring]})
                      for c, ring in shapes.items()])
            copy = ap.TOWNS_COPY
        else:
            fc = _fc([_feature(c, {"type": "Point", "coordinates": list(xy)})
                      for c, xy in POINTS[lv].items()])
            copy = ap.POINTS_COPY
        dk = s3.display_keys(PLOT, harvest, sha, copy)
        pages[f"{BASE}/{dk['envelope']}"] = json.dumps({
            "metadata": {"derived_from": sha},
            "provenance": [{"primitive": "make_display_copy",
                            "publication": [{"step": "rounded", "detail": "6 places"}]}],
            "warnings": []})
        pages[f"{BASE}/{dk['geojson']}"] = json.dumps(fc)
    return pages


def judge(envelope, *, plot, target, sharing_level, plot_dir):
    return {"decision": "allow", "record": {"sharing_level": sharing_level,
                                            "gate_version": "test", "context_text": NOTE,
                                            "license": []}}


@pytest.fixture(autouse=True)
def valid_shapes(monkeypatch):
    """the door's validity read is shapely's; where shapely is absent, these
    tests hold everything else and the rounding tests below are skipped."""
    try:
        import shapely  # noqa: F401
    except ImportError:
        monkeypatch.setattr(ap, "_invalid_reason", lambda polygons: None)


def run(root, pages, portal, *, write=True, **kw):
    return door.publish_places(PLOT, ["test"], root=root, write=write,
                               by="tester" if write else None,
                               reason="a test" if write else None, domain=DOMAIN,
                               fetch=fakes.fetcher(pages), judge=judge,
                               kinds=registered(http=portal), ask=lambda p: "test-password",
                               now="2026-11-18T00:00:00+00:00", **kw)


def stored(portal):
    [item] = portal.items.values()
    return item, json.loads(item["text"])


# ── building it ──────────────────────────────────────────────────────────
def test_a_dry_run_signs_in_nowhere_and_says_what_it_would_build(tmp_path):
    root, portal = garden(tmp_path), StoringPortal()
    [o] = run(root, bucket(root), portal, write=False)
    assert o.outcome == "would publish" and portal.calls == []
    said = "\n".join(o.lines)
    assert "cousub: 2 of 3 told, as shapes rounded to 1 m" in said
    assert "left out: Penobscot Indian Island Reservation (2300357936, Town or city)" in said


def test_every_level_is_a_layer_and_tribal_points_are_drawn_last(tmp_path):
    root, portal = garden(tmp_path), StoringPortal()
    [o] = run(root, bucket(root), portal)
    assert o.outcome == "published"
    _, data = stored(portal)
    ids = [l["id"].replace("rewilding-places-", "") for l in data["operationalLayers"]]
    assert ids == list(ap.ORDER) and ids[-1] == "aiannh"
    kinds = {l["id"]: l["featureCollection"]["layers"][0]["layerDefinition"]["geometryType"]
             for l in data["operationalLayers"]}
    assert kinds["rewilding-places-cousub"] == "esriGeometryPolygon"
    assert {k for k, v in kinds.items() if v == "esriGeometryPoint"} == {
        f"rewilding-places-{lv}" for lv in ap.ORDER if lv != "cousub"}


def test_only_the_states_row_carries_the_withheld_field(tmp_path):
    root, portal = garden(tmp_path), StoringPortal()
    run(root, bucket(root), portal)
    _, data = stored(portal)
    carrying = [l["id"] for l in data["operationalLayers"]
                if any(f["name"] == "withheld"
                       for f in l["featureCollection"]["layers"][0]["layerDefinition"]["fields"])]
    assert carrying == ["rewilding-places-state"]


def test_a_withheld_field_with_no_place_is_refused(tmp_path):
    root = garden(tmp_path)
    pages = bucket(root)
    harvest = ap.OUTLINES["state"]
    dk = s3.display_keys(PLOT, harvest, "s" * 64, ap.POINTS_COPY)
    pages[f"{BASE}/{dk['geojson']}"] = json.dumps(_fc([]))
    [o] = run(root, pages, StoringPortal(), write=False)
    assert o.outcome == "refused" and "D-376" in "\n".join(o.lines)


def test_the_stored_map_hashes_the_same_as_the_sent_one(tmp_path):
    root, portal = garden(tmp_path), StoringPortal()
    [o] = run(root, bucket(root), portal)
    assert "SAME as sent" in "\n".join(o.lines)
    _, data = stored(portal)
    entry = door.read_record(root / "plots" / PLOT)["targets"]["test"][door.PLACES_KEY]
    assert ap.map_sha256(data) == entry["map_sha256"]
    assert entry["kind"] == "arcgis_places_map" and entry["refusals_sha256"]


def test_no_whole_float_is_sent():
    def floats(x):
        if isinstance(x, dict):
            return any(floats(v) for v in x.values())
        if isinstance(x, list):
            return any(floats(v) for v in x)
        return isinstance(x, float) and x.is_integer()
    assert ap.door_form({"a": [5615270.0, 1.5]}) == {"a": [5615270, 1.5]}
    assert not floats(ap.door_form({"x": [1.0, {"y": 2.0}]}))


def test_rings_are_wound_esris_way():
    outer = ap.esri_ring(_square(-70, 44), outer=True)
    hole = ap.esri_ring(_square(-69.995, 44.005, 0.002), outer=False)
    assert ap._signed_area(outer) < 0 < ap._signed_area(hole)
    assert outer[0] == outer[-1] and all(isinstance(v, int) for p in outer for v in p)


def test_a_ring_the_rounding_collapses_is_said():
    assert ap.esri_ring(_square(-70, 44, 1e-7), outer=True) is None


def _lonlat(x, y):
    """the inverse of the door's _mercator."""
    import math
    r = 6378137.0
    return math.degrees(x / r), math.degrees(2 * math.atan(math.exp(y / r)) - math.pi / 2)


def test_a_level_is_rounded_finer_when_1_m_collapses_a_ring():
    """a hole 0.3 m across collapses at 1 m and survives at 0.1 m, so the
    whole level goes to 0.1 m and says why (D-368)."""
    from canopy.expose.targets.arcgis_webmap import _mercator
    x, y = _mercator(-69.995, 44.005)
    x0, y0 = int(x) + 0.12, int(y) + 0.12
    hole = [list(_lonlat(a, b)) for a, b in
            ((x0, y0), (x0, y0 + 0.3), (x0 + 0.3, y0 + 0.3), (x0 + 0.3, y0), (x0, y0))]
    rings, decimals, finer = ap.shaped_level("cousub", {("a", "1"): {
        "type": "Polygon", "coordinates": [_square(-70, 44), hole]}})
    assert decimals == 1 and "at 1 m" in finer[0] and "ring collapsed" in finer[0]
    assert len(rings[("a", "1")]) == 2


def test_a_shape_broken_at_both_roundings_is_refused():
    pytest.importorskip("shapely")
    bow = [[-70.0, 44.0], [-69.99, 44.01], [-69.99, 44.0], [-70.0, 44.01], [-70.0, 44.0]]
    with pytest.raises(PublishRefusal, match="D-368"):
        ap.shaped_level("cousub", {("a", "1"): {"type": "Polygon", "coordinates": [bow]}})


# ── what it is owed ──────────────────────────────────────────────────────
def test_a_second_push_of_the_same_parents_changes_nothing(tmp_path):
    root, portal = garden(tmp_path), StoringPortal()
    pages = bucket(root)
    run(root, pages, portal)
    [o] = run(root, pages, portal)
    assert o.outcome == "unchanged"


def test_a_new_profile_version_moves_the_whole_map(tmp_path):
    root, portal = garden(tmp_path), StoringPortal()
    run(root, bucket(root), portal)
    moved = rows()
    moved[1]["about"] = "Androscoggin County is a county in Maine."
    [o] = run(root, bucket(root, profile="q" * 64, the_rows=moved), portal)
    assert o.outcome == "updated" and "the whole map" in "\n".join(o.lines)
    _, data = stored(portal)
    county = data["operationalLayers"][1]["featureCollection"]["layers"][0]["featureSet"]
    assert county["features"][0]["attributes"]["about"].startswith("Androscoggin County is a")


def test_a_new_outline_version_is_owed_a_move(tmp_path):
    root, portal = garden(tmp_path), StoringPortal()
    run(root, bucket(root), portal)
    [o] = run(root, bucket(root, versions={"county": "e" * 64}), portal, write=False)
    assert o.outcome == "would update" and "the whole map" in "\n".join(o.lines)


def test_a_seed_changed_and_not_yet_told_is_refused(tmp_path):
    root = garden(tmp_path)
    pages = bucket(root)
    (root / "seeds" / "notes" / "notes.yml").write_text("# changed\n")
    with pytest.raises(PublishRefusal, match="no told copy"):
        run(root, pages, StoringPortal(), write=False)


def test_a_missing_markers_copy_says_how_to_draw_it(tmp_path):
    root = garden(tmp_path)
    pages = bucket(root)
    dk = s3.display_keys(PLOT, ap.OUTLINES["sldu"], "s" * 64, ap.POINTS_COPY)
    pages.pop(f"{BASE}/{dk['geojson']}")
    with pytest.raises(PublishRefusal) as e:
        run(root, pages, StoringPortal(), write=False)
    assert "--display --markers --write" in e.value.would_admit


def test_a_map_changed_by_hand_is_refused_and_checked(tmp_path):
    root, portal = garden(tmp_path), StoringPortal()
    run(root, bucket(root), portal)
    item, data = stored(portal)
    data["operationalLayers"].pop()
    item["text"] = json.dumps(data)
    [o] = run(root, bucket(root, profile="q" * 64), portal)
    assert o.outcome == "refused" and "changed by hand" in "\n".join(o.lines)
    [c] = door.check(PLOT, ["test"], root=root, kinds=registered(http=portal),
                     ask=lambda p: "test-password",
                     fresh_refusals=lambda plot, r: _recorded(root)["refusals_sha256"])
    assert c.outcome == "differs" and "changed by hand" in "\n".join(c.lines)


def _recorded(root):
    return door.read_record(root / "plots" / PLOT)["targets"]["test"][door.PLACES_KEY]


def test_check_reads_a_places_map_as_recorded(tmp_path):
    root, portal = garden(tmp_path), StoringPortal()
    run(root, bucket(root), portal)
    [c] = door.check(PLOT, ["test"], root=root, kinds=registered(http=portal),
                     ask=lambda p: "test-password",
                     fresh_refusals=lambda plot, r: _recorded(root)["refusals_sha256"])
    assert c.outcome == "as recorded", c.lines


def test_check_says_a_stale_refusal_record(tmp_path):
    root, portal = garden(tmp_path), StoringPortal()
    run(root, bucket(root), portal)
    [c] = door.check(PLOT, ["test"], root=root, kinds=registered(http=portal),
                     ask=lambda p: "test-password", fresh_refusals=lambda plot, r: "f" * 64)
    assert c.outcome == "differs" and "stale" in "\n".join(c.lines)


def test_check_compares_sharing_with_the_target_not_only_the_record(tmp_path):
    root, portal = garden(tmp_path), StoringPortal()
    run(root, bucket(root), portal)
    import yaml
    path = root / "plots" / PLOT / "publish" / "targets.yml"
    doc = yaml.safe_load(path.read_text())
    doc["targets"]["test"]["sharing"] = "organization"
    path.write_text(yaml.safe_dump(doc))
    [c] = door.check(PLOT, ["test"], root=root, kinds=registered(http=portal),
                     ask=lambda p: "test-password",
                     fresh_refusals=lambda plot, r: _recorded(root)["refusals_sha256"])
    assert c.outcome == "differs" and "the target says organization" in "\n".join(c.lines)


def test_an_entry_with_no_kind_is_refused_on_both_paths(tmp_path):
    root, portal = garden(tmp_path), StoringPortal()
    run(root, bucket(root), portal)
    rec = door.read_record(root / "plots" / PLOT)
    rec["targets"]["test"][door.PLACES_KEY].pop("kind")
    door.write_record(root / "plots" / PLOT, rec)
    [o] = run(root, bucket(root), portal, write=False)
    assert o.outcome == "refused" and "D-371" in "\n".join(o.lines)
    [c] = door.check(PLOT, ["test"], root=root, kinds=registered(http=portal),
                     ask=lambda p: "test-password")
    assert c.outcome == "differs" and "D-371" in "\n".join(c.lines)


def test_a_target_kind_from_before_d371_is_refused_with_its_new_name(tmp_path):
    root = fakes.garden(tmp_path, {"test": {
        "kind": "arcgis_webmap", "portal": fakes.PORTAL, "owner": "RDS_NU",
        "owner_kind": "institutional", "folder": "f", "sharing": "private", "groups": []}})
    from canopy.expose.targets import load_targets
    with pytest.raises(PublishRefusal) as e:
        load_targets(root / "plots" / fakes.PLOT, registered())
    assert e.value.would_admit == "kind: arcgis"


def test_the_description_names_every_parent_and_the_maps_hash(tmp_path):
    root, portal = garden(tmp_path), StoringPortal()
    run(root, bucket(root), portal)
    item, data = stored(portal)
    assert ap.map_sha256(data) in item["description"]
    for harvest in ap.OUTLINES.values():
        assert harvest in item["description"]
    assert "held inside this map" in item["description"]
    assert "Penobscot Indian Island Reservation" in item["description"]


def test_the_command_asks_for_places_rightly():
    import argparse
    from canopy.cli import publish as cli
    parser = argparse.ArgumentParser()
    cli.register(parser.add_subparsers())
    ok = parser.parse_args(["publish", "maine", "--places", "--to", "test"])
    assert cli._asked_wrongly(ok) is None
    for argv, said in ((["publish", "maine", "x", "--places", "--to", "test"], "no artifact"),
                       (["publish", "maine", "--places"], "--to"),
                       (["publish", "maine", "--places", "--to", "test", "--write"], "--by")):
        assert said in cli._asked_wrongly(parser.parse_args(argv))


def test_every_step_the_display_copy_and_the_told_copy_record_is_in_the_closed_set():
    import re
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "seeds" / "schemas" / "provenance.schema.json").read_text())
    allowed = set(schema["properties"]["publication"]["items"]["properties"]["step"]["enum"])
    for rel in ("canopy/aws/display.py", "canopy/aws/told.py"):
        recorded = set(re.findall(r'"step": "([a-z_]+)"', (root / rel).read_text()))
        assert recorded and recorded <= allowed, (rel, sorted(recorded - allowed))
    assert display.display_name("markers", 25) == "markers"
