"""
tests/test_loam_values.py  |  rewildingCities, Sprint 05 change 7 (plan build 2)

Values attach to places in loam as views, never copies (D-168): every value
table is combined into indicator_values, keyed (unit_authority, unit_code,
indicator, time) with no level of its own (D-169), and place_values joins
them to places, so towns, districts and counties sit in one view. Each row
says whether it attached and, if not, why: no place, no declared rule (D-170),
a Census tribal area (D-171), boundaries that differ, or attached but
unchecked for a statistical area. A key two tables both give is one fact when
they agree and no view when they disagree (D-172). A count of ours says which
boundaries it was counted on in boundary_vintage, never through `time`
(D-231). Each publisher is judged on its own levels (LOAM-2), so a count of
ours attaches to a Census tribal area, beside its note (D-233).
"""

import json
from pathlib import Path

import pandas as pd
import yaml

from canopy.wonder.session import open_plot

REPO = Path(__file__).resolve().parents[1]
ACS_2024 = "2020-2024 (5-year estimates)"

PLACES = pd.DataFrame([
    {"authority": "us_census_geoid", "code": "23005", "level": "county", "vintage": "2024",
     "kind": "county", "name": "Cumberland County", "census_funcstat": None},
    {"authority": "us_census_geoid", "code": "2300560545", "level": "cousub", "vintage": "2024",
     "kind": "city", "name": "Portland city", "census_funcstat": "F"},
    {"authority": "us_census_geoid", "code": "2300990001", "level": "cousub", "vintage": "2024",
     "kind": "unorganized_territory", "name": "Example UT", "census_funcstat": "S"},
    {"authority": "us_census_sldl", "code": "23118", "level": "sldl", "vintage": "2024",
     "kind": "house_district", "name": "House District 118", "census_funcstat": None},
    {"authority": "us_census_aiannh", "code": "2760R", "level": "aiannh", "vintage": "2020",
     "kind": "tribal_reservation", "name": "Penobscot Reservation", "census_funcstat": None},
])


def value(authority, code, indicator="cii_broadband", time=ACS_2024, publisher="us_census_acs",
          v=90.0):
    return {"measurement_id": f"{indicator}:{authority}:{code}", "unit_authority": authority,
            "unit_code": code, "indicator": indicator, "value": v, "published_by": publisher,
            "time": time}


TOWN_VALUES = pd.DataFrame([
    value("us_census_geoid", "2300560545"),
    value("us_census_geoid", "2300990001"),
    value("us_census_geoid", "2399999999"),
])
OTHER_VALUES = pd.DataFrame([
    value("us_census_geoid", "23005"),
    value("us_census_geoid", "23005", indicator="cii_rent_burden",
          time="2019-2023 (5-year estimates)"),
    value("us_census_sldl", "23118"),
    value("us_census_sldl", "23118", indicator="cii_rent_burden", publisher="someone_else"),
    value("us_census_aiannh", "2760R"),
])


def a_plot(tmp_path):
    plot = tmp_path / "plots" / "demo"
    (plot / ".data").mkdir(parents=True)
    (plot / ".envelopes").mkdir()
    (plot / "manifest.yml").write_text(yaml.safe_dump({
        "city": {"id": "demo", "name": "demo"}, "crs": {"working": "EPSG:4326"},
        "datasets": {}}))
    return plot


def a_receipt(plot, name, frame, semantic_type, metadata=None):
    data = plot / ".data" / f"{name}.parquet"
    frame.to_parquet(data, index=False)
    meta = {"semantic_type": semantic_type, "data_category": "tabular", "crs": None,
            "row_count": len(frame), "variables": list(frame.columns), **(metadata or {})}
    (plot / ".envelopes" / f"{name}.envelope.json").write_text(json.dumps({
        "data": {"path": str(data), "format": "parquet"}, "metadata": meta,
        "provenance": [], "warnings": []}))


def a_valued_plot(tmp_path):
    plot = a_plot(tmp_path)
    a_receipt(plot, "graph_places_places", PLACES, "places",
              {"id_fields": ["authority", "code"], "spatial_unit": "place"})
    a_receipt(plot, "cousub_derive_values", TOWN_VALUES, "indicator_values",
              {"id_field": "measurement_id"})
    a_receipt(plot, "other_derive_values", OTHER_VALUES, "indicator_values",
              {"id_field": "measurement_id"})
    return plot


def opened(plot):
    return open_plot("demo", root=REPO, directory=plot)


def status_of(loam, authority, code, indicator="cii_broadband"):
    return loam.con.execute(
        "SELECT status, attached, why, level FROM place_values "
        "WHERE unit_authority = ? AND unit_code = ? AND indicator = ?",
        [authority, code, indicator]).fetchone()


# ── one view, every level ─────────────────────────────────────────────────
def test_towns_districts_and_counties_sit_in_one_view(tmp_path):
    _vocab, loam, report = opened(a_valued_plot(tmp_path))
    assert report["graph"]["indicator_values"]["rows"] == 8
    levels = {r[0] for r in loam.con.execute(
        "SELECT DISTINCT level FROM place_values WHERE attached").fetchall()}
    assert levels == {"county", "cousub", "sldl"}


def test_a_value_has_its_places_level_never_its_own(tmp_path):
    _vocab, loam, _ = opened(a_valued_plot(tmp_path))
    status, attached, _why, level = status_of(loam, "us_census_sldl", "23118")
    assert (status, attached, level) == ("attached", True, "sldl")


# ── every refusal names why ───────────────────────────────────────────────
def test_a_tribal_area_value_is_refused_and_says_why(tmp_path):
    _vocab, loam, _ = opened(a_valued_plot(tmp_path))
    status, attached, why, _ = status_of(loam, "us_census_aiannh", "2760R")
    assert (status, attached) == ("tribal_area", False)
    assert "2024 boundaries" in why and "Census 2020 legal area" in why and "D-171" in why


def test_a_value_on_other_boundaries_is_refused(tmp_path):
    _vocab, loam, _ = opened(a_valued_plot(tmp_path))
    status, attached, why, _ = status_of(loam, "us_census_geoid", "23005", "cii_rent_burden")
    assert (status, attached) == ("vintage_mismatch", False)
    assert "2023 boundaries" in why and "2024" in why


def test_a_statistical_area_attaches_unchecked(tmp_path):
    _vocab, loam, _ = opened(a_valued_plot(tmp_path))
    status, attached, why, _ = status_of(loam, "us_census_geoid", "2300990001")
    assert (status, attached) == ("unchecked_statistical", True)
    assert "not yet verified" in why


def test_a_value_with_no_place_is_named(tmp_path):
    _vocab, loam, _ = opened(a_valued_plot(tmp_path))
    status, attached, why, _ = status_of(loam, "us_census_geoid", "2399999999")
    assert (status, attached) == ("no_place", False)


def test_a_publisher_with_no_declared_rule_attaches_nothing(tmp_path):
    _vocab, loam, _ = opened(a_valued_plot(tmp_path))
    status, attached, why, _ = status_of(loam, "us_census_sldl", "23118", "cii_rent_burden")
    assert (status, attached) == ("no_rule", False)
    assert "D-170" in why


# ── keys ──────────────────────────────────────────────────────────────────
def test_two_tables_that_agree_on_a_key_are_one_fact_recorded_twice(tmp_path):
    plot = a_valued_plot(tmp_path)
    a_receipt(plot, "older_derive_values", TOWN_VALUES.head(1), "indicator_values")
    _vocab, loam, report = opened(plot)
    values = report["graph"]["indicator_values"]
    assert values["made"] and values["rows"] == 8 and values["collapsed"] == 1
    assert values["agreeing"] == ["cousub_derive_values.envelope.json, "
                                  "older_derive_values.envelope.json"]
    (recorded,) = loam.con.execute(
        "SELECT recorded_in FROM place_values WHERE unit_code = '2300560545'").fetchone()
    assert "older_derive_values" in recorded and "cousub_derive_values" in recorded


def test_two_tables_that_disagree_on_a_key_make_no_view_naming_only_them(tmp_path):
    plot = a_valued_plot(tmp_path)
    a_receipt(plot, "older_derive_values", TOWN_VALUES.head(1).assign(value=12.5),
              "indicator_values")
    _vocab, _loam, report = opened(plot)
    why = report["graph"]["indicator_values"]["why"]
    assert "different values" in why and "D-172" in why
    assert "cousub_derive_values.envelope.json and older_derive_values.envelope.json" in why
    assert "other_derive_values" not in why
    assert not report["graph"]["place_values"]["made"]


def test_every_value_names_the_receipt_it_was_read_from(tmp_path):
    _vocab, loam, _ = opened(a_valued_plot(tmp_path))
    receipts = {r[0] for r in loam.con.execute(
        "SELECT DISTINCT value_receipt FROM place_values").fetchall()}
    assert receipts == {"cousub_derive_values.envelope.json", "other_derive_values.envelope.json"}


def test_a_value_table_without_the_key_is_left_out_by_name(tmp_path):
    plot = a_valued_plot(tmp_path)
    a_receipt(plot, "units_derive_values", TOWN_VALUES.drop(columns=["unit_authority"]),
              "indicator_values")
    _vocab, _loam, report = opened(plot)
    values = report["graph"]["indicator_values"]
    assert values["made"] and values["rows"] == 8
    assert any("units_derive_values" in w and "unit_authority" in w for w in values["left_out"])


def test_deleting_and_rebuilding_loam_gives_the_same_values(tmp_path):
    plot = a_valued_plot(tmp_path)
    query = "SELECT * FROM place_values ORDER BY unit_authority, unit_code, indicator, time"
    _vocab, loam, _ = opened(plot)
    before = loam.con.execute(query).fetchall()
    loam.con.close()
    (plot / ".loam" / "loam.duckdb").unlink()
    _vocab, again, _ = opened(plot)
    assert again.con.execute(query).fetchall() == before


# ── a count's boundaries travel in boundary_vintage (D-231) ───────────────
def a_count(authority, code, boundary_vintage="2024", time="2026-11-14"):
    row = value(authority, code, indicator="health_center_sites_per_1000", time=time,
                publisher="rewildingcities", v=1.5)
    if boundary_vintage is not ...:
        row["boundary_vintage"] = boundary_vintage
    return row


def a_counted_plot(tmp_path, rows):
    plot = a_valued_plot(tmp_path)
    a_receipt(plot, "sites_counts_values", pd.DataFrame(rows), "indicator_values",
              {"id_field": "measurement_id"})
    return plot


def test_a_count_dated_by_its_snapshot_attaches_on_its_edges_boundaries(tmp_path):
    _vocab, loam, _ = opened(a_counted_plot(tmp_path, [a_count("us_census_geoid", "2300560545")]))
    status, attached, _why, _ = status_of(loam, "us_census_geoid", "2300560545",
                                          "health_center_sites_per_1000")
    assert (status, attached) == ("attached", True)


def test_a_count_on_other_boundaries_is_a_mismatch_whatever_its_time(tmp_path):
    rows = [a_count("us_census_geoid", "23005", boundary_vintage="2020", time="FY 2024")]
    _vocab, loam, _ = opened(a_counted_plot(tmp_path, rows))
    status, attached, why, _ = status_of(loam, "us_census_geoid", "23005",
                                         "health_center_sites_per_1000")
    assert (status, attached) == ("vintage_mismatch", False)
    assert "2020 boundaries" in why


def test_a_count_that_does_not_say_its_boundaries_is_refused_by_name(tmp_path):
    _vocab, loam, _ = opened(a_counted_plot(
        tmp_path, [a_count("us_census_geoid", "23005", boundary_vintage=...)]))
    status, attached, why, _ = status_of(loam, "us_census_geoid", "23005",
                                         "health_center_sites_per_1000")
    assert (status, attached) == ("no_boundary_vintage", False)
    assert "boundary_vintage" in why and "D-231" in why


def test_a_blank_boundary_vintage_beside_a_filled_one_is_refused(tmp_path):
    rows = [a_count("us_census_geoid", "2300560545"),
            a_count("us_census_geoid", "23005", boundary_vintage=None)]
    _vocab, loam, _ = opened(a_counted_plot(tmp_path, rows))
    assert status_of(loam, "us_census_geoid", "23005",
                     "health_center_sites_per_1000")[0] == "no_boundary_vintage"
    assert status_of(loam, "us_census_geoid", "2300560545",
                     "health_center_sites_per_1000")[0] == "attached"


def test_the_acs_is_still_judged_by_its_time_beside_our_counts(tmp_path):
    _vocab, loam, _ = opened(a_counted_plot(tmp_path, [a_count("us_census_geoid", "2300560545")]))
    assert status_of(loam, "us_census_geoid", "23005", "cii_rent_burden")[0] == "vintage_mismatch"
    assert status_of(loam, "us_census_sldl", "23118")[0] == "attached"


# ── a tribal area: our count attaches with its note, the ACS still does not ─
def test_our_tribal_count_attaches_on_the_areas_own_vintage_with_its_note(tmp_path):
    row = a_count("us_census_aiannh", "2760R", boundary_vintage="2020")
    row["context_note"] = "carrier_unseen_on_nations_land"
    _vocab, loam, _ = opened(a_counted_plot(tmp_path, [row]))
    status, attached, _why, level = status_of(loam, "us_census_aiannh", "2760R",
                                              "health_center_sites_per_1000")
    assert (status, attached, level) == ("attached", True, "aiannh")
    (note,) = loam.con.execute(
        "SELECT context_note FROM place_values WHERE unit_code = '2760R' "
        "AND indicator = 'health_center_sites_per_1000'").fetchone()
    assert note == "carrier_unseen_on_nations_land"


def test_the_acs_on_a_tribal_area_is_still_refused_beside_our_count(tmp_path):
    row = a_count("us_census_aiannh", "2760R", boundary_vintage="2020")
    _vocab, loam, _ = opened(a_counted_plot(tmp_path, [row]))
    assert status_of(loam, "us_census_aiannh", "2760R")[0] == "tribal_area"


def test_a_publisher_is_judged_on_its_own_levels(tmp_path):
    # the ACS declares no tribal level, ours does: one rule never stands in
    # for another (LOAM-2)
    rules = yaml.safe_load((REPO / "seeds" / "vintages" / "boundaries.yml").read_text())
    assert "aiannh" not in rules["publishers"]["us_census_acs"]["levels"]
    assert "aiannh" in rules["publishers"]["rewildingcities"]["levels"]
