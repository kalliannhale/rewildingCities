"""
tests/test_edge_rules.py  |  rewildingCities, Sprint 05 change 12 (plan builds 4 and 5)

What may move along an edge (D-179): only a count, only by a weight that
equals its universe (D-181), with a warning naming the weight. A median, a
rate or a percentage never moves, and the contract sits above the seed: an
indicator whose publisher combines it upward by weighted mean still never
moves along an overlaps edge. Whether a town has none of a universe in a
place (D-180) is judged by the weight its universe declares.
"""

import pytest

from canopy.loam.edge_rules import (EdgeRuleRefused, Universe, allocate_count,
                                    may_allocate, share_of, zero_here)

HOUSEHOLDS = Universe("households", "weight_households", "equals")
PERSONS = Universe("persons", "weight_population", "equals")
RENTERS = Universe("renter households with rent burden computed", "weight_households", "contains")

EDGE = {"from_authority": "us_census_geoid", "from_code": "2302735310",
        "to_authority": "us_census_sldl", "to_code": "23042", "kind": "overlaps",
        "weight_population": 0.25, "weight_households": 0.2, "weight_reason": None,
        "source": "2020 blocks", "vintage": "2024"}


# ── what may move ─────────────────────────────────────────────────────────
def test_allocating_a_median_is_refused():
    ok, why = may_allocate({"id": "cii_rent_burden", "aggregation": "none"})
    assert not ok and "aggregation: 'none'" in why and "D-27" in why


def test_a_share_is_refused_even_though_its_publisher_combines_it_upward():
    ok, why = may_allocate({"id": "cii_broadband", "aggregation": "population_weighted_mean"})
    assert not ok
    assert "population_weighted_mean" in why and "Contract 3 rules 1 and 3" in why


def test_only_a_declared_sum_may_be_allocated():
    assert may_allocate({"id": "a_count", "aggregation": "sum"})[0]
    assert not may_allocate({"id": "undeclared"})[0]


def test_allocating_a_count_warns_naming_the_weight_used():
    a = allocate_count(1000, EDGE, HOUSEHOLDS)
    assert a.figure == pytest.approx(200.0)
    assert a.weight_column == "weight_households" and a.weight == 0.2
    assert "allocated, not measured" in a.warning
    assert "weight_households 0.2000" in a.warning
    assert "never stored" in a.warning and "D-179" in a.warning


def test_a_null_weight_allocates_nothing_and_says_why():
    edge = {**EDGE, "weight_households": None, "weight_reason": "zero_households"}
    with pytest.raises(EdgeRuleRefused, match="zero_households"):
        allocate_count(1000, edge, HOUSEHOLDS)


def test_a_contained_universe_never_allocates():
    with pytest.raises(EdgeRuleRefused, match="only contains"):
        allocate_count(300, EDGE, RENTERS)


def test_an_undeclared_universe_never_allocates():
    with pytest.raises(EdgeRuleRefused, match="guessed weight"):
        allocate_count(300, EDGE, None)


def test_a_count_moves_only_along_contains_or_overlaps():
    with pytest.raises(EdgeRuleRefused, match="not 'located_in'"):
        allocate_count(10, {**EDGE, "kind": "located_in"}, HOUSEHOLDS)


# ── shares and zero ───────────────────────────────────────────────────────
def test_only_an_equal_universe_shows_a_share():
    assert share_of(EDGE, HOUSEHOLDS) == (0.2, "")
    share, why = share_of(EDGE, RENTERS)
    assert share is None and "only contains" in why


def test_a_weight_of_zero_means_none_here():
    here, why = zero_here({**EDGE, "weight_population": 0.0}, PERSONS)
    assert here is True and "none of its persons" in why


def test_a_town_with_no_households_has_none_here_by_definition():
    edge = {**EDGE, "weight_households": None, "weight_reason": "zero_households"}
    assert zero_here(edge, HOUSEHOLDS)[0] is True
    assert zero_here(edge, RENTERS)[0] is True


def test_a_contained_universe_judges_zero_by_its_containing_weight():
    assert zero_here({**EDGE, "weight_households": 0.0}, RENTERS)[0] is True
    assert zero_here(EDGE, RENTERS)[0] is False


def test_zero_that_cannot_be_judged_says_so():
    here, why = zero_here({**EDGE, "weight_households": None, "weight_reason": "no_block_points"},
                          HOUSEHOLDS)
    assert here is None and "no_block_points" in why
    assert zero_here(EDGE, None)[0] is None
