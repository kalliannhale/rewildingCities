"""tests for soil/transform/prepare_library_points.py (Sprint 06, step 3;
D-208, D-210, D-211)."""

import importlib.util
import sys
from pathlib import Path

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
    "ME,ME0175,001,GONE LIBRARY,TOWN,YORK,CE,Y,03,POINTADDRESS,100,230310235011049,43.5,-70.5",
    "NH,NH0001,001,ELSEWHERE,TOWN,X,CE,Y,00,POINTADDRESS,100,330000000000000,43.0,-71.0"]
CODES = {"00": {"meaning": "no change from last year", "group": "open"},
         "03": {"meaning": "closed", "group": "permanent"},
         "23": {"meaning": "temporary closure", "group": "temporary"},
         "25": {"meaning": "survey nonrespondent", "group": "open"}}
TYPES = dict(fixed_types=["CE", "BR"], mobile_types=["BS", "BM"])


def _table(rows=ROWS):
    return lp.read_outlets((HEAD + "\n".join(rows) + "\n").encode("latin-1"), "latin-1")


def _points(rows=ROWS, closed="listed", codes=CODES):
    return lp.points_from(_table(rows), "ME", **TYPES, status_codes=codes,
                          temporarily_closed=closed)


def _ids(fc):
    return [f["properties"]["feature_id"] for f in fc["features"]]


def test_a_feature_is_an_outlet_named_by_system_and_sequence():
    fc, meta = _points()
    assert _ids(fc) == ["ME0033-002", "ME0200-001"]
    assert meta["id_field"] == "feature_id"


def test_a_bookmobile_is_listed_and_never_placed():
    for closed in ("listed", "placed"):
        fc, meta = _points(closed=closed)
        assert "ME0033-003" not in _ids(fc)
        assert meta["mobile_outlets"] == [{"feature_id": "ME0033-003", "type": "BS",
                                           "name": "CURTIS MEMORIAL LIBRARY", "city": "BRUNSWICK"}]


def test_a_permanently_closed_outlet_is_listed_whatever_the_choice():
    for closed in ("listed", "placed"):
        fc, meta = _points(closed=closed)
        assert "ME0175-001" not in _ids(fc)
        gone = [o for o in meta["closed_outlets"] if o["feature_id"] == "ME0175-001"]
        assert gone == [{"feature_id": "ME0175-001", "type": "CE", "name": "GONE LIBRARY",
                         "city": "TOWN", "status": "03", "reason": "closed_permanently"}]


def test_a_temporary_closure_listed_is_named_and_not_placed():
    fc, meta = _points(closed="listed")
    assert "ME0174-006" not in _ids(fc)
    assert {"feature_id": "ME0174-006", "type": "BR", "name": "PORTLAND - RIVERTON BRANCH",
            "city": "PORTLAND", "status": "23", "reason": "closed_temporarily"} in meta["closed_outlets"]
    assert meta["temporarily_closed"] == "listed"


def test_a_temporary_closure_placed_carries_its_flag():
    fc, meta = _points(closed="placed")
    assert "ME0174-006" in _ids(fc)
    flags = {f["properties"]["feature_id"]: f["properties"]["flags"] for f in fc["features"]}
    assert flags["ME0174-006"] == "manual_geocode;status_23:temporary closure"
    assert [o["feature_id"] for o in meta["closed_outlets"]] == ["ME0175-001"]


def test_flags_carry_the_declared_meaning():
    fc, _ = _points()
    flags = {f["properties"]["feature_id"]: f["properties"]["flags"] for f in fc["features"]}
    assert flags["ME0033-002"] is None
    assert flags["ME0200-001"] == "status_25:survey nonrespondent;not_fscs_public_library"


def test_an_undeclared_status_code_is_refused():
    codes = {k: v for k, v in CODES.items() if k != "25"}
    with pytest.raises(lp.LibraryPointsRefused, match="25 are not declared"):
        _points(codes=codes)


def test_a_blank_status_is_refused():
    row = ROWS[0].replace(",CE,Y,00,", ",CE,Y,,")
    with pytest.raises(lp.LibraryPointsRefused, match="no structure status: ME0033-002"):
        _points([row])


def test_a_mobile_outlets_status_is_never_judged():
    row = ROWS[1].replace(",BS,Y,00,", ",BS,Y,99,")
    fc, meta = _points([ROWS[0], row])
    assert _ids(fc) == ["ME0033-002"] and len(meta["mobile_outlets"]) == 1


def test_a_status_without_meaning_or_group_is_refused():
    with pytest.raises(lp.LibraryPointsRefused, match="declares no meaning"):
        _points(codes={**CODES, "00": {"group": "open"}})
    with pytest.raises(lp.LibraryPointsRefused, match="group 'closed'"):
        _points(codes={**CODES, "03": {"meaning": "closed", "group": "closed"}})


def test_a_closure_choice_outside_its_options_is_refused():
    with pytest.raises(lp.LibraryPointsRefused, match="temporarily_closed is 'dropped'"):
        _points(closed="dropped")


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
