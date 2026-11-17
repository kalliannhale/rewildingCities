"""
tests/test_choropleth.py ~ the keyed join (D-331, LAYER-1)

a long-form table joins a place on (unit_authority, unit_code) to (authority,
code), wide, every indicator's columns beside the place's own; every row is
counted; a place with no row stays, empty; and every choice it could make
silently is refused. pure pandas: no geometry, no files but the authorities
seed. ~
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from canopy import choropleth as c

ROOT = Path(__file__).resolve().parents[1]
WIDTHS = {"us_census_geoid": {"state": 2, "county": 5, "cousub": 10},
          "us_census_sldl": {"sldl": 5}}


def table(rows=None):
    rows = rows or [
        ("us_census_geoid", "23005", "cii_broadband", 92.7, 61.0),
        ("us_census_geoid", "23029", "cii_broadband", 84.3, 12.5),
        ("us_census_geoid", "04013", "cii_broadband", 90.1, 44.0),     # Arizona: outside
        ("us_census_geoid", "23", "cii_broadband", 89.0, None),        # the state: another level
        ("us_census_sldl", "23001", "cii_broadband", 88.0, None),      # a district: another authority
    ]
    return pd.DataFrame([{"unit_authority": a, "unit_code": u, "indicator": i, "value": v,
                          "percentile": p, "name": f"row {u}", "context_note": None}
                         for a, u, i, v, p in rows])


def places():
    return [{"authority": "us_census_geoid", "code": "23005", "name": "Cumberland County",
             "context_note": None},
            {"authority": "us_census_geoid", "code": "23029", "name": "Washington County",
             "context_note": "contains_census_tribal_area"},
            {"authority": "us_census_geoid", "code": "23031", "name": "York County",
             "context_note": None}]


def test_a_row_joins_its_place_by_authority_and_code_wide():
    out = c.join(table(), places(), level="county", widths=WIDTHS)
    by = {p["code"]: p for p in out["properties"]}
    assert by["23005"]["cii_broadband__value"] == 92.7
    assert by["23005"]["cii_broadband__percentile"] == 61.0
    assert by["23005"]["name"] == "Cumberland County"          # the place's own name wins
    assert by["23005"]["cii_broadband__name"] == "row 23005"   # the table's is kept, named
    assert by["23005"][c.JOINED] is True


def test_a_place_with_no_row_stays_empty_never_dropped():
    out = c.join(table(), places(), level="county", widths=WIDTHS)
    york = [p for p in out["properties"] if p["code"] == "23031"][0]
    assert york[c.JOINED] is False and york["cii_broadband__value"] is None
    assert len(out["properties"]) == 3 and out["counts"]["places_without_row"] == 1


def test_every_row_is_counted_where_it_belongs():
    k = c.join(table(), places(), level="county", widths=WIDTHS)["counts"]
    assert k["rows_in_outline"] == 2
    assert k["rows_outside_outline"] == 1       # Arizona, at the outline's own level
    assert k["rows_other_level"] == 1           # the state row
    assert k["rows_other_authority"] == 1       # the House district, same code width


def test_a_district_never_joins_a_county_that_shares_its_code():
    t = table([("us_census_sldl", "23005", "cii_broadband", 1.0, 1.0)])
    with pytest.raises(c.ChoroplethRefusal, match="no row of the table names a place"):
        c.join(t, places(), level="county", widths=WIDTHS)


def test_a_row_written_twice_is_refused():
    t = pd.concat([table(), table().iloc[:1]])
    with pytest.raises(c.ChoroplethRefusal, match="share a unit and indicator"):
        c.join(t, places(), level="county", widths=WIDTHS)


def test_a_place_without_its_key_is_refused_never_name_matched():
    bad = [{"name": "Cumberland County", "GEOID": "23005"}]
    with pytest.raises(c.ChoroplethRefusal, match="no authority and code") as e:
        c.join(table(), bad, level="county", widths=WIDTHS)
    assert "GEOID" in e.value.reason


def test_an_outline_under_two_authorities_is_refused():
    mixed = places() + [{"authority": "us_census_sldl", "code": "23001"}]
    with pytest.raises(c.ChoroplethRefusal, match="2 authorities"):
        c.join(table(), mixed, level="county", widths=WIDTHS)


def test_a_level_with_no_declared_width_is_refused():
    with pytest.raises(c.ChoroplethRefusal, match="no width"):
        c.join(table(), places(), level="tract", widths=WIDTHS)


def test_a_column_that_would_overwrite_a_place_is_refused():
    p = places()
    p[0]["cii_broadband__value"] = "a place's own"
    with pytest.raises(c.ChoroplethRefusal, match="overwrite"):
        c.join(table(), p, level="county", widths=WIDTHS)


def test_a_table_that_is_not_long_form_is_refused():
    with pytest.raises(c.ChoroplethRefusal, match="not long-form"):
        c.join(pd.DataFrame({"GEOID": ["23005"], "pci": [1.0]}), places(), level="county",
               widths=WIDTHS)


def test_two_indicators_sit_side_by_side():
    t = pd.concat([table(), table().assign(indicator="cii_rent_burden", value=30.0)])
    out = c.join(t, places(), level="county", widths=WIDTHS)
    assert out["indicators"] == ["cii_broadband", "cii_rent_burden"]
    cumberland = out["properties"][0]
    assert cumberland["cii_rent_burden__value"] == 30.0
    assert cumberland["cii_broadband__value"] == 92.7


def test_the_notes_are_those_the_drawn_places_carry():
    t = table()
    t.loc[t["unit_code"] == "04013", "context_note"] = "an_arizona_note"
    out = c.join(t, places(), level="county", widths=WIDTHS)
    assert c.row_notes(out["properties"]) == ["contains_census_tribal_area"]


def test_a_map_colours_a_standing_by_percentile_and_markers_by_count():
    cols = {"x": ["x__value", "x__percentile", "x__count"]}
    assert c.colour_field("x", cols) == "x__percentile"
    assert c.colour_field("x", cols, markers=True) == "x__count"
    with pytest.raises(c.ChoroplethRefusal, match="no indicator"):
        c.colour_field("y", cols)


def test_missing_values_become_none():
    assert c.plain(float("nan")) is None and c.plain(pd.NA) is None
    assert c.plain(pd.Timestamp("2026-11-01")) == "2026-11-01T00:00:00"


def test_the_widths_come_from_the_authorities_seed():
    widths = c.load_widths(ROOT)
    assert widths["us_census_geoid"]["county"] == 5
    assert widths["us_census_geoid"]["cousub"] == 10
