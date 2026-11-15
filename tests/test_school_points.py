"""tests for soil/transform/prepare_school_points.py (Sprint 06, step 3, the
second carrier; a school is placed where NCES's point stands, never by its
operator, D-230; NCES's columns and codes read from one crosswalk, D-226)."""

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "prepare_school_points", ROOT / "soil" / "transform" / "prepare_school_points.py")
sp = importlib.util.module_from_spec(_spec)
sys.modules["prepare_school_points"] = sp
_spec.loader.exec_module(sp)

READING = yaml.safe_load(
    (ROOT / "seeds" / "crosswalks" / "schools" / "nces_edge_geocode.yml").read_text())

FAYETTE = ("230000800455|2300008|Fayette Central School|23|2023 Main Street|Fayette|ME|04349|23|"
           "23011|Kennebec County|42|44.407300|-70.039147|12300|Augusta-Waterville, ME|2|N|N|"
           "2302|23058|23017|2024-2025")
# INDIAN_ISLAND: NCESSCH through CITY, county and coordinates are the release's;
# locale, CBSA and districts are illustrative, not NCES's values.
INDIAN_ISLAND = ("590016000051|5900160|Indian Island School|59|10 Wabanaki Way|Indian Island|ME|"
                 "04468|23|23019|Penobscot County|41|44.949901|-68.646884|12620|Bangor, ME|1|N|N|"
                 "2302|23021|23009|2024-2025")
NO_POINT = ("230000899999|2300008|Lost School|23|M|M|ME|M|N|N|N|N|M|M|N|N|N|N|N|N|N|N|2024-2025")
OVER_LINE = ("230000877777|2300008|Border School|23|1 Line Rd|Kittery|ME|03904|33|33015|"
             "Rockingham County|41|43.08|-70.75|14460|Boston, MA-NH|1|148|Boston, MA|3301|33001|"
             "33021|2024-2025")
QUOTED = ('180020202661|1800202|"Bethel Park Elementary | pilotED Schools"|18|2710 Bethel Ave|'
          "Indianapolis|IN|46203|18|18097|Marion County|11|39.744248|-86.117110|26900|"
          "Indianapolis, IN|1|294|Indianapolis, IN|1807|18100|18046|2024-2025")
ROWS = [FAYETTE, INDIAN_ISLAND, NO_POINT, OVER_LINE, QUOTED]


def _table(rows=ROWS):
    return sp.read_geocodes(("\n".join(rows) + "\n").encode("utf-8"), "utf-8", READING)


def _points(rows=ROWS):
    return sp.points_from(_table(rows), "ME", "23", READING)


def _ids(fc):
    return [f["properties"]["feature_id"] for f in fc["features"]]


def test_a_feature_is_a_school_named_by_ncessch():
    fc, meta = _points()
    assert _ids(fc) == ["230000800455", "590016000051"]
    assert meta["id_field"] == "feature_id" and meta["spatial_unit"] == "public_school"
    assert all(f["properties"]["name"] for f in fc["features"])


def test_a_quoted_pipe_stays_inside_one_name():
    t = _table()
    assert "Bethel Park Elementary | pilotED Schools" in set(t["NAME"])
    assert list(t.columns) == READING["columns"]


def test_a_school_operated_from_elsewhere_is_placed_and_flagged():
    fc, meta = _points()
    flags = {f["properties"]["feature_id"]: f["properties"]["flags"] for f in fc["features"]}
    assert flags["590016000051"] == "operator_59:operated by the Bureau of Indian Education"
    assert flags["230000800455"] is None
    assert meta["operated_elsewhere"] == ["590016000051"]


def test_an_operator_filter_would_drop_what_the_rule_keeps():
    t = _table()
    by_operator = set(t[t["OPSTFIPS"] == "23"]["NCESSCH"])
    fc, _ = _points()
    assert "590016000051" in _ids(fc) and "590016000051" not in by_operator


def test_a_school_located_in_another_state_is_listed_never_placed():
    fc, meta = _points()
    assert "230000877777" not in _ids(fc)
    assert [s["feature_id"] for s in meta["located_elsewhere"]] == ["230000877777"]
    assert meta["located_elsewhere"][0]["reason"] == "located_in_another_state"


def test_nces_markers_are_never_values():
    fc, _ = _points()
    props = {f["properties"]["feature_id"]: f["properties"] for f in fc["features"]}
    assert props["230000800455"]["nces_cd"] == "2302"
    assert "N" not in props["230000800455"].values()


def test_a_school_with_no_coordinates_is_listed_by_reason():
    fc, meta = _points()
    assert "230000899999" not in _ids(fc)
    assert meta["unplaced_schools"] == [{"feature_id": "230000899999", "name": "Lost School",
                                         "city": None, "state": "ME", "located_state_fips": None,
                                         "reason": "no_coordinates"}]
    assert [s["feature_id"] for s in meta["located_elsewhere"]] == ["230000877777"]


def test_the_receipt_names_the_source_datum_and_year():
    _, meta = _points()
    assert meta["source_crs"] == "EPSG:4269" and meta["crs"] == "EPSG:4326"
    assert meta["school_years"] == ["2024-2025"]


def test_a_row_with_another_field_count_is_refused():
    with pytest.raises(sp.SchoolPointsRefused, match="declared columns"):
        _table([FAYETTE, FAYETTE + "|extra"])


def test_a_header_row_is_refused():
    with pytest.raises(sp.SchoolPointsRefused, match="headerless"):
        _table(["|".join(READING["columns"]), FAYETTE])


def test_a_feature_id_used_twice_is_refused():
    with pytest.raises(sp.SchoolPointsRefused, match="used twice"):
        _points([FAYETTE, FAYETTE])


def test_the_declared_encoding_is_held():
    raw = ("\n".join([FAYETTE.replace("Fayette Central", "Fayétte Central")]) + "\n").encode("latin-1")
    with pytest.raises(sp.SchoolPointsRefused, match="not utf-8"):
        sp.read_geocodes(raw, "utf-8", READING)


def test_a_crosswalk_missing_a_needed_column_is_refused():
    broken = dict(READING, columns=[c for c in READING["columns"] if c != "STFIP"])
    with pytest.raises(sp.SchoolPointsRefused, match="STFIP"):
        sp.read_geocodes((FAYETTE + "\n").encode(), "utf-8", broken)
