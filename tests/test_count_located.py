"""tests for soil/transform/count_located.py (Sprint 06, step 3, D-209)."""

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "count_located", ROOT / "soil" / "transform" / "count_located.py")
cl = importlib.util.module_from_spec(_spec)
sys.modules["count_located"] = cl
_spec.loader.exec_module(cl)

IND = {"id": "library_outlets_per_1000",
       "derivation": {"kind": "located_count", "layer": "libs", "denominator": "persons",
                      "scale": 1000.0}}
SPINE = pd.DataFrame([
    {"GEOID": "b1", "county": "23001", "cousub": "2300100001", "sldl": "23001", "sldu": "23001", "persons": 1500, "households": 600},
    {"GEOID": "b2", "county": "23001", "cousub": "2300100002", "sldl": "23001", "sldu": "23002", "persons": 500, "households": 200},
    {"GEOID": "b3", "county": "23003", "cousub": "2300300003", "sldl": "23002", "sldu": "23002", "persons": 0, "households": 0}])
PLACES = pd.DataFrame([{"authority": a, "code": c, "level": l, "name": n} for a, c, l, n in [
    ("us_census_geoid", "23", "state", "Maine"),
    ("us_census_geoid", "23001", "county", "A County"), ("us_census_geoid", "23003", "county", "C County"),
    ("us_census_geoid", "2300100001", "cousub", "One"), ("us_census_geoid", "2300100002", "cousub", "Two"),
    ("us_census_geoid", "2300300003", "cousub", "Empty"),
    ("us_census_sldl", "23001", "sldl", "House 1"), ("us_census_sldl", "23002", "sldl", "House 2"),
    ("us_census_sldu", "23001", "sldu", "Senate 1"), ("us_census_sldu", "23002", "sldu", "Senate 2")]])


def _edges(rows):
    return pd.DataFrame([{"from_authority": "libs", "from_code": f, "to_authority": a,
                          "to_code": c, "kind": "located_in"} for f, a, c in rows])


EDGES = _edges([("L1", "us_census_geoid", "23"), ("L1", "us_census_geoid", "23001"),
                ("L1", "us_census_geoid", "2300100001"), ("L1", "us_census_sldl", "23001"),
                ("L1", "us_census_sldu", "23001")])
LEVELS = ["state", "county", "cousub", "sldl", "sldu"]


def _count(edges=EDGES, levels=LEVELS, ind=IND):
    return cl.count(edges, SPINE, PLACES, ind, levels, "FY 2024", "rewildingcities").set_index(
        ["unit_authority", "unit_code"])


def test_a_point_counts_in_every_place_it_stands_in():
    out = _count()
    for key in [("us_census_geoid", "23"), ("us_census_geoid", "2300100001"),
                ("us_census_sldl", "23001"), ("us_census_sldu", "23001")]:
        assert out.loc[key, "count"] == 1


def test_the_rate_is_per_the_places_own_persons():
    out = _count()
    assert out.loc[("us_census_geoid", "2300100001"), "value"] == pytest.approx(1 / 1500 * 1000)
    assert out.loc[("us_census_geoid", "23001"), "households"] == 2000
    assert out.loc[("us_census_geoid", "23001"), "households_counts"] == "persons"


def test_a_place_with_none_here_gets_a_zero_row():
    out = _count()
    assert out.loc[("us_census_geoid", "2300100002"), "count"] == 0
    assert out.loc[("us_census_geoid", "2300100002"), "value"] == 0


def test_a_place_with_no_people_has_no_rate():
    out = _count()
    row = out.loc[("us_census_geoid", "2300300003")]
    assert pd.isna(row["value"]) and row["empty_reason"] == "zero_population"


def test_rows_carry_the_value_key_and_the_publisher():
    out = _count().reset_index()
    assert set(cl.KEY) <= set(out.columns)
    assert set(out["published_by"]) == {"rewildingcities"}
    assert len(out) == len(PLACES)


def test_a_tribal_area_is_never_counted():
    with pytest.raises(cl.CountRefused, match="TRIBE-7"):
        _count(levels=LEVELS + ["aiannh"])


def test_edges_from_another_layer_are_refused():
    bad = EDGES.assign(from_authority="schools")
    with pytest.raises(cl.CountRefused, match="counts libs only"):
        _count(edges=bad)


def test_only_a_located_count_is_counted():
    with pytest.raises(cl.CountRefused, match="not a located_count"):
        _count(ind={"id": "x", "derivation": {"kind": "ratio"}})
