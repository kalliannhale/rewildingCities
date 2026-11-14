"""the registry knows located_count (D-209): it parses, names the type it
counts (D-224), reads no source variable, describes itself, and preview
refuses it by name. carriers are found by role (D-223)."""

from pathlib import Path

import pytest

from canopy.indicators import IndicatorRegistry
from canopy.indicators.preview import PreviewError, derive, describe

ROOT = Path(__file__).resolve().parents[1]


def _registry():
    return IndicatorRegistry.load(ROOT / "seeds" / "indicators")


def test_the_library_indicator_parses_as_a_carrier():
    ind = _registry().get("library_outlets_per_1000")
    assert ind.role == "carrier"
    assert ind.derivation.kind == "located_count"
    assert ind.derivation.counts == "library_outlet"
    assert ind.declared_in.endswith("carriers.yml")


def test_a_located_count_asks_an_acquisition_for_nothing():
    ind = _registry().get("library_outlets_per_1000")
    assert ind.estimate_variables() == [] and ind.acquisition_variables() == []


def test_its_declaration_names_the_type_it_counts():
    d = _registry().declaration("library_outlets_per_1000")["derivation"]
    assert d == {"kind": "located_count", "counts": "library_outlet",
                 "denominator": "persons", "scale": 1000.0}


def test_preview_and_the_declaration_show_one_derivation():
    reg = _registry()
    for ind_id in reg.all():
        assert describe(reg.get(ind_id))["derivation"] == reg.declaration(ind_id)["derivation"]


def test_the_seed_names_no_release_and_no_plot():
    ind = _registry().get("library_outlets_per_1000")
    assert "2024" not in str(ind.derivation.as_dict())
    assert "maine" not in str(ind.source).lower()


def test_carriers_are_found_by_role():
    reg = _registry()
    assert "library_outlets_per_1000" in reg.with_role("carrier")
    assert all(reg.get(i).role == "carrier" for i in reg.with_role("carrier"))
    with pytest.raises(ValueError, match="not one of"):
        reg.with_role("carriers")


def test_preview_describes_it_and_refuses_to_derive_it():
    ind = _registry().get("library_outlets_per_1000")
    assert describe(ind)["derivation"]["counts"] == "library_outlet"
    with pytest.raises(PreviewError) as e:
        derive(None, ind, unit_authority="us_census_geoid", published_by=None, time=None)
    assert e.value.kind == "unavailable"


def _one_located_count(tmp_path, derivation: str):
    (tmp_path / "x.yml").write_text(
        "indicators:\n  bad:\n    name: n\n    defined_by: d\n    measures: m\n"
        "    role: carrier\n    rests_on: {add: [P1_001N], counts: persons}\n"
        f"    unit: u\n    derivation: {derivation}\n"
        "    direction: higher_is_better\n    aggregation: none\n    uncertainty: none\n"
        "    source: {provider: rewildingcities}\n")


def test_a_located_count_without_counts_is_refused(tmp_path):
    _one_located_count(tmp_path, "{kind: located_count, denominator: persons, scale: 1000}")
    with pytest.raises(ValueError, match="needs counts"):
        IndicatorRegistry.load(tmp_path)


def test_a_layer_label_in_the_seed_is_refused_by_name(tmp_path):
    _one_located_count(tmp_path, "{kind: located_count, layer: libs, counts: library_outlet, "
                                 "denominator: persons, scale: 1000}")
    with pytest.raises(ValueError, match="D-224"):
        IndicatorRegistry.load(tmp_path)


def test_our_counts_have_a_boundary_rule_on_the_acs_levels():
    import yaml
    pubs = yaml.safe_load((ROOT / "seeds" / "vintages" / "boundaries.yml").read_text())["publishers"]
    ours = pubs["rewildingcities"]
    assert ours["boundary_year"] == "final_year_of_time"
    # loam reads the ACS's levels for every publisher, so ours must be the same set
    assert set(ours["levels"]) == set(pubs["us_census_acs"]["levels"])
