"""tests for soil/transform/build_located_in.py (Sprint 06, step 2)."""

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "build_located_in", ROOT / "soil" / "transform" / "build_located_in.py")
li = importlib.util.module_from_spec(_spec)
sys.modules["build_located_in"] = li   # a dataclass needs its module registered
_spec.loader.exec_module(li)

V = {"state": "2024", "county": "2024", "town": "2024", "sldl": "2024", "sldu": "2024",
     "aiannh": "2020", "division": "MEGIS METWP24P"}
SPINE = pd.DataFrame([
    {"block": "B1", "town": "2301360545", "sldl": "23118", "sldu": "23009", "aiannh": None},
    {"block": "B2", "town": "2301360545", "sldl": "23119", "sldu": "23009", "aiannh": "2760R"},
    {"block": "B3", "town": "2301399999", "sldl": "23118", "sldu": "23010", "aiannh": None}])
DIVS = pd.DataFrame([{"block": "B1", "division": "1001"}])
PLACES = pd.DataFrame([{"authority": a, "code": c} for a, c in [
    ("us_census_geoid", "23"), ("us_census_geoid", "23013"),
    ("us_census_geoid", "2301360545"), ("us_census_geoid", "2301399999"),
    ("us_census_sldl", "23118"), ("us_census_sldl", "23119"),
    ("us_census_sldu", "23009"), ("us_census_sldu", "23010"),
    ("us_census_aiannh", "2760R"), ("megis", "1001")]])


def _points(rows):
    return pd.DataFrame(rows, columns=["layer", "feature_id", "block", "town", "county"])


def _locate(points, places=PLACES):
    return li.locate(points, SPINE, DIVS, places, V, "test")


def _to(edges, fid):
    e = edges[edges.from_code == fid]
    return set(zip(e.to_authority, e.to_code))


def test_a_point_reaches_every_area_it_falls_in_with_weights_one():
    p = _locate(_points([("libs", "L1", "B1", "2301360545", "23013")]))
    assert _to(p.edges, "L1") == {("us_census_geoid", "23"), ("us_census_geoid", "23013"),
                                  ("us_census_geoid", "2301360545"), ("us_census_sldl", "23118"),
                                  ("us_census_sldu", "23009"), ("megis", "1001")}
    assert set(p.edges.kind) == {"located_in"}
    assert (p.edges.weight_population == 1).all() and (p.edges.weight_households == 1).all()


def test_a_point_counts_in_its_house_and_its_senate_district():
    p = _locate(_points([("libs", "L1", "B1", "2301360545", "23013")]))
    to = _to(p.edges, "L1")
    assert ("us_census_sldl", "23118") in to and ("us_census_sldu", "23009") in to


def test_a_point_names_its_tribal_area_from_its_block():
    p = _locate(_points([("libs", "L2", "B2", "2301360545", "23013")]))
    assert ("us_census_aiannh", "2760R") in _to(p.edges, "L2")


def test_town_comes_from_the_face_and_a_split_block_is_listed():
    p = _locate(_points([("libs", "L3", "B3", "2301360545", "23013")]))
    assert ("us_census_geoid", "2301360545") in _to(p.edges, "L3")
    assert ("us_census_geoid", "2301399999") not in _to(p.edges, "L3")
    assert p.split == [{"layer": "libs", "feature_id": "L3", "block": "B3",
                        "face_town": "2301360545", "block_town": "2301399999"}]
    assert ("us_census_sldu", "23010") in _to(p.edges, "L3")


def test_a_point_in_no_face_is_listed_never_dropped_or_guessed():
    p = _locate(_points([("libs", "L4", None, None, None), ("libs", "L5", "B9", "x", "y")]))
    assert p.edges.empty
    assert [u["feature_id"] for u in p.unplaced] == ["L4", "L5"]
    assert "not in the spine" in p.unplaced[1]["why"]


def test_a_feature_id_twice_in_a_layer_is_refused():
    with pytest.raises(li.LocatedInRefused, match="used twice"):
        _locate(_points([("libs", "L1", "B1", "2301360545", "23013"),
                         ("libs", "L1", "B2", "2301360545", "23013")]))


def test_the_same_id_in_two_layers_is_two_points():
    p = _locate(_points([("libs", "1", "B1", "2301360545", "23013"),
                         ("schools", "1", "B1", "2301360545", "23013")]))
    assert set(p.edges.from_authority) == {"libs", "schools"}


def test_an_edge_to_a_place_not_in_places_is_refused():
    with pytest.raises(li.LocatedInRefused, match="not in places"):
        _locate(_points([("libs", "L1", "B1", "2301360545", "23013")]),
                places=PLACES[PLACES.code != "23118"])


def test_every_level_carries_its_own_vintage():
    p = _locate(_points([("libs", "L2", "B2", "2301360545", "23013")]))
    v = dict(zip(p.edges.to_authority + ":" + p.edges.to_code, p.edges.vintage))
    assert v["us_census_aiannh:2760R"] == "2020"
    assert v["us_census_sldl:23119"] == "2024"


def test_the_receipt_lists_unplaced_and_split_points():
    p = _locate(_points([("libs", "L3", "B3", "2301360545", "23013"),
                         ("libs", "L4", None, None, None)]))
    meta = li.output_metadata(p)
    assert meta["id_fields"] == li.KEY
    assert [u["feature_id"] for u in meta["unplaced"]] == ["L4"]
    assert [s["feature_id"] for s in meta["split_block_points"]] == ["L3"]


def test_a_listed_reason_travels_with_an_unplaced_point():
    pts = _points([("libs", "L6", None, None, None)]).assign(
        why_unplaced=["the feature has no usable coordinates"])
    p = _locate(pts)
    assert p.unplaced[0]["why"] == "the feature has no usable coordinates"


def test_the_spine_is_read_in_its_own_words():
    spine = pd.DataFrame([{"GEOID": "B1", "cousub": "2301360545", "sldl": "23118",
                           "sldu": "23009", "aiannh": "2760", "aiannh_comptyp": "T"},
                          {"GEOID": "B2", "cousub": "2301360545", "sldl": "23118",
                           "sldu": "23009", "aiannh": None, "aiannh_comptyp": None}])
    t = li.spine_table(spine)
    assert list(t.columns) == ["block", "town", "sldl", "sldu", "aiannh"]
    assert t.loc[0, "aiannh"] == "2760T"
    assert pd.isna(t.loc[1, "aiannh"])


def test_points_and_faces_meet_by_geometry():
    gpd = pytest.importorskip("geopandas")
    from shapely.geometry import Point, box
    faces = gpd.GeoDataFrame(
        {"block": ["B1", "B3"], "town": ["2301360545", "2301399999"],
         "county": ["23013", "23013"]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)], crs="EPSG:4269")
    points = gpd.GeoDataFrame(
        {"feature_id": ["in", "line", "out", "none"]},
        geometry=[Point(0.5, 0.5), Point(1.0, 0.5), Point(5, 5), None], crs="EPSG:4269")
    got = li.faces_for_points(points, faces, "libs").set_index("feature_id")
    assert got.loc["in", "block"] == "B1"
    assert "on a line between faces" in got.loc["line", "why_unplaced"]
    assert pd.isna(got.loc["out", "block"]) and pd.isna(got.loc["out", "why_unplaced"])
    assert "no usable coordinates" in got.loc["none", "why_unplaced"]


def test_the_publishers_block_is_checked_never_used():
    located = pd.DataFrame([{"feature_id": "a", "block": "B1"}, {"feature_id": "b", "block": "B2"},
                            {"feature_id": "c", "block": None}])
    points = pd.DataFrame({"feature_id": ["a", "b", "c"],
                           "declared_block": ["B1", "B9", "B3"]})
    check = li.block_check(located, points, "cenblock")
    assert (check["checked"], check["agree"]) == (2, 1)
    assert check["disagree"] == [{"feature_id": "b", "ours": "B2", "theirs": "B9"}]
