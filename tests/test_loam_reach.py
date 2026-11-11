"""
tests/test_loam_reach.py  |  rewildingCities, Sprint 05 changes 2 and 3

LOAM-1: one run reads another run's output by semantic type, `$loam.<type>`
(D-163), answered by the plot's loam bed, rebuilt fresh from its receipts
(D-164). Exactly one tended or gathered artifact of the type must be there;
none, several, a manifest dataset, an unknown type, and a type the run makes
itself are each refused, naming why.

Change 3 judges what was reached before any step runs (D-165, D-166): a
changed input or a changed declaration is stale and refuses; an unhashed
input, a missing file, a missing declaration, or a step from before D-167
cannot be told, and the run proceeds, saying so in its receipt.

Nothing here runs a primitive. As in test_preparations.py, the real
orchestrator, registries, vocabulary and methods index are used, and only
EnvelopeBuilder.run is a fake that writes an output file and returns the
envelope a primitive would. The small helpers are repeated here rather than
imported, so each test file can be read on its own.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from canopy.envelope import (BuildResult, Envelope, HashInfo, Hasher, InputRecord,
                             ProvenanceEntry)
from canopy.orchestrator.orchestrator import Orchestrator
from canopy.orchestrator.references import ReferenceResolver
from canopy.wonder.session import open_plot

REPO = Path(__file__).resolve().parents[1]
PREP_METHOD = "$methods/information/county_units_for_mapping"


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
                "available": True, "semantic_type": "governance_unit",
                "format": "geojson", "source": {"type": "manual"},
                "cache": {"path": ".data/counties.geojson"},
            },
        },
    }))
    return plot


def a_preparation(plot, name, steps):
    folder = plot / "preparations"
    folder.mkdir(exist_ok=True)
    path = folder / f"{name}.yml"
    path.write_text(yaml.safe_dump({
        "id": name, "name": name, "city": "demo", "kind": "preparation",
        "manifest": "../manifest.yml", "method": {"ref": PREP_METHOD},
        "choices": {}, "parameters": {}, "steps": steps}, sort_keys=False))
    return path


def a_step(step_id, inputs, output_name, output_type):
    return {"id": step_id, "primitive": "soil/repair_geometry", "inputs": inputs,
            "outputs": {output_name: output_type}, "params": {}}


def recorded_hash(path):
    """the hash a full-profile run would record, so freshness can recompute
    it later; a path that is not a file is recorded as skipped."""
    if Path(path).is_file():
        return Hasher(profile="full").hash_file(path)
    return HashInfo(value=None, method="skipped", reason="test fixture")


def run(path, tmp_path, seen=None):
    """run one preparation with a fake primitive; `seen` collects, per step,
    the inputs the builder was handed."""
    orch = Orchestrator(path, project_root=REPO, output_dir=tmp_path / "out")

    def fake(primitive, version, inputs, output_path, output_format,
             output_semantic_type, output_data_category, params=None,
             passthrough=False, run=None, step=None):
        if seen is not None:
            seen[step] = inputs
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text("{}")
        records = [InputRecord(
            name=i.name,
            semantic_type=(i.envelope.metadata["semantic_type"] if i.envelope else i.semantic_type),
            path=str(i.envelope.data["path"] if i.envelope else i.path),
            hash=recorded_hash(i.envelope.data["path"] if i.envelope else i.path))
            for i in inputs]
        env = Envelope(
            data={"path": str(output_path), "format": output_format},
            metadata={"semantic_type": output_semantic_type,
                      "data_category": output_data_category,
                      "crs": None if output_data_category == "tabular" else "EPSG:4326"},
            provenance=[ProvenanceEntry(
                primitive=Path(primitive).stem, version=version,
                timestamp="2026-11-11T00:00:00Z", params=params or {},
                inputs=records, duration_seconds=0.0, run=run, step=step)],
            warnings=[])
        return BuildResult(success=True, envelope=env, error=None, message=None)

    orch.envelope_builder.run = fake
    orch._write_run_log = lambda result: None
    return orch, orch.run()


def make_places(plot, tmp_path, step_id="graph_places", name="geography"):
    path = a_preparation(plot, name, [a_step(
        step_id, {"features": "$manifest.governance_unit_county"}, "places", "places")])
    _, result = run(path, tmp_path)
    assert result.success, result.error or result.message
    return path


def read_places(plot, name="seats"):
    return a_preparation(plot, name, [a_step(
        "seats", {"features": "$loam.places"}, "seats", "governance_unit")])


# ── reaching ──────────────────────────────────────────────────────────────
def test_a_run_reaches_what_another_run_made(tmp_path):
    plot = a_plot(tmp_path)
    make_places(plot, tmp_path)
    seen = {}
    _, result = run(read_places(plot), tmp_path, seen)
    assert result.success, result.error or result.message
    (given,) = seen["seats"]
    assert given.envelope is not None, "a $loam. input arrives with its envelope"
    assert given.envelope.metadata["semantic_type"] == "places"
    made_by = given.envelope.provenance[-1]
    assert (made_by.run, made_by.step) == ("geography", "graph_places")


def test_open_plot_reads_the_folder_it_is_given(tmp_path):
    plot = a_plot(tmp_path)
    _vocab, _loam, report = open_plot("demo", root=REPO, directory=plot)
    assert report["planted"] == 1
    assert (plot / ".loam" / "loam.duckdb").is_file()


# ── refusals, each naming its reason ──────────────────────────────────────
def test_nothing_made_is_refused(tmp_path):
    plot = a_plot(tmp_path)
    _, result = run(read_places(plot), tmp_path)
    assert not result.success
    assert result.error == "Input resolution failed"
    assert "no run in plot 'demo' has made places" in result.message


def test_two_makers_are_refused_naming_both(tmp_path):
    plot = a_plot(tmp_path)
    make_places(plot, tmp_path, step_id="graph_places", name="geography")
    make_places(plot, tmp_path, step_id="older_places", name="older_geography")
    _, result = run(read_places(plot), tmp_path)
    assert not result.success
    assert "2 artifacts" in result.message
    assert "graph_places_places.envelope.json" in result.message
    assert "older_places_places.envelope.json" in result.message


def test_a_manifest_dataset_is_not_reached_through_loam(tmp_path):
    plot = a_plot(tmp_path)
    path = a_preparation(plot, "seats", [a_step(
        "seats", {"features": "$loam.governance_unit"}, "seats", "places")])
    _, result = run(path, tmp_path)
    assert not result.success
    assert "only as a manifest dataset" in result.message
    assert "$manifest." in result.message


def test_an_unknown_type_is_refused(tmp_path):
    plot = a_plot(tmp_path)
    path = a_preparation(plot, "seats", [a_step(
        "seats", {"features": "$loam.not_a_type_anywhere"}, "seats", "places")])
    _, result = run(path, tmp_path)
    assert not result.success
    assert "has no type 'not_a_type_anywhere'" in result.message


def test_a_run_cannot_reach_for_what_it_makes(tmp_path):
    plot = a_plot(tmp_path)
    path = a_preparation(plot, "loop", [
        a_step("graph_places", {"features": "$manifest.governance_unit_county"},
               "places", "places"),
        a_step("seats", {"features": "$loam.places"}, "seats", "governance_unit")])
    errors, _ = Orchestrator(path, project_root=REPO).validate()
    assert any("makes itself" in e and "$steps.graph_places.places" in e for e in errors)


def a_resolver(loam_reach=None):
    return ReferenceResolver(
        manifest=SimpleNamespace(datasets={}),
        experiment=SimpleNamespace(choices={}, parameters={}, steps=[]),
        loam_reach=loam_reach)


def test_loam_is_refused_as_a_param():
    with pytest.raises(ValueError, match="not param values"):
        a_resolver().resolve_param_value("$loam.places", context="step 'x' params.y")


def test_a_resolver_given_no_plot_says_so():
    with pytest.raises(ValueError, match="given no plot to read"):
        a_resolver().resolve_input("$loam.places")


def test_loam_names_a_type_never_its_maker():
    with pytest.raises(ValueError, match="never who made it"):
        a_resolver().resolve_input("$loam.geography.places")


# ── freshness, judged before any step runs (change 3) ─────────────────────
def receipt(plot, name):
    return json.loads((plot / ".envelopes" / f"{name}.envelope.json").read_text())


def rewrite_receipt(plot, name, change):
    path = plot / ".envelopes" / f"{name}.envelope.json"
    doc = json.loads(path.read_text())
    change(doc)
    path.write_text(json.dumps(doc))


def test_an_unchanged_input_reads_as_fresh_and_the_receipt_says_so(tmp_path):
    plot = a_plot(tmp_path)
    make_places(plot, tmp_path)
    _, result = run(read_places(plot), tmp_path)
    assert result.success, result.error or result.message
    (record,) = receipt(plot, "seats_seats")["metadata"]["lineage"]["loam_inputs"]
    assert record["type"] == "places" and record["verdict"] == "fresh"
    assert record["not_judged"] == "primitive code"
    assert any("is fresh" in w and "primitive code is not checked" in w for w in result.warnings)


def test_a_changed_input_is_stale_and_nothing_runs(tmp_path):
    plot = a_plot(tmp_path)
    make_places(plot, tmp_path)
    (plot / ".data" / "counties.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "features": [], "edited": True}))
    _, result = run(read_places(plot), tmp_path)
    assert not result.success
    assert result.error == "Stale input" and result.failed_step == "seats"
    assert "counties.geojson" in result.message and "has changed since" in result.message
    assert "rerun geography" in result.message
    assert "primitive code is not checked" in result.message
    assert not (plot / ".envelopes" / "seats_seats.envelope.json").exists()


def test_a_changed_declaration_is_stale(tmp_path):
    plot = a_plot(tmp_path)
    producer = make_places(plot, tmp_path)
    doc = yaml.safe_load(producer.read_text())
    doc["steps"][0]["params"] = {"tolerance_m": 5}
    producer.write_text(yaml.safe_dump(doc, sort_keys=False))
    _, result = run(read_places(plot), tmp_path)
    assert result.error == "Stale input"
    assert ("step graph_places of geography is now declared with different params "
            "(tolerance_m)") in result.message


def test_a_receipt_from_before_d167_cannot_be_told_and_says_so(tmp_path):
    plot = a_plot(tmp_path)
    make_places(plot, tmp_path)

    def forget_identity(doc):
        for entry in doc["provenance"]:
            entry.pop("run", None)
            entry.pop("step", None)
    rewrite_receipt(plot, "graph_places_places", forget_identity)

    _, result = run(read_places(plot), tmp_path)
    assert result.success, result.error or result.message
    seats = receipt(plot, "seats_seats")
    assert seats["metadata"]["lineage"]["loam_inputs"][0]["verdict"] == "cannot_tell"
    told = [w["message"] for w in seats["warnings"] if "cannot be fully told" in w["message"]]
    assert len(told) == 1 and "recorded before D-167" in told[0]


def test_a_missing_input_file_cannot_be_told(tmp_path):
    plot = a_plot(tmp_path)
    make_places(plot, tmp_path)
    (plot / ".data" / "counties.geojson").unlink()
    _, result = run(read_places(plot), tmp_path)
    assert result.success, result.error or result.message
    assert any("no longer on disk" in w for w in result.warnings)


def test_a_missing_declaration_cannot_be_told(tmp_path):
    plot = a_plot(tmp_path)
    producer = make_places(plot, tmp_path)
    producer.unlink()
    _, result = run(read_places(plot), tmp_path)
    assert result.success, result.error or result.message
    assert any("no run with id geography is declared" in w for w in result.warnings)


def test_one_input_recorded_twice_is_checked_once(tmp_path):
    from canopy.loam.freshness import judge, FRESH
    f = tmp_path / "blocks.csv"
    f.write_text("block,pop\n1,10\n")
    entry = ProvenanceEntry(
        primitive="build_block_spine", version="1.0.0", timestamp="2026-11-11T00:00:00Z",
        params={}, inputs=[InputRecord(name="counts", semantic_type="census_block_counts",
                                       path=str(f), hash=recorded_hash(f))],
        duration_seconds=0.0, run="geography", step="graph_spine")
    env = Envelope(data={"path": "x"}, metadata={"semantic_type": "places"},
                   provenance=[entry, entry], warnings=[])
    verdict = judge(env, tmp_path, lambda run, step: ({}, None))
    assert verdict.status == FRESH
    assert verdict.checked_inputs == 1 and verdict.checked_steps == 1
