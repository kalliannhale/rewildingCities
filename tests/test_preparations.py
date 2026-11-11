"""
tests/test_preparations.py

D-98: one schema, two kinds of run. A preparation readies data and answers no
question: it names no curiosity, uses soil/ primitives only, and its method is
a preparation method. It runs through the same orchestrator and the same
precondition gate as an experiment, and its receipts say `kind: preparation`.

Nothing here runs R. The real orchestrator, registries, vocabulary and methods
index are used; only the primitive call itself (EnvelopeBuilder.run) is a fake
that writes an output file and returns the envelope a primitive would.
"""

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from canopy.envelope import (BuildResult, Envelope, HashInfo, InputRecord,
                             ProvenanceEntry, Warning)
from canopy.orchestrator.orchestrator import Orchestrator
from canopy.orchestrator.parsing import parse_experiment

REPO = Path(__file__).resolve().parents[1]
PREP_METHOD = "$methods/information/county_units_for_mapping"
ANALYSIS_METHOD = "$methods/information/cii_indicator_values"


# ── a small plot, written fresh for each test ────────────────────────────
def a_plot(tmp_path):
    plot = tmp_path / "plots" / "demo"
    (plot / ".data").mkdir(parents=True)
    (plot / ".data" / "counties.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "features": []}))
    (plot / "manifest.yml").write_text(yaml.safe_dump({
        "city": {"id": "demo", "name": "demo"},
        "crs": {"working": "EPSG:4326"},
        "datasets": {
            "governance_unit_county": {
                "available": True,
                "semantic_type": "governance_unit",
                "format": "geojson",
                "source": {"type": "manual"},
                "cache": {"path": ".data/counties.geojson"},
            },
        },
    }))
    return plot


def a_run(plot, name, **fields):
    """write a run file under plots/demo/preparations/ and return its path."""
    folder = plot / "preparations"
    folder.mkdir(exist_ok=True)
    doc = {"id": name, "name": name, "city": "demo",
           "manifest": "../manifest.yml", "choices": {}, "parameters": {}}
    doc.update(fields)
    path = folder / f"{name}.yml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    return path


def step(step_id, primitive, inputs, output="out"):
    return {"id": step_id, "primitive": primitive, "inputs": inputs,
            "outputs": {output: "governance_unit"}, "params": {}}


def orchestrator(path, tmp_path):
    return Orchestrator(path, project_root=REPO, output_dir=tmp_path / "out")


# ── a fake primitive: writes its output, returns its envelope ────────────
def fake_builder(monkeypatch, orch, warn_after=None):
    """every step 'runs': its output file is written and an envelope comes
    back. the step whose primitive name is warn_after leaves a critical
    warning on its output, as a real primitive would on a bad result."""
    def run(primitive, version, inputs, output_path, output_format,
            output_semantic_type, output_data_category, params=None,
            passthrough=False):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(
            {"type": "FeatureCollection", "features": []}))
        name = Path(primitive).stem
        # the provenance schema requires at least one input record (minItems
        # 1), so the fake records the inputs it was given, as a primitive does.
        # the hash is a real md5 of nothing: a skipped hash (value None) is
        # dropped by Envelope.to_dict and then fails the schema, which
        # requires `value` (HASH-1), so the fake cannot use one.
        records = [InputRecord(
            name=i.name, semantic_type=i.semantic_type or "governance_unit",
            path=str(i.path or "in-memory"),
            hash=HashInfo(value=hashlib.md5(b"").hexdigest(),
                          method="full_file", algorithm="md5"))
            for i in inputs]
        warnings = [Warning(level="critical", primitive=name,
                            message="every unit has the same geometry")] \
            if name == warn_after else []
        env = Envelope(
            data={"path": str(output_path), "format": output_format},
            metadata={"semantic_type": output_semantic_type,
                      "data_category": output_data_category,
                      "crs": "EPSG:4326"},
            provenance=[ProvenanceEntry(
                primitive=name, version=version, timestamp="2026-11-10T00:00:00Z",
                params=params or {}, inputs=records, duration_seconds=0.0)],
            warnings=warnings)
        return BuildResult(success=True, envelope=env, error=None, message=None)
    monkeypatch.setattr(orch.envelope_builder, "run", run)
    # a run log belongs to a real run; these would land in the repo's
    # compost/logs/ under the real project root.
    monkeypatch.setattr(orch, "_write_run_log", lambda result: None)


# ── the sprint's three tests ─────────────────────────────────────────────
def test_a_preparation_runs_with_no_curiosity_and_its_receipt_says_so(
        tmp_path, monkeypatch):
    plot = a_plot(tmp_path)
    path = a_run(plot, "county_units", kind="preparation",
                 method={"ref": PREP_METHOD},
                 steps=[step("units_repair", "soil/repair_geometry",
                             {"features": "$manifest.governance_unit_county"},
                             output="repaired")])
    orch = orchestrator(path, tmp_path)
    fake_builder(monkeypatch, orch)

    result = orch.run()
    assert result.success, result.error or result.message

    receipt = json.loads(
        (plot / ".envelopes" / "units_repair_repaired.envelope.json").read_text())
    lineage = receipt["metadata"]["lineage"]
    assert lineage["kind"] == "preparation"
    assert lineage["run"] == "county_units"
    assert lineage["method"] == PREP_METHOD
    # absent, never empty: a receipt must not read as "a question, unknown"
    assert "curiosity" not in lineage and "sub_question" not in lineage


def test_an_experiment_with_no_curiosity_is_still_flagged(tmp_path):
    plot = a_plot(tmp_path)
    path = a_run(plot, "no_question", method={"ref": ANALYSIS_METHOD},
                 curiosity={"ref": ""},
                 steps=[step("units_repair", "soil/repair_geometry",
                             {"features": "$manifest.governance_unit_county"})])
    errors, warnings = orchestrator(path, tmp_path).validate()
    assert not [e for e in errors if "curiosity" in e]
    assert any("names no curiosity" in w and "D-64" in w for w in warnings)


def test_the_gate_stops_a_preparation_whose_input_carries_a_blocking_warning(
        tmp_path, monkeypatch):
    # assign_geoid declares no_unresolved_critical in soil/_registry.yml.
    plot = a_plot(tmp_path)
    path = a_run(plot, "county_units", kind="preparation",
                 method={"ref": PREP_METHOD},
                 steps=[step("units_dissolve", "soil/dissolve_by_field",
                             {"features": "$manifest.governance_unit_county"},
                             output="dissolved"),
                        step("units_geoid", "soil/assign_geoid",
                             {"boundaries": "$steps.units_dissolve.dissolved"},
                             output="with_geoid")])
    orch = orchestrator(path, tmp_path)
    fake_builder(monkeypatch, orch, warn_after="dissolve_by_field")

    result = orch.run()
    assert not result.success
    assert result.failed_step == "units_geoid"
    assert "no_unresolved_critical" in (result.message or "")
    assert not (plot / ".envelopes" / "units_geoid_with_geoid.envelope.json").exists()


# ── what makes a preparation a preparation ───────────────────────────────
def test_a_preparation_that_names_a_curiosity_is_refused(tmp_path):
    plot = a_plot(tmp_path)
    path = a_run(plot, "borrowed", kind="preparation",
                 method={"ref": PREP_METHOD},
                 curiosity={"ref": "$curiosity-space/information/information_access"},
                 steps=[step("units_repair", "soil/repair_geometry",
                             {"features": "$manifest.governance_unit_county"})])
    errors, _ = orchestrator(path, tmp_path).validate()
    assert any("names no curiosity" in e for e in errors)


def test_a_preparation_with_a_roots_step_is_refused(tmp_path):
    plot = a_plot(tmp_path)
    path = a_run(plot, "analysis_inside", kind="preparation",
                 method={"ref": PREP_METHOD},
                 steps=[step("standardize", "roots/standardize_indicator",
                             {"values": "$manifest.governance_unit_county"})])
    errors, _ = orchestrator(path, tmp_path).validate()
    assert any("soil/ primitives only" in e and "standardize" in e for e in errors)


def test_a_preparation_needs_a_preparation_method(tmp_path):
    plot = a_plot(tmp_path)
    path = a_run(plot, "wrong_method", kind="preparation",
                 method={"ref": ANALYSIS_METHOD},
                 steps=[step("units_repair", "soil/repair_geometry",
                             {"features": "$manifest.governance_unit_county"})])
    errors, _ = orchestrator(path, tmp_path).validate()
    assert any("must be a preparation method" in e for e in errors)


def test_an_experiment_cannot_use_a_preparation_method(tmp_path):
    plot = a_plot(tmp_path)
    path = a_run(plot, "no_answer", method={"ref": PREP_METHOD},
                 curiosity={"ref": "$curiosity-space/information/information_access"},
                 steps=[step("units_repair", "soil/repair_geometry",
                             {"features": "$manifest.governance_unit_county"})])
    errors, _ = orchestrator(path, tmp_path).validate()
    assert any("is a preparation method" in e for e in errors)


def test_an_unknown_kind_is_refused_when_parsed(tmp_path):
    plot = a_plot(tmp_path)
    path = a_run(plot, "typo", kind="preperation", method={"ref": PREP_METHOD},
                 steps=[])
    with pytest.raises(ValueError, match="kind must be one of"):
        parse_experiment(path)


def test_an_older_file_without_kind_reads_as_an_experiment(tmp_path):
    plot = a_plot(tmp_path)
    path = a_run(plot, "older", method={"ref": ANALYSIS_METHOD},
                 curiosity={"ref": "$curiosity-space/information/broadband_access"},
                 steps=[])
    lineage = parse_experiment(path).lineage
    assert lineage.kind == "experiment"
    assert lineage.curiosity_ref == "$curiosity-space/information/broadband_access"


# ── the Maine preparations as committed ──────────────────────────────────
@pytest.mark.parametrize("name", ["maine_county_units", "maine_cousub_indicator_values",
                                  "maine_counties", "maine_governance_units"])
def test_each_maine_preparation_validates_as_one(name):
    path = REPO / "plots" / "maine" / "preparations" / f"{name}.yml"
    orch = Orchestrator(path, project_root=REPO)
    errors, _ = orch.validate()
    assert errors == []
    lineage = orch._lineage_dict()
    assert lineage["kind"] == "preparation" and "curiosity" not in lineage


def test_wonder_never_offers_a_preparation_method_as_an_answer():
    from canopy.wonder.possibility import _candidate_methods
    methods = {
        "county_units_for_mapping": {"id": "county_units_for_mapping",
                                     "domain": "information", "kind": "preparation"},
        "cii_indicator_values": {"id": "cii_indicator_values", "domain": "information"},
    }
    by_domain = _candidate_methods({"domain": "information"}, methods)
    by_name = _candidate_methods(
        {"compatible_methods": [{"ref": "$methods/information/county_units_for_mapping"}]},
        methods)
    assert [m["id"] for m in by_domain] == ["cii_indicator_values"]
    assert by_name == []


def test_an_experiment_with_no_curiosity_says_so_in_its_receipts(tmp_path, monkeypatch):
    # E-6: the warning reaches the receipt, not only the terminal
    plot = a_plot(tmp_path)
    path = a_run(plot, "no_question", method={"ref": ANALYSIS_METHOD},
                 curiosity={"ref": ""},
                 steps=[step("units_repair", "soil/repair_geometry",
                             {"features": "$manifest.governance_unit_county"},
                             output="repaired")])
    orch = orchestrator(path, tmp_path)
    fake_builder(monkeypatch, orch)
    assert orch.run().success
    receipt = json.loads(
        (plot / ".envelopes" / "units_repair_repaired.envelope.json").read_text())
    assert any("names no curiosity" in w["message"] for w in receipt["warnings"])


def test_a_preparation_writes_no_curiosity_warning(tmp_path, monkeypatch):
    plot = a_plot(tmp_path)
    path = a_run(plot, "county_units", kind="preparation", method={"ref": PREP_METHOD},
                 steps=[step("units_repair", "soil/repair_geometry",
                             {"features": "$manifest.governance_unit_county"},
                             output="repaired")])
    orch = orchestrator(path, tmp_path)
    fake_builder(monkeypatch, orch)
    assert orch.run().success
    receipt = json.loads(
        (plot / ".envelopes" / "units_repair_repaired.envelope.json").read_text())
    assert not any("names no curiosity" in w["message"] for w in receipt["warnings"])
