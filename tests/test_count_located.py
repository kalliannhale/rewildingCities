"""tests for soil/transform/count_located.py (Sprint 06, step 3, D-209;
one layer, named in the receipt, D-224; boundary_vintage, D-231; a tribal
area counted only beside its note, D-233)."""

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
       "derivation": {"kind": "located_count", "counts": "library_outlet",
                      "denominator": "persons", "scale": 1000.0}}
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


def _edges(rows, vintage="2024"):
    return pd.DataFrame([{"from_authority": "libs", "from_code": f, "to_authority": a,
                          "to_code": c, "kind": "located_in", "vintage": vintage}
                         for f, a, c in rows])


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


def test_a_tribal_area_is_never_counted_without_its_note():
    with pytest.raises(cl.CountRefused, match="only beside a note"):
        _count(levels=LEVELS + ["aiannh"])


def test_edges_from_two_layers_are_refused():
    mixed = pd.concat([EDGES, EDGES.assign(from_authority="schools")], ignore_index=True)
    with pytest.raises(cl.CountRefused, match="one layer"):
        _count(edges=mixed)


def test_no_edges_at_all_are_refused():
    with pytest.raises(cl.CountRefused, match="no layer"):
        _count(edges=EDGES.iloc[0:0])


def test_the_receipt_names_the_layer_counted():
    out = _count().reset_index()
    assert cl.output_metadata(out, cl.counted_layer(EDGES))["counted_layer"] == "libs"
    assert "counted_layer" not in cl.output_metadata(out)


def test_only_a_located_count_is_counted():
    with pytest.raises(cl.CountRefused, match="not a located_count"):
        _count(ind={"id": "x", "derivation": {"kind": "ratio"}})


# ── which boundaries a count sits on (D-231) ──────────────────────────────
def test_every_row_carries_its_levels_edge_vintage_zeros_included():
    out = _count()
    assert set(out["boundary_vintage"]) == {"2024"}
    assert out.loc[("us_census_geoid", "2300100002"), "boundary_vintage"] == "2024"


def test_time_is_written_as_given_and_never_read_for_boundaries():
    out = cl.count(EDGES, SPINE, PLACES, IND, LEVELS, "2026-11-14", "rewildingcities")
    assert set(out["time"]) == {"2026-11-14"} and set(out["boundary_vintage"]) == {"2024"}


def test_a_level_whose_edges_carry_two_vintages_is_refused():
    mixed = pd.concat([EDGES, _edges([("L2", "us_census_geoid", "2300100002")], vintage="2020")],
                      ignore_index=True)
    with pytest.raises(cl.CountRefused, match="cousub places carry vintages 2020, 2024"):
        _count(edges=mixed)


def test_a_level_no_edge_reaches_takes_its_places_vintage():
    places = PLACES.assign(vintage="2024")
    out = cl.count(EDGES[EDGES["to_authority"] != "us_census_sldu"], SPINE, places, IND,
                   LEVELS, "FY 2024", "rewildingcities").set_index(["unit_authority", "unit_code"])
    assert out.loc[("us_census_sldu", "23001"), "count"] == 0
    assert out.loc[("us_census_sldu", "23001"), "boundary_vintage"] == "2024"
    assert cl.levels_without_edges(EDGES[EDGES["to_authority"] != "us_census_sldu"],
                                   places, LEVELS) == ["sldu"]


def test_a_level_no_edge_reaches_whose_places_carry_no_vintage_is_refused():
    with pytest.raises(cl.CountRefused, match="no edge reaches a sldu place"):
        _count(edges=EDGES[EDGES["to_authority"] != "us_census_sldu"])


def test_edges_without_a_vintage_are_refused():
    with pytest.raises(cl.CountRefused, match="carry no vintage"):
        _count(edges=EDGES.drop(columns=["vintage"]))
    with pytest.raises(cl.CountRefused, match="carries no vintage"):
        _count(edges=EDGES.assign(vintage=None))


# ── a tribal area, counted beside its note (D-233) ────────────────────────
T_SPINE = pd.concat([SPINE.assign(aiannh=None, aiannh_comptyp=None), pd.DataFrame([
    {"GEOID": "b4", "county": "23019", "cousub": "2301900004", "sldl": "23002", "sldu": "23002",
     "aiannh": "2760", "aiannh_comptyp": "R", "persons": 370, "households": 150},
    {"GEOID": "b5", "county": "23019", "cousub": "2301900004", "sldl": "23002", "sldu": "23002",
     "aiannh": "2760", "aiannh_comptyp": "T", "persons": 30, "households": 10}])],
    ignore_index=True)
T_PLACES = pd.concat([PLACES, pd.DataFrame([
    {"authority": "us_census_aiannh", "code": "2760R", "level": "aiannh", "name": "Reservation"},
    {"authority": "us_census_aiannh", "code": "2760T", "level": "aiannh", "name": "Trust land"}])],
    ignore_index=True)


def _tribal(edges=EDGES, note="carrier_unseen_on_nations_land"):
    return cl.count(edges, T_SPINE, T_PLACES.assign(vintage="2020"), IND, ["state", "aiannh"],
                    "FY 2024", "rewildingcities", note).set_index(["unit_authority", "unit_code"])


def test_every_tribal_row_carries_the_note_and_no_other_row_does():
    out = _tribal()
    tribal = out.loc["us_census_aiannh"]
    assert set(tribal["context_note"]) == {"carrier_unseen_on_nations_land"}
    assert pd.isna(out.loc[("us_census_geoid", "23"), "context_note"])


def test_a_reservation_and_trust_land_are_two_places_with_their_own_persons():
    out = _tribal()
    assert out.loc[("us_census_aiannh", "2760R"), "households"] == 370
    assert out.loc[("us_census_aiannh", "2760T"), "households"] == 30


def test_a_point_on_a_reservation_counts_there():
    edges = pd.concat([EDGES, _edges([("L1", "us_census_aiannh", "2760R")], vintage="2020")],
                      ignore_index=True)
    out = _tribal(edges=edges)
    assert out.loc[("us_census_aiannh", "2760R"), "count"] == 1
    assert out.loc[("us_census_aiannh", "2760R"), "boundary_vintage"] == "2020"
    assert out.loc[("us_census_aiannh", "2760T"), "count"] == 0


def test_with_no_point_on_any_tribal_area_the_zeros_sit_on_its_places_vintage():
    out = _tribal()
    assert set(out.loc["us_census_aiannh"]["boundary_vintage"]) == {"2020"}
    assert set(out.loc["us_census_aiannh"]["count"]) == {0}


def test_a_note_with_no_tribal_level_is_refused():
    with pytest.raises(cl.CountRefused, match="no tribal level"):
        cl.count(EDGES, SPINE, PLACES, IND, LEVELS, "FY 2024", "rewildingcities", "x")
