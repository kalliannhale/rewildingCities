"""the maine_clerk_offices preparation agrees with its method, registry,
manifest and crosswalks (Sprint 06, step 3, the fourth carrier; GEO-1,
D-234 to D-238). the list's own facts are declared once, in the manifest,
which the run is held to (D-192, D-226)."""

from pathlib import Path

import yaml

from canopy.orchestrator.parsing import parse_experiment, parse_manifest

ROOT = Path(__file__).resolve().parents[1]
PREP = ROOT / "plots" / "maine" / "preparations" / "maine_clerk_offices.yml"
REGISTRY = ROOT / "soil" / "_registry.yml"


def _steps():
    return {s.id: s for s in parse_experiment(PREP).steps}


def _datasets():
    return parse_manifest(ROOT / "plots" / "maine" / "manifest.yml").datasets


def test_both_copies_are_declared_and_usable():
    ds = _datasets()
    clerks, addresses = ds["maine_sos_clerk_info_20261114"], ds["maine_e911_addresses_20260827"]
    assert clerks.is_usable, clerks.underspecified
    assert addresses.is_usable, addresses.underspecified
    assert clerks.semantic_type == "municipal_clerk_list"
    assert addresses.semantic_type == "address_point_release"


def test_neither_copy_may_be_published_until_its_terms_are_read():
    # the parsed dataset carries no license, so the declaration is read raw
    raw = yaml.safe_load((ROOT / "plots" / "maine" / "manifest.yml").read_text())["datasets"]
    for name in ("maine_sos_clerk_info_20261114", "maine_e911_addresses_20260827"):
        assert raw[name]["license"] == "terms_unknown", name


def test_every_reading_comes_from_a_shared_crosswalk_never_the_plot():
    p = _steps()["clerk_offices_points"].params
    assert p["clerks_reading"] == "$crosswalks.maine_sos_clerk_info"
    assert p["addresses_reading"] == "$crosswalks.maine_e911_fgdb"
    assert p["streets"] == "$crosswalks.usps_pub28"
    assert "columns" not in p and "header" not in p
    for rel in ("clerks/maine_sos_clerk_info.yml", "addresses/maine_e911_fgdb.yml",
                "addresses/usps_pub28.yml"):
        assert (ROOT / "seeds" / "crosswalks" / rel).is_file(), rel


def test_the_list_declares_what_the_run_writes_of_it():
    ds = _datasets()["maine_sos_clerk_info_20261114"]
    assert _steps()["clerk_offices_points"].params["encoding"] == ds.source["clerks_encoding"] == "utf-8"
    reg = yaml.safe_load(REGISTRY.read_text())["primitives"]
    assert reg["prepare_clerk_office_points"]["source_facts"] == {
        "input": "clerks", "params": {"encoding": "source.clerks_encoding"}}


def test_the_campus_choice_is_declared_in_the_method_and_made_in_the_run():
    method = yaml.safe_load((ROOT / "garden" / "methods" / "information"
                             / "clerk_office_carriers.yml").read_text())
    choice = method["choices"]["campus_ties"]
    assert set(choice["options"]) == {"listed", "municipal_class"} and choice["default"] == "listed"
    assert yaml.safe_load(PREP.read_text())["choices"] == {"campus_ties": "municipal_class"}
    assert _steps()["clerk_offices_points"].params["campus_ties"] == "$choices.campus_ties"


def test_build_located_in_lists_every_carrier_it_places():
    reg = yaml.safe_load(REGISTRY.read_text())["primitives"]
    points = next(i for i in reg["build_located_in"]["inputs"] if i["name"] == "points")
    assert {"library_outlet", "public_school", "health_center_site",
            "municipal_clerk_office"} <= set(points["semantic_types"])


def test_a_tribal_area_is_counted_beside_the_seen_note():
    # the list names all three nations' voting districts (TRIBE-10)
    p = _steps()["clerk_offices_counts"].params
    assert "aiannh" in p["levels"] and p["tribal_note"] == "carrier_seen_on_nations_land"


def test_the_graph_is_read_through_loam():
    s = _steps()["clerk_offices_located_in"]
    assert s.inputs["spine"] == "$loam.block_spine"
    assert s.inputs["places"] == "$loam.places"
    assert s.params["layer"] == "maine_sos_20261114_e911_20260827_clerk_offices"


def test_the_registry_declares_every_param_the_steps_write():
    reg = yaml.safe_load(REGISTRY.read_text())["primitives"]
    for sid, name in (("clerk_offices_points", "prepare_clerk_office_points"),
                      ("clerk_offices_located_in", "build_located_in"),
                      ("clerk_offices_counts", "count_located")):
        assert set(_steps()[sid].params) <= set(reg[name]["params"]), name
