"""
tests/test_loam_records.py  |  rewildingCities, Sprint 06 zip 2 (D-275)

The records a profile reads that are not indicator values get views of their
own, keyed by (unit_authority, unit_code), every row naming the receipt it
came from, never through place_values (D-268, D-263). A record two receipts
both give means no view, naming them: which one stands is a choice (D-163).
"""

import json
from pathlib import Path

import pandas as pd
import yaml

from canopy.wonder.session import open_plot

REPO = Path(__file__).resolve().parents[1]

LITERACY = pd.DataFrame([
    {"record_id": "county:23005", "level": "county", "unit_authority": "us_census_geoid",
     "unit_code": "23005", "name": "Cumberland County", "measure": "literacy_at_or_below_level_1",
     "share": 0.12, "lower": 0.09, "upper": 0.15, "confidence": 0.95,
     "population_16_74": 230000, "left_out": 27600, "left_out_lower": 20700,
     "left_out_upper": 34500},
    {"record_id": "state:23", "level": "state", "unit_authority": "us_census_geoid",
     "unit_code": "23", "name": "Maine", "measure": "literacy_at_or_below_level_1",
     "share": 0.15, "lower": 0.13, "upper": 0.17, "confidence": 0.95,
     "population_16_74": 1000000, "left_out": 150000, "left_out_lower": 130000,
     "left_out_upper": 170000},
])


def a_plot(tmp_path):
    plot = tmp_path / "plots" / "demo"
    (plot / ".data").mkdir(parents=True)
    (plot / ".envelopes").mkdir()
    (plot / "manifest.yml").write_text(yaml.safe_dump({
        "city": {"id": "demo", "name": "demo"}, "crs": {"working": "EPSG:4326"},
        "datasets": {}}))
    return plot


def a_csv_receipt(plot, name, frame, semantic_type, id_field="record_id"):
    data = plot / ".data" / f"{name}.csv"
    frame.to_csv(data, index=False)
    meta = {"semantic_type": semantic_type, "data_category": "tabular", "crs": None,
            "row_count": len(frame), "variables": list(frame.columns)}
    if id_field:
        meta["id_field"] = id_field
    (plot / ".envelopes" / f"{name}.envelope.json").write_text(json.dumps({
        "data": {"path": str(data), "format": "csv"}, "metadata": meta,
        "provenance": [], "warnings": []}))


def opened(plot):
    return open_plot("demo", root=REPO, directory=plot)


def test_literacy_rows_are_a_view_keyed_by_place_naming_their_receipt(tmp_path):
    plot = a_plot(tmp_path)
    a_csv_receipt(plot, "literacy_estimates_estimates", LITERACY, "literacy_estimates")
    _v, loam, report = opened(plot)
    assert report["graph"]["literacy_estimates"]["made"]
    assert report["graph"]["literacy_estimates"]["key"] == ["unit_authority", "unit_code"]
    row = loam.con.execute("SELECT share, record_receipt, unit_code FROM literacy_estimates "
                           "WHERE unit_authority = 'us_census_geoid' AND unit_code = '23005'"
                           ).fetchone()
    assert row == ("0.12", "literacy_estimates_estimates.envelope.json", "23005")


def test_records_never_enter_place_values(tmp_path):
    plot = a_plot(tmp_path)
    a_csv_receipt(plot, "literacy_estimates_estimates", LITERACY, "literacy_estimates")
    _v, loam, report = opened(plot)
    assert not (report["graph"].get("place_values") or {}).get("made")


def test_one_record_in_two_receipts_makes_no_view_and_names_them(tmp_path):
    plot = a_plot(tmp_path)
    a_csv_receipt(plot, "literacy_a", LITERACY, "literacy_estimates")
    a_csv_receipt(plot, "literacy_b", LITERACY.head(1), "literacy_estimates")
    _v, loam, report = opened(plot)
    entry = report["graph"]["literacy_estimates"]
    assert not entry["made"]
    assert "literacy_a.envelope.json" in entry["why"] and "literacy_b.envelope.json" in entry["why"]
    assert "literacy_estimates" not in {r[0] for r in loam.con.execute(
        "SELECT table_name FROM information_schema.tables").fetchall()}


def test_a_receipt_without_its_id_field_is_left_out_by_name(tmp_path):
    plot = a_plot(tmp_path)
    a_csv_receipt(plot, "literacy_estimates_estimates", LITERACY, "literacy_estimates",
                  id_field=None)
    _v, _loam, report = opened(plot)
    entry = report["graph"]["literacy_estimates"]
    assert not entry["made"]
    assert any("declares no id field" in x for x in entry["left_out"])


def test_a_plot_without_records_says_so(tmp_path):
    _v, _loam, report = opened(a_plot(tmp_path))
    assert report["graph"]["section203_records"] == {
        "made": False, "why": "no run in plot 'demo' has made section203_records"}
