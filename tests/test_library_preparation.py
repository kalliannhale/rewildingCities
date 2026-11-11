"""the maine_libraries preparation agrees with its registry, manifest and
vocabulary (Sprint 06, step 3)."""

from pathlib import Path

import yaml

from canopy.orchestrator.parsing import parse_experiment, parse_manifest

ROOT = Path(__file__).resolve().parents[1]
PREP = ROOT / "plots" / "maine" / "preparations" / "maine_libraries.yml"


def _steps():
    return {s.id: s for s in parse_experiment(PREP).steps}


def test_the_survey_is_a_usable_public_release():
    ds = parse_manifest(ROOT / "plots" / "maine" / "manifest.yml").datasets["pls_fy2024"]
    assert ds.is_usable, ds.underspecified
    assert ds.semantic_type == "library_survey_release"
    assert ds.provenance["published_by"] == "imls"


def test_bookmobiles_are_declared_mobile():
    p = _steps()["libraries_points"].params
    assert p["fixed_types"] == ["CE", "BR"] and "BS" in p["mobile_types"]
    assert p["encoding"] == "windows-1252"


def test_the_graph_is_read_through_loam_and_checked_against_imls():
    s = _steps()["libraries_located_in"]
    assert s.inputs["spine"] == "$loam.block_spine"
    assert s.inputs["places"] == "$loam.places"
    assert s.params["check_block_field"] == "cenblock"
    assert s.params["layer"] == "imls_pls_fy2024_outlets"


def test_the_registry_declares_every_param_the_steps_write():
    reg = yaml.safe_load((ROOT / "soil" / "_registry.yml").read_text())["primitives"]
    for sid, name in (("libraries_points", "prepare_library_points"),
                      ("libraries_located_in", "build_located_in")):
        assert set(_steps()[sid].params) <= set(reg[name]["params"]), name
