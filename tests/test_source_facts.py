"""
tests/test_source_facts.py

a source says what it is (D-189), and a run that repeats what it says must
agree with it (D-192). a source's publisher is published_by wherever a
manifest says it (NAME-4), and a retired word makes one dataset unusable,
never a whole plot.
"""

from pathlib import Path

import pytest
import yaml

from canopy.orchestrator import Orchestrator, parse_manifest
from canopy.orchestrator.registry import _normalize_source_facts, load_registry

REPO = Path(__file__).resolve().parents[1]
MAINE = REPO / "plots" / "maine"


# ── the manifest's words ──────────────────────────────────────────────────
def test_the_retired_publisher_word_makes_only_its_dataset_unusable(tmp_path):
    base = {"semantic_type": "indicator_source", "format": "csv",
            "cache": {"path": ".data/x.csv"}}
    (tmp_path / "manifest.yml").write_text(yaml.safe_dump({"datasets": {
        "old": {**base, "provenance": {"authority": "us_census_acs"}},
        "new": {**base, "provenance": {"published_by": "us_census_acs"}}}}))
    ds = parse_manifest(tmp_path / "manifest.yml").datasets
    assert not ds["old"].is_usable
    assert any("provenance.published_by" in u for u in ds["old"].underspecified)
    assert ds["new"].is_usable


def test_no_maine_dataset_names_its_publisher_in_the_retired_word():
    for name, ds in parse_manifest(MAINE / "manifest.yml").datasets.items():
        assert "authority" not in (ds.provenance or {}), name


def test_every_maine_indicator_source_declares_its_publisher_and_unit_authority():
    sources = parse_manifest(MAINE / "manifest.yml").datasets_by_semantic_type("indicator_source")
    assert sources
    for ds in sources:
        assert (ds.provenance or {}).get("published_by"), ds.name
        assert (ds.source or {}).get("unit_authority"), ds.name


# ── the registry's declaration ────────────────────────────────────────────
def test_derive_indicator_declares_its_source_facts_and_its_publisher_param():
    spec = load_registry("soil", REPO)["derive_indicator"]
    assert spec.source_facts == {
        "input": "source",
        "params": {"unit_authority": "source.unit_authority",
                   "published_by": "provenance.published_by"}}
    assert "published_by" in spec.params
    assert "authority" not in spec.params


@pytest.mark.parametrize("bad", [
    {"params": {"x": "source.x"}},
    {"input": "source"},
    {"input": "source", "params": {"x": "elsewhere.x"}},
    {"input": "source", "params": {"x": "source"}},
])
def test_a_malformed_source_facts_declaration_is_refused(bad):
    with pytest.raises(ValueError, match="source_facts"):
        _normalize_source_facts(bad, "p", "soil")


# ── a run held to its source (D-192) ──────────────────────────────────────
def a_run(tmp_path, *, written="us_census_sldl", declared="us_census_sldl",
          published_by="us_census_acs", provenance=None, parameters=None):
    plot = tmp_path / "plots" / "demo"
    (plot / "preparations").mkdir(parents=True)
    source = {"type": "manual"}
    if declared is not None:
        source["unit_authority"] = declared
    (plot / "manifest.yml").write_text(yaml.safe_dump({
        "city": {"id": "demo", "name": "Demo"},
        "datasets": {"acs_sldl": {
            "available": True, "semantic_type": "indicator_source", "format": "csv",
            "source": source, "cache": {"path": ".data/acs.csv"},
            "provenance": provenance or {"published_by": "us_census_acs"}}}}))
    run = {"id": "demo_values", "name": "Demo values", "kind": "preparation",
           "city": "demo", "manifest": "../manifest.yml",
           "method": {"ref": "$methods/information/indicator_values"},
           "parameters": parameters or {},
           "steps": [{"id": "derive", "primitive": "soil/derive_indicator",
                      "inputs": {"source": "$manifest.acs_sldl"},
                      "outputs": {"values": "indicator_values"},
                      "params": {"spatial_unit": "state legislative district",
                                 "published_by": published_by,
                                 "unit_authority": written}}]}
    path = plot / "preparations" / "demo_values.yml"
    path.write_text(yaml.safe_dump(run))
    return path


def source_fact_errors(path, tmp_path):
    errors, _ = Orchestrator(path, project_root=REPO, output_dir=tmp_path / "out").validate()
    return [e for e in errors if "D-192" in e or "cannot be used" in e]


def test_a_run_that_agrees_with_its_source_passes(tmp_path):
    assert source_fact_errors(a_run(tmp_path), tmp_path) == []


def test_a_unit_authority_that_disagrees_with_the_source_is_refused(tmp_path):
    errors = source_fact_errors(a_run(tmp_path, written="us_census_geoid"), tmp_path)
    assert len(errors) == 1
    assert "declares source.unit_authority: 'us_census_sldl'" in errors[0]


def test_a_publisher_that_disagrees_with_the_source_is_refused(tmp_path):
    errors = source_fact_errors(a_run(tmp_path, published_by="someone_else"), tmp_path)
    assert len(errors) == 1
    assert "declares provenance.published_by: 'us_census_acs'" in errors[0]


def test_a_fact_the_source_does_not_declare_is_refused(tmp_path):
    errors = source_fact_errors(a_run(tmp_path, declared=None), tmp_path)
    assert len(errors) == 1
    assert "declares no source.unit_authority" in errors[0]


def test_a_written_fact_is_checked_as_the_run_resolves_it(tmp_path):
    path = a_run(tmp_path, written="$parameters.ua", parameters={"ua": "us_census_geoid"})
    errors = source_fact_errors(path, tmp_path)
    assert len(errors) == 1
    assert "'us_census_geoid'" in errors[0]


def test_a_source_in_the_retired_word_cannot_be_read_by_a_run(tmp_path):
    path = a_run(tmp_path, provenance={"authority": "us_census_acs"})
    errors = source_fact_errors(path, tmp_path)
    assert len(errors) == 1
    assert "cannot be used" in errors[0] and "provenance.published_by" in errors[0]


# ── the real plot: every Maine run that derives agrees with its source ────
MAINE_DERIVING = sorted(p for sub in ("preparations", "experiments")
                        for p in (MAINE / sub).glob("*.yml")
                        if "soil/derive_indicator" in p.read_text())


def test_maine_has_runs_that_derive():
    assert MAINE_DERIVING


@pytest.mark.parametrize("path", MAINE_DERIVING, ids=lambda p: p.stem)
def test_every_maine_run_agrees_with_its_sources(path, tmp_path):
    assert source_fact_errors(path, tmp_path) == []
