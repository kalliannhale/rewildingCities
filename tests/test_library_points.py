"""tests for soil/transform/prepare_library_points.py (Sprint 06, step 3)."""

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "prepare_library_points", ROOT / "soil" / "transform" / "prepare_library_points.py")
lp = importlib.util.module_from_spec(_spec)
sys.modules["prepare_library_points"] = lp
_spec.loader.exec_module(lp)

HEAD = ("STABR,FSCSKEY,FSCS_SEQ,LIBNAME,CITY,CNTY,C_OUT_TY,C_FSCS,STATSTRU,GEOMTYPE,"
        "GEOSCORE,CENBLOCK,LATITUDE,LONGITUD\n")
ROWS = [
    "ME,ME0033,002,CURTIS MEMORIAL LIBRARY,BRUNSWICK,CUMBERLAND,CE,Y,00,POINTADDRESS,100,230050112053012,43.91,-69.96",
    "ME,ME0033,003,CURTIS MEMORIAL LIBRARY,BRUNSWICK,CUMBERLAND,BS,Y,00,POINTADDRESS,100,230050112053012,43.91,-69.96",
    "ME,ME0174,006,PORTLAND - RIVERTON BRANCH,PORTLAND,CUMBERLAND,BR,Y,23,MANUAL,95,230050021022000,43.69,-70.30",
    "ME,ME0200,001,SMALL LIBRARY,TOWN,YORK,CE,N,25,POINTADDRESS,99,230310235011048,,",
    "NH,NH0001,001,ELSEWHERE,TOWN,X,CE,Y,00,POINTADDRESS,100,330000000000000,43.0,-71.0"]
TYPES = dict(fixed_types=["CE", "BR"], mobile_types=["BS", "BM"],
             status_codes={"02": "new outlet", "23": "closed temporarily"})


def _table(rows=ROWS):
    return lp.read_outlets((HEAD + "\n".join(rows) + "\n").encode("latin-1"), "latin-1")


def _points(rows=ROWS):
    return lp.points_from(_table(rows), "ME", **TYPES)


def test_a_feature_is_an_outlet_named_by_system_and_sequence():
    fc, meta = _points()
    ids = [f["properties"]["feature_id"] for f in fc["features"]]
    assert ids == ["ME0033-002", "ME0174-006", "ME0200-001"]
    assert meta["id_field"] == "feature_id"


def test_a_bookmobile_is_listed_and_never_placed():
    fc, meta = _points()
    assert "ME0033-003" not in [f["properties"]["feature_id"] for f in fc["features"]]
    assert meta["mobile_outlets"] == [{"feature_id": "ME0033-003", "type": "BS",
                                       "name": "CURTIS MEMORIAL LIBRARY", "city": "BRUNSWICK"}]


def test_flags_say_what_a_reader_must_know():
    fc, meta = _points()
    flags = {f["properties"]["feature_id"]: f["properties"]["flags"] for f in fc["features"]}
    assert flags["ME0033-002"] is None
    assert flags["ME0174-006"] == "manual_geocode;status_23:closed temporarily"
    assert flags["ME0200-001"] == "status_25:unknown;not_fscs_public_library"
    assert meta["status_codes_unknown"] == ["25"]


def test_a_point_with_no_coordinates_keeps_its_feature():
    fc, _ = _points()
    small = next(f for f in fc["features"] if f["properties"]["feature_id"] == "ME0200-001")
    assert small["geometry"] is None


def test_another_states_outlets_are_left_out():
    fc, _ = _points()
    assert all(f["properties"]["fscskey"].startswith("ME") for f in fc["features"])


def test_an_undeclared_outlet_type_is_refused():
    with pytest.raises(lp.LibraryPointsRefused, match="neither"):
        _points(ROWS + ["ME,ME0300,001,X,Y,Z,BM2,Y,00,POINTADDRESS,100,2300,43,-70"])


def test_a_byte_where_latin1_and_cp1252_disagree_is_refused():
    raw = (HEAD + ROWS[0]).encode("latin-1") + b"\x93\n"
    with pytest.raises(lp.LibraryPointsRefused, match="Windows-1252"):
        lp.read_outlets(raw, "latin-1")


def test_a_windows_1252_dash_reads_as_a_dash():
    row = ROWS[0].replace("CURTIS MEMORIAL", "CURTIS \u2013 MEMORIAL")
    table = lp.read_outlets((HEAD + row + "\n").encode("cp1252"), "windows-1252")
    assert "\u2013" in table.loc[0, "LIBNAME"]


def test_a_byte_windows_1252_does_not_define_is_refused():
    raw = (HEAD + ROWS[0]).encode("cp1252") + b"\x81\n"
    with pytest.raises(lp.LibraryPointsRefused, match="not windows-1252"):
        lp.read_outlets(raw, "windows-1252")


def test_an_accented_name_reads_as_written():
    row = ROWS[0].replace("CURTIS", "CURT\u00cdS")
    fc, _ = _points([row])
    assert fc["features"][0]["properties"]["name"].startswith("CURT\u00cdS")
