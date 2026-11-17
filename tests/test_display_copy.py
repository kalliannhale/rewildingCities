"""
tests/test_display_copy.py  |  rewildingCities

Contract 2, section 4: a display copy is drawn from one canonical version, read
back from the bucket by its sha256, lives under that version, records every
change it made, and is never a second truth. The bucket is a fake that keeps
the overwrite lock (D-309). Most tests draw with a stand-in, so the rules are
held where geopandas is absent; the last tests draw real geometry and are
skipped without it.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from canopy.aws import display, s3

PLOT = "demo"
HARVEST = "outline_towns_outline"


class FakeError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class FakeS3:
    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.puts: list[dict] = []

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise FakeError("404")
        return {}

    def get_object(self, Bucket, Key):
        if Key not in self.objects:
            raise FakeError("NoSuchKey")
        return {"Body": io.BytesIO(self.objects[Key]), "ETag": '"e"'}

    def put_object(self, Bucket, Key, Body, **kw):
        self.puts.append(dict(kw, Key=Key))
        if "/versions/" in Key and kw.get("IfNoneMatch") != "*":
            raise FakeError("AccessDenied")
        if kw.get("IfNoneMatch") == "*" and Key in self.objects:
            raise FakeError("PreconditionFailed")
        self.objects[Key] = bytes(Body)
        return {}

    def __getattr__(self, name):
        if "delete" in name:
            raise AssertionError(f"a display copy asked the bucket to {name}")
        raise AttributeError(name)


RECEIPT = {
    "data": {"path": "plots/demo/.data/outline.geojson", "format": "geojson", "secondary": {}},
    "metadata": {"semantic_type": "place_outline", "data_category": "vector",
                 "crs": "EPSG:4269", "id_field": "code", "total_area_m2": 1.0,
                 "geometry_type_native": "MULTIPOLYGON",
                 "row_context_notes": ["census_tribal_area"],
                 "lineage": {"kind": "preparation", "method": "$methods/x"}},
    "provenance": [{"primitive": "build_place_outlines", "version": "1.0.0",
                    "timestamp": "2026-11-11T11:17:57+00:00", "params": {}, "inputs": [],
                    "duration_seconds": 1.0, "lineage_branch": None,
                    "publication": [{"step": "clipped", "detail": "water", "count": 5,
                                     "by": "build_place_outlines",
                                     "at": "2026-11-11T11:17:57+00:00"}]}],
    "warnings": [{"level": "info", "primitive": "x", "message": "a warning"}],
}


def canonical(client, data=b"PAR1 towns", data_name="data.parquet", receipt=None):
    """a version already in the fake bucket, with its pointer."""
    sha = s3.sha256_of(data)
    prefix = s3.version_prefix(PLOT, HARVEST, sha)
    client.objects[f"{prefix}/{data_name}"] = data
    client.objects[f"{prefix}/envelope.json"] = json.dumps(receipt or RECEIPT).encode()
    client.objects[s3.pointer_key(PLOT, HARVEST)] = json.dumps(
        {"sha256": sha, "allow": "a" * 64, "data": data_name}).encode()
    return sha


def drawer(kind="polygons", body=b'{"type": "FeatureCollection", "features": []}'):
    def draw(data, *, tolerance_m, id_field):
        name = display.display_name(kind, tolerance_m)
        steps = [{"step": "simplified", "count": 0 if kind == "points" else 2,
                  "detail": f"stand-in at {tolerance_m} m"},
                 {"step": "rounded", "count": 2, "detail": "6 places"},
                 {"step": "format_changed", "count": 2, "detail": "to GeoJSON"}]
        stats = {"feature_count": 2, "geometry_type": "Polygon", "bbox": [0, 0, 1, 1],
                 "vertex_count": 8, "vertices_before": 10, "size_bytes": len(body),
                 "attribute_fields": ["code"], "source_crs": "EPSG:4269"}
        return {"bytes": body, "steps": steps, "kind": kind, "name": name, "stats": stats}
    return draw


def allow(envelope, *, plot, plot_dir):
    return {"decision": "allow", "record": {"tiers": [
        {"semantic_type": "place_outline", "tier": "public", "ancestor": "x"}]}}


def prepare(client, **kw):
    kw.setdefault("drawer", drawer())
    return s3.prepare_display(PLOT, HARVEST, client=client, bucket="b", domain="d.example",
                              root=Path("/tmp"), judge=kw.pop("judge", allow),
                              validate=lambda e: [], **kw)


# ── where a copy comes from ──────────────────────────────────────────────
def test_a_copy_needs_a_canonical_version_first():
    with pytest.raises(s3.CanonicalRefusal, match="no canonical version"):
        prepare(FakeS3())


def test_a_document_has_no_display_copy():
    client = FakeS3()
    canonical(client, data=b"{}", data_name="data.json")
    with pytest.raises(s3.CanonicalRefusal, match="document"):
        prepare(client)


def test_bytes_that_do_not_hash_to_their_version_are_refused():
    client = FakeS3()
    sha = canonical(client)
    client.objects[f"{s3.version_prefix(PLOT, HARVEST, sha)}/data.parquet"] = b"other bytes"
    with pytest.raises(s3.CanonicalRefusal, match="do not hash"):
        prepare(client)


def test_the_drawing_is_given_the_versions_own_bytes():
    client = FakeS3()
    canonical(client, data=b"PAR1 towns")
    seen = {}

    def spy(data, *, tolerance_m, id_field):
        seen.update(data=data, tolerance_m=tolerance_m, id_field=id_field)
        return drawer()(data, tolerance_m=tolerance_m, id_field=id_field)
    prepare(client, drawer=spy, tolerance_m=40)
    assert seen == {"data": b"PAR1 towns", "tolerance_m": 40, "id_field": "code"}


def test_a_drawing_that_fails_is_a_refusal_never_a_crash():
    client = FakeS3()
    canonical(client)

    def broken(data, *, tolerance_m, id_field):
        raise TypeError("Object of type Timestamp is not JSON serializable")
    with pytest.raises(s3.CanonicalRefusal, match="drawing the copy failed: TypeError"):
        prepare(client, drawer=broken)


# ── what the copy's envelope says ────────────────────────────────────────
def test_the_envelope_says_what_it_came_from_and_every_change():
    client = FakeS3()
    sha = canonical(client)
    p = prepare(client)
    env = p.envelope
    assert env["data"] == {"path": p.keys["geojson"], "format": "geojson", "secondary": {}}
    assert env["metadata"]["derived_from"] == sha and env["metadata"]["allow"] == "a" * 64
    assert env["metadata"]["crs"] == "EPSG:4326"
    assert "total_area_m2" not in env["metadata"]
    own = env["provenance"][-1]
    assert own["primitive"] == display.PRIMITIVE and own["lineage_branch"] is None
    assert own["inputs"][0]["hash"] == {"value": sha, "method": "full_file", "algorithm": "sha256"}
    assert [r["step"] for r in own["publication"]] == ["simplified", "rounded", "format_changed"]
    assert all(r["by"] == display.PRIMITIVE and r["at"] == own["timestamp"]
               for r in own["publication"])


def test_the_versions_lineage_notes_and_chain_travel_with_the_copy():
    client = FakeS3()
    canonical(client)
    env = prepare(client).envelope
    assert env["metadata"]["lineage"] == RECEIPT["metadata"]["lineage"]
    assert env["metadata"]["row_context_notes"] == ["census_tribal_area"]
    assert env["provenance"][0]["primitive"] == "build_place_outlines"
    assert env["provenance"][0]["lineage_branch"] == "version"
    assert env["provenance"][0]["publication"][0]["step"] == "clipped"
    assert env["warnings"] == RECEIPT["warnings"]


def test_a_points_copy_says_it_simplified_nothing():
    client = FakeS3()
    canonical(client)
    p = prepare(client, drawer=drawer(kind="points"))
    simplified = p.envelope["provenance"][-1]["publication"][0]
    assert p.name == "web" and simplified["step"] == "simplified" and simplified["count"] == 0


def test_the_gate_judges_the_copy_and_a_custom_tier_is_refused():
    client = FakeS3()
    canonical(client)

    def custom(envelope, *, plot, plot_dir):
        return {"decision": "allow", "record": {"tiers": [
            {"semantic_type": "relational_hub", "tier": "custom", "ancestor": "x"}]}}
    with pytest.raises(s3.CanonicalRefusal, match="custom tier"):
        prepare(client, judge=custom)


def test_an_envelope_the_schema_refuses_is_refused():
    client = FakeS3()
    canonical(client)
    with pytest.raises(s3.CanonicalRefusal, match="envelope schema"):
        s3.prepare_display(PLOT, HARVEST, client=client, bucket="b", domain="d.example",
                           root=Path("/tmp"), judge=allow, drawer=drawer(),
                           validate=lambda e: ["metadata: 'crs' is required"])


# ── writing it ───────────────────────────────────────────────────────────
def test_a_copy_lives_under_its_version_named_by_its_tolerance():
    client = FakeS3()
    sha = canonical(client)
    p = prepare(client, tolerance_m=25)
    assert p.keys["geojson"] == f"harvests/{PLOT}/{HARVEST}/versions/{sha}/display/web_25m.geojson"
    assert p.keys["envelope"].endswith("/display/web_25m.envelope.json")


def test_the_envelope_goes_first_and_the_geojson_last_each_once():
    client = FakeS3()
    canonical(client)
    result = s3.write_display(prepare(client), client=client, bucket="b")
    assert result["copy"] == "new"
    assert [k.rsplit("/", 1)[-1] for k in result["written"]] == [
        "web_25m.envelope.json", "web_25m.geojson"]
    assert all(put.get("IfNoneMatch") == "*" for put in client.puts)


def test_the_same_copy_twice_writes_nothing():
    client = FakeS3()
    canonical(client)
    s3.write_display(prepare(client), client=client, bucket="b")
    before = len(client.puts)
    again = s3.write_display(prepare(client), client=client, bucket="b")
    assert again == dict(again, copy="exists", written=[]) and len(client.puts) == before


def test_other_bytes_under_the_same_name_are_refused_never_replaced():
    client = FakeS3()
    canonical(client)
    first = prepare(client)
    s3.write_display(first, client=client, bucket="b")
    other = prepare(client, drawer=drawer(body=b'{"type": "FeatureCollection", "x": 1}'))
    with pytest.raises(s3.CanonicalRefusal, match="other bytes"):
        s3.write_display(other, client=client, bucket="b")
    assert client.objects[first.keys["geojson"]] == first.body


def test_a_tolerance_is_whole_meters_above_zero():
    for bad in (0, -5, 2.5, True):
        with pytest.raises(s3.CanonicalRefusal):
            display.display_name("polygons", bad)
    assert display.display_name("points", 0) == "web"


def test_drawing_never_removes_anything():
    source = Path(display.__file__).read_text().lower()
    assert "delete" not in source


# ── real geometry, where geopandas is installed ──────────────────────────
def _parquet(tmp_path, frame) -> bytes:
    path = tmp_path / "version.parquet"
    frame.to_parquet(path, index=False)
    return path.read_bytes()


def _towns(geopandas, shapely):
    """two towns sharing one wiggly edge, in NAD83 as Maine's outlines are.
    the wiggle is about 1.6 m, well inside a 25 m tolerance."""
    edge = [(-69.80 + (0.00002 if i % 2 else 0.0), 44.30 + i * 0.0005) for i in range(41)]
    west = shapely.Polygon([(-69.85, 44.30)] + edge + [(-69.85, 44.32)])
    east = shapely.Polygon(edge + [(-69.75, 44.32), (-69.75, 44.30)])
    return geopandas.GeoDataFrame({"code": ["2300100001", "2300100002"],
                                   "name": ["West", "East"]},
                                  geometry=[west, east], crs="EPSG:4269")


def test_real_towns_keep_one_shared_edge(tmp_path):
    geopandas = pytest.importorskip("geopandas")
    shapely = pytest.importorskip("shapely")
    towns = _towns(geopandas, shapely)
    numpy = pytest.importorskip("numpy")
    assert shapely.coverage_is_valid(numpy.asarray(towns.geometry))
    drawn = display.draw(_parquet(tmp_path, towns), tolerance_m=25, id_field="code")
    out = geopandas.read_file(io.BytesIO(drawn["bytes"]))
    assert drawn["name"] == "web_25m" and len(out) == 2 and out.crs.to_epsg() == 4326
    assert drawn["stats"]["vertex_count"] < drawn["stats"]["vertices_before"]
    assert shapely.coverage_is_valid(numpy.asarray(out.geometry))
    steps = [s["step"] for s in drawn["steps"]]
    assert steps == ["simplified", "rounded", "format_changed"]
    assert "EPSG:4269" in drawn["steps"][-1]["detail"]


def test_real_towns_draw_the_same_bytes_twice(tmp_path):
    geopandas = pytest.importorskip("geopandas")
    shapely = pytest.importorskip("shapely")
    data = _parquet(tmp_path, _towns(geopandas, shapely))
    assert display.draw(data, tolerance_m=25)["bytes"] == display.draw(data, tolerance_m=25)["bytes"]


def test_overlapping_towns_are_refused(tmp_path):
    geopandas = pytest.importorskip("geopandas")
    shapely = pytest.importorskip("shapely")
    a = shapely.box(-69.85, 44.30, -69.79, 44.32)
    b = shapely.box(-69.80, 44.30, -69.75, 44.32)
    frame = geopandas.GeoDataFrame({"code": ["1", "2"]}, geometry=[a, b], crs="EPSG:4269")
    with pytest.raises(s3.CanonicalRefusal, match="not a valid coverage"):
        display.draw(_parquet(tmp_path, frame), tolerance_m=25)


def test_real_points_simplify_nothing(tmp_path):
    geopandas = pytest.importorskip("geopandas")
    shapely = pytest.importorskip("shapely")
    frame = geopandas.GeoDataFrame({"id": ["a", "b"]},
                                   geometry=[shapely.Point(-69.8123456789, 44.3),
                                             shapely.Point(-68.7, 44.8)], crs="EPSG:4326")
    drawn = display.draw(_parquet(tmp_path, frame))
    out = json.loads(drawn["bytes"])
    assert drawn["name"] == "web" and drawn["steps"][0]["count"] == 0
    assert out["features"][0]["geometry"]["coordinates"][0] == -69.812346
    assert "no reprojection" in drawn["steps"][-1]["detail"]



def test_real_dates_are_written_as_text_and_named(tmp_path):
    geopandas = pytest.importorskip("geopandas")
    shapely = pytest.importorskip("shapely")
    pandas = pytest.importorskip("pandas")
    frame = geopandas.GeoDataFrame(
        {"id": ["a", "b"],
         "record_date": pandas.to_datetime(["2026-11-14", None])},
        geometry=[shapely.Point(-69.8, 44.3), shapely.Point(-68.7, 44.8)], crs="EPSG:4326")
    drawn = display.draw(_parquet(tmp_path, frame))
    out = json.loads(drawn["bytes"])
    assert out["features"][0]["properties"]["record_date"].startswith("2026-11-14")
    assert out["features"][1]["properties"]["record_date"] is None
    assert "ISO 8601" in drawn["steps"][-1]["detail"]
    assert "record_date" in drawn["steps"][-1]["detail"]

# ── the command's own refusals ───────────────────────────────────────────
def _args(**kw):
    import argparse
    base = dict(plot="maine", artifact=None, all=False, write=False, by=None, reason=None,
                display=False, tolerance=None)
    return argparse.Namespace(**dict(base, **kw))


@pytest.mark.parametrize("kw", [
    dict(all=True, display=True),
    dict(artifact="x", tolerance=25),
])
def test_the_command_refuses_a_display_asked_wrongly(kw):
    from canopy.cli import canonical
    assert canonical.run(_args(**kw)) == 2


def test_a_display_needs_its_environment_even_as_a_dry_run(monkeypatch):
    from canopy.cli import canonical
    monkeypatch.delenv(s3.BUCKET_ENV, raising=False)
    monkeypatch.delenv(s3.DOMAIN_ENV, raising=False)
    assert canonical.run(_args(artifact="x", display=True)) == 2
