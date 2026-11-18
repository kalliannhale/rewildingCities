"""
tests/test_told.py ~ the refusal record and the told copy (zip 9b1, D-363, D-370, D-376)

the refusal record holds the gate's refusals only: kinds of data and why,
never a value or a member, versioned by content that holds no time. the told
copy tells the profile's current version with the current refusal record,
lives under the profile's version, is named by everything that can change its
bytes, carries a `told` record, and is judged by the gate as the profile was.
the bucket is a fake that keeps the overwrite lock (D-309). ~
"""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

import pytest

from canopy.aws import s3, told
from canopy.wonder.telling import TellingContext, tell_all, tell_withheld

REPO = Path(__file__).resolve().parents[1]
PLOT = "demo"
_spec = importlib.util.spec_from_file_location(
    "_telling_fixtures", Path(__file__).with_name("test_telling.py"))
tf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tf)


class FakeError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class FakeS3:
    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.puts: list[dict] = []

    def get_object(self, Bucket, Key):
        if Key not in self.objects:
            raise FakeError("NoSuchKey")
        return {"Body": io.BytesIO(self.objects[Key]), "ETag": f'"{len(self.objects[Key])}"'}

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise FakeError("404")
        return {}

    def put_object(self, Bucket, Key, Body, **kw):
        self.puts.append(dict(kw, Key=Key))
        if "/versions/" in Key and kw.get("IfNoneMatch") != "*":
            raise FakeError("AccessDenied")
        if Key.endswith("/current") and not (kw.get("IfNoneMatch") or kw.get("IfMatch")):
            raise FakeError("AccessDenied")
        if kw.get("IfNoneMatch") == "*" and Key in self.objects:
            raise FakeError("PreconditionFailed")
        self.objects[Key] = bytes(Body)
        return {}

    def __getattr__(self, name):
        if "delete" in name:
            raise AssertionError(f"the told write asked the bucket to {name}")
        raise AttributeError(name)


JUDGED = {
    "outlets_points": {"semantic_type": "news_outlet_points", "result": {
        "decision": "refuse", "refusals": [
            {"rule": 5, "semantic_type": "news_outlet_points", "tier": "aggregate-only",
             "ancestor": "the artifact itself", "reason": "counts only",
             "would_admit": "aggregate it", "checked_at": "2026-11-18T00:00:00"}]}},
    "clerks_points": {"semantic_type": "clerk_office_points", "result": {"decision": "allow"}},
}


def test_a_receipt_the_write_refuses_before_the_gate_is_named_apart():
    """validate_counties_checked is MEGIS's own layer passed through: the write
    refuses it before asking the gate, so the record never tells it (D-363)."""
    judged = dict(JUDGED, validate_checked={"semantic_type": "governance_unit", "result": {
        "decision": "refuse", "refusals": [{"rule": 4}]}})
    record = told.refusal_record(PLOT, root=REPO, judged=judged,
                                 before_gate=lambda a: a == "validate_checked")
    assert [w["receipt"] for w in record["withheld"]] == ["outlets_points"]
    assert record["refused_before_the_gate"] == ["validate_checked"]


def test_the_record_holds_the_gates_refusals_and_no_time():
    record = told.refusal_record(PLOT, root=REPO, judged=JUDGED)
    assert [w["receipt"] for w in record["withheld"]] == ["outlets_points"]
    assert "checked_at" not in json.dumps(record)
    assert record["receipts_judged"] == 2 and record["target"] == "canonical"
    again = told.refusal_record(PLOT, root=REPO, judged=JUDGED)
    assert told.document_bytes(record) == told.document_bytes(again)


def test_the_record_is_written_once_and_its_pointer_moves_with_its_condition():
    client = FakeS3()
    record = told.refusal_record(PLOT, root=REPO, judged=JUDGED)
    first = told.write_refusals(record, client=client, bucket="b", by="tester", reason="a test")
    assert first["pointer"] == "created"
    assert "/_refusals/versions/" in first["written"][0]
    again = told.write_refusals(record, client=client, bucket="b", by="tester", reason="a test")
    assert again["pointer"] == "unchanged" and again["written"] == []
    judged = dict(JUDGED, clerks_points={"semantic_type": "x", "result": {
        "decision": "refuse", "refusals": [{"rule": 10}]}})
    moved = told.write_refusals(told.refusal_record(PLOT, root=REPO, judged=judged),
                                client=client, bucket="b", by="tester", reason="a test")
    assert moved["pointer"] == "moved" and moved["previous"] == first["sha256"]
    assert told.read_refusals(client, "b", PLOT)[0] == moved["sha256"]


def test_a_record_write_names_who_and_why():
    with pytest.raises(s3.CanonicalRefusal, match="who moved the pointer"):
        told.write_refusals({"plot": PLOT}, client=FakeS3(), bucket="b", by="", reason="x")


def test_no_receipt_can_take_the_records_name():
    with pytest.raises(s3.CanonicalRefusal):
        s3.validate_artifact(told.REFUSALS)


# ── the withheld field ───────────────────────────────────────────────────
def test_the_withheld_field_names_each_kind_once_with_why_and_no_id():
    ctx = TellingContext.load(tf.doc(), REPO)
    record = {"withheld": [
        {"semantic_type": "news_outlet_points", "refusals": [{"rule": 5}]},
        {"semantic_type": "news_outlet_points", "refusals": [{"rule": 5}]},
        {"semantic_type": "located_in_edges", "refusals": [{"rule": 9}, {"rule": 5}]}]}
    said = tell_withheld(record, ctx)
    assert said.startswith("This tool holds 2 kinds of data")
    assert said.lower().count("news outlet points") == 1 and "_" not in said
    assert not ctx.language.working_ids.search(said)
    assert "Nothing" in tell_withheld({"withheld": []}, ctx)


def test_only_the_states_row_tells_the_withheld_field():
    state = tf.profile(code="23", level="state", kind="state", name="Maine")
    town = tf.profile()
    rows, _ = tell_all(tf.doc(state, town), REPO, refusals={"withheld": []})
    assert [r["level"] for r in rows if "withheld" in r] == ["State"]
    rows, _ = tell_all(tf.doc(state, town), REPO)
    assert not any("withheld" in r for r in rows)


# ── the told copy ────────────────────────────────────────────────────────
def _profile_in(client, doc, sha_allow="9" * 64):
    data = json.dumps(doc).encode()
    sha = s3.sha256_of(data)
    prefix = s3.version_prefix(PLOT, told.PROFILE, sha)
    client.objects[f"{prefix}/data.json"] = data
    client.objects[f"{prefix}/envelope.json"] = json.dumps({
        "data": {"path": "x", "format": "json"},
        "metadata": {"semantic_type": "place_profile", "data_category": "tabular", "crs": None,
                     "context_notes": ["census_tribal_area"], "row_context_notes": []},
        "provenance": [{"primitive": "build_profile", "version": "1.0.0",
                        "timestamp": "2026-11-18T00:00:00+00:00", "params": {}, "inputs": [],
                        "duration_seconds": 1.0, "lineage_branch": None}],
        "warnings": []}).encode()
    client.objects[s3.pointer_key(PLOT, told.PROFILE)] = json.dumps(
        {"sha256": sha, "allow": sha_allow, "data": "data.json"}).encode()
    return sha


def allow(envelope, *, plot, plot_dir):
    return {"decision": "allow", "record": {"tiers": [
        {"semantic_type": "place_profile", "tier": "public", "ancestor": "x"}]}}


def _prepared(client, **kw):
    return told.prepare_told(PLOT, client=client, bucket="b", domain="d.example", root=REPO,
                             judge=kw.pop("judge", allow), validate=lambda e: [], **kw)


def _ready():
    client = FakeS3()
    sha = _profile_in(client, tf.doc(tf.profile(code="23", level="state", kind="state",
                                                name="Maine"), tf.profile()))
    told.write_refusals(told.refusal_record(PLOT, root=REPO, judged=JUDGED), client=client,
                        bucket="b", by="tester", reason="a test")
    return client, sha


def test_the_told_copy_lives_under_the_profiles_version_named_by_its_inputs():
    client, sha = _ready()
    p = _prepared(client)
    assert p.keys["json"].startswith(s3.version_prefix(PLOT, told.PROFILE, sha) + "/display/told_")
    assert p.name == told.told_name(told.told_inputs(REPO), p.refusals_sha256)
    assert p.rows == 2 and json.loads(p.body)["refusals_version"] == p.refusals_sha256


def test_the_name_moves_with_any_input_or_a_new_judgment():
    inputs = told.told_inputs(REPO)
    base = told.told_name(inputs, "r" * 64)
    assert told.told_name(inputs, "s" * 64) != base
    for rel in told.TOLD_INPUTS:
        assert told.told_name(dict(inputs, **{rel: "0" * 64}), "r" * 64) != base
    assert "canopy/wonder/place.py" in told.TOLD_INPUTS
    assert not any("standards" in rel for rel in told.TOLD_INPUTS)


def test_the_envelope_carries_the_profiles_chain_and_a_told_record():
    client, sha = _ready()
    env = _prepared(client).envelope
    assert env["metadata"]["derived_from"] == sha and env["metadata"]["row_count"] == 2
    assert env["data"]["format"] == "json"
    assert env["provenance"][0]["lineage_branch"] == "version"
    own = env["provenance"][-1]
    assert [s["step"] for s in own["publication"]] == ["told"]
    assert [i["name"] for i in own["inputs"]] == ["version"]
    assert own["params"]["refusals"]["version"]


def test_with_no_refusal_record_nothing_is_told():
    client = FakeS3()
    _profile_in(client, tf.doc(tf.profile(code="23", level="state", kind="state", name="Maine")))
    with pytest.raises(s3.CanonicalRefusal, match="no refusal record"):
        _prepared(client)


def test_with_no_state_row_the_record_has_no_home():
    client = FakeS3()
    _profile_in(client, tf.doc(tf.profile()))
    told.write_refusals({"plot": PLOT, "withheld": []}, client=client, bucket="b",
                        by="tester", reason="a test")
    with pytest.raises(s3.CanonicalRefusal, match="D-376"):
        _prepared(client)


def test_a_gate_refusal_refuses_the_told_copy():
    client, _ = _ready()

    def refuse(envelope, *, plot, plot_dir):
        return {"decision": "refuse", "refusals": [{"rule": 9, "reason": "a note"}]}
    with pytest.raises(s3.CanonicalRefusal, match="withheld"):
        _prepared(client, judge=refuse)


def test_the_told_copy_is_written_once_envelope_first():
    client, _ = _ready()
    p = _prepared(client)
    first = told.write_told(p, client=client, bucket="b")
    assert first["copy"] == "new" and first["written"][0].endswith(".envelope.json")
    assert told.write_told(p, client=client, bucket="b")["copy"] == "exists"
    client.objects[p.keys["json"]] = b"other bytes"
    with pytest.raises(s3.CanonicalRefusal, match="other bytes"):
        told.write_told(p, client=client, bucket="b")


def test_the_told_write_never_removes_anything():
    source = (REPO / "canopy" / "aws" / "told.py").read_text()
    assert "delete" not in source.lower().replace("deleted", "")


@pytest.mark.parametrize("argv,said", [
    (["canonical", "maine", "x", "--refusals"], "takes no artifact"),
    (["canonical", "maine", "--refusals", "--write"], "--by and --reason"),
    (["canonical", "maine", "--told"], "names the profile"),
    (["canonical", "maine", "p", "--told", "--display"], "takes no --display"),
    (["canonical", "maine", "p", "--told", "--local", "--write"], "never writes"),
])
def test_the_command_refuses_a_told_or_record_asked_wrongly(argv, said):
    import argparse
    from canopy.cli import canonical as cli
    parser = argparse.ArgumentParser()
    cli.register(parser.add_subparsers())
    assert said in cli._asked_wrongly(parser.parse_args(argv))
