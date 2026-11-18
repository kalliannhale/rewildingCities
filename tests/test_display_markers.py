"""
tests/test_display_markers.py ~ an outline drawn as markers, and ROUND-2 (zip 9b1)

the places map draws every level but the towns as points, from a canonical
copy of each outline drawn as one point on each place's own surface (D-377),
named `markers` under the outline's version and recorded `marked`. a polygon
copy names any shape its rounding leaves invalid, by id, in its `rounded`
record, and is not refused for it: the door refuses to send an invalid shape
(D-368), and the copy's dry run is where one is first seen (ROUND-2, D-379).
the bucket is test_display_copy.py's fake; the real drawing is skipped where
geopandas is absent. ~
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from canopy.aws import display, s3

_spec = importlib.util.spec_from_file_location(
    "_display_fakes", Path(__file__).with_name("test_display_copy.py"))
dc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dc)


def test_an_outline_alone_is_drawn_as_markers_under_its_own_name():
    client = dc.FakeS3()
    dc.canonical(client)
    asked = {}

    def draw(data, *, tolerance_m, id_field, markers=False):
        asked["markers"] = markers
        kind = "markers" if markers else "polygons"
        body = b'{"type": "FeatureCollection", "features": []}'
        return {"bytes": body, "kind": kind, "name": display.display_name(kind, tolerance_m),
                "steps": [{"step": "marked", "count": 2, "detail": "stand-in"},
                          {"step": "rounded", "count": 2, "detail": "6 places"},
                          {"step": "format_changed", "count": 2, "detail": "to GeoJSON"}],
                "stats": {"feature_count": 2, "geometry_type": "Point", "bbox": [0, 0, 1, 1],
                          "vertex_count": 2, "vertices_before": 10, "size_bytes": len(body),
                          "attribute_fields": ["code"], "source_crs": "EPSG:4269"}}
    p = dc.prepare(client, drawer=draw, markers=True)
    assert asked["markers"] is True and p.name == "markers"
    assert p.keys["geojson"].endswith("/display/markers.geojson")
    assert p.envelope["provenance"][-1]["params"]["markers"] is True


def test_a_copy_without_markers_asks_the_drawer_nothing_new():
    client = dc.FakeS3()
    dc.canonical(client)
    p = dc.prepare(client)                # the stand-in drawer takes no markers argument
    assert p.name == "web_25m"


def _parquet(tmp_path, frame) -> bytes:
    path = tmp_path / "v.parquet"
    frame.to_parquet(path, index=False)
    return path.read_bytes()


def test_real_markers_stand_inside_their_places(tmp_path):
    geopandas = pytest.importorskip("geopandas")
    shapely = pytest.importorskip("shapely")
    frame = geopandas.GeoDataFrame(
        {"authority": ["a", "a"], "code": ["1", "2"]},
        geometry=[shapely.box(-70.0, 44.0, -69.9, 44.1), shapely.box(-69.9, 44.0, -69.8, 44.1)],
        crs="EPSG:4269")
    drawn = display.draw(_parquet(tmp_path, frame), id_field="code", markers=True)
    assert drawn["name"] == "markers" and drawn["kind"] == "markers"
    assert [s["step"] for s in drawn["steps"]][0] == "marked"
    fc = json.loads(drawn["bytes"])
    for f, box in zip(fc["features"], frame.geometry):
        assert box.contains(shapely.Point(f["geometry"]["coordinates"]))


def test_real_points_are_not_drawn_as_markers(tmp_path):
    geopandas = pytest.importorskip("geopandas")
    shapely = pytest.importorskip("shapely")
    frame = geopandas.GeoDataFrame({"code": ["1"]}, geometry=[shapely.Point(-70, 44)],
                                   crs="EPSG:4269")
    with pytest.raises(s3.CanonicalRefusal, match="outline of polygons"):
        display.draw(_parquet(tmp_path, frame), markers=True)


def test_real_polygons_say_whether_every_shape_is_valid_after_rounding(tmp_path):
    geopandas = pytest.importorskip("geopandas")
    shapely = pytest.importorskip("shapely")
    frame = geopandas.GeoDataFrame(
        {"code": ["1", "2"]},
        geometry=[shapely.box(-70.0, 44.0, -69.9, 44.1), shapely.box(-69.9, 44.0, -69.8, 44.1)],
        crs="EPSG:4269")
    drawn = display.draw(_parquet(tmp_path, frame), id_field="code")
    rounded = [s for s in drawn["steps"] if s["step"] == "rounded"][0]
    assert "every shape valid after rounding" in rounded["detail"]
