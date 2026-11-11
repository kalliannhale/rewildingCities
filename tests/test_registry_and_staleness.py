"""
tests/test_registry_and_staleness.py

Sprint 02, items 4 to 6. A registry that declares a key twice fails to load,
naming it (REG-5). The ownership chain is registered and its precondition
names what provenance actually records (OWN-1). A source whose declaration
now needs variables its acquisition never requested reads as stale (ACQ-4).
"""

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from canopy.orchestrator.registry import RegistryManager, load_registry
from canopy.manifest.staleness import staleness

REPO = Path(__file__).resolve().parents[1]


# ── REG-5 ────────────────────────────────────────────────────────────────
def test_a_registry_with_a_duplicate_key_fails_to_load_naming_it(tmp_path):
    (tmp_path / "roots").mkdir()
    (tmp_path / "roots" / "_registry.yml").write_text(
        "primitives:\n  twice:\n    path: a.R\n  twice:\n    path: b.R\n")
    with pytest.raises(ValueError, match="duplicate key 'twice'.*line 2.*line 4"):
        load_registry("roots", tmp_path)


def test_a_duplicate_inside_one_primitive_is_refused_too(tmp_path):
    (tmp_path / "soil").mkdir()
    (tmp_path / "soil" / "_registry.yml").write_text(
        "primitives:\n  p:\n    path: a.R\n    passthrough: true\n    passthrough: true\n")
    with pytest.raises(ValueError, match="duplicate key 'passthrough'"):
        load_registry("soil", tmp_path)


@pytest.mark.parametrize("layer", ["roots", "soil"])
def test_the_real_registries_load_with_no_repeated_key(layer):
    assert load_registry(layer, REPO)


# ── the ownership chain ──────────────────────────────────────────────────
def test_the_ownership_chain_is_registered_in_soil():
    m = RegistryManager(project_root=REPO)
    for name in ("resolve_ownership", "geocode_to_unit"):
        path, _ = m.resolve_primitive(f"soil/{name}")
        assert path.endswith(f"validate/{name}.py")


def test_concentration_waits_for_the_name_provenance_records():
    # provenance names a primitive by its file (envelope.py), so the
    # precondition must say resolve_ownership, not its warnings' name (OWN-1)
    _, spec = RegistryManager(project_root=REPO).resolve_primitive("roots/concentration_index")
    assert spec.preconditions == [{"provenance_contains": "resolve_ownership"}]


# ── ACQ-4 ────────────────────────────────────────────────────────────────
def changelog(tmp_path, variables):
    path = tmp_path / ".manifest_changelog.yml"
    path.write_text(yaml.safe_dump([{
        "timestamp": "2026-10-07T00:00:00+00:00",
        "changes": [{"dataset": "acs", "field": "available", "value": "true",
                     "provenance": {"provider": "census_acs",
                                    "vintage_window": "2020-2024",
                                    "variables_requested": variables}}]}]))
    return path


def acs_source(indicators):
    return SimpleNamespace(name="acs", source={
        "provider": "census_acs", "dataset": "acs/acs5", "year": 2024,
        "geography": "county", "indicators": indicators})


def test_a_changed_declaration_makes_its_acquisition_stale(tmp_path):
    # acquired when broadband alone was declared; rent burden added since
    from canopy.providers.census_acs import CensusACSProvider
    before, _ = CensusACSProvider.resolve_variables(acs_source(["cii_broadband"]).source)
    log = changelog(tmp_path, before)
    judged = staleness(acs_source(["cii_broadband", "cii_rent_burden"]), log)
    assert judged["stale"]
    assert "B25070_001E" in judged["missing"] and "B25071_001E" in judged["missing"]
    assert "declared differently than acquired" in judged["message"]


def test_an_acquisition_that_matches_its_declaration_is_fresh(tmp_path):
    from canopy.providers.census_acs import CensusACSProvider
    needed, _ = CensusACSProvider.resolve_variables(acs_source(["cii_broadband"]).source)
    judged = staleness(acs_source(["cii_broadband"]), changelog(tmp_path, needed))
    assert judged == {"stale": False, "missing": [], "message": "acquired as declared"}


def test_no_record_of_the_acquisition_is_stale_not_fresh(tmp_path):
    judged = staleness(acs_source(["cii_broadband"]), tmp_path / "absent.yml")
    assert judged["stale"] and "no recorded acquisition" in judged["message"]


def test_a_source_that_records_no_variables_cannot_be_judged(tmp_path):
    other = SimpleNamespace(name="parks", source={"provider": "arcgis_rest"})
    assert staleness(other, tmp_path / "absent.yml") is None
