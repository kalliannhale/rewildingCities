"""
tests/test_map_indicators.py

map draws one indicator out of a long-form table, joins it by its declared
authority (LAYER-1: unit_authority and unit_code to a place's authority and
code, through canopy/choropleth.py), draws an empty value as empty, and
refuses a choice it would otherwise make silently (MAP-1). a wide result
(NYC's parks) still joins on a shared column.
"""

import pandas as pd
import pytest

from canopy.cli import map as m


def long_table():
    rows = []
    for ind, vals in {"cii_broadband": [92.7, 84.3, None],
                      "cii_rent_burden": [30.0, 30.8, 27.7]}.items():
        for code, v in zip(["23005", "23029", "23031"], vals):
            rows.append({"measurement_id": f"{ind}:{code}", "unit_authority": "us_census_geoid",
                         "unit_code": code, "name": code, "indicator": ind,
                         "value": float("nan") if v is None else v, "moe": float("nan"),
                         "moe_status": "not_derived"})
    return pd.DataFrame(rows)


WIDTHS = {"us_census_geoid": {"state": 2, "county": 5, "cousub": 10}}


def counties(with_geoid=True, with_key=True):
    out = []
    for code, name in [("23005", "Cumberland"), ("23029", "Washington"), ("23031", "York")]:
        props = {"COUNTY": name, "CNTYCODE": code[2:]}
        if with_geoid:
            props["GEOID"] = code
        if with_key:
            props.update(authority="us_census_geoid", code=code)
        out.append({"type": "Feature", "properties": props,
                    "geometry": {"type": "Point", "coordinates": [0, 0]}})
    return out


def keyed(one, layer, color_by, indicator):
    return m.keyed_join(one, layer, level="county", widths=WIDTHS, color_by=color_by,
                        indicator=indicator, meta={"semantic_type": "indicator_values"},
                        layer="counties", plot="maine")


def env(st, cat, fmt, joins_to=None, path="x"):
    md = {"semantic_type": st, "data_category": cat}
    if joins_to:
        md["joins_to"] = joins_to
    return {"metadata": md, "data": {"path": path, "format": fmt}}


# ── one indicator out of many ──────────────────────────────────────────────
def test_a_long_table_needs_an_indicator_named():
    with pytest.raises(m.MapRefusal) as e:
        m.long_form_view(long_table(), None)
    assert "cii_broadband" in str(e.value) and "--indicator" in str(e.value)


def test_an_unknown_indicator_is_refused():
    with pytest.raises(m.MapRefusal):
        m.long_form_view(long_table(), "cii_nope")


def test_one_indicator_is_keyed_by_its_authority_and_colored_by_value():
    one, key, color_by = m.long_form_view(long_table(), "cii_rent_burden")
    assert (key, color_by) == (m.KEYED, "value")
    assert list(one["unit_code"]) == ["23005", "23029", "23031"]
    assert set(one["indicator"]) == {"cii_rent_burden"}


# ── the join ──────────────────────────────────────────────────────────────
def test_the_join_uses_the_declared_authority_and_keeps_empty_as_empty():
    one, _, color_by = m.long_form_view(long_table(), "cii_broadband")
    fc = keyed(one, counties(), color_by, "cii_broadband")
    by = {f["properties"]["code"]: f["properties"] for f in fc["features"]}
    assert by["23031"]["cii_broadband__value"] is None
    assert by["23031"]["fill"] == m._EMPTY_FILL
    assert by["23005"]["fill"] != m._EMPTY_FILL
    assert fc["rewilding:map"]["empty_values"] == 1
    assert fc["rewilding:map"]["color_by"] == "cii_broadband__value"


def test_a_layer_without_authority_and_code_is_refused_never_geoid_matched():
    one, _, color_by = m.long_form_view(long_table(), "cii_broadband")
    with pytest.raises(m.MapRefusal) as e:
        keyed(one, counties(with_key=False), color_by, "cii_broadband")
    assert "authority and code" in str(e.value) and "GEOID" in str(e.value)


def test_unjoined_rows_are_counted():
    one, _, color_by = m.long_form_view(long_table(), "cii_rent_burden")
    fc = keyed(one, counties()[:2], color_by, "cii_rent_burden")
    assert fc["rewilding:map"]["rows_outside_outline"] == 1
    assert fc["rewilding:map"]["places_without_row"] == 0


def test_a_wide_result_still_joins_the_old_way():
    df = pd.DataFrame({"GEOID": ["23005", "23029"], "pci": [1.0, 2.0]})
    fc = m._join_and_color(df, counties(), {}, "counties", "nyc")
    assert fc["rewilding:map"]["join_on"] == "GEOID"
    assert fc["rewilding:map"]["color_by"] == "pci"


# ── choices are refused, not made (MAP-1) ─────────────────────────────────
def test_two_layers_of_the_joined_type_are_a_choice():
    by_name = {"dissolve_counties_dissolved": env("governance_unit", "vector", "geojson"),
               "dissolve_towns_dissolved": env("governance_unit", "vector", "geojson")}
    meta = {"joins_to": "governance_unit"}
    with pytest.raises(m.MapRefusal) as e:
        m.resolve_layer(meta, by_name)
    assert "dissolve_counties_dissolved" in str(e.value) and "--layer" in str(e.value)
    name, _ = m.resolve_layer(meta, by_name, "dissolve_counties_dissolved")
    assert name == "dissolve_counties_dissolved"


def test_one_layer_is_simply_the_answer():
    by_name = {"counties": env("governance_unit", "vector", "geojson"),
               "values": env("indicator_values", "tabular", "parquet")}
    name, _ = m.resolve_layer({"joins_to": "governance_unit"}, by_name)
    assert name == "counties"


def test_no_layer_falls_back_to_the_descriptor():
    assert m.resolve_layer({"joins_to": "governance_unit"},
                           {"v": env("indicator_values", "tabular", "parquet")}) is None


def test_a_named_layer_must_exist():
    with pytest.raises(m.MapRefusal):
        m.resolve_layer({}, {"counties": env("governance_unit", "vector", "geojson")}, "towns")


def test_two_results_of_one_type_are_a_choice():
    by_name = {"a_values": env("indicator_values", "tabular", "parquet"),
               "b_values": env("indicator_values", "tabular", "parquet")}
    with pytest.raises(m.MapRefusal) as e:
        m.resolve_result(by_name, "indicator_values")
    assert "--result" in str(e.value)
    assert m.resolve_result(by_name, "indicator_values", "b_values")[0] == "b_values"


def test_a_standings_table_is_colored_by_percentile():
    df = long_table()
    df["percentile"] = [90.0, 10.0, None, 50.0, 20.0, 80.0]
    _, key, color_by = m.long_form_view(df, "cii_broadband")
    assert (key, color_by) == (m.KEYED, "percentile")