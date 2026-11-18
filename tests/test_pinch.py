"""
tests/test_pinch.py ~ a pinch is opened in the copy, never in the outline (COVER-1)

Gray and Windham, and House Districts 113 and 116, each meet at one point
where both places have a hole (removed water) touching their shared border.
every border matches, yet GEOS's coverage check refuses the shape. the copy
moves only those hole vertices OPEN_PINCH_M into their own holes, records it
as `opened`, and simplifies as before; anything else invalid is still refused.
these need shapely and geopandas, so they run where the plot runs. ~
"""

from __future__ import annotations

import io

import pytest

from canopy.aws import display, s3


def _pinch(shapely):
    """two squares in metres sharing the edge x = 1000, each with a triangular
    hole touching that edge at (1000, 500): the shape the coverage read found."""
    left = shapely.Polygon([(0, 0), (1000, 0), (1000, 500), (1000, 1000), (0, 1000)],
                           [[(1000, 500), (600, 300), (600, 700)]])
    right = shapely.Polygon([(1000, 0), (2000, 0), (2000, 1000), (1000, 1000), (1000, 500)],
                            [[(1000, 500), (1400, 700), (1400, 300)]])
    return left, right


def test_the_pinch_is_refused_by_geos_as_the_coverage_read_found():
    shapely = pytest.importorskip("shapely")
    numpy = pytest.importorskip("numpy")
    left, right = _pinch(shapely)
    assert left.is_valid and right.is_valid
    assert not shapely.coverage_is_valid(numpy.array([left, right]))


def test_opening_moves_only_the_holes_and_makes_a_valid_coverage():
    shapely = pytest.importorskip("shapely")
    numpy = pytest.importorskip("numpy")
    left, right = _pinch(shapely)
    out, record = display._open_pinches(numpy.array([left, right]), display.OPEN_PINCH_M)
    assert record["step"] == "opened" and record["count"] == 2
    assert shapely.coverage_is_valid(out) and all(shapely.is_valid(out))
    for before, after in zip((left, right), out):
        assert list(after.exterior.coords) == list(before.exterior.coords)   # no border moved
        moved = shapely.Point(1000, 500).distance(shapely.LineString(after.interiors[0].coords))
        assert moved == pytest.approx(display.OPEN_PINCH_M, rel=1e-6)
        hole_after = shapely.Polygon(after.interiors[0].coords).area
        hole_before = shapely.Polygon(before.interiors[0].coords).area
        assert hole_after < hole_before                       # the water shrank, slightly


def test_an_overlap_is_not_a_pinch_and_is_still_refused():
    shapely = pytest.importorskip("shapely")
    numpy = pytest.importorskip("numpy")
    a, b = shapely.box(0, 0, 1000, 1000), shapely.box(900, 0, 2000, 1000)
    coverage, record = display._open_pinches(numpy.array([a, b]), display.OPEN_PINCH_M)
    assert record is None


def test_a_pinched_outline_draws_with_opened_before_simplified(tmp_path):
    geopandas = pytest.importorskip("geopandas")
    shapely = pytest.importorskip("shapely")
    left, right = _pinch(shapely)
    frame = geopandas.GeoDataFrame({"code": ["1", "2"]}, geometry=[left, right],
                                   crs=display.PROJECTED)
    path = tmp_path / "v.parquet"
    frame.to_parquet(path, index=False)
    drawn = display.draw(path.read_bytes(), tolerance_m=25, id_field="code")
    assert [s["step"] for s in drawn["steps"]] == ["opened", "simplified", "rounded",
                                                   "format_changed"]
    out = geopandas.read_file(io.BytesIO(drawn["bytes"]))
    assert len(out) == 2


def test_an_overlapping_outline_is_still_refused_whole(tmp_path):
    geopandas = pytest.importorskip("geopandas")
    shapely = pytest.importorskip("shapely")
    frame = geopandas.GeoDataFrame({"code": ["1", "2"]},
                                   geometry=[shapely.box(0, 0, 1000, 1000),
                                             shapely.box(900, 0, 2000, 1000)],
                                   crs=display.PROJECTED)
    path = tmp_path / "v.parquet"
    frame.to_parquet(path, index=False)
    with pytest.raises(s3.CanonicalRefusal, match="not a valid coverage"):
        display.draw(path.read_bytes(), tolerance_m=25)
