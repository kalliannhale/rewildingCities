"""
tests/test_universes.py  |  rewildingCities, Sprint 05 change 12 (plan builds 4 and 5)

seeds/universes/universes.yml says which edge weight counts what each
indicator's value rests on (D-181). Every indicator's rests_on.counts phrase
is declared there, exactly, so no reader ever guesses a weight; D-121's two
mappings are declared rather than assumed; and a malformed entry is refused
by name.
"""

from pathlib import Path

import pytest
import yaml

from canopy.loam.edge_rules import load_universes

REPO = Path(__file__).resolve().parents[1]


def every_counts_phrase():
    for f in sorted((REPO / "seeds" / "indicators").glob("*.yml")):
        doc = yaml.safe_load(f.read_text()) or {}
        for key, spec in (doc.get("indicators") or {}).items():
            rests_on = (spec or {}).get("rests_on") or {}
            if rests_on.get("counts"):
                yield f.name, key, rests_on["counts"]


def test_every_indicators_universe_is_declared():
    universes = load_universes(REPO)
    phrases = list(every_counts_phrase())
    assert phrases, "the indicator seeds declare at least one universe"
    missing = [f"{f}: {k} counts '{c}'" for f, k, c in phrases if c not in universes]
    assert not missing, "undeclared in seeds/universes/universes.yml: " + "; ".join(missing)


def test_d121s_two_weights_are_declared_not_assumed():
    universes = load_universes(REPO)
    assert (universes["households"].weight, universes["households"].relation) == \
        ("weight_households", "equals")
    assert (universes["persons"].weight, universes["persons"].relation) == \
        ("weight_population", "equals")


def test_renters_are_contained_by_households_never_equal_to_them():
    renters = load_universes(REPO)["renter households with rent burden computed"]
    assert (renters.weight, renters.relation) == ("weight_households", "contains")
    assert "subset" in renters.reason


@pytest.mark.parametrize("entry, match", [
    ("{weight: weight_housing_units, relation: equals}", "names weight"),
    ("{weight: weight_households, relation: roughly}", "says relation"),
])
def test_a_malformed_universe_is_refused_by_name(tmp_path, entry, match):
    seed = tmp_path / "seeds" / "universes"
    seed.mkdir(parents=True)
    (seed / "universes.yml").write_text(f"universes:\n  households: {entry}\n")
    with pytest.raises(ValueError, match=match):
        load_universes(tmp_path)
