"""
tests/test_telling.py ~ a profile told in plain sentences (Sprint 09)

the explorer's fields come from canopy/wonder/telling.py. these tests hold
them to seeds/language/plain_language.yml: no ledger id and no claim word in
any field, a missing value never said as a number, a tribal area's notes
carried and marked as drafts, a split town named in every district it
touches. when the plot's real profiles are on disk, every place is also
held to the reading-level ceiling and the size the explorer's item can carry.
"""

from __future__ import annotations

import json
import re
import statistics
from pathlib import Path

import pytest

from canopy.wonder.telling import (EXPLORER_LEVELS, Language, TellingContext, amount,
                                   reading_grade, short_name, tell, tell_all)

REPO = Path(__file__).resolve().parents[1]
REAL = REPO / "plots" / "maine" / ".data" / "place_profile_profiles.json"
META = ("key", "authority", "code", "name", "level", "profile_version", "built_at")
ROW_BYTES, ITEM_BYTES = 8_000, 4_000_000


def _barrier(bid, words, entries):
    return {"barrier": bid, "words": words, "sides": [], "indicators": entries}


def _entry(measure, verdict, says, value=None, unit=None, name=None):
    e = {"measure": measure, "value": value, "unit": unit,
         "verdict": {"verdict": verdict, "says": says}}
    if name:
        e["name"] = name
    return e


def profile(code="2300528870", level="cousub", kind="town", name="Gray town", *,
            note=None, overlapping=(), needs=(), carriers=None, barriers=None,
            not_acquired=(), refusals=(), flags=()):
    return {
        "place_key": f"us_census_geoid:{code}",
        "header": {"place": {"authority": "us_census_geoid", "code": code, "level": level,
                             "kind": kind, "name": name, "vintage": "2024"},
                   "flags": list(flags), "context_note": note},
        "represented": {
            "population": {"count": 8269.0}, "households": {"count": 3656.0,
                                                            "release": "2020-2024 (5-year estimates)"},
            "needs": list(needs), "inside": [], "overlapping": list(overlapping),
            "legislators": {"status": "not_held", "why": "the 133rd Legislature's rosters are "
                            "acquired on or after 2026-12-02 (TRIBE-4, SEN-1)"}},
        "barriers": barriers if barriers is not None else [
            _barrier("requires_digital_access", "requires digital access", [
                _entry("households_without_broadband", "within_margin",
                       "the data cannot say whether any households here fall short (D-272)",
                       value=120.0, unit="households",
                       name="Households without broadband of any type"),
                _entry("fcc_served_100_20", "cannot_judge",
                       "this cannot be judged here: not acquired: step 7b, the FCC map (P-6)")])],
        "carriers": carriers if carriers is not None else [
            {"type": "library_outlet", "count": 1}, {"type": "news_outlet", "count": 0},
            {"type": "health_center_site", "count": None}],
        "disagreements": {"entries": []},
        "cannot_answer": {
            "gaps": [{"holding": "seats", "why": "rosters after 2026-12-02 (TRIBE-4)"}],
            "not_acquired": list(not_acquired) or [
                {"measure": "fcc_served_100_20", "status": "acquirable",
                 "source": "FCC National Broadband Map", "needs": "step 7b (P-6)"},
                {"measure": "outlet_last_post", "status": "needs_our_model",
                 "source": "our own observation", "needs": "OBS-1 (D-294)"}],
            "cannot_judge": [], "refusals": list(refusals)},
        "channels": {"pairings": [], "empty_because": "the pairing table (P-2) waits"},
    }


def doc(*places):
    return {"profile_version": "0.4.0", "built_at": "2026-11-18T00:00:00+00:00",
            "places": list(places)}


@pytest.fixture
def ctx():
    return TellingContext.load(doc(), REPO)


def told(*places):
    rows, _ = tell_all(doc(*places), REPO)
    return rows


def _fields(row):
    return {k: v for k, v in row.items() if k not in META}


# ── the register ──────────────────────────────────────────────────────────
def test_every_field_is_a_string_and_none_is_empty():
    [row] = told(profile())
    assert all(isinstance(v, str) and v.strip() for v in row.values())


def test_no_working_id_reaches_a_field():
    lang = Language.load(REPO)
    [row] = told(profile())
    for k, v in _fields(row).items():
        assert not lang.working_ids.search(v), (k, v)


def test_no_claim_word_reaches_a_field():
    lang = Language.load(REPO)
    [row] = told(profile())
    for k, v in _fields(row).items():
        words = set(re.findall(r"[a-z]+", v.lower()))
        assert not words & set(lang.claim_words), (k, v)


def test_the_id_pattern_finds_ledger_ids_steps_and_census_codes():
    lang = Language.load(REPO)
    for s in ("D-271", "OBS-1", "P-6", "TRIBE-4", "step 7b", "B25071_001E", "rule 5"):
        assert lang.working_ids.search(f"before {s} after"), s
    assert not lang.working_ids.search("100/20 Mbps in 2020-2024, at 32.5%")


def test_reading_grade_tells_plain_from_dense():
    assert reading_grade("The town has one library. It has four schools.") < 5
    assert reading_grade("Notwithstanding methodological heterogeneity, institutional "
                         "infrastructures characteristically necessitate interdisciplinary "
                         "operationalization.") > 15


# ── gaps are said, never drawn as zero ────────────────────────────────────
def test_a_missing_need_is_said_and_never_a_number():
    [row] = told(profile(needs=[{"measure": "cii_rent_burden", "value": None, "bound": None,
                                 "name": "Median gross rent as a percentage of household income",
                                 "why": "source value empty: B25071_001E"}]))
    assert "no estimate" in row["needs"] and "B25071" not in row["needs"]
    assert not re.search(r"\d", row["needs"])


def test_an_open_ended_value_keeps_the_sources_words():
    [row] = told(profile(needs=[{"measure": "cii_rent_burden", "value": None,
                                 "bound": "50.0 or more", "name": "Median gross rent"}]))
    assert "50.0 or more" in row["needs"] and "only this bound" in row["needs"]


def test_a_count_of_zero_is_none_listed_and_a_missing_count_is_not_available():
    [row] = told(profile())
    assert "1 public library" in row["carriers"]
    assert "Local news outlets: none listed" in row["carriers"]
    assert "Health center sites: not available" in row["carriers"]


def test_a_measure_not_held_is_told_from_its_status_and_source():
    [row] = told(profile())
    b = row["barrier_requires_digital_access"]
    assert "cannot say whether any households" in b
    assert "Not yet added. Source: FCC National Broadband Map." in row["cannot_answer"]
    assert "No published source records this yet." in row["cannot_answer"]


def test_seats_are_said_with_their_date_in_words():
    [row] = told(profile())
    assert "December 2, 2026" in row["represented"]


def test_a_withheld_layer_is_named_with_its_reason():
    [row] = told(profile(refusals=[{"receipt": "outlets_listing", "semantic_type": "outlet_listing",
                                    "refusals": [{"rule": 5, "reason":
                                                  "named members may not leave (rule 5)"}]}]))
    assert "Withheld: outlet listing." in row["cannot_answer"]
    assert "Named members may not leave." in row["cannot_answer"]
    assert "rule" not in row["cannot_answer"]


# ── shares (D-76) ─────────────────────────────────────────────────────────
def _edge(frm, to, w):
    return {"from": {"code": frm}, "to": {"code": to}, "weight_population": w}


def test_a_split_town_names_every_district_it_touches_with_its_share():
    town = profile(overlapping=[
        {"authority": "megis", "code": "05100", "name": "Gray", "level": "megis_division",
         "edge": _edge("05100", "2300528870", 1.0)},
        {"authority": "us_census_sldl", "code": "23104", "level": "sldl",
         "name": "State House District 104 (2024); Maine", "edge": _edge("2300528870", "23104", 0.4025)},
        {"authority": "us_census_sldl", "code": "23105", "level": "sldl",
         "name": "State House District 105 (2024); Maine", "edge": _edge("2300528870", "23105", 0.5975)}])
    [row] = told(town)
    assert "House District 104: 40.2% of the people here." in row["shares"]
    assert "House District 105: 59.8% of the people here." in row["shares"]
    assert "Gray:" not in row["shares"]                        # civil divisions stay out


def test_a_district_names_its_towns_with_how_much_of_each_lives_there():
    district = profile(code="23105", level="sldl", kind="house_district",
                       name="State House District 105 (2024); Maine", overlapping=[
                           {"authority": "us_census_geoid", "code": "2300528870", "level": "cousub",
                            "name": "Gray town", "edge": _edge("2300528870", "23105", 0.5975)}])
    [row] = told(district)
    assert row["shares"].startswith("Towns in this district.")
    assert "Gray town: 59.8% of its people live here." in row["shares"]


def test_a_district_name_is_said_as_a_reader_would():
    assert short_name("State Senate District 25 (2024); Maine") == "Senate District 25"
    assert short_name("Gray town") == "Gray town"


# ── tribal areas (D-72, D-171, TRIBE-7) ───────────────────────────────────
def tribal():
    return profile(code="2760R", level="aiannh", kind="tribal_trust_land",
                   name="Aroostook Band of Micmac Trust Land",
                   note={"id": "census_tribal_area",
                         "text": "This boundary is the U.S. Census Bureau's, not the nation's own."},
                   carriers=[{"type": "library_outlet", "count": 0,
                              "context_note": {"id": "carrier_unseen_on_nations_land",
                                               "text": "A zero here cannot be trusted."}}])


def test_a_tribal_area_carries_its_note_and_its_carriers_draft_note():
    [row] = told(tribal())
    assert row["level"] == "Census tribal area"
    assert "Census Bureau's, not the nation's own" in row["note"]
    assert "Draft wording: A zero here cannot be trusted." in row["carriers"]


def test_a_tribal_area_carries_the_draft_note_on_representation():
    [row] = told(tribal())
    assert "Draft wording:" in row["represented"] and "Mi'kmaq Nation" in row["represented"]
    [town] = told(profile())
    assert "Wabanaki" not in town["represented"]


def test_a_reviewed_note_is_not_marked_as_a_draft():
    [row] = told(tribal())
    assert not row["note"].startswith("Draft wording")


# ── which places ──────────────────────────────────────────────────────────
def test_civil_divisions_stay_out_and_are_counted():
    rows, ctx = tell_all(doc(profile(), profile(code="05100", level="megis_division",
                                                kind="civil_division", name="Gray")), REPO)
    assert [r["level"] for r in rows] == ["Town or city"]
    assert ctx.skipped == {"megis_division": 1}
    assert set(EXPLORER_LEVELS) == {"state", "county", "cousub", "sldl", "sldu", "aiannh"}


def test_an_amount_says_its_unit_once():
    assert amount(3.0, "percent_of_households", said_in="Households with no vehicle") == "3.0%"
    assert amount(0.12, "share_of_adults_16_to_74") == "12.0% of adults 16 to 74"
    assert amount(0.121, "per_1000_persons") == "0.12 per 1,000 persons"
    assert amount(None, "households") == "no value"


# ── the real profiles, when they are on disk ──────────────────────────────
@pytest.fixture
def real():
    if not REAL.is_file():
        pytest.skip("the plot's profiles are not built here")
    return tell_all(json.loads(REAL.read_text()), REPO)


def test_every_real_place_is_told_within_the_items_size(real):
    rows, _ = real
    sizes = [len(json.dumps(r, ensure_ascii=False).encode()) for r in rows]
    assert max(sizes) <= ROW_BYTES and sum(sizes) <= ITEM_BYTES


def test_every_real_field_meets_the_reading_ceiling_at_its_median_place(real):
    rows, ctx = real
    masked = {}
    for r in rows:
        for k, v in _fields(r).items():
            masked.setdefault(k, []).append(reading_grade(re.sub(r"\b[A-Z][\w'’-]*", "Name", v)))
    over = {k: round(statistics.median(v), 1) for k, v in masked.items()
            if statistics.median(v) > ctx.language.ceiling}
    assert not over, over


def test_no_real_field_carries_an_id_or_a_claim_word(real):
    rows, ctx = real
    for r in rows:
        for k, v in _fields(r).items():
            assert not ctx.language.working_ids.search(v), (r["key"], k, v)
            assert not set(re.findall(r"[a-z]+", v.lower())) & set(ctx.language.claim_words)
