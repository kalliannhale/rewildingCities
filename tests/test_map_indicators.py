"""
tests/test_map_indicators.py

map draws one indicator out of a long-form table, joins on a declared key,
draws an empty value as empty, and refuses a choice it would otherwise make
silently (MAP-1).
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


def counties(with_geoid=True):
    out = []
    for code, name in [("23005", "Cumberland"), ("23029", "Washington"), ("23031", "York")]:
        props = {"COUNTY": name, "CNTYCODE": code[2:]}
        if with_geoid:
            props["GEOID"] = code
        out.append({"type": "Feature", "properties": props,
                    "geometry": {"type": "Point", "coordinates": [0, 0]}})
    return out


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


def test_one_indicator_is_keyed_by_geoid_and_colored_by_value():
    one, key, color_by = m.long_form_view(long_table(), "cii_rent_burden")
    assert (key, color_by) == ("GEOID", "value")
    assert list(one["GEOID"]) == ["23005", "23029", "23031"]
    assert set(one["indicator"]) == {"cii_rent_burden"}


# ── the join ──────────────────────────────────────────────────────────────
def test_the_join_uses_the_declared_key_and_keeps_empty_as_empty():
    one, key, color_by = m.long_form_view(long_table(), "cii_broadband")
    fc = m._join_and_color(one, counties(), {"semantic_type": "indicator_values"},
                           "counties", "maine", key=key, color_by=color_by)
    by = {f["properties"]["GEOID"]: f["properties"] for f in fc["features"]}
    assert by["23031"]["value"] is None
    assert by["23031"]["fill"] == m._EMPTY_FILL
    assert by["23005"]["fill"] != m._EMPTY_FILL
    assert fc["rewilding:map"]["empty_values"] == 1
    assert fc["rewilding:map"]["join_on"] == "GEOID"


def test_a_layer_without_the_key_is_refused_never_name_matched():
    one, key, color_by = m.long_form_view(long_table(), "cii_broadband")
    with pytest.raises(m.MapRefusal) as e:
        m._join_and_color(one, counties(with_geoid=False), {}, "counties", "maine",
                          key=key, color_by=color_by)
    assert "GEOID" in str(e.value) and "CNTYCODE" in str(e.value)


def test_unjoined_rows_are_counted():
    one, key, color_by = m.long_form_view(long_table(), "cii_rent_burden")
    fc = m._join_and_color(one, counties()[:2], {}, "counties", "maine",
                           key=key, color_by=color_by)
    assert fc["rewilding:map"]["unjoined_rows"] == 1


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
    assert (key, color_by) == ("GEOID", "percentile")