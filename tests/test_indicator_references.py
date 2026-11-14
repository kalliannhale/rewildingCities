"""
tests/test_indicator_references.py

$indicators.<id> resolves an indicator's declaration into a step's params, so a
primitive receives parsed derivations and never reads YAML (D-33). what the
declaration's hash covers is held in tests/test_declaration_hash.py (D-227).
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from canopy.indicators import IndicatorRegistry
from canopy.orchestrator.references import ReferenceResolver

SEEDS = Path(__file__).resolve().parents[1] / "seeds" / "indicators"


def resolver():
    experiment = SimpleNamespace(choices={"grain": "county"},
                                 parameters={"vintage": "2020-2024"})
    return ReferenceResolver(manifest=SimpleNamespace(datasets={}),
                             experiment=experiment,
                             indicator_registry=IndicatorRegistry.load(SEEDS))


def test_an_indicator_resolves_to_its_parsed_declaration():
    d = resolver().resolve_param_value("$indicators.cii_broadband")
    assert d["id"] == "cii_broadband"
    assert d["derivation"] == {"kind": "ratio", "numerator": ["B28002_004E"],
                               "denominator": "B28002_001E", "scale": 100.0}
    assert d["moe_variables"] == ["B28002_004M", "B28002_001M"]
    assert d["declared_in"] == "indicators/cii_2026.yml"
    assert len(d["declaration_sha256"]) == 64


def test_a_list_of_indicators_resolves_element_by_element():
    out = resolver().resolve_param_value(
        ["$indicators.cii_broadband", "$indicators.cii_rent_burden"])
    assert [d["id"] for d in out] == ["cii_broadband", "cii_rent_burden"]
    # rent burden declares where its open-ended categories begin (ACS-7), and
    # the declaration resolves whole, edges included (REF-1)
    assert out[1]["derivation"] == {"kind": "passthrough", "column": "B25071_001E",
                                    "open_ended": {"lower": 10.0, "upper": 50.0}}


def test_an_unknown_indicator_is_refused_with_a_suggestion():
    with pytest.raises(ValueError) as e:
        resolver().resolve_param_value("$indicators.cii_brodband", context="step 'x'")
    assert "cii_broadband" in str(e.value)


def test_the_singular_is_caught_as_a_typo():
    with pytest.raises(ValueError) as e:
        resolver().resolve_param_value("$indicator.cii_broadband")
    assert "$indicators." in str(e.value)


def test_an_indicator_is_never_an_input():
    with pytest.raises(ValueError) as e:
        resolver().resolve_input("$indicators.cii_broadband")
    assert "params, not inputs" in str(e.value)


def test_the_other_references_still_resolve():
    r = resolver()
    assert r.resolve_param_value("$choices.grain") == "county"
    assert r.resolve_param_value("$parameters.vintage") == "2020-2024"
    assert r.resolve_param_value("plain text") == "plain text"
