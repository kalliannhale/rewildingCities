"""
tests/test_slim_copy.py ~ a lens's copy: its lane's columns alone, sent compressed
(zip 9b2c, D-396, D-397)

the towns language copy weighed 16.2 MB because it carries all 26 of its
table's indicators, and a lens draws one or two. a slim copy keeps only the
named indicators' columns and every place's own fields, says in its joined step
which it left out, and is named by exactly which it holds, so a changed set is
a new name and never new bytes under one (D-322). it is sent as
application/json, which CloudFront compresses; every other copy keeps
application/geo+json, which it does not. the bucket and the drawing are
test_joined_copy.py's fakes, loaded by path; the real drawing is skipped
without geopandas. ~
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from canopy.aws import display, s3

_spec = importlib.util.spec_from_file_location(
    "_joined_fakes", Path(__file__).with_name("test_joined_copy.py"))
jf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(jf)


class TypedS3(jf.FakeS3):
    """the fake bucket, remembering each object's content type."""

    def __init__(self):
        super().__init__()
        self.types: dict[str, str] = {}

    def put_object(self, Bucket, Key, Body, **kw):
        out = super().put_object(Bucket, Key, Body, **kw)
        self.types[Key] = kw.get("ContentType")
        return out


def slim_stand_in():
    full = jf.stand_in()

    def draw(table_bytes, outline_bytes, *, only=None, **kw):
        drawn = full(table_bytes, outline_bytes, **kw)
        drawn["name"] = display.joined_name(kw["outline_harvest"], kw["outline_sha256"],
                                            markers=kw["markers"], tolerance_m=kw["tolerance_m"],
                                            only=only)
        if only:
            drawn["join"].update(only=sorted(only), left_out=["other_indicator"])
        return drawn
    return draw


def test_a_slim_copy_is_named_by_exactly_what_it_holds():
    a = display.joined_name("outline_towns_outline", "e" * 64, tolerance_m=250,
                            only=["limited_english_persons_share", "limited_english_households"])
    b = display.joined_name("outline_towns_outline", "e" * 64, tolerance_m=250,
                            only=["limited_english_households", "limited_english_persons_share"])
    full = display.joined_name("outline_towns_outline", "e" * 64, tolerance_m=250)
    assert a == b and a.startswith(full + "_only_") and len(a) == len(full) + len("_only_") + 8
    assert a != display.joined_name("outline_towns_outline", "e" * 64, tolerance_m=250,
                                    only=["limited_english_households"])


def test_a_slim_copy_records_what_it_keeps_and_is_sent_compressible():
    client = TypedS3()
    jf.both(client)
    p = jf.joined(client, drawer=slim_stand_in(), only=["cii_broadband"])
    own = p.envelope["provenance"][-1]
    assert own["params"]["only"] == ["cii_broadband"]
    assert own["params"]["content_type"] == "application/json"
    assert p.envelope["metadata"]["join"]["only"] == ["cii_broadband"]
    assert p.name.endswith("_only_" + display.only_key(["cii_broadband"]))
    s3.write_display(p, client=client, bucket="b")
    assert client.types[p.keys["geojson"]] == display.COMPRESSED_TYPE


def test_every_other_copy_keeps_its_geojson_type():
    client = TypedS3()
    jf.both(client)
    p = jf.joined(client)
    s3.write_display(p, client=client, bucket="b")
    assert client.types[p.keys["geojson"]] == display.GEOJSON_TYPE
    assert "only" not in p.envelope["metadata"]["join"]


def test_only_goes_with_a_join():
    client = TypedS3()
    jf.both(client)
    with pytest.raises(s3.CanonicalRefusal):
        s3.prepare_display(jf.PLOT, jf.TABLE, client=client, bucket="b", domain="d.example",
                           root=jf.ROOT, judge=jf.allow, validate=lambda e: [],
                           only=["cii_broadband"])


def test_the_command_takes_only_with_a_join():
    import argparse
    from canopy.cli import canonical as cli
    parser = argparse.ArgumentParser()
    cli.register(parser.add_subparsers())
    asked = lambda *argv: cli._asked_wrongly(parser.parse_args(["canonical", *argv]))
    assert asked("maine", "t", "--display", "--only", "a,b")
    assert asked("maine", "t", "--display", "--join", "o", "--only", "a,b") is None
    assert asked("maine", "--refusals", "--only", "a")


def test_real_slim_copy_keeps_only_its_columns(tmp_path):
    geopandas = pytest.importorskip("geopandas")
    pd = pytest.importorskip("pandas")
    pytest.importorskip("shapely")
    pytest.importorskip("pyarrow")
    from shapely.geometry import box
    frame = geopandas.GeoDataFrame(
        {"authority": ["us_census_geoid"] * 2, "code": ["23005", "23031"],
         "level": ["county"] * 2, "name": ["Cumberland", "York"]},
        geometry=[box(-70.5, 43.6, -70.0, 44.0), box(-70.0, 43.6, -69.5, 44.0)], crs="EPSG:4269")
    opath, tpath = tmp_path / "o.parquet", tmp_path / "t.parquet"
    frame.to_parquet(opath)
    pd.DataFrame({"unit_authority": ["us_census_geoid"] * 4,
                  "unit_code": ["23005", "23031", "23005", "23031"],
                  "indicator": ["keep_me"] * 2 + ["leave_me"] * 2,
                  "value": [1.0, 2.0, 3.0, 4.0]}).to_parquet(tpath)
    kw = dict(outline_harvest=jf.OUTLINE, outline_sha256="e" * 64, level="county",
              widths={"us_census_geoid": {"county": 5}}, id_field="code")
    slim = display.draw_joined(tpath.read_bytes(), opath.read_bytes(), only=["keep_me"], **kw)
    props = json.loads(slim["bytes"])["features"][0]["properties"]
    assert "keep_me__value" in props and not any(k.startswith("leave_me") for k in props)
    assert {"authority", "code", "name"} <= set(props)
    assert slim["join"]["indicators"] == ["keep_me"] and slim["join"]["left_out"] == ["leave_me"]
    joined = next(s for s in slim["steps"] if s["step"] == "joined")
    assert "leave_me" in joined["detail"] and "D-396" in joined["detail"]
    with pytest.raises(s3.CanonicalRefusal):
        display.draw_joined(tpath.read_bytes(), opath.read_bytes(), only=["not_here"], **kw)
