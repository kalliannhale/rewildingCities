"""
tests/test_loam_graph.py  |  rewildingCities, Sprint 05 change 6 (plan build 1)

Loam holds its plot's part of the weighted graph as two views, places and
edges, over the files its receipts point at, never as copies (D-168). The
plan's rebuild test: deleting and rebuilding the bed gives the same places
and edges. A view is made only from exactly one receipt that declares its key
(KEYS-1) over a file carrying that key; otherwise the plot still opens and the
report says why. A snapshot of the bed carries no graph values, since the
gate never sees it.
"""

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from canopy.wonder.session import open_plot

REPO = Path(__file__).resolve().parents[1]

PLACES = pd.DataFrame([
    {"authority": "us_census_geoid", "code": "23", "level": "state", "name": "Maine"},
    {"authority": "us_census_geoid", "code": "23005", "level": "county", "name": "Cumberland"},
    {"authority": "us_census_geoid", "code": "2300560545", "level": "cousub", "name": "Portland"},
    {"authority": "us_census_sldl", "code": "23118", "level": "sldl", "name": "House District 118"},
])
EDGES = pd.DataFrame([
    {"from_authority": "us_census_geoid", "from_code": "23", "to_authority": "us_census_geoid",
     "to_code": "23005", "kind": "contains", "weight_population": 1.0, "weight_households": 1.0},
    {"from_authority": "us_census_geoid", "from_code": "2300560545",
     "to_authority": "us_census_sldl", "to_code": "23118", "kind": "overlaps",
     "weight_population": 0.25, "weight_households": 0.24},
])
PLACES_KEY = ["authority", "code"]
EDGES_KEY = ["from_authority", "from_code", "to_authority", "to_code"]


def a_plot(tmp_path):
    plot = tmp_path / "plots" / "demo"
    (plot / ".data").mkdir(parents=True)
    (plot / ".envelopes").mkdir()
    (plot / "manifest.yml").write_text(yaml.safe_dump({
        "city": {"id": "demo", "name": "demo"}, "crs": {"working": "EPSG:4326"},
        "datasets": {}}))
    return plot


def a_receipt(plot, name, frame, semantic_type, key, unit):
    data = plot / ".data" / f"{name}.parquet"
    frame.to_parquet(data, index=False)
    metadata = {"semantic_type": semantic_type, "data_category": "tabular", "crs": None,
                "row_count": len(frame), "variables": list(frame.columns)}
    if key:
        metadata.update({"id_fields": key, "spatial_unit": unit})
    (plot / ".envelopes" / f"{name}.envelope.json").write_text(json.dumps({
        "data": {"path": str(data), "format": "parquet"}, "metadata": metadata,
        "provenance": [], "warnings": []}))
    return data


def a_graph(plot):
    a_receipt(plot, "graph_places_places", PLACES, "places", PLACES_KEY, "place")
    a_receipt(plot, "graph_edges_edges", EDGES, "place_edges", EDGES_KEY, "edge")


def opened(plot):
    return open_plot("demo", root=REPO, directory=plot)


def rows(loam, view, key):
    return loam.con.execute(f"SELECT * FROM {view} ORDER BY {', '.join(key)}").fetchall()


# ── the views ─────────────────────────────────────────────────────────────
def test_places_and_edges_are_views_over_the_receipts_files(tmp_path):
    plot = a_plot(tmp_path)
    a_graph(plot)
    _vocab, loam, report = opened(plot)
    assert report["graph"]["places"]["made"] and report["graph"]["edges"]["made"]
    assert report["graph"]["places"]["rows"] == 4 and report["graph"]["edges"]["rows"] == 2
    kinds = {r[0]: r[1] for r in loam.con.execute(
        "SELECT table_name, table_type FROM information_schema.tables "
        "WHERE table_name IN ('places', 'edges')").fetchall()}
    assert kinds == {"places": "VIEW", "edges": "VIEW"}
    share = loam.con.execute(
        "SELECT e.weight_population FROM edges e JOIN places p "
        "ON p.authority = e.to_authority AND p.code = e.to_code "
        "WHERE p.name = 'House District 118'").fetchone()[0]
    assert share == 0.25


def test_deleting_and_rebuilding_loam_gives_the_same_places_and_edges(tmp_path):
    plot = a_plot(tmp_path)
    a_graph(plot)
    _vocab, loam, _ = opened(plot)
    before = (rows(loam, "places", PLACES_KEY), rows(loam, "edges", EDGES_KEY),
              loam.con.execute("SELECT * EXCLUDE (created_at) FROM loam ORDER BY name").fetchall())
    loam.con.close()
    (plot / ".loam" / "loam.duckdb").unlink()
    _vocab, again, _ = opened(plot)
    after = (rows(again, "places", PLACES_KEY), rows(again, "edges", EDGES_KEY),
             again.con.execute("SELECT * EXCLUDE (created_at) FROM loam ORDER BY name").fetchall())
    assert before == after


def test_a_snapshot_of_the_bed_carries_no_graph_values(tmp_path):
    plot = a_plot(tmp_path)
    a_graph(plot)
    _vocab, loam, _ = opened(plot)
    snap = pd.read_parquet(loam.snapshot(str(tmp_path / "snapshot.parquet")))
    assert "authority" not in snap.columns and "weight_population" not in snap.columns
    assert len(snap) == loam.count(plot="demo")


# ── no view, and the report says why ──────────────────────────────────────
def test_a_plot_with_no_graph_opens_and_says_so(tmp_path):
    plot = a_plot(tmp_path)
    _vocab, loam, report = opened(plot)
    assert not report["graph"]["places"]["made"]
    assert "no run in plot 'demo' has made places" in report["graph"]["places"]["why"]
    with pytest.raises(Exception):
        loam.con.execute("SELECT * FROM places")


def test_two_places_tables_make_no_view(tmp_path):
    plot = a_plot(tmp_path)
    a_graph(plot)
    a_receipt(plot, "older_places_places", PLACES, "places", PLACES_KEY, "place")
    _vocab, _loam, report = opened(plot)
    why = report["graph"]["places"]["why"]
    assert "graph_places_places.envelope.json" in why and "older_places_places.envelope.json" in why
    assert report["graph"]["edges"]["made"]


def test_a_receipt_that_declares_no_key_makes_no_view(tmp_path):
    plot = a_plot(tmp_path)
    a_receipt(plot, "graph_places_places", PLACES, "places", None, None)
    _vocab, _loam, report = opened(plot)
    assert "declares no key" in report["graph"]["places"]["why"]


def test_a_declared_key_missing_from_the_file_makes_no_view(tmp_path):
    plot = a_plot(tmp_path)
    a_receipt(plot, "graph_places_places", PLACES.drop(columns=["code"]), "places",
              PLACES_KEY, "place")
    _vocab, _loam, report = opened(plot)
    assert "has no code" in report["graph"]["places"]["why"]


def test_a_receipt_whose_file_is_gone_makes_no_view(tmp_path):
    plot = a_plot(tmp_path)
    a_receipt(plot, "graph_places_places", PLACES, "places", PLACES_KEY, "place").unlink()
    _vocab, _loam, report = opened(plot)
    assert "not on disk" in report["graph"]["places"]["why"]
