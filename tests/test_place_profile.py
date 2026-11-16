"""
tests/test_place_profile.py  |  rewildingCities, Sprint 06 zip 2 (Contract 4, 0.4)

Every place's profile, built from a small bed, held to Contract 4's rules:
all six parts, always, an empty part saying why; every barrier value with
households_behind; every universal verdict with left_out; no threshold
without its kind and source; a borrowed value named as its place's own and
never judged; every margin with its confidence; a tribal area's note; no
standing anywhere. The gate is asked first (D-284): a withheld receipt's
values never enter the file, and part 5 says it exists and why.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
import yaml

from canopy.wonder.session import open_plot

REPO = Path(__file__).resolve().parents[1]
ACS = "2020-2024 (5-year estimates)"
G = "us_census_geoid"
STATE, COUNTY = (G, "23"), (G, "23005")
PORTLAND, OTHER = (G, "2300560545"), (G, "2300512345")
DISTRICT, TRIBAL = ("us_census_sldl", "23118"), ("us_census_aiannh", "2760R")
WITHHELD_COUNT = 77777          # a number only the withheld receipt holds

PLACES = pd.DataFrame([
    {"authority": G, "code": "23", "level": "state", "vintage": "2024", "kind": "state",
     "name": "Maine", "census_funcstat": None, "flags": None, "context_note": None},
    {"authority": G, "code": "23005", "level": "county", "vintage": "2024", "kind": "county",
     "name": "Cumberland County", "census_funcstat": None, "flags": None, "context_note": None},
    {"authority": G, "code": "2300560545", "level": "cousub", "vintage": "2024", "kind": "city",
     "name": "Portland city", "census_funcstat": "F", "flags": None, "context_note": None},
    {"authority": G, "code": "2300512345", "level": "cousub", "vintage": "2024", "kind": "town",
     "name": "Example town", "census_funcstat": "A", "flags": None, "context_note": None},
    {"authority": "us_census_sldl", "code": "23118", "level": "sldl", "vintage": "2024",
     "kind": "house_district", "name": "House District 118", "census_funcstat": None,
     "flags": None, "context_note": None},
    {"authority": "us_census_aiannh", "code": "2760R", "level": "aiannh", "vintage": "2020",
     "kind": "tribal_reservation", "name": "Penobscot Reservation", "census_funcstat": None,
     "flags": None, "context_note": "census_tribal_area"},
    {"authority": "megis_geocode", "code": "01010", "level": "megis_division", "vintage": "2024",
     "kind": "township", "name": "Example Township", "census_funcstat": None,
     "flags": None, "context_note": None},
])
DIVISION = ("megis_geocode", "01010")


def edge(a, b, kind, wp=1.0, wh=1.0):
    return {"from_authority": a[0], "from_code": a[1], "to_authority": b[0], "to_code": b[1],
            "kind": kind, "weight_population": wp, "weight_households": wh,
            "weight_reason": None, "source": "test", "vintage": "2024"}


EDGES = pd.DataFrame([
    edge(STATE, COUNTY, "contains"), edge(COUNTY, PORTLAND, "contains"),
    edge(COUNTY, OTHER, "contains"), edge(PORTLAND, DISTRICT, "overlaps", 0.5, 0.5),
])


def acs(key, indicator, value, moe, households, counts, status="published", formula=None):
    return {"measurement_id": f"{indicator}:{key[0]}:{key[1]}", "unit_authority": key[0],
            "unit_code": key[1], "indicator": indicator, "value": value, "moe": moe,
            "moe_status": status, "moe_formula": formula, "bound": None, "empty_reason": None,
            "households": households, "households_counts": counts, "households_reason": None,
            "cv": None, "reliability_note": None, "published_by": "us_census_acs",
            "method": "derive_indicator:count", "time": ACS}


def count(key, indicator, n, persons, vintage="2024", note=None):
    return {"measurement_id": f"{indicator}:{key[0]}:{key[1]}", "unit_authority": key[0],
            "unit_code": key[1], "indicator": indicator, "value": n / persons * 1000,
            "moe": None, "moe_status": "not_applicable", "bound": None, "empty_reason": None,
            "households": persons, "households_counts": "persons", "households_reason": None,
            "cv": None, "reliability_note": None, "published_by": "rewildingcities",
            "method": "count_located:located_count", "time": "FY 2024",
            "boundary_vintage": vintage, "context_note": note, "count": n}


PERSONS = {STATE: 1_362_359, COUNTY: 303_069, PORTLAND: 68_408, OTHER: 1_000,
           DISTRICT: 9_000, TRIBAL: 600}
TOWN_VALUES = pd.DataFrame([
    acs(PORTLAND, "limited_english_persons", 500, 120, 64_000, "persons 5 years and over"),
    acs(PORTLAND, "limited_english_spanish", 1200, 150, 64_000, "persons 5 years and over"),
    acs(PORTLAND, "limited_english_spanish_share", 2.0, 0.3, 64_000, "persons 5 years and over",
        status="derived", formula="proportion"),
    acs(OTHER, "limited_english_persons", 4, 9, 950, "persons 5 years and over"),
])
COUNTY_VALUES = pd.DataFrame([
    acs(COUNTY, "households_without_broadband", 5000, 400, 120_000, "households"),
    acs(COUNTY, "cii_broadband", 90.0, 1.1, 120_000, "households", status="derived",
        formula="proportion"),
])
LIBRARIES = pd.DataFrame([count(k, "library_outlets_per_1000", 3, p,
                                vintage="2020" if k == TRIBAL else "2024",
                                note="carrier_unseen_on_nations_land" if k == TRIBAL else None)
                          for k, p in PERSONS.items()])
NEWS = pd.DataFrame([count(COUNTY, "news_outlets_per_1000", WITHHELD_COUNT, 303_069)])
LITERACY = pd.DataFrame([{
    "record_id": "county:23005", "level": "county", "unit_authority": G, "unit_code": "23005",
    "name": "Cumberland County", "group": "all", "measure": "literacy_at_or_below_level_1",
    "share": 0.12, "lower": 0.09, "upper": 0.15, "confidence": 0.95, "cv": 0.1,
    "population_16_74": 230000, "left_out": 27600, "left_out_lower": 20700,
    "left_out_upper": 34500, "estimate_kind": "model_based", "period": "PIAAC 2012/2014/2017"}])


def receipt(plot, name, frame, semantic_type, fmt="parquet", **meta):
    data = plot / ".data" / f"{name}.{fmt}"
    (frame.to_parquet(data, index=False) if fmt == "parquet" else frame.to_csv(data, index=False))
    (plot / ".envelopes" / f"{name}.envelope.json").write_text(json.dumps({
        "data": {"path": str(data), "format": fmt},
        "metadata": {"semantic_type": semantic_type, "data_category": "tabular", "crs": None,
                     "row_count": len(frame), "variables": list(frame.columns), **meta},
        "provenance": [], "warnings": []}))


@pytest.fixture
def plot(tmp_path):
    plot = tmp_path / "plots" / "demo"
    (plot / ".data").mkdir(parents=True)
    (plot / ".envelopes").mkdir()
    (plot / "manifest.yml").write_text(yaml.safe_dump({
        "city": {"id": "demo", "name": "demo"}, "crs": {"working": "EPSG:4326"},
        "datasets": {}}))
    receipt(plot, "graph_places_places", PLACES, "places",
            id_fields=["authority", "code"], spatial_unit="place")
    receipt(plot, "graph_edges_edges", EDGES, "place_edges",
            id_fields=["from_authority", "from_code", "to_authority", "to_code"])
    receipt(plot, "cousub_derive_values", TOWN_VALUES, "indicator_values",
            id_field="measurement_id")
    receipt(plot, "county_derive_values", COUNTY_VALUES, "indicator_values",
            id_field="measurement_id")
    receipt(plot, "libraries_counts_values", LIBRARIES, "indicator_values",
            id_field="measurement_id")
    receipt(plot, "carriers_counts_values", NEWS, "indicator_values",
            id_field="measurement_id")
    receipt(plot, "literacy_estimates_estimates", LITERACY, "literacy_estimates", fmt="csv",
            id_field="record_id")
    return plot


def gate(plot, withheld=("carriers_counts_values",)):
    """the gate's answer for this fixture's plot: these receipts are kept
    back, the rest may leave. the gate's own rules are tests/test_gate.py's;
    here only what the profile does with its answer is held."""
    def judge(_plot, *, root=None, sharing_level="public", target="public"):
        refused = {"decision": "refuse", "refusals": [{
            "rule": 3, "semantic_type": "outlet_listing", "tier": "excluded",
            "ancestor": "input 'listing' of stack_outlet_sources",
            "reason": "'outlet_listing' is excluded", "would_admit": "nothing"}]}
        return {p.name[:-len(".envelope.json")]: {
            "semantic_type": "indicator_values",
            "result": refused if p.name.startswith(withheld) else {"decision": "allow"}}
            for p in sorted((plot / ".envelopes").glob("*.envelope.json"))}
    return judge


@pytest.fixture
def built(plot, monkeypatch):
    import canopy.expose.check as check
    from canopy.wonder.profile import build_profiles
    monkeypatch.setattr(check, "judge_receipts", gate(plot))
    _v, loam, _r = open_plot("demo", root=REPO, directory=plot)
    profiles, ctx = build_profiles(loam, "demo", REPO, plot)
    return {p["place_key"]: p for p in profiles}, ctx, loam


def entry(profile, measure):
    return next(e for b in profile["barriers"] for e in b["indicators"]
                if e["measure"] == measure)


def walk(x):
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk(v)


# ── every place, every part ───────────────────────────────────────────────
def test_every_place_is_profiled_in_level_order(built):
    profiles, _ctx, _loam = built
    assert list(profiles) == [f"{a}:{c}" for a, c in (STATE, COUNTY, OTHER, PORTLAND, DISTRICT,
                                                       TRIBAL, DIVISION)]


def test_a_level_outside_contract_4_is_profiled_and_says_so(built):
    p = built[0]["megis_geocode:01010"]
    assert "groundwork" in p["header"]["place"]["level_note"]
    assert "level_note" not in built[0][f"{G}:23005"]["header"]["place"]


def test_all_six_parts_always_and_an_empty_part_says_why(built):
    for p in built[0].values():
        for part in ("header", "represented", "barriers", "carriers", "disagreements",
                     "cannot_answer", "channels"):
            assert part in p, part
        assert p["channels"]["pairings"] == [] and "P-2" in p["channels"]["empty_because"]
        assert p["channels"]["label"] == "standard outreach practice, not a finding"
        if not p["disagreements"]["entries"]:
            assert p["disagreements"]["empty_because"]
        c = p["cannot_answer"]
        assert any(c[k] for k in ("gaps", "not_acquired", "cannot_judge", "refusals")) or \
            c.get("nothing_missing")


def test_every_barrier_value_carries_households_behind(built):
    for p in built[0].values():
        for b in p["barriers"]:
            for e in b["indicators"]:
                assert "households_behind" in e, (p["place_key"], e["measure"])


def test_every_universal_verdict_carries_left_out(built):
    for p in built[0].values():
        for b in p["barriers"]:
            universal = {s["judges"] for s in b["sides"] if s["kind"] == "universal"}
            for e in b["indicators"]:
                if e["measure"] in universal:
                    assert "left_out" in e, (p["place_key"], e["measure"])


def test_no_threshold_without_its_kind_and_source(built):
    for p in built[0].values():
        for b in p["barriers"]:
            assert b["sides"]
            for s in b["sides"]:
                assert s["kind"] in ("universal", "trigger", "none") and s["source"]["name"]


def test_every_margin_states_its_confidence(built):
    for p in built[0].values():
        for d in walk(p):
            if d.get("margin") is not None or d.get("interval") is not None:
                assert d.get("confidence") is not None, d


def test_no_profile_carries_a_standing(built):
    text = json.dumps(list(built[0].values())).lower()
    for word in ("standing", "percentile", "z_score", "zscore", "rank"):
        assert f'"{word}' not in text, word


# ── verdicts, as the standard says ────────────────────────────────────────
def test_a_towns_universal_count_is_below_with_its_left_out(built):
    e = entry(built[0][f"{G}:2300560545"], "limited_english_persons")
    assert e["verdict"]["verdict"] == "below"
    assert e["left_out"]["lower"] == 380 and e["left_out"]["confidence"] == 0.9
    assert entry(built[0][f"{G}:2300560545"], "limited_english_persons_share")["judged_on"] == \
        "limited_english_persons"


def test_a_small_count_is_within_margin_never_meets(built):
    e = entry(built[0][f"{G}:2300512345"], "limited_english_persons")
    assert e["verdict"]["verdict"] == "within_margin"
    assert "does not show that everyone is reached" in e["verdict"]["says"]


def test_a_language_group_crosses_the_safe_harbor_by_its_margins(built):
    p = built[0][f"{G}:2300560545"]
    e = entry(p, "limited_english_spanish")
    assert (e["verdict"]["verdict"], e["verdict"]["tier"]) == ("crosses", "translate")
    assert entry(p, "limited_english_spanish_share")["judged_on"] == "limited_english_spanish"
    harbor = next(s for b in p["barriers"] for s in b["sides"] if s["id"] == "doj_safe_harbor")
    assert harbor["crosses"] == [{"group": "Spanish", "tier": "translate", "persons": 1200}]


def test_a_county_literacy_is_its_own_and_judged_by_its_bounds(built):
    e = entry(built[0][f"{G}:23005"], "literacy_at_or_below_level_1")
    assert e["value"] == 0.12 and e["uncertainty"]["method"] == "credible_interval"
    assert e["verdict"]["verdict"] == "below" and e["left_out"]["lower"] == 20700


def test_a_borrowed_value_names_its_place_and_is_never_judged(built):
    e = entry(built[0]["us_census_sldl:23118"], "literacy_at_or_below_level_1")
    assert e["value"] is None
    assert [b["place"]["code"] for b in e["borrowed_from"]] == ["23005"]
    assert e["borrowed_from"][0]["share"] == 1.0 and e["borrowed_from"][0]["value"] == 0.12
    assert e["verdict"]["verdict"] == "cannot_judge" and "D-276" in e["verdict"]["reason"]
    assert e["left_out"]["count"] is None


def test_a_barrier_of_kind_none_judges_nothing(built):
    e = entry(built[0][f"{G}:23005"], "library_outlets_per_1000")
    assert e["verdict"]["verdict"] == "no_threshold"


# ── the gate first (D-284) ────────────────────────────────────────────────
def test_a_withheld_receipts_values_never_enter_and_part_5_says_why(built):
    profiles, ctx, _loam = built
    assert str(WITHHELD_COUNT) not in json.dumps(list(profiles.values()))
    county = profiles[f"{G}:23005"]
    news = next(c for c in county["carriers"] if c["indicator"] == "news_outlets_per_1000")
    assert news["withheld"] and news["count"] is None
    refusal = county["cannot_answer"]["refusals"]
    assert [r["receipt"] for r in refusal] == ["carriers_counts_values"]
    assert refusal[0]["refusals"][0]["tier"] == "excluded"
    assert "carriers_counts_values" not in ctx.read


def test_refusals_are_said_for_every_place_they_touch_not_only_the_first(built):
    profiles, _ctx, _loam = built
    assert not profiles[f"{G}:2300560545"]["cannot_answer"]["refusals"]
    assert profiles[f"{G}:23005"]["cannot_answer"]["refusals"]


# ── who is represented, carriers ──────────────────────────────────────────
def test_population_is_the_census_count_every_rate_divides_by(built):
    p = built[0][f"{G}:23005"]
    assert p["represented"]["population"]["count"] == 303_069
    assert "P1_001N" in p["represented"]["population"]["release"]
    assert p["represented"]["households"]["count"] == 120_000
    assert "D-286" in p["represented"]["households"]["why_no_margin"]
    assert p["represented"]["legislators"]["status"] == "not_held"


def test_a_tribal_area_carries_its_note_and_its_counts_note(built):
    p = built[0]["us_census_aiannh:2760R"]
    assert p["header"]["context_note"]["id"] == "census_tribal_area"
    assert p["header"]["context_note"]["text"]
    library = next(c for c in p["carriers"] if c["indicator"] == "library_outlets_per_1000")
    assert library["context_note"]["id"] == "carrier_unseen_on_nations_land"


def test_a_county_reads_its_towns_with_the_range_statement(built):
    p = built[0][f"{G}:23005"]
    e = entry(p, "households_without_broadband")
    assert e["verdict"]["verdict"] == "below"
    assert "one estimate per town" in e["towns"]["statement"]
    assert e["towns"]["touching"] == 2
    assert {c["code"] for c in p["represented"]["inside"]} == {"2300560545", "2300512345"}


# ── part 4 alone ──────────────────────────────────────────────────────────
def test_two_publishers_of_one_measure_are_both_shown_never_picked():
    from canopy.indicators import IndicatorRegistry
    from canopy.wonder.profile import Value, _part_disagreements
    registry = IndicatorRegistry.load(REPO / "seeds" / "indicators")
    ctx = SimpleNamespace(registry=registry, take=lambda r: None)
    values = {
        "cii_broadband": Value("cii_broadband", {"value": 90.0, "published_by": "us_census_acs",
                                                 "time": ACS}, "a"),
        "cii_pub_broadband": Value("cii_pub_broadband", {"value": 88.5,
                                                         "published_by": "cii_2026",
                                                         "time": "2026"}, "b"),
    }
    (d,) = _part_disagreements(ctx, values)
    assert d["measures"] == "household_broadband_subscription"
    assert [v["value"] for v in d["values"]] == [90.0, 88.5]
    assert d["difference"] == pytest.approx(1.5) and d["reason"] == "unknown"


# ── the artifact and its receipt (D-274) ──────────────────────────────────
def test_the_artifact_lists_what_it_read_and_never_a_withheld_input(built, plot):
    from canopy.envelope import validate_envelope
    from canopy.wonder.profile import write_profiles
    profiles, ctx, _loam = built
    written = write_profiles(list(profiles.values()), ctx, started=0.0)
    env = json.loads((plot / ".envelopes" / "place_profile_profiles.envelope.json").read_text())
    assert validate_envelope(env, REPO) == []
    own = env["provenance"][-1]
    assert own["primitive"] == "build_profile"
    assert "carriers_counts_values" not in {i["name"] for i in own["inputs"]}
    assert own["params"]["receipts_withheld"] == ["carriers_counts_values"]
    assert env["metadata"]["semantic_type"] == "place_profile"
    assert "census_tribal_area" in env["metadata"]["row_context_notes"]
    assert set(env["metadata"]["row_context_notes"]) <= set(env["metadata"]["context_notes"])
    data = json.loads((plot / ".data" / "place_profile_profiles.json").read_text())
    assert len(data["places"]) == written["places"] == 7
    assert {"graph_places_places", "graph_edges_edges"} <= {i["name"] for i in own["inputs"]}
    assert written["structure_withheld"] == []


def test_the_structure_is_an_input_even_when_the_gate_withholds_it(plot, monkeypatch):
    import canopy.expose.check as check
    from canopy.wonder.profile import build_profiles, write_profiles
    monkeypatch.setattr(check, "judge_receipts",
                        gate(plot, withheld=("carriers_counts_values", "graph_places_places")))
    _v, loam, _r = open_plot("demo", root=REPO, directory=plot)
    profiles, ctx = build_profiles(loam, "demo", REPO, plot)
    written = write_profiles(profiles, ctx, started=0.0)
    assert written["structure_withheld"] == ["graph_places_places"]
    env = json.loads((plot / ".envelopes" / "place_profile_profiles.envelope.json").read_text())
    assert "graph_places_places" in {i["name"] for i in env["provenance"][-1]["inputs"]}
    assert env["provenance"][-1]["params"]["structure_withheld"] == ["graph_places_places"]


def test_a_long_build_says_how_far_it_has_come(plot, monkeypatch):
    import canopy.expose.check as check
    from canopy.wonder.profile import build_profiles
    monkeypatch.setattr(check, "judge_receipts", gate(plot))
    _v, loam, _r = open_plot("demo", root=REPO, directory=plot)
    seen = []
    build_profiles(loam, "demo", REPO, plot, progress=lambda done, total: seen.append((done, total)))
    assert seen == [(n, 7) for n in range(1, 8)]
