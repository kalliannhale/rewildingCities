"""
tests/test_door_choropleth.py ~ the door's choropleths and its check (zip 8b)

a choropleth is a table drawn on an outline, so the door holds both parents:
it reads the copy drawn on the outline's current version, owes a move when
either parent moves, checks every note against both allow records, credits
both, keys its record <table>/<outline>/<indicator>, and owns its renderer.
`check` reads every recorded item and writes nothing (DOORCHECK-1).

the bucket, the portal and the gate are the fakes test_publish_door.py keeps,
loaded by path so its tests are not collected twice. ~
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from canopy.aws import display
from canopy.expose import publish as door
from canopy.expose.targets import PublishRefusal, registered

_spec = importlib.util.spec_from_file_location(
    "_door_fakes", Path(__file__).with_name("test_publish_door.py"))
fakes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fakes)

DOMAIN, PLOT = fakes.DOMAIN, fakes.PLOT
TABLE, OUTLINE, IND = "broadband_standings", "outline_counties_outline", "cii_broadband"
T1, T2 = "a" * 64, "b" * 64
O1, O2 = "c" * 64, "d" * 64
A1, A2, B1, B2 = "1" * 64, "2" * 64, "3" * 64, "4" * 64
KEY = f"{TABLE}/{OUTLINE}/{IND}"


def _features(values=(61.0, 12.5, None)):
    codes = ("23005", "23029", "23031")
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": []},
         "properties": {"authority": "us_census_geoid", "code": c, "name": f"county {c}",
                        "context_note": "contains_census_tribal_area" if c == "23029" else None,
                        f"{IND}__percentile": v, f"{IND}__value": 90.0,
                        "cii_rent_burden__value": 30.0, "joined": v is not None}}
        for c, v in zip(codes, values)]}


def pages(t=T1, o=O1, ta=A1, oa=B1, *, markers=False, values=(61.0, 12.5, None),
          table_notes=None, outline_notes=None, ref_n=3144, copy_on=None):
    """the bucket by URL: the table's and the outline's current versions, their
    allow records and receipts, and the copy drawn on outline version copy_on."""
    base = f"https://{DOMAIN}/harvests/{PLOT}"
    out = {}
    tnotes = {} if table_notes is None else table_notes
    onotes = ({"contains_census_tribal_area": "the Census's tribal area, not the nation's"}
              if outline_notes is None else outline_notes)
    for harvest, sha, allow, notes, lic, cat in (
            (TABLE, t, ta, tnotes, [{"dataset": "acs_us_county_2024", "term": "us_gov"}], "tabular"),
            (OUTLINE, o, oa, onotes, [{"dataset": "faces_2024_me", "term": "geo"}], "vector")):
        v = f"{base}/{harvest}/versions/{sha}"
        out[f"{base}/{harvest}/current"] = json.dumps({"sha256": sha, "allow": allow,
                                                       "data": "data.parquet"})
        out[f"{v}/allow/{allow}.json"] = json.dumps({"gate": {
            "context_text": notes, "caveats": [], "license": lic,
            "publication_steps": [{"step": "format_changed", "detail": f"{harvest} to parquet"}]}})
        out[f"{v}/envelope.json"] = json.dumps({"metadata": {"data_category": cat}})
    drawn_on = copy_on or o
    name = display.joined_name(OUTLINE, drawn_on, markers=markers)
    v = f"{base}/{TABLE}/versions/{t}/display/{name}"
    columns = {IND: [f"{IND}__percentile", f"{IND}__value"],
               "cii_rent_burden": ["cii_rent_burden__value"]}
    if markers:
        columns[IND].append(f"{IND}__count")
    out[f"{v}.envelope.json"] = json.dumps({
        "metadata": {"semantic_type": "indicator_standings", "derived_from": t,
                     "display_kind": "markers" if markers else "polygons",
                     "feature_count": 3, "bbox": [-71.0, 43.0, -67.0, 47.5],
                     "lineage": {"kind": "experiment", "run": "bb", "method": "$m"},
                     "reference_population": {"rule": "units with a value",
                                              "per_indicator": {IND: {"n": ref_n}}},
                     "joined_to": {"harvest": OUTLINE, "sha256": drawn_on, "allow": oa,
                                   "level": "county"},
                     "join": {"indicators": [IND, "cii_rent_burden"], "columns": columns,
                              "counts": {"places": 3, "places_without_row": 1,
                                         "rows_outside_outline": 3128}}},
        "provenance": [{"primitive": "make_display_copy",
                        "publication": [{"step": "joined", "detail": "on authority and code"}]}],
        "warnings": []})
    fc = _features(values)
    if markers:
        for f in fc["features"]:
            f["properties"][f"{IND}__count"] = 0 if f["properties"]["code"] == "23031" else 19
    out[f"{v}.geojson"] = json.dumps(fc)
    return out


def judge(notes=None, license=None):
    notes = ({"contains_census_tribal_area": "the Census's tribal area, not the nation's"}
             if notes is None else notes)
    def j(envelope, *, plot, target, sharing_level, plot_dir):
        return {"decision": "allow", "record": {"sharing_level": sharing_level,
                                                "gate_version": "test", "context_text": notes,
                                                "license": license or []}}
    return j


def run(root, bucket, portal, *, write=True, j=None, markers=False, **kw):
    def ask(prompt):
        return "test-password"
    return door.publish(PLOT, TABLE, ["test"], root=root, write=write,
                        by="tester" if write else None, reason="a test" if write else None,
                        domain=DOMAIN, fetch=fakes.fetcher(bucket), judge=j or judge(),
                        kinds=registered(http=portal), ask=ask, now="2026-11-17T00:00:00+00:00",
                        join=OUTLINE, indicator=kw.pop("indicator", IND), markers=markers, **kw)


def garden(tmp_path):
    root = fakes.garden(tmp_path)
    lic = root / "seeds" / "licenses" / "licenses.yml"
    import yaml
    doc = yaml.safe_load(lic.read_text())
    doc["terms"]["us_gov"] = {"name": "U.S. government work", "permits": ["private"],
                              "attribution": "none", "verified": True, "basis": "test"}
    lic.write_text(yaml.safe_dump(doc))
    return root


def layer_of(portal):
    [item] = portal.items.values()
    return item, json.loads(item["text"])["operationalLayers"][0]


# ── the first push ───────────────────────────────────────────────────────
def test_a_choropleth_is_made_with_the_doors_quintiles(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    [o] = run(root, pages(), portal)
    assert o.outcome == "published"
    item, layer = layer_of(portal)
    assert layer["id"] == f"rewilding-{TABLE}-{OUTLINE}-{IND}"
    r = layer["layerDefinition"]["drawingInfo"]["renderer"]
    assert r["type"] == "classBreaks" and r["field"] == f"{IND}__percentile"
    assert [i["classMaxValue"] for i in r["classBreakInfos"]] == [20, 40, 60, 80, 100]
    assert r["defaultSymbol"]["style"] == "esriSFSBackwardDiagonal"
    assert "3,144" in layer["title"] and "higher is better" in layer["title"]
    assert f"/versions/{T1}/display/{OUTLINE}_{O1[:12]}_web_25m.geojson" in layer["url"]


def test_the_record_holds_both_parents_under_the_maps_own_key(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    run(root, pages(), portal)
    entry = fakes.record(root)["targets"]["test"][KEY]
    assert entry["sha256"] == T1 and entry["allow"] == A1
    assert entry["outline"] == {"harvest": OUTLINE, "sha256": O1, "allow": B1}
    assert entry["indicator"] == IND and entry["renderer_sha256"]


def test_the_popup_shows_the_place_and_the_one_indicator(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    run(root, pages(), portal)
    _, layer = layer_of(portal)
    seen = {f["fieldName"]: f["visible"] for f in layer["popupInfo"]["fieldInfos"]}
    assert seen["name"] and seen[f"{IND}__percentile"] and seen["context_note"]
    assert not seen["cii_rent_burden__value"] and not seen["joined"]


def test_the_description_names_the_outline_and_credits_both_parents(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    run(root, pages(), portal)
    item, _ = layer_of(portal)
    d = item["description"]
    assert OUTLINE in d and O1 in d and B1 in d and "3128" in d
    assert "the Census&#x27;s tribal area" in d
    assert "Maine GeoLibrary data" in d and "U.S. government work" in d


def test_a_second_push_owes_nothing(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    run(root, pages(), portal)
    before = len(portal.calls)
    [o] = run(root, pages(), portal)
    assert o.outcome == "unchanged" and len(portal.calls) == before


# ── either parent moves ──────────────────────────────────────────────────
def test_a_new_outline_version_is_owed_and_waits_for_its_copy(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    run(root, pages(), portal)
    stale = pages(o=O2, copy_on=O1)
    for url in [u for u in stale if f"{OUTLINE}_{O2[:12]}" in u]:
        stale.pop(url)
    with pytest.raises(PublishRefusal, match="no display copy") as e:
        run(root, stale, portal)
    assert "--join" in e.value.would_admit


def test_a_new_outline_version_moves_the_layer_and_puts_the_renderer_back(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    run(root, pages(), portal)
    item, _ = layer_of(portal)
    data = json.loads(item["text"])
    data["operationalLayers"][0]["layerDefinition"]["drawingInfo"] = {"renderer": {"type": "simple"}}
    item["text"] = json.dumps(data)
    [o] = run(root, pages(o=O2, oa=B2), portal)
    assert o.outcome == "updated"
    assert any("restyled by hand" in line for line in o.lines)
    _, layer = layer_of(portal)
    assert layer["layerDefinition"]["drawingInfo"]["renderer"]["type"] == "classBreaks"
    assert f"{OUTLINE}_{O2[:12]}" in layer["url"]
    entry = fakes.record(root)["targets"]["test"][KEY]
    assert entry["outline"]["sha256"] == O2
    assert entry["previous"]["outline"]["sha256"] == O1


def test_a_new_table_version_is_a_move_too(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    run(root, pages(), portal)
    [o] = run(root, pages(t=T2), portal)
    assert o.outcome == "updated"
    assert any(line.startswith("owed: the layer moved from") for line in o.lines)


def test_a_new_outline_allow_record_rewrites_the_description_alone(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    run(root, pages(), portal)
    [o] = run(root, pages(oa=B2), portal)
    assert o.outcome == "updated"
    [update] = portal.posts("/update")
    assert "text" not in update[2]


# ── what the door refuses ────────────────────────────────────────────────
def test_a_copy_drawn_on_another_outline_version_is_refused(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    bucket = pages()
    name = display.joined_name(OUTLINE, O1)
    url = f"https://{DOMAIN}/harvests/{PLOT}/{TABLE}/versions/{T1}/display/{name}.envelope.json"
    env = json.loads(bucket[url])
    env["metadata"]["joined_to"]["sha256"] = O2
    bucket[url] = json.dumps(env)
    with pytest.raises(PublishRefusal, match="not .*current version"):
        run(root, bucket, portal)


def test_two_parents_that_word_one_note_differently_are_refused(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    bucket = pages(table_notes={"contains_census_tribal_area": "other words"})
    [o] = run(root, bucket, portal)
    assert o.outcome == "refused" and any("cannot say both" in line for line in o.lines)
    assert portal.calls == []


def test_a_note_only_the_outline_holds_passes(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    [o] = run(root, pages(table_notes={}), portal)
    assert o.outcome == "published"


def test_a_dataset_neither_record_credits_is_refused(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    j = judge(license=[{"dataset": "faces_2024_me", "term": "geo"},
                       {"dataset": "something_unheld", "term": "geo"}])
    [o] = run(root, pages(), portal, j=j)
    assert o.outcome == "refused" and any("something_unheld" in line for line in o.lines)
    assert portal.items == {}


def test_a_colour_field_with_no_number_is_refused(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    [o] = run(root, pages(values=(None, None, None)), portal)
    assert o.outcome == "refused" and any("holds no number" in line for line in o.lines)


def test_a_standing_with_no_reference_population_is_refused(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    [o] = run(root, pages(ref_n=None), portal)
    assert o.outcome == "refused" and any("reference population" in line for line in o.lines)


def test_an_indicator_the_copy_does_not_hold_is_refused(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    with pytest.raises(PublishRefusal, match="no indicator 'cii_nope'"):
        run(root, pages(), portal, indicator="cii_nope")


def test_a_choropleth_is_never_adopted(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    with pytest.raises(PublishRefusal, match="adopt"):
        run(root, pages(), portal, adopt="x")


# ── markers ──────────────────────────────────────────────────────────────
def test_markers_are_sized_in_equal_steps_with_none_listed_its_own_class(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    [o] = run(root, pages(markers=True), portal, markers=True)
    assert o.outcome == "published"
    _, layer = layer_of(portal)
    r = layer["layerDefinition"]["drawingInfo"]["renderer"]
    assert r["field"] == f"{IND}__count"
    infos = r["classBreakInfos"]
    assert infos[0]["classMaxValue"] == 0 and infos[0]["label"] == "none listed"
    assert infos[-1]["classMaxValue"] == 19 and len(infos) == 5
    sizes = [i["symbol"]["size"] for i in infos]
    assert sizes == sorted(sizes)
    assert "equal steps" in layer["title"]


def test_a_map_of_markers_and_a_map_of_outlines_are_two_copies(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    with pytest.raises(PublishRefusal, match="no display copy"):
        run(root, pages(markers=False), portal, markers=True)


# ── DOORSAY-1 ────────────────────────────────────────────────────────────
def test_the_plan_line_reads_true_after_the_write(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    [o] = run(root, pages(), portal)
    assert not any(line.startswith("would ") for line in o.lines)
    assert any(line.startswith("owed: a new web map") for line in o.lines)


# ── the check (DOORCHECK-1) ──────────────────────────────────────────────
def check(root, portal):
    return door.check(PLOT, [], root=root, kinds=registered(http=portal),
                      ask=lambda prompt: "test-password")


def test_check_finds_every_item_as_recorded_and_writes_nothing(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    run(root, pages(), portal)
    before = fakes.record(root)
    posts = len([c for c in portal.calls if c[0] == "post"])
    [o] = check(root, portal)
    assert o.outcome == "as recorded"
    assert fakes.record(root) == before
    assert [c[1] for c in portal.calls if c[0] == "post"][posts:] == ["generateToken"]


def test_check_sees_a_deleted_item_a_hand_edit_and_a_restyle(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    run(root, pages(), portal)
    item, _ = layer_of(portal)
    item["description"] = "someone's own words"
    data = json.loads(item["text"])
    data["operationalLayers"][0]["layerDefinition"]["drawingInfo"] = {"renderer": {"type": "simple"}}
    item["text"] = json.dumps(data)
    [o] = check(root, portal)
    assert o.outcome == "differs"
    assert any("description" in line for line in o.lines)
    assert any("restyled" in line for line in o.lines)
    portal.items.clear()
    [o] = check(root, portal)
    assert o.outcome == "differs" and any("--replace" in line for line in o.lines)


def test_check_sees_a_sharing_changed_in_arcgis(tmp_path):
    root, portal = garden(tmp_path), fakes.FakePortal()
    run(root, pages(), portal)
    item, _ = layer_of(portal)
    item["access"] = "public"
    [o] = check(root, portal)
    assert o.outcome == "differs" and any("shared" in line for line in o.lines)


@pytest.mark.parametrize("argv,said", [
    (["publish", "maine", "x", "--to", "test", "--join", "o"], "--indicator"),
    (["publish", "maine", "x", "--to", "test", "--indicator", "i"], "go with --join"),
    (["publish", "maine", "x", "--check"], "takes no artifact"),
    (["publish", "maine", "--check", "--write"], "only reads"),
    (["publish", "maine", "--to", "test"], "or --check"),
])
def test_the_command_refuses_a_choropleth_or_check_asked_wrongly(argv, said):
    import argparse
    from canopy.cli import publish as cli
    parser = argparse.ArgumentParser()
    cli.register(parser.add_subparsers())
    assert said in cli._asked_wrongly(parser.parse_args(argv))


# ── a portal that rewrites what it stores (D-349) ────────────────────────
class SanitizingPortal(fakes.FakePortal):
    """ArcGIS Online as read 2026-11-17: an item's description is stored with
    the entities html.escape wrote decoded, &#x27; as '."""

    def post(self, url, data=None, headers=None, timeout=None):
        data = dict(data or {})
        if "description" in data:
            data["description"] = data["description"].replace("&#x27;", "'")
        return super().post(url, data=data, headers=headers, timeout=timeout)


def points(root, bucket, portal, **kw):
    return fakes.run(root, bucket, portal, **kw)


def test_the_door_records_the_description_as_the_portal_stores_it(tmp_path):
    root, portal = fakes.garden(tmp_path), SanitizingPortal()
    points(root, fakes.bucket(), portal)
    entry = fakes.record(root)["targets"]["test"][fakes.ART]
    stored = next(iter(portal.items.values()))["description"]
    assert entry["description_seen_sha256"] == door.sha256_text(stored)
    assert entry["description_seen_sha256"] != entry["description_sha256"]
    [o] = points(root, fakes.bucket(), portal)
    assert o.outcome == "unchanged"
    [o] = points(root, fakes.bucket(sha=fakes.SHA2), portal)
    assert o.outcome == "updated"
    [o] = check(root, portal)
    assert o.outcome == "as recorded"


def _before_the_read_back(root):
    import yaml
    path = root / "plots" / PLOT / "publish" / "published.yml"
    doc = yaml.safe_load(path.read_text())
    for entries in doc["targets"].values():
        for entry in entries.values():
            entry.pop("description_seen_sha256", None)
    path.write_text(yaml.safe_dump(doc))


def test_an_item_written_before_the_read_back_is_checked_then_recorded(tmp_path):
    root, portal = fakes.garden(tmp_path), SanitizingPortal()
    points(root, fakes.bucket(), portal)
    _before_the_read_back(root)
    [o] = check(root, portal)
    assert o.outcome == "differs" and any("not yet recorded" in line for line in o.lines)
    [o] = points(root, fakes.bucket(), portal, write=False)
    assert o.outcome == "would update" and any("as ArcGIS stores it" in line for line in o.lines)
    before = len(portal.posts("/update")) + len(portal.posts("/share"))
    [o] = points(root, fakes.bucket(), portal)
    assert o.outcome == "updated"
    assert len(portal.posts("/update")) + len(portal.posts("/share")) == before
    assert fakes.record(root)["targets"]["test"][fakes.ART]["description_seen_sha256"]
    [o] = check(root, portal)
    assert o.outcome == "as recorded"


def test_a_real_hand_edit_is_never_recorded_as_the_doors(tmp_path):
    root, portal = fakes.garden(tmp_path), SanitizingPortal()
    points(root, fakes.bucket(), portal)
    _before_the_read_back(root)
    next(iter(portal.items.values()))["description"] += "<p>someone's own words</p>"
    [o] = points(root, fakes.bucket(), portal)
    assert o.outcome == "refused" and any("changed by hand" in line for line in o.lines)
    assert "description_seen_sha256" not in fakes.record(root)["targets"]["test"][fakes.ART]


def test_an_old_item_that_owes_a_move_waits_for_its_record(tmp_path):
    root, portal = fakes.garden(tmp_path), SanitizingPortal()
    points(root, fakes.bucket(), portal)
    _before_the_read_back(root)
    [o] = points(root, fakes.bucket(sha=fakes.SHA2), portal)
    assert o.outcome == "refused" and any("D-349" in line for line in o.lines)
