"""
tests/test_lenses.py ~ the lenses (zip 9b2, D-383 to D-386, D-390)

the lanes are read from the repo's own seeds, so a seed that breaks a rule
fails here: a CII indicator joins a pillar only through the chain (D-383);
carriers are never in a pillar (D-384); every member of a lane of ours is
named with its reason, declares a direction, and is a share or a rate, never a
count (D-385). a lens is read from a fake bucket of joined copies and written
to the door's fake portal: one group per level, the first visible, only its
first measure on; a copy still to draw is named with its command and stops the
write (LENS-1); an empty lane holds the orientation copy and says so; the door
owns the whole lens, records it by hash, and `--check` reads it so (D-380).

the bucket, the portal and the gate are the door's fakes (test_publish_door.py),
loaded by path so its tests are not collected twice. ~
"""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest
import yaml

from canopy.aws import display, s3
from canopy.expose import lenses
from canopy.expose import publish as door
from canopy.expose.targets import PublishRefusal, registered
from canopy.expose.targets.arcgis_places import map_sha256
from canopy.expose.targets.arcgis_webmap import DIRECTIONS

_spec = importlib.util.spec_from_file_location(
    "_door_fakes", Path(__file__).with_name("test_publish_door.py"))
fakes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fakes)

REPO = Path(__file__).resolve().parents[1]
DOMAIN, PLOT = fakes.DOMAIN, "demo"
BASE = f"https://{DOMAIN}"
NOTE = {"census_note": "the boundary is the Census Bureau's"}
TOWNS, COUNTIES = "outline_towns_outline", "outline_counties_outline"
T_LANG, C_LANG = "cousub_language_derive_values", "county_language_derive_values"


# ── the seeds, as the repo holds them ────────────────────────────────────
def test_the_chain_places_ciis_own_three_where_cii_does():
    chain = lenses.pillar_chain(REPO, "cii_2026_equal_chips")
    assert chain["cii_broadband"] == "news_information"
    assert chain["cii_rent_burden"] == "health_opportunity"
    assert chain["cii_no_vehicle"] == "health_opportunity"
    weights = yaml.safe_load((REPO / "seeds/weights/cii_2026_equal_chips.yml").read_text())
    assert set(chain.values()) <= set(weights["pillars"])


def test_every_lane_keeps_the_seeds_rules():
    lanes = lenses.load_lanes(REPO)
    indicators = lenses.load_indicators(REPO)
    chain = lenses.pillar_chain(REPO, "cii_2026_equal_chips", indicators)
    weights = yaml.safe_load((REPO / "seeds/weights/cii_2026_equal_chips.yml").read_text())
    assert {k for k, v in lanes.items() if v["kind"] == "pillar"} == set(weights["pillars"])
    seen = {}
    for lane, the in lanes.items():
        for ind, m in the["members"].items():
            assert ind not in seen, f"{ind} is in {seen.get(ind)} and {lane}"
            seen[ind] = lane
            body = indicators[ind]
            assert body.get("direction") in DIRECTIONS, ind
            assert m["reason"].strip(), ind
            if the["kind"] == "ours":
                assert not lenses.is_count(body.get("unit")), f"{ind} is a count"
                assert m["placed_by"] == "rewildingcities"
                assert body.get("defined_by") == "rewildingcities", ind
                assert body.get("role") == the["role"], ind
                assert ind not in chain, f"{ind} replicates CII, so it is CII's to place"
            else:
                assert m["placed_by"] == "replicates" and chain[ind] == lane


def test_our_carriers_are_never_in_a_pillar():
    """D-384: our carriers are their own lane. CII's own carrier measures (library
    visits, journalist equivalents) stay in the pillar CII places them in."""
    lanes = lenses.load_lanes(REPO)
    carriers = {i for i, b in lenses.load_indicators(REPO).items()
                if b.get("role") == "carrier" and b.get("defined_by") == "rewildingcities"}
    in_pillars = {i for v in lanes.values() if v["kind"] == "pillar" for i in v["members"]}
    assert carriers and not carriers & in_pillars
    assert set(lanes["carriers"]["members"]) <= carriers


def test_an_indicator_declared_twice_is_refused(tmp_path):
    d = tmp_path / "seeds" / "indicators"
    d.mkdir(parents=True)
    for name in ("a.yml", "b.yml"):
        (d / name).write_text(yaml.safe_dump({"indicators": {"x": {"unit": "percent"}}}))
    with pytest.raises(PublishRefusal):
        lenses.load_indicators(tmp_path)


def test_counts_are_told_apart_from_what_a_lens_draws():
    for unit in ("count", "persons", "households", None):
        assert lenses.is_count(unit), unit
    for unit in ("percent_of_households", "per_1000_persons", "years", "score", "days"):
        assert not lenses.is_count(unit), unit


def test_a_pillars_count_is_named_and_never_drawn():
    lanes = lenses.load_lanes(REPO)
    indicators = lenses.load_indicators(REPO)
    assert "cii_pub_news_outlets" in lanes["news_information"]["members"]
    assert lenses.is_count(indicators["cii_pub_news_outlets"]["unit"])


# ── a garden and a bucket of joined copies ───────────────────────────────
def garden(tmp_path, tables=None, sharing="private"):
    root = fakes.garden(tmp_path, {"test": {
        "kind": "arcgis", "portal": fakes.PORTAL, "owner": "RDS_NU",
        "owner_kind": "institutional", "folder": "rc test", "sharing": sharing, "groups": []}})
    for rel in ("seeds/indicators", "seeds/weights", "seeds/crosswalks/pillars"):
        shutil.copytree(REPO / rel, root / rel)
    plan = {"orientation": COUNTIES, "levels": {
        "cousub": {"outline": TOWNS, "tables": tables if tables is not None else [T_LANG]},
        "county": {"outline": COUNTIES, "tables": [C_LANG]}}}
    (root / "plots" / PLOT / "publish" / "lenses.yml").write_text(yaml.safe_dump(plan))
    return root


def _square(x, y, d=0.01):
    return [[x, y], [x + d, y], [x + d, y + d], [x, y + d], [x, y]]


def _outline(pages, harvest, sha, markers=False):
    v = f"{BASE}/{s3.version_prefix(PLOT, harvest, sha)}"
    pages[f"{BASE}/{s3.pointer_key(PLOT, harvest)}"] = json.dumps(
        {"sha256": sha, "allow": "a" * 64, "data": "data.parquet"})
    pages[f"{v}/allow/{'a' * 64}.json"] = json.dumps({"gate": {
        "context_text": NOTE, "license": [{"dataset": "faces", "term": "geo"}]}})
    pages[f"{v}/envelope.json"] = json.dumps({"metadata": {"data_category": "vector"}})
    if markers:
        dk = s3.display_keys(PLOT, harvest, sha, "markers")
        pages[f"{BASE}/{dk['envelope']}"] = json.dumps({
            "metadata": {"derived_from": sha, "bbox": [-71.0, 43.0, -67.0, 47.5]},
            "provenance": [{"publication": [{"step": "marked", "detail": "16 places"}]}],
            "warnings": []})
        pages[f"{BASE}/{dk['geojson']}"] = json.dumps({"type": "FeatureCollection", "features": [
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-70.2, 44.1]},
             "properties": {"authority": "us_census_geoid", "code": "23001",
                            "name": "Androscoggin County"}}]})


def _joined(pages, table, tsha, outline, osha, level, values, *, standing=False):
    """a values table's version and its copy joined on the outline's version."""
    v = f"{BASE}/{s3.version_prefix(PLOT, table, tsha)}"
    pages[f"{BASE}/{s3.pointer_key(PLOT, table)}"] = json.dumps(
        {"sha256": tsha, "allow": "b" * 64, "data": "data.parquet"})
    pages[f"{v}/allow/{'b' * 64}.json"] = json.dumps({"gate": {
        "context_text": NOTE, "license": [{"dataset": "acs", "term": "geo"}]}})
    pages[f"{v}/envelope.json"] = json.dumps({"metadata": {"data_category": "tabular"}})
    inds = sorted({i for row in values for i in row})
    columns = {i: [f"{i}__value"] + ([f"{i}__percentile"] if standing else []) for i in inds}
    name = display.joined_name(outline, osha)
    dk = s3.display_keys(PLOT, table, tsha, name)
    pages[f"{BASE}/{dk['envelope']}"] = json.dumps({
        "metadata": {"derived_from": tsha, "bbox": [-71.0, 43.0, -67.0, 47.5],
                     "display_kind": "outlines",
                     "joined_to": {"harvest": outline, "sha256": osha, "level": level},
                     "join": {"indicators": inds, "columns": columns,
                              "directions": {i: "higher_is_worse" for i in inds}}},
        "provenance": [{"publication": [{"step": "joined", "detail": f"{len(values)} places"}]}],
        "warnings": []})
    feats = []
    for k, row in enumerate(values):
        props = {"authority": "us_census_geoid", "code": f"23{k:03d}", "name": f"Place {k}"}
        props.update({f"{i}__value": x for i, x in row.items()})
        feats.append({"type": "Feature", "properties": props,
                      "geometry": {"type": "Polygon", "coordinates": [_square(-70 + k / 10, 44)]}})
    pages[f"{BASE}/{dk['geojson']}"] = json.dumps({"type": "FeatureCollection", "features": feats})


def bucket(*, towns_sha="t" * 64, table_sha="1" * 64, draw_towns=True, standing=False):
    pages = {}
    _outline(pages, TOWNS, towns_sha)
    _outline(pages, COUNTIES, "c" * 64, markers=True)
    both = [{"limited_english_persons_share": 2.5, "limited_english_households": 1.0},
            {"limited_english_persons_share": 7.5, "limited_english_households": 3.0}]
    if draw_towns:
        _joined(pages, T_LANG, table_sha, TOWNS, towns_sha, "cousub", both, standing=standing)
    else:
        v = f"{BASE}/{s3.version_prefix(PLOT, T_LANG, table_sha)}"
        pages[f"{BASE}/{s3.pointer_key(PLOT, T_LANG)}"] = json.dumps(
            {"sha256": table_sha, "allow": "b" * 64, "data": "data.parquet"})
        pages[f"{v}/allow/{'b' * 64}.json"] = json.dumps({"gate": {"context_text": NOTE}})
        pages[f"{v}/envelope.json"] = json.dumps({"metadata": {"data_category": "tabular"}})
    _joined(pages, C_LANG, "2" * 64, COUNTIES, "c" * 64, "county", both)
    return pages


def judge(envelope, *, plot, target, sharing_level, plot_dir):
    return {"decision": "allow", "record": {"sharing_level": sharing_level,
                                            "gate_version": "test", "context_text": NOTE,
                                            "license": []}}


class StoringPortal(fakes.FakePortal):
    """stores a whole float as an integer, as ArcGIS does (D-362)."""

    def post(self, url, data=None, headers=None, timeout=None):
        from canopy.expose.targets.arcgis_places import door_form
        if data and "text" in data:
            data = dict(data, text=json.dumps(door_form(json.loads(data["text"]))))
        return super().post(url, data=data, headers=headers, timeout=timeout)


def run(root, pages, portal, lane="our_barriers", *, write=True, **kw):
    return door.publish_lens(PLOT, lane, ["test"], root=root, write=write,
                             by="tester" if write else None, reason="a test" if write else None,
                             domain=DOMAIN, fetch=fakes.fetcher(pages), judge=judge,
                             kinds=registered(http=portal), ask=lambda p: "test-password",
                             now="2026-11-18T00:00:00+00:00", **kw)


def stored(portal):
    [item] = portal.items.values()
    return item, json.loads(item["text"])


# ── reading and building ─────────────────────────────────────────────────
def test_a_dry_run_names_each_level_and_signs_in_nowhere(tmp_path):
    root, portal = garden(tmp_path), StoringPortal()
    [o] = run(root, bucket(), portal, write=False)
    said = "\n".join(o.lines)
    assert o.outcome == "would publish" and portal.calls == []
    assert "Towns: limited_english_persons_share, limited_english_households" in said
    assert "placed by rewildingCities" in said


def test_a_group_per_level_with_only_the_first_measure_on(tmp_path):
    root, portal = garden(tmp_path), StoringPortal()
    [o] = run(root, bucket(), portal)
    assert o.outcome == "published"
    _, data = stored(portal)
    groups = data["operationalLayers"]
    assert [g["layerType"] for g in groups] == ["GroupLayer", "GroupLayer"]
    assert [g["visibility"] for g in groups] == [True, False]
    for g in groups:
        assert [l["visibility"] for l in g["layers"]] == [True, False]
        for l in g["layers"]:
            assert l["url"].startswith(BASE) and "featureCollection" not in l
            assert l["layerDefinition"]["drawingInfo"]["renderer"]["type"] == "classBreaks"


def test_the_lens_is_its_own_kind_recorded_by_its_hash(tmp_path):
    root, portal = garden(tmp_path), StoringPortal()
    [o] = run(root, bucket(), portal)
    assert "SAME as sent" in "\n".join(o.lines)
    _, data = stored(portal)
    entry = door.read_record(root / "plots" / PLOT)["targets"]["test"]["lens/our_barriers"]
    assert entry["kind"] == "arcgis_lens_map" and entry["lane"] == "our_barriers"
    assert map_sha256(data) == entry["map_sha256"]
    assert set(entry["parents"]) == {f"cousub {T_LANG}", f"county {C_LANG}"}


def test_the_same_copies_twice_change_nothing(tmp_path):
    root, portal = garden(tmp_path), StoringPortal()
    pages = bucket()
    run(root, pages, portal)
    [o] = run(root, pages, portal)
    assert o.outcome == "unchanged"


def test_a_new_outline_version_moves_the_whole_lens(tmp_path):
    root, portal = garden(tmp_path), StoringPortal()
    run(root, bucket(), portal)
    [o] = run(root, bucket(towns_sha="u" * 64), portal)
    assert o.outcome == "updated" and "the whole map" in "\n".join(o.lines)


def test_a_copy_still_to_draw_is_named_and_stops_the_write(tmp_path):
    root, portal = garden(tmp_path), StoringPortal()
    [o] = run(root, bucket(draw_towns=False), portal)
    said = "\n".join(o.lines)
    assert o.outcome == "refused" and portal.items == {}
    assert f"canonical {PLOT} {T_LANG} --display --join {TOWNS} --write" in said
    assert "LENS-1" in said


def test_a_table_never_written_is_named_with_both_commands(tmp_path):
    root, portal = garden(tmp_path, tables=[T_LANG, "cousub_derive_values"]), StoringPortal()
    [o] = run(root, bucket(), portal, write=False)
    said = "\n".join(o.lines)
    assert "cousub_derive_values is not written" in said and o.outcome == "refused"


def test_a_standing_is_never_drawn_on_a_lens(tmp_path):
    root = garden(tmp_path)
    with pytest.raises(PublishRefusal) as e:
        run(root, bucket(standing=True), StoringPortal(), write=False)
    assert "D-365" in e.value.reason


def test_an_empty_lane_holds_the_orientation_copy_and_says_so(tmp_path):
    root, portal = garden(tmp_path), StoringPortal()
    [o] = run(root, bucket(), portal, lane="civic_participation")
    assert o.outcome == "published"
    item, data = stored(portal)
    [layer] = data["operationalLayers"]
    assert layer["title"].startswith("No measure is placed in this lens yet")
    assert "No measure is placed in this lens yet" in item["description"]


def test_an_unknown_lane_is_refused(tmp_path):
    root = garden(tmp_path)
    with pytest.raises(PublishRefusal):
        run(root, bucket(), StoringPortal(), lane="vibes", write=False)


def test_check_reads_a_lens_by_its_hash(tmp_path):
    root, portal = garden(tmp_path), StoringPortal()
    run(root, bucket(), portal)
    kinds = registered(http=portal)
    [o] = door.check(PLOT, ["test"], root=root, kinds=kinds, ask=lambda p: "test-password")
    assert o.outcome == "as recorded", o.lines
    item, data = stored(portal)
    data["operationalLayers"][0]["title"] = "renamed by hand"
    item["text"] = json.dumps(data)
    [o] = door.check(PLOT, ["test"], root=root, kinds=kinds, ask=lambda p: "test-password")
    assert o.outcome == "differs" and "changed by hand" in "\n".join(o.lines)


def test_a_lens_changed_by_hand_is_refused_on_the_next_move(tmp_path):
    root, portal = garden(tmp_path), StoringPortal()
    run(root, bucket(), portal)
    item, data = stored(portal)
    data["baseMap"] = {"title": "a person's basemap"}
    item["text"] = json.dumps(data)
    [o] = run(root, bucket(towns_sha="u" * 64), portal)
    assert o.outcome == "refused" and "lens was changed by hand" in "\n".join(o.lines)
