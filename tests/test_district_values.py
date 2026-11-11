"""
tests/test_district_values.py  |  rewildingCities, Sprint 05 change 10 (plan builds 4 and 5)

District values come from the ACS directly (Contract 3, rule 1), keyed by the
authority that codes their chamber (GRAPH-1, D-176). A Census GEOID is unique
only within its level: 23005 is Cumberland County, House District 5 and
Senate District 5, and only the authority tells them apart. The preparation
is held to that key here, before anything runs; its grain is one the method
offers (D-177); and loam keeps one code under three authorities as three
places and three facts, never one conflict.
"""

import json
from pathlib import Path

import pandas as pd
import yaml

from canopy.orchestrator.parsing import parse_experiment, parse_method
from canopy.wonder.session import open_plot

REPO = Path(__file__).resolve().parents[1]
PREPARATION = REPO / "plots" / "maine" / "preparations" / "maine_district_indicator_values.yml"
METHOD = REPO / "garden" / "methods" / "information" / "indicator_values.yml"
ACS_2024 = "2020-2024 (5-year estimates)"

# each district table, and the one authority its codes may be keyed by
CHAMBERS = {
    "$manifest.acs_sldl_2024": "us_census_sldl",
    "$manifest.acs_sldu_2024": "us_census_sldu",
}


# ── the preparation, before anything runs ─────────────────────────────────
def test_every_district_step_is_keyed_by_its_chambers_authority():
    seen = {}
    for step in parse_experiment(PREPARATION).steps:
        source = step.inputs.get("source")
        assert source in CHAMBERS, f"{step.id} reads {source}, which is not a district table"
        assert step.params.get("unit_authority") == CHAMBERS[source], (
            f"{step.id} keys {source} as {step.params.get('unit_authority')}; "
            f"a GEOID is unique only within its level (GRAPH-1)")
        seen[source] = step.id
    assert set(seen) == set(CHAMBERS), "both chambers are derived"


def test_the_preparation_chooses_a_grain_its_method_offers():
    run = parse_experiment(PREPARATION)
    assert run.lineage.kind == "preparation"
    assert run.lineage.curiosity_ref is None
    assert run.lineage.method_ref == "$methods/information/indicator_values"
    grain = run.choices["aggregation_unit_level"]
    assert grain == "state legislative district"
    assert grain in parse_method(METHOD).choices["aggregation_unit_level"].options


def test_every_step_takes_its_grain_from_the_choice():
    for step in parse_experiment(PREPARATION).steps:
        assert step.params.get("spatial_unit") == "$choices.aggregation_unit_level", (
            f"{step.id} names its grain by hand, outside its lineage (D-79)")


def test_widening_the_method_keeps_every_grain_it_offered():
    options = set(parse_method(METHOD).choices["aggregation_unit_level"].options)
    assert {"county", "county subdivision", "tract"} <= options


# ── one code, three authorities, in loam ──────────────────────────────────
PLACES = pd.DataFrame([
    {"authority": "us_census_geoid", "code": "23005", "level": "county", "vintage": "2024",
     "kind": "county", "name": "Cumberland County", "census_funcstat": None},
    {"authority": "us_census_sldl", "code": "23005", "level": "sldl", "vintage": "2024",
     "kind": "house_district", "name": "State House District 5 (2024); Maine",
     "census_funcstat": None},
    {"authority": "us_census_sldu", "code": "23005", "level": "sldu", "vintage": "2024",
     "kind": "senate_district", "name": "State Senate District 5 (2024); Maine",
     "census_funcstat": None},
])


def value(authority, code, v, indicator="cii_broadband"):
    return {"measurement_id": f"{indicator}:{authority}:{code}", "unit_authority": authority,
            "unit_code": code, "indicator": indicator, "value": v,
            "authority": "us_census_acs", "time": ACS_2024}


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


def test_one_code_under_three_authorities_is_three_places_and_three_facts(tmp_path):
    plot = a_plot(tmp_path)
    a_receipt(plot, "graph_places_places", PLACES, "places",
              {"id_fields": ["authority", "code"], "spatial_unit": "place"})
    # three receipts, as on real data: towns and counties, and one per chamber.
    # three different values, so a value landing on the wrong place would show
    for name, authority, v in (("county_derive_values", "us_census_geoid", 91.0),
                               ("sldl_derive_values", "us_census_sldl", 88.0),
                               ("sldu_derive_values", "us_census_sldu", 85.0)):
        a_receipt(plot, name, pd.DataFrame([value(authority, "23005", v)]),
                  "indicator_values", {"id_field": "measurement_id"})

    _vocab, loam, report = open_plot("demo", root=REPO, directory=plot)
    values = report["graph"]["indicator_values"]
    assert values["made"] and values["rows"] == 3 and values["collapsed"] == 0

    rows = loam.con.execute(
        "SELECT unit_authority, level, place_name, value, status FROM place_values "
        "WHERE unit_code = '23005' ORDER BY unit_authority").fetchall()
    assert rows == [
        ("us_census_geoid", "county", "Cumberland County", 91.0, "attached"),
        ("us_census_sldl", "sldl", "State House District 5 (2024); Maine", 88.0, "attached"),
        ("us_census_sldu", "sldu", "State Senate District 5 (2024); Maine", 85.0, "attached"),
    ]
