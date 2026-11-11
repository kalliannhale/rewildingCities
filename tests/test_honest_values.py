"""
tests/test_honest_values.py

Sprint 02, the Python half. Every value says what it rests on (item 2): the
count of households behind it, from its declared `rests_on`, or why there is
none. A declared small-sample rule (item 3, D-106) adds a plain-words note: a
household count everywhere a count exists, a coefficient of variation wherever
the Census published a margin. Every indicator declares one role (item 7,
D-107). The R half is held to the same numbers by
tests/test_derive_indicator_oracle.py.

Runs without R, pyarrow or network.
"""

from pathlib import Path

import pandas as pd
import pytest

from canopy.indicators import IndicatorRegistry
from canopy.indicators import preview as ip

GEOID = "us_census_geoid"

SEEDS = Path(__file__).resolve().parents[1] / "seeds" / "indicators"
RULE = {"min_households": 50, "max_cv": 0.40}


def registry():
    return IndicatorRegistry.load(SEEDS)


# ── the declarations ─────────────────────────────────────────────────────
def test_every_indicator_declares_one_role_and_what_it_rests_on():
    reg = registry()
    for iid in reg.all():
        ind = reg.get(iid)
        assert ind.role in ("need", "barrier", "carrier", "outcome", "context"), iid
        ro = ind.rests_on
        assert (ro.not_published is not None) != bool(ro.add), iid
        if ro.add:
            assert ro.counts, iid


def test_a_ratio_rests_on_its_denominator():
    for iid, den in [("cii_broadband", "B28002_001E"), ("cii_no_vehicle", "B08201_001E"),
                     ("limited_english_households", "C16002_001E")]:
        ind = registry().get(iid)
        assert ind.rests_on.add == (den,) and ind.rests_on.counts == "households"


def test_rent_burden_rests_on_its_universe_and_fetches_it():
    ind = registry().get("cii_rent_burden")
    assert ind.rests_on.add == ("B25070_001E",)
    assert ind.rests_on.subtract == ("B25070_011E",)
    # fetched with the value, so an acquisition without it reads as stale
    assert {"B25070_001E", "B25070_011E"} <= set(ind.acquisition_variables())


def test_cii_published_values_say_their_count_is_not_published():
    ind = registry().get("cii_pub_rent_burden")
    assert ind.rests_on.not_published and not ind.rests_on.add


@pytest.mark.parametrize("bad, match", [
    ("rests_on: {}", "rests_on needs add"),
    ("rests_on: {add: [X_001E]}", "rests_on needs counts"),
    ("rests_on: {add: [X_001E], counts: households, extra: 1}", "unknown rests_on"),
    ("rests_on: {not_published: ''}", "not_published"),
    ("role: mood", "role"),
])
def test_malformed_role_or_rests_on_is_refused(tmp_path, bad, match):
    key = bad.split(":")[0]
    good = {"role": "role: barrier",
            "rests_on": "rests_on: {add: [X_001E], counts: households}"}
    good[key] = bad
    (tmp_path / "t.yml").write_text(f"""
indicators:
  t:
    name: t
    defined_by: test
    measures: t
    {good['role']}
    {good['rests_on']}
    unit: percent
    derivation: {{kind: passthrough, column: X_002E}}
    direction: higher_is_worse
    aggregation: none
    uncertainty: none
    source: {{provider: census_acs}}
""")
    with pytest.raises(ValueError, match=match):
        IndicatorRegistry.load(tmp_path)


def test_a_missing_role_or_rests_on_is_refused(tmp_path):
    (tmp_path / "t.yml").write_text("""
indicators:
  t:
    name: t
    defined_by: test
    measures: t
    unit: percent
    derivation: {kind: passthrough, column: X_002E}
    direction: higher_is_worse
    aggregation: none
    uncertainty: none
    source: {provider: census_acs}
""")
    with pytest.raises(ValueError, match="role, rests_on"):
        IndicatorRegistry.load(tmp_path)


# ── the derivation ───────────────────────────────────────────────────────
def broadband_frame():
    return pd.DataFrame({
        "GEOID": ["2300100001", "2300100002", "2300100003"],
        "NAME": ["big town", "small town", "no count"],
        "B28002_004E": [900.0, 20.0, 5.0],
        "B28002_001E": [1000.0, 30.0, None],
        "B28002_004M": [40.0, 9.0, 4.0],
        "B28002_001M": [30.0, 8.0, None],
    })


def test_every_value_carries_its_household_count_or_why_not():
    ind = registry().get("cii_broadband")
    rows, _ = ip.derive(broadband_frame(), ind, unit_authority=GEOID, authority=None, time=None)
    by = {r["unit"]["code"]: r for r in rows}
    assert by["2300100001"]["households"] == 1000.0
    assert by["2300100001"]["households_counts"] == "households"
    assert by["2300100002"]["households"] == 30.0
    assert by["2300100003"]["households"] is None
    assert by["2300100003"]["households_reason"] == "source count empty: B28002_001E"


def test_rent_burden_count_is_its_universe_less_not_computed():
    ind = registry().get("cii_rent_burden")
    frame = pd.DataFrame({
        "GEOID": ["23005"], "NAME": ["Cumberland"],
        "B25071_001E": [29.4], "B25071_001M": [1.2],
        "B25070_001E": [30000.0], "B25070_011E": [1500.0],
        "B25071_001M_annotation": [None],
    })
    rows, _ = ip.derive(frame, ind, unit_authority=GEOID, authority=None, time=None)
    assert rows[0]["households"] == 28500.0


def test_the_count_rule_fires_below_its_floor_and_says_so():
    ind = registry().get("cii_broadband")
    rows, _ = ip.derive(broadband_frame(), ind, unit_authority=GEOID, authority=None, time=None, reliability=RULE)
    by = {r["unit"]["code"]: r for r in rows}
    assert by["2300100001"]["reliability_note"] is None
    note = by["2300100002"]["reliability_note"]
    assert note.startswith("read with care") and "30 households" in note and "50" in note
    # a ratio has no derived margin (D-18), so no CV and no CV test
    assert by["2300100002"]["cv"] is None and "coefficient" not in note


def test_the_cv_rule_fires_where_a_margin_is_published():
    ind = registry().get("cii_rent_burden")
    frame = pd.DataFrame({
        "GEOID": ["23001", "23002"], "NAME": ["steady", "wide"],
        "B25071_001E": [30.0, 30.0], "B25071_001M": [1.0, 25.0],
        "B25070_001E": [5000.0, 5000.0], "B25070_011E": [0.0, 0.0],
        "B25071_001M_annotation": [None, None],
    })
    rows, _ = ip.derive(frame, ind, unit_authority=GEOID, authority=None, time=None, reliability=RULE)
    by = {r["unit"]["code"]: r for r in rows}
    assert by["23001"]["reliability_note"] is None
    assert by["23002"]["cv"] == pytest.approx((25.0 / 1.645) / 30.0)
    assert "coefficient of variation" in by["23002"]["reliability_note"]


def test_no_rule_declared_means_no_note():
    ind = registry().get("cii_broadband")
    rows, _ = ip.derive(broadband_frame(), ind, unit_authority=GEOID, authority=None, time=None)
    assert all(r["reliability_note"] is None for r in rows)


def test_an_open_ended_median_stands_outside_the_ranking():
    ind = registry().get("cii_rent_burden")
    frame = pd.DataFrame({
        "GEOID": ["13141", "23005", "23001"], "NAME": ["open", "a", "b"],
        "B25071_001E": [51.0, 29.4, 31.0], "B25071_001M": [None, 1.2, 1.0],
        "B25070_001E": [100.0, 30000.0, 9000.0], "B25070_011E": [0.0, 0.0, 0.0],
        "B25071_001M_annotation": ["-333333333", None, None],
    })
    rows, _ = ip.derive(frame, ind, unit_authority=GEOID, authority=None, time=None)
    out, population = ip.standings(rows, ind, sd="sample")
    by = {r["unit"]["code"]: r for r in out}
    assert by["13141"]["percentile"] is None and by["13141"]["outside_reason"]
    # ranked among the two counties with a measurement, not three
    assert population["n"] == 2


def test_a_standing_keeps_what_its_value_rests_on():
    ind = registry().get("cii_rent_burden")
    frame = pd.DataFrame({
        "GEOID": ["23001", "23002", "23003"], "NAME": ["a", "b", "small"],
        "B25071_001E": [30.0, 28.0, 33.0], "B25071_001M": [1.0, 1.0, 2.0],
        "B25070_001E": [5000.0, 4000.0, 30.0], "B25070_011E": [0.0, 0.0, 0.0],
        "B25071_001M_annotation": [None, None, None],
    })
    rows, _ = ip.derive(frame, ind, unit_authority=GEOID, authority=None, time=None, reliability=RULE)
    out, _ = ip.standings(rows, ind, sd="sample")
    by = {r["unit"]["code"]: r for r in out}
    assert by["23003"]["households"] == 30.0 and by["23003"]["percentile"] is not None
    assert "30 renter households" in by["23003"]["reliability_note"]
    assert by["23001"]["households_counts"] == "renter households with rent burden computed"
