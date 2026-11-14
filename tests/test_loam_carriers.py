"""
tests/test_loam_carriers.py  |  rewildingCities, Sprint 06 (CMAP-1, D-225)

Two more views in a plot's bed, over the files its receipts point at, never
copies (D-168). located_in: every located_in_edges receipt unioned, each row
naming its receipt (LOC-VIEW-1). carriers: one row per placed point of every
located_count carrier (D-223), its points found the way the orchestrator
checks them before a run (D-224): the edges receipt's own record reads one
input of the counted type, and that input's path is the points file. These
read the repo's real seeds; the plot is built in a temporary folder.
"""

import json
from pathlib import Path

import pandas as pd
import yaml

from canopy.wonder.session import open_plot

REPO = Path(__file__).resolve().parents[1]
EDGE_KEY = ["from_authority", "from_code", "to_authority", "to_code"]
POINTS = [("L1", "ACTON PUBLIC LIBRARY", -70.909, 43.532),
          ("L2", "MAYHEW LIBRARY ASSN", -67.744, 44.619),
          ("L3", "A LIBRARY THE EDGES NEVER PLACED", -69.440, 44.532)]
EDGES = [("L1", "us_census_geoid", "23"), ("L1", "us_census_geoid", "23001"),
         ("L2", "us_census_geoid", "23")]


def a_plot(tmp_path):
    plot = tmp_path / "plots" / "demo"
    (plot / ".data").mkdir(parents=True)
    (plot / ".envelopes").mkdir()
    (plot / "manifest.yml").write_text(yaml.safe_dump({
        "city": {"id": "demo", "name": "demo"}, "crs": {"working": "EPSG:4326"},
        "datasets": {}}))
    return plot


def some_points(plot, name="libraries_points_points", named=True):
    data = plot / ".data" / f"{name}.geojson"
    features = [{"type": "Feature",
                 "geometry": {"type": "Point", "coordinates": [lon, lat]},
                 "properties": {"feature_id": fid, **({"name": label} if named else {})}}
                for fid, label, lon, lat in POINTS]
    data.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    (plot / ".envelopes" / f"{name}.envelope.json").write_text(json.dumps({
        "data": {"path": str(data), "format": "geojson"},
        "metadata": {"semantic_type": "library_outlet", "data_category": "vector",
                     "crs": "EPSG:4326", "feature_count": len(features),
                     "geometry_type": "Point", "bbox": [-70.909, 43.532, -67.744, 44.619],
                     "total_area_m2": 0.0, "id_field": "feature_id",
                     "spatial_unit": "library_outlet"},
        "provenance": [], "warnings": []}))
    return data


def some_edges(plot, points, name="libraries_located_in_edges", layer="libs",
               points_type="library_outlet"):
    data = plot / ".data" / f"{name}.parquet"
    frame = pd.DataFrame([{"from_authority": layer, "from_code": f, "to_authority": a,
                           "to_code": c, "kind": "located_in", "weight_population": 1.0,
                           "weight_households": 1.0} for f, a, c in EDGES])
    frame.to_parquet(data, index=False)
    record = {"primitive": "build_located_in", "version": "1.0.0",
              "timestamp": "2026-11-14T00:00:00Z", "params": {}, "duration_seconds": 0.1,
              "inputs": [{"name": "points", "semantic_type": points_type, "path": str(points),
                          "hash": {"value": None, "method": "skipped"}}]}
    (plot / ".envelopes" / f"{name}.envelope.json").write_text(json.dumps({
        "data": {"path": str(data), "format": "parquet"},
        "metadata": {"semantic_type": "located_in_edges", "data_category": "tabular",
                     "crs": None, "row_count": len(frame), "variables": list(frame.columns),
                     "id_fields": EDGE_KEY, "spatial_unit": "edge"},
        "provenance": [record], "warnings": []}))
    return data


def opened(plot):
    _vocab, loam, report = open_plot("demo", root=REPO, directory=plot)
    return loam, report["graph"]


def test_located_in_is_a_view_over_the_edges_naming_its_receipt(tmp_path):
    plot = a_plot(tmp_path)
    some_edges(plot, some_points(plot))
    loam, graph = opened(plot)
    assert graph["located_in"]["made"] and graph["located_in"]["rows"] == len(EDGES)
    assert graph["located_in"]["layers"] == ["libs"]
    receipts = {r[0] for r in loam.con.execute("SELECT edges_receipt FROM located_in").fetchall()}
    assert receipts == {"libraries_located_in_edges.envelope.json"}


def test_carriers_names_each_placed_point_with_its_layer(tmp_path):
    plot = a_plot(tmp_path)
    some_edges(plot, some_points(plot))
    loam, graph = opened(plot)
    assert graph["carriers"]["made"], graph["carriers"]
    rows = loam.con.execute("SELECT indicator, counts, layer, feature_id, name, longitude "
                            "FROM carriers ORDER BY feature_id").fetchall()
    assert rows == [("library_outlets_per_1000", "library_outlet", "libs", "L1",
                     "ACTON PUBLIC LIBRARY", -70.909),
                    ("library_outlets_per_1000", "library_outlet", "libs", "L2",
                     "MAYHEW LIBRARY ASSN", -67.744)]


def test_a_carriers_places_are_its_rows_in_located_in(tmp_path):
    plot = a_plot(tmp_path)
    some_edges(plot, some_points(plot))
    loam, _ = opened(plot)
    places = loam.con.execute(
        "SELECT e.to_code FROM carriers c JOIN located_in e "
        "ON e.from_authority = c.layer AND e.from_code = c.feature_id "
        "WHERE c.name = 'ACTON PUBLIC LIBRARY' ORDER BY e.to_code").fetchall()
    assert places == [("23",), ("23001",)]


def test_one_layer_in_two_receipts_makes_no_located_in_view(tmp_path):
    plot = a_plot(tmp_path)
    points = some_points(plot)
    some_edges(plot, points)
    some_edges(plot, points, name="older_located_in_edges")
    _, graph = opened(plot)
    why = graph["located_in"]["why"]
    assert not graph["located_in"]["made"] and "libs" in why and "older_located_in_edges" in why
    assert not graph["carriers"]["made"]


def test_edges_made_from_other_points_leave_the_carrier_out(tmp_path):
    plot = a_plot(tmp_path)
    some_edges(plot, some_points(plot), points_type="governance_unit")
    _, graph = opened(plot)
    assert graph["located_in"]["made"] and not graph["carriers"]["made"]
    assert "library_outlet" in graph["carriers"]["left_out"]["library_outlets_per_1000"]


def test_points_without_a_name_leave_the_carrier_out(tmp_path):
    plot = a_plot(tmp_path)
    some_edges(plot, some_points(plot, named=False))
    _, graph = opened(plot)
    assert not graph["carriers"]["made"]
    assert "'name'" in graph["carriers"]["left_out"]["library_outlets_per_1000"]


def test_a_plot_with_no_edges_has_neither_view_and_says_why(tmp_path):
    plot = a_plot(tmp_path)
    some_points(plot)
    _, graph = opened(plot)
    assert "has made located_in_edges" in graph["located_in"]["why"]
    assert "no located_in view" in graph["carriers"]["why"]
