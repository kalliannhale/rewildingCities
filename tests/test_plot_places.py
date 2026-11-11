"""
tests/test_plot_places.py  |  rewildingCities, Sprint 05 change 9 (plan build 3)

A plot is a set of places (D-174). Declaring none, it answers for every place
in its graph. Declared, each entry is one place, or one place with what it
contains (followed down contains edges), or with what it touches (overlaps
edges); the plot's places are the union, each with the reason it is there.
A key that is not a place, or an entry of any other shape, means no view,
naming it. There is no parent key: a sub-plot would relate to its parent
through contains edges between their places (D-175).
"""

import json
from pathlib import Path

import pandas as pd
import yaml

from canopy.orchestrator.parsing import parse_manifest
from canopy.wonder.session import open_plot

REPO = Path(__file__).resolve().parents[1]
GEOID, SLDL = "us_census_geoid", "us_census_sldl"


def place(authority, code, level, name):
    return {"authority": authority, "code": code, "level": level, "name": name,
            "vintage": "2024", "kind": level, "census_funcstat": None}


PLACES = pd.DataFrame([
    place(GEOID, "23", "state", "Maine"),
    place(GEOID, "23005", "county", "Cumberland County"),
    place(GEOID, "23009", "county", "Hancock County"),
    place(GEOID, "2300560545", "cousub", "Portland city"),
    place(GEOID, "2300524915", "cousub", "Falmouth town"),
    place(GEOID, "2300904860", "cousub", "Bar Harbor town"),
    place(SLDL, "23118", "sldl", "House District 118"),
    place(SLDL, "23014", "sldl", "House District 14"),
])


def edge(fa, fc, ta, tc, kind, w=1.0):
    return {"from_authority": fa, "from_code": fc, "to_authority": ta, "to_code": tc,
            "kind": kind, "weight_population": w, "weight_households": w}


EDGES = pd.DataFrame([
    edge(GEOID, "23", GEOID, "23005", "contains"),
    edge(GEOID, "23", GEOID, "23009", "contains"),
    edge(GEOID, "23005", GEOID, "2300560545", "contains"),
    edge(GEOID, "23005", GEOID, "2300524915", "contains"),
    edge(GEOID, "23009", GEOID, "2300904860", "contains"),
    edge(GEOID, "2300560545", SLDL, "23118", "overlaps", 0.25),
    edge(GEOID, "2300524915", SLDL, "23118", "overlaps", 0.10),
    edge(GEOID, "2300904860", SLDL, "23014", "overlaps"),
])


def a_plot(tmp_path, places=None):
    plot = tmp_path / "plots" / "demo"
    (plot / ".data").mkdir(parents=True)
    (plot / ".envelopes").mkdir()
    manifest = {"city": {"id": "demo", "name": "demo"}, "crs": {"working": "EPSG:4326"},
                "datasets": {}}
    if places is not None:
        manifest["places"] = places
    (plot / "manifest.yml").write_text(yaml.safe_dump(manifest))
    for name, frame, semantic_type, key, unit in (
            ("graph_places_places", PLACES, "places", ["authority", "code"], "place"),
            ("graph_edges_edges", EDGES, "place_edges",
             ["from_authority", "from_code", "to_authority", "to_code"], "edge")):
        data = plot / ".data" / f"{name}.parquet"
        frame.to_parquet(data, index=False)
        (plot / ".envelopes" / f"{name}.envelope.json").write_text(json.dumps({
            "data": {"path": str(data), "format": "parquet"},
            "metadata": {"semantic_type": semantic_type, "data_category": "tabular",
                         "crs": None, "id_fields": key, "spatial_unit": unit},
            "provenance": [], "warnings": []}))
    return plot


def chosen(tmp_path, places=None):
    _vocab, loam, report = open_plot("demo", root=REPO, directory=a_plot(tmp_path, places))
    if not report["graph"]["plot_places"]["made"]:
        return None, report["graph"]["plot_places"]
    rows = loam.con.execute(
        "SELECT name, included_by FROM plot_places ORDER BY name").fetchall()
    return dict(rows), report["graph"]["plot_places"]


def key(code, authority=GEOID, **rule):
    return {"authority": authority, "code": code, **rule}


# ── what a plot answers for ───────────────────────────────────────────────
def test_a_plot_that_declares_no_places_answers_for_its_whole_graph(tmp_path):
    rows, report = chosen(tmp_path)
    assert len(rows) == len(PLACES) and report["declared"] is False
    assert all("manifest declares none" in why for why in rows.values())


def test_one_place_declared_alone(tmp_path):
    rows, _ = chosen(tmp_path, [key("2300560545")])
    assert rows == {"Portland city": "declared"}


def test_a_place_with_what_it_contains_follows_contains_edges_down(tmp_path):
    rows, _ = chosen(tmp_path, [key("23", **{"with": "contained"})])
    assert set(rows) == {"Maine", "Cumberland County", "Hancock County", "Portland city",
                         "Falmouth town", "Bar Harbor town"}
    assert rows["Maine"] == "declared, with what it contains"
    assert rows["Portland city"] == "contained in us_census_geoid 23"


def test_a_district_with_what_it_touches(tmp_path):
    rows, _ = chosen(tmp_path, [key("23118", SLDL, **{"with": "touching"})])
    assert rows == {"House District 118": "declared, with what it overlaps",
                    "Portland city": "touching us_census_sldl 23118",
                    "Falmouth town": "touching us_census_sldl 23118"}


def test_entries_combine_and_a_place_keeps_every_reason(tmp_path):
    rows, report = chosen(tmp_path, [key("2300560545"),
                                     key("23005", **{"with": "contained"}),
                                     key("23118", SLDL, **{"with": "touching"})])
    assert report["entries"] == 3
    assert rows["Portland city"] == ("contained in us_census_geoid 23005; declared; "
                                     "touching us_census_sldl 23118")
    assert "Bar Harbor town" not in rows and "House District 14" not in rows


def test_the_one_parser_carries_the_declaration(tmp_path):
    plot = a_plot(tmp_path, [key("23005", **{"with": "contained"})])
    assert parse_manifest(plot / "manifest.yml").places == [
        {"authority": GEOID, "code": "23005", "with": "contained"}]
    assert parse_manifest(a_plot(tmp_path / "other").joinpath("manifest.yml")).places is None


# ── refusals, by name ─────────────────────────────────────────────────────
def test_a_key_the_graph_does_not_hold_is_refused_by_name(tmp_path):
    rows, report = chosen(tmp_path, [key("2300560545"), key("23999")])
    assert rows is None
    assert report["why"] == "us_census_geoid 23999 is not a place in this plot's graph"


def test_an_entry_of_another_shape_is_refused_by_name(tmp_path):
    rows, report = chosen(tmp_path, [key("23005", **{"with": "near"}), "Portland",
                                     {"authority": GEOID, "code": "23", "name": "Maine"}])
    assert rows is None
    assert "places[0] says with: 'near'" in report["why"]
    assert "places[1] is not a place key" in report["why"]
    assert "places[2] carries name" in report["why"]


def test_an_empty_declaration_is_refused(tmp_path):
    rows, report = chosen(tmp_path, [])
    assert rows is None and "non-empty list" in report["why"]


def test_deleting_and_rebuilding_loam_gives_the_same_plot_places(tmp_path):
    plot = a_plot(tmp_path, [key("23005", **{"with": "contained"})])
    query = "SELECT * FROM plot_places ORDER BY authority, code"
    _vocab, loam, _ = open_plot("demo", root=REPO, directory=plot)
    before = loam.con.execute(query).fetchall()
    loam.con.close()
    (plot / ".loam" / "loam.duckdb").unlink()
    _vocab, again, _ = open_plot("demo", root=REPO, directory=plot)
    assert again.con.execute(query).fetchall() == before
