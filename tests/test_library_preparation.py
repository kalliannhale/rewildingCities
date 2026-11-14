"""the maine_libraries preparation agrees with its method, registry, manifest
and vocabulary (Sprint 06, step 3; D-210, D-211, D-212). IMLS's codes are a
shared crosswalk, and the release's own facts are declared once, in the
manifest, which the run is held to (D-192, D-226)."""

from pathlib import Path

import yaml

from canopy.orchestrator.parsing import parse_experiment, parse_manifest

ROOT = Path(__file__).resolve().parents[1]
PREP = ROOT / "plots" / "maine" / "preparations" / "maine_libraries.yml"
METHOD = ROOT / "garden" / "methods" / "information" / "library_carriers.yml"


def _steps():
    return {s.id: s for s in parse_experiment(PREP).steps}


def test_the_survey_is_a_usable_public_release():
    ds = parse_manifest(ROOT / "plots" / "maine" / "manifest.yml").datasets["pls_fy2024"]
    assert ds.is_usable, ds.underspecified
    assert ds.semantic_type == "library_survey_release"
    assert ds.provenance["published_by"] == "imls"


CROSSWALK = ROOT / "seeds" / "crosswalks" / "libraries" / "imls_pls_outlets.yml"


def test_imls_codes_come_from_the_shared_crosswalk_never_the_plot():
    p = _steps()["libraries_points"].params
    assert p["reading"] == "$crosswalks.imls_pls_outlets"
    assert not {"fixed_types", "mobile_types", "status_codes"} & set(p)


def test_bookmobiles_are_read_mobile():
    types = yaml.safe_load(CROSSWALK.read_text())["outlet_types"]
    assert {c for c, e in types.items() if e["kind"] == "fixed"} == {"CE", "BR"}
    assert types["BS"]["kind"] == "mobile" and types["BM"]["kind"] == "mobile"


def test_every_status_code_has_a_meaning_and_a_group():
    codes = yaml.safe_load(CROSSWALK.read_text())["structure_status"]
    assert all(e["meaning"] and e["group"] in ("open", "temporary", "permanent")
               for e in codes.values())
    assert codes["23"]["group"] == "temporary"
    assert codes["25"]["group"] == "open"
    assert codes["03"]["group"] == "permanent"


def test_the_release_declares_what_the_run_writes_of_it():
    ds = parse_manifest(ROOT / "plots" / "maine" / "manifest.yml").datasets["pls_fy2024"]
    p = _steps()["libraries_points"].params
    assert p["member"] == ds.source["outlet_member"]
    assert p["encoding"] == ds.source["outlet_encoding"] == "windows-1252"
    reg = yaml.safe_load((ROOT / "soil" / "_registry.yml").read_text())["primitives"]
    facts = reg["prepare_library_points"]["source_facts"]
    assert facts == {"input": "survey", "params": {"member": "source.outlet_member",
                                                   "encoding": "source.outlet_encoding"}}


def test_the_catalogue_points_at_homes_that_exist():
    text = (ROOT / "seeds" / "sources" / "imls_pls.yml").read_text()
    for home in ("seeds/crosswalks/libraries/imls_pls_outlets.yml",
                 "garden/methods/information/library_carriers.yml",
                 "seeds/indicators/carriers.yml", "plots/maine/manifest.yml"):
        assert home in text and (ROOT / home).is_file(), home


def test_temporary_closures_follow_a_choice_the_method_declares():
    run = parse_experiment(PREP)
    assert _steps()["libraries_points"].params["temporarily_closed"] == "$choices.temporarily_closed"
    options = yaml.safe_load(METHOD.read_text())["choices"]["temporarily_closed"]["options"]
    assert run.choices["temporarily_closed"] in options


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
