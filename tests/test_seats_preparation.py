"""
tests/test_seats_preparation.py  |  rewildingCities, Sprint 05 change 4

Seats as their own preparation (D-141), reading places through loam
(LOAM-1, D-163 to D-166). This closes Sprint 04's step 4 on its dependency
(TIME-2): build_seats runs, for real, on places another run made.

The places run is faked, as in test_loam_reach.py, so no Census data is
needed. The seats run is not: the real orchestrator runs the real
build_seats primitive on rosters in the exact shapes fetched 2026-11-11,
synthetic and phone-free (D-138, D-139), from tests/test_seats.py.
"""

import importlib.util
import json
from pathlib import Path

import pandas as pd
import yaml

from canopy.envelope import (BuildResult, Envelope, HashInfo, Hasher, InputRecord,
                             ProvenanceEntry)
from canopy.orchestrator.orchestrator import Orchestrator

REPO = Path(__file__).resolve().parents[1]
MAINE_SEATS = REPO / "plots" / "maine" / "preparations" / "maine_seats.yml"

spec = importlib.util.spec_from_file_location("seat_fixtures", REPO / "tests" / "test_seats.py")
seat_fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seat_fixtures)


# ── the Maine preparation as committed ────────────────────────────────────
def test_the_maine_seats_preparation_validates_as_one():
    orch = Orchestrator(MAINE_SEATS, project_root=REPO)
    errors, _ = orch.validate()
    assert errors == []
    lineage = orch._lineage_dict()
    assert lineage["kind"] == "preparation" and "curiosity" not in lineage
    (step,) = orch.experiment.steps
    assert step.inputs["places"] == "$loam.places"
    declared = {t["name"] for t in step.params["tribal_seats"]}
    assert declared == {t["name"] for t in seat_fixtures.TRIBAL}


# ── a small plot with rosters, written fresh for each test ────────────────
def a_plot(tmp_path, rosters_available=True):
    plot = tmp_path / "plots" / "demo"
    (plot / ".data").mkdir(parents=True)
    (plot / ".data" / "counties.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "features": []}))
    seat_fixtures.house_roster().to_csv(plot / ".data" / "house.csv", index=False)
    seat_fixtures.senate_roster().to_csv(plot / ".data" / "senate.csv", index=False)

    def roster(chamber):
        return {"available": rosters_available, "semantic_type": "legislature_roster",
                "format": "csv", "source": {"type": "manual"},
                "cache": {"path": f".data/{chamber}.csv"}}

    (plot / "manifest.yml").write_text(yaml.safe_dump({
        "city": {"id": "demo", "name": "demo"},
        "crs": {"working": "EPSG:4326"},
        "datasets": {
            "governance_unit_county": {
                "available": True, "semantic_type": "governance_unit",
                "format": "geojson", "source": {"type": "manual"},
                "cache": {"path": ".data/counties.geojson"}},
            "house_roster": roster("house"),
            "senate_roster": roster("senate"),
        },
    }))
    return plot


def a_preparation(plot, name, method, steps):
    folder = plot / "preparations"
    folder.mkdir(exist_ok=True)
    path = folder / f"{name}.yml"
    path.write_text(yaml.safe_dump({
        "id": name, "name": name, "city": "demo", "kind": "preparation",
        "manifest": "../manifest.yml", "method": {"ref": method},
        "choices": {}, "parameters": {}, "steps": steps}, sort_keys=False))
    return path


def make_places(plot, tmp_path):
    """a places run, faked: it writes the small places table test_seats.py
    builds seats from, with a receipt that records real input hashes."""
    path = a_preparation(plot, "geography", "$methods/information/county_units_for_mapping", [{
        "id": "graph_places", "primitive": "soil/repair_geometry",
        "inputs": {"features": "$manifest.governance_unit_county"},
        "outputs": {"places": "places"}, "params": {}}])
    orch = Orchestrator(path, project_root=REPO, output_dir=tmp_path / "out")

    def fake(primitive, version, inputs, output_path, output_format,
             output_semantic_type, output_data_category, params=None,
             passthrough=False, run=None, step=None):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        seat_fixtures.places().to_parquet(output_path, index=False)
        records = [InputRecord(name=i.name, semantic_type=i.semantic_type, path=str(i.path),
                               hash=Hasher(profile="full").hash_file(i.path)) for i in inputs]
        env = Envelope(
            data={"path": str(output_path), "format": output_format},
            metadata={"semantic_type": output_semantic_type,
                      "data_category": output_data_category, "crs": None},
            provenance=[ProvenanceEntry(
                primitive="build_places", version=version,
                timestamp="2026-11-11T00:00:00Z", params=params or {},
                inputs=records, duration_seconds=0.0, run=run, step=step)],
            warnings=[])
        return BuildResult(success=True, envelope=env, error=None, message=None)

    orch.envelope_builder.run = fake
    orch._write_run_log = lambda result: None
    result = orch.run()
    assert result.success, result.error or result.message


def a_seats_run(plot, tmp_path):
    step = yaml.safe_load(MAINE_SEATS.read_text())["steps"][0]
    step["inputs"] = {"places": "$loam.places", "house": "$manifest.house_roster",
                      "senate": "$manifest.senate_roster"}
    path = a_preparation(plot, "seats_133", "$methods/information/legislative_seats", [step])
    orch = Orchestrator(path, project_root=REPO, output_dir=tmp_path / "out")
    orch._write_run_log = lambda result: None
    return orch.run()


# ── step 4, closed on its dependency ──────────────────────────────────────
def test_build_seats_runs_for_real_on_places_another_run_made(tmp_path):
    plot = a_plot(tmp_path)
    make_places(plot, tmp_path)
    result = a_seats_run(plot, tmp_path)
    assert result.success, result.error or result.message

    (written,) = (tmp_path / "out").glob("seats_seats.*")
    seats = (pd.read_parquet(written) if written.suffix == ".parquet"
             else pd.read_csv(written, dtype=str, keep_default_na=False))
    assert len(seats) == 3 + 2 + 4
    assert set(seats.loc[seats["seat_kind"] == "tribal", "seat_ref"]) == \
        {t["name"] for t in seat_fixtures.TRIBAL}

    receipt = json.loads((plot / ".envelopes" / "seats_seats.envelope.json").read_text())
    assert receipt["metadata"]["lineage"]["loam_inputs"][0]["verdict"] == "fresh"
    made = {(e.get("run"), e.get("step")) for e in receipt["provenance"]}
    assert ("geography", "graph_places") in made, "places' own entry travels into seats"
    assert ("seats_133", "seats") in made


def test_a_seats_run_waits_for_its_rosters_and_says_so(tmp_path):
    plot = a_plot(tmp_path, rosters_available=False)
    make_places(plot, tmp_path)
    result = a_seats_run(plot, tmp_path)
    assert not result.success
    assert "house_roster" in (result.error or "") and "senate_roster" in (result.error or "")
    assert not (plot / ".envelopes" / "seats_seats.envelope.json").exists()
