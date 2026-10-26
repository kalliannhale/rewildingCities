"""tests/test_map_join_scope.py

MAP-2 and MAP-3: a choropleth keeps every unit of its layer, tells rows that
belong elsewhere apart from rows of this place that failed to join, and
carries the result's provenance chain and warnings.
"""

from canopy.cli.map import _join_and_color

import pandas as pd


def _fixture():
    df = pd.DataFrame({
        "GEOID": ["2300102060", "2300102061", "2300199999", "0100100000"],
        "indicator": ["x"] * 4,
        "value": [80.0, 90.0, 70.0, 50.0],
    })
    features = [{"type": "Feature", "properties": {"GEOID": g}, "geometry": None}
                for g in ["2300102060", "2300102061", "2300103000"]]
    envelope = {"provenance": [{"primitive": "derive_indicator"}],
                "warnings": [{"level": "warning", "primitive": "derive_indicator", "message": "m"}]}
    return _join_and_color(df, features, {"semantic_type": "indicator_values"},
                           "layer", "maine", key="GEOID", color_by="value",
                           envelope=envelope, result_name="result")


def test_rows_are_split_by_scope():
    m = _fixture()["rewilding:map"]
    assert m["unjoined_rows"] == 2
    assert m["rows_outside_scope"] == 1
    assert m["rows_unmatched_in_scope"] == 1
    assert m["unmatched_in_scope_examples"] == ["2300199999"]


def test_a_unit_without_a_row_stays_on_the_map_as_empty():
    fc = _fixture()
    assert len(fc["features"]) == 3
    missing = [f for f in fc["features"] if f["properties"]["GEOID"] == "2300103000"][0]
    assert missing["properties"]["joined"] is False
    assert missing["properties"]["value"] is None
    assert missing["properties"]["fill"] == "#d9d9d9"
    assert fc["rewilding:map"]["features_without_row"] == 1


def test_provenance_and_warnings_travel_with_the_map():
    prov = _fixture()["rewilding:provenance"]
    assert prov["result_envelope"] == "result"
    assert prov["chain"][0]["primitive"] == "derive_indicator"
    assert len(prov["warnings"]) == 1
