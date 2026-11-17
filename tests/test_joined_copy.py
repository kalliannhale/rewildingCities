"""
tests/test_joined_copy.py ~ a table drawn on an outline (D-331, zip 8b)

the joined copy has two parents and says so: it lives under the table's
version, is named for the outline's, inherits both chains under the branches
`table` and `outline`, names the outline whole in joined_to (which the gate
reads for rule 10), and carries the notes its drawn places carry. a local dry
run draws from the bytes a write would send and can never be written.

the bucket is a fake, the drawing a stand-in, so these run without geopandas;
the real drawing has its own tests at the end, skipped without it. ~
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
import yaml

from canopy.aws import display, s3
from canopy.expose.gate import lineage_datasets

ROOT = Path(__file__).resolve().parents[1]
PLOT, TABLE, OUTLINE = "demo", "broadband_standings", "outline_counties_outline"


class FakeError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class FakeS3:
    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.puts: list[str] = []

    def get_object(self, Bucket, Key):
        if Key not in self.objects:
            raise FakeError("NoSuchKey")
        return {"Body": io.BytesIO(self.objects[Key]), "ETag": '"e"'}

    def put_object(self, Bucket, Key, Body, **kw):
        if "/versions/" in Key and kw.get("IfNoneMatch") != "*":
            raise FakeError("AccessDenied")
        if Key in self.objects:
            raise FakeError("PreconditionFailed")
        self.puts.append(Key)
        self.objects[Key] = bytes(Body)
        return {"ETag": '"e"'}

    def __getattr__(self, name):
        if "delete" in name:
            raise AssertionError(f"asked the bucket to {name}")
        raise AttributeError(name)


def _lineage(datasets, kind="preparation"):
    return {"kind": kind, "run": "r", "method": "$methods/m",
            "data_resolution": {"datasets_available": datasets}}


TABLE_RECEIPT = {
    "data": {"path": "plots/demo/.data/t.parquet", "format": "parquet", "secondary": {}},
    "metadata": {"semantic_type": "indicator_standings", "data_category": "tabular", "crs": None,
                 "row_count": 6, "variables": ["unit_code"], "id_field": "measurement_id",
                 "lineage": _lineage(["acs_us_county_2024"], "experiment"),
                 "reference_population": {"per_indicator": {"cii_broadband": {"n": 3144}}}},
    "provenance": [{"primitive": "standardize_indicator", "version": "1.0.0",
                    "timestamp": "2026-11-01T00:00:00+00:00", "params": {}, "inputs": [
                        {"name": "values", "semantic_type": "indicator_values", "path": "x",
                         "hash": {"value": None, "method": "skipped"}}],
                    "duration_seconds": 1.0, "lineage_branch": None}],
    "warnings": [{"level": "info", "primitive": "t", "message": "a table warning"}],
}
OUTLINE_RECEIPT = {
    "data": {"path": "plots/demo/.data/o.geojson", "format": "geojson", "secondary": {}},
    "metadata": {"semantic_type": "place_outline", "data_category": "vector", "crs": "EPSG:4269",
                 "id_field": "code", "level": "county", "authority": "us_census_geoid",
                 "spatial_unit": "county", "lineage": _lineage(["faces_2024_me"]),
                 "row_context_notes": ["contains_census_tribal_area"]},
    "provenance": [{"primitive": "build_place_outlines", "version": "1.0.0",
                    "timestamp": "2026-11-01T00:00:00+00:00", "params": {}, "inputs": [
                        {"name": "places", "semantic_type": "place_table", "path": "y",
                         "hash": {"value": None, "method": "skipped"}}],
                    "duration_seconds": 1.0, "lineage_branch": None}],
    "warnings": [{"level": "info", "primitive": "o", "message": "an outline warning"}],
}


def version(client, harvest, data, receipt, allow="a" * 64):
    sha = s3.sha256_of(data)
    prefix = s3.version_prefix(PLOT, harvest, sha)
    client.objects[f"{prefix}/data.parquet"] = data
    client.objects[f"{prefix}/envelope.json"] = json.dumps(receipt).encode()
    client.objects[s3.pointer_key(PLOT, harvest)] = json.dumps(
        {"sha256": sha, "allow": allow, "data": "data.parquet"}).encode()
    return sha


def stand_in(row_notes=("contains_census_tribal_area",)):
    seen = {}

    def draw(table_bytes, outline_bytes, *, outline_harvest, outline_sha256, level, widths,
             markers, tolerance_m, id_field):
        seen.update(table=table_bytes, outline=outline_bytes, level=level, markers=markers,
                    widths=widths)
        name = display.joined_name(outline_harvest, outline_sha256, markers=markers,
                                   tolerance_m=tolerance_m)
        return {"bytes": b'{"type": "FeatureCollection", "features": []}',
                "steps": [{"step": "joined", "count": 16, "detail": "stand-in"}],
                "kind": "markers" if markers else "polygons", "name": name,
                "stats": {"feature_count": 16, "geometry_type": "Point" if markers else "Polygon",
                          "bbox": [-71, 43, -67, 47], "vertex_count": 16, "vertices_before": 99,
                          "size_bytes": 40, "attribute_fields": ["code"], "source_crs": "EPSG:4269"},
                "join": {"counts": {"places": 16, "places_without_row": 0, "rows_in_outline": 16,
                                    "rows_outside_outline": 3128, "rows_other_level": 0,
                                    "rows_other_authority": 0},
                         "indicators": ["cii_broadband"],
                         "columns": {"cii_broadband": ["cii_broadband__percentile"]},
                         "authority": "us_census_geoid", "level": level,
                         "row_notes": list(row_notes)}}
    draw.seen = seen
    return draw


def allow(envelope, *, plot, plot_dir):
    return {"decision": "allow", "record": {"tiers": []}}


def joined(client, **kw):
    kw.setdefault("drawer", stand_in())
    return s3.prepare_display(PLOT, TABLE, client=client, bucket="b", domain="d.example",
                              root=ROOT, judge=kw.pop("judge", allow), validate=lambda e: [],
                              join=OUTLINE, **kw)


def both(client):
    t = version(client, TABLE, b"PAR1 table", TABLE_RECEIPT, allow="1" * 64)
    o = version(client, OUTLINE, b"PAR1 outline", OUTLINE_RECEIPT, allow="2" * 64)
    return t, o


# ── where it lives and what it is called ─────────────────────────────────
def test_the_copy_lives_under_the_tables_version_named_for_the_outlines():
    client = FakeS3()
    t, o = both(client)
    p = joined(client)
    assert p.keys["geojson"] == (f"{s3.version_prefix(PLOT, TABLE, t)}/display/"
                                 f"{OUTLINE}_{o[:12]}_web_25m.geojson")
    assert p.joined_to == {"harvest": OUTLINE, "sha256": o, "allow": "2" * 64}


def test_markers_are_another_copy_with_another_name():
    client = FakeS3()
    _, o = both(client)
    p = joined(client, markers=True)
    assert p.name == f"{OUTLINE}_{o[:12]}_markers"
    assert p.envelope["metadata"]["display_kind"] == "markers"


def test_the_drawing_is_given_both_versions_own_bytes():
    client, draw = FakeS3(), stand_in()
    both(client)
    joined(client, drawer=draw)
    assert draw.seen["table"] == b"PAR1 table" and draw.seen["outline"] == b"PAR1 outline"
    assert draw.seen["level"] == "county" and draw.seen["widths"]["us_census_geoid"]["county"] == 5


# ── the envelope names both parents ──────────────────────────────────────
def test_the_envelope_names_both_parents_and_both_chains():
    client = FakeS3()
    t, o = both(client)
    env = joined(client).envelope
    meta = env["metadata"]
    assert meta["derived_from"] == t and meta["allow"] == "1" * 64
    assert meta["joined_to"]["sha256"] == o and meta["joined_to"]["allow"] == "2" * 64
    assert meta["joined_to"]["lineage"]["data_resolution"]["datasets_available"] == ["faces_2024_me"]
    branches = [e.get("lineage_branch") for e in env["provenance"]]
    assert branches == ["table", "outline", None]
    own = env["provenance"][-1]
    assert [i["name"] for i in own["inputs"]] == ["table", "outline"]
    assert [i["hash"]["value"] for i in own["inputs"]] == [t, o]
    assert {w["message"] for w in env["warnings"]} == {"a table warning", "an outline warning"}


def test_a_copy_of_places_drops_the_tables_own_row_description():
    client = FakeS3()
    both(client)
    meta = joined(client).envelope["metadata"]
    assert "row_count" not in meta and "variables" not in meta
    assert meta["id_field"] == "code" and meta["data_category"] == "vector"
    assert meta["reference_population"]["per_indicator"]["cii_broadband"]["n"] == 3144


def test_the_notes_are_those_of_the_drawn_places():
    client = FakeS3()
    both(client)
    meta = joined(client).envelope["metadata"]
    assert meta["row_context_notes"] == ["contains_census_tribal_area"]
    assert meta["context_notes"] == ["contains_census_tribal_area"]
    client = FakeS3()
    both(client)
    meta = joined(client, drawer=stand_in(row_notes=())).envelope["metadata"]
    assert meta["row_context_notes"] == [] and meta["context_notes"] == []


def test_the_gate_reads_the_outlines_datasets_for_rule_10():
    client = FakeS3()
    both(client)
    env = joined(client).envelope
    datasets = {"acs_us_county_2024": {}, "faces_2024_me": {}}
    assert lineage_datasets(env, datasets) == ["acs_us_county_2024", "faces_2024_me"]


def test_an_envelope_with_no_second_parent_is_read_as_before():
    env = {"metadata": {"lineage": _lineage(["a"])}, "provenance": []}
    assert lineage_datasets(env, {"a": {}, "b": {}}) == ["a"]


# ── refusals ─────────────────────────────────────────────────────────────
def test_only_a_table_is_joined():
    client = FakeS3()
    version(client, TABLE, b"PAR1 table", OUTLINE_RECEIPT)
    version(client, OUTLINE, b"PAR1 outline", OUTLINE_RECEIPT)
    with pytest.raises(s3.CanonicalRefusal, match="draws a table on an outline"):
        joined(client)


def test_only_a_place_outline_is_joined_onto():
    client = FakeS3()
    version(client, TABLE, b"PAR1 table", TABLE_RECEIPT)
    plain = json.loads(json.dumps(OUTLINE_RECEIPT))
    plain["metadata"].pop("level")
    version(client, OUTLINE, b"PAR1 outline", plain)
    with pytest.raises(s3.CanonicalRefusal, match="not a place outline"):
        joined(client)


def test_an_outline_never_written_says_so():
    client = FakeS3()
    version(client, TABLE, b"PAR1 table", TABLE_RECEIPT)
    with pytest.raises(s3.CanonicalRefusal, match="no canonical version"):
        joined(client)


def test_markers_need_an_outline():
    with pytest.raises(s3.CanonicalRefusal, match="joined onto an outline"):
        s3.prepare_display(PLOT, TABLE, client=FakeS3(), bucket="b", domain="d", root=ROOT,
                           judge=allow, validate=lambda e: [], markers=True)


def test_a_gate_refusal_refuses_the_copy():
    client = FakeS3()
    both(client)
    with pytest.raises(s3.CanonicalRefusal, match="withheld"):
        joined(client, judge=lambda e, **k: {"decision": "refuse", "refusals": [{"rule": 10}]})


def test_the_joined_copy_is_written_like_any_copy():
    client = FakeS3()
    both(client)
    p = joined(client)
    result = s3.write_display(p, client=client, bucket="b")
    assert result["written"] == [p.keys["envelope"], p.keys["geojson"]]


# ── a local dry run ──────────────────────────────────────────────────────
def _garden(tmp_path):
    plot = tmp_path / "plots" / PLOT
    for sub in (".data", ".envelopes", "preparations"):
        (plot / sub).mkdir(parents=True, exist_ok=True)
    auth = tmp_path / "seeds" / "authorities"
    auth.mkdir(parents=True)
    auth.joinpath("authorities.yml").write_text((ROOT / "seeds" / "authorities" /
                                                 "authorities.yml").read_text())
    for name, receipt, body in ((TABLE, TABLE_RECEIPT, b"PAR1 table"),
                                (OUTLINE, OUTLINE_RECEIPT, b"PAR1 outline")):
        r = json.loads(json.dumps(receipt))
        r["data"] = {"path": f"plots/{PLOT}/.data/{name}.parquet", "format": "parquet",
                     "secondary": {}}
        (plot / ".data" / f"{name}.parquet").write_bytes(body)
        (plot / ".envelopes" / f"{name}.envelope.json").write_text(json.dumps(r))
    return tmp_path


def _canonical_allow(envelope, *, plot, plot_dir):
    return {"decision": "allow", "record": {"tiers": [], "publication_steps": []}}


def test_a_local_dry_run_needs_no_bucket_and_draws_the_bytes_a_write_would_send(tmp_path):
    root = _garden(tmp_path)
    draw = stand_in()
    p = s3.prepare_display(PLOT, TABLE, client=None, bucket=None, domain=None, root=root,
                           judge=_canonical_allow, validate=lambda e: [], join=OUTLINE,
                           drawer=draw, local=True)
    assert p.local and draw.seen["table"] == b"PAR1 table"
    assert p.sha256 == s3.sha256_of(b"PAR1 table")
    assert p.joined_to["sha256"] == s3.sha256_of(b"PAR1 outline")
    assert p.copy_sha256 == s3.sha256_of(p.body)


def test_a_local_copy_can_never_be_written(tmp_path):
    root = _garden(tmp_path)
    p = s3.prepare_display(PLOT, TABLE, client=None, bucket=None, domain=None, root=root,
                           judge=_canonical_allow, validate=lambda e: [], join=OUTLINE,
                           drawer=stand_in(), local=True)
    client = FakeS3()
    with pytest.raises(s3.CanonicalRefusal, match="dry run only"):
        s3.write_display(p, client=client, bucket="b")
    assert client.puts == []


# ── the command ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("argv,said", [
    (["canonical", "maine", "t", "--join", "o"], "go with --display"),
    (["canonical", "maine", "t", "--display", "--markers"], "--markers goes with --join"),
    (["canonical", "maine", "t", "--display", "--join", "o", "--markers", "--tolerance", "5"],
     "no --tolerance"),
    (["canonical", "maine", "t", "--display", "--local", "--write"], "never writes"),
])
def test_the_command_refuses_a_join_asked_wrongly(argv, said):
    import argparse
    from canopy.cli import canonical as cli
    parser = argparse.ArgumentParser()
    cli.register(parser.add_subparsers())
    assert said in cli._asked_wrongly(parser.parse_args(argv))



def test_every_step_a_copy_records_is_in_rule_11s_closed_set():
    """the schema names the publication steps; a copy recording a step it does
    not name is refused by the real validator, which these tests stub (D-348)."""
    import re
    schema = json.loads((ROOT / "seeds" / "schemas" / "provenance.schema.json").read_text())
    allowed = set(schema["properties"]["publication"]["items"]["properties"]["step"]["enum"])
    source = (ROOT / "canopy" / "aws" / "display.py").read_text()
    recorded = set(re.findall(r'"step": "([a-z_]+)"', source))
    assert recorded and recorded <= allowed, sorted(recorded - allowed)

# ── the real drawing, where geopandas is installed ───────────────────────
def _real(tmp_path, *, markers=False):
    geopandas = pytest.importorskip("geopandas")
    shapely = pytest.importorskip("shapely")
    pd = pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    from shapely.geometry import box
    frame = geopandas.GeoDataFrame(
        {"authority": ["us_census_geoid"] * 2, "code": ["23005", "23031"],
         "level": ["county"] * 2, "name": ["Cumberland", "York"],
         "context_note": [None, "contains_census_tribal_area"]},
        geometry=[box(-70.5, 43.6, -70.0, 44.0), box(-70.0, 43.6, -69.5, 44.0)], crs="EPSG:4269")
    opath, tpath = tmp_path / "o.parquet", tmp_path / "t.parquet"
    frame.to_parquet(opath)
    pd.DataFrame({"unit_authority": ["us_census_geoid"] * 2, "unit_code": ["23005", "04013"],
                  "indicator": ["cii_broadband"] * 2, "value": [92.7, 90.1],
                  "percentile": [61.0, 44.0]}).to_parquet(tpath)
    return display.draw_joined(tpath.read_bytes(), opath.read_bytes(), outline_harvest=OUTLINE,
                               outline_sha256="e" * 64, level="county",
                               widths={"us_census_geoid": {"county": 5}}, markers=markers,
                               id_field="code")


def test_real_counties_draw_wide_and_keep_the_unjoined_place(tmp_path):
    drawn = _real(tmp_path)
    fc = json.loads(drawn["bytes"])
    by = {f["properties"]["code"]: f["properties"] for f in fc["features"]}
    assert by["23005"]["cii_broadband__percentile"] == 61.0
    assert by["23031"]["cii_broadband__percentile"] is None and by["23031"]["joined"] is False
    assert drawn["join"]["counts"]["rows_outside_outline"] == 1
    assert drawn["join"]["row_notes"] == ["contains_census_tribal_area"]
    assert [s["step"] for s in drawn["steps"]] == ["simplified", "rounded", "joined", "format_changed"]


def test_real_markers_stand_inside_their_places(tmp_path):
    drawn = _real(tmp_path, markers=True)
    fc = json.loads(drawn["bytes"])
    assert {f["geometry"]["type"] for f in fc["features"]} == {"Point"}
    x = [f["geometry"]["coordinates"][0] for f in fc["features"]]
    assert -70.5 < x[0] < -70.0 and -70.0 < x[1] < -69.5
    assert drawn["steps"][0]["step"] == "marked" and drawn["stats"]["geometry_type"] == "Point"


def test_real_joined_copies_are_the_same_bytes_twice(tmp_path):
    assert _real(tmp_path)["bytes"] == _real(tmp_path)["bytes"]
