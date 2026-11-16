"""
tests/test_verdicts.py  |  rewildingCities, Sprint 06 zip 2 (D-272, D-273, D-276)

The rules a profile judges with, as numbers in and verdicts out. A universal
side counts the people short of its line against zero: below when the count
less its margin is above zero, within_margin otherwise, and never meets
(D-272). A trigger is judged per group over every value its margins allow,
naming only tiers a value inside could truly be in (D-273). A borrowed
value's shares are residents, never another count (D-276).
"""

import pytest

from canopy.wonder.verdicts import (MEETS_UNREACHABLE, as_published, borrowed_shares,
                                    comparable, tiers_within, trigger_on_group,
                                    universal_on_count, universal_on_interval)

SAFE_HARBOR = [
    {"id": "translate", "says": "written translation",
     "when_any": [{"persons": 1000}, {"share": 5, "persons": 50}]},
    {"id": "written_notice", "says": "written notice of free interpretation",
     "when_any": [{"share": 5}]},
]
NOTHING = "nothing written is asked"


def group(persons, share):
    return trigger_on_group({"persons": persons, "share": share}, SAFE_HARBOR,
                            below_every_tier=NOTHING)


# ── universal (D-272) ─────────────────────────────────────────────────────
def test_a_count_whose_margin_clears_zero_is_below():
    v = universal_on_count(500, 120, counts="persons", confidence=0.9)
    assert v.verdict == "below"
    assert v.left_out == {"count": 500, "lower": 380, "upper": 620, "counts": "persons",
                          "confidence": 0.9, "bounds": "estimate less and plus its margin"}
    assert "at least 380 persons" in v.says


@pytest.mark.parametrize("estimate, moe", [(80, 120), (0, 13), (120, 120)])
def test_a_count_whose_margin_reaches_zero_is_within_margin_never_meets(estimate, moe):
    v = universal_on_count(estimate, moe, counts="persons", confidence=0.9)
    assert v.verdict == "within_margin"
    assert "does not show that everyone is reached" in v.says
    assert v.left_out["lower"] == 0


def test_meets_is_never_reached_and_says_why():
    seen = {universal_on_count(e, m, counts="persons", confidence=0.9).verdict
            for e in (0, 1, 50, 10_000) for m in (0, 1, 30)}
    assert "meets" not in seen
    assert "never" in MEETS_UNREACHABLE


@pytest.mark.parametrize("estimate, moe, reason", [
    (None, 10, "no estimate"), (10, None, "no margin"), (float("nan"), 3, "no estimate"),
    (-1, 3, "negative")])
def test_a_count_that_cannot_be_judged_says_why(estimate, moe, reason):
    v = universal_on_count(estimate, moe, counts="persons", confidence=0.9)
    assert v.verdict == "cannot_judge" and reason in v.reason


def test_a_models_count_is_judged_by_its_credible_bounds():
    assert universal_on_interval(12926, 9852, 16158, counts="adults",
                                 confidence=0.95).verdict == "below"
    assert universal_on_interval(40, 0, 90, counts="adults",
                                 confidence=0.95).verdict == "within_margin"
    assert universal_on_interval(40, 50, 90, counts="adults",
                                 confidence=0.95).verdict == "cannot_judge"


# ── trigger (D-273) ───────────────────────────────────────────────────────
def test_a_group_whose_whole_margin_is_in_one_tier_crosses_it():
    v = group((1500, 100), (2, 0.5))
    assert (v.verdict, v.tier) == ("crosses", "translate")
    v = group((30, 10), (6, 0.5))
    assert (v.verdict, v.tier) == ("crosses", "written_notice")


def test_a_group_below_every_tier_at_both_ends_does_not_cross():
    v = group((10, 5), (0.1, 0.1))
    assert v.verdict == "does_not_cross" and NOTHING in v.says


def test_within_margin_names_only_tiers_a_value_inside_could_be_in():
    v = group((950, 100), (1, 0.2))
    assert v.verdict == "within_margin"
    assert v.tiers_possible == ("translate", "below_every_tier")
    assert "written notice" not in v.says


def test_the_fifty_person_edge_between_notice_and_translation():
    v = group((45, 10), (6, 0.5))
    assert v.tiers_possible == ("translate", "written_notice")


def test_tiers_within_finds_a_tier_only_inside_the_box():
    assert tiers_within({"persons": 40, "share": 4.5}, {"persons": 60, "share": 5.5},
                        SAFE_HARBOR) == {None, "written_notice", "translate"}


def test_a_group_with_no_margin_cannot_be_judged():
    assert group((1500, None), (2, 0.5)).verdict == "cannot_judge"


# ── as published, borrowed, comparable ───────────────────────────────────
def test_a_determination_is_reported_never_judged():
    assert as_published([], 72, publisher="the Census Bureau").verdict == "as_published"
    assert "no group covered" in as_published([], 72, publisher="the Census Bureau").says
    assert "Spanish" in as_published(["Spanish"], 72, publisher="the Census Bureau").says
    assert as_published([], 0, publisher="the Census Bureau").verdict == "cannot_judge"


def test_borrowed_shares_sum_residents_per_place():
    shares = borrowed_shares([(("g", "1"), 300), (("g", "2"), 100), (("g", "1"), 100)])
    assert [(s["key"], s["share"]) for s in shares] == [(("g", "1"), 0.8), (("g", "2"), 0.2)]


def test_a_borrowed_share_refuses_a_count_that_is_not_one():
    with pytest.raises(ValueError):
        borrowed_shares([(("g", "1"), None)])


def test_two_percents_of_one_measure_are_comparable_and_other_units_are_not():
    assert comparable("percent", "percent_of_households")
    assert not comparable("count", "per_1000_persons")
