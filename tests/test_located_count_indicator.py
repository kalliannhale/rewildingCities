"""the registry knows located_count (D-209): it parses, reads no source
variable, describes itself, and preview refuses it by name."""

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
    assert ind.derivation.layer == "imls_pls_fy2024_outlets"
    assert ind.declared_in.endswith("carriers.yml")


def test_a_located_count_asks_an_acquisition_for_nothing():
    ind = _registry().get("library_outlets_per_1000")
    assert ind.estimate_variables() == [] and ind.acquisition_variables() == []


def test_its_declaration_names_its_layer():
    d = _registry().declaration("library_outlets_per_1000")["derivation"]
    assert d == {"kind": "located_count", "layer": "imls_pls_fy2024_outlets",
                 "denominator": "persons", "scale": 1000.0}


def test_preview_describes_it_and_refuses_to_derive_it():
    ind = _registry().get("library_outlets_per_1000")
    assert describe(ind)["derivation"]["layer"] == "imls_pls_fy2024_outlets"
    with pytest.raises(PreviewError) as e:
        derive(None, ind, unit_authority="us_census_geoid", published_by=None, time=None)
    assert e.value.kind == "unavailable"


def test_a_located_count_without_a_layer_is_refused(tmp_path):
    (tmp_path / "x.yml").write_text(
        "indicators:\n  bad:\n    name: n\n    defined_by: d\n    measures: m\n"
        "    role: carrier\n    rests_on: {add: [P1_001N], counts: persons}\n"
        "    unit: u\n    derivation: {kind: located_count, denominator: persons, scale: 1000}\n"
        "    direction: higher_is_better\n    aggregation: none\n    uncertainty: none\n"
        "    source: {provider: rewildingcities}\n")
    with pytest.raises(ValueError, match="needs the layer"):
        IndicatorRegistry.load(tmp_path)


def test_our_counts_have_a_boundary_rule_on_the_acs_levels():
    import yaml
    pubs = yaml.safe_load((ROOT / "seeds" / "vintages" / "boundaries.yml").read_text())["publishers"]
    ours = pubs["rewildingcities"]
    assert ours["boundary_year"] == "final_year_of_time"
    # loam reads the ACS's levels for every publisher, so ours must be the same set
    assert set(ours["levels"]) == set(pubs["us_census_acs"]["levels"])
