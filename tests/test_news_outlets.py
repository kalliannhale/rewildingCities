"""outlets placed by town (Sprint 06, step 3, the fifth carrier; D-241 to
D-252): one outlet per group with an id from its members; closed, local
news and where, asked in that order; a list's say or a database's declared
type; a named town first, a statewide name the state alone, an office town
only by choice and never a shared office under office_town_unshared; towns
matched by declared names, reviews keyed by the words, and located_in edges
at town, county and state, or the state alone."""

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
                                    "last_post_prefix": "Last post"},
           "operating_elsewhere": {"maine_media_ecosystem": {"medium_raw": {"ceased": ["CLOSED"]}}},
           "source_kinds": {"local_news_catalyst": "local_news_list",
                            "maine_media_ecosystem": "local_news_list",
                            "easton": "local_news_list",
                            "cision": "media_database", "cision_raw": "media_database"},
           "statewide_names": ["Statewide"],
           "media_database_types": {
               "read_for": ["cision", "cision_raw"],
               "classes": {"newspaper": {"counted_under": ["newspapers", "print_and_web"]},
                           "online_consumer": {"counted_under": ["print_and_web"]},
                           "blog_consumer": {},
                           "radio_station": {},
                           "radio_program": {"program": True},
                           "unknown": {"unknown": True}},
               "values": {"Newspaper": "newspaper", "Online, consumer": "online_consumer",
                          "Blog, consumer": "blog_consumer", "Radio station": "radio_station",
                          "Radio program": "radio_program", "0": "unknown"}}}
NP = "Newspaper"
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
        "named_county", "office_town", "office_county", "operating_raw", "medium_raw",
        "address_raw", "zip_raw"]


def grouped(*records):
    """records: (group, source, line, name, named_town, named_county,
    office_town, operating[, medium[, address, zip]])"""
    rows = []
    for rec in records:
        g, src, line, name, nt, nc, ot, op = rec[:8]
        medium = rec[8] if len(rec) > 8 else None
        address, zip_ = (rec[9], rec[10]) if len(rec) > 10 else (None, None)
        rows.append({"source": src, "source_line": str(line), "name": name,
                     "name_key": name.lower(), "group_id": g, "named_town": nt,
                     "named_county": nc, "office_town": ot, "office_county": None,
                     "operating_raw": op, "medium_raw": medium, "address_raw": address,
                     "zip_raw": zip_})
    return pd.DataFrame(rows, columns=COLS)


def run(df, fallback="office_town", ceased="listed", reviews=None, alone="newspapers",
        sources=None):
    return pno.prepare(df, PLACES, sources or SOURCES, NAMES, fallback, ceased, alone, "23",
                       reviews)


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
                    ("g1", "cision", 5, "Advertiser Democrat", None, None, "South Portland", "yes", NP)))
    r = p.outlets.iloc[0]
    assert r.town_code == "2301754420" and r.placed_by == "named_town"
    assert "office_town_not_named" not in (r["flags"] or "")


def test_with_no_fallback_an_unnamed_outlet_is_listed():
    p = run(grouped(("g1", "cision", 5, "Office Only", None, None, "Portland", "yes", NP)),
            fallback="none")
    assert p.outlets.empty and listed(p) == {"Office Only": "no_town_given"}


def test_by_choice_an_office_town_places_and_says_so():
    p = run(grouped(("g1", "cision", 5, "Office Only", None, None, "Portland", "yes", NP)))
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
    p = run(grouped(("g1", "cision", 5, "Gone", None, None, "Portland", "Ceased Operations", NP)))
    assert listed(p) == {"Gone": "ceased"}


def test_a_ceased_outlet_can_be_counted_and_flagged():
    p = run(grouped(("g1", "cision", 5, "Gone", None, None, "Portland", "Ceased Operations", NP)),
            ceased="counted")
    r = p.outlets.iloc[0]
    assert r.operating == "ceased" and "operating:ceased" in r["flags"]


def test_a_last_post_is_quiet_counted_and_keeps_its_words():
    p = run(grouped(("g1", "cision", 5, "Quiet", None, None, "Portland", "Last Post August 2025", NP)))
    r = p.outlets.iloc[0]
    assert (r.operating, r.operating_note) == ("last_post", "Last Post August 2025")


def test_a_value_in_no_list_stays_counted_and_says_so():
    p = run(grouped(("g1", "cision", 5, "Odd", None, None, "Portland", "maybe", NP)))
    assert p.outlets.iloc[0].operating == "unmapped"


def test_no_status_is_not_given():
    p = run(grouped(("g1", "local_news_catalyst", 2, "Plain", "Norway", None, None, None)))
    assert p.outlets.iloc[0].operating == "not_given"


# ── ids ────────────────────────────────────────────────────────────────────

def test_an_id_comes_from_the_first_member_by_source_order():
    p = run(grouped(("g1", "cision", 5, "Sun Journal", None, None, "Portland", "yes", NP),
                    ("g1", "local_news_catalyst", 9, "Sun Journal", "Portland", None, None, None)))
    assert p.outlets.iloc[0].feature_id == "outlet:local_news_catalyst:sun_journal"


def test_ids_do_not_follow_row_order():
    a = grouped(("g1", "local_news_catalyst", 2, "Alpha", "Norway", None, None, None),
                ("g2", "local_news_catalyst", 3, "Beta", "Portland", None, None, None))
    b = grouped(("g1", "cision", 1, "New One", None, None, "Portland", "yes", NP),
                ("g2", "local_news_catalyst", 3, "Alpha", "Norway", None, None, None),
                ("g3", "local_news_catalyst", 4, "Beta", "Portland", None, None, None))
    ids_a = set(run(a).outlets.feature_id)
    ids_b = set(run(b).outlets.feature_id)
    assert ids_a <= ids_b


def test_two_outlets_one_name_take_their_lines():
    p = run(grouped(("g1", "cision", 5, "Twin", None, None, "Portland", "yes", NP),
                    ("g2", "cision", 8, "Twin", None, None, "Norway", "yes", NP)))
    assert set(p.outlets.feature_id) == {"outlet:cision:twin:5", "outlet:cision:twin:8"}
    assert all("id_by_line" in f for f in p.outlets["flags"])


# ── reviews ────────────────────────────────────────────────────────────────

REVIEW = {"evidence": "read on both mastheads", "read_on": "2026-11-15", "read_by": "Kalli A. Hale"}


def test_a_reviewed_merge_joins_two_groups():
    df = grouped(("g1", "local_news_catalyst", 2, "The Ellsworth American", "Norway", None, None, None),
                 ("g2", "cision", 5, "Ellsworth American Inc", None, None, "Portland", "yes", NP))
    merge = {"records": [{"source": "local_news_catalyst", "name": "The Ellsworth American"},
                         {"source": "cision", "name": "Ellsworth American Inc"}], **REVIEW}
    p = run(df, reviews={"merges": [merge]})
    assert len(p.outlets) == 1
    r = p.outlets.iloc[0]
    assert r.town_code == "2301754420" and "merged_by_review" in r["flags"]
    assert r.review_read_by == "Kalli A. Hale"


def test_a_merge_the_run_no_longer_needs_refuses():
    df = grouped(("g1", "local_news_catalyst", 2, "Same", "Norway", None, None, None),
                 ("g1", "cision", 5, "Same", None, None, "Portland", "yes", NP))
    merge = {"records": [{"source": "local_news_catalyst", "name": "Same"},
                         {"source": "cision", "name": "Same"}], **REVIEW}
    with pytest.raises(pno.OutletsRefused, match="already one group"):
        run(df, reviews={"merges": [merge]})


def test_a_merge_that_would_hold_one_source_twice_refuses():
    df = grouped(("g1", "cision", 2, "A", None, None, "Portland", "yes", NP),
                 ("g2", "cision", 5, "B", None, None, "Portland", "yes", NP))
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
        pno.prepare(grouped(), PLACES, bad, NAMES, "none", "listed", "none", "23")


def test_a_missing_vocabulary_refuses():
    bad = {k: v for k, v in SOURCES.items() if k != "operating_vocabulary"}
    with pytest.raises(pno.OutletsRefused, match="operating_vocabulary"):
        pno.prepare(grouped(), PLACES, bad, NAMES, "none", "listed", "none", "23")


def test_a_choice_outside_its_options_refuses():
    with pytest.raises(pno.OutletsRefused, match="town_fallback"):
        pno.prepare(grouped(), PLACES, SOURCES, NAMES, "address", "listed", "none", "23")


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
                       ("g3", "cision", 5, "Portland Weekly", None, None, "Portland", "yes", NP))).outlets


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


# ── is it local news (D-247, D-248) ────────────────────────────────────────

def test_an_outlet_on_a_local_news_list_counts_whatever_its_medium():
    p = run(grouped(("g1", "maine_media_ecosystem", 4, "Valley Radio", "Norway", None, None, None,
                     "Radio"),
                    ("g1", "cision", 5, "Valley Radio", None, None, "Portland", "yes",
                     "Radio station")))
    r = p.outlets.iloc[0]
    assert r.vouched_by == "maine_media_ecosystem" and r.database_class == "radio_station"
    assert "maine_media_ecosystem: Radio" in r.medium_as_written


def test_a_database_alone_outlet_counts_only_as_its_choice_says():
    df = grouped(("g1", "cision", 5, "Weekly", None, None, "Portland", "yes", NP),
                 ("g2", "cision", 6, "Site", None, None, "Portland", "yes", "Online, consumer"),
                 ("g3", "cision", 7, "Station", None, None, "Portland", "yes", "Radio station"))
    news = run(df, alone="newspapers")
    assert list(news.outlets.name) == ["Weekly"] and news.outlets.iloc[0].vouched_by is None
    assert listed(news) == {"Site": "medium_not_counted", "Station": "medium_not_counted"}
    web = run(df, alone="print_and_web")
    assert set(web.outlets.name) == {"Weekly", "Site"}
    none = run(df, alone="none")
    assert none.outlets.empty and set(listed(none).values()) == {"medium_not_counted"}


def test_a_placeholder_type_is_unknown_and_never_a_class():
    alone = run(grouped(("g1", "cision_raw", 5, "Zero", None, None, "Portland", None, "0")))
    assert listed(alone) == {"Zero": "medium_unknown"}
    beside = run(grouped(("g1", "cision", 5, "Paper", None, None, "Portland", "yes", NP),
                         ("g1", "cision_raw", 9, "Paper", None, None, "Portland", None, "0")))
    assert beside.outlets.iloc[0].database_class == "newspaper; unknown"


def test_two_database_types_one_counted_one_not_is_a_conflict():
    p = run(grouped(("g1", "cision", 5, "Both", None, None, "Portland", "yes", NP),
                    ("g1", "cision_raw", 9, "Both", None, None, "Portland", None, "Online, consumer")))
    assert listed(p) == {"Both": "medium_conflict"}


def test_an_undeclared_database_type_refuses_the_run():
    with pytest.raises(pno.OutletsRefused, match="does not declare"):
        run(grouped(("g1", "cision", 5, "New", None, None, "Portland", "yes", "Hologram")))


def test_a_program_never_counts_under_any_choice():
    bad = dict(SOURCES["media_database_types"])
    bad["classes"] = {**bad["classes"], "radio_program": {"program": True,
                                                         "counted_under": ["print_and_web"]}}
    with pytest.raises(pno.OutletsRefused, match="transmitter twice"):
        run(grouped(), sources={**SOURCES, "media_database_types": bad})
    p = run(grouped(("g1", "cision", 5, "Morning Show", None, None, "Portland", "yes",
                     "Radio program")), alone="print_and_web")
    assert listed(p) == {"Morning Show": "medium_not_counted"}


def test_an_unknown_class_counts_under_nothing():
    bad = dict(SOURCES["media_database_types"])
    bad["classes"] = {**bad["classes"], "unknown": {"unknown": True,
                                                   "counted_under": ["newspapers"]}}
    with pytest.raises(pno.OutletsRefused, match="never evidence"):
        run(grouped(), sources={**SOURCES, "media_database_types": bad})


def test_the_medium_is_judged_before_the_town():
    df = grouped(("g1", "cision", 5, "A Blog", None, None, "Nowhere", "yes", "Blog, consumer"))
    assert listed(run(df)) == {"A Blog": "medium_not_counted"}
    town = {"source": "cision", "name": "A Blog", "town_code": "2300560545", **REVIEW}
    with pytest.raises(pno.OutletsRefused, match="for its medium"):
        run(df, reviews={"towns": [town]})


def test_every_source_has_a_declared_kind():
    bad = {**SOURCES, "source_kinds": {k: v for k, v in SOURCES["source_kinds"].items()
                                       if k != "easton"}}
    with pytest.raises(pno.OutletsRefused, match="same set"):
        run(grouped(), sources=bad)
    worse = {**SOURCES, "source_kinds": {**SOURCES["source_kinds"], "easton": "rumour"}}
    with pytest.raises(pno.OutletsRefused, match="kind is one of"):
        run(grouped(), sources=worse)


def test_a_database_choice_outside_its_options_refuses():
    with pytest.raises(pno.OutletsRefused, match="database_alone"):
        run(grouped(), alone="everything")


# ── a status written elsewhere (D-251) ─────────────────────────────────────

def test_a_status_written_in_the_medium_column_is_read():
    p = run(grouped(("g1", "maine_media_ecosystem", 4, "Shut", "Norway", None, None, None,
                     "CLOSED")))
    assert listed(p) == {"Shut": "ceased"}
    assert "CLOSED (maine_media_ecosystem medium_raw)" in p.listed[0]["detail"]


# ── statewide (D-249) ──────────────────────────────────────────────────────

def test_a_statewide_outlet_is_placed_in_the_state_alone():
    p = run(grouped(("g1", "maine_media_ecosystem", 4, "Amjambo Africa", "Statewide", "Maine",
                     None, None, "Newspaper")))
    r = p.outlets.iloc[0]
    assert (r.scope, r.placed_by, r.town_as_written) == ("state", "named_state", "Statewide")
    assert pd.isna(r.town_code) and pd.isna(r.county_code)
    assert "placed_in_state_only" in r["flags"]
    e = btl.locate_by_town(p.outlets, PLACES, "lyr", "feature_id", "town_code", "23", "scope")
    assert list(e["to_code"]) == ["23"] and btl.output_metadata(e)["state_only"] == 1


def test_a_named_town_wins_over_a_statewide_name():
    p = run(grouped(("g1", "local_news_catalyst", 2, "Paper", "Portland", None, None, None),
                    ("g1", "maine_media_ecosystem", 4, "Paper", "Statewide", None, None, None)))
    r = p.outlets.iloc[0]
    assert r.scope == "town" and r.town_code == "2300560545"
    assert "statewide_also:maine_media_ecosystem" in r["flags"]


def test_a_town_review_for_a_statewide_outlet_refuses():
    df = grouped(("g1", "maine_media_ecosystem", 4, "Everywhere", "Statewide", None, None, None))
    town = {"source": "maine_media_ecosystem", "name": "Everywhere",
            "town_code": "2300560545", **REVIEW}
    with pytest.raises(pno.OutletsRefused, match="no longer needs"):
        run(df, reviews={"towns": [town]})


def test_statewide_names_must_be_declared():
    bad = {k: v for k, v in SOURCES.items() if k != "statewide_names"}
    with pytest.raises(pno.OutletsRefused, match="statewide_names"):
        run(grouped(), sources=bad)


def test_edges_refuse_a_scope_that_says_two_things():
    f = pd.DataFrame({"feature_id": ["a"], "town_code": ["2301754420"], "scope": ["state"]})
    with pytest.raises(btl.TownLocatedRefused, match="one thing"):
        btl.locate_by_town(f, PLACES, "lyr", "feature_id", "town_code", "23", "scope")
    f = pd.DataFrame({"feature_id": ["a"], "town_code": ["2301754420"], "scope": ["region"]})
    with pytest.raises(btl.TownLocatedRefused, match="scope is one of"):
        btl.locate_by_town(f, PLACES, "lyr", "feature_id", "town_code", "23", "scope")


# ── a shared office (D-250) ────────────────────────────────────────────────

ADDR = ("1 Main St.", "04106-1234")


def _chain():
    return grouped(("g1", "cision", 5, "North Weekly", None, None, "Portland", "yes", NP, *ADDR),
                   ("g2", "cision", 6, "South Weekly", None, None, "Portland", "yes", NP,
                    "1 main st", "04106"))


def test_a_shared_office_is_flagged_under_office_town():
    p = run(_chain(), fallback="office_town")
    assert len(p.outlets) == 2
    assert all("office_shared:2" in f for f in p.outlets["flags"])


def test_a_shared_office_is_listed_under_office_town_unshared():
    p = run(_chain(), fallback="office_town_unshared")
    assert p.outlets.empty
    assert listed(p) == {"North Weekly": "office_shared", "South Weekly": "office_shared"}
    assert "South Weekly" in p.listed[0]["detail"]


def test_a_named_sibling_shows_the_office_is_a_publishers():
    df = grouped(("g1", "local_news_catalyst", 2, "Advertiser Democrat", "Norway", None, None, None),
                 ("g1", "cision", 5, "Advertiser Democrat", None, None, "South Portland", "yes",
                  NP, "5 Elm St", "04106"),
                 ("g2", "cision", 6, "Office Only", None, None, "South Portland", "yes", NP,
                  "5 Elm St", "04106"))
    p = run(df, fallback="office_town_unshared")
    assert list(p.outlets.name) == ["Advertiser Democrat"]
    assert p.outlets.iloc[0].placed_by == "named_town"
    assert listed(p) == {"Office Only": "office_shared"}


def test_an_office_is_shared_only_on_street_and_zip_alike():
    df = grouped(("g1", "cision", 5, "One", None, None, "Portland", "yes", NP, "1 Main St", "04106"),
                 ("g2", "cision", 6, "Two", None, None, "Norway", "yes", NP, "1 Main St", "04268"),
                 ("g3", "cision", 7, "Three", None, None, "Portland", "yes", NP, "1 Main St", None))
    p = run(df, fallback="office_town_unshared")
    assert len(p.outlets) == 3 and not p.listed


def test_a_town_review_settles_a_shared_office():
    town = {"source": "cision", "name": "North Weekly", "town_code": "2301754420", **REVIEW}
    p = run(_chain(), fallback="office_town_unshared", reviews={"towns": [town]})
    r = p.outlets[p.outlets.name == "North Weekly"].iloc[0]
    assert r.placed_by == "reviewed" and "review_settled:office_shared" in r["flags"]


# ── the real declaration ───────────────────────────────────────────────────

def test_the_real_declaration_reads_and_its_rules_hold():
    import yaml
    doc = yaml.safe_load((ROOT / "seeds" / "crosswalks" / "outlets" / "outlet_sources.yml")
                         .read_text())
    order = pno.read_source_order(doc, doc["source_order"])
    kinds = pno.read_kinds(doc, order)
    types = pno.read_database_types(doc, kinds)
    assert {s for s, k in kinds.items() if k == "media_database"} == {"cision", "cision_raw"}
    assert types.values["0"] == "unknown" and types.values["Newspaper"] == "newspaper"
    for cid, c in types.classes.items():
        if (c or {}).get("program"):
            assert not (c or {}).get("counted_under"), cid
    news = {c for c, d in types.classes.items() if "newspapers" in ((d or {}).get("counted_under") or [])}
    assert news == {"newspaper"}
    assert pno.read_statewide(doc) == frozenset({"statewide"})
    assert pno.read_operating_elsewhere(doc, order, ["medium_raw"]) == [
        ("maine_media_ecosystem", "medium_raw", "ceased", "closed")]


# ── across the file the run writes (session 11's failed first run) ─────────

def test_a_statewide_outlet_survives_the_csv_between_steps(tmp_path=None):
    # the run writes the outlets to csv and the next step reads them back
    # with dtype=str. in pandas 3 a column holding text and blanks reads as
    # str, and Series.map turns a None back into NaN, so a missing town read
    # through a map was text-like nan, not None. tested here across the file
    import tempfile
    p = run(grouped(("g1", "maine_media_ecosystem", 4, "Amjambo Africa", "Statewide", None,
                     None, None, NP),
                    ("g2", "local_news_catalyst", 2, "Norway Paper", "Norway", None, None, None)))
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "outlets.csv"
        p.outlets.to_csv(path, index=False)
        back = pd.read_csv(path, dtype=str)
    e = btl.locate_by_town(back, PLACES, "lyr", "feature_id", "town_code", "23", "scope")
    by = e.groupby("from_code")["to_code"].apply(set).to_dict()
    assert by["outlet:maine_media_ecosystem:amjambo_africa"] == {"23"}
    assert by["outlet:local_news_catalyst:norway_paper"] == {"23", "23017", "2301754420"}


def test_a_place_with_a_blank_vintage_refuses_across_the_file():
    # the same pandas 3 trap on the places side: a blank vintage beside
    # filled ones must still read as missing (D-231)
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "places.csv"
        blank = PLACES.copy()
        blank.loc[blank["code"] == "2301754420", "vintage"] = None
        blank.to_csv(path, index=False)
        places = pd.read_csv(path, dtype=str)
    f = pd.DataFrame({"feature_id": ["a"], "town_code": ["2301754420"]})
    with pytest.raises(btl.TownLocatedRefused, match="carries no vintage"):
        btl.locate_by_town(f, places, "lyr", "feature_id", "town_code", "23")


def test_a_zip_a_spreadsheet_stripped_gets_its_zero_back():
    # the shape the real export holds (session 11's Turner read): Maine's
    # 04282 written 4282. a ZIP+4 so stripped must not shift into another ZIP
    assert pno._zip5("4282") == "04282"
    assert pno._zip5("4282-1234") == "04282"
    assert pno._zip5("04106") == "04106" and pno._zip5("04106-1234") == "04106"
    assert pno._zip5("041061234") == "04106"
    assert pno._zip5("12") is None and pno._zip5("ME 04106") is None and pno._zip5(None) is None
    df = grouped(("g1", "cision_raw", 5, "Two Cent Times", None, None, "Portland", None, NP,
                  "5 Fern Street", "4282"),
                 ("g2", "cision_raw", 6, "Moose Prints", None, None, "Portland", None, NP,
                  "5 Fern Street", "04282"))
    p = run(df, fallback="office_town_unshared")
    assert listed(p) == {"Two Cent Times": "office_shared", "Moose Prints": "office_shared"}


# ── editions and records written twice (D-254, D-255) ──────────────────────

def test_an_edition_merge_may_hold_one_source_twice_when_it_says_so():
    # the Press Herald: Cision lists the daily and its Sunday edition apart,
    # and two lists name one or the other
    df = grouped(("g1", "maine_media_ecosystem", 43, "Portland Press Herald", "Portland", None, None, None),
                 ("g1", "cision", 140, "Portland Press Herald", None, None, "South Portland", "yes", NP),
                 ("g2", "local_news_catalyst", 3, "Portland Press Herald/Maine Sunday Telegram", "Portland",
                  None, None, None),
                 ("g2", "cision", 143, "Portland Press Herald - Maine Sunday Telegram", None, None,
                  "South Portland", "yes", NP))
    assert len(run(df).outlets) == 2
    merge = {"records": [{"source": "cision", "name": "Portland Press Herald"},
                         {"source": "cision", "name": "Portland Press Herald - Maine Sunday Telegram"}],
             "editions": "the daily and its Sunday edition, one newsroom", **REVIEW}
    p = run(df, reviews={"merges": [merge]})
    assert len(p.outlets) == 1
    r = p.outlets.iloc[0]
    assert r.town_code == "2300560545" and "editions_by_review" in r["flags"]
    assert pno.output_metadata(p)["edition_merges"][0]["editions"].startswith("the daily")


def test_editions_where_no_source_is_twice_refuses():
    df = grouped(("g1", "local_news_catalyst", 2, "A", "Norway", None, None, None),
                 ("g2", "cision", 5, "B", None, None, "Portland", "yes", NP))
    merge = {"records": [{"source": "local_news_catalyst", "name": "A"}, {"source": "cision", "name": "B"}],
             "editions": "print and web", **REVIEW}
    with pytest.raises(pno.OutletsRefused, match="editions would say what is not there"):
        run(df, reviews={"merges": [merge]})


def test_a_record_written_twice_is_not_a_source_held_twice():
    df = grouped(("g1", "local_news_catalyst", 2, "Wiscasset Paper", "Norway", None, None, None),
                 ("g2", "cision", 5, "Wiscasset Paper Inc", None, None, "Portland", "yes", NP),
                 ("g2", "cision", 6, "Wiscasset Paper Inc, The", None, None, "Portland", "yes", NP))
    df["same_record_as"] = [None, None, "5"]
    merge = {"records": [{"source": "local_news_catalyst", "name": "Wiscasset Paper"},
                         {"source": "cision", "name": "Wiscasset Paper Inc"}], **REVIEW}
    p = run(df, reviews={"merges": [merge]})
    assert len(p.outlets) == 1 and "editions_by_review" not in p.outlets.iloc[0]["flags"]


# ── office reads (D-256) ───────────────────────────────────────────────────

OFFICE = grouped(("g1", "cision", 5, "Office Only", None, None, "Portland", "yes", NP))


def _read(verdict, **more):
    return {"source": "cision", "name": "Office Only", "verdict": verdict, **more, **REVIEW}


def test_an_unread_office_town_says_so():
    r = run(OFFICE).outlets.iloc[0]
    assert "office_town_unread" in r["flags"] and "office_town_not_named" in r["flags"]


def test_an_office_read_may_keep_an_outlet_where_it_is():
    p = run(OFFICE, reviews={"office_reads": [_read("keep")]})
    r = p.outlets.iloc[0]
    assert r.placed_by == "office_town" and r.town_code == "2300560545"
    assert "office_read:keep" in r["flags"] and "office_town_unread" not in r["flags"]
    assert r.review_read_by == "Kalli A. Hale"
    assert pno.output_metadata(p)["office_reads"] == {"keep": 1}


def test_an_office_read_may_move_an_outlet_to_its_town():
    r = run(OFFICE, reviews={"office_reads": [_read("town", town_code="2301754420")]}).outlets.iloc[0]
    assert r.placed_by == "reviewed" and r.town_code == "2301754420" and r.county_code == "23017"
    assert "office_read:town" in r["flags"]


def test_an_office_read_may_place_an_outlet_in_the_state_alone():
    p = run(OFFICE, reviews={"office_reads": [_read("state")]})
    r = p.outlets.iloc[0]
    assert r.scope == "state" and pd.isna(r.town_code) and "placed_in_state_only" in r["flags"]
    e = btl.locate_by_town(p.outlets, PLACES, "lyr", "feature_id", "town_code", "23", "scope")
    assert set(e["to_code"]) == {"23"}


def test_an_office_read_may_list_an_outlet_with_its_reason():
    p = run(OFFICE, reviews={"office_reads": [_read("list", reason="a bureau of a daily")]})
    assert p.outlets.empty and listed(p) == {"Office Only": "office_read_listed"}
    assert p.listed[0]["detail"] == "a bureau of a daily"


def test_an_office_read_must_be_whole():
    for bad, words in ((_read("move"), "verdict"), (_read("keep", town_code="2301754420"), "only a town"),
                       (_read("town", town_code="23017"), "not a town"), (_read("list"), "reason")):
        with pytest.raises(pno.OutletsRefused, match=words):
            run(OFFICE, reviews={"office_reads": [bad]})


def test_an_office_read_the_run_no_longer_needs_refuses():
    named = grouped(("g1", "cision", 5, "Office Only", "Norway", None, "Portland", "yes", NP))
    with pytest.raises(pno.OutletsRefused, match="no longer needs"):
        run(named, reviews={"office_reads": [_read("keep")]})
    blog = grouped(("g1", "cision", 5, "Office Only", None, None, "Portland", "yes", "Blog, consumer"))
    with pytest.raises(pno.OutletsRefused, match="no longer needs"):
        run(blog, reviews={"office_reads": [_read("keep")]})
    with pytest.raises(pno.OutletsRefused, match="no longer needs"):
        run(_chain(), fallback="office_town_unshared",
            reviews={"office_reads": [{**_read("keep"), "name": "North Weekly"}]})


def test_one_outlet_takes_one_reading_of_where_it_is():
    town = {"source": "cision", "name": "Office Only", "town_code": "2301754420", **REVIEW}
    with pytest.raises(pno.OutletsRefused, match="already has a reading"):
        run(OFFICE, reviews={"office_reads": [_read("keep")], "towns": [town]})


def test_a_review_names_a_record_written_twice_once():
    df = grouped(("g2", "local_news_catalyst", 2, "Bay Paper", None, None, None, None),
                 ("g2", "cision_raw", 347, "Bay Paper", None, None, "Portland", "yes", NP),
                 ("g2", "cision_raw", 348, "Bay Paper", None, None, "Portland", "yes", NP))
    df["same_record_as"] = [None, None, "347"]
    merge = {"records": [{"source": "local_news_catalyst", "name": "Bay Paper"},
                         {"source": "cision_raw", "name": "Bay Paper"}], **REVIEW}
    with pytest.raises(pno.OutletsRefused, match="already one group"):
        run(df, reviews={"merges": [merge]})
    df.loc[0, "group_id"] = "g9"
    p = run(df, reviews={"merges": [merge]})
    assert len(p.outlets) == 1 and p.outlets.iloc[0].records.count("cision_raw") == 2


# ── a town review may place an outlet in the state alone (D-257) ──────────

def test_a_town_review_may_place_a_listed_outlet_in_the_state_alone():
    df = grouped(("g1", "easton", 3, "Statewide Radio", None, None, None, None))
    assert listed(run(df)) == {"Statewide Radio": "no_town_given"}
    town = {"source": "easton", "name": "Statewide Radio", "state": True, **REVIEW}
    p = run(df, reviews={"towns": [town]})
    r = p.outlets.iloc[0]
    assert r.scope == "state" and pd.isna(r.town_code) and r.placed_by == "reviewed"
    assert "review_settled:no_town_given" in r["flags"] and "placed_in_state_only" in r["flags"]


def test_a_town_review_says_a_town_or_the_state_never_both():
    df = grouped(("g1", "easton", 3, "Statewide Radio", None, None, None, None))
    both = {"source": "easton", "name": "Statewide Radio", "state": True,
            "town_code": "2300560545", **REVIEW}
    with pytest.raises(pno.OutletsRefused, match="never both"):
        run(df, reviews={"towns": [both]})
    neither = {"source": "easton", "name": "Statewide Radio", "state": "yes", **REVIEW}
    with pytest.raises(pno.OutletsRefused, match="not a town"):
        run(df, reviews={"towns": [neither]})
