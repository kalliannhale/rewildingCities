"""
tests/test_canonical_write.py  |  rewildingCities

Contract 2's canonical write, held through an injected fake client (D-305):
no moto, no network. The fake keeps the bucket policy's overwrite lock
(D-309) so a put without its condition fails here as it would in AWS, and it
answers any removal with an AssertionError.

The gate is a stand-in (judge=...), so these tests hold the writer, not the
gate: the gate has its own tests in tests/test_gate.py. One test converts a
real GeoJSON and is skipped where geopandas is not installed.
"""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path

import pytest

from canopy.aws import s3

PLOT = "demo"


class FakeError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class FakeS3:
    """a bucket that keeps the overwrite lock and refuses every removal."""

    def __init__(self):
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.puts: list[dict] = []
        self._n = 0

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise FakeError("404")
        return {"ETag": self.objects[Key][1]}

    def get_object(self, Bucket, Key):
        if Key not in self.objects:
            raise FakeError("NoSuchKey")
        body, etag = self.objects[Key]
        return {"Body": io.BytesIO(body), "ETag": etag}

    def put_object(self, Bucket, Key, Body, **kw):
        self.puts.append(dict(kw, Key=Key))
        if "/versions/" in Key and kw.get("IfNoneMatch") != "*":
            raise FakeError("AccessDenied")
        if Key.endswith("/current") and not (kw.get("IfNoneMatch") or kw.get("IfMatch")):
            raise FakeError("AccessDenied")
        if kw.get("IfNoneMatch") == "*" and Key in self.objects:
            raise FakeError("PreconditionFailed")
        if "IfMatch" in kw and (Key not in self.objects or self.objects[Key][1] != kw["IfMatch"]):
            raise FakeError("PreconditionFailed")
        self._n += 1
        self.objects[Key] = (bytes(Body), f'"etag-{self._n}"')
        return {"ETag": self.objects[Key][1]}

    def __getattr__(self, name):
        if "delete" in name:
            raise AssertionError(f"the canonical write asked the bucket to {name}")
        raise AttributeError(name)


def allow(tiers=None, steps=None, note="a draft note", checked_at="2026-11-16T00:00:00"):
    def judge(envelope, *, plot, plot_dir):
        return {"decision": "allow", "record": {
            "decision": "allow", "target": s3.TARGET, "sharing_level": s3.SHARING_LEVEL,
            "tiers": tiers or [{"semantic_type": "indicator_values", "tier": "public",
                                "ancestor": "the artifact itself"}],
            "context_notes": ["census_tribal_area"],
            "context_text": {"census_tribal_area": note},
            "publication_steps": steps or [], "gate_version": "test",
            "checked_at": checked_at}}
    return judge


def refuse(envelope, *, plot, plot_dir):
    return {"decision": "refuse", "refusals": [
        {"rule": 9, "reason": "a note does not travel", "would_admit": "a note"}]}


def receipt(root: Path, name: str, data: bytes, fmt: str = "parquet",
            path: str | None = None, secondary: dict | None = None) -> Path:
    """a receipt and its data file in a tiny garden, its path written the way
    real receipts write it (through preparations/..)."""
    plot = root / "plots" / PLOT
    (plot / ".data").mkdir(parents=True, exist_ok=True)
    (plot / ".envelopes").mkdir(parents=True, exist_ok=True)
    ext = {"parquet": "parquet", "geojson": "geojson", "json": "json", "csv": "csv"}[fmt]
    (plot / ".data" / f"{name}.{ext}").write_bytes(data)
    env = {"data": {"path": path or f"plots/{PLOT}/preparations/../.data/{name}.{ext}",
                    "format": fmt, "secondary": secondary or {}},
           "metadata": {"semantic_type": "indicator_values"}, "provenance": [], "warnings": []}
    p = plot / ".envelopes" / f"{name}.envelope.json"
    p.write_text(json.dumps(env, indent=2))
    return p


def write(root, name, client, judge=None, **kw):
    prepared = s3.prepare(PLOT, name, root=root, judge=judge or allow(), **kw)
    return prepared, s3.write(prepared, client=client, bucket="b", by="Kalli", reason="a test")


# ── the four Contract 2 names ────────────────────────────────────────────
def test_same_bytes_write_nothing(tmp_path):
    receipt(tmp_path, "counts", b"parquet bytes")
    client = FakeS3()
    _, first = write(tmp_path, "counts", client)
    assert first["version"] == "new" and first["pointer"] == "created"
    before = len(client.puts)
    _, again = write(tmp_path, "counts", client)
    assert again == dict(again, version="exists", pointer="unchanged", written=[])
    assert len(client.puts) == before


def test_a_refused_gate_writes_nothing(tmp_path):
    receipt(tmp_path, "counts", b"parquet bytes")
    with pytest.raises(s3.CanonicalRefusal) as e:
        s3.prepare(PLOT, "counts", root=tmp_path, judge=refuse)
    assert e.value.refusals[0]["rule"] == 9


def test_a_write_without_an_allow_record_is_refused(tmp_path):
    receipt(tmp_path, "counts", b"parquet bytes")
    prepared = s3.prepare(PLOT, "counts", root=tmp_path, judge=allow())
    prepared.allow_doc["gate"]["decision"] = "refuse"
    client = FakeS3()
    with pytest.raises(s3.CanonicalRefusal):
        s3.write(prepared, client=client, bucket="b", by="Kalli", reason="a test")
    assert client.puts == []


def test_every_put_carries_its_condition(tmp_path):
    receipt(tmp_path, "counts", b"version one")
    client = FakeS3()
    write(tmp_path, "counts", client)
    receipt(tmp_path, "counts", b"version two")
    write(tmp_path, "counts", client)
    for put in client.puts:
        if "/versions/" in put["Key"]:
            assert put.get("IfNoneMatch") == "*" and "IfMatch" not in put
    pointer = [p for p in client.puts if p["Key"].endswith("/current")]
    assert pointer[0].get("IfNoneMatch") == "*"
    assert pointer[1].get("IfMatch") == '"etag-4"'


def test_nothing_is_ever_removed():
    source = Path(s3.__file__).read_text()
    assert "delete" not in source.lower()


# ── the pointer ──────────────────────────────────────────────────────────
def test_a_move_keeps_previous_and_says_who_and_why(tmp_path):
    receipt(tmp_path, "counts", b"version one")
    client = FakeS3()
    first, _ = write(tmp_path, "counts", client)
    receipt(tmp_path, "counts", b"version two")
    second, moved = write(tmp_path, "counts", client)
    pointer = json.loads(client.objects[second.keys["current"]][0])
    assert moved["pointer"] == "moved"
    assert pointer["previous"] == first.sha256 and pointer["sha256"] == second.sha256
    assert pointer["moved_by"] == "Kalli" and pointer["reason"] == "a test"
    assert first.keys["data"] in client.objects


def test_a_pointer_moved_by_someone_else_is_left_alone(tmp_path):
    receipt(tmp_path, "counts", b"version one")
    client = FakeS3()
    write(tmp_path, "counts", client)
    receipt(tmp_path, "counts", b"version two")
    prepared = s3.prepare(PLOT, "counts", root=tmp_path, judge=allow())
    real_get = client.get_object

    def stale_get(Bucket, Key):
        got = real_get(Bucket=Bucket, Key=Key)
        if Key.endswith("/current"):
            got["ETag"] = '"someone-else"'
        return got
    client.get_object = stale_get
    with pytest.raises(s3.CanonicalRefusal, match="pointer moved"):
        s3.write(prepared, client=client, bucket="b", by="Kalli", reason="a test")
    assert prepared.keys["data"] in client.objects


def test_a_write_cut_off_partway_finishes(tmp_path):
    receipt(tmp_path, "counts", b"parquet bytes")
    prepared = s3.prepare(PLOT, "counts", root=tmp_path, judge=allow())
    client = FakeS3()
    client.objects[prepared.keys["envelope"]] = (prepared.receipt_bytes, '"etag-0"')
    result = s3.write(prepared, client=client, bucket="b", by="Kalli", reason="a test")
    assert prepared.keys["envelope"] not in result["written"]
    assert prepared.keys["data"] in result["written"]


def test_a_write_names_who_and_why(tmp_path):
    receipt(tmp_path, "counts", b"parquet bytes")
    prepared = s3.prepare(PLOT, "counts", root=tmp_path, judge=allow())
    with pytest.raises(s3.CanonicalRefusal):
        s3.write(prepared, client=FakeS3(), bucket="b", by=" ", reason="a test")


# ── the allow record, versioned inside its version (D-320) ──────────────
def test_a_rerun_that_judges_the_same_way_writes_nothing(tmp_path):
    from datetime import datetime, timezone
    receipt(tmp_path, "counts", b"parquet bytes")
    client = FakeS3()
    write(tmp_path, "counts", client, judge=allow(checked_at="2026-11-16T01:00:00"),
          now=datetime(2026, 11, 16, 1, tzinfo=timezone.utc))
    path = receipt(tmp_path, "counts", b"parquet bytes")
    path.write_text(path.read_text().replace('"warnings": []', '"warnings": [{"level": "info"}]'))
    before = len(client.puts)
    _, again = write(tmp_path, "counts", client, judge=allow(checked_at="2026-11-17T09:00:00"),
                     now=datetime(2026, 11, 17, 9, tzinfo=timezone.utc))
    assert again["pointer"] == "unchanged" and again["written"] == []
    assert len(client.puts) == before


def test_a_changed_note_writes_its_allow_record_alone_and_moves_the_pointer(tmp_path):
    receipt(tmp_path, "counts", b"parquet bytes")
    client = FakeS3()
    first, _ = write(tmp_path, "counts", client, judge=allow(note="a draft note"))
    second, moved = write(tmp_path, "counts", client, judge=allow(note="the nations' words"))
    assert second.sha256 == first.sha256 and second.allow_sha256 != first.allow_sha256
    assert moved["version"] == "exists" and moved["allow"] == "new"
    assert moved["written"] == [second.keys["allow"], second.keys["current"]]
    pointer = json.loads(client.objects[second.keys["current"]][0])
    assert pointer["sha256"] == pointer["previous"] == first.sha256
    assert pointer["allow"] == second.allow_sha256
    assert pointer["previous_allow"] == first.allow_sha256


def test_the_old_allow_record_is_kept(tmp_path):
    receipt(tmp_path, "counts", b"parquet bytes")
    client = FakeS3()
    first, _ = write(tmp_path, "counts", client, judge=allow(note="a draft note"))
    write(tmp_path, "counts", client, judge=allow(note="the nations' words"))
    kept = json.loads(client.objects[first.keys["allow"]][0])
    assert kept["gate"]["context_text"]["census_tribal_area"] == "a draft note"


def test_the_pointer_names_its_allow_record(tmp_path):
    receipt(tmp_path, "counts", b"parquet bytes")
    client = FakeS3()
    prepared, _ = write(tmp_path, "counts", client)
    pointer = json.loads(client.objects[prepared.keys["current"]][0])
    assert pointer["allow"] == prepared.allow_sha256 and pointer["previous_allow"] is None
    assert prepared.keys["allow"] in client.objects


def test_a_conversion_records_its_own_time_outside_the_allow_records_name(tmp_path):
    from datetime import datetime, timezone
    receipt(tmp_path, "points", b"{}", fmt="geojson")

    def converter(src, dst):
        dst.write_bytes(b"PAR1 stand-in")
        return {"features": 0, "crs": "EPSG:4326", "libraries": {"geopandas": "x"}}
    one = s3.prepare(PLOT, "points", root=tmp_path, judge=allow(), converter=converter,
                     now=datetime(2026, 11, 16, tzinfo=timezone.utc))
    two = s3.prepare(PLOT, "points", root=tmp_path, judge=allow(), converter=converter,
                     now=datetime(2026, 12, 1, tzinfo=timezone.utc))
    assert one.allow_sha256 == two.allow_sha256


# ── what the version holds ───────────────────────────────────────────────
def test_the_receipt_travels_byte_for_byte_and_the_allow_record_beside_it(tmp_path):
    path = receipt(tmp_path, "counts", b"parquet bytes")
    client = FakeS3()
    prepared, _ = write(tmp_path, "counts", client)
    assert client.objects[prepared.keys["envelope"]][0] == path.read_bytes()
    allow_doc = json.loads(client.objects[prepared.keys["allow"]][0])
    assert prepared.keys["allow"].endswith(f"/allow/{prepared.allow_sha256}.json")
    assert allow_doc["allow"] == prepared.allow_sha256 == s3.allow_identity(allow_doc)
    assert allow_doc["gate"]["decision"] == "allow"
    assert allow_doc["sha256"] == s3.sha256_of(b"parquet bytes")
    assert allow_doc["source"]["path"] == f"plots/{PLOT}/.data/counts.parquet"
    assert prepared.keys["data"].endswith(f"/versions/{prepared.sha256}/data.parquet")


def test_a_document_stays_json(tmp_path):
    receipt(tmp_path, "profiles", b'{"places": []}', fmt="json")
    prepared = s3.prepare(PLOT, "profiles", root=tmp_path, judge=allow())
    assert prepared.data_name == "data.json" and prepared.data_bytes == b'{"places": []}'
    assert prepared.allow_doc["gate"]["publication_steps"] == []


def test_geojson_is_converted_and_says_so(tmp_path):
    receipt(tmp_path, "points", b'{"type": "FeatureCollection", "features": []}', fmt="geojson")

    def converter(src, dst):
        dst.write_bytes(b"PAR1 stand-in")
        return {"features": 0, "crs": "EPSG:4326", "libraries": {"geopandas": "x"}}
    prepared = s3.prepare(PLOT, "points", root=tmp_path, judge=allow(), converter=converter)
    assert prepared.canonical_format == "geoparquet" and prepared.data_name == "data.parquet"
    assert prepared.sha256 == s3.sha256_of(b"PAR1 stand-in")
    step = prepared.allow_doc["gate"]["publication_steps"][-1]
    assert step["step"] == "format_changed" and step["by"] == s3.WRITTEN_BY
    assert prepared.allow_doc["source"]["sha256"] in step["detail"]


def test_a_conversion_that_differs_between_runs_is_refused(tmp_path):
    receipt(tmp_path, "points", b"{}", fmt="geojson")
    runs = iter([b"one", b"two"])

    def unstable(src, dst):
        dst.write_bytes(next(runs))
        return {"features": 0}
    with pytest.raises(s3.CanonicalRefusal, match="two different files"):
        s3.prepare(PLOT, "points", root=tmp_path, judge=allow(), converter=unstable)


def test_a_conversion_that_fails_is_a_refusal(tmp_path):
    receipt(tmp_path, "outline", b"{}", fmt="geojson")

    def too_large(src, dst):
        raise ValueError("GeoJSON object too complex/large\nsecond line")
    with pytest.raises(s3.CanonicalRefusal, match="the conversion failed: ValueError"):
        s3.prepare(PLOT, "outline", root=tmp_path, judge=allow(), converter=too_large)


def test_a_real_geojson_converts_to_the_same_bytes_twice(tmp_path):
    geopandas = pytest.importorskip("geopandas")
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"name": "a", "n": 1},
         "geometry": {"type": "Point", "coordinates": [-69.8, 44.3]}},
        {"type": "Feature", "properties": {"name": "b", "n": 2},
         "geometry": {"type": "Point", "coordinates": [-68.7, 44.8]}}]}
    receipt(tmp_path, "points", json.dumps(fc).encode(), fmt="geojson")
    prepared = s3.prepare(PLOT, "points", root=tmp_path, judge=allow())
    out = tmp_path / "read_back.parquet"
    out.write_bytes(prepared.data_bytes)
    back = geopandas.read_parquet(out)
    assert len(back) == 2 and back.crs.to_epsg() == 4326
    assert prepared.features == 2


# ── what is refused ──────────────────────────────────────────────────────
def test_a_custom_tier_is_refused_until_withdrawal_is_decided(tmp_path):
    receipt(tmp_path, "counts", b"parquet bytes")
    tiers = [{"semantic_type": "relational_hub", "tier": "custom", "ancestor": "x"}]
    with pytest.raises(s3.CanonicalRefusal, match="custom tier"):
        s3.prepare(PLOT, "counts", root=tmp_path, judge=allow(tiers=tiers))


def test_a_csv_is_refused_by_name(tmp_path):
    receipt(tmp_path, "stack", b"a,b\n1,2\n", fmt="csv")
    with pytest.raises(s3.CanonicalRefusal, match="its data is csv"):
        s3.prepare(PLOT, "stack", root=tmp_path, judge=allow())


def test_data_outside_the_plot_is_refused(tmp_path):
    (tmp_path / "garden" / "reference").mkdir(parents=True)
    (tmp_path / "garden" / "reference" / "listing.parquet").write_bytes(b"x")
    receipt(tmp_path, "counts", b"x", path="plots/demo/../../garden/reference/listing.parquet")
    with pytest.raises(s3.CanonicalRefusal, match="not in plots/demo/.data"):
        s3.prepare(PLOT, "counts", root=tmp_path, judge=allow())


def test_secondary_files_are_refused_rather_than_left_behind(tmp_path):
    receipt(tmp_path, "counts", b"x", secondary={"summary": "plots/demo/.data/s.csv"})
    with pytest.raises(s3.CanonicalRefusal, match="secondary"):
        s3.prepare(PLOT, "counts", root=tmp_path, judge=allow())


@pytest.mark.parametrize("artifact", ["../counts", "a/b", "", ".hidden"])
def test_only_a_receipt_by_its_own_name(tmp_path, artifact):
    receipt(tmp_path, "counts", b"x")
    with pytest.raises(s3.CanonicalRefusal):
        s3.prepare(PLOT, artifact, root=tmp_path, judge=allow())


def test_a_missing_receipt_is_refused(tmp_path):
    receipt(tmp_path, "counts", b"x")
    with pytest.raises(s3.CanonicalRefusal, match="no receipt named"):
        s3.prepare(PLOT, "maine_e911", root=tmp_path, judge=allow())


@pytest.mark.parametrize("plot", ["maine", "michigan/delton"])
def test_plot_names_that_are_plots(plot):
    assert s3.validate_plot(plot) == plot


@pytest.mark.parametrize("plot", ["", "../maine", "Maine", "maine/"])
def test_plot_names_that_are_not(plot):
    with pytest.raises(s3.CanonicalRefusal):
        s3.validate_plot(plot)


# ── the command's own refusals ───────────────────────────────────────────
def _args(**kw):
    base = dict(plot="maine", artifact=None, all=False, write=False, by=None, reason=None)
    return argparse.Namespace(**dict(base, **kw))


@pytest.mark.parametrize("kw", [
    dict(),
    dict(artifact="x", all=True),
    dict(all=True, write=True),
    dict(artifact="x", write=True, by="Kalli"),
    dict(artifact="x", write=True, reason="why"),
])
def test_the_command_refuses_what_it_should_not_try(kw):
    from canopy.cli import canonical
    assert canonical.run(_args(**kw)) == 2


def test_the_dry_run_reads_every_receipt_through_a_surprise(tmp_path, capsys):
    import types
    from canopy.cli import canonical

    def prepare(plot, artifact, *, root):
        if artifact == "b":
            raise RuntimeError("a surprise")
        raise s3.CanonicalRefusal("withheld for the test", "nothing")
    fake = types.SimpleNamespace(list_receipts=lambda root, plot: ["a", "b", "c"],
                                 prepare=prepare, CanonicalRefusal=s3.CanonicalRefusal)
    assert canonical._dry_run_all(fake, tmp_path, PLOT) == 1
    out = capsys.readouterr().out
    assert "b  could not be judged: RuntimeError: a surprise" in out
    assert "0 of 3 may leave; 2 withheld; 1 could not be judged" in out


def test_a_write_without_its_environment_is_refused(monkeypatch):
    from canopy.cli import canonical
    monkeypatch.delenv(s3.BUCKET_ENV, raising=False)
    monkeypatch.delenv(s3.DOMAIN_ENV, raising=False)
    assert canonical.run(_args(artifact="x", write=True, by="Kalli", reason="why")) == 2
