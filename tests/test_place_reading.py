"""
tests/test_place_reading.py  |  rewildingCities, Sprint 05 change 12 (plan builds 4 and 5)

wonder reads a district through its edges (D-184): its own ACS value, never
one made from its towns (Contract 3 rule 1); every town that touches it with
its shares (MP-76); and their range per indicator (rule 3). A town with none
of a value's universe here is listed and kept out of the range (D-180); a
value on other boundaries stays out, named; a statistical area and a small
sample enter, and the range's ends say what they rest on (D-183); a
contained universe shows no share (D-182); towns wholly inside are ranged
apart from towns the line splits, a split town always says how much of it
is here and of how many, and the firm range is the towns wholly here on a
sound sample (D-183, D-185). A range whose ends are one says so once.
"""

import json
from pathlib import Path

import pandas as pd
import yaml

from canopy.wonder.place import read_place, say_place
from canopy.wonder.session import open_plot

REPO = Path(__file__).resolve().parents[1]
ACS = "2020-2024 (5-year estimates)"
DISTRICT = ("us_census_sldl", "23009")
RENTERS = "renter households with rent burden computed"


def town(code, name, kind="town", funcstat="A"):
    return {"authority": "us_census_geoid", "code": code, "level": "cousub", "vintage": "2024",
            "kind": kind, "name": name, "census_funcstat": funcstat, "context_note": None}


PLACES = pd.DataFrame([
    {"authority": "us_census_sldl", "code": "23009", "level": "sldl", "vintage": "2024",
     "kind": "house_district", "name": "State House District 9 (2024); Maine",
     "census_funcstat": None, "context_note": None},
    {"authority": "us_census_geoid", "code": "23001", "level": "county", "vintage": "2024",
     "kind": "county", "name": "Example County", "census_funcstat": None, "context_note": None},
    town("2300100001", "Alpha town"),
    town("2300100002", "Beta town"),
    town("2300100003", "Cove Twp", "unorganized_territory", "S"),
    town("2300100004", "Dune gore", "gore"),
    town("2300100005", "Echo plantation", "plantation"),
    town("2300100006", "Fox town"),
    town("2300100007", "Gull Island UT", "unorganized_territory", "S"),
])


def edge(code, population, households, reason=None, to=DISTRICT, kind="overlaps"):
    return {"from_authority": "us_census_geoid", "from_code": code,
            "to_authority": to[0], "to_code": to[1], "kind": kind,
            "weight_population": population, "weight_households": households,
            "weight_reason": reason, "source": "2020 blocks", "vintage": "2024"}


EDGES = pd.DataFrame([
    edge("2300100001", 1.0, 1.0),
    edge("2300100002", 0.4, 0.35),
    edge("2300100003", 1.0, 1.0),
    edge("2300100004", 0.0, None, "zero_households"),
    edge("2300100005", 0.3, 0.3),
    edge("2300100006", 0.015, 0.02),
    edge("2300100007", 1.0, 1.0),
])
COUNTY_EDGES = pd.DataFrame([
    {**edge("x", 1.0, 1.0), "from_authority": "us_census_geoid", "from_code": "23001",
     "to_authority": "us_census_geoid", "to_code": c, "kind": "contains"}
    for c in ("2300100001", "2300100002")])


def value(authority, code, indicator, v, households=1000.0, counts="households",
          note=None, time=ACS, empty=None):
    return {"measurement_id": f"{indicator}:{authority}:{code}", "unit_authority": authority,
            "unit_code": code, "indicator": indicator, "value": v, "moe": None,
            "moe_status": "not_derived", "households": households,
            "households_counts": counts, "reliability_note": note, "empty_reason": empty,
            "published_by": "us_census_acs", "time": time}


G = "us_census_geoid"
VALUES = pd.DataFrame([
    value(*DISTRICT, "cii_broadband", 79.0, 9000.0),
    value(*DISTRICT, "cii_rent_burden", 28.0, 2000.0, RENTERS),
    value(G, "2300100001", "cii_broadband", 70.0),
    value(G, "2300100002", "cii_broadband", 88.0, 40.0,
          note="rests on fewer than 50 households"),
    value(G, "2300100003", "cii_broadband", 75.0),
    value(G, "2300100004", "cii_broadband", 99.0),
    value(G, "2300100005", "cii_broadband", 50.0, time="2019-2023 (5-year estimates)"),
    value(G, "2300100006", "cii_broadband", 80.0),
    value(G, "2300100007", "cii_broadband", None, 0.0, empty="zero denominator"),
    value(G, "2300100001", "cii_rent_burden", 30.0, 300.0, RENTERS),
    value(G, "2300100002", "cii_rent_burden", 25.0, 12.0, RENTERS),
    value(G, "2300100004", "cii_rent_burden", 60.0, 5.0, RENTERS),
])


def a_receipt(plot, name, frame, semantic_type, metadata=None):
    data = plot / ".data" / f"{name}.parquet"
    frame.to_parquet(data, index=False)
    meta = {"semantic_type": semantic_type, "data_category": "tabular", "crs": None,
            "row_count": len(frame), "variables": list(frame.columns), **(metadata or {})}
    (plot / ".envelopes" / f"{name}.envelope.json").write_text(json.dumps({
        "data": {"path": str(data), "format": "parquet"}, "metadata": meta,
        "provenance": [], "warnings": []}))


def opened(tmp_path):
    plot = tmp_path / "plots" / "demo"
    (plot / ".data").mkdir(parents=True)
    (plot / ".envelopes").mkdir()
    (plot / "manifest.yml").write_text(yaml.safe_dump({
        "city": {"id": "demo", "name": "demo"}, "crs": {"working": "EPSG:4326"},
        "datasets": {}}))
    a_receipt(plot, "graph_places_places", PLACES, "places",
              {"id_fields": ["authority", "code"], "spatial_unit": "place"})
    a_receipt(plot, "graph_edges_edges", pd.concat([EDGES, COUNTY_EDGES], ignore_index=True),
              "place_edges",
              {"id_fields": ["from_authority", "from_code", "to_authority", "to_code", "kind"]})
    a_receipt(plot, "all_derive_values", VALUES, "indicator_values",
              {"id_field": "measurement_id"})
    _vocab, loam, report = open_plot("demo", root=REPO, directory=plot)
    assert report["graph"]["place_values"]["made"], report["graph"]
    return loam


def indicator(reading, name):
    return next(i for i in reading.indicators if i.indicator == name)


# ── the plan's tests ──────────────────────────────────────────────────────
def test_a_district_reading_lists_every_town_that_touches_it_with_its_share(tmp_path):
    reading = read_place(opened(tmp_path), *DISTRICT, root=REPO)
    assert reading.found and reading.level == "sldl"
    shares = {t.name: (t.weight_population, t.weight_households) for t in reading.towns}
    assert shares == {"Alpha town": (1.0, 1.0), "Beta town": (0.4, 0.35),
                      "Cove Twp": (1.0, 1.0), "Dune gore": (0.0, None),
                      "Echo plantation": (0.3, 0.3), "Fox town": (0.015, 0.02),
                      "Gull Island UT": (1.0, 1.0)}


def test_a_districts_value_is_its_own_never_made_from_its_towns(tmp_path):
    broadband = indicator(read_place(opened(tmp_path), *DISTRICT, root=REPO), "cii_broadband")
    assert broadband.own_value == 79.0 and broadband.own_status == "attached"


# ── the range ─────────────────────────────────────────────────────────────
def test_the_range_is_the_min_and_max_of_the_towns_that_enter_it(tmp_path):
    broadband = indicator(read_place(opened(tmp_path), *DISTRICT, root=REPO), "cii_broadband")
    assert (broadband.minimum, broadband.maximum) == (70.0, 88.0)
    assert broadband.minimum_towns == ["Alpha town"] and broadband.maximum_towns == ["Beta town"]
    assert {t.name for t in broadband.in_range} == {"Alpha town", "Beta town", "Cove Twp", "Fox town"}


def test_a_town_with_none_of_its_households_here_is_listed_and_kept_out(tmp_path):
    reading = read_place(opened(tmp_path), *DISTRICT, root=REPO)
    dune = next(t for t in reading.towns if t.name == "Dune gore")
    assert dune.residents_here is False and "D-180" in dune.note
    out = {t.name: t.out_why for t in indicator(reading, "cii_broadband").left_out}
    assert "D-180" in out["Dune gore"]


def test_a_value_on_other_boundaries_stays_out_and_says_why(tmp_path):
    out = {t.name: t.out_why for t in
           indicator(read_place(opened(tmp_path), *DISTRICT, root=REPO), "cii_broadband").left_out}
    assert "2023 boundaries" in out["Echo plantation"]


def test_a_statistical_area_and_a_small_sample_enter_the_range_and_are_named(tmp_path):
    broadband = indicator(read_place(opened(tmp_path), *DISTRICT, root=REPO), "cii_broadband")
    entered = {t.name: t for t in broadband.in_range}
    assert entered["Cove Twp"].unchecked and entered["Beta town"].small_sample


def test_the_firm_range_is_the_towns_wholly_here_on_a_sound_sample(tmp_path):
    reading = read_place(opened(tmp_path), *DISTRICT, root=REPO)
    broadband = indicator(reading, "cii_broadband")
    assert (broadband.firm_minimum, broadband.firm_maximum) == (70.0, 70.0)
    assert broadband.firm_minimum_towns == ["Alpha town"] and broadband.firm_count == 1
    assert "Fox town" not in broadband.firm_maximum_towns, "a split town never sets a firm end"
    rent = indicator(reading, "cii_rent_burden")
    assert rent.firm_count is None, "no town wholly here is shaky, so the firm range is theirs"


def test_whole_towns_are_ranged_apart_from_towns_the_line_splits(tmp_path):
    broadband = indicator(read_place(opened(tmp_path), *DISTRICT, root=REPO), "cii_broadband")
    assert (broadband.whole_minimum, broadband.whole_maximum) == (70.0, 75.0)
    assert broadband.whole_count == 2
    assert [t.name for t in broadband.split] == ["Beta town", "Fox town"]


def test_each_indicators_towns_are_listed_most_here_first(tmp_path):
    broadband = indicator(read_place(opened(tmp_path), *DISTRICT, root=REPO), "cii_broadband")
    assert [t.name for t in broadband.towns] == [
        "Alpha town", "Cove Twp", "Gull Island UT", "Beta town", "Echo plantation",
        "Fox town", "Dune gore"]


def test_an_empty_value_is_said_in_plain_words(tmp_path):
    broadband = indicator(read_place(opened(tmp_path), *DISTRICT, root=REPO), "cii_broadband")
    gull = next(t for t in broadband.towns if t.name == "Gull Island UT")
    assert not gull.in_range
    assert "the ACS estimates none of its households (zero denominator)" in gull.out_why


def test_a_contained_universe_shows_no_share(tmp_path):
    rent = indicator(read_place(opened(tmp_path), *DISTRICT, root=REPO), "cii_rent_burden")
    assert rent.universe == RENTERS and rent.universe_relation == "contains"
    assert "D-182" in rent.universe_note
    assert all(t.share is None for t in rent.towns)
    assert (rent.minimum, rent.maximum) == (25.0, 30.0)
    assert {t.name for t in rent.in_range} == {"Alpha town", "Beta town"}


# ── other places ──────────────────────────────────────────────────────────
def test_a_county_reads_its_towns_through_contains_edges(tmp_path):
    reading = read_place(opened(tmp_path), "us_census_geoid", "23001", root=REPO)
    assert reading.found and [t.name for t in reading.towns] == ["Alpha town", "Beta town"]
    assert all(t.edge_kind == "contains" for t in reading.towns)


def test_a_key_that_is_not_a_place_says_so(tmp_path):
    reading = read_place(opened(tmp_path), "us_census_sldl", "23999", root=REPO)
    assert not reading.found and "not a place" in reading.why


# ── the telling ──────────────────────────────────────────────────────────
def test_the_telling_says_each_town_its_value_and_what_the_range_rests_on(tmp_path):
    said = say_place(read_place(opened(tmp_path), *DISTRICT, root=REPO))
    assert "State House District 9 (2024); Maine" in said
    assert "not of this place's people" in said
    assert "this place: 79.0, margin not derived (D-18), the publisher's own estimate" in said
    assert "~ Beta town: 88.0, on 40 households, a small sample; 35.0% of its households here" in said
    assert ("range: 70.0 (Alpha town) to 88.0 (Beta town, 35.0% of its 40 households here, "
            "a small sample), across 4 of 7 towns") in said
    assert ("towns wholly here: 70.0 (Alpha town) to 75.0 (Cove Twp, a statistical area, "
            "attached unchecked), across 2") in said
    assert ("towns split by its line: 88.0 (Beta town, 35.0% of its 40 households here, a small "
            "sample); 80.0 (Fox town, 2.0% of its 1,000 households here)") in said
    assert ("wholly here, without small samples or unchecked areas: all 70.0 (Alpha town), "
            "across 1") in said
    assert "Dune gore (gore): its land touches this place; none of its residents live here" in said
    assert "~ Echo plantation: 50.0, left out of the range:" in said
    assert "Fox town (town): 1.5% of its residents, 2.0% of its households" in said
    assert "~ Alpha town: 30.0, on 300 renter households with rent burden computed" in said
    assert "towns split by its line: 25.0 (Beta town, partly here)" in said
