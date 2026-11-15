"""the maine_schools preparation agrees with its method, registry, manifest,
crosswalk and catalogue (Sprint 06, step 3, the second carrier; D-230). the
release's own facts are declared once, in the manifest, which the run is
held to (D-192, D-226)."""

import re
from pathlib import Path

import yaml

from canopy.orchestrator.parsing import parse_experiment, parse_manifest

ROOT = Path(__file__).resolve().parents[1]
PREP = ROOT / "plots" / "maine" / "preparations" / "maine_schools.yml"
CROSSWALK = ROOT / "seeds" / "crosswalks" / "schools" / "nces_edge_geocode.yml"


def _steps():
    return {s.id: s for s in parse_experiment(PREP).steps}


def _release():
    return parse_manifest(ROOT / "plots" / "maine" / "manifest.yml").datasets["edge_publicsch_2425"]


def test_the_release_is_a_usable_public_release():
    ds = _release()
    assert ds.is_usable, ds.underspecified
    assert ds.semantic_type == "school_geocode_release"
    assert ds.provenance["published_by"] == "nces"


def test_nces_columns_come_from_the_shared_crosswalk_never_the_plot():
    p = _steps()["schools_points"].params
    assert p["reading"] == "$crosswalks.nces_edge_geocode"
    assert "columns" not in p
    columns = yaml.safe_load(CROSSWALK.read_text())["columns"]
    assert len(columns) == 23 and columns[0] == "NCESSCH" and columns[-1] == "SCHOOLYEAR"


def test_the_bureau_of_indian_education_code_has_its_meaning():
    codes = yaml.safe_load(CROSSWALK.read_text())["operating_codes"]
    assert codes["59"]["meaning"] == "operated by the Bureau of Indian Education"


def test_the_release_declares_what_the_run_writes_of_it():
    ds = _release()
    p = _steps()["schools_points"].params
    assert p["member"] == ds.source["geocode_member"]
    assert p["encoding"] == ds.source["geocode_encoding"] == "utf-8"
    reg = yaml.safe_load((ROOT / "soil" / "_registry.yml").read_text())["primitives"]
    assert reg["prepare_school_points"]["source_facts"] == {
        "input": "release", "params": {"member": "source.geocode_member",
                                       "encoding": "source.geocode_encoding"}}


def test_schools_are_placed_by_where_they_stand():
    p = _steps()["schools_points"].params
    assert p["state_fips"] == "23" and p["state"] == "ME"
    assert "operating_state" not in p and "opstfips" not in {k.lower() for k in p}


def test_the_catalogue_points_at_homes_that_exist():
    text = (ROOT / "seeds" / "sources" / "nces_edge_geocode.yml").read_text()
    for home in ("seeds/crosswalks/schools/nces_edge_geocode.yml",
                 "garden/methods/information/school_carriers.yml",
                 "seeds/indicators/schools.yml", "plots/maine/manifest.yml"):
        assert home in text and (ROOT / home).is_file(), home


def test_the_graph_is_read_through_loam():
    s = _steps()["schools_located_in"]
    assert s.inputs["spine"] == "$loam.block_spine"
    assert s.inputs["places"] == "$loam.places"
    assert s.params["layer"] == "nces_edge_2425_public_schools"
    assert "check_block_field" not in s.params


def test_the_count_names_the_year_of_its_places():
    t = _steps()["schools_counts"].params["time"]
    assert re.match(r".*([0-9]{4})", t).group(1) == "2024"


def test_the_registry_declares_every_param_the_steps_write():
    reg = yaml.safe_load((ROOT / "soil" / "_registry.yml").read_text())["primitives"]
    for sid, name in (("schools_points", "prepare_school_points"),
                      ("schools_located_in", "build_located_in"),
                      ("schools_counts", "count_located")):
        assert set(_steps()[sid].params) <= set(reg[name]["params"]), name
