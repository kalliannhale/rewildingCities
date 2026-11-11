"""
tests/test_publication_steps.py  |  rewildingCities

Contract 1, rule 11 (D-143): a step that changes what leaves records it in its
own provenance entry, the builder stamps by and at, the record travels with
the entry to every descendant, and the gate gathers every record in the chain,
in order, each once. The primitive runner is a stand-in, so no primitive runs.

The builder uses the dev profile: a test-profile hash drops its null value in
to_dict, which from_dict and the schema both require (HASH-2).
"""

from __future__ import annotations

from canopy.envelope import (Envelope, EnvelopeBuilder, EnvelopeInput,
                             validate_envelope)
from canopy.expose.gate import publication_steps
from canopy.paths import project_root
from canopy.primitive import PrimitiveResult

CLIP = {"step": "clipped", "detail": "to the 2024 land faces", "count": 3}
ROUND = {"step": "rounded", "detail": "shares to 4 places", "count": 530}


class StandIn:
    """writes an empty output and answers every run with the metadata it was
    given, so the next generation has a file to hash."""

    def __init__(self, metadata):
        self.metadata = metadata

    def run(self, primitive, inputs, output_path, params):
        open(output_path, "wb").close()
        return PrimitiveResult(success=True, output_path=str(output_path),
                               metadata=dict(self.metadata), warnings=[])


def run(tmp_path, name, inputs, metadata):
    builder = EnvelopeBuilder(profile="dev", project_root=project_root())
    builder.runner = StandIn(dict({"crs": "EPSG:4326"}, **metadata))
    return builder.run(primitive=f"transform/{name}.py", version="1.0.0", inputs=inputs,
                       output_path=tmp_path / f"{name}.geojson", output_format="geojson",
                       output_semantic_type="governance_unit", output_data_category="vector")


def raw(tmp_path):
    path = tmp_path / "faces.zip"
    path.write_bytes(b"")
    return EnvelopeInput(name="faces", path=str(path), semantic_type="census_faces")


def test_builder_stamps_by_and_at_and_keeps_metadata_clean(tmp_path):
    res = run(tmp_path, "outline", [raw(tmp_path)], {"publication": [CLIP]})
    assert res.success, res.message
    entry = res.envelope.provenance[-1]
    assert entry.publication == [dict(CLIP, by="outline", at=entry.timestamp)]
    assert "publication" not in res.envelope.metadata


def test_record_survives_two_generations(tmp_path):
    first = run(tmp_path, "outline", [raw(tmp_path)], {"publication": [CLIP]}).envelope
    second = run(tmp_path, "join", [EnvelopeInput(name="outlines", envelope=first)], {}).envelope
    third = run(tmp_path, "render", [EnvelopeInput(name="joined", envelope=second)], {}).envelope
    clip = [e for e in third.provenance if e.publication]
    assert len(clip) == 1
    assert clip[0].primitive == "outline"
    assert clip[0].lineage_branch == "outlines"
    assert clip[0].publication[0]["step"] == "clipped"
    assert third.provenance[-1].publication == []
    again = Envelope.from_dict(third.to_dict())
    assert again.to_dict() == third.to_dict()


def test_gate_gathers_in_chain_order_each_once(tmp_path):
    first = run(tmp_path, "outline", [raw(tmp_path)], {"publication": [CLIP]}).envelope
    both = [EnvelopeInput(name="left", envelope=first),
            EnvelopeInput(name="right", envelope=first)]
    joined = run(tmp_path, "join", both, {"publication": [ROUND]}).envelope
    doc = joined.to_dict()
    assert sum(1 for e in doc["provenance"] if e["publication"]) == 3
    steps = publication_steps(doc)
    assert [s["step"] for s in steps] == ["clipped", "rounded"]
    assert steps[0]["by"] == "outline" and steps[0]["lineage_branch"] == "left"
    assert steps[1]["by"] == "join" and steps[1]["lineage_branch"] is None


def test_gate_never_reads_metadata_publication():
    doc = {"metadata": {"semantic_type": "x", "publication": [CLIP]},
           "provenance": [{"primitive": "p", "lineage_branch": None, "inputs": []}]}
    assert publication_steps(doc) == []


def test_old_receipt_without_records_reads_as_none(tmp_path):
    doc = run(tmp_path, "outline", [raw(tmp_path)], {}).envelope.to_dict()
    for entry in doc["provenance"]:
        del entry["publication"]
    back = Envelope.from_dict(doc)
    assert all(e.publication == [] for e in back.provenance)


def test_unknown_step_refused_at_write(tmp_path):
    good = run(tmp_path, "outline", [raw(tmp_path)], {"publication": [CLIP]}).envelope.to_dict()
    bad = run(tmp_path, "outline", [raw(tmp_path)],
              {"publication": [dict(CLIP, step="carved")]}).envelope.to_dict()
    new = set(validate_envelope(bad, project_root())) - set(validate_envelope(good, project_root()))
    assert new, "a step outside the closed set passed the schema"
    assert all("carved" in e for e in new)


def test_primitive_that_stamps_by_is_refused(tmp_path):
    res = run(tmp_path, "outline", [raw(tmp_path)],
              {"publication": [dict(CLIP, by="someone_else")]})
    assert not res.success
    assert res.error == "Publication record not understood"
    assert "stamped by" in res.message


def test_primitive_that_stamps_at_is_refused(tmp_path):
    res = run(tmp_path, "outline", [raw(tmp_path)],
              {"publication": [dict(CLIP, at="2026-01-01T00:00:00+00:00")]})
    assert not res.success
    assert "stamped at" in res.message


def test_records_that_are_not_a_list_are_refused(tmp_path):
    res = run(tmp_path, "outline", [raw(tmp_path)], {"publication": CLIP})
    assert not res.success
    assert "must be a list" in res.message
