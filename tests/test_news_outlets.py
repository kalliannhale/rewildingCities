"""outlets placed by town (Sprint 06, step 3, the fifth carrier; D-241 to
D-246): one outlet per group with an id from its members, a named town
first and an office town only by choice, towns matched by declared names,
operating status by a declared vocabulary, reviews keyed by the words, and
located_in edges at town, county and state only."""

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    path = ROOT / "soil" / "transform" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod          # before exec: the module defines dataclasses
    spec.loader.exec_module(mod)
    return mod


pno = _load("prepare_news_outlets")
btl = _load("build_town_located_in")
cl = _load("count_located")

ORDER = ["local_news_catalyst", "maine_media_ecosystem", "cision", "cision_raw", "easton"]
SOURCES = {"sources": {k: {} for k in ORDER}, "source_order": ORDER,
           "operating_vocabulary": {"operating": ["yes"], "ceased": ["Ceased Operations"],
                                    "last_post_prefix": "Last post"}}
NAMES = {"suffixes": {"cousub": ["city", "town", "plantation"], "county": ["County"]}}
G = "us_census_geoid"

PLACES = pd.DataFrame([
    (G, "23", "state", "Maine", "2024"),
    (G, "23017", "county", "Oxford County", "2024"),
    (G, "23005", "county", "Cumberland County", "2024"),
    (G, "23013", "county", "Knox County", "2024"),
    (G, "23029", "county", "Washington County", "2024"),
    (G, "23021", "county", "Piscataquis County", "2024"),
    (G, "2301754420", "cousub", "Norway town", "2024"),
    (G, "2300560545", "cousub", "Portland city", "2024"),
    (G, "2300571990", "cousub", "South Portland city", "2024"),
    (G, "2301311111", "cousub", "Washington town", "2024"),
    (G, "2302922222", "cousub", "Washington town", "2024"),
    (G, "2302117000", "cousub", "Dover-Foxcroft town", "2024"),
    ("us_census_sldl", "23001", "sldl", "State House District 1", "2024"),
], columns=["authority", "code", "level", "name", "vintage"])

COLS = ["source", "source_line", "name", "name_key", "group_id", "named_town",
        "named_county", "office_town", "office_county", "operating_raw"]


def grouped(*records):
    """records: (group, source, line, name, named_town, named_county,
    office_town, operating)"""
    rows = []
    for g, src, line, name, nt, nc, ot, op in records:
        rows.append({"source": src, "source_line": str(line), "name": name,
                     "name_key": name.lower(), "group_id": g, "named_town": nt,
                     "named_county": nc, "office_town": ot, "office_county": None,
                     "operating_raw": op})
    return pd.DataFrame(rows, columns=COLS)


def run(df, fallback="office_town", ceased="listed", reviews=None):
    return pno.prepare(df, PLACES, SOURCES, NAMES, fallback, ceased, "23", reviews)


def listed(p):
    return {r["name"]: r["reason"] for r in p.listed}


# ── where an outlet is ─────────────────────────────────────────────────────

def test_a_named_town_places_the_outlet():
    p = run(grouped(("g1", "local_news_catalyst", 2, "Norway Paper", "Norway", None, None, None)))
    r = p.outlets.iloc[0]
    assert (r.town_code, r.town_name, r.county_code, r.placed_by) == (
        "2301754420", "Norway town", "23017", "named_town")


def test_a_named_town_wins_over_an_office_town():
    # the Advertiser Democrat: a Norway paper Cision puts in South Portland
    p = run(grouped(("g1", "local_news_catalyst", 2, "Advertiser Democrat", "Norway", None, None, None),
                    ("g1", "cision", 5, "Advertiser Democrat", None, None, "South Portland", "yes")))
    r = p.outlets.iloc[0]
    assert r.town_code == "2301754420" and r.placed_by == "named_town"
    assert "office_town_not_named" not in (r["flags"] or "")


def test_with_no_fallback_an_unnamed_outlet_is_listed():
    p = run(grouped(("g1", "cision", 5, "Office Only", None, None, "Portland", "yes")),
            fallback="none")
    assert p.outlets.empty and listed(p) == {"Office Only": "no_town_given"}


def test_by_choice_an_office_town_places_and_says_so():
    p = run(grouped(("g1", "cision", 5, "Office Only", None, None, "Portland", "yes")))
    r = p.outlets.iloc[0]
    assert r.placed_by == "office_town" and r.town_code == "2300560545"
    assert "office_town_not_named" in r["flags"]


def test_no_town_at_all_is_listed():
    p = run(grouped(("g1", "easton", 3, "Served Only", None, None, None, None)))
    assert listed(p) == {"Served Only": "no_town_given"}


def test_two_named_towns_disagree_and_are_listed():
    p = run(grouped(("g1", "local_news_catalyst", 2, "Two Towns", "Norway", None, None, None),
                    ("g1", "maine_media_ecosystem", 4, "Two Towns", "Portland", None, None, None)))
    assert listed(p) == {"Two Towns": "towns_disagree"}
    assert "Norway town" in p.listed[0]["detail"] and "Portland city" in p.listed[0]["detail"]


def test_one_town_spelled_two_ways_is_no_disagreement():
    p = run(grouped(("g1", "local_news_catalyst", 2, "One Town", "Portland", None, None, None),
                    ("g1", "maine_media_ecosystem", 4, "One Town", "portland city", None, None, None)))
    assert p.outlets.iloc[0].town_code == "2300560545"


def test_a_shared_name_needs_a_county():
    p = run(grouped(("g1", "local_news_catalyst", 2, "No County", "Washington", None, None, None),
                    ("g2", "local_news_catalyst", 3, "With County", "Washington", "Knox", None, None)))
    assert listed(p) == {"No County": "ambiguous_town"}
    assert p.outlets.iloc[0].town_code == "2301311111"


def test_a_county_that_does_not_hold_the_town_is_no_match():
    p = run(grouped(("g1", "local_news_catalyst", 2, "Wrong County", "Norway", "Knox", None, None)))
    assert listed(p) == {"Wrong County": "no_town_match"}


def test_a_hyphen_reads_as_a_space_and_nothing_more_is_forgiven():
    p = run(grouped(("g1", "local_news_catalyst", 2, "Hyphen", "Dover Foxcroft", None, None, None),
                    ("g2", "local_news_catalyst", 3, "Village", "Northeast Harbor", None, None, None),
                    ("g3", "local_news_catalyst", 4, "Abbrev", "So. Portland", None, None, None)))
    assert p.outlets.iloc[0].town_code == "2302117000"
    assert listed(p) == {"Village": "no_town_match", "Abbrev": "no_town_match"}


def test_a_matched_and_an_unmatched_named_town_place_with_a_flag():
    p = run(grouped(("g1", "local_news_catalyst", 2, "Half", "Norway", None, None, None),
                    ("g1", "maine_media_ecosystem", 4, "Half", "Norway Village", None, None, None)))
    r = p.outlets.iloc[0]
    assert r.town_code == "2301754420" and "town_unmatched:" in r["flags"]


# ── operating status ───────────────────────────────────────────────────────

def test_a_ceased_outlet_is_listed_by_choice():
    p = run(grouped(("g1", "cision", 5, "Gone", None, None, "Portland", "Ceased Operations")))
    assert listed(p) == {"Gone": "ceased"}


def test_a_ceased_outlet_can_be_counted_and_flagged():
    p = run(grouped(("g1", "cision", 5, "Gone", None, None, "Portland", "Ceased Operations")),
            ceased="counted")
    r = p.outlets.iloc[0]
    assert r.operating == "ceased" and "operating:ceased" in r["flags"]


def test_a_last_post_is_quiet_counted_and_keeps_its_words():
    p = run(grouped(("g1", "cision", 5, "Quiet", None, None, "Portland", "Last Post August 2025")))
    r = p.outlets.iloc[0]
    assert (r.operating, r.operating_note) == ("last_post", "Last Post August 2025")


def test_a_value_in_no_list_stays_counted_and_says_so():
    p = run(grouped(("g1", "cision", 5, "Odd", None, None, "Portland", "maybe")))
    assert p.outlets.iloc[0].operating == "unmapped"


def test_no_status_is_not_given():
    p = run(grouped(("g1", "local_news_catalyst", 2, "Plain", "Norway", None, None, None)))
    assert p.outlets.iloc[0].operating == "not_given"


# ── ids ────────────────────────────────────────────────────────────────────

def test_an_id_comes_from_the_first_member_by_source_order():
    p = run(grouped(("g1", "cision", 5, "Sun Journal", None, None, "Portland", "yes"),
                    ("g1", "local_news_catalyst", 9, "Sun Journal", "Portland", None, None, None)))
    assert p.outlets.iloc[0].feature_id == "outlet:local_news_catalyst:sun_journal"


def test_ids_do_not_follow_row_order():
    a = grouped(("g1", "local_news_catalyst", 2, "Alpha", "Norway", None, None, None),
                ("g2", "local_news_catalyst", 3, "Beta", "Portland", None, None, None))
    b = grouped(("g1", "cision", 1, "New One", None, None, "Portland", "yes"),
                ("g2", "local_news_catalyst", 3, "Alpha", "Norway", None, None, None),
                ("g3", "local_news_catalyst", 4, "Beta", "Portland", None, None, None))
    ids_a = set(run(a).outlets.feature_id)
    ids_b = set(run(b).outlets.feature_id)
    assert ids_a <= ids_b


def test_two_outlets_one_name_take_their_lines():
    p = run(grouped(("g1", "cision", 5, "Twin", None, None, "Portland", "yes"),
                    ("g2", "cision", 8, "Twin", None, None, "Norway", "yes")))
    assert set(p.outlets.feature_id) == {"outlet:cision:twin:5", "outlet:cision:twin:8"}
    assert all("id_by_line" in f for f in p.outlets["flags"])


# ── reviews ────────────────────────────────────────────────────────────────

REVIEW = {"evidence": "read on both mastheads", "read_on": "2026-11-15", "read_by": "Kalli A. Hale"}


def test_a_reviewed_merge_joins_two_groups():
    df = grouped(("g1", "local_news_catalyst", 2, "The Ellsworth American", "Norway", None, None, None),
                 ("g2", "cision", 5, "Ellsworth American Inc", None, None, "Portland", "yes"))
    merge = {"records": [{"source": "local_news_catalyst", "name": "The Ellsworth American"},
                         {"source": "cision", "name": "Ellsworth American Inc"}], **REVIEW}
    p = run(df, reviews={"merges": [merge]})
    assert len(p.outlets) == 1
    r = p.outlets.iloc[0]
    assert r.town_code == "2301754420" and "merged_by_review" in r["flags"]
    assert r.review_read_by == "Kalli A. Hale"


def test_a_merge_the_run_no_longer_needs_refuses():
    df = grouped(("g1", "local_news_catalyst", 2, "Same", "Norway", None, None, None),
                 ("g1", "cision", 5, "Same", None, None, "Portland", "yes"))
    merge = {"records": [{"source": "local_news_catalyst", "name": "Same"},
                         {"source": "cision", "name": "Same"}], **REVIEW}
    with pytest.raises(pno.OutletsRefused, match="already one group"):
        run(df, reviews={"merges": [merge]})


def test_a_merge_that_would_hold_one_source_twice_refuses():
    df = grouped(("g1", "cision", 2, "A", None, None, "Portland", "yes"),
                 ("g2", "cision", 5, "B", None, None, "Portland", "yes"))
    merge = {"records": [{"source": "cision", "name": "A"}, {"source": "cision", "name": "B"}], **REVIEW}
    with pytest.raises(pno.OutletsRefused, match="twice"):
        run(df, reviews={"merges": [merge]})


def test_a_review_whose_words_changed_refuses():
    df = grouped(("g1", "local_news_catalyst", 2, "Renamed", "Norway", None, None, None))
    merge = {"records": [{"source": "local_news_catalyst", "name": "Old Name"},
                         {"source": "cision", "name": "Other"}], **REVIEW}
    with pytest.raises(pno.OutletsRefused, match="no local_news_catalyst record"):
        run(df, reviews={"merges": [merge]})


def test_a_reviewed_town_settles_a_listed_outlet():
    df = grouped(("g1", "local_news_catalyst", 2, "Two Towns", "Norway", None, None, None),
                 ("g1", "maine_media_ecosystem", 4, "Two Towns", "Portland", None, None, None))
    town = {"source": "local_news_catalyst", "name": "Two Towns", "town_code": "2301754420", **REVIEW}
    p = run(df, reviews={"towns": [town]})
    r = p.outlets.iloc[0]
    assert r.placed_by == "reviewed" and r.town_code == "2301754420"
    assert "review_settled:towns_disagree" in r["flags"]


def test_a_town_review_the_run_no_longer_needs_refuses():
    df = grouped(("g1", "local_news_catalyst", 2, "Placed", "Norway", None, None, None))
    town = {"source": "local_news_catalyst", "name": "Placed", "town_code": "2301754420", **REVIEW}
    with pytest.raises(pno.OutletsRefused, match="no longer needs"):
        run(df, reviews={"towns": [town]})


def test_a_town_review_must_name_a_town_and_its_evidence():
    df = grouped(("g1", "local_news_catalyst", 2, "Village", "Northeast Harbor", None, None, None))
    bad_code = {"source": "local_news_catalyst", "name": "Village", "town_code": "23017", **REVIEW}
    with pytest.raises(pno.OutletsRefused, match="not a town"):
        run(df, reviews={"towns": [bad_code]})
    no_evidence = {"source": "local_news_catalyst", "name": "Village", "town_code": "2301754420",
                   "read_on": "2026-11-15", "read_by": "Kalli A. Hale"}
    with pytest.raises(pno.OutletsRefused, match="evidence"):
        run(df, reviews={"towns": [no_evidence]})


# ── the declarations ───────────────────────────────────────────────────────

def test_source_order_must_name_every_declared_source():
    bad = {**SOURCES, "source_order": ORDER[:-1]}
    with pytest.raises(pno.OutletsRefused, match="same set"):
        pno.prepare(grouped(), PLACES, bad, NAMES, "none", "listed", "23")


def test_a_missing_vocabulary_refuses():
    bad = {k: v for k, v in SOURCES.items() if k != "operating_vocabulary"}
    with pytest.raises(pno.OutletsRefused, match="operating_vocabulary"):
        pno.prepare(grouped(), PLACES, bad, NAMES, "none", "listed", "23")


def test_a_choice_outside_its_options_refuses():
    with pytest.raises(pno.OutletsRefused, match="town_fallback"):
        pno.prepare(grouped(), PLACES, SOURCES, NAMES, "address", "listed", "23")


def test_the_receipt_lists_every_outlet_not_placed():
    p = run(grouped(("g1", "local_news_catalyst", 2, "Placed", "Norway", None, None, None),
                    ("g2", "easton", 3, "Unplaced", None, None, None, None)))
    meta = pno.output_metadata(p)
    assert meta["placed_by"] == {"named_town": 1}
    assert meta["listed_reasons"] == {"no_town_given": 1}
    assert meta["listed_outlets"][0]["records"] == "easton:3"


# ── located_in by town, and the count it feeds ─────────────────────────────

def _outlets():
    return run(grouped(("g1", "local_news_catalyst", 2, "Norway Paper", "Norway", None, None, None),
                       ("g2", "local_news_catalyst", 3, "Portland Paper", "Portland", None, None, None),
                       ("g3", "cision", 5, "Portland Weekly", None, None, "Portland", "yes"))).outlets


def test_edges_reach_town_county_and_state_only():
    e = btl.locate_by_town(_outlets(), PLACES, "lyr", "feature_id", "town_code", "23")
    assert len(e) == 9 and set(e["to_authority"]) == {G}
    assert set(e["vintage"]) == {"2024"}
    one = e[e["from_code"] == "outlet:local_news_catalyst:norway_paper"]
    assert set(one["to_code"]) == {"23", "23017", "2301754420"}
    assert set(btl.output_metadata(e)["not_placed_at"]) == {"sldl", "sldu", "aiannh", "division"}


def test_edges_refuse_what_is_not_a_town():
    f = pd.DataFrame({"feature_id": ["a"], "town_code": ["23017"]})
    with pytest.raises(btl.TownLocatedRefused, match="not a town"):
        btl.locate_by_town(f, PLACES, "lyr", "feature_id", "town_code", "23")
    f = pd.DataFrame({"feature_id": ["a", "a"], "town_code": ["2301754420"] * 2})
    with pytest.raises(btl.TownLocatedRefused, match="used twice"):
        btl.locate_by_town(f, PLACES, "lyr", "feature_id", "town_code", "23")
    f = pd.DataFrame({"feature_id": ["a"], "town_code": [None]})
    with pytest.raises(btl.TownLocatedRefused, match="names no town"):
        btl.locate_by_town(f, PLACES, "lyr", "feature_id", "town_code", "23")


def test_count_located_counts_town_placed_outlets_unchanged():
    edges = btl.locate_by_town(_outlets(), PLACES, "lyr", "feature_id", "town_code", "23")
    spine = pd.DataFrame({
        "GEOID": ["b1", "b2", "b3", "b4", "b5", "b6", "b7"],
        "county": ["23017", "23005", "23005", "23013", "23029", "23021", "23005"],
        "cousub": ["2301754420", "2300560545", "2300571990", "2301311111",
                   "2302922222", "2302117000", "2300560545"],
        "persons": ["2000", "30000", "10000", "1000", "500", "4000", "38000"]})
    ind = {"id": "news_outlets_per_1000",
           "derivation": {"kind": "located_count", "denominator": "persons", "scale": 1000}}
    out = cl.count(edges, spine, PLACES, ind, ["state", "county", "cousub"], "undated",
                   "rewildingcities")
    by = dict(zip(out["unit_code"], out["count"]))
    assert by["2300560545"] == 2 and by["2301754420"] == 1 and by["2300571990"] == 0
    assert by["23005"] == 2 and by["23"] == 3
    assert out.loc[out["unit_code"] == "2300560545", "value"].iloc[0] == pytest.approx(2 / 68000 * 1000)
    assert set(out["boundary_vintage"]) == {"2024"}
