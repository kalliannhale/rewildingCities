"""
tests/test_derived_margins.py
derived margins, the count kind and the language family (D-258 to D-262).

the arithmetic is the Census's 2025 "Instructions for Applying Statistical
Testing to American Community Survey Data"; canopy/indicators/margins.py is
its one Python home and derive_indicator.R its R twin, held to each other by
tests/test_derive_indicator_oracle.py. these tests need only pandas.
"""
import math
from pathlib import Path

import pandas as pd
import pytest
import yaml

from canopy.indicators import IndicatorRegistry, margins
from canopy.indicators import preview as ip

ROOT = Path(__file__).resolve().parents[1]
SEEDS = ROOT / "seeds" / "indicators"
GEOID = "us_census_geoid"
MAX_GET = 50


def _reg():
    return IndicatorRegistry.load(SEEDS)


def _rows(frame, ind_id):
    rows, _ = ip.derive(frame, _reg().get(ind_id), unit_authority=GEOID,
                        published_by=None, time=None)
    return {r["unit"]["code"]: r for r in rows}


def _broadband_frame(**over):
    base = {"GEOID": ["23001"], "NAME": ["A"],
            "B28002_004E": [800.0], "B28002_001E": [1000.0],
            "B28002_004M": [30.0], "B28002_001M": [20.0]}
    base.update(over)
    return pd.DataFrame(base)


# ── the arithmetic ───────────────────────────────────────────────────────
def test_a_sum_margin_is_the_root_of_summed_squares():
    assert margins.sum_margin([3.0, 4.0]) == 5.0


def test_a_controlled_margin_is_zero_and_an_unknown_one_is_none():
    assert margins.part_margin(None, margins.CONTROLLED) == 0.0
    assert margins.part_margin(None, -222222222) is None
    assert margins.part_margin(7.0, None) == 7.0


def test_the_proportion_and_ratio_formulas_differ_as_the_census_writes_them():
    q, f = margins.quotient_margin(800.0, 30.0, 1000.0, 20.0, "proportion")
    assert f == "proportion"
    assert q == math.sqrt(30.0 * 30.0 - 0.8 * 0.8 * 20.0 * 20.0) / 1000.0
    q, f = margins.quotient_margin(800.0, 30.0, 1000.0, 20.0, "ratio")
    assert f == "ratio"
    assert q == math.sqrt(30.0 * 30.0 + 0.8 * 0.8 * 20.0 * 20.0) / 1000.0


def test_a_proportion_of_one_is_not_derived():
    assert margins.quotient_margin(10.0, 3.0, 10.0, 3.0, "proportion") == (None, None)


# ── through the preview ──────────────────────────────────────────────────
def test_a_derived_margin_feeds_the_cv():
    row = _rows(_broadband_frame(), "cii_broadband")["23001"]
    assert row["moe_status"] == "derived"
    assert row["cv"] == (row["moe"] / 1.645) / abs(row["value"])


def test_a_missing_part_margin_leaves_the_margin_absent():
    row = _rows(_broadband_frame(B28002_001M=[None]), "cii_broadband")["23001"]
    assert row["value"] == 80.0
    assert (row["moe"], row["moe_status"], row["moe_formula"]) == (None, "absent", None)


def test_a_controlled_part_counts_as_zero():
    frame = _broadband_frame(B28002_001M=[None])
    frame["B28002_001M_annotation"] = ["-555555555"]
    row = _rows(frame, "cii_broadband")["23001"]
    assert row["moe"] == math.sqrt(30.0 * 30.0) / 1000.0 * 100.0
    assert row["moe_status"] == "derived"


def test_the_digital_count_is_the_rates_own_complement():
    """D-262: households without broadband are the households the rate
    leaves out, so count and rate tell one story."""
    frame = _broadband_frame()
    count = _rows(frame, "households_without_broadband")["23001"]
    rate = _rows(frame, "cii_broadband")["23001"]
    assert count["value"] == 200.0
    assert abs(count["value"] - 1000.0 * (1 - rate["value"] / 100)) < 1e-9
    assert count["moe"] == math.sqrt(20.0 * 20.0 + 30.0 * 30.0)
    assert (count["moe_status"], count["moe_formula"]) == ("derived", "sum")


def test_a_one_cell_count_carries_its_published_margin():
    frame = pd.DataFrame({"GEOID": ["23001"], "NAME": ["A"],
                          "C16001_001E": [5000.0], "C16001_001M": [40.0],
                          "C16001_005E": [37.0], "C16001_005M": [21.0]})
    row = _rows(frame, "limited_english_spanish")["23001"]
    assert (row["value"], row["moe"], row["moe_status"]) == (37.0, 21.0, "published")
    assert row["moe_formula"] is None


# ── the registry ─────────────────────────────────────────────────────────
def test_every_ratio_declares_its_relation():
    reg = _reg()
    for i in reg.all():
        d = reg.get(i).derivation
        if d.kind == "ratio":
            assert d.relation in ("proportion", "ratio"), i


def test_the_language_family_is_twenty_six_and_fits_one_request():
    """D-261: twelve groups' counts and shares, the total and its share;
    the family's cells, margins and NAME stay under the API's 50."""
    reg = _reg()
    ids = [i for i in reg.all() if i.startswith("limited_english_")
           and i != "limited_english_households"]
    assert len(ids) == 26
    cells = set()
    for i in ids:
        cells.update(reg.get(i).acquisition_variables())
    assert len(cells) + 1 <= MAX_GET
    assert all(c.startswith("C16001_") for c in cells)


def test_the_language_cells_are_the_less_than_very_well_cells():
    """codes read from the 2024 groups API on 2026-11-15: the total and every
    third code from 005 to 038."""
    reg = _reg()
    adds = set(reg.get("limited_english_persons").derivation.numerator)
    assert adds == {f"C16001_{n:03d}E" for n in range(5, 39, 3)}


def test_every_language_universe_is_declared():
    declared = yaml.safe_load((ROOT / "seeds" / "universes" / "universes.yml").read_text())
    reg = _reg()
    for i in reg.all():
        if i.startswith("limited_english_") and i != "limited_english_households":
            assert reg.get(i).rests_on.counts in declared["universes"], i
