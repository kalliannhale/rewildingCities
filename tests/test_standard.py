"""
tests/test_standard.py  |  rewildingCities, Sprint 06 zip 2 (D-270, D-271)

The standard is one seed, read through one schema (D-270). Its barriers hold
their measures, and barrier membership lives there alone: every indicator
whose role is barrier is named by exactly one barrier. A universal side
judges one count; a trigger's tiers name only quantities its groups declare;
a determination is reported as published. Anything else is refused, every
problem named at once.
"""

import copy
import shutil
from pathlib import Path

import pytest
import yaml

from canopy.indicators import IndicatorRegistry
from canopy.standards import StandardShapeError, load_standard, name_problems

REPO = Path(__file__).resolve().parents[1]
SEED = REPO / "seeds" / "standards" / "information_barriers.yml"


@pytest.fixture(scope="module")
def registry():
    return IndicatorRegistry.load(REPO / "seeds" / "indicators")


@pytest.fixture
def data():
    return yaml.safe_load(SEED.read_text())


def test_the_information_standard_loads(registry):
    s = load_standard("information_barriers", root=REPO, registry=registry)
    assert [b.id for b in s.barriers] == [
        "not_in_the_right_language", "requires_digital_access", "at_the_wrong_literacy_level",
        "lacking_cultural_cues", "behind_a_paywall", "outdated", "not_where_people_look",
        "not_from_a_trusted_source"]
    assert len(s.sha256) == 64 and s.path == "seeds/standards/information_barriers.yml"


def test_every_barrier_indicator_has_one_home_in_the_standard(registry):
    s = load_standard("information_barriers", root=REPO, registry=registry)
    named = [m.indicator for m in s.measures.values() if m.indicator]
    for ind in registry.with_role("barrier"):
        assert named.count(ind) == 1, ind


def test_d271_sides_as_decided(registry):
    s = load_standard("information_barriers", root=REPO, registry=registry)
    sides = {b.id: {x.id: x for x in b.sides} for b in s.barriers}
    language = sides["not_in_the_right_language"]
    assert language["every_limited_english_resident"].judges == "limited_english_persons"
    harbor = language["doj_safe_harbor"]
    assert len(harbor.groups) == 12
    assert [t["id"] for t in harbor.tiers] == ["translate", "written_notice"]
    assert harbor.tiers[0]["when_any"] == [{"persons": 1000}, {"share": 5, "persons": 50}]
    assert "rescinded 2025-03-21" in harbor.source["status"]
    assert language["section_203"].as_published == "section_203_determinations"
    digital = sides["requires_digital_access"]
    assert digital["every_household_connected"].judges == "households_without_broadband"
    assert sides["at_the_wrong_literacy_level"]["every_adult_at_level_2"].judges == \
        "literacy_at_or_below_level_1"
    for barrier in ("lacking_cultural_cues", "behind_a_paywall", "outdated",
                    "not_where_people_look", "not_from_a_trusted_source"):
        assert [x.kind for x in sides[barrier].values()] == ["none"], barrier


def test_every_side_names_its_kind_its_source_and_who_declared_it(registry):
    s = load_standard("information_barriers", root=REPO, registry=registry)
    for b in s.barriers:
        for side in b.sides:
            assert side.kind in ("universal", "trigger", "none")
            assert side.source.get("name") and side.declared_by and side.statement.strip()


def test_estimate_kinds_are_inferred_or_declared_never_guessed(registry):
    s = load_standard("information_barriers", root=REPO, registry=registry)
    kinds = {m_id: m.estimate_kind for m_id, m in s.measures.items() if m.status == "acquired"}
    assert kinds["limited_english_persons"] == "survey"
    assert kinds["library_outlets_per_1000"] == "administrative"
    assert kinds["literacy_at_or_below_level_1"] == "model_based"
    assert kinds["section_203_determinations"] == "published_determination"
    assert None not in kinds.values()


def test_a_broken_standard_names_every_problem(registry, data):
    bad = copy.deepcopy(data)
    bad["barriers"]["outdated"]["measures"].append("cii_broadband")
    bad["barriers"]["requires_digital_access"]["sides"][0]["judges"] = "cii_broadband"
    del bad["measures"]["cii_pub_literacy"]
    problems = name_problems(bad, registry)
    assert any("named by 2 barriers" in p for p in problems)
    assert any("not a count" in p for p in problems)
    assert any("cii_pub_literacy' is not declared" in p for p in problems)
    assert any("role barrier but no barrier" in p for p in problems)


def test_a_tier_naming_an_undeclared_quantity_is_refused(registry, data):
    bad = copy.deepcopy(data)
    side = bad["barriers"]["not_in_the_right_language"]["sides"][1]
    side["tiers"][0]["when_any"].append({"households": 10})
    assert any("names 'households'" in p for p in name_problems(bad, registry))


def test_a_measure_not_acquired_says_where_from_and_what_it_needs(registry, data):
    bad = copy.deepcopy(data)
    del bad["measures"]["fcc_served_100_20"]["needs"]
    assert any("needs both source and needs" in p for p in name_problems(bad, registry))


def _garden(tmp_path, data):
    (tmp_path / "seeds" / "schemas").mkdir(parents=True)
    (tmp_path / "seeds" / "standards").mkdir()
    shutil.copy(REPO / "seeds" / "schemas" / "standard.schema.yml",
                tmp_path / "seeds" / "schemas")
    (tmp_path / "seeds" / "standards" / "information_barriers.yml").write_text(
        yaml.safe_dump(data, sort_keys=False))
    return tmp_path


def test_an_undescribed_field_is_refused_by_the_schema(tmp_path, registry, data):
    bad = copy.deepcopy(data)
    bad["barriers"]["outdated"]["threshold"] = 3
    with pytest.raises(StandardShapeError, match="threshold"):
        load_standard("information_barriers", root=_garden(tmp_path, bad), registry=registry)


def test_a_key_written_twice_is_refused(tmp_path, registry):
    root = _garden(tmp_path, {})
    text = SEED.read_text().replace("measures:\n", "measures:\n  outlet_last_post: "
                                    "{status: acquired, indicator: cii_broadband}\n", 1)
    (root / "seeds" / "standards" / "information_barriers.yml").write_text(text)
    with pytest.raises(Exception):
        load_standard("information_barriers", root=root, registry=registry)
