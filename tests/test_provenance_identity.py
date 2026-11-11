"""
tests/test_provenance_identity.py  |  rewildingCities, Sprint 05 change 1

A provenance entry names the run and the step that made it (D-167), and that
name travels with every inherited copy, so staleness can judge an entry
against its own declaration however far it has travelled (D-165).

A receipt written under the test profile round-trips and validates (HASH-2):
its skipped hash keeps its required, null value.
"""

import json
from pathlib import Path

import jsonschema
import pytest

from canopy.envelope import (Envelope, EnvelopeBuilder, EnvelopeInput, HashInfo,
                             Hasher, InputRecord, ProvenanceEntry)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "seeds" / "schemas" / "provenance.schema.json").read_text())


def make_entry(run=None, step=None, hash_info=None, branch=None):
    return ProvenanceEntry(
        primitive="build_places", version="1.0.0",
        timestamp="2026-11-11T09:30:07+00:00", params={"state_fips": "23"},
        inputs=[InputRecord(
            name="spine", semantic_type="block_spine", path="plots/maine/.data/spine.parquet",
            hash=hash_info or HashInfo(value="a30f87139b019bdca59111e4892379bf",
                                       method="full_file", algorithm="md5"))],
        duration_seconds=1.0, lineage_branch=branch, run=run, step=step)


def make_envelope(entries):
    return Envelope(data={"path": "plots/maine/.data/graph_places_places.parquet",
                          "format": "parquet", "secondary": {}},
                    metadata={"semantic_type": "places"},
                    provenance=entries, warnings=[])


def validate(entry_dict):
    jsonschema.Draft202012Validator(SCHEMA).validate(entry_dict)


def round_trip(envelope):
    return Envelope.from_dict(json.loads(json.dumps(envelope.to_dict())))


# HASH-2

def test_a_skipped_hash_writes_its_null_value(tmp_path):
    f = tmp_path / "input.csv"
    f.write_text("a,b\n1,2\n")
    skipped = Hasher(profile="test").hash_file(f)
    written = make_envelope([make_entry(hash_info=skipped)]).to_dict()
    record = written["provenance"][0]["inputs"][0]["hash"]
    assert record["value"] is None
    assert record["method"] == "skipped"
    validate(written["provenance"][0])


def test_a_skipped_hash_round_trips(tmp_path):
    f = tmp_path / "input.csv"
    f.write_text("a,b\n1,2\n")
    skipped = Hasher(profile="test").hash_file(f)
    back = round_trip(make_envelope([make_entry(hash_info=skipped)]))
    assert back.provenance[0].inputs[0].hash.value is None
    assert back.provenance[0].inputs[0].hash.reason == "test profile"


def test_a_receipt_written_before_the_fix_still_loads():
    old = make_envelope([make_entry()]).to_dict()
    old["provenance"][0]["inputs"][0]["hash"] = {"method": "skipped", "reason": "test profile"}
    back = Envelope.from_dict(old)
    assert back.provenance[0].inputs[0].hash.value is None


# D-167

def test_run_and_step_are_written_and_read():
    env = make_envelope([make_entry(run="maine_geography_graph", step="graph_places")])
    written = env.to_dict()["provenance"][0]
    assert written["run"] == "maine_geography_graph"
    assert written["step"] == "graph_places"
    validate(written)
    back = round_trip(env)
    assert (back.provenance[0].run, back.provenance[0].step) == ("maine_geography_graph", "graph_places")


def test_an_entry_from_before_d167_keeps_its_shape():
    written = make_envelope([make_entry()]).to_dict()["provenance"][0]
    assert "run" not in written and "step" not in written
    validate(written)
    back = Envelope.from_dict(make_envelope([make_entry()]).to_dict())
    assert back.provenance[0].run is None and back.provenance[0].step is None


def test_the_entry_stays_closed_to_unknown_fields():
    written = make_envelope([make_entry(run="r", step="s")]).to_dict()["provenance"][0]
    written["stp"] = "a misspelling"
    with pytest.raises(jsonschema.ValidationError):
        validate(written)


def test_inherited_entries_keep_their_own_run_and_step():
    places = make_envelope([make_entry(run="maine_geography_graph", step="graph_places")])
    seats_entry = make_entry(run="maine_seats", step="seats")
    builder = object.__new__(EnvelopeBuilder)
    merged = builder._merge_provenance([EnvelopeInput(name="places", envelope=places)], seats_entry)
    inherited, own = merged[0], merged[-1]
    assert (inherited.run, inherited.step) == ("maine_geography_graph", "graph_places")
    assert inherited.lineage_branch == "places"
    assert (own.run, own.step) == ("maine_seats", "seats")
