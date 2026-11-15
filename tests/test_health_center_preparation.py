"""the maine_health_centers preparation agrees with its method, registry,
manifest, crosswalk and catalogue (Sprint 06, step 3, the third carrier;
D-232). the copy's own facts are declared once, in the manifest, which the
run is held to (D-192, D-226)."""

from pathlib import Path

import yaml

from canopy.orchestrator.parsing import parse_experiment, parse_manifest

ROOT = Path(__file__).resolve().parents[1]
PREP = ROOT / "plots" / "maine" / "preparations" / "maine_health_centers.yml"
CROSSWALK = ROOT / "seeds" / "crosswalks" / "health_centers" / "hrsa_health_center_sites.yml"


def _steps():
    return {s.id: s for s in parse_experiment(PREP).steps}


def _snapshot():
    return parse_manifest(ROOT / "plots" / "maine" / "manifest.yml").datasets[
        "hrsa_health_center_sites_20261114"]


def test_the_snapshot_is_a_usable_public_copy():
    ds = _snapshot()
    assert ds.is_usable, ds.underspecified
    assert ds.semantic_type == "health_center_sites_snapshot"
    assert ds.provenance["published_by"] == "hrsa"


def test_hrsas_columns_come_from_the_shared_crosswalk_never_the_plot():
    p = _steps()["health_centers_points"].params
    assert p["reading"] == "$crosswalks.hrsa_health_center_sites"
    assert "columns" not in p
    columns = yaml.safe_load(CROSSWALK.read_text())["columns"]
    assert columns["site_key"] == "BPHC Assigned Number"


def test_the_snapshot_declares_what_the_run_writes_of_it():
    ds = _snapshot()
    p = _steps()["health_centers_points"].params
    assert p["encoding"] == ds.source["sites_encoding"] == "utf-8"
    assert p["snapshot_date"] == ds.source["sites_snapshot_date"] == "2026-11-14"
    reg = yaml.safe_load((ROOT / "soil" / "_registry.yml").read_text())["primitives"]
    assert reg["prepare_health_center_points"]["source_facts"] == {
        "input": "snapshot", "params": {"encoding": "source.sites_encoding",
                                        "snapshot_date": "source.sites_snapshot_date"}}


def test_the_count_says_the_day_its_copy_describes():
    # its boundaries travel in boundary_vintage, from the edges (D-231)
    assert _steps()["health_centers_counts"].params["time"] == "2026-11-14"


def test_a_tribal_area_is_counted_beside_the_unseen_note():
    p = _steps()["health_centers_counts"].params
    assert "aiannh" in p["levels"] and p["tribal_note"] == "carrier_unseen_on_nations_land"


def test_the_catalogue_points_at_homes_that_exist():
    text = (ROOT / "seeds" / "sources" / "hrsa.yml").read_text()
    for home in ("seeds/crosswalks/health_centers/hrsa_health_center_sites.yml",
                 "garden/methods/information/health_center_carriers.yml",
                 "seeds/indicators/health_centers.yml", "plots/maine/manifest.yml"):
        assert home in text and (ROOT / home).is_file(), home


def test_the_graph_is_read_through_loam():
    s = _steps()["health_centers_located_in"]
    assert s.inputs["spine"] == "$loam.block_spine"
    assert s.inputs["places"] == "$loam.places"
    assert s.params["layer"] == "hrsa_hcsd_20261114_health_center_sites"


def test_the_registry_declares_every_param_the_steps_write():
    reg = yaml.safe_load((ROOT / "soil" / "_registry.yml").read_text())["primitives"]
    for sid, name in (("health_centers_points", "prepare_health_center_points"),
                      ("health_centers_located_in", "build_located_in"),
                      ("health_centers_counts", "count_located")):
        assert set(_steps()[sid].params) <= set(reg[name]["params"]), name
